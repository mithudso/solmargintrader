import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('trade-status annotation discloses reconciliation effects', () => {
  const source = readFileSync(new URL('../src/mcp.js', import.meta.url), 'utf8');
  const start = source.indexOf('const tools = [');
  const end = source.indexOf('\n];', start);
  assert.ok(start >= 0 && end > start);
  const listed = vm.runInNewContext(`${source.slice(start, end + 3)}\ntools`, { emptySchema: {}, intentSchema: {} });
  const status = listed.find(item => item.name === 'oraclebot_get_trade_status');
  assert.equal(status.annotations.readOnlyHint, false);
  assert.equal(status.annotations.idempotentHint, false);
  assert.equal(status.annotations.openWorldHint, true);
});
