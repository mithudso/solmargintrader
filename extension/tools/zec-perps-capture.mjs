/** Freeze public ZEC GUM candles, funding distributions and market terms for research. */
import { createHash } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import { setTimeout as delay } from 'node:timers/promises';
import { readJson, readMinutes, readSnapshot } from '../src/perps/market.js';

const { values } = parseArgs({ options: {
  start: { type: 'string' }, end: { type: 'string' }, output: { type: 'string' }, help: { type: 'boolean' },
} });
if (values.help) {
  console.log('node extension/tools/zec-perps-capture.mjs --start ISO_UTC --end ISO_UTC --output FILE');
  process.exit(0);
}

const asset = 'ZEC';
const endpoint = 'https://api.gum.ag/app/perps/';
const start = Date.parse(values.start ?? '') / 1000;
const end = Date.parse(values.end ?? '') / 1000;
if (!values.output || ![start, end].every(time => Number.isSafeInteger(time) && time % 600 === 0)
    || end <= start || end > Date.now() / 1000 || end - start > 90 * 86400) {
  throw new Error('Supply two past, ordered UTC ten-minute boundaries up to 90 days apart and an output file.');
}

async function withRetry(read) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await read();
    } catch (error) {
      if (attempt === 2) throw error;
      await delay((attempt + 1) * 1000);
    }
  }
}

const snapshot = await withRetry(() => readSnapshot(asset));
const capturedAt = new Date().toISOString();
const minutes = [];
const pageSeconds = 43200;
for (let from = start; from < end; from += 4 * pageSeconds) {
  const starts = [0, 1, 2, 3].map(page => from + page * pageSeconds).filter(time => time < end);
  const pages = await Promise.all(starts.map(time =>
    withRetry(() => readMinutes(asset, time, Math.min(time + pageSeconds, end)))));
  for (const page of pages) minutes.push(...page);
}
const missingMinutes = (end - start) / 60 - minutes.length;
if (missingMinutes || minutes.some((bar, i) => bar.time !== start + i * 60)) {
  throw new Error('Candle window is discontinuous, with ' + missingMinutes + ' missing minutes.');
}

const funding = [];
const firstHour = Math.ceil(start / 3600) * 3600;
const finalHour = Math.floor(end / 3600) * 3600;
for (let from = firstHour; from <= finalHour; from += 168 * 3600) {
  const to = Math.min(from + 167 * 3600, finalHour);
  const query = new URLSearchParams({ startTime: String(from), endTime: String(to), limit: '500' });
  const data = await withRetry(() => readJson(endpoint + 'fundingRate/' + asset + '/history?' + query));
  if (!Array.isArray(data?.entries) || data.entries.length !== (to - from) / 3600 + 1
      || data.entries.some((row, i) => row.symbol !== asset || !Number.isFinite(row.rateBps1h)
           || row.timestamp !== to - 3600 * i)) {
    throw new Error('Funding distributions are incomplete or malformed starting ' + new Date(from * 1000).toISOString());
  }
  funding.push(...data.entries.toReversed());
}

const frozen = JSON.stringify({
  version: 1, asset, start, end, capturedAt,
  sources: { candles: endpoint + 'ohlcv/' + asset, funding: endpoint + 'fundingRate/' + asset + '/history',
    market: endpoint + 'markets' },
  terms: { long: snapshot.long, short: snapshot.short }, minutes, funding,
}) + '\n';
await writeFile(values.output, frozen, { flag: 'wx' });
console.log(JSON.stringify({ minutes: minutes.length, funding: funding.length,
  sha256: createHash('sha256').update(frozen).digest('hex') }));
