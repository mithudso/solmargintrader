import test from 'node:test';
import assert from 'node:assert/strict';
import { importSource } from './helpers/import-source.js';
const cli = () => importSource('tools/cli.js', { replace: [
  ["import { createNodeDeps } from './deps.js';", 'const createNodeDeps = options => globalThis.__cliFixture.deps(options);'],
  ['import { runCommand,', 'import {'],
], tail: 'main().catch', append: 'const runCommand = input => globalThis.__cliFixture.run(input); export {main, coerce};' });
async function invoke(argv) {
  const calls = { deps: [], run: [] }, saved = process.argv, log = console.log;
  globalThis.__cliFixture = { deps: async o => { calls.deps.push(o); return {}; }, run: async o => { calls.run.push(o); return {}; } };
  try { process.argv = ['node', 'fixture', ...argv]; console.log = () => {}; await (await cli()).main(); return calls; }
  finally { process.argv = saved; console.log = log; delete globalThis.__cliFixture; }
}
test('CDO-025e359146 explicit true keeps CLI persistence disabled', async () => {
  assert.equal((await invoke(['status', '--ephemeral', 'true'])).deps[0].ephemeral, true);
});
test('CDO-67e36f1ec9 bare numeric CLI flags refuse before dependencies', async () => {
  await assert.rejects(invoke(['plan', '--price', '--ephemeral']), /number/);
});
test('CDO-3f0336d073 registry passphrase survives shared global flag parsing', async () => {
  const calls = await invoke(['createSessionKey', '--passphrase', 'synthetic-passphrase', '--ephemeral']);
  assert.equal(calls.run[0].args.passphrase, 'synthetic-passphrase');
});
test('CDO-014ac7de94 measure venue echoes exact stable order identities across ticks', async () => {
  const { recordingVenue } = await importSource('tools/measure-recentre.js', { tail: 'main().then', append: 'export {recordingVenue};' });
  const v = recordingVenue(() => 100), intent = { intentKey: 'i', side: 'buy', level: 90, baseQty: 1, notionalUsd: 90 };
  const placed = await v.placeOrder({ intent });
  const [live] = await v.getOpenOrders();
  assert.equal(live.venueOrderId, placed.venueOrderId);
  assert.equal(live.baseQty, 1);
});
test('CDO-eec409deee measure rejects each malformed observation instead of filtering it', async () => {
  const { main } = await importSource('tools/measure-recentre.js', { replace: [["import { readFileSync } from 'node:fs';", 'const readFileSync = () => globalThis.__csvFixture;']], tail: 'main().then', append: 'export {main};' });
  const saved = process.argv;
  try {
    process.argv = ['node', 'fixture'];
    for (const row of ['Infinity', '', 'junk', '-1']) {
      globalThis.__csvFixture = `close\n100\n${row}\n101`;
      await assert.rejects(main(), /row|price|observation/i, row);
    }
  } finally { process.argv = saved; delete globalThis.__csvFixture; }
});
test('CDO-a50f34bc7b measure refuses an errors-bearing tick', async () => {
  const { run } = await importSource('tools/measure-recentre.js', { replace: [["import { tick } from '../src/core/engine.js';", 'const tick = async () => ({ errors: [{error: "safe-code"}] });']], tail: 'main().then', append: 'export {run};' });
  await assert.rejects(run({ closes: [100, 101], autoRecentre: false }), /tick|bar|failed/i);
});
test('CDO-8d9b566e2a dry-run tick count refuses before scenario effects', async () => {
  const { parseArgs } = await importSource('tools/dryrun.js', { replace: [['const args = parseArgs(process.argv.slice(2));', 'const args = {};']], tail: 'main().catch', append: 'export {parseArgs};' });
  for (const value of ['Infinity', 'NaN', '0', '-1', '1.5', '']) assert.throws(() => parseArgs(['--ticks', value]), /tick|positive|value/i, value);
});
