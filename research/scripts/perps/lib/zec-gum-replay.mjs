/** Shared offline GUM market path and account metrics for the ZEC studies. */
import { barrier, carryCost } from '../../../../extension/src/perps/model.js';
import { PAPER_CAPITAL, PaperBroker } from '../../../../extension/src/perps/replay.js';

export function validateCapture(source) {
  const { start, end, minutes, funding, terms } = source;
  const firstHour = Math.ceil(start / 3600) * 3600;
  const lastHour = Math.floor(end / 3600) * 3600;
  if (source.version !== 1 || source.asset !== 'ZEC' || terms?.long?.venue !== 'GUM' || terms?.short?.venue !== 'GUM'
      || !Number.isInteger(start) || start % 600 || !Number.isInteger(end) || end % 600 || end - start < 7 * 86400
      || minutes?.length !== (end - start) / 60
      || minutes.some(({ time, open, high, low, close }, i) => time !== start + 60 * i
        || ![open, high, low, close].every(value => Number.isFinite(value) && value > 0)
        || low > Math.min(open, close) || high < Math.max(open, close))
      || funding?.length !== (lastHour - firstHour) / 3600 + 1
      || funding.some((row, i) => row?.symbol !== 'ZEC' || !Number.isFinite(row.rateBps1h)
        || row.timestamp !== firstHour + 3600 * i)) {
    throw new Error('Capture needs contiguous ZEC GUM OHLC, complete hourly funding and market terms.');
  }
}

export function prepareGumWindows({ start, minutes, funding, terms }) {
  const fundingByHour = new Map(funding.map(row => [row.timestamp, row.rateBps1h]));
  const marketAt = time => {
    const carryBps = fundingByHour.get(time) ?? 0;
    return { long: { ...terms.long, carryBps }, short: { ...terms.short, carryBps } };
  };

  function prepareWindow([from, to]) {
    const bars = minutes.slice((from - start) / 60, (to - start) / 60);
    return { bars: bars.map(bar => ({ bar, market: marketAt(bar.time) })), to, closingMarket: marketAt(to) };
  }
  return prepareWindow;
}

function summarize(broker, last, to) {
  const view = broker.view(last.close);
  let wins = 0;
  let grossWins = 0;
  let grossLosses = 0;
  let fundingUsd = 0;
  let heldMinutes = 0;
  let endPnlUsd = 0;
  const exits = { liquidation: 0, stop: 0, take: 0, signal: 0, end: 0 };
  for (const trade of broker.ledger) {
    if (trade.pnl > 0) {
      wins += 1;
      grossWins += trade.pnl;
    } else {
      grossLosses -= trade.pnl;
    }
    fundingUsd += trade.carry;
    heldMinutes += (trade.time - trade.openedAt) / 60;
    exits[trade.reason] += 1;
    if (trade.time === to) endPnlUsd += trade.pnl;
  }
  return {
    returnPct: 100 * view.realized / PAPER_CAPITAL, drawdownPct: 100 * view.drawdown,
    trades: view.exits, wins, liquidations: exits.liquidation, refused: broker.refused,
    stops: exits.stop, takes: exits.take, signals: exits.signal, ends: exits.end,
    endPnlUsd, fundingUsd, heldMinutes, grossWins, grossLosses,
  };
}

export function runGumWindow(window, candidate, decisions, settings) {
  const broker = new PaperBroker(settings);
  const observation = { decision: undefined, decisionKind: candidate.kind, long: null, short: null };
  for (const { bar, market } of window.bars) {
    const decision = decisions.get(bar.time);
    if (decision === undefined && !broker.position && (candidate.kind !== 'volty' || !broker.signal)) continue;
    observation.decision = decision;
    observation.long = market.long;
    observation.short = market.short;
    broker.observe(bar, observation);
  }
  const last = window.bars.at(-1).bar;
  const { position } = broker;
  if (position) {
    const market = position.direction === 1 ? window.closingMarket.long : window.closingMarket.short;
    position.carry += carryCost({ ...position, market }, position.time, window.to, last.close);
    const closeBar = { open: last.close, high: last.close, low: last.close };
    broker.close(window.to, barrier(position, closeBar, position.carry) ?? { reason: 'end', price: last.close });
  }
  return summarize(broker, last, window.to);
}
