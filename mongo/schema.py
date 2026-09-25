"""Collection layout for the local research store: specs, validators, indexes.

    python3 mongo/schema.py --create      # create everything (drops first)
    python3 mongo/schema.py --describe    # print the layout, touch nothing

Design notes, because the shape is the part worth arguing about:

  * **Bars are a native time series collection.** Per-bar, time-ordered,
    append-only measurements are what that collection type exists for; it buckets
    and column-compresses automatically instead of storing 18,000 standalone
    documents with an index entry each.
  * **Provenance lives in the metaField**, not on every measurement. `source_path`
    and `source_sha256` are constant for a given (asset, interval) series, which is
    exactly the constraint a metaField wants, and MongoDB stores it once per bucket
    rather than once per bar.
  * **JLP spot is its own collection**, one document, on purpose. It is a Jupiter
    price snapshot with no OHLCV columns -- `research/decide.py` refuses to read it
    as bars and `docs/known-issues.md` records that as correct. Merging the two here
    would contradict the distinction the code enforces, and `granularity` is a
    per-collection setting that cannot suit both 18k regular bars and one snapshot.
  * **Strategy cards keep their own vocabulary.** No invented `registered` boolean:
    `registry_key` is null for the 20 cards that are not `Strategy` implementations,
    and `status` ("measured" / "implemented" / "spec-only") plus `runner` carry the
    rest. The ladder grid is implemented and has no registry key because it is not a
    `Strategy` at all.
  * **Experiment rows are separate documents**, not an array on the experiment.
    `cpcv_combos_results.csv` alone is 1,212 rows; embedding would be the unbounded
    array antipattern and would make the rows unaggregatable, which is the whole
    reason for loading them.
  * **Decisions are stored as `decide.build_report()` emits them.** Re-deriving a
    Mongo-specific shape would let the store and the readout disagree.

Time series collections accept neither `$jsonSchema` validators nor unique indexes.
That has a consequence the loader has to own: there is no database-level guard
against loading the same series twice, so `load.py` drops and recreates rather than
upserting. See its docstring.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

DB_NAME = "solmargintrader"

# Only these collections are ever created, dropped, or written by this component.
# The same server also hosts unrelated databases; nothing here touches anything
# outside `DB_NAME`, and the loader refuses a collection name not on this list.
TIME_SERIES: dict[str, dict[str, Any]] = {
    "bars": {
        "timeseries": {
            "timeField": "ts",
            "metaField": "series",
            # Daily and hourly bars both live here, separated by the metaField.
            # "hours" is the coarsest granularity offered and suits both.
            "granularity": "hours",
        },
        "comment": "OHLCV bars. meta: {asset, interval, source, source_path, source_sha256}",
    },
    "spot_prices": {
        "timeseries": {
            "timeField": "ts",
            "metaField": "snapshot",
            "granularity": "hours",
        },
        "comment": "Jupiter USD price snapshots. Not OHLCV; see the module docstring",
    },
    "equity_points": {
        "timeseries": {
            "timeField": "ts",
            "metaField": "curve",
            "granularity": "hours",
        },
        "comment": "Backtest equity curves. meta: {run_id, strategy}",
    },
}

# `$jsonSchema` validators for the regular collections. Strict, because this store
# has exactly one writer (`load.py`) -- the usual reason to start with
# `moderate`/`warn` is pre-existing data of unknown shape, and there is none.
PROVENANCE_PROPERTIES: dict[str, Any] = {
    "source_path": {"bsonType": "string", "description": "repo-relative source file"},
    "source_sha256": {"bsonType": "string"},
    "loaded_at": {"bsonType": "date"},
}
PROVENANCE_REQUIRED = ["source_path", "source_sha256", "loaded_at"]


def _doc(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """A `$jsonSchema` validator carrying the shared provenance fields."""
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [*required, *PROVENANCE_REQUIRED],
            "properties": {**properties, **PROVENANCE_PROPERTIES},
        }
    }


COLLECTIONS: dict[str, dict[str, Any]] = {
    "strategies": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string", "description": "the card's own id"},
                "name": {"bsonType": "string"},
                "kind": {"enum": ["exposure-strategy", "ladder", "pairs"]},
                "status": {"enum": ["measured", "implemented", "spec-only"]},
                "family": {"bsonType": "string"},
                "summary": {"bsonType": "string"},
                "registry_key": {
                    "bsonType": ["string", "null"],
                    "description": "null when the card is not a Strategy implementation",
                },
                "runner": {"bsonType": ["string", "null"]},
                "warmup_bars": {"bsonType": ["int", "null"]},
                "data_available": {"bsonType": "bool"},
                "success_likelihood": {"bsonType": "string"},
                "success_basis": {"enum": ["measured-oos", "base-rate", "a-priori"]},
                "params": {"bsonType": "object"},
                "presets": {"bsonType": "object"},
                "body": {"bsonType": "string", "description": "the card's prose"},
                "registry": {
                    "bsonType": ["object", "null"],
                    "description": "live code facts; present only when registry_key is set",
                },
            },
            ["_id", "name", "kind", "status", "family", "summary"],
        ),
        "indexes": [
            ([("status", 1), ("family", 1)], {"name": "status_family"}),
            ([("family", 1)], {"name": "family"}),
            (
                [("registry_key", 1)],
                {
                    "name": "registry_key_unique",
                    "unique": True,
                    # 20 cards carry no registry key, and a unique index would
                    # otherwise reject all but the first null.
                    "partialFilterExpression": {"registry_key": {"$type": "string"}},
                },
            ),
            ([("data_available", 1), ("success_likelihood", 1)], {"name": "feasibility"}),
        ],
        "comment": "One document per strategy card (45). Registry facts embedded for the 25 registered",
    },
    "signals": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string"},
                "rule": {"bsonType": "string"},
                "tracks_strategy": {
                    "bsonType": ["string", "null"],
                    "description": "the registry key whose defaults this rule mirrors, if any",
                },
            },
            ["_id", "rule"],
        ),
        "indexes": [([("tracks_strategy", 1)], {"name": "tracks_strategy"})],
        "comment": "The 15 stateless one-bar rules in research/decide.py",
    },
    "indicators": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string"},
                "reported": {
                    "bsonType": "bool",
                    "description": "false for helpers/series forms that carry no per-bar reading",
                },
                "sources": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                    "description": "core.indicators functions this row covers",
                },
                "skip_reason": {"bsonType": ["string", "null"]},
            },
            ["_id", "reported"],
        ),
        "indexes": [([("reported", 1)], {"name": "reported"})],
        "comment": "16 reported indicator rows plus the 4 explicitly skip-listed functions",
    },
    "decisions": {
        "validator": _doc(
            {
                "asset": {"bsonType": "string"},
                "interval": {"bsonType": "string"},
                "bars": {"bsonType": "int"},
                "data_checksum": {"bsonType": "string"},
                "decision_bar": {"bsonType": "object"},
                "execution": {"bsonType": "object"},
                "strategies": {"bsonType": "array"},
                "signals": {"bsonType": "array"},
                "indicators": {"bsonType": "array"},
            },
            ["asset", "interval", "bars", "data_checksum", "decision_bar"],
        ),
        "indexes": [
            (
                [
                    ("asset", 1),
                    ("interval", 1),
                    ("decision_bar.timestamp", 1),
                    ("data_checksum", 1),
                ],
                {"name": "readout_identity", "unique": True},
            ),
            ([("decision_bar.timestamp", -1)], {"name": "recent_first"}),
            ([("strategies.key", 1), ("strategies.action", 1)], {"name": "by_action"}),
        ],
        "comment": "One document per `decide.py` readout, exactly as build_report() emits it",
    },
    "backtest_runs": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string", "description": "run id"},
                "asset": {"bsonType": "string"},
                "interval": {"bsonType": "string"},
                "mode": {"bsonType": "string"},
                "manifest": {
                    "bsonType": "object",
                    "description": "RunManifest verbatim -- what reproduces the run",
                },
                "results": {
                    "bsonType": "array",
                    "description": "per-strategy metrics; bounded by the strategies run",
                },
            },
            ["_id", "manifest"],
        ),
        "indexes": [
            ([("asset", 1), ("interval", 1)], {"name": "asset_interval"}),
            ([("results.strategy", 1)], {"name": "by_strategy"}),
        ],
        "comment": "One document per backtest run: manifest plus embedded per-strategy metrics",
    },
    "trades": {
        "validator": _doc(
            {
                "run_id": {"bsonType": "string"},
                "strategy": {"bsonType": "string"},
                "ts": {"bsonType": "date"},
                "side": {"bsonType": "string"},
                "price": {"bsonType": "double"},
            },
            ["run_id", "strategy", "ts"],
        ),
        "indexes": [
            ([("run_id", 1), ("strategy", 1), ("ts", 1)], {"name": "run_strategy_time"}),
        ],
        "comment": "One document per fill",
    },
    "experiments": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string", "description": "kind/name"},
                "kind": {
                    "enum": [
                        "cpcv",
                        "sweep",
                        "perturbation",
                        "geometry",
                        "top-coins",
                        "counts",
                        "cross-asset",
                    ]
                },
                "name": {"bsonType": "string"},
                "row_count": {"bsonType": "int"},
                "summary_row_count": {"bsonType": "int"},
                "summary": {
                    "bsonType": ["object", "null"],
                    "description": (
                        "the JSON sidecar when it is a single object. A sidecar "
                        "holding a LIST -- one PBO per horizon, or per geometry -- "
                        "is loaded into experiment_rows with section='summary' "
                        "instead, because those are the most queried numbers in the "
                        "research set and a blob would hide them"
                    ),
                },
            },
            ["_id", "kind", "name", "row_count"],
        ),
        "indexes": [([("kind", 1), ("name", 1)], {"name": "kind_name", "unique": True})],
        "comment": "Metadata and summary per experiment; rows live in experiment_rows",
    },
    "experiment_rows": {
        "validator": _doc(
            {
                "experiment_id": {"bsonType": "string"},
                "kind": {"bsonType": "string"},
                "section": {
                    "enum": ["result", "summary"],
                    "description": "'result' from the CSV, 'summary' from a list-shaped sidecar",
                },
                "row": {
                    "bsonType": "int",
                    "description": "0-based position within its section",
                },
            },
            ["experiment_id", "kind", "section", "row"],
        ),
        "indexes": [
            (
                [("experiment_id", 1), ("section", 1), ("row", 1)],
                # Row numbers restart per section, so the identity is all three.
                {"name": "experiment_section_row", "unique": True},
            ),
            ([("kind", 1), ("strategy", 1)], {"name": "kind_strategy"}),
            ([("section", 1), ("pbo", 1)], {"name": "section_pbo"}),
            ([("horizon", 1), ("pbo", 1)], {"name": "horizon_pbo"}),
        ],
        "comment": "One document per result row, so results can be aggregated across experiments",
    },
    "documents": {
        "validator": _doc(
            {
                "_id": {"bsonType": "string", "description": "kind/slug"},
                "kind": {
                    "enum": ["coin-intelligence", "research", "component", "strategy-cards"]
                },
                "slug": {"bsonType": "string"},
                "title": {"bsonType": "string"},
                "body": {"bsonType": "string"},
                "words": {"bsonType": "int"},
            },
            ["_id", "kind", "slug", "body"],
        ),
        "indexes": [
            ([("kind", 1), ("slug", 1)], {"name": "kind_slug", "unique": True}),
            # One text index per collection is the server limit; this is the one.
            ([("title", "text"), ("body", "text")], {"name": "fulltext"}),
        ],
        "comment": "Markdown reference: coin spokes, research prose, component docs",
    },
    "test_results": {
        "validator": _doc(
            {
                "suite": {"enum": ["backtester", "soltui", "extension"]},
                "count": {"bsonType": "int"},
                "ok": {"bsonType": "bool"},
                "recorded_at": {"bsonType": "date"},
                "git_sha": {"bsonType": "string"},
            },
            ["suite", "count", "ok", "recorded_at", "git_sha"],
        ),
        "indexes": [
            ([("suite", 1), ("recorded_at", -1)], {"name": "suite_recent"}),
            ([("git_sha", 1), ("suite", 1)], {"name": "sha_suite", "unique": True}),
        ],
        "comment": "A suite-count snapshot per commit, so growth is queryable over time",
    },
}

ALL_COLLECTIONS = (*TIME_SERIES, *COLLECTIONS)


def connect(uri: str = "mongodb://localhost:27017"):
    """A client for the local server.

    Import is local so `--describe` works without pymongo installed, which keeps
    the layout readable from a checkout that has not run
    `pip install -r mongo/requirements.txt`.
    """
    from pymongo import MongoClient

    # serverSelectionTimeoutMS so a missing local server fails in seconds with a
    # clear message rather than blocking for the 30s default.
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def create(db, *, drop: bool = True) -> list[str]:
    """Create every collection with its validator and indexes.

    Drops first by default: this store is derived from files in the repo, so
    recreating it is always safe and is the only way to keep the time series
    collections idempotent (they accept no unique index, so a second load would
    silently double every measurement).
    """
    from pymongo.errors import CollectionInvalid

    created = []
    for name, spec in TIME_SERIES.items():
        if drop:
            db.drop_collection(name)
        try:
            db.create_collection(name, timeseries=spec["timeseries"])
        except CollectionInvalid:
            # Already present and not dropped; the caller asked for that.
            pass
        created.append(name)

    for name, spec in COLLECTIONS.items():
        if drop:
            db.drop_collection(name)
        try:
            db.create_collection(
                name,
                validator=spec["validator"],
                validationLevel="strict",
                validationAction="error",
            )
        except CollectionInvalid:
            db.command(
                "collMod",
                name,
                validator=spec["validator"],
                validationLevel="strict",
                validationAction="error",
            )
        for keys, options in spec["indexes"]:
            db[name].create_index(keys, **options)
        created.append(name)

    return created


def describe() -> str:
    """The layout as text, with no server involved."""
    lines = [f"database: {DB_NAME}", "", "time series collections:"]
    for name, spec in TIME_SERIES.items():
        ts = spec["timeseries"]
        lines.append(
            f"  {name:<16} timeField={ts['timeField']} metaField={ts['metaField']} "
            f"granularity={ts['granularity']}"
        )
        lines.append(f"  {'':<16} {spec['comment']}")
    lines += ["", "regular collections:"]
    for name, spec in COLLECTIONS.items():
        required = spec["validator"]["$jsonSchema"]["required"]
        lines.append(f"  {name:<16} required={', '.join(required)}")
        lines.append(f"  {'':<16} {spec['comment']}")
        for keys, options in spec["indexes"]:
            shape = ", ".join(f"{k}:{v}" for k, v in keys)
            flags = " unique" if options.get("unique") else ""
            lines.append(f"  {'':<16}   index {options['name']}({shape}){flags}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--create", action="store_true", help="create collections (drops first)")
    ap.add_argument("--describe", action="store_true", help="print the layout and exit")
    ap.add_argument("--uri", default="mongodb://localhost:27017")
    ap.add_argument(
        "--keep",
        action="store_true",
        help="with --create, do not drop existing collections first",
    )
    args = ap.parse_args(argv)

    if args.describe or not args.create:
        print(describe())
        return 0

    db = connect(args.uri)[DB_NAME]
    created = create(db, drop=not args.keep)
    print(f"{DB_NAME}: {len(created)} collections ready")
    for name in created:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
