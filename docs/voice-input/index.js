'use strict';
/**
 * dsh-voice-input — Host half (v0.3, HTTP-server architecture)
 *
 * Starts a localhost HTTP server (127.0.0.1:8765, CORS-enabled) exposing the
 * ASR orchestration to the web client via plain fetch — no harness, no Remote
 * decorators. Spawns the sherpa-onnx streaming recognizer (SAPI fallback).
 */
const http = require('node:http');

module.exports = {
  inject: ['subprocess', 'timer'],
  apply(ctx) {
    const MODEL = 'G:/dsh/_tools/asr/sherpa-onnx-streaming-paraformer-bilingual-zh-en';
    const OFFLINE_MODEL = 'G:/dsh/_tools/asr/sherpa-onnx-paraformer-zh-int8-2025-10-07';
    const PY = 'G:/dsh/_tools/asr/stream-recognize.py';
    const PORT = Number(process.env.DSH_VOICE_PORT || 8765);
    let state = null; // { handle, offset, mode, lastText }

    function readOut(handle, offset) {
      const read = handle.collected.stdout.readFrom(offset);
      let last = '';
      let found = false;
      let finalText = '';
      for (const l of read.text.split('\n')) {
        if (l.startsWith('TEXT: ')) {
          last = l.slice(6).trim();
          found = true;
        } else if (l.startsWith('FINAL: ')) {
          finalText = l.slice(7).trim();
        }
      }
      // found=true: the last TEXT line wins (even when empty -> keep previous lastText)
      // found=false: no TEXT lines at all (SAPI mode) -> raw output as-is
      return { nextOffset: read.nextOffset, text: read.text, last: found ? last : read.text.trim(), finalText: finalText };
    }

    function applyRead(st, r) {
      st.offset = r.nextOffset;
      if (r.last) st.lastText = r.last;
      return st.lastText || '';
    }

    async function startSherpa() {
      const exe = await ctx.subprocess.resolveExecutable('python');
      const handle = ctx.subprocess.spawn({
        argv: [exe, PY, MODEL, OFFLINE_MODEL],
        cwd: 'G:/dsh',
        env: { PYTHONIOENCODING: 'utf-8' },
        stdio: { stdin: 'pipe', stdout: { maxBytes: 262144, spill: { maxBytes: 1048576 } }, stderr: { maxBytes: 65536 } },
        graceMs: 5000,
      });
      let exited = null;
      const deadline = Date.now() + 8000;
      while (Date.now() < deadline) {
        const out = handle.collected.stdout.readFrom(0).text;
        if (out.includes('READY')) return { ok: true, handle };
        exited = await Promise.race([handle.done, ctx.timer.timeout(250).then(() => null)]);
        if (exited !== null) break;
      }
      if (exited !== null && exited.exitCode !== 0) {
        const err = handle.collected.stderr.readFrom(0).text.trim();
        return { ok: false, error: err ? err.split('\n').slice(0, 2).join(' | ') : 'recognizer exited (' + exited.exitCode + ')' };
      }
      return { ok: true, handle };
    }

    async function startSapi() {
      const script = [
        '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8',
        'Add-Type -AssemblyName System.Speech',
        '$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine',
        '$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))',
        '$rec.SetInputToDefaultAudioDevice()',
        '$r = $rec.Recognize()',
        'if ($r) { Write-Output $r.Text }',
      ].join('; ');
      const exe = await ctx.subprocess.resolveExecutable('powershell.exe');
      const handle = ctx.subprocess.spawn({
        argv: [exe, '-NoProfile', '-NonInteractive', '-Command', script],
        cwd: 'G:/dsh',
        stdio: { stdin: 'ignore', stdout: { maxBytes: 131072 }, stderr: { maxBytes: 65536 } },
        graceMs: 5000,
      });
      return { ok: true, handle };
    }

    function sendJson(res, code, obj) {
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(obj));
    }

    async function handleStart() {
      if (state) {
        try { state.handle.terminate(); } catch (e) { /* noop */ }
        state = null;
      }
      const s = await startSherpa();
      if (s.ok) {
        state = { handle: s.handle, offset: 0, mode: 'sherpa', lastText: '' };
        return { ok: true, mode: 'sherpa' };
      }
      const sapi = await startSapi();
      state = { handle: sapi.handle, offset: 0, mode: 'sapi', lastText: '' };
      return { ok: true, mode: 'sapi', error: s.error };
    }

    function handlePeek() {
      if (!state) return { ok: false, text: '' };
      return { ok: true, text: applyRead(state, readOut(state.handle, state.offset)) };
    }

    async function handleStop() {
      if (!state) return { ok: false, text: '', error: '没有进行中的录音' };
      const st = state;
      state = null;
      try {
        // signal the recognizer to finalize: it runs the offline model and
        // prints `FINAL: <refined text>` then exits
        if (st.handle.stdin) {
          st.handle.stdin.write('f\n');
        }
      } catch (e) { /* noop */ }
      // wait for the script to finish (FINAL printed, process exits) or timeout
      await Promise.race([st.handle.done, ctx.timer.timeout(15000).then(() => null)]);
      try { st.handle.terminate(); } catch (e) { /* noop */ }
      const r = readOut(st.handle, st.offset);
      st.offset = r.nextOffset;
      if (r.finalText) return { ok: true, text: r.finalText, mode: st.mode, refined: true };
      const text = applyRead(st, r) || st.lastText;
      return { ok: true, text: text, mode: st.mode };
    }

    const server = http.createServer((req, res) => {
      const pathname = decodeURIComponent(new URL(req.url || '/', 'http://x').pathname);
      if (req.method === 'OPTIONS') {
        sendJson(res, 204, {});
        return;
      }
      (async () => {
        if (pathname === '/asr/start' && req.method === 'POST') {
          sendJson(res, 200, await handleStart());
        } else if (pathname === '/asr/peek' && req.method === 'GET') {
          sendJson(res, 200, handlePeek());
        } else if (pathname === '/asr/stop' && req.method === 'POST') {
          sendJson(res, 200, await handleStop());
        } else if (pathname === '/asr/health' && req.method === 'GET') {
          sendJson(res, 200, { ok: true });
        } else {
          sendJson(res, 404, { error: 'not found' });
        }
      })().catch((e) => {
        sendJson(res, 500, { ok: false, error: String(e && e.message ? e.message : e) });
      });
    });

    ctx.effect(() => {
      server.listen(PORT, '127.0.0.1');
      return () => {
        try { server.close(); } catch (e) { /* noop */ }
        if (state) {
          try { state.handle.terminate(); } catch (e) { /* noop */ }
          state = null;
        }
      };
    });
  },
};
