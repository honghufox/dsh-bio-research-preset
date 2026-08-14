'use strict';
/**
 * dsh-smart-approval — 智能审批（学习式规则）
 *
 * 对齐 Claude Code 权限规则模型，但规则由「人工批准」自动生成：
 *  - 目录规则  ：批准某路径后，该目录（含子目录）后续升级自动放行
 *  - 操作规则  ：无路径的命令（pip/git 等），同一会话内同 (tool, mode) 第二次起自动放行
 *  - 配置规则  ：可在组合配置中预置（持久，跨会话），形态同 Claude Code 的 allow 列表
 *  - 新位置/新操作类型 → 仍要求人工批准一次；被拒绝 → 不学习
 *
 * 挂载点：`approval/request` 瀑布（人工应答器之前）。插件永不抛错（fail-closed）。
 *
 * 配置示例（agent/cordis 组合行 config）：
 *   rules:
 *     dirs:
 *       - 'C:/Users/me/.dsh'
 *     kinds:
 *       - 'pwsh:danger-full-access'
 *   dirLearning: true
 *   kindLearning: true
 */
const path = require('node:path');

module.exports = function smartApproval(ctx, config) {
  const cfg = config || {};
  const dirLearning = cfg.dirLearning !== false;
  const kindLearning = cfg.kindLearning !== false;
  // 预置规则（持久，跨会话，Claude Code allow 列表式）
  const configuredDirs = new Set((cfg.rules && cfg.rules.dirs ? cfg.rules.dirs : []).map(dirKey).filter(Boolean));
  const configuredKinds = new Set((cfg.rules && cfg.rules.kinds ? cfg.rules.kinds : []));

  // 会话级学习状态: sessionId -> { dirs: Set<string>, kinds: Set<string> }
  const state = new Map();

  function stateOf(req) {
    const session = req && req.agent && req.agent.session;
    const id = session ? session.id : 'anonymous';
    let s = state.get(id);
    if (!s) {
      s = { dirs: new Set(), kinds: new Set() };
      state.set(id, s);
    }
    return s;
  }

  /** 规范化路径：去引号、统一分隔符、小写。 */
  function dirKey(p) {
    if (!p) return null;
    let t = String(p).trim().replace(/["']/g, '');
    if (!t) return null;
    try {
      t = path.normalize(t);
    } catch {
      return null;
    }
    while (t.length > 3 && (t.endsWith('\\') || t.endsWith('/'))) {
      t = t.slice(0, -1);
    }
    return t.toLowerCase();
  }

  /** 归一为「目录级」目标：结尾带分隔符视为目录本身，否则视为文件取其父目录。 */
  function targetDir(p) {
    const s = String(p).trim().replace(/["']/g, '');
    if (!s) return null;
    const isDirHint = s.endsWith('\\') || s.endsWith('/');
    if (isDirHint) return dirKey(s);
    return dirKey(path.dirname(s));
  }

  /** 从 reason/justification 提取候选路径（Windows 盘符 / UNC / 正斜杠形式）。 */
  function extractPaths(text) {
    if (!text) return [];
    const re = /(?:[A-Za-z]:[\\/][^\s"'<>|?*]+|\\\\[^\s"'<>|?*]+)/g;
    const out = [];
    let m;
    while ((m = re.exec(text)) !== null) out.push(m[0]);
    return out;
  }

  /** 从 reason 提取升级模式（"escalate sandbox to danger-full-access: ..."）。 */
  function extractMode(reason) {
    if (!reason) return null;
    const m = /escalate sandbox to (\S+?):/.exec(reason);
    return m ? m[1] : null;
  }

  function isUnder(child, parent) {
    if (child === parent) return true;
    if (!parent) return false;
    return child.startsWith(parent + path.sep) || child.startsWith(parent + '/') || child.startsWith(parent + '\\');
  }

  /** 目录是否命中任意已批准（或预置）目录。 */
  function dirAllowed(td, s) {
    for (const d of configuredDirs) if (isUnder(td, d)) return true;
    if (dirLearning) for (const d of s.dirs) if (isUnder(td, d)) return true;
    return false;
  }

  ctx.on('approval/request', async (req, next) => {
    try {
      const reason = req && req.reason ? req.reason : '';
      const mode = extractMode(reason);
      if (!mode) return next(); // 非沙箱升级请求 → 人工

      const s = stateOf(req);
      const paths = extractPaths(reason);

      if (paths.length > 0) {
        // —— 有路径：目录规则 ——
        for (const p of paths) {
          const td = targetDir(p);
          if (td && dirAllowed(td, s)) {
            return 'allowed-once'; // 已批准目录（含子目录）或预置目录 → 自动放行
          }
        }
        // 新目录 → 人工；批准后学习
        const outcome = await next();
        if (outcome === 'allowed-once' && dirLearning) {
          for (const p of paths) {
            const td = targetDir(p);
            if (td) s.dirs.add(td);
          }
        }
        return outcome;
      }

      // —— 无路径：操作类型规则 ——
      const kind = (req.toolName || '?') + ':' + mode;
      if (configuredKinds.has(kind)) return 'allowed-once';
      if (kindLearning) {
        if (s.kinds.has(kind)) return 'allowed-once';
        const outcome = await next();
        if (outcome === 'allowed-once') s.kinds.add(kind);
        return outcome;
      }

      return next();
    } catch (err) {
      return next(); // fail-closed
    }
  });

  ctx.on('session/dispose', (session) => {
    if (session && session.id) state.delete(session.id);
  });
};
