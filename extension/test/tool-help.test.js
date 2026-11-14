import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const run = promisify(execFile);
const root = fileURLToPath(new URL('../tools/', import.meta.url));
const preload = 'globalThis.fetch=async()=>{throw new Error("TEST_NETWORK_REFUSED")};';

test('Node tools expose help and reject unknown arguments before any I/O', async () => {
  const home = await mkdtemp(path.join(os.tmpdir(), 'smt-tool-help-'));
  const env = { ...process.env, HOME: home, SMT_API_TOKEN: '', JUPITER_API_KEY: '',
    NODE_OPTIONS: `--import=data:text/javascript,${encodeURIComponent(preload)}` };
  try {
    for (const tool of ['api-server.js', 'dryrun.js', 'measure-recentre.js', 'verify-endpoints.js']) {
      const result = await run(process.execPath, [path.join(root, tool), '--help'], { cwd: home, env, timeout: 5000 });
      assert.match(result.stdout, /Usage:/, tool);
      assert.match(result.stdout, /Example:/, tool);
      assert.doesNotMatch(result.stdout + result.stderr, /TEST_NETWORK_REFUSED/);
      await assert.rejects(run(process.execPath, [path.join(root, tool), '--unrecognized-audit-flag'], { cwd: home, env, timeout: 5000 }), error => {
        assert.equal(error.code, 2, tool);
        assert.match(error.stderr, /Usage:/, tool);
        assert.doesNotMatch(error.stdout + error.stderr, /TEST_NETWORK_REFUSED/);
        return true;
      });
    }
    await assert.rejects(run(process.execPath, [path.join(root, 'cli.js'), 'setConfig', '--patch', 'AUDIT_CANARY'], { cwd: home, env, timeout: 5000 }), error => {
      assert.doesNotMatch(error.stdout + error.stderr, /AUDIT_CANARY/);
      assert.match(error.stderr, /valid JSON/);
      return true;
    });
  } finally { await rm(home, { recursive: true, force: true }); }
});

test('endpoint verification does not count an upstream 500 as a passing Trigger route', async () => {
  const configURL = new URL('../src/storage/store.js', import.meta.url).href;
  const fixture = `const {DEFAULT_CONFIG:c}=await import(${JSON.stringify(configURL)});globalThis.fetch=async url=>String(url).includes('/price/v3')?new Response(JSON.stringify({[c.baseMint]:{usdPrice:100,decimals:9},[c.quoteMint]:{usdPrice:1,decimals:6}})):new Response('{}',{status:500});`;
  await assert.rejects(run(process.execPath, [path.join(root, 'verify-endpoints.js')], {
    env: { ...process.env, JUPITER_API_KEY: '', NODE_OPTIONS: `--import=data:text/javascript,${encodeURIComponent(fixture)}` }, timeout: 5000,
  }), error => {
    assert.equal(error.code, 1);
    assert.match(error.stdout, /FAIL\s+trigger v2/);
    return true;
  });
});
