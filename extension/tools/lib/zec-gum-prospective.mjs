/** Forward-only ZEC/GUM comparison. All execution uses independent virtual accounts. */
import { mkdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { readMinutes, readSnapshot } from '../../src/perps/market.js';
import { barrier } from '../../src/perps/model.js';
import { PAPER_CAPITAL, PaperBroker } from '../../src/perps/replay.js';
import { aggregateMinutes } from '../../src/perps/strategies.js';
import { fiveMinuteCandidates, fiveMinuteContext, fiveMinuteDecisions } from './zec-gum-five-minute.mjs';

const market = 'ZEC';
const step = 300;
const minute = 60;
const warmup = 720 * minute;
const markGapLimit = 45;
const decisionGrace = 60;
const clockSeconds = () => Math.floor(Date.now() / 1000);
const boundaryAt = time => Math.floor(time / step) * step;
export const paperSettings = Object.freeze({
  sizing: 'notional', amount: 250, leverage: 25, slippageBps: 2, additiveBps: 0, networkUsd: 0.01,
});
const stressSlippageBps = 6;
const catalog = new Map(fiveMinuteCandidates().map(candidate => [candidate.id, candidate]));
const zscore = catalog.get('zscore-12--2.5-0');
const volty = catalog.get('volty-10-1.5');

function bookProfile(id, candidate, tp, sl, slippageBps) {
  return Object.freeze({ id, candidateId: candidate.id, direction: -1, tp, sl, slippageBps });
}

export const prospectiveProfiles = Object.freeze([
  bookProfile('zscore-short', zscore, 2, 1.6, paperSettings.slippageBps),
  bookProfile('volty-short', volty, 0, 0.8, paperSettings.slippageBps),
  bookProfile('zscore-short-stress', zscore, 2, 1.6, stressSlippageBps),
  bookProfile('volty-short-stress', volty, 0, 0.8, stressSlippageBps),
  Object.freeze({ id: 'cash', candidateId: null, direction: 0, tp: 0, sl: 0, slippageBps: 0 }),
]);

export function prospectiveConfig(startedAt, pollSeconds, sourceSha256) {
  return {
    version: 1, mode: 'paper', market, step, startedAt, pollSeconds, sourceSha256,
    capitalPerProfileUsd: PAPER_CAPITAL, settings: paperSettings, stressSlippageBps, profiles: prospectiveProfiles,
  };
}

function settingsFor({ tp, sl, slippageBps }) {
  return { ...paperSettings, tp, sl, slippageBps };
}

// Match the historical reflected Z-score and carry its state across the retained candle window.
export function shortZScoreState(bars, { after = null, weight = 0 } = {}) {
  const { window, entry_z, exit_z } = zscore.params;
  const canResume = after !== null && bars[window]?.time < after && after <= bars.at(-1).time + step;
  if (!canResume) weight = 0;
  for (let i = window; i < bars.length; i += 1) {
    if (canResume && bars[i].time + step <= after) continue;
    const closes = bars.slice(i - window + 1, i + 1).map(bar => -bar.close);
    const mean = closes.reduce((sum, close) => sum + close, 0) / window;
    const squares = closes.reduce((sum, close) => sum + (close - mean) ** 2, 0);
    const z = squares > 0 ? (closes.at(-1) - mean) / Math.sqrt(squares / (window - 1)) : 0;
    if (weight === 0 && z <= entry_z) weight = 1;
    else if (weight === 1 && z >= exit_z) weight = 0;
  }
  return { weight };
}

function createBooks(saved) {
  const profiles = prospectiveProfiles.filter(profile => profile.direction === -1);
  if (saved && (!Array.isArray(saved) || saved.length !== profiles.length)) {
    throw new Error('The paper comparison checkpoint is incomplete.');
  }
  return profiles.map((profile, i) => {
    const settings = settingsFor(profile);
    const state = saved?.[i];
    if (!saved) return { profile, broker: new PaperBroker(settings, { entryDirection: -1 }), exits: 0, liquidations: 0 };
    if (!state) throw new Error('The paper comparison checkpoint is missing an account.');
    const broker = PaperBroker.fromCheckpoint(state.broker);
    if (state.id !== profile.id || broker.entryDirection !== -1 || broker.position?.direction === 1
        || JSON.stringify(broker.settings) !== JSON.stringify(settings)
        || ![state.exits, state.liquidations].every(count => Number.isSafeInteger(count) && count >= 0)
        || state.liquidations > state.exits) {
      throw new Error('The paper account checkpoint does not match its frozen profile.');
    }
    return { profile, broker, exits: state.exits, liquidations: state.liquidations };
  });
}

function accountObservation(book, mark, terms, action, decisionTime, decision) {
  const { broker, profile } = book;
  const breakoutBook = profile.candidateId === volty.id;
  let executable;
  if (action === 'apply') executable = decision;
  else if (breakoutBook && action !== 'observe') executable = null;
  else if (!breakoutBook && action === 'resync') {
    // Preserve protection and allow a current mean-reversion exit. Skip newly seen stale entries.
    broker.lastWeight = decision?.weight ?? broker.lastWeight;
    if (broker.position && decision?.weight === 0) executable = decision;
  }
  const { time, price } = mark;
  const point = { time, open: price, high: price, low: price, close: price };
  const previousWeight = broker.lastWeight;
  const wasFlat = !broker.position;
  broker.observe(point, { ...terms, decisionKind: breakoutBook ? 'volty' : 'signal', decision: executable });
  if (!breakoutBook && wasFlat && executable?.weight > previousWeight) {
    // PaperBroker's weight entry is long-only; keep its close/cost path and admit the mirrored short edge.
    broker.open(time, price, -1, terms.short, executable.weight);
    if (broker.position) {
      const exit = barrier(broker.position, point, 0);
      if (exit) broker.close(time, exit);
    }
  }
  const view = broker.view(price);
  book.exits += view.exits;
  book.liquidations += view.liquidations;
  const newExits = broker.ledger;
  broker.ledger = [];
  const position = view.position && {
    openedAt: view.position.openedAt, direction: view.position.direction, entry: view.position.entry,
    sizeUsd: view.position.size, take: view.position.take, stop: view.position.stop,
    liquidation: view.position.liquidation, carryUsd: view.position.carry,
  };
  return {
    id: profile.id, candidateId: profile.candidateId,
    decision: { status: action, boundary: decisionTime, value: decision ?? null },
    equity: view.equity, realizedPnlUsd: view.realized, drawdown: view.drawdown, position,
    exits: book.exits, liquidations: book.liquidations, refused: broker.refused, newExits,
  };
}

function cashObservation() {
  return {
    id: 'cash', candidateId: null, decision: null, equity: PAPER_CAPITAL, realizedPnlUsd: 0,
    drawdown: 0, position: null, exits: 0, liquidations: 0, refused: 0, newExits: [],
  };
}

export class ProspectiveSession {
  constructor(startedAt, saved = null) {
    this.startedAt = startedAt;
    this.books = createBooks(saved?.books);
    this.minutes = [];
    this.historyEnd = null;
    this.markTime = saved?.markTime ?? null;
    this.receivedAt = saved?.receivedAt ?? null;
    this.boundary = saved?.boundary ?? null;
    this.blockEntryThrough = saved?.blockEntryThrough ?? null;
    this.zWeight = saved?.zWeight ?? 0;
    this.resuming = saved !== null;
    if (saved && (saved.version !== 1 || !saved.books
        || !Number.isSafeInteger(this.markTime) || !Number.isSafeInteger(this.receivedAt)
        || this.markTime < startedAt || this.receivedAt < startedAt
        || ![this.boundary, this.blockEntryThrough].every(time => time === null || (Number.isSafeInteger(time) && time % step === 0))
        || ![0, 1].includes(this.zWeight))) {
      throw new Error('The prospective paper checkpoint is invalid.');
    }
  }

  checkpoint() {
    return {
      version: 1, markTime: this.markTime, receivedAt: this.receivedAt, boundary: this.boundary,
      blockEntryThrough: this.blockEntryThrough, zWeight: this.zWeight,
      books: this.books.map(({ profile, broker, exits, liquidations }) => ({
        id: profile.id, broker: broker.checkpoint(), exits, liquidations,
      })),
    };
  }

  async sample(signal, { clock = clockSeconds, candles = readMinutes, snapshot = readSnapshot } = {}) {
    const requestedEnd = boundaryAt(clock() - 5);
    let candleIssue = null;
    if (this.historyEnd === null || requestedEnd > this.historyEnd) {
      const replace = this.historyEnd === null || requestedEnd - this.historyEnd >= warmup;
      const from = replace ? requestedEnd - warmup : this.historyEnd;
      try {
        const incoming = await candles(market, from, requestedEnd, signal);
        if (incoming.length !== (requestedEnd - from) / minute
            || !incoming.every((bar, index) => bar.time === from + index * minute)) {
          throw new Error('Waiting for consecutive closed GUM trade candles.');
        }
        this.minutes = replace ? incoming : this.minutes.concat(incoming).slice(-warmup / minute);
        this.historyEnd = requestedEnd;
      } catch (error) {
        if (signal?.aborted) throw error;
        candleIssue = error.message;
      }
    }

    let latest;
    let at;
    try {
      latest = await snapshot(market, signal);
      at = clock();
      const { mark, short, long } = latest;
      if (!Number.isSafeInteger(at) || !Number.isSafeInteger(mark?.time) || !Number.isFinite(mark.price) || mark.price <= 0
          || mark.time < at - 20 || mark.time > at + 5 || mark.time < this.startedAt
          || (this.receivedAt !== null && at < this.receivedAt)
          || (this.markTime !== null && mark.time <= this.markTime)
          || short?.venue !== 'GUM' || long?.venue !== 'GUM' || !Number.isFinite(short.carryBps)) {
        throw new Error('A fresh, newer GUM mark and funding terms are required.');
      }
    } catch (error) {
      if (signal?.aborted) throw error;
      return { type: 'feed-unavailable', market, mode: 'paper', at: clock(), issue: error.message, candleIssue };
    }

    const { mark, ...terms } = latest;
    const target = boundaryAt(Math.min(mark.time, at));
    const quoteGap = this.markTime !== null && mark.time - this.markTime > markGapLimit;
    const fundingGap = quoteGap && Math.floor(mark.time / 3600) > Math.floor(this.markTime / 3600)
      && this.books.some(book => book.broker.position !== null);
    if (this.boundary === null || this.resuming || quoteGap) this.blockEntryThrough = target;
    const canDecide = this.historyEnd !== null && target <= this.historyEnd
      && (this.boundary === null || target > this.boundary);
    let action = 'observe';
    let zDecision;
    let voltyDecision;
    if (canDecide) {
      const timely = this.boundary !== null && target === this.boundary + step && mark.time - target <= decisionGrace;
      action = timely && target > this.blockEntryThrough ? 'apply' : 'resync';
      const closed = this.historyEnd === target ? this.minutes : this.minutes.filter(bar => bar.time < target);
      zDecision = shortZScoreState(aggregateMinutes(closed, step), { after: this.boundary, weight: this.zWeight });
      voltyDecision = fiveMinuteDecisions(fiveMinuteContext(closed), volty).get(target);
      if (voltyDecision === undefined) throw new Error('The completed Volty boundary is absent from its candle context.');
      this.boundary = target;
      this.zWeight = zDecision.weight;
    } else if (this.boundary === null || target > this.boundary) {
      action = 'await-candle';
    } else if (quoteGap || this.resuming) {
      action = 'quote-gap';
    }
    const profiles = this.books.map(book => accountObservation(book, mark, terms, action, canDecide ? target : null,
      book.profile.candidateId === volty.id ? voltyDecision : zDecision));
    profiles.push(cashObservation());
    this.markTime = mark.time;
    this.receivedAt = at;
    this.resuming = false;
    return {
      type: 'observation', market, mode: 'paper', at, mark, terms: { long: terms.long, short: terms.short },
      candleIssue, candleThrough: this.historyEnd, quoteGap, fundingGap, profiles,
    };
  }
}

const cohortSchema = `
CREATE TABLE IF NOT EXISTS cohort (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  started_at INTEGER NOT NULL,
  config TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
  mark_at INTEGER PRIMARY KEY,
  observed_at INTEGER NOT NULL,
  event TEXT NOT NULL,
  checkpoint TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS cohort_no_update BEFORE UPDATE ON cohort
BEGIN SELECT RAISE(ABORT, 'Paper cohort binding is immutable.'); END;
CREATE TRIGGER IF NOT EXISTS cohort_no_delete BEFORE DELETE ON cohort
BEGIN SELECT RAISE(ABORT, 'Paper cohort binding is immutable.'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON observations
BEGIN SELECT RAISE(ABORT, 'Paper observations are append-only.'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON observations
BEGIN SELECT RAISE(ABORT, 'Paper observations are append-only.'); END;
CREATE TRIGGER IF NOT EXISTS observations_ordered BEFORE INSERT ON observations
WHEN NEW.mark_at <= (SELECT max(mark_at) FROM observations)
  OR NEW.observed_at < (SELECT observed_at FROM observations ORDER BY mark_at DESC LIMIT 1)
BEGIN SELECT RAISE(ABORT, 'Paper observations must advance their clocks.'); END;
`;

export async function openProspectiveJournal(output, pollSeconds, sourceSha256, { clock = clockSeconds } = {}) {
  const { DatabaseSync } = await import('node:sqlite');
  await mkdir(output, { mode: 0o700, recursive: true });
  const lock = new DatabaseSync(join(output, 'owner.sqlite3'));
  let db;
  try {
    try {
      // The separate lock DB keeps single-writer ownership without locking out report readers.
      lock.exec('BEGIN EXCLUSIVE');
    } catch (error) {
      if (error.errcode !== 5 && error.errcode !== 6) throw error;
      throw new Error('The paper cohort already has an active writer.', { cause: error });
    }
    db = new DatabaseSync(join(output, 'cohort.sqlite3'));
    db.exec('PRAGMA journal_mode = WAL; PRAGMA synchronous = FULL; BEGIN IMMEDIATE;');
    db.exec(cohortSchema);
    const current = db.prepare('SELECT started_at, config FROM cohort WHERE id = 1').get();
    const config = prospectiveConfig(current?.started_at ?? clock(), pollSeconds, sourceSha256);
    const text = JSON.stringify(config);
    if (current && current.config !== text) {
      throw new Error('This paper cohort is bound to different rules, source or polling. Use a new cohort directory.');
    }
    if (!current) db.prepare('INSERT INTO cohort VALUES (1, ?, ?)').run(config.startedAt, text);
    const latest = db.prepare('SELECT mark_at, observed_at, checkpoint FROM observations ORDER BY mark_at DESC LIMIT 1').get();
    if ((!current && latest) || !Number.isSafeInteger(config.startedAt)) throw new Error('Invalid paper cohort ledger.');
    const saved = latest ? JSON.parse(latest.checkpoint) : null;
    if (latest && (saved?.markTime !== latest.mark_at || saved.receivedAt !== latest.observed_at)) {
      throw new Error('Paper observation and checkpoint clocks differ.');
    }
    const session = new ProspectiveSession(config.startedAt, saved);
    db.exec('COMMIT');
    const insert = db.prepare('INSERT INTO observations VALUES (?, ?, ?, ?)');
    return {
      config, session,
      append(event) {
        if (event.type !== 'observation' || event.mark.time !== session.markTime || event.at !== session.receivedAt) {
          throw new Error('Paper journal requires the current accepted observation.');
        }
        insert.run(event.mark.time, event.at, JSON.stringify(event), JSON.stringify(session.checkpoint()));
      },
      close() {
        try { db.close(); } finally { lock.close(); }
      },
    };
  } catch (error) {
    try { db?.close(); } finally { lock.close(); }
    throw error;
  }
}

export async function runProspective({ output, attempts, pollSeconds, sourceSha256 }) {
  process.umask(0o077);
  const journal = await openProspectiveJournal(resolve(output), pollSeconds, sourceSha256);
  const controller = new AbortController();
  const stop = () => controller.abort();
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
  let observations = 0;
  let loggedAt = 0;
  try {
    for (let attempt = 0; !controller.signal.aborted && attempt < attempts; attempt += 1) {
      const event = await journal.session.sample(controller.signal);
      if (event.type === 'observation') {
        journal.append(event);
        observations += 1;
        if (event.at - loggedAt >= 60 || event.profiles.some(profile => profile.newExits.length)) {
          console.log(JSON.stringify({ mode: event.mode, market, markAt: event.mark.time,
            candleThrough: event.candleThrough, profiles: event.profiles.map(({ id, equity, exits }) => ({ id, equity, exits })) }));
          loggedAt = event.at;
        }
      } else if (event.at - loggedAt >= 60) {
        console.error(event.issue);
        loggedAt = event.at;
      }
      if (attempt + 1 < attempts) await delay(pollSeconds * 1000, undefined, { signal: controller.signal });
    }
    if (!observations && !controller.signal.aborted) process.exitCode = 1;
  } catch (error) {
    if (!controller.signal.aborted) throw error;
  } finally {
    process.off('SIGINT', stop);
    process.off('SIGTERM', stop);
    journal.close();
  }
}
