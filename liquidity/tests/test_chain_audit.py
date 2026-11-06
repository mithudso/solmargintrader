"""Pinned-state, economic ownership and unknown-penalty regressions."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from test_executor import GAUGE, OWNER, T0, T1, make_position

from aero_lp import chain as module
from aero_lp.chain import AeroChain


def staked_chain(*, membership=True, penalty=(100, 5000), denominator=10000, earned=5 * 10**18):
    pos = make_position(True)
    pos.pool.block = 100
    c = AeroChain.__new__(AeroChain)
    c.npm = c.gauge_factory = SimpleNamespace()
    c.head = lambda: (100, int(time.time()))
    c.pool_address = lambda *a: pos.pool.address
    c.pool_state = lambda *a, **k: pos.pool
    c._c = c.gauge_contract = lambda *a: SimpleNamespace()
    seen = []
    values = {
        "positions": (0, OWNER, T0, T1, 100, pos.tick_lower, pos.tick_upper, pos.liquidity, 0, 0, 0, 0),
        "ownerOf": GAUGE,
        "ticks": (0, 0, 0, 0, 0, 0, 0, 0, True),
        "depositBlock": 90,
        "effectivePenaltyConfig": penalty,
        "MAX_PIPS": denominator,
        "earned": earned,
        "deferredEmissions": 0,
        "stakedContains": membership,
    }

    def multicall(calls, block="latest"):
        seen.extend((call.fn, block) for call in calls)
        return [values[call.fn] for call in calls]

    c.multicall = multicall
    return c, seen


def test_head_pins_at_our_receipt_and_retries_lagging_nodes(monkeypatch):
    monkeypatch.setattr(module, "MIN_BLOCK_READ_DELAY_S", 0)
    c = AeroChain.__new__(AeroChain)
    c.min_block = 100
    asked = []

    def block(tag):
        asked.append(tag)
        if tag == "latest":
            return {"number": 99, "timestamp": time.time()}
        if asked.count(100) < 3:
            raise ValueError("header not found")
        return {"number": 100, "timestamp": time.time()}

    c.w3 = SimpleNamespace(eth=SimpleNamespace(get_block=block))
    assert c.head()[0] == 100
    assert asked == ["latest", 100, 100, 100]


def test_old_postmint_snapshot_cannot_prove_position_gone(monkeypatch):
    monkeypatch.setattr(module, "MIN_BLOCK_READ_DELAY_S", 0)
    c = AeroChain.__new__(AeroChain)
    c.min_block = 100
    c.npm = SimpleNamespace()

    def block(tag):
        if tag != "latest":
            raise ValueError("header not found")
        return {"number": 99, "timestamp": time.time()}

    c.w3 = SimpleNamespace(eth=SimpleNamespace(get_block=block))
    c.multicall = lambda calls, block: [None, None]
    with pytest.raises(RuntimeError, match="at or after block 100"):
        c.position(777, owner_hint=OWNER)


def test_foreign_staked_hint_is_not_an_economic_owner():
    c, seen = staked_chain(membership=False)
    with pytest.raises(RuntimeError, match="not staked by"):
        c.position(42, owner_hint=OWNER)
    assert ("stakedContains", 100) in seen


@pytest.mark.parametrize("penalty,denominator", [(None, 10000), ((100, 5000), None), ((100, 5000), 0)])
def test_unknown_or_invalid_penalty_cannot_become_zero(penalty, denominator):
    c, _ = staked_chain(penalty=penalty, denominator=denominator)
    with pytest.raises(RuntimeError, match="penalty"):
        c.position(42, owner_hint=OWNER)


@pytest.mark.parametrize("membership", [False, None])
def test_staked_membership_must_be_positive_evidence(membership):
    c, _ = staked_chain(membership=membership)
    with pytest.raises(RuntimeError, match="not staked by"):
        c.position(42, owner_hint=OWNER)


@pytest.mark.parametrize("penalty,denominator", [((100, -1), 10000), ((100, 10001), 10000), ((-1, 0), 10000)])
def test_penalty_bounds_are_validated(penalty, denominator):
    c, _ = staked_chain(penalty=penalty, denominator=denominator)
    with pytest.raises(RuntimeError, match="penalty"):
        c.position(42, owner_hint=OWNER)


def test_verified_staked_owner_retains_measured_active_penalty():
    c, seen = staked_chain()
    pos = c.position(42, owner_hint=OWNER)
    assert pos.owner == OWNER and pos.staked
    assert pos.penalty_blocks_left == 90 and pos.penalty_rate == 0.5
    assert all(block == 100 for _, block in seen)


def test_explicit_zero_penalty_is_allowed():
    c, _ = staked_chain(penalty=(0, 0))
    pos = c.position(42, owner_hint=OWNER)
    assert pos.penalty_blocks_left == 0 and pos.penalty_rate == 0


def test_unknown_accrued_reward_cannot_erase_early_exit_cost():
    c, _ = staked_chain(earned=None)
    with pytest.raises(RuntimeError, match="reward"):
        c.position(42, owner_hint=OWNER)
