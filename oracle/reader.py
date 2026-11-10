"""Inert archive inspection through the canonical Oracle query implementation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .engine import OracleEngine, number
from .feeds import validate_instrument
from .store import Store, canonical
from .strategies import StrategySet


class ReadOnlyStore(Store):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().absolute()
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("oracle_archive_unavailable")
        with self.connection() as db:
            if (
                db.execute("PRAGMA user_version").fetchone()[0] != 1
                or db.execute("PRAGMA application_id").fetchone()[0] != 0x4F52434C
            ):
                raise ValueError("oracle_archive_incompatible")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            with db:
                yield db
        finally:
            db.close()


class ReadOnlyOracle(OracleEngine):
    """Load the recorded policy without constructing a writer or changing DDL.

    Query methods remain the engine's own implementation. A changed evaluator or
    card identity refuses rather than grading old evidence under new code.
    """

    def __init__(self, path: str | Path, *, instrument: str) -> None:
        self.store = ReadOnlyStore(path)
        self.instrument = validate_instrument(instrument)
        with self.store.connection() as db:
            row = db.execute("SELECT body FROM metadata WHERE key='policy'").fetchone()
        if row is None or len(row[0]) > 128_000:
            raise ValueError("oracle_policy_unavailable")
        policy = json.loads(row[0])
        if (
            not isinstance(policy, dict)
            or policy.get("schema_version") != 1
            or policy.get("instrument") != self.instrument
            or policy.get("flat_band_bps") != 0
            or policy.get("window") != "all_resolved_in_this_policy"
        ):
            raise ValueError("oracle_policy_incompatible")
        for key in ("horizon_seconds", "bar_seconds", "minimum_resolved"):
            value = policy.get(key)
            if type(value) is not int or not 1 <= value <= 86400:
                raise ValueError("oracle_policy_incompatible")
            setattr(self, key, value)
        for key in ("max_age", "resolution_tolerance"):
            value = policy.get(key)
            if not number(value) or not 0 < value <= 3600:
                raise ValueError("oracle_policy_incompatible")
            setattr(self, key, value)
        implementation = hashlib.sha256()
        for name in ("engine.py", "store.py", "strategies.py", "voting.py"):
            implementation.update(name.encode())
            implementation.update(Path(__file__).with_name(name).read_bytes())
        self.strategy_set = StrategySet()
        expected = [
            {key: item[key] for key in ("strategy_id", "version", "parameters")}
            for item in self.strategies()
        ]
        if (
            policy.get("implementation_sha256") != implementation.hexdigest()
            or policy.get("strategies") != expected
        ):
            raise ValueError("oracle_policy_implementation_unavailable")
        self.policy = policy
        self.policy_hash = hashlib.sha256(canonical(policy).encode()).hexdigest()
