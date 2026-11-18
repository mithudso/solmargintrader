/** Operator-run ZEC paper forward books on public GUM candles and sampled marks. */
import { createHash } from 'node:crypto';
import { mkdir, open, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { readMinutes, readSnapshot } from '../src/perps/market.js';
import { PAPER_CAPITAL, PaperBroker } from '../src/perps/replay.js';
import { fiveMinuteCandidates, fiveMinuteContext, fiveMinuteDecisions } from './lib/zec-gum-five-minute.mjs';

const market = 'ZEC';
const step = 300;
const minute = 60;
const warmup = 720 * minute;
const decisionGrace = 60;
const maxMarkGap = 45;
const settings = { sizing: 'notional', amount: 250, leverage: 25, slippageBps: 2, additiveBps: 0, networkUsd: 0.01 };
const defaultConfig = new URL('../../research/results/zec_gum_25x_5m_live.json', import.meta.url);
const wallSeconds = () => Math.floor(Date.now() / 1000);
const floorBar = time => Math.floor(time / step) * step;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

function resolveProfiles(config) {
  if (config?.version !== 1 || config.market !== market || config.step !== step || config.mode !== 'paper'
      || !Object.entries(settings).every(([key, value]) => config.settings?.[key] === value)
      || !Array.isArray(config.profiles) || config.profiles.length !== 3) {
    throw new Error('Expected three ZEC 5m paper profiles at 25× and $250 target exposure.');
  }
  const catalog = new Map(fiveMinuteCandidates().map(candidate => [candidate.id, candidate]));
  const ids = new Set();
  const selections = new Set();
  return config.profiles.map(profile => {
    const { id, candidateId, tp, sl } = profile ?? {};
    const candidate = catalog.get(candidateId);
    const selection = JSON.stringify([candidateId, tp, sl]);
    if (typeof id !== 'string' || !/^[a-z0-9][a-z0-9-]{0,79}$/u.test(id) || ids.has(id) || selections.has(selection)
        || !candidate || ![tp, sl].every(value => Number.isFinite(value) && value >= 0 && value < 100)) {
      throw new Error('The live preset has a missing, duplicate or invalid profile.');
    }
    ids.add(id);
    selections.add(selection);
    return { id, candidate, settings: { ...settings, tp, sl } };
  });
}

function visibleDecision(decision) {
  if (!decision) return null;
  if ('weight' in decision) return { weight: decision.weight };
  // The signal code uses infinity to disable one side without inventing a price.
  return { upper: Number.isFinite(decision.upper) ? decision.upper : null,
    lower: Number.isFinite(decision.lower) ? decision.lower : null };
}

function sampleBook(book, mark, terms, action, decisionTime, decision) {
  const { broker, profile } = book;
  let executable;
  if (action === 'apply') {
    executable = decision;
  } else if (action === 'bootstrap' || action === 'resync') {
    if (profile.candidate.kind === 'volty') {
      executable = null;
    } else {
      // Seed from history without entering on a signal that predates the session.
      broker.lastWeight = decision?.weight ?? 0;
      if (broker.position && decision && !decision.weight) executable = decision;
    }
  } else if (action === 'await-candle' || action === 'quote-gap') {
    if (profile.candidate.kind === 'volty') executable = null;
  }

  const { time, price } = mark;
  const previousExits = broker.ledger.length;
  broker.observe({ time, open: price, high: price, low: price, close: price }, {
    long: terms.long, short: terms.short, decisionKind: profile.candidate.kind, decision: executable,
  });
  const view = broker.view(price);
  const position = view.position && {
    openedAt: view.position.openedAt, direction: view.position.direction, entry: view.position.entry,
    sizeUsd: view.position.size, take: view.position.take, stop: view.position.stop,
    liquidation: view.position.liquidation, carryUsd: view.position.carry,
  };
  return {
    id: profile.id, candidateId: profile.candidate.id,
    decision: { status: action, boundary: decisionTime, value: visibleDecision(decision) },
    equity: view.equity, realizedPnlUsd: view.realized, drawdown: view.drawdown, position,
    exits: view.exits, liquidations: view.liquidations, refused: broker.refused,
    newExits: broker.ledger.slice(previousExits),
  };
}

export class LivePaperSession {
  constructor(config) {
    this.profiles = resolveProfiles(config);
    this.books = this.profiles.map(profile => ({ profile, broker: new PaperBroker(profile.settings) }));
    this.minutes = [];
    this.historyEnd = null;
    this.boundary = null;
    this.markTime = null;
  }

  async sample(signal, { clock = wallSeconds, candles = readMinutes, snapshot = readSnapshot } = {}) {
    // Allow the newest minute to settle before requesting it at a boundary.
    const requestedEnd = floorBar(clock() - (this.historyEnd === null ? minute : 5));
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
        this.minutes = replace ? incoming : this.minutes.concat(incoming);
        this.historyEnd = requestedEnd;
      } catch (error) {
        if (signal?.aborted) throw error;
        candleIssue = error.message;
      }
    }

    let latest;
    try {
      latest = await snapshot(market, signal);
      const receivedAt = clock();
      if (!Number.isFinite(latest.mark?.time) || !Number.isFinite(latest.mark?.price) || latest.mark.price <= 0
          || latest.mark.time < receivedAt - 20 || latest.mark.time > receivedAt + 5
          || latest.long?.venue !== 'GUM' || latest.short?.venue !== 'GUM') {
        throw new Error('A fresh GUM mark and terms are required.');
      }
    } catch (error) {
      if (signal?.aborted) throw error;
      return { type: 'feed-unavailable', market, mode: 'paper', at: clock(), issue: error.message, candleIssue };
    }
    if (this.historyEnd === null) {
      return { type: 'feed-unavailable', market, mode: 'paper', at: clock(), issue: candleIssue };
    }
    const { mark, long, short } = latest;
    if (this.markTime !== null && mark.time <= this.markTime) {
      return { type: 'feed-unavailable', market, mode: 'paper', at: clock(),
        issue: 'GUM mark timestamp is unchanged or regressed.', candleIssue };
    }
    const target = floorBar(Math.min(mark.time, clock()));
    const quoteGap = this.markTime !== null && mark.time - this.markTime > maxMarkGap;
    const bootstrap = this.boundary === null;
    const freshBoundary = bootstrap || (target > this.boundary && target <= this.historyEnd);
    const decisionTime = freshBoundary ? Math.min(target, this.historyEnd) : null;
    let action = 'observe';
    let decisions;
    if (freshBoundary) {
      const timely = target === this.boundary + step && mark.time - target <= decisionGrace;
      action = bootstrap ? 'bootstrap' : !quoteGap && timely ? 'apply' : 'resync';
      const closed = this.historyEnd === decisionTime
        ? this.minutes : this.minutes.filter(bar => bar.time < decisionTime);
      const context = fiveMinuteContext(closed);
      decisions = this.profiles.map(profile => fiveMinuteDecisions(context, profile.candidate).get(decisionTime));
      if (decisions.some(decision => decision === undefined)) {
        throw new Error('A completed signal boundary is absent from the strategy context.');
      }
      this.boundary = target;
    } else if (target > this.boundary) {
      action = 'await-candle';
    } else if (quoteGap) {
      action = 'quote-gap';
    }

    const profiles = this.books.map((book, i) =>
      sampleBook(book, mark, { long, short }, action, decisionTime, decisions?.[i]));
    this.markTime = mark.time;
    return { type: 'observation', market, mode: 'paper', at: clock(), mark, terms: { long, short }, candleIssue,
      candleThrough: this.historyEnd, quoteGap, profiles };
  }
}

const sourceUrls = [
  new URL(import.meta.url), new URL('./lib/zec-gum-five-minute.mjs', import.meta.url),
  new URL('./lib/zec-perps-signals.mjs', import.meta.url), new URL('../src/perps/market.js', import.meta.url),
  new URL('../src/perps/replay.js', import.meta.url), new URL('../src/perps/model.js', import.meta.url),
  new URL('../src/perps/strategies.js', import.meta.url), new URL('../src/perps/archive-presets.js', import.meta.url),
  new URL('../src/1000x/indicators.js', import.meta.url), new URL('../src/1000x/reversal.js', import.meta.url),
  new URL('../src/1000x/feed.js', import.meta.url),
];

async function main() {
  const { values } = parseArgs({ options: {
    config: { type: 'string' }, output: { type: 'string' }, once: { type: 'boolean' },
    samples: { type: 'string' }, 'poll-seconds': { type: 'string', default: '10' }, help: { type: 'boolean' },
  } });
  if (values.help) {
    console.log('node extension/tools/zec-gum-live.mjs --output NEW_DIR [--config FILE] [--once | --samples N] [--poll-seconds S]');
    return;
  }
  const pollSeconds = Number(values['poll-seconds']);
  const attempts = values.samples === undefined ? (values.once ? 1 : Infinity) : Number(values.samples);
  if (!values.output || (values.once && values.samples !== undefined)
      || (values.samples !== undefined && !Number.isSafeInteger(attempts)) || attempts < 1
      || !Number.isInteger(pollSeconds) || pollSeconds < 5 || pollSeconds > 30) {
    throw new Error('Supply a new session directory, optional positive sample count and a 5–30 second poll interval.');
  }
  const configSource = values.config ? resolve(values.config) : defaultConfig;
  const bytes = await readFile(configSource);
  const live = new LivePaperSession(JSON.parse(bytes));
  const sourceSha256 = Object.fromEntries(await Promise.all(sourceUrls.map(async url =>
    [url.pathname.split('/').at(-1), digest(await readFile(url))])));
  const output = resolve(values.output);
  await mkdir(output, { mode: 0o700 });
  const session = {
    version: 1, mode: 'paper', market, step, startedAt: new Date().toISOString(), pollSeconds,
    configSha256: digest(bytes), sourceSha256, capitalPerProfileUsd: PAPER_CAPITAL, profiles: live.profiles,
    execution: {
      price: 'Sampled live GUM marks. Paper prices include modeled slippage and network costs.',
      funding: 'Current signed rate estimate applied at elapsed UTC hour boundaries.',
      candles: 'Contiguous completed GUM trade candles. Startup history seeds signals without paper entry.',
      outages: 'Stale entries are discarded. After a mark gap, the first available current mark evaluates existing paper barriers.',
      restart: 'A new session starts flat and requires a new directory. The prior JSONL is retained with its last equity and position.',
    },
  };
  await writeFile(join(output, 'session.json'), JSON.stringify(session, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  const log = await open(join(output, 'events.jsonl'), 'wx', 0o600);
  const emit = async event => {
    await log.writeFile(JSON.stringify(event) + '\n');
    await log.sync();
  };
  const controller = new AbortController();
  const stop = () => controller.abort();
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
  let observations = 0;
  try {
    for (let attempt = 0; !controller.signal.aborted && attempt < attempts; attempt += 1) {
      const event = await live.sample(controller.signal);
      await emit(event);
      if (event.type === 'observation') {
        observations += 1;
        console.log(JSON.stringify({ mode: 'paper', market, mark: event.mark, candleThrough: event.candleThrough,
          profiles: event.profiles.map(profile => ({ id: profile.id, decision: profile.decision.status,
            equity: profile.equity, open: Boolean(profile.position), exits: profile.exits })) }));
      } else {
        console.error(event.issue);
      }
      if (attempt + 1 < attempts) await delay(pollSeconds * 1000, undefined, { signal: controller.signal });
    }
    if (!observations && !controller.signal.aborted) process.exitCode = 1;
  } catch (error) {
    if (!controller.signal.aborted) throw error;
  } finally {
    process.off('SIGINT', stop);
    process.off('SIGTERM', stop);
    await emit({ type: 'stopped', mode: 'paper', market, at: wallSeconds(), observations });
    await log.close();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await main();
}
