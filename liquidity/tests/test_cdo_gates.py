"""Offline regressions for finite, durable pre-live evidence."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import Event

import pytest

from aero_lp import gates
from aero_lp.config import Config, load
from aero_lp.strategy import StrategyConfig

OWNER = "0x" + "ab" * 20


@pytest.mark.parametrize("field", [k for k in asdict(StrategyConfig()) if k != "width_mode"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "1"])
def test_strategy_numeric_fields_refuse_invalid_evidence(field, value):
    with pytest.raises(ValueError, match=field):
        StrategyConfig(**{field: value})


def test_strategy_toml_refuses_nonfinite_and_fractional_confirmations(tmp_path):
    path = tmp_path / "config.toml"
    for setting in ("benefit_cost_ratio = nan", "cooldown_minutes = nan", "confirm_checks = 1.5"):
        path.write_text(f'owner = "{OWNER}"\n[strategy]\n{setting}\n')
        with pytest.raises(ValueError):
            load(path)
    assert StrategyConfig(cooldown_minutes=0, benefit_cost_ratio=0, lvr_weight=0).cooldown_minutes == 0


@pytest.mark.parametrize("field", ["accumulated_s", "started_at", "last_tick_at"])
@pytest.mark.parametrize("value", [float("inf"), float("nan"), True, "Infinity", -1])
def test_corrupt_soak_evidence_never_opens_gate(tmp_path, field, value):
    cfg = Config(OWNER)
    doc = gates.record_dry_run_tick(tmp_path, cfg, now=1)
    doc.update(accumulated_s=100000)
    doc[field] = value
    (tmp_path / "soak.json").write_text(json.dumps(doc))
    assert not gates.soak_status(tmp_path, cfg).ok


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2", -1])
def test_corrupt_research_timestamp_cannot_fall_back_to_pass(tmp_path, value):
    cfg = Config(OWNER)
    path = gates.research_path(tmp_path, cfg)
    path.write_text(
        json.dumps(
            {
                "schema": gates.RESEARCH_SCHEMA,
                "results": [
                    {"strategy": cfg.gates.strategy_id, "result": "pass", "checked_at": value, "source": "old"},
                    {"strategy": cfg.gates.strategy_id, "result": "fail", "checked_at": 2, "source": "new"},
                ],
            }
        )
    )
    assert not gates.research_status(tmp_path, cfg)[0]


@pytest.mark.parametrize("writer", ["soak", "research", "grandfather"])
def test_gate_writers_refuse_nonfinite_time(tmp_path, writer):
    cfg = Config(OWNER)
    with pytest.raises(ValueError):
        if writer == "soak":
            gates.record_dry_run_tick(tmp_path, cfg, now=float("nan"))
        elif writer == "grandfather":
            gates.grandfather(tmp_path, cfg, "synthetic", now=float("inf"))
        else:
            gates.record_research_result(tmp_path, cfg, cfg.gates.strategy_id, "pass", "test", now=float("nan"))


def test_research_writers_serialize_read_append_replace(tmp_path, monkeypatch):
    cfg = Config(OWNER)
    entered, release, newer_started = Event(), Event(), Event()
    original = gates.atomic_write_json

    def write(path, doc):
        if doc["results"][-1]["source"] == "older":
            entered.set()
            assert release.wait(3)
        original(path, doc)

    def newer():
        newer_started.set()
        gates.record_research_result(tmp_path, cfg, cfg.gates.strategy_id, "fail", "newer", now=2)

    monkeypatch.setattr(gates, "atomic_write_json", write)
    with ThreadPoolExecutor(2) as pool:
        old = pool.submit(gates.record_research_result, tmp_path, cfg, cfg.gates.strategy_id, "pass", "older", now=1)
        assert entered.wait(3)
        new = pool.submit(newer)
        assert newer_started.wait(3)
        # Allow the unprotected implementation to commit the newer failure before the old replacement.
        try:
            new.result(timeout=0.1)
        except TimeoutError:
            pass
        finally:
            release.set()
        old.result(timeout=3)
        new.result(timeout=3)
    doc = json.loads(gates.research_path(tmp_path, cfg).read_text())
    assert len(doc["results"]) == 2
    assert not gates.research_status(tmp_path, cfg)[0]


def test_equal_research_timestamps_keep_latest_failure(tmp_path):
    cfg = Config(OWNER)
    gates.record_research_result(tmp_path, cfg, cfg.gates.strategy_id, "pass", "old", now=1)
    gates.record_research_result(tmp_path, cfg, cfg.gates.strategy_id, "fail", "new", now=1)
    assert not gates.research_status(tmp_path, cfg)[0]
