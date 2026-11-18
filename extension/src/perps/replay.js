import { barrier, carryCost, liquidationPrice, planPosition, settle } from './model.js';
import { breakout, signalMap } from './strategies.js';

export const PAPER_CAPITAL = 1000;

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

  constructor(settings) {
    this.settings = Object.freeze({ ...settings });
  }

  open(time, price, direction, market, weight) {
    try {
      const position = planPosition(this.settings, market, price, direction, weight);
      if (position.deposit > this.equity) throw new Error('Paper account has insufficient remaining capital.');
      this.position = { ...position, carry: 0, time, openedAt: time };
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
    this.ledger.push({ ...result, time, openedAt: position.openedAt, entry: position.entry, direction: position.direction });
    this.position = null;
    this.mark(exit.price);
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
  observe(bar, { decision, decisionKind, long, short }) {
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
      const exit = barrier(position, atOpen, position.carry) ?? signalExit ?? barrier(position, bar, position.carry);
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
          this.open(time, entry.price, entry.direction, entry.direction === 1 ? long : short, 1);
          if (this.position) {
            const exit = barrier(this.position, { ...bar, open: entry.price }, 0);
            if (exit) this.close(time, exit);
          }
        }
      }
    } else if (decision !== undefined) {
      const weight = decision?.weight ?? 0;
      if (!weight) this.close(time, { reason: 'signal', price: bar.open });
      else if (!ended && !this.position && weight > this.lastWeight) {
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
