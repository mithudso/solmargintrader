"""Earnings model, volatility estimate, price cache and state file (offline)."""

import json
import math

import httpx
import pytest

from aero_lp import clmath
from aero_lp.market import (
    STABLES,
    MarketData,
    PoolEconomics,
    earn_usd_per_day,
    liquidity_for_usd,
    vol_from_closes,
)
from aero_lp.state import State

WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def econ(**kw) -> PoolEconomics:
    base = dict(
        volume_usd_per_day=1_000_000.0,
        fee=0.0005,
        unstaked_fee_share=0.1,
        aero_per_day=1000.0,
        aero_usd=0.5,
        active_liquidity=9 * 10**18,
        staked_liquidity=4 * 10**18,
        price0_usd=2000.0,
        price1_usd=1.0,
        dec0=18,
        dec1=6,
    )
    base.update(kw)
    return PoolEconomics(**base)


def test_earn_staked_is_share_of_emissions():
    e = econ()
    # a new 1e18 deposit joins 4e18 of staked liquidity -> 20% of 1000 AERO * $0.5
    assert earn_usd_per_day(10**18, True, True, e, already_counted=False) == pytest.approx(100.0)
    # an existing deposit is already inside the 4e18 -> 25%
    assert earn_usd_per_day(10**18, True, True, e, already_counted=True) == pytest.approx(125.0)


def test_earn_unstaked_is_share_of_net_fees():
    e = econ()
    fees = 1_000_000 * 0.0005 * (1 - 0.1)  # volume * fee * (1 - diverted share)
    assert earn_usd_per_day(10**18, False, True, e, already_counted=False) == pytest.approx(fees * 0.1)


def test_earn_is_zero_out_of_range_or_without_liquidity():
    e = econ()
    assert earn_usd_per_day(10**18, True, False, e, already_counted=True) == 0.0
    assert earn_usd_per_day(0, False, True, e, already_counted=True) == 0.0


def test_liquidity_for_usd_round_trips_to_the_requested_value():
    e = econ()
    tick = -199211
    sp = clmath.get_sqrt_ratio_at_tick(tick)
    tl, tu = -200100, -198300
    liq = liquidity_for_usd(25_000.0, sp, tl, tu, e)
    a0, a1 = clmath.get_amounts_for_liquidity(
        sp, clmath.get_sqrt_ratio_at_tick(tl), clmath.get_sqrt_ratio_at_tick(tu), liq
    )
    assert a0 / 1e18 * 2000.0 + a1 / 1e6 * 1.0 == pytest.approx(25_000.0, rel=1e-6)
    # out of range on the low side: the deposit is all token0
    assert liquidity_for_usd(1000.0, clmath.get_sqrt_ratio_at_tick(tl - 500), tl, tu, e) > 0


def test_vol_from_closes_scales_hourly_to_daily():
    closes = [100.0 * (1.01 if i % 2 else 1.0) for i in range(49)]  # alternating +1% / -0.99%
    rets = [math.log(closes[i + 1] / closes[i]) for i in range(48)]
    mean = sum(rets) / 48
    hourly = math.sqrt(sum((r - mean) ** 2 for r in rets) / 47)
    assert vol_from_closes(closes) == pytest.approx(hourly * math.sqrt(24))
    assert vol_from_closes(closes, step_hours=4) == pytest.approx(hourly * math.sqrt(6))
    assert vol_from_closes([1.0] * 5) is None  # too short


def _market(handler) -> MarketData:
    return MarketData(ttl=60, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_token_prices_skip_stables_and_use_the_cache():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        return httpx.Response(200, json={"data": {"attributes": {"token_prices": {WETH: "2500.5", "0xdead": None}}}})

    m = _market(handler)
    prices = m.token_prices_usd([WETH.upper().replace("0X", "0x"), USDC])
    assert prices == {USDC: 1.0, WETH: 2500.5}
    assert USDC in STABLES and USDC not in calls[0]  # stables are never asked for
    m.token_prices_usd([WETH, USDC])
    assert len(calls) == 1  # second call served from the cache


def test_market_retries_on_429_then_raises(monkeypatch):
    monkeypatch.setattr("aero_lp.market.time.sleep", lambda s: None)
    n = {"c": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        n["c"] += 1
        return httpx.Response(429)

    with pytest.raises(RuntimeError, match="rate limited"):
        _market(handler)._get("https://example.test/x")
    assert n["c"] == 4


def test_state_round_trip_and_atomic_file(tmp_path):
    path = tmp_path / "sub" / "state.json"
    st = State(path)
    slot = st.slot(7)
    slot.current_token_id, slot.edge_checks, slot.last_rebalance_ts = 99, 2, 1000.0
    slot.history.append({"old": 7, "new": 99})
    st.save()
    assert [p.name for p in path.parent.iterdir()] == ["state.json"]  # no temp file left behind
    again = State(path).slot(7)
    assert (again.current_token_id, again.edge_checks, again.last_rebalance_ts) == (99, 2, 1000.0)
    assert again.history == [{"old": 7, "new": 99}]
    assert json.loads(path.read_text())["slots"]["7"]["current_token_id"] == 99
    assert again.minutes_since_rebalance(now=1000.0 + 600) == pytest.approx(10.0)
    assert State(path).slot(8).current_token_id == 8  # a new slot starts at its configured id
