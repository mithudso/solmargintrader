/** Public-read data acquisition and deterministic paper replay. No wallet or order interface. */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { parseArgs } from 'node:util';
import { readMinutes, readSnapshot } from '../../../extension/src/perps/market.js';
import { MARKETS, planPosition } from '../../../extension/src/perps/model.js';
import { replay } from '../../../extension/src/perps/replay.js';
import { marketPresets, RISK_PRESETS, signalMap } from '../../../extension/src/perps/strategies.js';

const { values } = parseArgs({ options: {
  output: { type: 'string' }, end: { type: 'string' }, days: { type: 'string', default: '7' },
  offline: { type: 'boolean' }, help: { type: 'boolean' },
} });
if (values.help) {
  console.log('node research/scripts/perps/perps-sweep.mjs --output DIR --end ISO_UTC [--days 7] [--offline]');
  process.exit(0);
}
if (!values.output) throw new Error('Supply a separate output path.');
const output = resolve(values.output);
const end = Date.parse(values.end ?? '') / 1000;
const days = Number(values.days);
if (!Number.isSafeInteger(end) || end % 60 || end > Date.now() / 1000 || days < 1 || days > 30 || !Number.isInteger(days)) {
  throw new Error('Supply a past UTC minute and 1–30 days.');
}
const start = end - days * 86400;
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

function longest(rows) {
  let first = 0;
  let bestStart = 0;
  let bestLength = 0;
  for (let i = 0; i <= rows.length; i += 1) {
    if (!i || i < rows.length && rows[i].time === rows[i - 1].time + 60) continue;
    if (i - first > bestLength) {
      bestStart = first;
      bestLength = i - first;
    }
    first = i;
  }
  return rows.slice(bestStart, bestStart + bestLength);
}

await mkdir(output, { recursive: true });
const markets = {};
const results = [];
for (const asset of Object.keys(MARKETS)) {
  const path = join(output, asset + '.json');
  if (!values.offline) {
    const snapshot = await readSnapshot(asset);
    const minutes = [];
    for (let from = start; from < end; from += 43200) {
      minutes.push(...await readMinutes(asset, from, Math.min(end, from + 43200)));
    }
    await writeFile(path, JSON.stringify({ asset, start, end, captureTime: new Date().toISOString(),
      terms: { long: snapshot.long, short: snapshot.short }, minutes }) + '\n', { flag: 'wx' });
  }
  const bytes = await readFile(path);
  const source = JSON.parse(bytes);
  if (source.asset !== asset || source.start !== start || source.end !== end) throw new Error('Frozen input mismatch for ' + asset);
  const minutes = longest(source.minutes);
  const validation = minutes[Math.floor(minutes.length * 0.6)]?.time;
  const test = minutes[Math.floor(minutes.length * 0.8)]?.time;
  const to = minutes.at(-1)?.time + 60;
  if (!validation || !test || !to) throw new Error('Insufficient minutes for ' + asset);
  const { terms } = source;
  markets[asset] = { sourceSha256: hash(bytes), capturedAt: source.captureTime, venue: terms.long.venue,
    capturedMinutes: source.minutes.length, continuousMinutes: minutes.length,
    from: minutes[0].time, validation, test, to, terms };
  const presets = marketPresets(asset);
  for (const preset of presets) {
    const decisions = signalMap(minutes, preset);
    const leverages = [...new Set([1.1, 2, 5, 10, 20, 25, 50, 100, 150, 250, terms.long.max])]
      .filter(leverage => leverage <= terms.long.max);
    for (const size of ['collateral', 'notional']) {
      for (const leverage of leverages) {
        for (const [risk, levels] of Object.entries(RISK_PRESETS)) {
          const settings = { sizing: size, amount: size === 'collateral' ? 25 : 250, leverage,
            slippageBps: 2, additiveBps: 0, networkUsd: 0.01, ...levels };
          let bufferPct = null;
          try {
            const entry = planPosition(settings, terms.long, minutes.find(row => row.time === test).open);
            bufferPct = 100 * (1 - entry.liquidation / entry.entry);
          } catch {
            // Replay records refusals at each attempted entry.
          }
          results.push({ asset, strategy: preset.id, cadenceSeconds: preset.step, size, leverage, risk, bufferPct,
            validation: replay(minutes, preset, settings, terms, validation, test, decisions),
            test: replay(minutes, preset, settings, terms, test, to, decisions) });
        }
      }
    }
  }
}

const summary = { version: 1, start, end, markets, results };
const json = JSON.stringify(summary, null, 2) + '\n';
await writeFile(join(output, 'summary.json'), json);
console.log(JSON.stringify({ markets: Object.keys(markets), cases: results.length, sha256: hash(json) }));
