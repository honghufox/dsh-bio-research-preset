'use strict';
/**
 * TOTP（RFC 6238 / Google Authenticator：HMAC-SHA1、30s 周期、6 位）实现。
 *
 * 集群登录走 keyboard-interactive 的「密码 + 动态口令」，系统 ssh 通过
 * SSH_ASKPASS 取这两项，所以这里按需现算动态口令。
 * 密钥来自 <DSH_HOME>/dsh-ssh-totp.json，键为 "user@host:port"；
 * 该文件只存本机，绝不进任何仓库。
 */
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const BASE32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

function base32Decode(input) {
  const clean = String(input).toUpperCase().replace(/[^A-Z2-7]/g, '');
  let bits = 0;
  let value = 0;
  const out = [];
  for (const ch of clean) {
    value = (value << 5) | BASE32.indexOf(ch);
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

function totp(secretBase32, atMs) {
  const key = base32Decode(secretBase32);
  const counter = Math.floor((atMs === undefined ? Date.now() : atMs) / 1000 / 30);
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(counter));
  const h = crypto.createHmac('sha1', key).update(buf).digest();
  const offset = h[h.length - 1] & 0x0f;
  const bin = ((h[offset] & 0x7f) << 24) | ((h[offset + 1] & 0xff) << 16) | ((h[offset + 2] & 0xff) << 8) | (h[offset + 3] & 0xff);
  return String(bin % 1000000).padStart(6, '0');
}

function dshHome() {
  return process.env.DSH_HOME || path.join(os.homedir(), '.dsh');
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) { return undefined; }
}

/** 读取已保存的 SSH 连接（dsh-ssh 的连接注册表文件）。 */
function readConnections() {
  const state = readJson(path.join(dshHome(), 'dsh-ssh-connections.json'));
  return (state && Array.isArray(state.connections)) ? state.connections : [];
}

/** 按 user@host:port 取动态口令；无密钥时返回 null（调用方应提示用户）。 */
function totpForEndpoint(username, host, port) {
  const ring = readJson(path.join(dshHome(), 'dsh-ssh-totp.json'));
  if (ring === undefined || ring === null) return null;
  const secret = ring[`${username}@${host}:${port}`] || ring[`${username}@${host}`];
  if (secret === undefined) return null;
  try { return totp(secret); } catch (error) { return null; }
}

module.exports = { totp, totpForEndpoint, readConnections, readJson, dshHome };
