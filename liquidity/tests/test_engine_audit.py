"""Live safety and interrupted-operation persistence regressions (all I/O stubbed)."""

from __future__ import annotations

import signal
import time
from types import SimpleNamespace

import pytest
from test_engine import chain_stub, make_engine, make_ev
from test_executor import make_position

from aero_lp import addresses
from aero_lp import engine as module
from aero_lp.executor import RebalanceResult


def setup_live(eng, monkeypatch, *, eth_usd=2000):
    pos = make_position(False)
    pos.pool.timestamp = time.time()
    pos.pool.tick = -199000
    eng.chain = chain_stub(pos)
    eng.gate = None
    eng.on_stop = None
    eng.market = SimpleNamespace(
        token_prices_usd=lambda tokens: {
            addresses.WETH.lower(): eth_usd,
            pos.pool.token1.address.lower(): 1,
        }
    )
    eng.twap_deviation_bps = lambda p: 1
    monkeypatch.setattr(module, "SimRunner", lambda *a: "sim")
    monkeypatch.setattr(module, "LiveRunner", lambda *a, **kw: "live")
    return pos


def test_fresh_position_above_cap_never_reaches_live_runner(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    pos = setup_live(eng, monkeypatch)
    pos.amount0, pos.amount1 = 100 * 10**18, 100 * 10**6
    calls = []

    def run(*a, **kw):
        calls.append(a[3])
        return RebalanceResult(777, False, ["mint"], [], {"mint": 100000})

    monkeypatch.setattr(module, "Rebalancer", lambda *a: SimpleNamespace(rebalance=run))
    with pytest.raises(RuntimeError, match="max_position_usd"):
        eng.rebalance(make_ev(), True, object())
    assert calls == ["sim"]


@pytest.mark.parametrize("quote", [float("nan"), float("inf"), -1, 0])
def test_invalid_market_eth_quote_cannot_withdraw_live(tmp_path, monkeypatch, quote):
    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch, eth_usd=quote)
    calls = []

    def run(pos, runner):
        calls.append(runner)
        return RebalanceResult(None, False, ["remove"], ["0xhash"], {"remove": 100000})

    monkeypatch.setattr(module, "Rebalancer", lambda *a: SimpleNamespace(withdraw=run))
    with pytest.raises(RuntimeError, match="ETH price"):
        eng.withdraw(42, True, object())
    assert calls == ["sim"]


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_deferred_stop_persists_successful_withdraw(tmp_path, monkeypatch, sig):
    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch)
    slot = eng.state.slot(42)

    def run(pos, runner):
        if runner == "live":
            signal.raise_signal(sig)
        return RebalanceResult(None, False, ["remove"], ["0xhash"], {"remove": 100000})

    monkeypatch.setattr(module, "Rebalancer", lambda *a: SimpleNamespace(withdraw=run))
    with pytest.raises((KeyboardInterrupt, SystemExit)):
        eng.withdraw(42, True, object())
    assert slot.history[-1]["tx"] == ["0xhash"]


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_deferred_stop_persists_rebalance_history_and_cooldown(tmp_path, monkeypatch, sig):
    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch)
    monkeypatch.setattr(eng, "evaluate", lambda slot: make_ev())

    def run(*args, **kw):
        if args[3] == "live":
            signal.raise_signal(sig)
        return RebalanceResult(777, False, ["mint"], ["0xhash"], {"mint": 100000})

    monkeypatch.setattr(module, "Rebalancer", lambda *a: SimpleNamespace(rebalance=run))
    with pytest.raises((KeyboardInterrupt, SystemExit)):
        eng.step(42, True, object())
    slot = eng.state.slot(42)
    assert slot.history[-1]["tx"] == ["0xhash"]
    assert slot.current_token_id == 777 and slot.last_rebalance_ts is not None
