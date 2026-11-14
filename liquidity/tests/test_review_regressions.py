"""Synthetic regression counterexamples from the whole-source review. No external I/O."""

import json
import math
import os

import pytest

from aero_lp import backtest, gates, state, strategy, wallet
from aero_lp.config import Config


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, 0.0])
def test_backtest_refuses_invalid_observations(bad):
    with pytest.raises(ValueError):
        backtest.run([100.0, bad, 100.0], 0.05, lambda width: 0.0)


def test_backtest_cannot_borrow_after_capital_exhaustion():
    result = backtest.run([100.0, 120.0, 80.0, 120.0], 0.05, lambda width: 0.0, start_value=1.0, gas_cost=10.0)
    assert result.final_value >= 0
    assert result.rebalances == 0
    assert result.exhausted


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_economics_cannot_authorize_rebalance(bad):
    with pytest.raises(ValueError):
        strategy.EarnInputs(bad, 0.0)
    with pytest.raises(ValueError):
        strategy.CostInputs(1000.0, bad, 0.1, 0.5)


def test_clipped_range_never_excludes_current_tick():
    with pytest.raises(ValueError, match="tick"):
        strategy.target_range(887272, 100, 0.05)


def test_failed_json_replace_preserves_original_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    state.atomic_write_json(path, {"old": 1})
    before = path.read_bytes()
    monkeypatch.setattr(state.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("full")))
    with pytest.raises(OSError):
        state.atomic_write_json(path, {"new": 2})
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), "1", True])
def test_invalid_persisted_cooldown_fails_before_decision(tmp_path, bad):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"slots": {"7": {"current_token_id": 7, "last_rebalance_ts": bad}}}))
    with pytest.raises(ValueError):
        state.State(path)


def test_key_loader_rejects_fifo_without_blocking(tmp_path):
    path = tmp_path / "synthetic-fifo"
    os.mkfifo(path, 0o600)
    with pytest.raises(wallet.WalletError, match="regular"):
        wallet._from_file(str(path))


def test_key_loader_bounds_content(tmp_path):
    path = tmp_path / "synthetic-input"
    path.write_text("x" * 4096)
    path.chmod(0o600)
    with pytest.raises(wallet.WalletError, match="large"):
        wallet._from_file(str(path))


def test_soak_does_not_double_credit_backward_clock(tmp_path):
    cfg = Config("0x" + "ab" * 20)
    for now in (1000, 2800, 1000, 2800):
        doc = gates.record_dry_run_tick(tmp_path, cfg, now)
    assert math.isclose(doc["accumulated_s"], 1800)
