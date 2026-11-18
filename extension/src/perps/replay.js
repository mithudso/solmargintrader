import { barrier, carryCost, liquidationPrice, planPosition, settle } from './model.js';
import { breakout, signalMap } from './strategies.js';
import { evaluateExitSignals, validateExitSignals } from './managed-exits.js';

export const PAPER_CAPITAL = 1000;
const directions = [-1, 0, 1];
const positionId = value => typeof value === 'string' && value.length > 0 && value.length <= 128;
const featureVector = value => Array.isArray(value) && value.length > 0 && value.length <= 128
  && value.every(Number.isFinite);

function bindEntry(position, id, entryFeatures) {
  Object.defineProperties(position, {
    id: { value: id, enumerable: true, writable: false, configurable: false },
    entryFeatures: { value: Object.freeze([...entryFeatures]), enumerable: true, writable: false, configurable: false },
  });
}

function validCheckpointPosition(position) {
  if (position === null) return true;
  if (!position || ![1, -1].includes(position.direction)
      || ![position.entry, position.units, position.deposit].every(value => Number.isFinite(value) && value > 0)
      || ![position.time, position.openedAt, position.carry].every(Number.isFinite)
      || position.time < position.openedAt) return false;
  return position.id === undefined && position.entryFeatures === undefined
    || positionId(position.id) && featureVector(position.entryFeatures);
}

/** Positions belong to one paper account. Every transition is synchronous and records the source time. */
export class PaperBroker {
  equity = PAPER_CAPITAL;
  position = null;
  ledger = [];
  refused = 0;
  peak = PAPER_CAPITAL;
  drawdown = 0;
  lastWeight = 0;
  lastBreakout = 0;
  signal = null;
  note = '';

  constructor(settings, { entryDirection = 0, onEntry = null } = {}) {
    if (!directions.includes(entryDirection) || (onEntry !== null && typeof onEntry !== 'function')) {
      throw new Error('Invalid paper broker options.');
    }
    this.settings = Object.freeze({ ...settings });
    this.entryDirection = entryDirection;
    this.onEntry = onEntry;
  }

  /** Ledger rows are appended to the journal separately from the account checkpoint. */
  checkpoint() {
    const { settings, entryDirection, equity, position, refused, peak, drawdown,
      lastWeight, lastBreakout, signal, note } = this;
    return structuredClone({ version: 1, settings, entryDirection, equity, position,
      refused, peak, drawdown, lastWeight, lastBreakout, signal, note });
  }

  static fromCheckpoint(saved, { onEntry = null } = {}) {
    if (saved?.version !== 1 || !saved.settings || typeof saved.settings !== 'object' || Array.isArray(saved.settings)
        || !directions.includes(saved.entryDirection) || !directions.includes(saved.lastBreakout)
        || ![saved.equity, saved.refused, saved.peak, saved.drawdown, saved.lastWeight].every(Number.isFinite)
        || saved.peak < PAPER_CAPITAL || saved.equity < 0 || !Number.isSafeInteger(saved.refused) || saved.refused < 0
        || saved.drawdown < 0 || saved.drawdown > 1 || saved.lastWeight < 0 || saved.lastWeight > 1
        || typeof saved.note !== 'string' || !validCheckpointPosition(saved.position)) {
      throw new Error('Invalid paper account checkpoint.');
    }
    const { position, equity, refused, peak, drawdown, lastWeight, lastBreakout, signal, note } = structuredClone(saved);
    if (position?.id !== undefined) bindEntry(position, position.id, position.entryFeatures);
    const broker = new PaperBroker(saved.settings, { entryDirection: saved.entryDirection, onEntry });
    Object.assign(broker, { position, equity, refused, peak, drawdown, lastWeight, lastBreakout, signal, note });
    return broker;
  }

  open(time, price, direction, market, weight) {
    try {
      if (this.position) throw new Error('Close the open paper position before replacing it.');
      const position = planPosition(this.settings, market, price, direction, weight);
      if (position.deposit > this.equity) throw new Error('Paper account has insufficient remaining capital.');
      const held = { ...position, carry: 0, time, openedAt: time };
      if (this.onEntry) {
        const { id, entryFeatures } = this.onEntry({ time, price, direction, market, weight }) ?? {};
        if (!positionId(id) || !featureVector(entryFeatures)) {
          throw new Error('Wait for complete candle history to capture causal entry features.');
        }
        bindEntry(held, id, entryFeatures);
      }
      this.position = held;
      this.note = '';
    } catch (error) {
      this.refused += 1;
      this.note = error.message;
    }
  }

  close(time, exit) {
    if (!this.position) return;
    const position = this.position;
    const result = settle(position, exit, position.carry);
    this.equity += result.pnl;
    const entry = position.id === undefined ? {} : {
      id: position.id, features: [...position.entryFeatures], units: position.units, size: position.size,
    };
    this.ledger.push({ ...result, time, openedAt: position.openedAt, entry: position.entry, direction: position.direction, ...entry });
    this.position = null;
    this.mark(exit.price);
  }

  managePosition(id, { tp, sl, armedAt, signals = null } = {}) {
    const position = this.position;
    if (!positionId(id) || position?.id !== id) throw new Error('The selected paper position is no longer open.');
    if (![tp, sl].every(value => Number.isFinite(value) && value >= 0 && value < 100)
        || !Number.isFinite(armedAt) || armedAt < position.time) {
      throw new Error('Enter valid price distances and a current observation time.');
    }
    const policy = validateExitSignals(signals);
    const existing = position.exitPolicy;
    if (existing && position.time < existing.armedAt) {
      throw new Error('Wait for a fresh mark to apply the pending exit edit.');
    }
    const priorBrackets = { take: position.take, stop: position.stop };
    const priorSignal = existing?.signals
      ? { signals: existing.signals, armedAt: existing.armedAt, lastEvaluatedAt: existing.lastEvaluatedAt } : null;
    position.stop = sl ? position.entry * (1 - position.direction * sl / 100) : null;
    position.take = tp ? position.entry * (1 + position.direction * tp / 100) : null;
    position.exitPolicy = { tp, sl, armedAt, signals: policy, lastEvaluatedAt: armedAt, priorBrackets, priorSignal };
  }

  managedExit(policy, bar, minutes) {
    if (!policy?.signals) return null;
    const boundary = Math.floor(bar.time / policy.signals.step) * policy.signals.step;
    if (boundary <= policy.lastEvaluatedAt) return null;
    const { available, matched } = evaluateExitSignals(minutes, policy.signals, bar.time);
    if (available) policy.lastEvaluatedAt = boundary;
    return matched ? { reason: 'managed-signal', price: bar.open } : null;
  }

  allowsEntry(direction) {
    return this.entryDirection === 0 || this.entryDirection === direction;
  }

  mark(price) {
    const position = this.position;
    const openPnl = position ? settle(position, { reason: 'mark', price }, position.carry).pnl : 0;
    const equity = this.equity + openPnl;
    this.peak = Math.max(this.peak, equity);
    this.drawdown = Math.max(this.drawdown, 1 - equity / this.peak);
    return equity;
  }

  /** OHLC simulation or an observed tick with high=low=open=close. */
  observe(bar, { decision, decisionKind, long, short, exitMinutes }) {
    const time = bar.time;
    let ended = false;
    if (this.position) {
      const position = this.position;
      const market = position.direction === 1 ? long : short;
      position.carry += carryCost({ ...position, market }, position.time, time, bar.open);
      position.time = time;
      const atOpen = { open: bar.open, high: bar.open, low: bar.open };
      const signalExit = decision !== undefined && decisionKind !== 'volty' && !decision?.weight
        ? { reason: 'signal', price: bar.open } : null;
      const policy = position.exitPolicy;
      const managed = policy && time > policy.armedAt;
      // Late observations retain the last effective price brackets until this edit takes effect.
      const protective = policy && !managed ? { ...position, ...policy.priorBrackets } : position;
      const opening = barrier(protective, atOpen, position.carry);
      const activePolicy = managed ? policy : policy?.priorSignal;
      const exit = activePolicy
        ? opening ?? barrier(protective, bar, position.carry) ?? this.managedExit(activePolicy, bar, exitMinutes) ?? signalExit
        : opening ?? signalExit ?? barrier(protective, bar, position.carry);
      if (exit) {
        this.close(time, exit);
        ended = true;
      }
    }
    if (decision !== undefined) {
      this.signal = decision;
      this.lastBreakout = 0;
    }
    if (decisionKind === 'volty') {
      if (this.signal && !ended) {
        const entry = breakout(bar, this.signal, this.position?.direction ?? this.lastBreakout);
        if (entry) {
          this.lastBreakout = entry.direction;
          this.close(time, { reason: 'signal', price: entry.price });
          if (this.allowsEntry(entry.direction)) {
            this.open(time, entry.price, entry.direction, entry.direction === 1 ? long : short, 1);
          }
          if (this.position) {
            const exit = barrier(this.position, { ...bar, open: entry.price }, 0);
            if (exit) this.close(time, exit);
          }
        }
      }
    } else if (decision !== undefined) {
      const weight = decision?.weight ?? 0;
      if (!weight) this.close(time, { reason: 'signal', price: bar.open });
      else if (!ended && !this.position && weight > this.lastWeight && this.allowsEntry(1)) {
        this.open(time, bar.open, 1, long, weight);
        if (this.position) {
          const exit = barrier(this.position, bar, 0);
          if (exit) this.close(time, exit);
        }
      }
      this.lastWeight = weight;
    }
    this.mark(bar.close);
  }

  view(price) {
    const position = this.position;
    return {
      equity: this.mark(price), realized: this.equity - PAPER_CAPITAL, drawdown: this.drawdown,
      position: position ? { ...position, liquidation: liquidationPrice(position, position.carry) } : null,
      exits: this.ledger.length, liquidations: this.ledger.filter(row => row.reason === 'liquidation').length,
    };
  }
}

export function replay(minutes, preset, settings, terms, from, to, decisions = signalMap(minutes, preset)) {
  const broker = new PaperBroker(settings);
  let last = null;
  for (const bar of minutes) {
    if (bar.time < from || bar.time >= to) continue;
    if (last && bar.time !== last.time + 60) throw new Error('A replay slice must be contiguous.');
    broker.observe(bar, { decision: decisions.get(bar.time), decisionKind: preset.kind, ...terms });
    last = bar;
  }
  if (!last) throw new Error('No complete replay candles.');
  if (broker.position) {
    const position = broker.position;
    const market = position.direction === 1 ? terms.long : terms.short;
    position.carry += carryCost({ ...position, market }, position.time, last.time + 60, last.close);
    const mark = { open: last.close, high: last.close, low: last.close };
    broker.close(last.time + 60, barrier(position, mark, position.carry) ?? { reason: 'end', price: last.close });
  }
  const view = broker.view(last.close);
  return {
    returnPct: 100 * view.realized / PAPER_CAPITAL, drawdownPct: 100 * view.drawdown,
    trades: view.exits, liquidations: view.liquidations, refused: broker.refused,
    stops: broker.ledger.filter(row => row.reason === 'stop').length,
    takes: broker.ledger.filter(row => row.reason === 'take').length,
  };
}
