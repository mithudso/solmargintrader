"""Engine safety gates and partial-failure bookkeeping, with the chain and market stubbed out."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from aero_lp import addresses
from aero_lp import engine as engine_mod
from aero_lp.config import Config, SafetyConfig
from aero_lp.engine import Engine
from aero_lp.executor import RebalanceError, RebalanceResult
from aero_lp.state import State
from aero_lp.strategy import Action, Decision, Range

OWNER = "0x" + "ab" * 20
NEW_RANGE = Range(-199700, -198700)


def make_engine(tmp_path, **safety) -> Engine:
    cfg = Config(OWNER, [42], state_path=str(tmp_path / "state.json"), safety=SafetyConfig(**safety))
    eng = Engine.__new__(Engine)
    eng.cfg, eng.state = cfg, State(cfg.state_file)
    return eng


def chain_stub(fresh, balance=10**18):
    return SimpleNamespace(
        gas_price_wei=lambda: 10**6,
        check_fresh=lambda: 1,
        position=lambda *a, **k: fresh,
        w3=SimpleNamespace(eth=SimpleNamespace(get_balance=lambda a: balance)),
    )


def make_ev(**kw):
    base = dict(
        twap_deviation_bps=5.0,
        value_usd=1000.0,
        gas_usd=0.1,
        eth_usd=2000.0,
        econ=SimpleNamespace(price0_usd=2000.0, price1_usd=1.0),
        pos=SimpleNamespace(
            token_id=42,
            pool=SimpleNamespace(
                address="0x" + "11" * 20,
                token0=SimpleNamespace(address=addresses.WETH),
                token1=SimpleNamespace(address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
            ),
        ),
        decision=Decision(Action.REBALANCE, "test", NEW_RANGE),
        notes=[],
        stake_new=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_clean_evaluation_passes_live_safety(tmp_path):
    assert make_engine(tmp_path).safety_blocks(make_ev(), live=True) == []


@pytest.mark.parametrize(
    "override, needle",
    [
        ({"twap_deviation_bps": None}, "TWAP unavailable"),
        ({"twap_deviation_bps": 500.0}, "from the 10-min TWAP"),
        ({"econ": SimpleNamespace(price0_usd=0.0, price1_usd=1.0)}, "missing USD price"),
        ({"eth_usd": 0.0}, "missing USD price"),
        ({"value_usd": 50_000.0}, "max_position_usd"),
        ({"gas_usd": 9.0}, "max_gas_usd"),
    ],
)
def test_live_mode_fails_closed(tmp_path, override, needle):
    blocks = make_engine(tmp_path).safety_blocks(make_ev(**override), live=True)
    assert any(needle in b for b in blocks), blocks


def test_dry_run_only_reports_unknown_twap_and_missing_prices(tmp_path):
    eng = make_engine(tmp_path)
    assert eng.safety_blocks(make_ev(twap_deviation_bps=None, eth_usd=0.0), live=False) == []
    assert eng.safety_blocks(make_ev(twap_deviation_bps=500.0), live=False)  # a real deviation still blocks


def _step_with(eng: Engine, monkeypatch, rebalance):
    ev = make_ev()
    monkeypatch.setattr(eng, "evaluate", lambda slot: ev)
    monkeypatch.setattr(eng, "rebalance", rebalance)
    return ev


def test_failed_stake_keeps_tracking_the_minted_nft(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    partial = RebalanceResult(777, False, ["unstake", "remove", "mint"], ["0xaa", "0xbb"], {})

    def boom(ev, live, signer=None, on_stage=None):
        raise RebalanceError("rebalance failed after stage 'mint': stake reverted", partial)

    _step_with(eng, monkeypatch, boom)
    with pytest.raises(RebalanceError):
        eng.step(42, live=True, signer=object())
    slot = eng.state.slot(42)
    assert slot.current_token_id == 777 and slot.last_rebalance_ts is not None
    assert slot.history[-1]["error"].startswith("rebalance failed") and slot.history[-1]["tx"] == ["0xaa", "0xbb"]
    saved = json.loads((tmp_path / "state.json").read_text())
    assert saved["slots"]["42"]["current_token_id"] == 777  # persisted before the error propagated


def test_failure_before_any_broadcast_changes_no_state(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)

    def boom(ev, live, signer=None, on_stage=None):
        raise RebalanceError(
            "rebalance failed after stage 'start': sim reverted", RebalanceResult(None, False, [], [], {})
        )

    _step_with(eng, monkeypatch, boom)
    with pytest.raises(RebalanceError):
        eng.step(42, live=True, signer=object())
    slot = eng.state.slot(42)
    assert slot.current_token_id == 42 and slot.history == []


def test_unstake_then_failure_keeps_old_token_id_but_records_hashes(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    partial = RebalanceResult(None, False, ["unstake"], ["0xaa"], {})

    def boom(ev, live, signer=None, on_stage=None):
        raise RebalanceError("rebalance failed after stage 'unstake': remove reverted", partial)

    _step_with(eng, monkeypatch, boom)
    with pytest.raises(RebalanceError):
        eng.step(42, live=True, signer=object())
    slot = eng.state.slot(42)
    assert slot.current_token_id == 42 and slot.last_rebalance_ts is None
    assert slot.history[-1]["tx"] == ["0xaa"] and slot.history[-1]["new"] is None


def test_live_rebalance_refuses_when_simulated_gas_exceeds_limit(tmp_path, monkeypatch):
    eng = make_engine(tmp_path, max_gas_usd=1.0)
    eng.chain = SimpleNamespace(gas_price_wei=lambda: 10**9)  # 1 gwei
    sim = RebalanceResult(1, True, [], [], {"all": 3_000_000})  # 3M gas * 1 gwei * $2000 = $6 + $0.05 L1
    monkeypatch.setattr(engine_mod, "Rebalancer", lambda *a: SimpleNamespace(rebalance=lambda *x: sim))
    monkeypatch.setattr(engine_mod, "SimRunner", lambda *a: None)
    ev = make_ev()
    with pytest.raises(RuntimeError, match="simulated gas"):
        eng.rebalance(ev, live=True, signer=object())


def test_live_rebalance_rechecks_twap_on_fresh_state(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    fresh = SimpleNamespace(token_id=42, owner=OWNER, pool=SimpleNamespace(timestamp=time.time(), tick=-199000))
    eng.chain = chain_stub(fresh)
    sim = RebalanceResult(1, True, [], [], {"all": 1_000_000})
    monkeypatch.setattr(engine_mod, "Rebalancer", lambda *a: SimpleNamespace(rebalance=lambda *x: sim))
    monkeypatch.setattr(engine_mod, "SimRunner", lambda *a: None)
    monkeypatch.setattr(eng, "twap_deviation_bps", lambda pos: 400.0)  # price jumped after evaluate()
    ev = make_ev()
    with pytest.raises(RuntimeError, match="blocked before broadcast"):
        eng.rebalance(ev, live=True, signer=object())


def test_live_rebalance_rejects_foreign_owner(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    fresh = SimpleNamespace(token_id=42, owner="0x" + "cd" * 20)
    eng.chain = chain_stub(fresh)
    sim = RebalanceResult(1, True, [], [], {"all": 1_000_000})
    monkeypatch.setattr(engine_mod, "Rebalancer", lambda *a: SimpleNamespace(rebalance=lambda *x: sim))
    monkeypatch.setattr(engine_mod, "SimRunner", lambda *a: None)
    ev = make_ev()
    with pytest.raises(RuntimeError, match="not the configured owner"):
        eng.rebalance(ev, live=True, signer=object())


def test_force_is_refused_in_live_mode(tmp_path):
    with pytest.raises(ValueError, match="only allowed for dry runs"):
        make_engine(tmp_path).step(42, live=True, signer=object(), force=True)


def _live_setup(eng, monkeypatch, fresh, balance=10**18):
    eng.chain = chain_stub(fresh, balance)
    sim = RebalanceResult(1, True, [], [], {"all": 1_000_000})
    monkeypatch.setattr(engine_mod, "Rebalancer", lambda *a: SimpleNamespace(rebalance=lambda *x: sim))
    monkeypatch.setattr(engine_mod, "SimRunner", lambda *a: None)
    monkeypatch.setattr(eng, "twap_deviation_bps", lambda pos: 1.0)


def test_live_rebalance_needs_a_gas_reserve(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    fresh = SimpleNamespace(token_id=42, owner=OWNER, pool=SimpleNamespace(timestamp=time.time(), tick=-199000))
    _live_setup(eng, monkeypatch, fresh, balance=10**9)  # 1e-9 ETH
    with pytest.raises(RuntimeError, match="gas reserve"):
        eng.rebalance(make_ev(), live=True, signer=object())


def test_live_rebalance_refuses_stale_or_moved_state(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    stale = SimpleNamespace(token_id=42, owner=OWNER, pool=SimpleNamespace(timestamp=time.time() - 600, tick=-199000))
    _live_setup(eng, monkeypatch, stale)
    with pytest.raises(RuntimeError, match="stale"):
        eng.rebalance(make_ev(), live=True, signer=object())
    moved = SimpleNamespace(token_id=42, owner=OWNER, pool=SimpleNamespace(timestamp=time.time(), tick=0))
    _live_setup(eng, monkeypatch, moved)
    with pytest.raises(RuntimeError, match="left the proposed range"):
        eng.rebalance(make_ev(), live=True, signer=object())


def test_defer_sigint_holds_ctrl_c_until_the_block_ends():
    import os
    import signal

    from aero_lp.engine import defer_sigint

    finished = []
    with pytest.raises(KeyboardInterrupt), defer_sigint():
        os.kill(os.getpid(), signal.SIGINT)
        finished.append(True)  # still runs: the interrupt is deferred
    assert finished == [True]


def test_new_token_id_hits_disk_the_moment_the_mint_lands(tmp_path, monkeypatch):
    """A hard crash right after the mint (here SystemExit, not a RebalanceError) must not lose the new NFT."""
    eng = make_engine(tmp_path)

    def mint_then_die(ev, live, signer=None, on_stage=None):
        on_stage("remove", RebalanceResult(None, False, ["remove"], ["0xaa"], {}))
        on_stage("mint", RebalanceResult(888, False, ["remove", "mint"], ["0xaa", "0xbb"], {}))
        raise SystemExit("killed between mint and stake")

    _step_with(eng, monkeypatch, mint_then_die)
    with pytest.raises(SystemExit):
        eng.step(42, live=True, signer=object())
    saved = json.loads((tmp_path / "state.json").read_text())
    assert saved["slots"]["42"]["current_token_id"] == 888


def test_dry_run_hook_never_touches_state(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)

    def sim(ev, live, signer=None, on_stage=None):
        on_stage("mint", RebalanceResult(999, False, ["remove", "mint"], [], {}))
        return RebalanceResult(999, False, ["remove", "mint"], [], {})

    _step_with(eng, monkeypatch, sim)
    eng.step(42, live=False)
    assert eng.state.slot(42).current_token_id == 42
