/** Fixed-vocabulary errors and bounded cryptographic helpers for the private service. */
export class ExecutionError extends Error {
  constructor(code, status = 400) { super(code); this.name = 'ExecutionError'; this.code = code; this.status = status; }
}
export const refuse = (code, status) => { throw new ExecutionError(code, status); };
export const at = () => Math.floor(Date.now() / 1000);
export const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
export const exact = (value, keys) => object(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export const only = (value, keys) => object(value) && Object.keys(value).every(key => keys.includes(key));
export const opaque = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value);
export const uuid = value => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value);
export const json = (value, status = 200) => Response.json(value, { status, headers: { 'Cache-Control': 'no-store' } });
export function base64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}
export function decode64(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value)) refuse('invalid_secret');
  try { return Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - value.length % 4) % 4)), c => c.charCodeAt(0)); }
  catch { refuse('invalid_secret'); }
}
export async function digest(value) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(typeof value === 'string' ? value : JSON.stringify(value))))].map(x => x.toString(16).padStart(2, '0')).join('');
}
export async function boundedJSON(response, limit = 524288) {
  if (Number(response.headers.get('Content-Length')) > limit) refuse('provider_response_invalid', 502);
  const reader = response.body?.getReader();
  if (!reader) refuse('provider_response_invalid', 502);
  const parts = []; let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      length += value.length; if (length > limit) refuse('provider_response_invalid', 502); parts.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const all = new Uint8Array(length); let offset = 0;
  for (const part of parts) { all.set(part, offset); offset += part.length; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(all)); }
  catch { refuse('provider_response_invalid', 502); }
}
export const query = (env, sql, ...args) => {
  if (!env.DB) refuse('storage_unavailable', 503);
  return env.DB.prepare(sql).bind(...args);
};
export function cents(value, zero = false) {
  const s = typeof value === 'number' ? String(value) : value;
  if (typeof s !== 'string' || !/^\d{1,7}(?:\.\d{1,2})?$/.test(s)) refuse('invalid_money');
  const [whole, fraction = ''] = s.split('.'); const result = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(result) || result > 100000000 || (zero ? result < 0 : result <= 0)) refuse('invalid_money');
  return result;
}
