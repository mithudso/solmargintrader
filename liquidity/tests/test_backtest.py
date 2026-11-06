import math

import pytest

from aero_lp import backtest
from aero_lp.strategy import StrategyConfig


def test_flat_price_earns_yield_and_never_rebalances():
    prices = [2000.0] * (24 * 10 + 1)
    r = backtest.run(prices, math.log1p(0.05), lambda w: 0.001, start_value=10_000, gas_cost=0.1)
    assert r.rebalances == 0
    assert r.in_range_pct == 100
    assert r.final_value == pytest.approx(10_000, rel=1e-9)
    assert r.earned == pytest.approx(0.001 * 10_000 * 10, rel=1e-6)
    assert r.hodl_value == pytest.approx(10_000, rel=1e-9)


def test_trend_out_of_range_triggers_rebalances_and_costs():
    prices = [2000.0 * (1 + 0.004 * i) for i in range(200)]
    cfg = StrategyConfig(cooldown_minutes=0, confirm_checks=1)
    r = backtest.run(prices, math.log1p(0.02), lambda w: 0.0, start_value=10_000, gas_cost=0.5, cfg=cfg)
    assert r.rebalances > 3
    assert r.costs > 0
    # concentrated LP in a one-way trend underperforms holding (IL realised at each rebalance)
    assert r.total < r.hodl_value


def test_wider_range_rebalances_less():
    prices = [2000.0 * math.exp(0.02 * math.sin(i / 3)) for i in range(500)]
    narrow = backtest.run(prices, math.log1p(0.01), lambda w: 0.0)
    wide = backtest.run(prices, math.log1p(0.10), lambda w: 0.0)
    assert narrow.rebalances > wide.rebalances


def test_format_table_has_header_and_rows():
    prices = [100.0] * 50
    rs = [backtest.run(prices, math.log1p(w / 100), lambda x: 0.0) for w in (2, 8)]
    out = backtest.format_table(rs, 2.0)
    assert "vs HODL" in out and out.count("\n") == 2


def test_net_apr_is_on_starting_capital_not_end_hodl_value():
    prices = [2000.0 * (1 + 0.002 * i) for i in range(241)]  # +48% drift: end HODL value >> start value
    r = backtest.run(prices, math.log1p(0.5), lambda w: 0.0, start_value=10_000, gas_cost=0.0)
    assert r.start_value == 10_000 and r.hodl_value > 11_000
    apr = r.pnl_vs_hodl / 10_000 * 365 / 10 * 100
    assert f"{apr:>7.1f}%" in backtest.format_table([r], 10.0)
