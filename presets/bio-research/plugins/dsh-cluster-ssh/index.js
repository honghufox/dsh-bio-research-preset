/**
 * dsh-cluster-ssh —— 基于**系统 OpenSSH** 的 LSF 集群执行通道。
 *
 * 为什么不用 ssh2：这台集群（OpenSSH 7.4）上实测 ssh2 能完成认证，但随后客户端发
 * CHANNEL_OPEN(session) 时服务器直接断 TCP（无 CHANNEL_OPEN_FAILURE）。已排除加密
 * 套件（aes128-ctr 同样失败）、客户端 ident、限速等因素；系统 OpenSSH 9.5 用同一账号
 * 同一算法完全正常。因此本插件以 `ssh` 子进程为执行后端。
 *
 * 会话模型（为延迟与 token 双重优化）：
 *   - 起一个 `ssh -tt` 交互式会话，**只认证一次**（集群 TOTP 配了 DISALLOW_REUSE，
 *     同一时间步的码只能验证一次，逐条命令重登录必然失败）；
 *   - 之后所有命令复用同一会话，实测后续命令 ~200ms 量级；
 *   - 命令输出用哨兵切分，剥掉 ANSI 转义与登录横幅，不产生 PTY 回显/prompt 噪音，
 *     并按上限截断，避免把无关字节喂进模型上下文。
 */
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const totpModule = require('./totp.cjs')

const { readConnections, readJson, dshHome, totpForEndpoint } = totpModule

export const name = 'dsh-cluster-ssh'
export const inject = ['tools']

/**
 * 把工具定义交给宿主注册表。
 *
 * 优先用 `@deepseek-ai/dsh-tools` 的 `defineTool`（第一方工具的标准写法）；它会做
 * 参数校验与类型推导。若该包在当前 profile 里解析不到，则回退成宿主同样接受的
 * 原始 ToolDefinition（MCP 来源的工具走的就是这条路），并把 `parameters` 写成
 * 标准 JSON Schema。这样插件不因宿主包解析差异而整体失效。
 * @param definition - 以 defineTool 风格书写的定义。
 * @returns 可供 `ctx.tools.register` 使用的定义。
 */
function toToolDefinition(definition) {
  let defineTool
  try {
    defineTool = require('@deepseek-ai/dsh-tools').defineTool
  } catch (error) {
    defineTool = undefined
  }
  if (typeof defineTool === 'function') return defineTool(definition)

  const properties = {}
  const required = []
  for (const [key, spec] of Object.entries(definition.parameters ?? {})) {
    const { required: isRequired, ...rest } = spec
    properties[key] = rest
    if (isRequired === true) required.push(key)
  }
  return {
    name: definition.name,
    description: definition.description,
    parameters: { type: 'object', properties, ...(required.length > 0 ? { required } : {}) },
    output: definition.output,
    execute: definition.execute,
  }
}

const HERE = dirname(fileURLToPath(import.meta.url))
const ASKPASS_DIR = join(HERE, 'askpass')
const ASKPASS_BAT = join(ASKPASS_DIR, 'askpass.bat')
const ASKPASS_JS = join(ASKPASS_DIR, 'answer.cjs')
const CRED_FILE = join(ASKPASS_DIR, 'credentials.json')
const COUNT_FILE = join(ASKPASS_DIR, 'count')

const DEFAULT_TIMEOUT_MS = 120_000
const DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024
const READY_PATTERN = /[$#]\s*$/
const START_TIMEOUT_MS = 45_000

/** 生成 askpass 三件套：无 tty 时 ssh 通过 SSH_ASKPASS 取「密码」与「动态口令」。 */
function ensureAskpass() {
  mkdirSync(ASKPASS_DIR, { recursive: true })
  writeFileSync(ASKPASS_BAT, [
    '@echo off',
    'setlocal',
    `set CRED=${CRED_FILE}`,
    `set CNT=${COUNT_FILE}`,
    'set N=0',
    'if exist "%CNT%" set /p N=<"%CNT%"',
    'set /a N=%N%+1',
    '> "%CNT%" echo %N%',
    `"${process.execPath}" "${ASKPASS_JS}" %N%`,
    'exit /b 0',
    '',
  ].join('\r\n'), 'utf8')
  writeFileSync(ASKPASS_JS, [
    "'use strict';",
    '// 由 askpass.bat 调用：第 1 次询问回密码，之后回动态口令。',
    "const fs = require('node:fs');",
    "const cred = JSON.parse(fs.readFileSync(process.env.CRED, 'utf8'));",
    "process.stdout.write(String(process.argv[2] === '1' ? cred.password : cred.otp) + '\\n');",
    '',
  ].join('\n'), 'utf8')
}

/** 每次发起认证前重写凭据与计数：密码固定，动态口令现算。 */
function writeCredentials(spec) {
  const otp = totpForEndpoint(spec.username, spec.host, spec.port)
  if (otp === null) {
    throw new Error(`缺少动态口令：请在 ${join(dshHome(), 'dsh-ssh-totp.json')} 里为 "${spec.username}@${spec.host}:${spec.port}" 配置 base32 密钥（该文件只存本机，不要提交到仓库）`)
  }
  writeFileSync(CRED_FILE, JSON.stringify({ password: spec.password ?? '', otp }), { encoding: 'utf8', mode: 0o600 })
  rmSync(COUNT_FILE, { force: true })
}

/**
 * 去掉 PTY 的 ANSI 控制序列与 `\r`，保留其余字节原样。
 * 输出的切分由调用方的标记界定完成，这里只做终端装饰的清理。
 * @param raw - 会话原始字节解码后的文本。
 * @returns 可读文本。
 */
function stripAnsi(raw) {
  return raw
    .replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, '')
    .replace(/\x1b\[[0-9;?]*[a-zA-Z]/g, '')
    .replace(/\x1b[=>()][A-Za-z0-9]?/g, '')
    .replace(/\r/g, '')
}

/**
 * 取出两个整行标记之间的内容，作为命令的真实输出。
 *
 * 回显里每行只含一个标记（其后还跟着命令余部），而真实标记独占一行，因此用
 * 「标记后紧跟换行或文本结束」定位真正的边界：从最后一个这样的 `pre` 之后开始，
 * 到其后第一个 `post` 为止。
 * @param text - 已剥离 ANSI 的会话文本。
 * @param pre - 输出起始标记。
 * @param post - 输出结束标记。
 * @param command - 原始命令（回填到结果里）。
 * @param maxOutputBytes - 输出字节上限。
 * @returns 规范化的执行结果。
 */
function extractBetween(text, pre, post, command, maxOutputBytes) {
  const standalone = (marker, from) => {
    let index = text.indexOf(marker, from)
    while (index !== -1) {
      const after = text[index + marker.length]
      // 注意：after 可能是空串（行尾），空串是 falsy，不能直接用于条件
      if (after === '\n' || after === '' || after === undefined) return index
      index = text.indexOf(marker, index + 1)
    }
    return -1
  }

  const startAt = (() => {
    let found = -1
    let index = standalone(pre, 0)
    while (index !== -1) { found = index; index = standalone(pre, index + 1) }
    return found
  })()

  if (startAt === -1) {
    return { command, output: text.trim(), truncated: false, bytes: Buffer.byteLength(text, 'utf8'), timedOut: true }
  }

  const bodyFrom = startAt + pre.length
  const endAt = standalone(post, bodyFrom)
  const body = stripPromptPrefix(
    (endAt === -1 ? text.slice(bodyFrom) : text.slice(bodyFrom, endAt)).replace(/^\n+/, '').replace(/\n+$/, ''),
  )
  const bytes = Buffer.byteLength(body, 'utf8')
  const truncated = bytes > maxOutputBytes
  return {
    command,
    output: truncated ? `${body.slice(0, maxOutputBytes)}\n\n[输出已截断：共 ${bytes} 字节，仅保留前 ${maxOutputBytes} 字节]` : body,
    truncated,
    bytes,
    timedOut: endAt === -1,
  }
}

/** 去掉输出首尾残留的 shell 提示符（`[user@host ~]$`）与 `cd` 前缀。 */
function stripPromptPrefix(body) {
  return body
    .replace(/^\[[^\]\n]*@[^\]\n]*\][$#]\s?/, '')
    .replace(/^cd\s+\S+\s+2>\/dev\/null;\s*/, '')
    .replace(/\n\[[^\]\n]*@[^\]\n]*\][$#]\s?$/, '')
    .replace(/^\n+/, '')
    .replace(/\n+$/, '')
}

/** 一个持久 SSH 交互式会话；内部把命令串行化，避免哨兵互相污染。 */
export class ClusterSession {
  constructor(spec, options = {}) {
    this.spec = spec
    this.cwd = options.cwd ?? spec.cwd ?? ''
    this.child = undefined
    this.buffer = ''
    this.ready = false
    this.dead = false
    this.counter = 0
    this.tail = Promise.resolve()
    this.waiters = []
    this.rejectStart = undefined
  }

  /** 启动会话并等待提示符；失败时抛出带诊断的异常。 */
  start() {
    if (this.child !== undefined) return Promise.resolve()
    ensureAskpass()
    writeCredentials(this.spec)
    const args = [
      '-tt',
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'UserKnownHostsFile=NUL',
      '-o', 'PreferredAuthentications=keyboard-interactive',
      '-o', 'PubkeyAuthentication=no',
      '-o', 'ConnectTimeout=25',
      '-o', 'ServerAliveInterval=30',
      '-o', 'LogLevel=ERROR',
      '-p', String(this.spec.port),
      `${this.spec.username}@${this.spec.host}`,
    ]
    this.child = spawn(process.env.DSH_SSH_CLIENT ?? 'ssh', args, {
      env: { ...process.env, SSH_ASKPASS: ASKPASS_BAT, SSH_ASKPASS_REQUIRE: 'force', DISPLAY: 'localhost:0' },
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    })
    this.child.stdout.on('data', (chunk) => this.onData(chunk))
    this.child.stderr.on('data', (chunk) => this.onData(chunk))
    this.child.on('error', (error) => this.fail(error))
    this.child.on('close', () => this.fail(new Error('SSH 会话已关闭')))

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`SSH 会话在 ${START_TIMEOUT_MS / 1000}s 内未就绪；最近输出：${JSON.stringify(this.buffer.slice(-300))}`))
      }, START_TIMEOUT_MS)
      this.rejectStart = (error) => { clearTimeout(timer); reject(error) }
      this.waiters.push(() => { clearTimeout(timer); resolve() })
    })
  }

  onData(chunk) {
    this.buffer += chunk.toString('utf8')
    if (!this.ready && READY_PATTERN.test(this.buffer.replace(/\x1b\[[0-9;?]*[a-zA-Z]/g, ''))) {
      // 会话可用后立刻关掉 PTY 回显：否则命令本身会被回显进输出，
      // 而回显与结果挤在同一行，无法可靠切分。
      this.ready = true
      try { this.child.stdin.write('stty -echo\n') } catch (error) { /* 会话可能刚断开 */ }
      setTimeout(() => {
        this.buffer = ''
        const waiters = this.waiters
        this.waiters = []
        for (const waiter of waiters) waiter()
      }, 400)
    }
    if (this.onChunk !== undefined) this.onChunk()
  }

  fail(error) {
    if (this.dead) return
    this.dead = true
    this.ready = false
    if (this.rejectStart !== undefined) this.rejectStart(error)
    if (this.onChunk !== undefined) this.onChunk()
  }

  /**
   * 在会话里执行一条命令：用一对标记把输出夹住，再按标记切出来。
   *
   * 为什么用「标记界定」而不是「按提示符剥离回显」：PTY 会把命令回显与输出挤在同一
   * 个提示符行内（多行输出才会换行），按行判断无法可靠区分两者。把输出包在
   * `MARK_BEGIN … MARK_END` 之间后，回显里虽然也出现这两个串，但只有真正执行的那一份
   * 位于最后一个 MARK_END 之前，倒数定位即可精确取到输出。
   * @param command - bash 命令。
   * @param options - 超时与输出上限。
   * @returns 规范化的执行结果。
   */
  exec(command, { timeoutMs = DEFAULT_TIMEOUT_MS, maxOutputBytes = DEFAULT_MAX_OUTPUT_BYTES, rawOnly = false } = {}) {
    const run = async () => {
      await this.start()
      if (this.dead) throw new Error('SSH 会话不可用')
      const token = `${++this.counter}_${Date.now().toString(36)}`
      const pre = `__DSHP_${token}__`
      const post = `__DSHQ_${token}__`
      const prefixed = this.cwd.length > 0 ? `cd ${this.cwd} 2>/dev/null; ${command}` : command
      // 真实标记各占一整行；PTY 回显里同一行还会带命令余部，故用「标记后紧跟换行/结束」定位
      const payload = `echo ${pre}\n${prefixed}\necho ${post}\n`

      let settled = false
      let release
      const done = new Promise((resolve) => { release = resolve })
      this.onChunk = () => { if (!settled && this.buffer.includes(post)) { settled = true; release() } }
      this.buffer = ''
      this.child.stdin.write(payload)
      const timer = setTimeout(() => { if (!settled) { settled = true; release() } }, timeoutMs)
      await done
      clearTimeout(timer)
      const raw = this.buffer
      this.buffer = ''
      this.onChunk = undefined
      if (rawOnly) return { raw: stripAnsi(raw) }
      return extractBetween(stripAnsi(raw), pre, post, command, maxOutputBytes)
    }
    const chained = this.tail.then(run, run)
    this.tail = chained.then(() => undefined, () => undefined)
    return chained
  }

  dispose() {
    this.dead = true
    this.ready = false
    try { this.child?.stdin.write('exit\n') } catch (error) { /* 会话可能已断开 */ }
    try { this.child?.kill() } catch (error) { /* 已退出 */ }
    this.child = undefined
  }

  /**
   * 调试用：返回未切分的会话原文（已剥离 ANSI），用于校准标记定位。
   * @param command - 要执行的命令。
   * @returns 原文文本。
   */
  async execRaw(command) {
    const result = await this.exec(command, { rawOnly: true })
    return result.raw
  }

  get alive() { return this.dead !== true && this.ready === true }
}

/**
 * 注册集群工具。
 * @param ctx - 挂载上下文；插件只使用 `tools` 注册表。
 */
export function apply(ctx) {
  const sessions = new Map()

  /** 按连接 id 取（或建立）会话。 */
  function sessionFor(connectionId) {
    const connections = readConnections()
    const spec = connectionId === undefined
      ? connections[0]
      : connections.find((item) => item.id === connectionId)
    if (spec === undefined) {
      throw new Error(connections.length === 0
        ? `没有已保存的集群连接：请在 ${join(dshHome(), 'dsh-ssh-connections.json')} 中配置主机、端口、用户名与密码`
        : `找不到连接 "${connectionId}"；可用：${connections.map((c) => c.id).join(', ')}`)
    }
    const key = spec.id ?? `${spec.username}@${spec.host}:${spec.port}`
    let session = sessions.get(key)
    if (session === undefined || session.dead) {
      session = new ClusterSession(spec)
      sessions.set(key, session)
    }
    return { session, spec }
  }

  ctx.tools.register(toToolDefinition({
    name: 'cluster_exec',
    description: 'Run a bash command on the LSF cluster login node over SSH. Reuses one authenticated session, so consecutive calls are fast (~200ms). Use it for bjobs/bqueues/bhosts/module/ls/cat and other short work; submit heavy computation with bsub instead of running it on the login node.',
    parameters: {
      command: { type: 'string', required: true, description: 'Bash command line to run on the cluster login node.' },
      timeoutMs: { type: 'number', description: `Timeout in milliseconds (default ${DEFAULT_TIMEOUT_MS}).` },
      maxOutputBytes: { type: 'number', description: `Cap on returned output bytes (default ${DEFAULT_MAX_OUTPUT_BYTES}); longer output is truncated.` },
      connectionId: { type: 'string', description: 'Saved connection id to use; defaults to the first saved connection.' },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          command: { type: 'string', required: true },
          output: { type: 'string', required: true },
          truncated: { type: 'boolean', required: true },
          bytes: { type: 'number', required: true },
          timedOut: { type: 'boolean', required: true },
          host: { type: 'string', required: true },
        },
      },
      render: (_args, value) => [{ type: 'text', text: value.output.length > 0 ? value.output : '(命令无输出)' }],
    },
    async execute(args) {
      const { session, spec } = sessionFor(args.connectionId)
      const result = await session.exec(args.command, {
        timeoutMs: args.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        maxOutputBytes: args.maxOutputBytes ?? DEFAULT_MAX_OUTPUT_BYTES,
      })
      return { ...result, host: `${spec.username}@${spec.host}` }
    },
  }))

  ctx.tools.register(toToolDefinition({
    name: 'cluster_status',
    description: 'Report the cached cluster SSH session state: saved connections, live sessions, and whether the TOTP secret is present. Use it to diagnose before running cluster commands.',
    parameters: {},
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          connections: { type: 'array', required: true, items: { type: 'string' } },
          liveSessions: { type: 'array', required: true, items: { type: 'string' } },
          totpConfigured: { type: 'boolean', required: true },
          totpFile: { type: 'string', required: true },
          sshClient: { type: 'string', required: true },
        },
      },
      render: (_args, value) => [{
        type: 'text',
        text: [
          `已保存连接: ${value.connections.length === 0 ? '(无)' : value.connections.join('; ')}`,
          `活动会话: ${value.liveSessions.length === 0 ? '(无，首次调用 cluster_exec 时建立)' : value.liveSessions.join(', ')}`,
          `动态口令密钥: ${value.totpConfigured ? '已配置' : `未配置 -> ${value.totpFile}`}`,
          `ssh 客户端: ${value.sshClient}`,
        ].join('\n'),
      }],
    },
    async execute() {
      const connections = readConnections()
      const totpFile = join(dshHome(), 'dsh-ssh-totp.json')
      const ring = readJson(totpFile)
      const first = connections[0]
      const totpConfigured = first !== undefined && ring !== undefined && ring !== null
        && (ring[`${first.username}@${first.host}:${first.port}`] !== undefined || ring[`${first.username}@${first.host}`] !== undefined)
      return {
        connections: connections.map((c) => `${c.id ?? '?'} = ${c.username}@${c.host}:${c.port}`),
        liveSessions: [...sessions.entries()].filter(([, s]) => s.alive).map(([k]) => k),
        totpConfigured: totpConfigured === true,
        totpFile,
        sshClient: process.env.DSH_SSH_CLIENT ?? 'ssh',
      }
    },
  }))

  // 会话随插件 fiber 回收，避免留下悬空的 ssh 子进程
  ctx.effect(() => () => {
    for (const session of sessions.values()) session.dispose()
    sessions.clear()
  }, 'dsh-cluster-ssh session teardown')
}

export const askpassDirectory = ASKPASS_DIR
export const resolveSshClient = () => process.env.DSH_SSH_CLIENT ?? 'ssh'
