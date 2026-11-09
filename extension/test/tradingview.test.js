import test from 'node:test';
import assert from 'node:assert/strict';
import { tradingViewUrl } from '../src/ui/tradingview.js';

test('TradingView frame pins selected pair and cannot navigate to an injected origin', () => {
  const url = new URL(tradingViewUrl('SOL', 'dark'));
  assert.equal(url.origin, 'https://www.tradingview-widget.com');
  const config = JSON.parse(decodeURIComponent(url.hash.slice(1)));
  assert.equal(config.symbol, 'COINBASE:SOLUSD');
  assert.equal(config.interval, '1');
  assert.equal(JSON.parse(decodeURIComponent(new URL(tradingViewUrl('ETH')).hash.slice(1))).symbol, 'COINBASE:ETHUSD');
  assert.throws(() => tradingViewUrl('SOL/../../evil'));
});
