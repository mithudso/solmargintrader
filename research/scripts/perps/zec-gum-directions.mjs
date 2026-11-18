/** Re-run the frozen ZEC Volty profiles with matched long-only, short-only and two-sided entries. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import { gunzipSync } from 'node:zlib';
import { fiveMinuteCandidates, fiveMinuteContext, fiveMinuteDecisions } from '../../../extension/tools/lib/zec-gum-five-minute.mjs';
import { prepareGumWindows, runGumDirectionalWindow, validateCapture } from './lib/zec-gum-replay.mjs';

const data = new URL('../../json/results/', import.meta.url);
const selection = new URL('zec_gum_25x_5m_selection.json', data);
const replay = new URL('zec_gum_25x_5m_walk_forward.json.gz', data);
const archiveHash = 'fa2324e78f547b7bec0848d8c29f6bd1bcb38fa516e40221698c7bf725e45496';
const directions = { both: 0, long: 1, short: -1 };
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

async function validatedCapture(path, source) {
  const bytes = await readFile(path);
  assert.equal(hash(bytes), source.sha256, 'Capture hash differs from the published replay.');
  const capture = JSON.parse(bytes);
  validateCapture(capture);
  assert.equal(capture.start, source.start);
  assert.equal(capture.end, source.end);
  return capture;
}

function compareWithPublished(actual, expected, profile, window) {
  const metrics = Object.keys(expected);
  assert.deepEqual(Object.keys(actual).filter(key => key !== 'sides'), metrics);
  for (const metric of metrics) {
    const context = `${profile} ${window}: ${metric}`;
    if (Number.isInteger(expected[metric])) assert.equal(actual[metric], expected[metric], context);
    else assert.ok(Math.abs(actual[metric] - expected[metric]) <= 1e-10, context);
  }
}

async function main() {
  const { values } = parseArgs({
    options: { base: { type: 'string' }, week: { type: 'string' }, output: { type: 'string' }, help: { type: 'boolean' } },
  });
  if (values.help) {
    console.log('node research/scripts/perps/zec-gum-directions.mjs --base FROZEN_42_DAYS --week ADDED_7_DAYS --output NEW_JSON');
    return;
  }
  if (!values.base || !values.week || !values.output) throw new Error('Supply both frozen captures and a new output file.');
  const [selectionBytes, archiveBytes] = await Promise.all([readFile(selection), readFile(replay)]);
  const archiveBody = gunzipSync(archiveBytes);
  assert.equal(hash(archiveBody), archiveHash, 'Unexpected published replay.');
  const prior = JSON.parse(archiveBody);
  assert.equal(hash(selectionBytes), prior.selectionSha256, 'Unexpected frozen profile selection.');
  const { selected } = JSON.parse(selectionBytes);
  const [base, week] = await Promise.all([
    validatedCapture(values.base, prior.sources.base),
    validatedCapture(values.week, prior.sources.added),
  ]);
  assert.equal(base.end, week.start);
  const funding = [...base.funding];
  for (const row of week.funding) {
    if (row.timestamp === funding.at(-1).timestamp) {
      assert.deepEqual(row, funding.at(-1), 'Shared funding changed.');
    } else {
      funding.push(row);
    }
  }
  const joined = { ...base, end: week.end, minutes: [...base.minutes, ...week.minutes], funding };
  validateCapture(joined);
  const context = fiveMinuteContext(joined.minutes);
  const baseContext = fiveMinuteContext(base.minutes);
  const window = prepareGumWindows(joined);
  const ranges = { addedWeek: [week.start, week.end], continuousTest: [prior.windows[4][0], week.end] };
  const windows = Object.fromEntries(Object.entries(ranges).map(([name, range]) => [name, window(range)]));
  const catalog = new Map(fiveMinuteCandidates().map(rule => [rule.id, rule]));
  const profiles = selected.map(({ id, candidateId, tp, sl }) => {
    const previous = prior.walkForward.find(row => row.id === id);
    assert.deepEqual([candidateId, tp, sl], [previous.candidateId, previous.tp, previous.sl]);
    const candidate = catalog.get(candidateId);
    assert.equal(candidate?.kind, 'volty', 'Direction comparison requires a two-sided Volty signal.');
    const decisions = fiveMinuteDecisions(context, candidate);
    const prefix = fiveMinuteDecisions(baseContext, candidate);
    for (const [time, decision] of prefix) {
      if (time < base.end) assert.deepEqual(decisions.get(time), decision);
    }
    const settings = { ...prior.settings, tp, sl };
    const variants = {};
    for (const [variant, direction] of Object.entries(directions)) {
      variants[variant] = Object.fromEntries(Object.entries(windows).map(([name, bars]) => [
        name, runGumDirectionalWindow(bars, candidate, decisions, settings, direction),
      ]));
    }
    compareWithPublished(variants.both.addedWeek, previous.weeks.at(-1), id, 'added week');
    compareWithPublished(variants.both.continuousTest, previous.continuousTest, id, 'continuous test');
    return { id, candidateId, tp, sl, variants };
  });
  const report = {
    version: 1, mode: 'offline-replay', market: prior.market, step: prior.step, capital: prior.capital,
    settings: prior.settings, ranges, sourceHashes: {
      base: prior.sources.base.sha256, added: prior.sources.added.sha256,
      selection: prior.selectionSha256, decompressedPublishedResults: archiveHash,
    },
    checks: { publishedParity: 'passed', prefixCausality: 'passed' },
    entryPolicy: 'One net position. Reject only disallowed new entries, keeping both signal directions for exits.',
    profiles,
  };
  const body = JSON.stringify(report, null, 2) + '\n';
  await writeFile(values.output, body, { flag: 'wx' });
  console.log(JSON.stringify({ output: values.output, sha256: hash(body), profiles: profiles.length, ...report.checks }));
}

await main();
