"""Crash and corruption counterexamples for the journal's write-before-send boundary."""

from __future__ import annotations

import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from executor.errors import ExecutorError
from executor.journal import Journal, require_clear


def write_record(journal, **overrides):
    record = {"seq": 1, "ts": 1, "kind": "intent", "id": "x", **overrides}
    with journal.path.open("ab") as stream:
        stream.write((json.dumps(record) + "\n").encode())


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"seq": 1, "ts": 1, "kind": "misspelled", "id": "x"},
        {"seq": True, "ts": 1, "kind": "intent", "id": "x"},
        {"seq": 0, "ts": 1, "kind": "intent", "id": "x"},
        {"seq": 1, "ts": True, "kind": "intent", "id": "x"},
        {"seq": 1, "ts": float("nan"), "kind": "intent", "id": "x"},
        {"seq": 1, "ts": float("inf"), "kind": "intent", "id": "x"},
        {"seq": 1, "ts": 1, "kind": "intent", "id": " "},
        {"seq": 1, "ts": 1, "kind": "intent", "id": []},
    ],
)
def test_invalid_record_envelopes_are_corruption(tmp_path, value):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.path.write_text(json.dumps(value) + "\n")
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        require_clear(journal)


@pytest.mark.parametrize(
    "event",
    [
        {"kind": "result"},
        {"kind": "result", "status": "mystery"},
        {"kind": "result", "status": "dropped"},
        {"kind": "reconciled", "status": "rejected"},
        {"kind": "intent"},
        {"kind": "sending", "signature": "different"},
        {"kind": "unknown", "signature": "different"},
        {"kind": "result", "status": "confirmed", "signature": "different"},
    ],
)
def test_invalid_transition_cannot_clear_or_replace_pending_send(tmp_path, event):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x")
    journal.append("sending", "x", signature="signed-transaction")
    write_record(journal, seq=3, **event)
    state = journal.states()["x"]
    assert state["state"] == "sending"
    assert state["sending"]["signature"] == "signed-transaction"
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        require_clear(journal)


@pytest.mark.parametrize("kind", ["sending", "unknown", "result", "reconciled"])
def test_orphan_lifecycle_events_are_corruption(tmp_path, kind):
    journal = Journal(tmp_path / "journal.jsonl")
    write_record(journal, kind=kind, status="confirmed", signature="signature")
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        require_clear(journal)


@pytest.mark.parametrize("seq", [1, 0, -1, "2", True])
def test_nonmonotonic_or_malformed_sequence_is_corruption(tmp_path, seq):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x")
    write_record(journal, seq=seq, kind="sending", signature="signature")
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        require_clear(journal)


def test_short_write_finishes_before_append_reports_success(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "journal.jsonl")
    real_write = os.write
    writes = []

    def short_write(fd, data):
        writes.append(len(data))
        return real_write(fd, data[:7])

    monkeypatch.setattr("executor.journal.os.write", short_write)
    record = journal.append("intent", "x")
    assert len(writes) > 1
    assert list(journal.records()) == [record]
    assert journal.path.read_bytes().endswith(b"\n")


def test_zero_progress_write_refuses(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "journal.jsonl")
    monkeypatch.setattr("executor.journal.os.write", lambda fd, data: 0)
    with pytest.raises(ExecutorError, match="write"):
        journal.append("intent", "x")


def test_append_syncs_content_then_directory_entry_before_success(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "journal.jsonl")
    real_fsync = os.fsync
    synced = []

    def record_sync(fd):
        synced.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        real_fsync(fd)

    monkeypatch.setattr("executor.journal.os.fsync", record_sync)
    journal.append("intent", "x")
    assert synced == ["file", "directory"]


def test_directory_sync_failure_never_reports_append_success(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "journal.jsonl")
    real_fsync = os.fsync

    def fail_directory_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("directory sync failed")
        real_fsync(fd)

    monkeypatch.setattr("executor.journal.os.fsync", fail_directory_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        journal.append("intent", "x")
    # The caller received no success; the intact content remains available for recovery.
    assert journal.states()["x"]["state"] == "intent"


def test_write_error_after_partial_send_record_never_returns_success(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x")
    real_write = os.write
    attempts = 0

    def failed_write(fd, data):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return real_write(fd, data[:7])
        raise OSError("disk full")

    monkeypatch.setattr("executor.journal.os.write", failed_write)
    with pytest.raises((OSError, ExecutorError)):
        journal.append("sending", "x", signature="signature")
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        require_clear(journal)


@pytest.mark.parametrize("suffix", [b'{"private":"do-not-echo"', b"\xff\n", b"null\n"])
def test_corrupt_journal_is_readable_but_never_appended_or_exposed(tmp_path, suffix):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x")
    with journal.path.open("ab") as stream:
        stream.write(suffix)
    original = journal.path.read_bytes()
    records = list(journal.records())
    assert journal.states()["x"]["state"] == "intent"
    assert journal.corrupt_lines() == 1
    assert "do-not-echo" not in repr(records)
    with pytest.raises(ExecutorError):
        journal.append("dry_run", "next")
    assert journal.path.read_bytes() == original


def test_valid_json_without_final_newline_stays_corrupt_and_is_not_joined(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    write_record(journal)
    journal.path.write_bytes(journal.path.read_bytes().rstrip(b"\n"))
    original = journal.path.read_bytes()
    assert journal.corrupt_lines() == 1
    with pytest.raises(ExecutorError):
        journal.append("dry_run", "next")
    assert journal.path.read_bytes() == original


def test_rejected_append_leaves_existing_pending_hold_intact(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x", ts=123)
    journal.append("sending", "x", signature="signature", ts=124)
    original = journal.path.read_bytes()
    with pytest.raises(ExecutorError):
        journal.append("intent", "x")
    assert journal.path.read_bytes() == original
    assert journal.unresolved()[0]["state"] == "sending"


def test_duplicate_json_keys_cannot_turn_an_unknown_into_a_terminal_result(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x")
    journal.append("sending", "x", signature="signature")
    with journal.path.open("ab") as stream:
        stream.write(
            b'{"seq":3,"ts":1,"kind":"unknown","id":"x","signature":"signature","kind":"result","status":"confirmed"}\n'
        )
    assert journal.corrupt_lines() == 1
    assert journal.unresolved()[0]["state"] == "sending"
    with pytest.raises(ExecutorError):
        require_clear(journal)


def test_concurrent_journal_instances_preserve_every_complete_record(tmp_path):
    path = tmp_path / "journal.jsonl"

    def append_tick(number):
        return Journal(path).append("dry_run", f"dry-{number}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(append_tick, range(16)))
    journal = Journal(path)
    assert sorted(record["seq"] for record in records) == list(range(1, 17))
    assert {record["id"] for record in journal.records()} == {f"dry-{number}" for number in range(16)}
    assert journal.corrupt_lines() == 0
    require_clear(journal)


def test_minimal_terminal_records_and_late_unknown_stay_compatible(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "x", ts=123)
    journal.append("sending", "x", signature="signature", ts=124)
    journal.append("result", "x", status="confirmed", ts=125)
    journal.append("unknown", "x", signature="signature", reason="late duplicate", ts=126)
    assert journal.states()["x"]["state"] == "result"
    assert journal.corrupt_lines() == 0
    require_clear(journal)
