"""Descriptor and filtered-history regressions over disposable files/fakes."""

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from executor import config, registry
from executor.errors import ExecutorError
from executor.journal import Journal


def test_configuration_permission_check_and_read_bind_to_the_same_file(tmp_path, monkeypatch):
    target, replacement = tmp_path / "config.toml", tmp_path / "replacement.toml"
    target.write_text(config.default_toml())
    replacement.write_text(config.default_toml().replace('mode = "dry-run"', 'mode = "live"'))
    target.chmod(0o600)
    replacement.chmod(0o666)
    read_text = Path.read_text

    def swap_before_read(path, *args, **kwargs):
        if path == target:
            replacement.replace(target)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", swap_before_read)
    try:
        loaded = config.load_config(target, create=False)
    except ExecutorError:
        return  # Refusal also preserves the permission boundary.
    assert loaded.mode == "dry-run"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX-only special-file fixture")
def test_configuration_refuses_special_files_before_reading(tmp_path, monkeypatch):
    target = tmp_path / "fifo"
    os.mkfifo(target, 0o600)

    def unsafe_read(*args, **kwargs):
        raise AssertionError("attempted to read an unvalidated special file")

    monkeypatch.setattr(Path, "read_text", unsafe_read)
    with pytest.raises(ExecutorError):
        config.load_config(target, create=False)


def test_append_tightens_an_existing_journal_without_rewriting_evidence(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("dry_run", "first", strategy="synthetic")
    original = journal.path.read_bytes()
    journal.path.chmod(0o644)
    journal.append("dry_run", "second", strategy="synthetic")
    assert journal.path.read_bytes().startswith(original)
    assert stat.S_IMODE(journal.path.stat().st_mode) == 0o600
    assert [r["id"] for r in journal.records()] == ["first", "second"]


def test_strategy_history_limit_applies_after_filtering():
    records = [{"id": "wanted", "kind": "intent"}] + [{"id": f"unrelated-{i}", "kind": "dry_run"} for i in range(501)]
    journal = SimpleNamespace(
        records=lambda: iter(records),
        tail=lambda n: records[-n:],
        states=lambda: {"wanted": {"intent": {"strategy": "needle"}}},
        unresolved=lambda: [],
    )
    context = registry.Context(config.Config(), SimpleNamespace(journal=journal))
    assert registry._journal(context, {"strategy": "needle", "limit": 2})["records"] == records[:1]
