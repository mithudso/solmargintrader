/** Offline paper replay of the focused ZEC GUM grid. */
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import { planPosition } from '../src/perps/model.js';
import { PAPER_CAPITAL } from '../src/perps/replay.js';
import { RISK_PRESETS } from '../src/perps/strategies.js';
import { buildContext, buildDecisions, candidates } from './lib/zec-perps-signals.mjs';
import { prepareGumWindows, runGumWindow, validateCapture } from './lib/zec-gum-replay.mjs';

const { values } = parseArgs({ options: {
  capture: { type: 'string' }, output: { type: 'string' }, help: { type: 'boolean' },
} });
if (values.help) {
  console.log('node extension/tools/zec-perps-suite.mjs --capture FILE --output FILE');
  process.exit(0);
}
if (!values.capture || !values.output) throw new Error('Supply a frozen capture and an output file.');

const bytes = await readFile(values.capture);
const source = JSON.parse(bytes);
validateCapture(source);
const { start, end, minutes, funding, terms } = source;
const fundingByHour = new Map(funding.map(row => [row.timestamp, row.rateBps1h]));
const third = Math.floor((end - start) / (3 * 600)) * 600;
const windows = {
  warmup: [start, start + third],
  validation: [start + third, start + 2 * third],
  test: [start + 2 * third, end],
};
const prepareWindow = prepareGumWindows(source);
const validation = prepareWindow(windows.validation);
const test = prepareWindow(windows.test);
const brackets = {
  ...RISK_PRESETS,
  narrow: { tp: 0.5, sl: 0.1 },
};
const filters = {
  none: [false, false], shape: [true, false], cadence: [false, true], both: [true, true],
};
const sizes = { notional: 250, collateral: 25 };
const minValidationTrades = 10;
const leverages = [25, 50];

const caseSettings = (sizing, leverage, risk) => ({
  sizing, leverage, amount: sizes[sizing], slippageBps: 2, additiveBps: 0, networkUsd: 0.01, ...brackets[risk],
});

function bufferAtTestOpen(settings, direction) {
  const price = test.bars[0].bar.open;
  const position = planPosition(settings, direction === 1 ? terms.long : terms.short, price, direction);
  return direction * 100 * (1 - position.liquidation / position.entry);
}

const matrix = [];
for (const sizing of Object.keys(sizes)) {
  for (const leverage of leverages) {
    for (const risk of Object.keys(brackets)) {
      const settings = caseSettings(sizing, leverage, risk);
      matrix.push({ sizing, leverage, risk, settings,
        bufferLongPct: bufferAtTestOpen(settings, 1), bufferShortPct: bufferAtTestOpen(settings, -1) });
    }
  }
}

const catalog = [];
const pending = [];
for (const step of [300, 600]) {
  const context = buildContext(minutes, step);
  for (const candidate of candidates(step)) {
    const { id, name, family, params, details, kind, origin } = candidate;
    catalog.push({ id, name, family, params, details, kind, origin, step });
    for (const [filter, [shape, cadence]] of Object.entries(filters)) {
      if ((shape && family === 'shape') || (cadence && family === 'cadence')) continue;
      const decisions = buildDecisions(context, candidate, shape, cadence);
      for (const { settings, ...config } of matrix) {
        pending.push({ candidate, decisions, settings,
          row: { id, family, step, filter, ...config, validation: runGumWindow(validation, candidate, decisions, settings) } });
      }
    }
  }
  console.error('Validation complete for ' + (step / 60) + 'm.');
}

function byValidation(a, b) {
  return b.validation.returnPct - a.validation.returnPct || a.validation.drawdownPct - b.validation.drawdownPct
    || b.validation.trades - a.validation.trades || a.id.localeCompare(b.id) || a.filter.localeCompare(b.filter)
    || a.risk.localeCompare(b.risk);
}
const key = row => [row.step, row.leverage, row.sizing, row.risk, row.filter, row.id].join('/');
const selections = [];
const validationRows = pending.map(entry => entry.row);
for (const step of [300, 600]) {
  for (const leverage of leverages) {
    const eligible = validationRows.filter(row => row.step === step && row.leverage === leverage
      && row.sizing === 'notional' && row.validation.trades >= minValidationTrades && !row.validation.refused)
      .sort(byValidation);
    const families = [...new Set(eligible.map(row => row.family))];
    selections.push({ step, leverage, eligible: eligible.length, overall: eligible[0] ? key(eligible[0]) : null,
      families: Object.fromEntries(families.map(family => [family, key(eligible.find(row => row.family === family))])) });
  }
}
const selectionSha256 = createHash('sha256').update(JSON.stringify(selections)).digest('hex');

const rows = pending.map(({ row, candidate, decisions, settings }) =>
  ({ ...row, key: key(row), test: runGumWindow(test, candidate, decisions, settings) }));
const buyHold = {};
const hold = {};
for (const leverage of leverages) {
  const settings = caseSettings('notional', leverage, 'original');
  buyHold[leverage] = Object.fromEntries(Object.entries({ validation, test }).map(([name, window]) => [
    name, runGumWindow(window, hold, new Map([[window.bars[0].bar.time, { weight: 1 }]]), settings),
  ]));
}

const receipt = {
  version: 1, market: 'ZEC GUM', windows, terms, capital: PAPER_CAPITAL,
  settings: { leverages, sizes, brackets, filters, minValidationTrades, slippageBps: 2, networkUsd: 0.01 },
  capture: { capturedAt: source.capturedAt, sources: source.sources, sha256: createHash('sha256').update(bytes).digest('hex'),
    minutes: minutes.length, zeroRangeMinutes: minutes.filter(bar => bar.low === bar.high).length, fundingHours: funding.length,
    fundingBpsPerHour: { min: Math.min(...fundingByHour.values()), max: Math.max(...fundingByHour.values()) } },
  selectionSha256, selections, buyHold, catalog, rows,
};
const result = JSON.stringify(receipt) + '\n';
await writeFile(values.output, result, { flag: 'wx' });
console.log(JSON.stringify({ cases: rows.length, candidates: catalog.length, selectionSha256,
  sha256: createHash('sha256').update(result).digest('hex') }));
