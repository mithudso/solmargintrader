import { causalEntryFeatures } from './workbench-store.js';
import { planPosition } from './model.js';
import { PaperBroker, PAPER_CAPITAL } from './replay.js';
import { marketPresets, signalMap } from './strategies.js';

export const QUOTE_MAX_AGE = 20;

export function freshQuote(feed, now) {
  const mark = feed?.snapshot?.mark;
  return !feed?.issue && Number.isFinite(mark?.time) && Number.isFinite(mark?.price)
    && mark.price > 0 && mark.time >= now - QUOTE_MAX_AGE && mark.time <= now + 5 ? mark : null;
}

function hooks(feed, makeId) {
  return { onEntry: ({ time }) => {
    const entryFeatures = causalEntryFeatures(feed.history, time);
    return entryFeatures ? { id: makeId(), entryFeatures } : null;
  } };
}

function saved(account, broker) {
  const trades = broker.ledger.map(row => ({ ...row, strategy: account.strategy ?? 'manual', step: account.step }));
  const recent = [...account.recent, ...trades].slice(-5);
  return {
    account: { ...account, broker: broker.checkpoint(), recent, exits: account.exits + trades.length },
    trades,
  };
}

export function beginPaper(current, feed, { asset, settings, direction, strategy, step, now, makeId }) {
  const quote = freshQuote(feed, now);
  if (!quote || !causalEntryFeatures(feed.history, quote.time)) throw new Error('Wait for a fresh market mark and contiguous closed one-minute candles.');
  if (current?.running || current?.broker.position) throw new Error('This paper account already has an active strategy or position.');
  const preset = strategy && marketPresets(asset).find(value => value.id === strategy);
  if (strategy && !preset) throw new Error('Unknown paper strategy.');
  if ((!preset || preset.kind !== 'volty') && direction === 0) throw new Error('Choose a single direction for this entry.');
  if (preset && preset.kind !== 'volty' && direction !== 1) throw new Error('This strategy only supplies long signals.');
  for (const side of direction === 0 ? [1, -1] : [direction]) {
    const terms = side === 1 ? feed.snapshot.long : feed.snapshot.short;
    const position = planPosition(settings, terms, quote.price, side);
    if (position.deposit > (current?.broker.equity ?? PAPER_CAPITAL)) throw new Error('Paper account has insufficient remaining capital.');
  }
  const broker = new PaperBroker(settings, { entryDirection: direction, ...hooks(feed, makeId) });
  if (current) {
    broker.equity = current.broker.equity;
    broker.peak = current.broker.peak;
    broker.drawdown = current.broker.drawdown;
  }
  const lastDecision = preset ? Math.floor(quote.time / preset.step) * preset.step : 0;
  if (preset) {
    const decision = signalMap(feed.history, preset).get(lastDecision);
    if (!decision) throw new Error('Wait for the strategy to warm up on the latest closed candle.');
    if (preset.kind === 'volty') broker.signal = decision;
  } else {
    broker.open(quote.time, quote.price, direction, direction === 1 ? feed.snapshot.long : feed.snapshot.short, 1);
    if (!broker.position) throw new Error(broker.note || 'Paper entry was refused.');
  }
  return saved({
    asset, strategy: preset?.id ?? null, step: preset?.step ?? step, running: Boolean(preset),
    runId: preset ? makeId() : null,
    lastPoint: quote.time, lastDecision, notice: '', recent: current?.recent ?? [], exits: current?.exits ?? 0,
  }, broker);
}

function pause(account, broker, notice = '') {
  account.running = false;
  account.notice = notice;
  broker.signal = null;
}

export function stopPaperEntries(current, runId) {
  if (!current?.running || (current.runId ?? '') !== runId) return null;
  const broker = PaperBroker.fromCheckpoint(current.broker);
  const account = { ...current };
  pause(account, broker);
  return saved(account, broker);
}

function observation(snapshot, point, decision, decisionKind, history) {
  const { time, price } = point;
  return {
    bar: { time, open: price, high: price, low: price, close: price },
    market: { decision, decisionKind, long: snapshot.long, short: snapshot.short, exitMinutes: history },
  };
}

export function observePaper(current, feed, now, makeId) {
  const quote = freshQuote(feed, now);
  if (!quote || !current || !current.running && !current.broker.position || quote.time <= current.lastPoint) return null;
  const account = { ...current };
  const broker = PaperBroker.fromCheckpoint(current.broker, hooks(feed, makeId));
  const preset = account.strategy && marketPresets(account.asset).find(value => value.id === account.strategy);
  if (account.running && !preset) pause(account, broker, 'The saved strategy is unavailable. Entries are paused.');
  const decisions = account.running ? signalMap(feed.history, preset) : null;
  for (const point of feed.snapshot.points) {
    if (point.time <= account.lastPoint) continue;
    if (point.time - account.lastPoint > 25 && account.running) {
      pause(account, broker, 'Market observations were interrupted. Strategy entries are paused.');
    }
    const boundary = preset ? Math.floor(point.time / preset.step) * preset.step : 0;
    const planned = account.running && point.time - boundary < 60 ? decisions.get(boundary) : undefined;
    const decision = boundary > account.lastDecision ? planned : undefined;
    if (account.running && boundary > account.lastDecision && planned === undefined && point.time - boundary >= 45) {
      pause(account, broker, 'The next closed signal candle is unavailable. Strategy entries are paused.');
    }
    if (account.running && decision !== undefined) account.lastDecision = boundary;
    const { bar, market } = observation(feed.snapshot, point, decision, account.running ? preset.kind : 'manual', feed.history);
    broker.observe(bar, market);
    account.lastPoint = point.time;
  }
  return saved(account, broker);
}

export function closePaper(current, feed, id, now) {
  const quote = freshQuote(feed, now);
  if (!quote) throw new Error('Wait for a fresh market mark to close this position.');
  if (!current?.broker.position || current.broker.position.id !== id) throw new Error('This paper position has changed.');
  if (quote.time < current.lastPoint) throw new Error('Wait for a newer market mark.');
  const account = { ...current };
  const broker = PaperBroker.fromCheckpoint(current.broker);
  pause(account, broker);
  for (const point of feed.snapshot.points) {
    if (point.time <= account.lastPoint || point.time > quote.time || !broker.position) continue;
    const { bar, market } = observation(feed.snapshot, point, undefined, 'manual', feed.history);
    broker.observe(bar, market);
    account.lastPoint = point.time;
  }
  account.lastPoint = quote.time;
  if (broker.position) broker.close(quote.time, { reason: 'manual', price: quote.price });
  return saved(account, broker);
}

export function managePaper(current, id, rule) {
  if (!current?.broker.position || current.broker.position.id !== id) throw new Error('This paper position has changed.');
  const broker = PaperBroker.fromCheckpoint(current.broker);
  broker.managePosition(id, rule);
  return saved(current, broker);
}
