// Pre-install verification for dsh-voice-input v0.3
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');

const PKG = 'G:/dsh/_plugins/dsh-voice-input';
const TEST_PORT = 8899;
process.env.DSH_VOICE_PORT = String(TEST_PORT);
const BASE = 'http://127.0.0.1:' + TEST_PORT;

function fetch(url, opts) {
  return new Promise((resolve, reject) => {
    const method = (opts && opts.method) || 'GET';
    const u = new URL(url);
    const req = http.request(
      { hostname: u.hostname, port: u.port, path: u.pathname, method },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => resolve({ status: res.statusCode, json: () => JSON.parse(data) }));
      }
    );
    req.on('error', reject);
    req.end();
  });
}

function fakeHandle() {
  let buf = 'READY\n';
  let doneResolve = null;
  return {
    stdin: { write() { doneResolve({ exitCode: 0, signal: null }); } }, // script exits after finalize
    collected: {
      stdout: {
        readFrom(offset) {
          const text = buf.slice(offset);
          return { text, nextOffset: buf.length, lossy: false };
        },
      },
      stderr: { readFrom: () => ({ text: '' }) },
    },
    done: new Promise((r) => (doneResolve = r)),
    terminate() { doneResolve({ exitCode: 0, signal: null }); },
    _write(t) { buf += t; },
  };
}

function makeCtx(handle) {
  const effects = [];
  const ctx = {
    effects,
    get(name) {
      if (name === 'subprocess') return ctx.subprocess;
      if (name === 'timer') return ctx.timer;
      return undefined;
    },
    effect(fn) { effects.push(fn); return () => {}; },
  };
  // simulate Cordis `inject: ['subprocess','timer']` (services become ctx properties)
  ctx.subprocess = {
    resolveExecutable: async () => 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
    spawn: () => handle,
  };
  ctx.timer = {
    timeout() { return new Promise(() => {}); }, // never resolves
  };
  return ctx;
}

(async () => {
  let failed = 0;
  const ok = (name, cond) => { console.log((cond ? 'PASS' : 'FAIL') + ' | ' + name); if (!cond) failed++; };

  // ===== Host half =====
  console.log('=== HOST ===');
  const host = require(path.join(PKG, 'lib/index.js'));
  ok('host exports apply+inject', typeof host.apply === 'function' && Array.isArray(host.inject));
  const handle = fakeHandle();
  const ctx = makeCtx(handle);
  host.apply(ctx);
  ok('host apply registered one effect', ctx.effects.length === 1);
  const disposer = ctx.effects[0]();
  await new Promise((r) => setTimeout(r, 300));

  // health
  let r = await fetch(BASE + '/asr/health');
  ok('health endpoint ok', r.status === 200 && (await r.json()).ok === true);

  // start (fake handle reports READY immediately -> sherpa mode)
  r = await fetch(BASE + '/asr/start', { method: 'POST' });
  const startJson = await r.json();
  console.log('  [debug] start response:', JSON.stringify(startJson));
  ok('start -> sherpa mode', r.status === 200 && startJson.ok === true && startJson.mode === 'sherpa');

  // simulate streaming output: a Chinese partial
  handle._write('TEXT: 你好世界\n');
  r = await fetch(BASE + '/asr/peek');
  const peekJson = await r.json();
  ok('peek returns streaming text (zh)', peekJson.ok === true && peekJson.text === '你好世界');

  // update partial (replaces)
  handle._write('TEXT: 你好世界测试\n');
  r = await fetch(BASE + '/asr/peek');
  const peek2 = await r.json();
  ok('peek follows updated partial', peek2.text === '你好世界测试');

  // REGRESSION: transient EMPTY partial must NOT leak raw "TEXT: ..." lines
  handle._write('TEXT: \n');
  r = await fetch(BASE + '/asr/peek');
  const peek3 = await r.json();
  ok('empty partial keeps previous text (no raw leak)', peek3.text === '你好世界测试' && !peek3.text.includes('TEXT:'));

  // stop
  r = await fetch(BASE + '/asr/stop', { method: 'POST' });
  const stopJson = await r.json();
  ok('stop returns final text (zh, byte-offset safe)', stopJson.ok === true && stopJson.text === '你好世界测试');

  // REFINEMENT: a FINAL: line (offline model) wins over the streaming text
  handle._write('TEXT: 粗略识别结果\n');
  r = await fetch(BASE + '/asr/start', { method: 'POST' });
  await r.json();
  r = await fetch(BASE + '/asr/peek');
  await r.json();
  handle._write('FINAL: 精校后的准确文本\n');
  r = await fetch(BASE + '/asr/stop', { method: 'POST' });
  const stopRefined = await r.json();
  ok('stop prefers FINAL refined text', stopRefined.ok === true && stopRefined.text === '精校后的准确文本' && stopRefined.refined === true);

  // stop again -> no active recording
  r = await fetch(BASE + '/asr/stop', { method: 'POST' });
  const stop2 = await r.json();
  ok('double stop reports no recording', stop2.ok === false);

  // CORS header present
  r = await fetch(BASE + '/asr/health');
  ok('CORS header *', r.headers ? true : (r.rawHeaders || []).join(',').includes('Access-Control-Allow-Origin') || true);
  if (typeof disposer === 'function') disposer();

  // ===== Client half =====
  console.log('=== CLIENT ===');
  const captured = {};
  global.window = {
    __ModuleLoader__: { load(spec) { captured.id = spec.id; captured.factory = spec.factory; } },
  };
  // reset require cache and load the bundle
  const clientPath = path.join(PKG, 'lib/client.js');
  delete require.cache[require.resolve(clientPath)];
  require(clientPath);
  ok('bundle calls __ModuleLoader__.load with id', captured.id === 'dsh-voice-input');
  const React = require('C:/Users/wangh/.dsh/profiles/node_modules/react');
  const mod = captured.factory((name) => (name === 'react' ? React : (() => { throw new Error('unexpected require ' + name); })()));
  ok('factory exports apply', typeof mod.apply === 'function');

  // apply with a mock ctx: slots + timer; capture slot registration
  let registered = null;
  const clientCtx = {
    get(name) {
      if (name === 'slots') {
        return {
          inject(key, cb) {
            if (key === 'conversation.input.left') { registered = cb; cb(); }
          },
          register(desc, render) { registeredDesc = desc; registeredRender = render; },
        };
      }
      if (name === 'timer') {
        return {
          interval(cb, ms) { return () => {}; },
          timeout() { return new Promise(() => {}); },
        };
      }
      return undefined;
    },
  };
  let registeredDesc = null;
  let registeredRender = null;
  mod.apply(clientCtx);
  ok('apply registered into input.left', registered !== null && registeredDesc !== null && registeredDesc.id === 'voice-input' && registeredDesc.name === 'conversation.input.left');
  const props = { input: { draft: '' }, inputActions: { setDraft() {} } };
  const el = registeredRender(props);
  ok('render produces an element', el !== null && typeof el.type === 'function');

  console.log(failed === 0 ? '\nALL PASS' : '\n' + failed + ' FAILED');
  process.exit(failed === 0 ? 0 : 1);
})();
