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
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .errors import ExecutorError

TERMINAL = ("result", "reconciled")


class Journal:
    def __init__(self, path: Path):
        self.path = path

    def append(self, kind: str, intent_id: str, **fields: Any) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            seq = self._next_seq()
            rec = {"seq": seq, "ts": time.time(), "kind": kind, "id": intent_id, **fields}
            line = (json.dumps(rec, sort_keys=True, default=str, separators=(",", ":")) + "\n").encode()
            os.write(fd, line)
            os.fsync(fd)
            return rec
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _next_seq(self) -> int:
        last = 0
        for rec in self.records():
            last = max(last, int(rec.get("seq", 0)))
        return last + 1

    def records(self) -> Iterator[dict[str, Any]]:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                # A torn final line must never hide the rest, but silently skipping hides corruption: surface it.
                yield {"seq": -1, "ts": 0, "kind": "corrupt", "id": "", "line": line[:200]}
                continue
            if isinstance(rec, dict):
                yield rec

    def states(self) -> dict[str, dict[str, Any]]:
        """id -> {state, intent, sending, outcome, ...} by replaying the file."""
        out: dict[str, dict[str, Any]] = {}
        for rec in self.records():
            iid = rec.get("id", "")
            kind = rec.get("kind")
            if kind in ("intent", "sending", "unknown", "result", "reconciled"):
                st = out.setdefault(iid, {"id": iid, "state": "intent"})
                if kind == "intent":
                    st["intent"] = rec
                    st["state"] = "intent"
                elif kind == "sending":
                    st["sending"] = rec
                    st["state"] = "sending"
                elif kind == "unknown":
                    st["unknown"] = rec
                    if st["state"] not in TERMINAL:
                        st["state"] = "unknown"
                else:
                    st["outcome"] = rec
                    st["state"] = kind
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
