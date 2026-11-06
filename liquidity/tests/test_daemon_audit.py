"""Every live path shares safety gates; capital and ownership cannot bypass them."""

from __future__ import annotations

import pytest
from test_daemon import (
    AERO,
    MAIN_TICK,
    USDC,
    WETH,
    _arm,
    _armed_compound,
    _idle,
    _low_gas_wallet,
    addr,
    make_pool,
    make_pos,
    open_slot,
    pos_worth,
    tick_for,
)
from test_daemon import (
    make_daemon as daemon_fixture,
)

from aero_lp.config import SafetyConfig


@pytest.fixture
def make_daemon(tmp_path, monkeypatch):
    return daemon_fixture.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("operation", ["convert", "claim", "collect", "unwrap", "gas_swap"])
def test_every_live_write_path_honors_zero_gas_cap(make_daemon, operation):
    d = make_daemon(live_mode=True, safety=SafetyConfig(max_gas_usd=0))
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    if operation == "convert":
        d.test.chain.add_pool(make_pool(AERO, USDC, tick_for(1e-12), address=addr(0x22)))
        d._convert_into(pool, AERO, 3 * 10**18, None)
    elif operation in ("claim", "collect"):
        _armed_compound(d, staked=operation == "claim", fees=(0, 20 * 10**6))
        d.compound_slot("42")
    else:
        d.test.chain.w3.eth.get_code = lambda a: b"code" if operation == "gas_swap" else b""
        d._gas_topup(_low_gas_wallet())
    assert not [call for call in d.rb.calls if call[1] == "live"]


def test_foreign_direct_wallet_position_is_not_registered(make_daemon):
    d = make_daemon(live_mode=True)
    pos = make_pos()
    pos.owner = addr(0xDD)
    d.test.chain.positions[42] = pos
    with pytest.raises(RuntimeError, match="owner"):
        d._register(42)
    assert d.ledger.open_slots() == []


@pytest.mark.parametrize("other_value,expected_room", [(0, 6), (5, 1)])
def test_compound_clamps_rewards_to_fresh_position_and_total_caps(make_daemon, other_value, expected_room):
    d = make_daemon(live_mode=True, max_position_usd=10, max_total_deployed_usd=10)
    _armed_compound(d, staked=True, earned=20 * 10**18)
    d.rb.claimed = 20 * 10**18
    d.rb.swap_out = 10**16  # $20 measured WETH output
    if other_value:
        open_slot(d, "43", token_id=43, pool=make_pool(WETH, USDC, MAIN_TICK, address=addr(0x33)))
        d.test.chain.positions[43] = pos_worth(43, other_value)
    d.compound_slot("42")
    topup = [call for call in d.rb.calls if call[:2] == ("topup", "live")][-1]
    assert topup[2] <= int(expected_room / 2000 * 1e18)
    assert topup[3] == 0


def test_pool_pushed_during_conversions_cannot_be_deployed(make_daemon, monkeypatch):
    d = make_daemon(live_mode=True)
    good = make_pool(WETH, USDC, MAIN_TICK)
    bad = make_pool(WETH, USDC, MAIN_TICK + 500)
    reads = []

    def pool_state(address):
        reads.append(address)
        return good if len(reads) == 1 else bad

    monkeypatch.setattr(d.test.chain, "pool_state", pool_state)
    d.engine.pool_blocks = lambda pool, live: ["TWAP"] if pool.tick == bad.tick else []
    d.deploy_arm(_arm(good, 10), [_idle(USDC, 10, 10, 6)], None)
    assert not [call for call in d.rb.calls if call[:2] == ("deploy", "live")]


def test_compound_rechecks_total_exposure_after_simulation(make_daemon, monkeypatch):
    d = make_daemon(live_mode=True, max_position_usd=10, max_total_deployed_usd=10)
    _armed_compound(d, staked=True, earned=20 * 10**18)
    d.rb.claimed = 20 * 10**18
    d.rb.swap_out = 10**16
    open_slot(d, "43", token_id=43)
    d.test.chain.positions[43] = pos_worth(43, 1)
    original = d.rb.topup

    def topup(pos, a0, a1, runner, u0, u1, **kwargs):
        result = original(pos, a0, a1, runner, u0, u1, **kwargs)
        if runner[0] == "sim":
            d.test.chain.positions[43] = pos_worth(43, 8)
        return result

    monkeypatch.setattr(d.rb, "topup", topup)
    d.compound_slot("42")
    assert not [call for call in d.rb.calls if call[:2] == ("topup", "live")]
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='topup'").fetchone()[0] == 0


def test_successful_compound_refreshes_snapshot_before_later_allocation(make_daemon, monkeypatch):
    d = make_daemon(live_mode=True, max_position_usd=10, max_total_deployed_usd=10)
    _armed_compound(d, staked=True, earned=20 * 10**18)
    d.rb.claimed = 20 * 10**18
    d.rb.swap_out = 10**16
    original = d.rb.topup

    def topup(pos, a0, a1, runner, u0, u1, **kwargs):
        assert kwargs["include_unstake_proceeds"] is False
        result = original(pos, a0, a1, runner, u0, u1, **kwargs)
        if runner[0] == "live":
            pos.amount0 += a0
            pos.amount1 += a1
        return result

    monkeypatch.setattr(d.rb, "topup", topup)
    d.compound_slot("42")
    assert d.decisions["42"]["_stale"]
    assert d.ledger.pnl("42").value_usd == pytest.approx(10)
    assert d._slot_value_usd("42") == pytest.approx(10)
    assert sum(d._capital_values().values()) == pytest.approx(10)


def test_deploy_checks_twap_after_the_simulation_too(make_daemon, monkeypatch):
    d = make_daemon(live_mode=True)
    good = make_pool(WETH, USDC, MAIN_TICK)
    bad = make_pool(WETH, USDC, MAIN_TICK + 500)
    d.test.chain.add_pool(good)
    d.engine.pool_blocks = lambda pool, live: ["TWAP"] if pool.tick == bad.tick else []
    original = d.rb.deploy

    def deploy(pool, rng, stake, a0, a1, runner, u0, u1, on_stage=None):
        result = original(pool, rng, stake, a0, a1, runner, u0, u1, on_stage=on_stage)
        if runner[0] == "sim":
            d.test.chain.add_pool(bad)
        return result

    monkeypatch.setattr(d.rb, "deploy", deploy)
    d.deploy_arm(_arm(good, 10), [_idle(USDC, 10, 10, 6)], None)
    assert [call[:2] for call in d.rb.calls] == [("deploy", "sim")]
    assert d.ledger.open_slots() == []


def test_missing_simulation_gas_evidence_refuses_write(make_daemon):
    from aero_lp.executor import RebalanceResult

    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    why = d._preflight(pool, lambda sim: RebalanceResult(None, False, [], [], {}))
    assert "did not report gas" in why


def test_preflight_never_uses_cached_price_when_feed_is_down(make_daemon):
    from aero_lp.executor import RebalanceResult

    d = make_daemon(live_mode=True)
    d.prices()  # there is a valid bookkeeping fallback
    d.test.market.down = True
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    with pytest.raises(RuntimeError, match="price feed down"):
        d._preflight(pool, lambda sim: RebalanceResult(None, False, [], [], {"tx": 100000}))


def test_successful_rebalance_snapshots_replacement_reward_balance(make_daemon):
    import time

    from test_daemon import _rebalance_result, decision_ev

    from aero_lp.strategy import Action

    d = make_daemon(live_mode=True)
    old = make_pos(earned_aero=5 * 10**18)
    new = pos_worth(900, 40)
    new.earned_aero = 0
    d.test.chain.positions.update({42: old, 900: new})
    open_slot(d)
    d.engine.script[42] = (decision_ev(old, value_usd=40, action=Action.REBALANCE), _rebalance_result(aero=5 * 10**18))
    d.manage_slot("42", time.time())
    pnl = d.ledger.pnl("42")
    assert pnl.rewards_usd == 5
    assert pnl.unclaimed_usd == 0
    assert pnl.pnl_usd + pnl.gas_usd == pytest.approx(5)
    snap = d.ledger.db.execute("SELECT token_id, unclaimed_usd FROM snapshots ORDER BY id DESC").fetchone()
    assert tuple(snap) == (900, 0)


def test_failed_rebalance_refresh_keeps_old_snapshot_identity(make_daemon):
    import time

    from test_daemon import _rebalance_result, decision_ev

    from aero_lp.strategy import Action

    d = make_daemon(live_mode=True)
    old = make_pos(earned_aero=5 * 10**18)
    open_slot(d)
    d.ledger.snapshot("42", 42, 40, 40, 5)
    d.engine.script[42] = (decision_ev(old, value_usd=40, action=Action.REBALANCE), _rebalance_result(aero=5 * 10**18))
    # The replacement NFT is not available yet. Do not invent its snapshot from the burned NFT.
    d.manage_slot("42", time.time())
    snaps = d.ledger.db.execute("SELECT token_id FROM snapshots ORDER BY id").fetchall()
    assert [row[0] for row in snaps] == [42]
    assert d.decisions["42"]["_stale"]
    assert "refresh" in d.decisions["42"]["snapshot_error"]
