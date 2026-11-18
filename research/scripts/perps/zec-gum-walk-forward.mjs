/** Historical ZEC GUM research. The added week is scored only after the rank file is frozen. */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { PAPER_CAPITAL } from '../../../extension/src/perps/replay.js';
import { fiveMinuteCandidates, fiveMinuteContext, fiveMinuteDecisions } from '../../../extension/tools/lib/zec-gum-five-minute.mjs';
import { prepareGumWindows, runGumWindow, validateCapture } from './lib/zec-gum-replay.mjs';

const { values } = parseArgs({ options: {
  base: { type: 'string' }, week: { type: 'string' }, output: { type: 'string' }, help: { type: 'boolean' },
} });
if (values.help) {
  console.log('node research/scripts/perps/zec-gum-walk-forward.mjs --base FROZEN_42_DAYS --week ADDED_7_DAYS --output NEW_DIR');
  process.exit(0);
}
if (!values.base || !values.week || !values.output) throw new Error('Supply two frozen captures and a new output directory.');

const weekSeconds = 7 * 86400;
const config = {
  sizing: 'notional', amount: 250, leverage: 25, slippageBps: 2, additiveBps: 0, networkUsd: 0.01,
};
const TP = [0, 0.35, 0.5, 0.75, 1, 1.5, 2, 3];
const SL = [0, 0.2, 0.35, 0.5, 0.8, 1.2, 1.6];
const brackets = TP.flatMap(tp => SL.map(sl => ({ tp, sl })));
const hash = value => createHash('sha256').update(value).digest('hex');

async function capture(path) {
  const bytes = await readFile(path);
  const data = JSON.parse(bytes);
  validateCapture(data);
  const { start, end, capturedAt, sources, funding, minutes } = data;
  return { data, receipt: {
    sha256: hash(bytes), start, end, capturedAt, sources, minutes: minutes.length, fundingHours: funding.length,
  } };
}

const [old, recent] = await Promise.all([capture(values.base), capture(values.week)]);
const { start, end, terms } = old.data;
if (end - start !== 6 * weekSeconds || recent.data.start !== end || recent.data.end - end !== weekSeconds) {
  throw new Error('The second capture must append one contiguous week to the original six weeks.');
}
function staticTerms(side) {
  const fields = ['venue', 'max', 'baseBps', 'makerBps', 'liquidationBps', 'maintenanceBps',
    'firstTierCap', 'maxOrder', 'minOrder', 'maxQty', 'stepSize'];
  return fields.map(field => side[field]);
}
for (const side of ['long', 'short']) {
  if (JSON.stringify(staticTerms(terms[side])) !== JSON.stringify(staticTerms(recent.data.terms[side]))) {
    throw new Error('The two market-term snapshots differ. Establish a common fee and margin scenario before scoring.');
  }
}

const windows = Array.from({ length: 7 }, (_, i) => [start + i * weekSeconds, start + (i + 1) * weekSeconds]);
const developmentWeeks = windows.slice(2, 6);
const prepareBase = prepareGumWindows(old.data);
const development = developmentWeeks.map(prepareBase);
const catalog = fiveMinuteCandidates();
const oldContext = fiveMinuteContext(old.data.minutes);
const grid = [];
const fingerprints = new Map();
const includesDev = time => time >= developmentWeeks[0][0] && time < end;
for (const candidate of catalog) {
  const decisions = fiveMinuteDecisions(oldContext, candidate);
  const developmentSignals = [...decisions].filter(([time]) => includesDev(time));
  fingerprints.set(candidate.id, hash(JSON.stringify(developmentSignals)));
  for (const bracket of brackets) {
    const settings = { ...config, ...bracket };
    grid.push({
      candidateId: candidate.id, ...bracket,
      development: development.map(window => runGumWindow(window, candidate, decisions, settings)),
    });
  }
}

function summarize(weeks) {
  const returns = weeks.map(week => week.returnPct);
  return {
    returnPct: returns.reduce((total, value) => total + value, 0),
    worstWeekPct: Math.min(...returns),
    maxDrawdownPct: Math.max(...weeks.map(week => week.drawdownPct)),
    profitableWeeks: returns.filter(value => value > 0).length,
    trades: weeks.reduce((total, week) => total + week.trades, 0),
    liquidations: weeks.reduce((total, week) => total + week.liquidations, 0),
  };
}

const eligible = (weeks, minTrades) => weeks.every(week => week.trades >= 3 && !week.liquidations && !week.refused)
  && weeks.reduce((sum, week) => sum + week.trades, 0) >= minTrades;
function rank(a, b) {
  return b.score.returnPct - a.score.returnPct || b.score.worstWeekPct - a.score.worstWeekPct
    || a.score.maxDrawdownPct - b.score.maxDrawdownPct
    || a.candidateId.localeCompare(b.candidateId) || a.tp - b.tp || a.sl - b.sl;
}
const policy = {
  score: 'Sum of four weekly net returns, each starting from the same $1,000 and fixed $250 target exposure.',
  eligibility: 'At least 24 development exits, at least three per week, no simulated liquidations or refused entries.',
  tiebreaks: 'Higher worst-week return, lower maximum weekly drawdown, then candidate ID, TP and SL.',
  distinct: 'One bracket per rule and per exact development signal stream.',
  walkForward: 'Select the eligible bracket for the same rule using the previous two scored weeks, then run the next week flat from $1,000.',
};
const ranked = grid.filter(row => eligible(row.development, 24))
  .map(row => ({ ...row, score: summarize(row.development) })).sort(rank);
const seen = new Set();
const selected = [];
for (const row of ranked) {
  const fingerprint = fingerprints.get(row.candidateId);
  if (seen.has(fingerprint)) continue;
  selected.push({ ...row, fingerprint });
  seen.add(fingerprint);
  if (selected.length === 3) break;
}
if (selected.length !== 3) throw new Error('Fewer than three strategy signal streams met the development eligibility floor.');

const profiles = selected.map(({ candidateId, tp, sl }, i) =>
  ({ id: 'zec-25x-5m-' + (i + 1), candidateId, tp, sl }));
const live = { version: 1, market: 'ZEC', step: 300, mode: 'paper', settings: config, profiles };
const selection = JSON.stringify({
  version: 1, recordedBase: old.receipt, developmentWeeks, policy, eligibleRows: ranked.length,
  selected: selected.map((row, i) => ({ ...profiles[i], ...row })),
}, null, 2) + '\n';
await mkdir(values.output);
await writeFile(join(values.output, 'selection.json'), selection, { flag: 'wx' });
console.error('Frozen development selection ' + hash(selection));

const minutes = [...old.data.minutes, ...recent.data.minutes];
const funding = [...old.data.funding];
for (const row of recent.data.funding) {
  if (row.timestamp === funding.at(-1).timestamp) {
    if (row.rateBps1h !== funding.at(-1).rateBps1h) throw new Error('Funding at shared boundary changed.');
  } else {
    funding.push(row);
  }
}
const joined = { ...old.data, end: recent.data.end, minutes, funding };
validateCapture(joined);
const makeWindow = prepareGumWindows(joined);
const lastWeek = makeWindow(windows[6]);
const context = fiveMinuteContext(minutes);
const decisionsById = new Map();
const additions = new Map();
for (const candidate of catalog) {
  const decisions = fiveMinuteDecisions(context, candidate);
  const previous = [...decisions].filter(([time]) => includesDev(time));
  if (hash(JSON.stringify(previous)) !== fingerprints.get(candidate.id)) {
    throw new Error('Prefix signals changed when the added week was appended for ' + candidate.id);
  }
  if (selected.some(row => row.candidateId === candidate.id)) decisionsById.set(candidate.id, decisions);
  additions.set(candidate.id, brackets.map(bracket =>
    runGumWindow(lastWeek, candidate, decisions, { ...config, ...bracket })));
}
const results = grid.map((row, i) => ({
  ...row, addedWeek: additions.get(row.candidateId)[i % brackets.length],
}));
const byId = new Map(catalog.map(candidate => [candidate.id, candidate]));
const longHold = window =>
  runGumWindow(window, {}, new Map([[window.bars[0].bar.time, { weight: 1 }]]), { ...config, tp: 0, sl: 0 });
const continuousValidation = makeWindow([windows[2][0], windows[3][1]]);
const continuousTest = makeWindow([windows[4][0], windows[6][1]]);
const walkForward = profiles.map(profile => {
  const { id, candidateId, tp, sl } = profile;
  const candidate = byId.get(candidateId);
  const decisions = decisionsById.get(candidateId);
  const rows = results.filter(row => row.candidateId === candidateId);
  const locked = rows.find(row => row.tp === tp && row.sl === sl);
  const weeks = [...locked.development, locked.addedWeek];
  const folds = weeks.slice(2).map((fixed, i) => {
    const trainingWeeks = windows.slice(i + 2, i + 4);
    const testWeek = windows[i + 4];
    const best = rows.map(row => ({ row, training: row.development.slice(i, i + 2) }))
      .filter(({ training }) => eligible(training, 12))
      .map(({ row, training }) => ({ ...row, score: summarize(training) })).sort(rank)[0];
    return {
      trainingWeeks, testWeek, fixed,
      adaptive: best ? { tp: best.tp, sl: best.sl, training: best.score,
        test: i === 2 ? best.addedWeek : best.development[i + 2] } : null,
    };
  });
  return {
    id, candidateId, tp, sl, weeks, folds, development: summarize(locked.development),
    continuousValidation: runGumWindow(continuousValidation, candidate, decisions, { ...config, tp, sl }),
    continuousTest: runGumWindow(continuousTest, candidate, decisions, { ...config, tp, sl }),
  };
});

const output = {
  version: 1, market: 'ZEC GUM', step: 300, capital: PAPER_CAPITAL, settings: config, terms,
  windows, sources: { base: old.receipt, added: recent.receipt, totalMinutes: minutes.length, fundingHours: funding.length },
  selectionSha256: hash(selection), policy, brackets, catalog, eligibleRows: ranked.length,
  benchmarks: { cash: 0, buyHold: [...development, lastWeek].map(longHold) },
  walkForward, rows: results,
};
const encoded = JSON.stringify(output) + '\n';
await writeFile(join(values.output, 'results.json'), encoded, { flag: 'wx' });
await writeFile(join(values.output, 'live.json'), JSON.stringify(live, null, 2) + '\n', { flag: 'wx' });
console.log(JSON.stringify({ cases: results.length, candidates: catalog.length, eligibleRows: ranked.length,
  selectionSha256: hash(selection), resultsSha256: hash(encoded), profiles }));
