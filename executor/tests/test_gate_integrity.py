"""Persisted gate evidence must fail closed and survive concurrent writers."""

from __future__ import annotations

import json
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from executor import gates
from executor.config import Config, fingerprint
from executor.errors import BadParams, ExecutorError


def soak_record(cfg, **changes):
    record = {
        "fingerprint": fingerprint(cfg, "s"),
        "started_at": 100,
        "last_tick_at": 90100,
        "accumulated_s": 86400,
        "dry_runs": 50,
        "resets": [],
    }
    return {**record, **changes}


@pytest.mark.parametrize(
    "record",
    [
        ["not a record"],
        "not a record",
        {"accumulated_s": float("nan")},
        {"accumulated_s": float("inf")},
        {"accumulated_s": -1},
        {"accumulated_s": "86400"},
        {"dry_runs": True},
        {"dry_runs": 50.5},
        {"dry_runs": -1},
        {"started_at": float("nan")},
        {"last_tick_at": float("inf")},
        {"last_tick_at": 1e308},
        {"last_tick_at": 99},
        {"resets": "broken"},
        {"resets": [{"at": float("nan"), "from": "old"}]},
    ],
)
def test_malformed_soak_blocks_and_restarts_without_credit(tmp_path, record):
    cfg = Config()
    current = soak_record(cfg, **record) if isinstance(record, dict) else record
    (tmp_path / "soak.json").write_text(json.dumps({"schema": gates.SOAK_SCHEMA, "strategies": {"s": current}}))
    assert gates.soak_status(tmp_path, cfg, "s")[0] is False
    restarted = gates.record_dry_run(tmp_path, cfg, "s", now=100000)
    assert restarted["dry_runs"] == 1
    assert restarted["accumulated_s"] == 0
    assert gates.soak_status(tmp_path, cfg, "s")[0] is False


def test_backward_clock_restarts_soak_instead_of_reusing_elapsed_time(tmp_path):
    cfg = Config()
    gates.record_dry_run(tmp_path, cfg, "s", now=100)
    gates.record_dry_run(tmp_path, cfg, "s", now=1000)
    restarted = gates.record_dry_run(tmp_path, cfg, "s", now=500)
    assert restarted["dry_runs"] == 1
    assert restarted["accumulated_s"] == 0


def test_explicit_zero_soak_still_needs_a_valid_successful_dry_run(tmp_path):
    cfg = Config()
    cfg.gates.soak_hours = cfg.gates.min_dry_runs = 0
    assert gates.soak_status(tmp_path, cfg, "s")[0] is False
    gates.record_dry_run(tmp_path, cfg, "s", now=100)
    assert gates.soak_status(tmp_path, cfg, "s")[0] is True


def research_record(**changes):
    return {"strategy": "s", "result": "pass", "checked_at": 100, "source": "old-report", **changes}


@pytest.mark.parametrize(
    "changes",
    [
        {"checked_at": float("nan")},
        {"checked_at": float("inf")},
        {"checked_at": 1e308},
        {"checked_at": True},
        {"checked_at": -1},
        {"checked_at": "broken"},
        {"source": None},
        {"source": " "},
        {"result": "unknown"},
        {"note": []},
    ],
)
def test_malformed_newer_research_never_falls_back_to_an_old_pass(tmp_path, changes):
    cfg = Config()
    path = tmp_path / "research-gate.json"
    path.write_text(
        json.dumps(
            {
                "schema": gates.RESEARCH_SCHEMA,
                "results": [research_record(), research_record(**{"result": "fail", "checked_at": 101, **changes})],
            }
        )
    )
    before = path.read_bytes()
    assert gates.research_status(tmp_path, cfg, "s")[0] is False
    with pytest.raises(ExecutorError, match="inspect"):
        gates.record_research_result(tmp_path, cfg, "s", "pass", "new-report", now=102)
    assert path.read_bytes() == before


@pytest.mark.parametrize("doc", [[], {"results": [research_record()]}, {"schema": "wrong", "results": []}])
def test_research_schema_is_required_and_damage_is_preserved(tmp_path, doc):
    cfg = Config()
    path = tmp_path / "research-gate.json"
    path.write_text(json.dumps(doc))
    before = path.read_bytes()
    assert gates.research_status(tmp_path, cfg, "s")[0] is False
    with pytest.raises(ExecutorError, match="inspect"):
        gates.record_research_result(tmp_path, cfg, "s", "pass", "new-report", now=102)
    assert path.read_bytes() == before


@pytest.mark.parametrize("now", [float("nan"), float("inf"), 1e308, -1, True, "100"])
def test_invalid_recording_clock_cannot_write_gate_evidence(tmp_path, now):
    cfg = Config()
    with pytest.raises(BadParams):
        gates.record_dry_run(tmp_path, cfg, "s", now=now)
    with pytest.raises(BadParams):
        gates.record_research_result(tmp_path, cfg, "s", "pass", "report", now=now)
    assert not (tmp_path / "soak.json").exists()
    assert not (tmp_path / "research-gate.json").exists()


def test_research_same_timestamp_uses_the_last_recorded_result(tmp_path):
    cfg = Config()
    gates.record_research_result(tmp_path, cfg, "s", "pass", "old-report", now=100)
    gates.record_research_result(tmp_path, cfg, "s", "fail", "new-report", now=100)
    assert gates.research_status(tmp_path, cfg, "s")[0] is False


def test_research_clock_regression_retains_failure_and_blocks_prior_pass(tmp_path):
    cfg = Config()
    gates.record_research_result(tmp_path, cfg, "s", "pass", "old-report", now=200)
    recorded = gates.record_research_result(tmp_path, cfg, "s", "fail", "new-failure", now=100)
    assert recorded["result"] == "fail"
    path = tmp_path / "research-gate.json"
    before = path.read_bytes()
    assert [r["result"] for r in json.loads(before)["results"]] == ["pass", "fail"]
    assert gates.research_status(tmp_path, cfg, "s")[0] is False
    with pytest.raises(ExecutorError, match="inspect"):
        gates.record_research_result(tmp_path, cfg, "s", "pass", "later-report", now=300)
    assert path.read_bytes() == before


def test_an_imported_old_pass_does_not_override_a_newer_failure(tmp_path):
    cfg = Config()
    (tmp_path / "research-gate.json").write_text(
        json.dumps(
            {
                "schema": gates.RESEARCH_SCHEMA,
                "results": [
                    research_record(checked_at=100),
                    research_record(result="fail", checked_at=200),
                    research_record(checked_at=150),
                ],
            }
        )
    )
    assert gates.research_status(tmp_path, cfg, "s")[0] is False


def test_research_duplicate_result_keys_cannot_replace_failure_with_pass(tmp_path):
    cfg = Config()
    path = tmp_path / "research-gate.json"
    path.write_text(
        '{"schema":"executor-research-gate/1","results":['
        '{"strategy":"s","result":"fail","result":"pass","checked_at":100,"source":"fixture"}]}'
    )
    before = path.read_bytes()
    assert gates.research_status(tmp_path, cfg, "s")[0] is False
    with pytest.raises(ExecutorError, match="inspect"):
        gates.record_research_result(tmp_path, cfg, "s", "pass", "later-report", now=200)
    assert path.read_bytes() == before


def test_soak_duplicate_credit_keys_fail_closed(tmp_path):
    cfg = Config()
    text = json.dumps({"schema": gates.SOAK_SCHEMA, "strategies": {"s": soak_record(cfg)}})
    text = text.replace('"accumulated_s": 86400', '"accumulated_s": 0, "accumulated_s": 86400')
    (tmp_path / "soak.json").write_text(text)
    assert gates.soak_status(tmp_path, cfg, "s")[0] is False


@pytest.mark.parametrize("kind", ["soak", "research"])
def test_concurrent_read_modify_replace_preserves_both_updates(tmp_path, monkeypatch, kind):
    cfg = Config()
    first_writing = threading.Event()
    second_started = threading.Event()
    second_writing = threading.Event()
    release_first = threading.Event()
    first_written = threading.Event()
    atomic_write = gates._atomic_write

    def controlled_write(path, doc):
        if threading.current_thread().name.endswith("_0"):
            first_writing.set()
            assert release_first.wait(3)
            atomic_write(path, doc)
            first_written.set()
        else:
            second_writing.set()
            assert first_written.wait(3)
            atomic_write(path, doc)

    def record(which):
        if which == 1:
            second_started.set()
        if kind == "soak":
            return gates.record_dry_run(tmp_path, cfg, "s", now=100 + which)
        return gates.record_research_result(
            tmp_path, cfg, "s", "pass" if which == 0 else "fail", f"report-{which}", now=100 + which
        )

    monkeypatch.setattr(gates, "_atomic_write", controlled_write)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(record, 0)
        assert first_writing.wait(3)
        second = pool.submit(record, 1)
        assert second_started.wait(3)
        # Without a transaction lock the second writer reads stale evidence while the first is held here.
        second_writing.wait(0.2)
        release_first.set()
        first.result(timeout=3)
        second.result(timeout=3)
    if kind == "soak":
        assert gates.load_soak(tmp_path)["strategies"]["s"]["dry_runs"] == 2
    else:
        doc = json.loads((tmp_path / "research-gate.json").read_text())
        assert [r["result"] for r in doc["results"]] == ["pass", "fail"]
        assert gates.research_status(tmp_path, cfg, "s")[0] is False


def test_override_audit_retries_short_writes_until_the_whole_record_is_durable(tmp_path, monkeypatch):
    write = os.write

    def short_write(fd, data):
        return write(fd, data[:7])

    monkeypatch.setattr(gates.os, "write", short_write)
    gates.log_override(tmp_path, "s", "fixture-only override", now=100)
    lines = (tmp_path / "gate-overrides.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "at": 100,
        "iso": "1970-01-01T00:01:40Z",
        "gate": "research",
        "strategy": "s",
        "why": "fixture-only override",
    }


def test_override_audit_with_no_write_progress_refuses_instead_of_approving(tmp_path, monkeypatch):
    monkeypatch.setattr(gates.os, "write", lambda _fd, _data: 0)
    with pytest.raises(ExecutorError, match="override"):
        gates.log_override(tmp_path, "s", "fixture-only override", now=100)


def test_override_refuses_a_torn_prior_audit_record_without_modifying_it(tmp_path):
    path = tmp_path / "gate-overrides.jsonl"
    path.write_text('{"at":100,"gate":')
    before = path.read_bytes()
    with pytest.raises(ExecutorError, match="inspect"):
        gates.log_override(tmp_path, "s", "fixture-only override", now=101)
    assert path.read_bytes() == before


def test_new_override_log_requires_directory_durability(tmp_path, monkeypatch):
    fsync = os.fsync

    def fail_directory_fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("fixture directory fsync failure")
        return fsync(fd)

    monkeypatch.setattr(gates.os, "fsync", fail_directory_fsync)
    with pytest.raises(ExecutorError, match="override"):
        gates.log_override(tmp_path, "s", "fixture-only override", now=101)


def test_atomic_gate_write_requires_directory_fsync_and_cleans_its_temporary_file(tmp_path, monkeypatch):
    fsync = os.fsync
    directory_syncs = []

    def fail_directory_fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_syncs.append(fd)
            raise OSError("fixture directory fsync failure")
        return fsync(fd)

    monkeypatch.setattr(gates.os, "fsync", fail_directory_fsync)
    with pytest.raises(OSError, match="fixture directory fsync failure"):
        gates._atomic_write(tmp_path / "fixture.json", {"fixture": True})
    assert len(directory_syncs) == 1
    assert list(tmp_path.iterdir()) == [tmp_path / "fixture.json"]


def test_failed_gate_serialization_removes_the_temporary_file(tmp_path):
    with pytest.raises(ValueError):
        gates._atomic_write(tmp_path / "fixture.json", {"fixture": float("nan")})
    assert list(tmp_path.iterdir()) == []
