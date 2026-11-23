/** Read-only assessment of the frozen forward paper cohort and a separate sizing estimate. */
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const day = 86400;
const weekSeconds = 7 * day;
const candleStep = 300;
const candleGrace = 60;
const capital = 1000;
const baselineSlippageBps = 2;
const stressSlippageBps = 6;
const settings = { sizing: 'notional', amount: 250, leverage: 25, slippageBps: baselineSlippageBps,
  additiveBps: 0, networkUsd: 0.01 };
const candidates = [
  { id: 'zscore-short', candidateId: 'zscore-12--2.5-0', direction: -1, tp: 2, sl: 1.6 },
  { id: 'volty-short', candidateId: 'volty-10-1.5', direction: -1, tp: 0, sl: 0.8 },
];
const bookedProfiles = [
  ...candidates.map(profile => ({ ...profile, slippageBps: baselineSlippageBps })),
  ...candidates.map(profile => ({ ...profile, id: `${profile.id}-stress`, slippageBps: stressSlippageBps })),
  { id: 'cash', candidateId: null, direction: 0, tp: 0, sl: 0, slippageBps: 0 },
];
const validExitReasons = new Set(['liquidation', 'stop', 'take', 'signal']);
export const QUALIFICATION = Object.freeze({
  weeks: 4, minPositiveWeeks: 3, minExits: 40, minWeeklyExits: 3, maxDrawdownPct: 3,
  minCoverage: 0.95, maxCoveredGapSeconds: 45, maxGapSeconds: 300, maxAgeSeconds: 45,
  baselineSlippageBps, stressSlippageBps,
});
const integer = value => Number.isSafeInteger(value) && value >= 0;
const positive = value => Number.isFinite(value) && value > 0;
const nonnegative = value => Number.isFinite(value) && value >= 0;
const sha256 = value => typeof value === 'string' && /^[a-f0-9]{64}$/u.test(value);
const bps = 10000;
const utcMonday = time => Math.floor((time - 4 * day) / weekSeconds) * weekSeconds + 4 * day;
const sameSettings = (expected, value) => value && Object.entries(expected).every(([key, field]) => value[key] === field);
const failure = (status, reason) => ({ status, advisoryOnly: true, reasons: [reason], candidates: [] });

function cohortConfig(row, now) {
  if (!row || !integer(row.started_at) || row.started_at > now) throw new Error('invalid_cohort_start');
  const config = JSON.parse(row.config);
  if (config?.version !== 1 || config.mode !== 'paper' || config.market !== 'ZEC' || config.step !== candleStep
      || config.startedAt !== row.started_at || config.capitalPerProfileUsd !== capital
      || config.stressSlippageBps !== stressSlippageBps || !sameSettings(settings, config.settings)
      || !positive(config.pollSeconds) || config.pollSeconds > QUALIFICATION.maxCoveredGapSeconds
      || !config.sourceSha256 || typeof config.sourceSha256 !== 'object' || Array.isArray(config.sourceSha256)
      || !Object.keys(config.sourceSha256).length || !Object.values(config.sourceSha256).every(sha256)
      || !Array.isArray(config.profiles) || config.profiles.length !== bookedProfiles.length
      || !bookedProfiles.every(expected => sameSettings(expected, config.profiles.find(p => p?.id === expected.id)))) {
    throw new Error('unexpected_cohort_binding');
  }
  return config;
}

function bookState() {
  return { equity: capital, realized: 0, exits: 0, liquidations: 0, refused: 0, position: null };
}

function paperBook(view, expected, prior, markAt, startedAt) {
  if (view?.candidateId !== expected.candidateId || !nonnegative(view.equity)
      || !Number.isFinite(view.realizedPnlUsd) || !integer(view.exits) || !integer(view.liquidations)
      || !integer(view.refused) || view.refused < prior.refused || !Array.isArray(view.newExits)
      || (view.position !== null && (view.position?.direction !== -1 || expected.direction !== -1
        || !integer(view.position.openedAt) || view.position.openedAt < startedAt || view.position.openedAt > markAt))) {
    throw new Error('invalid_paper_book');
  }
  const next = { ...prior, equity: view.equity, refused: view.refused, position: view.position };
  for (const exit of view.newExits) {
    if (exit?.time !== markAt || !integer(exit.openedAt) || exit.openedAt < startedAt || exit.openedAt > markAt
        || !validExitReasons.has(exit.reason) || exit.direction !== -1 || expected.direction !== -1
        || !Number.isFinite(exit.pnl)) throw new Error('invalid_paper_exit');
    next.realized += exit.pnl;
    next.exits += 1;
    if (exit.reason === 'liquidation') next.liquidations += 1;
  }
  if (next.exits !== view.exits || next.liquidations !== view.liquidations
      || Math.abs(next.realized - view.realizedPnlUsd) > 0.00001
      || (next.position === null && Math.abs(next.equity - (capital + next.realized)) > 0.00001)
      || (expected.id === 'cash' && (next.equity !== capital || next.refused !== 0))) {
    throw new Error('paper_counters_do_not_reconcile');
  }
  return next;
}

function readObservation(row, prior, config, now) {
  const time = row.mark_at;
  const received = row.observed_at;
  const event = JSON.parse(row.event);
  if (!integer(time) || !integer(received) || time < config.startedAt || received < config.startedAt
      || time <= prior.time || received < prior.received || time < received - 20 || time > received + 5
      || received > now || time > now + 5 || event?.type !== 'observation' || event.mode !== 'paper'
      || event.market !== 'ZEC' || event.mark?.time !== time || event.at !== received
      || !positive(event.mark.price) || typeof event.quoteGap !== 'boolean' || typeof event.fundingGap !== 'boolean'
      || (event.candleThrough !== null && (!integer(event.candleThrough)
        || event.candleThrough % config.step || event.candleThrough > received))
      || (event.candleIssue !== null && typeof event.candleIssue !== 'string')
      || event.terms?.short?.venue !== 'GUM' || !Number.isFinite(event.terms.short.carryBps)
      || !Array.isArray(event.profiles) || event.profiles.length !== bookedProfiles.length) {
    throw new Error('invalid_or_nonprospective_observation');
  }
  const books = Object.fromEntries(bookedProfiles.map(profile => [
    profile.id,
    paperBook(event.profiles.find(value => value?.id === profile.id),
      profile, prior.books[profile.id], time, config.startedAt),
  ]));
  const candleReady = event.candleIssue === null && event.candleThrough !== null
    && event.candleThrough >= Math.floor((time - candleGrace) / candleStep) * candleStep;
  return { time, received, books, candleReady, quoteGap: event.quoteGap,
    fundingGap: event.fundingGap === true };
}

function evidenceWindow(startAt, endAt) {
  return { startAt, endAt, covered: 0, largestGap: 0, exposureGap: false, start: null, end: null,
    books: Object.fromEntries(bookedProfiles.map(profile => [profile.id, { peak: null, drawdown: 0 }])) };
}

function windowWeeks(startedAt, now) {
  const first = startedAt === utcMonday(startedAt) ? startedAt : utcMonday(startedAt) + weekSeconds;
  const end = utcMonday(now);
  const lastFour = end - QUALIFICATION.weeks * weekSeconds;
  const weeks = [];
  for (let startAt = Math.max(first, lastFour); startAt < end; startAt += weekSeconds) {
    weeks.push(evidenceWindow(startAt, startAt + weekSeconds));
  }
  return weeks;
}

function recordWeek(week, prior, observed) {
  const { startAt, endAt } = week;
  if (observed.time < startAt || prior.time >= endAt) return;
  const overlap = Math.min(endAt, observed.time) - Math.max(startAt, prior.time);
  const gap = observed.time - prior.time;
  if (overlap > 0) {
    week.largestGap = Math.max(week.largestGap, gap);
    const covered = gap <= QUALIFICATION.maxCoveredGapSeconds && !observed.quoteGap
      && prior.candleReady && observed.candleReady;
    if (covered) week.covered += overlap;
    if (observed.fundingGap || (gap > QUALIFICATION.maxCoveredGapSeconds
      && Object.values(prior.books).some(book => book.position !== null))) week.exposureGap = true;
  }
  if (!week.start && prior.time < startAt && observed.time >= startAt
      && startAt - prior.time <= QUALIFICATION.maxCoveredGapSeconds) {
    week.start = prior.books;
    for (const id of Object.keys(week.books)) week.books[id].peak = prior.books[id].equity;
  }
  if (!week.start || observed.time >= endAt) return;
  week.end = observed;
  for (const [id, book] of Object.entries(week.books)) {
    book.peak = Math.max(book.peak, observed.books[id].equity);
    const drawdown = book.peak > 0 ? 1 - observed.books[id].equity / book.peak : 1;
    book.drawdown = Math.max(book.drawdown, drawdown);
  }
}

function assessments(weeks, span, observations, latest) {
  return candidates.map(({ id }) => {
    const stressId = `${id}-stress`;
    const lanes = Object.fromEntries([id, stressId].map(lane => {
      const weekly = weeks.filter(week => week.start && week.end).map(week => ({
        startAt: week.startAt, netPnlUsd: week.end.books[lane].equity - week.start[lane].equity,
        exits: week.end.books[lane].exits - week.start[lane].exits,
        maxDrawdownPct: 100 * week.books[lane].drawdown,
        refused: week.end.books[lane].refused - week.start[lane].refused,
      }));
      return [lane, { weekly, netPnlUsd: weekly.reduce((sum, week) => sum + week.netPnlUsd, 0),
        exits: weekly.reduce((sum, week) => sum + week.exits, 0), liquidations: latest.books[lane].liquidations,
        positiveWeeks: weekly.filter(week => week.netPnlUsd > 0).length,
        maxDrawdownPct: span ? 100 * span.books[lane].drawdown : 0 }];
    }));
    const reasons = [...observations];
    const coverageReady = reasons.length === 0;
    let sampleReady = coverageReady;
    let measuredFailure = false;
    for (const [lane, result] of Object.entries(lanes)) {
      if (result.liquidations) {
        reasons.push(`${lane}:liquidation`);
        measuredFailure = true;
      }
      if (coverageReady) {
        if (result.exits < QUALIFICATION.minExits
            || result.weekly.some(week => week.exits < QUALIFICATION.minWeeklyExits)) {
          reasons.push(`${lane}:too_few_exits`);
          sampleReady = false;
        }
        if (result.maxDrawdownPct > QUALIFICATION.maxDrawdownPct) {
          reasons.push(`${lane}:drawdown`);
          measuredFailure = true;
        }
        if (result.weekly.some(week => week.refused > 0)) {
          reasons.push(`${lane}:entry_refusals`);
          measuredFailure = true;
        }
      }
    }
    if (sampleReady) {
      for (const [lane, result] of Object.entries(lanes)) {
        if (result.netPnlUsd <= 0 || result.positiveWeeks < QUALIFICATION.minPositiveWeeks) {
          reasons.push(`${lane}:net_return`);
          measuredFailure = true;
        }
      }
    }
    const status = measuredFailure ? 'did_not_qualify'
      : sampleReady ? 'qualified_for_owner_review' : 'insufficient_evidence';
    return { id, status, reasons, baseline: lanes[id], stress: lanes[stressId] };
  });
}

/** The caller supplies chronological rows from one snapshot. This never authorizes a trade. */
export function evaluatePaperEvidence(row, observations, now = Math.floor(Date.now() / 1000)) {
  try {
    if (!integer(now)) throw new Error('invalid_assessment_time');
    const config = cohortConfig(row, now);
    const weeks = windowWeeks(config.startedAt, now);
    const span = weeks.length ? evidenceWindow(weeks[0].startAt, weeks.at(-1).endAt) : null;
    let latest = { time: config.startedAt - 1, received: config.startedAt, candleReady: true,
      books: Object.fromEntries(bookedProfiles.map(profile => [profile.id, bookState()])) };
    let observedCount = 0;
    for (const observation of observations) {
      const next = readObservation(observation, latest, config, now);
      for (const week of weeks) recordWeek(week, latest, next);
      if (span) recordWeek(span, latest, next);
      latest = next;
      observedCount += 1;
    }
    const evidence = weeks.map(week => ({
      startAt: week.startAt, endAt: week.endAt, coverage: week.covered / weekSeconds, maxGapSeconds: week.largestGap,
      complete: Boolean(week.start && week.end && week.endAt - week.end.time <= QUALIFICATION.maxCoveredGapSeconds),
      exposureGap: week.exposureGap,
    }));
    const reasons = [];
    if (!observedCount) reasons.push('awaiting_first_observation');
    else if (now - latest.received > QUALIFICATION.maxAgeSeconds || now - latest.time > QUALIFICATION.maxAgeSeconds) {
      reasons.push('stale_observations');
    }
    if (weeks.length < QUALIFICATION.weeks) reasons.push('awaiting_four_complete_utc_weeks');
    if (evidence.some(week => !week.complete || week.coverage < QUALIFICATION.minCoverage
      || week.maxGapSeconds > QUALIFICATION.maxGapSeconds || week.exposureGap)) reasons.push('incomplete_market_coverage');
    const results = assessments(weeks, span, reasons, latest);
    const status = results.some(result => result.status === 'qualified_for_owner_review') ? 'qualified_for_owner_review'
      : results.some(result => result.status === 'did_not_qualify') ? 'did_not_qualify' : 'insufficient_evidence';
    return { status, advisoryOnly: true, rules: QUALIFICATION, market: 'ZEC', mode: 'paper', asOf: now,
      startedAt: config.startedAt, sourceSha256: config.sourceSha256, observedCount,
      lastMarkAt: observedCount ? latest.time : null, weeks: evidence, reasons, candidates: results };
  } catch (error) {
    return failure('invalid_evidence', error instanceof SyntaxError ? 'invalid_cohort_json' : 'cohort_integrity_check_failed');
  }
}

export async function assessCohort(directory, now) {
  const { DatabaseSync } = await import('node:sqlite');
  const db = new DatabaseSync(resolve(directory, 'cohort.sqlite3'), { readOnly: true });
  try {
    db.exec('PRAGMA query_only = ON; PRAGMA busy_timeout = 2000; BEGIN;');
    const row = db.prepare('SELECT started_at, config FROM cohort WHERE id = 1').get();
    return evaluatePaperEvidence(row,
      db.prepare('SELECT mark_at, observed_at, event FROM observations ORDER BY mark_at').iterate(),
      now ?? Math.floor(Date.now() / 1000));
  } finally {
    db.close();
  }
}

/**
 * Estimate the maximum short size that fits an explicit dollar loss budget and venue terms.
 * Stop gaps beyond the supplied stress distance can produce larger losses.
 */
export function proposePilotSize(input) {
  const { riskBudgetUsd, dailyRiskRemainingUsd, availableMarginUsd, maxNotionalUsd, markUsd, leverage, stopPct,
    entrySlippageBps, exitSlippageBps, stopGapBps, adverseFundingBps, networkUsdPerSide, market } = input ?? {};
  if (![riskBudgetUsd, maxNotionalUsd, markUsd, leverage, stopPct].every(positive)
      || ![dailyRiskRemainingUsd, availableMarginUsd, entrySlippageBps, exitSlippageBps,
        stopGapBps, adverseFundingBps, networkUsdPerSide].every(nonnegative)
      || entrySlippageBps >= bps || exitSlippageBps >= bps || stopGapBps >= bps || adverseFundingBps >= bps
      || stopPct >= 100 || market?.venue !== 'GUM' || leverage < 1.1 || leverage > market.max
      || ![market.max, market.minOrder, market.maxOrder, market.firstTierCap, market.maxQty, market.stepSize].every(positive)
      || ![market.baseBps, market.maintenanceBps, market.liquidationBps].every(nonnegative)) {
    return { status: 'invalid_sizing_inputs', advisoryOnly: true };
  }
  const effectiveBudgetUsd = Math.min(riskBudgetUsd, dailyRiskRemainingUsd);
  const entry = markUsd * (1 - entrySlippageBps / bps);
  const exitMark = entry * (1 + stopPct / 100) * (1 + stopGapBps / bps);
  const exitFill = exitMark * (1 + exitSlippageBps / bps);
  const fees = market.baseBps / bps;
  const fundingPerUnit = exitFill * adverseFundingBps / bps;
  const variableLoss = exitFill - entry + fees * (entry + exitFill) + fundingPerUnit;
  const reserveRate = (market.maintenanceBps + market.baseBps + market.liquidationBps) / bps;
  const marginPerUnit = entry * (1 / leverage + fees);
  const modelLiqWithoutFixedCosts = (entry + entry * (1 / leverage - fees)) / (1 + reserveRate);
  const maxUnits = Math.min(
    (effectiveBudgetUsd - 2 * networkUsdPerSide) / variableLoss,
    (availableMarginUsd - networkUsdPerSide) / marginPerUnit,
    maxNotionalUsd / markUsd,
    market.maxQty,
    market.maxOrder / Math.max(markUsd, exitFill),
    market.firstTierCap * (1 - 1e-12) / Math.max(markUsd, exitFill, modelLiqWithoutFixedCosts),
  );
  const units = Math.floor(maxUnits / market.stepSize) * market.stepSize;
  const notionalUsd = units * markUsd;
  const stressedLossUsd = units * variableLoss + 2 * networkUsdPerSide;
  const marginWithEntryCostsUsd = units * marginPerUnit + networkUsdPerSide;
  if (![units, notionalUsd, stressedLossUsd, marginWithEntryCostsUsd].every(positive)
      || units * entry < market.minOrder || stressedLossUsd > effectiveBudgetUsd
      || marginWithEntryCostsUsd > availableMarginUsd || notionalUsd > maxNotionalUsd
      || units * Math.max(markUsd, exitFill) > market.maxOrder || units > market.maxQty) {
    return { status: 'no_size_within_limits', advisoryOnly: true };
  }
  const liquidationMark = modelLiqWithoutFixedCosts - (networkUsdPerSide / units + fundingPerUnit) / (1 + reserveRate);
  if (liquidationMark <= Math.max(markUsd, exitFill)) {
    return { status: 'stressed_stop_at_or_beyond_liquidation', advisoryOnly: true };
  }
  return { status: 'sizing_estimate', advisoryOnly: true, units, notionalUsd, stressedLossUsd,
    marginWithEntryCostsUsd, effectiveBudgetUsd, stressedStopFillUsd: exitFill, liquidationMarkUsd: liquidationMark };
}

async function main() {
  const { values } = parseArgs({ options: { cohort: { type: 'string' }, size: { type: 'string' }, help: { type: 'boolean' } } });
  if (values.help) {
    console.log('node extension/tools/lib/zec-gum-funding-gate.mjs --cohort COHORT_DIR | --size SIZING_JSON');
    return;
  }
  if (Boolean(values.cohort) === Boolean(values.size)) throw new Error('Supply --cohort COHORT_DIR or --size SIZING_JSON.');
  const result = values.cohort ? await assessCohort(values.cohort)
    : proposePilotSize(JSON.parse(await readFile(values.size, 'utf8')));
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    process.exitCode = 1;
    console.error(error.message);
  });
}
