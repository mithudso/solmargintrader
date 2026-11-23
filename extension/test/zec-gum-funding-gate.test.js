import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { assessCohort, evaluatePaperEvidence, proposePilotSize } from '../tools/lib/zec-gum-funding-gate.mjs';
import { openProspectiveJournal } from '../tools/lib/zec-gum-prospective.mjs';

const weekSeconds = 7 * 86400;
const monday = Date.parse('2026-11-23T00:00:00Z') / 1000;
const end = monday + 4 * weekSeconds;
const profiles = [
  { id: 'zscore-short', candidateId: 'zscore-12--2.5-0', tp: 2, sl: 1.6 },
  { id: 'volty-short', candidateId: 'volty-10-1.5', tp: 0, sl: 0.8 },
];
const cohortProfiles = [
  ...profiles.map(profile => ({ ...profile, direction: -1, slippageBps: 2 })),
  ...profiles.map(profile => ({ ...profile, id: `${profile.id}-stress`, direction: -1, slippageBps: 6 })),
  { id: 'cash', candidateId: null, direction: 0, tp: 0, sl: 0, slippageBps: 0 },
];

function binding(startedAt = monday, overrides = {}) {
  return { started_at: startedAt, config: JSON.stringify({
    version: 1, mode: 'paper', market: 'ZEC', step: 300, startedAt,
    capitalPerProfileUsd: 1000, stressSlippageBps: 6, sourceSha256: { 'zec-gum-live.mjs': 'a'.repeat(64) }, pollSeconds: 15,
    settings: { sizing: 'notional', amount: 250, leverage: 25, slippageBps: 2, additiveBps: 0, networkUsd: 0.01 },
    profiles: cohortProfiles, ...overrides,
  }) };
}

function observation(time, fields = {}, books = new Map()) {
  const mark = { time, price: 650 };
  return { mark_at: time, observed_at: time, event: JSON.stringify({
    type: 'observation', mode: 'paper', market: 'ZEC', at: time, mark,
    quoteGap: false, fundingGap: false, candleIssue: null, candleThrough: Math.floor(time / 300) * 300,
    terms: { short: { venue: 'GUM', carryBps: 0 } },
    profiles: cohortProfiles.map(profile => ({
      id: profile.id, candidateId: profile.candidateId,
      equity: 1000, realizedPnlUsd: 0, exits: 0, liquidations: 0, refused: 0, position: null, newExits: [],
      ...books.get(profile.id),
    })),
    ...fields,
  }) };
}

function* forwardObservations({ gain = () => 0.2, skip = () => false, gapExposedAt = null,
  cadence = 45, tradeCadence = 54000 } = {}) {
  const books = new Map();
  let last = monday;
  for (let time = monday; time <= end; time += cadence) {
    if (skip(time)) continue;
    const tradeTime = time > monday && (time - monday) % tradeCadence === 0;
    for (const { id } of cohortProfiles.slice(0, -1)) {
      const prior = books.get(id);
      const pnl = tradeTime && gain(id, time);
      const reason = pnl === 'liquidation' ? 'liquidation' : 'signal';
      const change = reason === 'liquidation' ? -10 : pnl || 0;
      const cumulative = (prior?.realizedPnlUsd ?? 0) + change;
      books.set(id, {
        equity: 1000 + cumulative, realizedPnlUsd: cumulative,
        liquidations: (prior?.liquidations ?? 0) + Number(reason === 'liquidation'),
        exits: (prior?.exits ?? 0) + Number(tradeTime),
        position: time === gapExposedAt ? { direction: -1, openedAt: time } : null,
        newExits: tradeTime ? [{ direction: -1, pnl: change, time, openedAt: time - cadence, reason }] : [],
      });
    }
    yield observation(time, { quoteGap: time - last > 45 }, books);
    last = time;
  }
}

test('new or stale forward evidence cannot qualify', () => {
  const early = evaluatePaperEvidence(binding(), [observation(monday)], monday);
  assert.equal(early.status, 'insufficient_evidence');
  assert.equal(early.advisoryOnly, true);
  assert.deepEqual(early.reasons, ['awaiting_four_complete_utc_weeks']);
  const empty = evaluatePaperEvidence(binding(), [], monday);
  assert.ok(empty.reasons.includes('awaiting_first_observation'));
  const stale = evaluatePaperEvidence(binding(), [observation(monday)], end);
  assert.ok(stale.reasons.includes('stale_observations'));
  assert.ok(stale.reasons.includes('incomplete_market_coverage'));
});

test('cohort comparison rejects contamination, ledger mismatch and invalid frozen policy', () => {
  assert.equal(evaluatePaperEvidence(binding(monday + 1), [observation(monday)], monday + 1).status, 'invalid_evidence');
  const falseLedger = new Map([['zscore-short', { equity: 1001, realizedPnlUsd: 1, exits: 1 }]]);
  assert.equal(evaluatePaperEvidence(binding(), [observation(monday, {}, falseLedger)], monday).status, 'invalid_evidence');
  const long = new Map([['volty-short', { position: { direction: 1, openedAt: monday } }]]);
  assert.equal(evaluatePaperEvidence(binding(), [observation(monday, {}, long)], monday).status, 'invalid_evidence');
  assert.equal(evaluatePaperEvidence(binding(monday, { stressSlippageBps: 2 }), [], monday).status, 'invalid_evidence');
  assert.equal(evaluatePaperEvidence(binding(monday, { mode: 'live' }), [], monday).status, 'invalid_evidence');
});

test('four UTC weeks compare each candidate and its stressed book on the same evidence', () => {
  const rows = forwardObservations({ gain: id => id === 'zscore-short-stress' ? -0.1 : 0.2 });
  const result = evaluatePaperEvidence(binding(), rows, end);
  assert.equal(result.status, 'qualified_for_owner_review');
  assert.equal(result.advisoryOnly, true);
  assert.deepEqual(result.weeks.map(week => week.startAt), [0, 1, 2, 3].map(offset => monday + offset * weekSeconds));
  assert.ok(result.weeks.every(week => week.complete && week.coverage === 1));
  const [zscore, volty] = result.candidates;
  assert.equal(zscore.status, 'did_not_qualify');
  assert.deepEqual(zscore.reasons, ['zscore-short-stress:net_return']);
  assert.equal(volty.status, 'qualified_for_owner_review');
  assert.deepEqual(volty.reasons, []);
  assert.ok(volty.baseline.exits >= 40 && volty.stress.exits >= 40);
  assert.equal(volty.stress.positiveWeeks, 4);
});

test('small trade samples, open-exposure gaps and liquidation are explicit evidence limits', () => {
  const sparse = evaluatePaperEvidence(binding(), forwardObservations({ tradeCadence: 300000 }), end);
  assert.equal(sparse.status, 'insufficient_evidence');
  assert.ok(sparse.candidates[0].reasons.includes('zscore-short:too_few_exits'));
  const gap = evaluatePaperEvidence(binding(), forwardObservations({
    skip: time => time === monday + 945, gapExposedAt: monday + 900,
  }), end);
  assert.equal(gap.status, 'insufficient_evidence');
  assert.equal(gap.weeks[0].maxGapSeconds, 90);
  assert.equal(gap.weeks[0].exposureGap, true);
  assert.ok(gap.reasons.includes('incomplete_market_coverage'));
  const liquidation = evaluatePaperEvidence(binding(), forwardObservations({
    gain: (id, time) => id === 'volty-short' && time === monday + 54000 ? 'liquidation' : 0.2,
  }), end);
  assert.equal(liquidation.candidates[1].status, 'did_not_qualify');
  assert.ok(liquidation.candidates[1].reasons.includes('volty-short:liquidation'));
});

test('drawdown uses a running peak over the whole four-week span', () => {
  const result = evaluatePaperEvidence(binding(), forwardObservations({
    gain: (id, time) => {
      if (id !== 'volty-short') return 0.2;
      const weeks = (time - monday) / weekSeconds;
      return weeks < 0.5 ? 6 : weeks < 1.5 ? -4 : 7;
    },
  }), end);
  const { baseline, status, reasons } = result.candidates[1];
  assert.ok(baseline.weekly.every(week => week.maxDrawdownPct < 3));
  assert.ok(baseline.maxDrawdownPct > 3);
  assert.equal(status, 'did_not_qualify');
  assert.ok(reasons.includes('volty-short:drawdown'));
});

test('the real producer journal is read without modifying its rows', async t => {
  try {
    await import('node:sqlite');
  } catch (error) {
    if (error.code !== 'ERR_UNKNOWN_BUILTIN_MODULE') throw error;
    t.skip('The opt-in prospective journal requires Node.js 22.13 or newer.');
    return;
  }
  const directory = await mkdtemp(join(tmpdir(), 'zec-funding-'));
  try {
    const path = join(directory, 'cohort.sqlite3');
    const { sourceSha256 } = JSON.parse(binding().config);
    let clock = monday;
    const journal = await openProspectiveJournal(directory, 15, sourceSha256, { clock: () => clock });
    try {
      const snapshot = async () => ({ mark: { time: clock, price: 650 }, long: { venue: 'GUM', carryBps: 0 },
        short: { venue: 'GUM', carryBps: 0 } });
      const sample = await journal.session.sample(undefined, { clock: () => clock, snapshot,
        candles: async () => { throw new Error('simulated history unavailable'); } });
      assert.equal(sample.candleThrough, null);
      journal.append(sample);
      clock += 310;
      const next = await journal.session.sample(undefined, { clock: () => clock,
        snapshot: async () => ({ ...await snapshot(), mark: { time: monday + 299, price: 650 } }),
        candles: async (_, start, endAt) => Array.from({ length: (endAt - start) / 60 }, (_, index) => ({
          time: start + index * 60, open: 650, high: 651, low: 649, close: 650,
        })) });
      assert.equal(next.candleThrough, monday + 300);
      assert.ok(next.candleThrough > next.mark.time);
      journal.append(next);
    } finally {
      journal.close();
    }
    const before = await readFile(path);
    const result = await assessCohort(directory, clock);
    assert.equal(result.status, 'insufficient_evidence');
    assert.equal(result.observedCount, 2);
    assert.deepEqual(result.reasons, ['awaiting_four_complete_utc_weeks']);
    assert.deepEqual(await readFile(path), before);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

const sizing = {
  riskBudgetUsd: 5, dailyRiskRemainingUsd: 4, availableMarginUsd: 100, maxNotionalUsd: 500,
  markUsd: 100, leverage: 25, stopPct: 0.8, entrySlippageBps: 6, exitSlippageBps: 6,
  stopGapBps: 20, adverseFundingBps: 5, networkUsdPerSide: 0.01,
  market: { venue: 'GUM', max: 50, minOrder: 5, maxOrder: 10000, firstTierCap: 25000, maxQty: 100,
    stepSize: 0.01, baseBps: 3.5, maintenanceBps: 100, liquidationBps: 75 },
};

test('short sizing rounds down and includes gaps, slippage, fees and adverse carry', () => {
  const size = proposePilotSize(sizing);
  assert.equal(size.status, 'sizing_estimate');
  assert.equal(size.advisoryOnly, true);
  assert.equal(size.effectiveBudgetUsd, 4);
  assert.equal(size.units, 3.36);
  assert.ok(size.stressedLossUsd <= 4);
  const entry = 99.94;
  const stopFill = entry * 1.008 * 1.002 * 1.0006;
  const lossPerUnit = stopFill - entry + 0.00035 * (entry + stopFill) + 0.0005 * stopFill;
  assert.ok(Math.abs(size.stressedLossUsd - (lossPerUnit * size.units + 0.02)) < 1e-12);
  assert.ok(lossPerUnit * (size.units + 0.01) + 0.02 > 4);
  const largerGap = proposePilotSize({ ...sizing, stopGapBps: 40 });
  assert.equal(largerGap.status, 'sizing_estimate');
  assert.ok(largerGap.units < size.units);
});

test('sizing fails closed at venue, collateral, liquidation and daily constraints', () => {
  assert.equal(proposePilotSize({ ...sizing, stopPct: 0 }).status, 'invalid_sizing_inputs');
  assert.equal(proposePilotSize({ ...sizing, dailyRiskRemainingUsd: 0 }).status, 'no_size_within_limits');
  assert.equal(proposePilotSize({ ...sizing, availableMarginUsd: 0.1 }).status, 'no_size_within_limits');
  assert.equal(proposePilotSize({ ...sizing, maxNotionalUsd: 4 }).status, 'no_size_within_limits');
  assert.equal(proposePilotSize({ ...sizing, stopGapBps: 600 }).status, 'stressed_stop_at_or_beyond_liquidation');
  const constrained = proposePilotSize({ ...sizing, maxNotionalUsd: 34, market: { ...sizing.market, maxQty: 0.3 } });
  assert.equal(constrained.status, 'sizing_estimate');
  assert.equal(constrained.notionalUsd, 30);
});
