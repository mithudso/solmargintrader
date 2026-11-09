"""Append-only journal of intents and results: `$EXECUTOR_HOME/journal.jsonl`, mode 600.

Every swap that will be sent is written BEFORE sending (`intent`, then `sending` with the signature) and its outcome
AFTER (`result`). Lines are only ever appended, each under an exclusive lock and fsynced. State is derived by
replaying the file; nothing is rewritten.

Per intent id the states are:
  intent      written, never reached `sending`   -> abandoned; nothing was sent
  sending     `sending` written, no outcome      -> UNKNOWN: it may have landed. Blocks every new live swap
  unknown     the send or confirmation was ambiguous -> UNKNOWN, same
  result      confirmed or failed on chain       -> terminal
  reconciled  `executor reconcile` decided it from chain -> terminal

An unknown intent is never auto-retried. `reconcile` asks the chain by signature; only it can clear the block.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .errors import ExecutorError

TERMINAL = ("result", "reconciled")
KINDS = ("intent", "sending", "unknown", "result", "reconciled", "dry_run")
OUTCOMES = {"result": ("confirmed", "failed", "rejected"), "reconciled": ("confirmed", "failed", "dropped")}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _record_problem(rec: Any) -> str | None:
    if not isinstance(rec, dict):
        return "record is not an object"
    seq, ts, kind, iid = (rec.get(key) for key in ("seq", "ts", "kind", "id"))
    if type(seq) is not int or seq <= 0:
        return "sequence must be a positive integer"
    try:
        finite_time = type(ts) in (int, float) and math.isfinite(ts)
    except OverflowError:
        finite_time = False
    if not finite_time:
        return "timestamp must be a finite number"
    if not isinstance(kind, str) or kind not in KINDS:
        return "record kind is unknown"
    if not isinstance(iid, str) or not iid.strip():
        return "record id must be a nonempty string"
    if kind in ("sending", "unknown"):
        signature = rec.get("signature")
        if not isinstance(signature, str) or not signature.strip():
            return "send signature is missing or invalid"
    if kind in TERMINAL and rec.get("status") not in OUTCOMES[kind]:
        return "terminal status is missing or unknown"
    return None


def _apply_record(rec: dict[str, Any], states: dict[str, dict[str, Any]]) -> str | None:
    """Apply only valid transitions; an invalid event cannot replace a pending send."""
    iid, kind = rec["id"], rec["kind"]
    if kind == "dry_run":
        return None
    st = states.get(iid)
    if kind == "intent":
        if st is not None:
            return "intent id is already in use"
        states[iid] = {"id": iid, "state": "intent", "intent": rec}
        return None
    if st is None:
        return "event has no preceding intent"
    state = st["state"]
    if kind == "sending":
        if state != "intent":
            return "sending must follow an unsent intent"
        st["sending"] = rec
    else:
        if state == "intent":
            return "event has no preceding sending record"
        expected_signature = st["sending"]["signature"]
        if "signature" in rec and rec["signature"] != expected_signature:
            return "event signature disagrees with the sending record"
        if kind == "unknown":
            st["unknown"] = rec
            # A delayed transport error cannot undo an already established outcome.
            if state in TERMINAL:
                return None
        else:
            if state in TERMINAL:
                return "terminal outcome is already recorded"
            st["outcome"] = rec
    st["state"] = kind
    return None


class Journal:
    def __init__(self, path: Path):
        self.path = path

    def append(self, kind: str, intent_id: str, **fields: Any) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            records = list(self.records())
            if any(rec["kind"] == "corrupt" for rec in records):
                raise ExecutorError("the journal has an unparseable line; inspect it before appending", "refused")
            seq = records[-1]["seq"] + 1 if records else 1
            rec = {"seq": seq, "ts": time.time(), "kind": kind, "id": intent_id, **fields}
            if rec["seq"] != seq:
                raise ExecutorError("journal sequence cannot be overridden", "refused")
            problem = _record_problem(rec)
            if problem:
                raise ExecutorError(f"invalid journal record: {problem}", "refused")
            states: dict[str, dict[str, Any]] = {}
            for previous in records:
                _apply_record(previous, states)
            problem = _apply_record(rec, states)
            if problem:
                raise ExecutorError(f"invalid journal transition: {problem}", "refused")
            line = (
                json.dumps(rec, sort_keys=True, default=str, separators=(",", ":"), allow_nan=False) + "\n"
            ).encode()
            remaining = memoryview(line)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise ExecutorError("journal write made no progress", "failed")
                remaining = remaining[written:]
            os.fsync(fd)
            # File fsync does not persist a newly created journal's directory entry.
            directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return rec
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def records(self) -> Iterator[dict[str, Any]]:
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return
        states: dict[str, dict[str, Any]] = {}
        last_seq = 0
        lines = data.split(b"\n")
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            problem = None
            rec = None
            try:
                rec = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object)
                problem = _record_problem(rec)
            except (UnicodeDecodeError, ValueError):
                problem = "record is not valid UTF-8 JSON"
            if line_number == len(lines):
                problem = "final record has no newline"
            if problem is None and rec["seq"] <= last_seq:
                problem = "sequence is not increasing"
            if problem is None:
                problem = _apply_record(rec, states)
            if problem:
                # Journal commands may expose these diagnostics. Never echo damaged payloads.
                yield {"seq": -1, "ts": 0, "kind": "corrupt", "id": "", "line_number": line_number, "reason": problem}
            else:
                last_seq = rec["seq"]
                yield rec

    def states(self) -> dict[str, dict[str, Any]]:
        """id -> {state, intent, sending, outcome, ...} by replaying the file."""
        out: dict[str, dict[str, Any]] = {}
        for rec in self.records():
            if rec["kind"] != "corrupt":
                _apply_record(rec, out)
        return out

    def unresolved(self) -> list[dict[str, Any]]:
        """Intents that may have landed and have no outcome: they block new live swaps."""
        return [s for s in self.states().values() if s["state"] in ("sending", "unknown")]

    def corrupt_lines(self) -> int:
        return sum(1 for r in self.records() if r.get("kind") == "corrupt")

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        recs = list(self.records())
        return recs[-limit:] if limit > 0 else []


def require_clear(journal: Journal) -> None:
    pending = journal.unresolved()
    if pending:
        ids = ", ".join(f"{p['id']} ({p['state']})" for p in pending)
        raise ExecutorError(
            f"unresolved send(s): {ids}. Run `executor reconcile`; nothing is retried automatically", "refused"
        )
    if journal.corrupt_lines():
        raise ExecutorError("the journal has an unparseable line; inspect it before trading", "refused")
