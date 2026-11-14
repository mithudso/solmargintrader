import assert from 'node:assert/strict';
import { base58Encode, bytesToBase64 } from '../../extension/src/wallet/solana.js';

const usage = 'Usage: node website/scripts/smoke.mjs [http(s)://host]\nRequires a running Oraclebot worker. Local: npm --prefix website run dev';
const args = process.argv.slice(2);
if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
  console.log(usage);
  process.exit(0);
}
let target;
try {
  if (args.length > 1) throw new Error();
  target = new URL(args[0] || 'http://localhost:8787');
  if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password) throw new Error();
} catch {
  console.error(usage);
  process.exit(2);
}
const base = target.origin;
const headers = { Origin: base, 'Content-Type': 'application/json' };
async function request(path, init = {}) {
  try {
    return await fetch(`${base}${path}`, { ...init, headers: { ...headers, ...init.headers }, redirect: 'manual', signal: AbortSignal.timeout(15_000) });
  } catch {
    console.error('Oraclebot worker is unavailable or timed out. Start the local worker with: npm --prefix website run dev');
    process.exit(3);
  }
}
const health = await request('/api/health');
assert.equal(health.status, 200);
assert.equal(health.headers.get('x-content-type-options'), 'nosniff');
const capabilities = await health.json();
assert.equal(capabilities.liveExecution, false);
const denied = await request('/api/bots');
assert.equal(denied.status, 401);
const crossSite = await request('/api/auth/challenge', { method: 'POST', headers: { Origin: 'https://untrusted.invalid' }, body: '{}' });
assert.equal(crossSite.status, 403);
const key = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']);
const wallet = base58Encode(new Uint8Array(await crypto.subtle.exportKey('raw', key.publicKey)));
const challengeResponse = await request('/api/auth/challenge', { method: 'POST', body: JSON.stringify({ wallet }) });
assert.equal(challengeResponse.status, 200);
const { id, message } = await challengeResponse.json();
assert.ok(message.includes(base));
const signature = bytesToBase64(new Uint8Array(await crypto.subtle.sign('Ed25519', key.privateKey, new TextEncoder().encode(message))));
const login = await request('/api/auth/verify', { method: 'POST', body: JSON.stringify({ id, signature }) });
assert.equal(login.status, 200);
const cookie = login.headers.get('set-cookie');
assert.ok(cookie.includes('HttpOnly') && cookie.includes('Secure') && cookie.includes('SameSite=Lax'));
const authHeaders = { Cookie: cookie.split(';')[0] };
const me = await request('/api/me', { headers: authHeaders });
assert.equal((await me.json()).user.wallet, wallet);
const replay = await request('/api/auth/verify', { method: 'POST', body: JSON.stringify({ id, signature }) });
assert.equal(replay.status, 401);
const unpaid = await request('/api/bots', { method: 'POST', headers: authHeaders, body: JSON.stringify({ name: 'Smoke test', coin: 'SOL', venue: 'coinbase', strategy: 'ma_crossover', budget: 100, mode: 'paper' }) });
assert.equal(unpaid.status, 402);
const deletion = await request('/api/me', { method: 'DELETE', headers: authHeaders });
assert.equal(deletion.status, 200);
const after = await request('/api/me', { headers: authHeaders });
assert.equal((await after.json()).user, null);
console.log(JSON.stringify({ target: base, checks: 'security headers, anonymous isolation, CSRF, signed-wallet login, session, replay rejection, entitlement denial, account deletion', capabilities }, null, 2));
