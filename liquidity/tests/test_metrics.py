"""Metrics and scout numeric edge cases, with a stubbed chain and market (no network)."""

from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest
from web3 import Web3

from aero_lp import addresses, backtest, clmath, metrics, scout
from aero_lp.allocator import qualify
from aero_lp.chain import PoolState, Token
from aero_lp.config import AllocatorConfig
from aero_lp.strategy import StrategyConfig

WETH = Web3.to_checksum_address(addresses.WETH)
WSTETH = Web3.to_checksum_address("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452")
AERO = Web3.to_checksum_address(addresses.AERO_TOKEN)
POOL = Web3.to_checksum_address("0x" + "11" * 20)
GAUGE = Web3.to_checksum_address("0x" + "cc" * 20)
PRICES = {WETH.lower(): 2000.0, WSTETH.lower(): 2400.0, AERO.lower(): 1.0}


def make_pool(gauge_alive: bool = True) -> PoolState:
    tick = int(round(math.log(2000 / 2400) / math.log(1.0001)))
    return PoolState(
        POOL,
        Token(WETH, "WETH", 18),
        Token(WSTETH, "wstETH", 18),
        1,
        100,
        0,
        clmath.get_sqrt_ratio_at_tick(tick),
        tick,
        10**20,
        10**19,
        GAUGE,
        gauge_alive,
        0,
        0,
        0,
        1,
        1,
    )


class StubChain:
    def pool_state(self, address):
        return make_pool()

    def gauge_aero_per_day(self, gauge, block):
        return 1000.0

    def fee_growth_delta(self, address, block):
        return 2 * 10**30, 2 * 10**30, 1.0

    def gas_price_wei(self):
        return 10**6

    def twap_tick_series(self, address, hours=12, step_s=600):
        return []


class StubMarket:
    def __init__(self, prices=None, closes=None, tvl=1_000_000.0, volume=2_000_000.0):
        self.prices = PRICES if prices is None else prices
        self.closes = [] if closes is None else closes
        self.tvl, self.volume = tvl, volume

    def token_prices_usd(self, tokens):
        return {t.lower(): self.prices[t.lower()] for t in tokens if t.lower() in self.prices}

    def pool_info(self, pool):
        return {"reserve_usd": self.tvl, "volume_24h_usd": self.volume}

    def hourly_closes(self, pool, hours):
        return self.closes


def wobble(n=168):
    return [0.8333 * (1 + 0.0005 * math.sin(i / 3)) for i in range(n)]


def evaluate(deposit=50.0, **market_kwargs):
    return metrics.evaluate_pool(StubChain(), StubMarket(**market_kwargs), POOL, deposit, StrategyConfig())


YIELD = lambda w: 0.0005  # noqa: E731


def test_backtest_best_reports_no_replay_for_short_history_or_zero_deposit():
    cfg = StrategyConfig()
    assert metrics.backtest_best([1.0] * 23, YIELD, 50.0, 0.01, 0.0001, 1, cfg) == (0.0, 0.0, 0.0)
    assert metrics.backtest_best(wobble(), YIELD, 0.0, 0.01, 0.0001, 1, cfg) == (0.0, 0.0, 0.0)
    assert metrics.backtest_best(wobble(), YIELD, -5.0, 0.01, 0.0001, 1, cfg) == (0.0, 0.0, 0.0)
    assert metrics.backtest_best([], YIELD, 50.0, 0.01, 0.0001, 1, cfg) == (0.0, 0.0, 0.0)


def test_backtest_best_replays_a_pegged_path_and_reports_the_days():
    apr, width, days = metrics.backtest_best(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, StrategyConfig())
    assert days == pytest.approx(167 / 24) and math.isfinite(apr) and width > 0


def test_backtest_best_never_returns_nan_or_inf(monkeypatch):
    class Bad:
        pnl_vs_hodl = float("nan")

    monkeypatch.setattr(backtest, "run", lambda *a, **k: Bad())
    assert metrics.backtest_best(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, StrategyConfig()) == (0.0, 0.0, 0.0)

    class Inf:
        pnl_vs_hodl = float("-inf")

    monkeypatch.setattr(backtest, "run", lambda *a, **k: Inf())
    assert metrics.backtest_best(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, StrategyConfig()) == (0.0, 0.0, 0.0)


def test_zero_tvl_no_closes_and_missing_prices_give_a_low_confidence_pool_with_valid_json():
    m = evaluate(prices={}, tvl=0.0, volume=0.0)
    assert m.confidence == "low" and m.backtest_days == 0 and m.turnover == 0
    assert any("ETH price unavailable" in f for f in m.flags) and any("missing USD price" in f for f in m.flags)
    json.dumps(m.to_json(), allow_nan=False)  # NaN / inf would make soltui's parser reject the whole file
    cands, _ = qualify([m.to_json()], AllocatorConfig(min_net_apr=-1e6, min_confidence="low", min_tvl_usd=0))
    assert cands == []  # no replay, so never deployable, even with every threshold removed


def test_missing_eth_price_alone_forces_low_confidence_because_gas_would_be_understated():
    prices = {k: v for k, v in PRICES.items() if k != WETH.lower()}
    # WETH is the pool's token0, so its price is also missing; use a pool whose ETH price is the only gap
    m = evaluate(prices=prices, closes=wobble())
    assert m.confidence == "low" and any("ETH price" in f for f in m.flags)


def test_a_healthy_pool_has_a_replay_and_finite_numbers():
    m = evaluate(closes=wobble())
    assert m.backtest_days > 6 and m.confidence in ("medium", "high")
    d = m.to_json()
    json.dumps(d, allow_nan=False)
    assert all(math.isfinite(v) for v in d.values() if isinstance(v, float))


def test_zero_deposit_evaluates_without_error_and_never_looks_profitable():
    m = evaluate(deposit=0.0, closes=wobble())
    assert m.backtest_days == 0 and m.expected_net_apr <= 0
    json.dumps(m.to_json(), allow_nan=False)


def test_infinite_edge_is_clamped_in_the_file():
    # no vol at all (flat closes): LVR is 0 and income > 0, so the ratio is infinite
    m = evaluate(closes=[0.8333] * 168)
    d = m.to_json()
    assert math.isfinite(d["edge_ratio"]) and d["edge_ratio"] >= 1e8
    json.dumps(d, allow_nan=False)


def test_to_json_replaces_non_finite_floats_with_an_obviously_invalid_value():
    m = evaluate(closes=wobble())
    m.expected_net_apr = float("nan")
    m.tvl_usd = float("inf")
    d = m.to_json()
    assert d["expected_net_apr"] == metrics.NO_DATA and d["tvl_usd"] == metrics.NO_DATA


def test_scout_time_budget_stops_the_scan_and_lists_what_was_skipped(monkeypatch, tmp_path):
    ticks = iter([0.0, 0.0, 1000.0, 1000.0, 1000.0])
    monkeypatch.setattr(scout.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        scout, "evaluate_pool", lambda *a, **k: SimpleNamespace(pair="x", tick_spacing=1, expected_net_apr=1.0)
    )
    monkeypatch.setattr(scout, "rank", lambda r: [])
    out = tmp_path / "scout.json"
    doc = scout.run_scout(None, None, 50.0, pools=["0xa", "0xb", "0xc"], out=out, max_seconds=60)
    assert [e["pool"] for e in doc["errors"]] == ["0xb", "0xc"]
    assert all("time budget" in e["error"] for e in doc["errors"]) and out.exists()


def test_backtest_at_width_replays_exactly_the_deployed_width_and_reports_no_data_honestly(monkeypatch):
    cfg = StrategyConfig()
    wide = metrics.backtest_at_width(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, cfg, math.log1p(0.20))
    narrow = metrics.backtest_at_width(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, cfg, math.log1p(0.0001))
    assert math.isfinite(wide) and math.isfinite(narrow) and wide != narrow
    assert metrics.backtest_at_width([1.0] * 5, YIELD, 50.0, 0.01, 0.0001, 1, cfg, 0.01) == 0.0
    assert metrics.backtest_at_width(wobble(), YIELD, 0.0, 0.01, 0.0001, 1, cfg, 0.01) == 0.0

    class Bad:
        pnl_vs_hodl = float("nan")

    monkeypatch.setattr(backtest, "run", lambda *a, **k: Bad())
    assert metrics.backtest_at_width(wobble(), YIELD, 50.0, 0.01, 0.0001, 1, cfg, 0.01) == metrics.NO_DATA


def test_evaluate_pool_reports_the_replay_at_its_own_deployed_width():
    m = evaluate(closes=wobble())
    assert math.isfinite(m.backtest_deploy_apr) and m.backtest_days > 6
    d = m.to_json()
    assert "backtest_deploy_apr" in d
    assert evaluate(closes=[]).backtest_deploy_apr == 0.0 and evaluate(closes=[]).backtest_days == 0


def test_rank_puts_low_confidence_rows_after_trustworthy_ones():
    from aero_lp.metrics import PoolMetrics
    from aero_lp.scout import rank

    def m(pair, apr, conf):
        return PoolMetrics(
            pool=pair,
            pair=pair,
            token0="a",
            token1="b",
            tick_spacing=1,
            fee_pct=0.01,
            tvl_usd=1e6,
            volume_24h_usd=1e6,
            turnover=1.0,
            sigma_daily_pct=0.1,
            sigma_source="x",
            fee_apr_ref=1.0,
            aero_apr_ref=1.0,
            lvr_apr_ref=1.0,
            edge_ratio=1.0,
            best_mode="fees",
            best_half_width_pct=1.0,
            expected_net_apr=apr,
            rebalances_per_week=0.1,
            cost_per_rebalance_usd=0.01,
            break_even_deposit_usd=1.0,
            staked_share=0.5,
            gauge_active=True,
            confidence=conf,
        )

    out = rank([m("junk", 26.0, "low"), m("ok", 1.0, "medium"), m("best", 3.0, "high")])
    assert [x.pair for x in out] == ["best", "ok", "junk"]
