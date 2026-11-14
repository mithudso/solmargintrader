import { DatabaseSync } from 'node:sqlite';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { base58Encode } from '../../../extension/src/wallet/solana.js';

export const ORIGIN = 'https://oraclebot.example';
export const at = () => Math.floor(Date.now() / 1000);

export function createD1(sqlite = new DatabaseSync(':memory:')) {
  const batches = [];
  const DB = {
    prepare(sql) {
      let args = [];
      const execute = () => {
        const before = sqlite.prepare('SELECT total_changes() AS n').get().n;
        const statement = sqlite.prepare(sql);
        const results = statement.columns().length ? statement.all(...args) : (statement.run(...args), []);
        return { results, meta: { changes: sqlite.prepare('SELECT total_changes() AS n').get().n - before } };
      };
      return {
        bind(...values) { args = values; return this; },
        async first() { return sqlite.prepare(sql).get(...args) || null; },
        async all() { return { results: sqlite.prepare(sql).all(...args) }; },
        async run() { return execute(); },
        _execute: execute,
      };
    },
    async batch(statements) {
      // Execute synchronously inside the transaction. This matches D1's atomic
      // batch instead of letting concurrent test requests interleave BEGINs.
      sqlite.exec('BEGIN');
      try {
        const result = statements.map(statement => statement._execute());
        sqlite.exec('COMMIT'); batches.push(result); return result;
      } catch (error) { sqlite.exec('ROLLBACK'); throw error; }
    },
  };
  return { DB, sqlite, batches };
}

export function environment({ migrations } = {}) {
  const result = createD1();
  result.sqlite.exec('PRAGMA foreign_keys=ON');
  const directory = new URL('../../migrations/', import.meta.url);
  const names = migrations || readdirSync(directory).filter(name => /^\d{4}_.*\.sql$/.test(name)).sort();
  for (const name of names) {
    const file = new URL(name, directory);
    if (existsSync(file)) result.sqlite.exec(readFileSync(file, 'utf8'));
  }
  return { ...result, APP_ORIGIN: ORIGIN };
}

export function request(path, { method = 'GET', body, form, cookie, origin = ORIGIN, headers = {} } = {}) {
  return new Request(new URL(path, ORIGIN), {
    method,
    headers: {
      ...(method !== 'GET' ? { Origin: origin } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(form === undefined ? {} : { 'Content-Type': 'application/x-www-form-urlencoded' }),
      ...(cookie ? { Cookie: cookie } : {}), ...headers,
    },
    body: form === undefined ? (body === undefined ? undefined : JSON.stringify(body)) : new URLSearchParams(form).toString(),
  });
}

export async function keypair() {
  const keys = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']);
  const wallet = base58Encode(new Uint8Array(await crypto.subtle.exportKey('raw', keys.publicKey)));
  return { keys, wallet };
}

export async function seedUser(env, options = {}) {
  const pair = options.wallet ? { wallet: options.wallet, keys: options.keys } : await keypair();
  const id = options.id || crypto.randomUUID();
  env.sqlite.prepare('INSERT INTO users(id,wallet,created_at) VALUES (?,?,?)').run(id, pair.wallet, at());
  const token = Buffer.from(crypto.getRandomValues(new Uint8Array(32))).toString('base64url');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('hex');
  env.sqlite.prepare('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES (?,?,?)').run(hash, id, at() + 86400);
  return { ...pair, id, user: { id, wallet: pair.wallet }, cookie: `__Host-oraclebot=${token}` };
}
