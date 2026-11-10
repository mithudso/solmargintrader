"""Inert archive inspection through the canonical Oracle query implementation."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .engine import OracleEngine, number
from .feeds import validate_instrument
from .graphdb import history as graph_history
from .store import Store, canonical
from .strategies import STRATEGY_IDS, StrategySet
from .voting import MINIMUM_ACCURACY

LEGACY_EVALUATOR_SHA256 = "2470d1d4c20043cb34ba48a4e9c1f1ff84682c512ce84ceac845099e5deaab9b"

# This is the stored schema of the original fourteen cards, not constructors or
# current defaults. Inspection must never execute an archived strategy.
PARAMETER_TYPES = {
    "ma_crossover": {"fast": int, "slow": int, "short_when_below": bool},
    "rsi": {"period": int, "oversold": float, "exit_level": float},
    "breakout": {"entry_lookback": int, "exit_lookback": int},
    "macd": {"fast": int, "slow": int, "signal": int},
    "bb_reversion": {"window": int, "num_std": float},
    "bb_breakout": {
        "window": int,
        "num_std": float,
        "squeeze_lookback": int,
        "squeeze_quantile": float,
    },
    "keltner": {"ema_span": int, "atr_period": int, "mult": float},
    "ts_momentum": {"window": int, "threshold": float},
    "stochastic": {
        "k_period": int,
        "d_period": int,
        "oversold": float,
        "exit_level": float,
    },
    "zscore": {"window": int, "entry_z": float, "exit_z": float},
    "sma_regime": {"window": int},
    "ema_crossover": {"fast": int, "slow": int},
    "ppo": {"fast": int, "slow": int, "signal": int},
    "ma_ribbon": {"windows": int, "base": int},
}


def _recorded_catalog(value) -> list[dict]:
    if type(value) is not list or len(value) != len(STRATEGY_IDS):
        raise ValueError("oracle_recorded_catalog_invalid")
    seen = set()
    for row in value:
        if type(row) is not dict or set(row) != {
            "strategy_id",
            "version",
            "parameters",
        }:
            raise ValueError("oracle_recorded_catalog_invalid")
        key, version, parameters = row["strategy_id"], row["version"], row["parameters"]
        if (
            type(key) is not str
            or key not in STRATEGY_IDS
            or key in seen
            or type(version) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", version)
            or type(parameters) is not dict
            or set(parameters) != set(PARAMETER_TYPES[key])
        ):
            raise ValueError("oracle_recorded_catalog_invalid")
        seen.add(key)
        for name, expected in PARAMETER_TYPES[key].items():
            parameter = parameters[name]
            if expected is float:
                valid = number(parameter) and abs(parameter) <= 1_000_000
            elif expected is int:
                valid = (
                    type(parameter) is int
                    and (0 if name == "squeeze_lookback" else 1)
                    <= parameter
                    <= 1_000_000
                )
            else:
                valid = type(parameter) is bool
            if not valid:
                raise ValueError("oracle_recorded_parameters_invalid")
        if (
            ("fast" in parameters and parameters["fast"] >= parameters["slow"])
            or ("num_std" in parameters and parameters["num_std"] <= 0)
            or ("mult" in parameters and parameters["mult"] <= 0)
            or (
                "squeeze_quantile" in parameters
                and not 0 <= parameters["squeeze_quantile"] <= 1
            )
            or (
                "oversold" in parameters
                and not 0 <= parameters["oversold"] < parameters["exit_level"] <= 100
            )
            or (
                "entry_z" in parameters
                and parameters["entry_z"] >= parameters["exit_z"]
            )
        ):
            raise ValueError("oracle_recorded_parameters_invalid")
    return json.loads(canonical(value))


class RecordedStrategySet:
    """Metadata only: deliberately has no predict or strategy constructors."""

    def __init__(self, catalog: list[dict]) -> None:
        self._catalog = catalog

    def catalog(self) -> list[dict]:
        return json.loads(canonical(self._catalog))


class ReadOnlyStore(Store):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().absolute()
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("oracle_archive_unavailable")
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (1, 2) or db.execute(
                "PRAGMA application_id"
            ).fetchone()[0] != 0x4F52434C:
                raise ValueError("oracle_archive_incompatible")
            expected_columns = {
                "metadata": ("key", "body"),
                "events": ("sequence", "kind", "event_key", "body"),
                "observations": ("event_id", "observed", "received", "price", "body"),
                "forecasts": (
                    "id",
                    "strategy",
                    "version",
                    "issued",
                    "target",
                    "direction",
                    "reference",
                    "body",
                ),
                "resolutions": ("forecast", "outcome", "hit", "resolved_at", "body"),
            }
            if version == 2:
                expected_columns.update(
                    {
                        "graphdb_ticks": (
                            "tick_id",
                            "instrument",
                            "policy_hash",
                            "bar_index",
                            "chart_time",
                            "observed_at",
                            "received_at",
                            "price",
                            "observation_id",
                            "market_shape",
                            "aggregate",
                        ),
                        "graphdb_predictions": (
                            "tick_id",
                            "strategy_id",
                            "strategy_version",
                            "forecast_id",
                            "direction",
                            "issued_at",
                            "expires_at",
                            "hits",
                            "resolved",
                            "accuracy_percent",
                            "vote_weight",
                            "vote_eligible",
                            "reason",
                        ),
                    }
                )
            for table, columns in expected_columns.items():
                kind = db.execute(
                    "SELECT type FROM sqlite_master WHERE name=?", (table,)
                ).fetchone()
                if (
                    kind is None
                    or kind[0] != "table"
                    or tuple(
                        row[1] for row in db.execute(f"PRAGMA table_info({table})")
                    )
                    != columns
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

    def __init__(
        self, path: str | Path, *, instrument: str, archived_versions: bool = False
    ) -> None:
        if type(archived_versions) is not bool:
            raise ValueError("invalid_archived_version_mode")
        self.store = ReadOnlyStore(path)
        self.instrument = validate_instrument(instrument)
        with self.store.connection() as db:
            row = db.execute("SELECT body FROM metadata WHERE key='policy'").fetchone()
        if row is None or len(row[0]) > 128_000:
            raise ValueError("oracle_policy_unavailable")
        policy = json.loads(row[0])
        if (
            not isinstance(policy, dict)
            or policy.get("schema_version") not in (1, 2)
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
        for name in (
            "engine.py",
            "store.py",
            "strategies.py",
            "voting.py",
            "graphdb.py",
        ):
            implementation.update(name.encode())
            implementation.update(Path(__file__).with_name(name).read_bytes())
        evaluator = policy.get("implementation_sha256")
        legacy_evaluator = (
            archived_versions
            and policy.get("schema_version") == 1
            and evaluator == LEGACY_EVALUATOR_SHA256
        )
        if evaluator != implementation.hexdigest() and not legacy_evaluator:
            raise ValueError("oracle_policy_implementation_unavailable")
        if policy.get("schema_version") == 2 and (
            policy.get("minimum_vote_accuracy") != MINIMUM_ACCURACY
            or policy.get("vote_threshold_semantics")
            != "strictly_greater_than_minimum"
        ):
            raise ValueError("oracle_policy_incompatible")
        self.minimum_vote_accuracy = MINIMUM_ACCURACY
        self.policy = policy
        self.policy_hash = hashlib.sha256(canonical(policy).encode()).hexdigest()
        self.archived_versions = archived_versions
        if archived_versions:
            expected_policy_keys = {
                "schema_version",
                "instrument",
                "horizon_seconds",
                "implementation_sha256",
                "bar_seconds",
                "max_age",
                "minimum_resolved",
                "resolution_tolerance",
                "flat_band_bps",
                "window",
                "strategies",
            }
            if policy.get("schema_version") == 2:
                expected_policy_keys.update(
                    {"minimum_vote_accuracy", "vote_threshold_semantics"}
                )
            if set(policy) != expected_policy_keys:
                raise ValueError("oracle_recorded_policy_invalid")
            self.strategy_set = RecordedStrategySet(
                _recorded_catalog(policy.get("strategies"))
            )
            if row[0] != canonical(policy):
                raise ValueError("oracle_recorded_policy_invalid")
            self._verify_recorded_policy()
        else:
            self.strategy_set = StrategySet()
            expected = [
                {key: item[key] for key in ("strategy_id", "version", "parameters")}
                for item in self.strategies()
            ]
            if policy.get("strategies") != expected:
                raise ValueError("oracle_policy_implementation_unavailable")

    def _verify_recorded_policy(self) -> None:
        """Bind stored forecasts to their policy SHA and relational identities."""
        with self.store.connection() as db:
            if db.execute(
                "SELECT 1 FROM forecasts WHERE length(body)>128000 OR NOT json_valid(body) LIMIT 1"
            ).fetchone():
                raise ValueError("oracle_recorded_forecast_invalid")
            recorded = self.strategy_set.catalog()
            parameters = [
                value
                for row in recorded
                for value in (
                    row["strategy_id"],
                    row["version"],
                    canonical(row["parameters"]),
                )
            ]
            # A single relational pass validates all cards. No history is loaded
            # into Python and every mismatch aborts before any vote is exposed.
            placeholders = ",".join("(?,?,?)" for _ in recorded)
            if db.execute(
                f"""WITH recorded(strategy,version,parameters) AS (VALUES {placeholders})
                SELECT 1 FROM forecasts f LEFT JOIN recorded r ON f.strategy=r.strategy WHERE
                r.strategy IS NULL OR f.version IS NOT r.version
                OR json_extract(f.body,'$.policy_hash') IS NOT ?
                OR json_extract(f.body,'$.instrument') IS NOT ?
                OR json_extract(f.body,'$.strategy_id') IS NOT f.strategy
                OR json_extract(f.body,'$.version') IS NOT f.version
                OR json_extract(f.body,'$.parameters') IS NOT r.parameters
                OR json_extract(f.body,'$.issued_at') IS NOT f.issued
                OR json_extract(f.body,'$.expires_at') IS NOT f.target
                OR json_extract(f.body,'$.direction') IS NOT f.direction LIMIT 1""",
                [*parameters, self.policy_hash, self.instrument],
            ).fetchone():
                raise ValueError("oracle_recorded_policy_binding_invalid")

    def _recorded_provenance(self) -> dict:
        return {
            "legacy_policy": self.archived_versions,
            "policy_origin": "recorded_archive"
            if self.archived_versions
            else "current_verified",
            "recorded_versions": {
                row["strategy_id"]: row["version"] for row in self.strategies()
            },
            "strategy_code_compatibility": "not_asserted"
            if self.archived_versions
            else "current_verified",
        }

    def predictions(self, now: float | None = None) -> dict:
        return {**super().predictions(now), **self._recorded_provenance()}

    def graph_history(self, limit: int = 240) -> dict:
        with self.store.connection() as db:
            return graph_history(db, self.instrument, limit)

    def status(self) -> dict:
        return {**super().status(), **self._recorded_provenance()}
