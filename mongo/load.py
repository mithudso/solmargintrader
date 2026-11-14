"""Load the repo's research artifacts into the local MongoDB store.

    pip install -r mongo/requirements.txt
    python3 mongo/load.py                  # everything
    python3 mongo/load.py --only bars,strategies
    python3 mongo/load.py --dry-run        # count what would load, write nothing

Derived artifact collections are dropped and rebuilt to prevent duplicate time
series measurements. Test receipts are original observations with no backing file.
They are retained across reloads and upserted by (git_sha, suite) only when suites
are actually run. `mongo/tests/test_load.py` checks derived-load idempotence.

Scope: only the collections named in `mongo/schema.py`, only in the
`solmargintrader` database. The same server hosts unrelated databases and this
touches none of them.

Every document carries `source_path`, `source_sha256` and `loaded_at`. A number
without provenance is not worth storing -- the same reason `RunManifest` exists and
`decide.py` prints a data checksum. For bars the frame checksum from
`backtester.core.data.checksum_frame` is recorded too, so a row here can be tied to
the exact frame a backtest or readout saw.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from mongo.schema import DB_NAME, connect, create

LOADED_AT = datetime.now(UTC)


# --------------------------------------------------------------------------
# provenance and coercion
# --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_snapshot(path: Path) -> tuple[bytes, dict[str, Any]]:
    """Read once and bind provenance to exactly those bytes."""
    raw = path.read_bytes()
    return raw, {
        "source_path": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path.resolve()),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "loaded_at": LOADED_AT,
    }


def provenance(path: Path) -> dict[str, Any]:
    """Provenance for metadata-only callers; parsed data uses source_snapshot."""
    return source_snapshot(path)[1]


def clean(value: Any) -> Any:
    """Make a value BSON-safe.

    numpy scalars, NaN and infinity all need handling: pymongo cannot encode a
    `numpy.float64`, and BSON has no NaN that survives a round trip usefully, so a
    non-finite number becomes None rather than a value a later query would compare
    against and silently mis-rank.
    """
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        # numpy scalar
        try:
            value = value.item()
        except (AttributeError, ValueError):  # pragma: no cover - defensive
            return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def maybe_number(text: str) -> Any:
    """Parse a CSV cell as int or float when it looks like one, else keep the text."""
    stripped = text.strip()
    if stripped == "":
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        number = float(stripped)
    except ValueError:
        return stripped
    return number if math.isfinite(number) else None


def read_csv_snapshot(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw, prov = source_snapshot(path)
    rows = [
        {key: maybe_number(val) for key, val in row.items() if key is not None}
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    ]
    return rows, prov


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """CSV rows as dicts, with numeric cells parsed."""
    return read_csv_snapshot(path)[0]


def read_bar_snapshot(path: Path, interval: str):
    import pandas as pd

    from backtester.core.data import validate_bars
    raw, prov = source_snapshot(path)
    return validate_bars(pd.read_csv(io.BytesIO(raw)), interval, strict_gaps=False), prov


def git_sha() -> str:
    """Short HEAD sha, or 'unknown' outside a repo."""
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else "unknown"


def utc(epoch_seconds: float) -> datetime:
    """A UTC datetime from epoch seconds, which is how the CSVs store time."""
    return datetime.fromtimestamp(int(epoch_seconds), tz=UTC)


def observation_time(row: dict[str, Any], path: Path, index: int, *fields: str) -> datetime:
    """A declared financial observation cannot disappear because its time is absent."""
    value = next((row[name] for name in fields if row.get(name) is not None), None)
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("missing or invalid timestamp")
        return utc(value)
    except (ValueError, TypeError, OverflowError, OSError) as error:
        label = path.relative_to(REPO) if path.is_relative_to(REPO) else path.name
        raise ValueError(f"{label}: CSV row {index}: missing or invalid timestamp") from error


# --------------------------------------------------------------------------
# loaders -- one per collection, each returning the documents to insert
# --------------------------------------------------------------------------


def bar_files() -> list[tuple[Path, str, str]]:
    """Cached OHLCV files, excluding other cache contracts before bar loading."""
    from backtester.core.types import BAR_COLUMNS, INTERVAL_SECONDS

    found = []
    for path in sorted((REPO / "data").glob("*.csv")):
        stem = path.stem
        if "_" not in stem:
            continue
        asset, interval = stem.rsplit("_", 1)
        # JLP_spot.csv is a price snapshot, not a bar series; it has its own loader.
        if interval not in INTERVAL_SECONDS:
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            columns = set(next(csv.reader(handle), []))
        if not set(BAR_COLUMNS).issubset(columns):
            # Funding/tick snapshots share the data directory but are not bars.
            if ({'timestamp', 'funding_rate', 'premium'}.issubset(columns) or
                    {'timestamp', 'trade_id', 'price', 'size', 'side'}.issubset(columns)):
                continue
            raise ValueError(f"{path.name} has ambiguous or missing OHLCV bar columns")
        found.append((path, asset, interval))
    return found


def bar_source(path: Path, asset: str) -> dict[str, Any]:
    """Alternate caches declare their venue/quote in the exact-series sidecar."""
    sidecar = path.with_suffix(".source.json")
    if not sidecar.exists():
        # The original CsvLoader/fetch cache contract is Coinbase USD. Alternate
        # fetchers publish an explicit source sidecar beside the same CSV name.
        return {"source": "coinbase", "venue": "coinbase", "pair": f"{asset}-USD", "quote": "USD"}
    raw, prov = source_snapshot(sidecar)
    metadata = json.loads(raw.decode("utf-8"))
    if not isinstance(metadata, dict) or metadata.get("asset") != asset:
        raise ValueError(f"{sidecar}: source metadata asset does not match the bar cache")
    for key in ("venue", "pair", "quote"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"{sidecar}: source metadata requires {key}")
    from backtester.core.fetch_minutes_alt import VENUES
    venue = metadata["venue"]
    if venue == "coinbase":
        expected_pair = f"{asset}-USD"
    else:
        expected_pair = VENUES[venue].pair(asset) if venue in VENUES else None
    expected_quote = "USD" if venue == "coinbase" else "USDT"
    if metadata["quote"] != expected_quote or metadata["pair"] != expected_pair:
        raise ValueError(f"{sidecar}: unsupported or inconsistent venue/pair/quote identity")
    return {"source": metadata["venue"], **{key: metadata[key] for key in ("venue", "pair", "quote")},
            "source_metadata": metadata, "source_metadata_provenance": prov}


def load_bars() -> list[dict[str, Any]]:
    """One measurement per bar, with the series identity in the metaField."""
    from backtester.core.data import checksum_frame

    docs: list[dict[str, Any]] = []
    for path, asset, interval in bar_files():
        frame, prov = read_bar_snapshot(path, interval)
        meta = {
            "asset": asset,
            "interval": interval,
            **bar_source(path, asset),
            **prov,
            # The frame checksum, not the file checksum: this is the identity a
            # backtest or a readout reports, so a bar here can be tied to the run
            # that saw it.
            "frame_checksum": checksum_frame(frame),
            "bars": len(frame),
        }
        for row in frame.itertuples(index=False):
            docs.append(
                {
                    "ts": utc(row.timestamp),
                    "series": meta,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                    "loaded_at": prov["loaded_at"],
                }
            )
    return docs


def load_spot_prices() -> list[dict[str, Any]]:
    """The Jupiter price snapshot. Not OHLCV -- different columns entirely."""
    path = REPO / "data" / "JLP_spot.csv"
    if not path.exists():
        return []
    docs = []
    table, prov = read_csv_snapshot(path)
    for row in table:
        docs.append(
            {
                "ts": utc(row["timestamp"]),
                "snapshot": {
                    "mint": row.get("mint"),
                    "source": row.get("source"),
                    **prov,
                },
                "usd_price": float(row["usd_price"]),
                "iso": row.get("iso"),
                "loaded_at": LOADED_AT,
            }
        )
    return docs


def load_strategies() -> list[dict[str, Any]]:
    """One document per strategy card, with live registry facts where they exist.

    No invented `registered` flag: `registry_key` is null for cards that are
    not `Strategy` implementations, and `status` and `runner` carry the rest -- the
    ladder grid is `implemented` with no registry key because it is not a `Strategy`
    at all.
    """
    from backtester.core import strategy_cards as cards_mod
    from backtester.core.strategies import FAMILY, REGISTRY, build

    docs = []
    snapshots: dict[Path, dict[str, Any]] = {}

    def read_card(path: Path) -> str:
        raw, prov = source_snapshot(path)
        snapshots[path] = prov
        return raw.decode("utf-8")

    for card in cards_mod.load_all(read_text=read_card).values():
        path = Path(card.path)
        registry: dict[str, Any] | None = None
        if card.registry_key and card.registry_key in REGISTRY:
            live = build(card.registry_key)
            registry = {
                "key": card.registry_key,
                "class_name": type(live).__name__,
                "family": FAMILY.get(card.registry_key),
                "instance_name": live.name,
                "params": clean(dict(getattr(live, "params", {}))),
                "warmup_bars": int(live.warmup_bars()),
            }
        docs.append(
            {
                "_id": card.id,
                "name": card.name,
                "kind": card.kind,
                "status": card.status,
                "family": card.family,
                "summary": card.summary,
                "registry_key": card.registry_key,
                "runner": card.runner,
                "warmup_bars": card.warmup_bars,
                "evaluation": card.evaluation,
                "data_required": list(card.data_required),
                "data_available": bool(card.data_available),
                "success_likelihood": card.success_likelihood,
                "success_basis": card.success_basis,
                "params": clean(card.params),
                "presets": clean(card.presets),
                "body": card.body,
                "registry": registry,
                **snapshots[path],
            }
        )
    return docs


def load_signals() -> list[dict[str, Any]]:
    """The stateless one-bar rules, including which strategy defaults each mirrors."""
    from research import decide

    path = REPO / "research" / "decide.py"
    # Three rules take their periods from a registered strategy's own defaults so
    # the two cannot drift; recording which lets a reader follow that link.
    tracks = {
        f"donchian_{decide.DONCHIAN['entry_lookback']}_{decide.DONCHIAN['exit_lookback']}": "breakout",
        "ichimoku_cloud": "ichimoku",
        f"ts_momentum_{decide.TS_MOMENTUM['window']}": "ts_momentum",
    }
    return [
        {
            "_id": rule.key,
            "rule": rule.rule,
            "tracks_strategy": tracks.get(rule.key),
            **provenance(path),
        }
        for rule in decide.SIGNAL_RULES
    ]


def load_indicators() -> list[dict[str, Any]]:
    """The reported indicator rows plus the functions deliberately not reported."""
    from research import decide

    path = REPO / "research" / "decide.py"
    docs = [
        {
            "_id": row.key,
            "reported": True,
            "sources": list(row.sources),
            "skip_reason": None,
            **provenance(path),
        }
        for row in decide.INDICATOR_ROWS
    ]
    docs += [
        {
            "_id": name,
            "reported": False,
            "sources": [name],
            "skip_reason": reason,
            **provenance(path),
        }
        for name, reason in sorted(decide.INDICATOR_SKIP.items())
    ]
    return docs


def load_decisions() -> list[dict[str, Any]]:
    """A readout per cached series, stored exactly as `build_report()` emits it.

    Re-deriving a Mongo-specific shape here would let the store and the readout
    disagree about what a strategy said, which is the one thing this must not do.
    """
    from backtester.core.data import checksum_frame, frame_to_arrays
    from research import decide

    docs = []
    for path, asset, interval in bar_files():
        frame, prov = read_bar_snapshot(path, interval)
        report = decide.build_report(
            frame_to_arrays(frame),
            asset=asset,
            interval=interval,
            source=str(path.relative_to(REPO)),
            checksum=checksum_frame(frame),
        )
        docs.append({**clean(report), **prov})
    return docs


def run_context() -> tuple[dict[str, Any], dict[str, Any]] | None:
    path = REPO / "results" / "run_manifest.json"
    if not path.exists():
        return None
    raw, prov = source_snapshot(path)
    manifest = json.loads(raw.decode("utf-8"))
    names = manifest.get("strategies") if isinstance(manifest, dict) else None
    if not isinstance(names, (dict, list)) or any(
        not isinstance(name, str) or not name or "/" in name or "\\" in name or "\x00" in name
        for name in names
    ):
        raise ValueError("run manifest has invalid strategy identities")
    return manifest, prov


def artifact_rows(path: Path, context: tuple[dict[str, Any], dict[str, Any]]):
    try:
        table, prov = read_csv_snapshot(path)
    except OSError as exc:
        raise ValueError(f"missing or unreadable declared run artifact {path.name}; regenerate the run") from exc
    inventory = context[0].get("artifact_sha256")
    if not isinstance(inventory, dict) or inventory.get(path.name) != prov["source_sha256"]:
        raise ValueError(f"run artifact {path.name} lacks matching manifest hash proof; regenerate the run")
    return table, prov


def load_backtest_runs(*, run_snapshot=None) -> list[dict[str, Any]]:
    """One manifest and its proven comparison artifact."""
    context = run_snapshot if run_snapshot is not None else run_context()
    if context is None:
        return []
    manifest, prov = context
    comparison = REPO / "results" / "comparison.csv"
    results, comparison_prov = artifact_rows(comparison, context)
    return [{"_id": run_identifier(manifest), "manifest": clean(manifest),
             **{key:manifest.get(key) for key in ("asset", "interval", "mode")},
             "results": clean(results), "comparison": clean(results),
             "comparison_provenance": comparison_prov, **prov}]


def run_identifier(manifest: dict[str, Any]) -> str:
    """A stable id for a run, including economics and artifact identity."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
    identity = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return "-".join([str(manifest.get(k, "?")) for k in ("asset", "interval", "mode")] + [identity])


def load_equity_points(*, run_snapshot=None) -> list[dict[str, Any]]:
    context = run_snapshot if run_snapshot is not None else run_context()
    if context is None:
        return []
    manifest, manifest_prov = context
    run_id = run_identifier(manifest)
    docs = []
    for strategy in sorted(manifest["strategies"]):
        path = REPO / "results" / f"equity_{strategy}.csv"
        table, prov = artifact_rows(path, context)
        meta = {"run_id": run_id, "strategy": strategy, "manifest_provenance": manifest_prov, **prov}
        for index, row in enumerate(table, 2):
            ts = observation_time(row, path, index, "timestamp", "ts")
            equity = row.get("equity")
            if isinstance(equity, bool) or not isinstance(equity, (int, float)) or not math.isfinite(equity) or equity < 0:
                raise ValueError(f"{path.name}: CSV row {index}: invalid equity")
            docs.append({"ts": ts, "curve": meta, "equity": float(equity), "loaded_at": LOADED_AT})
    return docs


def protected_row(row: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    reserved = set(metadata) | {"_id", "source_fields"}
    result = {k: clean(v) for k, v in row.items() if k not in reserved}
    collisions = {k: clean(v) for k, v in row.items() if k in reserved}
    if collisions:
        result["source_fields"] = collisions
    return {**result, **metadata}


def load_trades(*, run_snapshot=None) -> list[dict[str, Any]]:
    context = run_snapshot if run_snapshot is not None else run_context()
    if context is None:
        return []
    manifest, manifest_prov = context
    run_id = run_identifier(manifest)
    docs = []
    for strategy in sorted(manifest["strategies"]):
        path = REPO / "results" / f"trades_{strategy}.csv"
        table, prov = artifact_rows(path, context)
        for index, row in enumerate(table, 2):
            ts = observation_time(row, path, index, "ts", "timestamp")
            data = {k: v for k, v in row.items() if k not in ("ts", "timestamp")}
            if "price" in data:
                price = data["price"]
                if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
                    raise ValueError(f"{path.name}: CSV row {index}: invalid trade price")
                data["price"] = float(price)
            docs.append(protected_row(data, {"run_id": run_id, "strategy": strategy, "ts": ts,
                                            "manifest_provenance": manifest_prov, **prov}))
    return docs


# research/results filename prefix -> experiment kind.
EXPERIMENT_KINDS: tuple[tuple[str, str], ...] = (
    ("cpcv_all25", "cross-asset"),
    ("cpcv_top5", "cross-asset"),
    ("cpcv_combos", "cpcv"),
    ("cpcv", "cpcv"),
    ("sweep", "sweep"),
    ("perturb", "perturbation"),
    ("geometry", "geometry"),
    ("top_coins", "top-coins"),
    ("configuration_counts", "counts"),
)


def experiment_kind(name: str) -> str | None:
    """The kind a research-results filename belongs to, longest prefix first."""
    for prefix, kind in EXPERIMENT_KINDS:
        if name.startswith(prefix):
            return kind
    return None


def read_sidecar(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """A result sidecar as (summary object, summary rows).

    Sidecars come in two shapes, and the difference matters. `cpcv_pbo.json` and the
    `geometry_*_k2.json` files hold a **list** of results -- one PBO per horizon, or
    per (blocks, k) geometry. Those are rows, and storing them as one opaque blob
    would make the single most queryable number in the research set ("PBO by
    horizon") unreachable without client-side parsing. Only a genuine object is kept
    as `summary`.
    """
    summary, rows, _ = read_sidecar_snapshot(path)
    return summary, rows


def read_sidecar_snapshot(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any] | None]:
    """Bind parsed sidecar values to the exact bytes that supplied them."""
    if not path.exists():
        return None, [], None
    raw, prov = source_snapshot(path)
    payload = clean(json.loads(raw.decode("utf-8")))
    if isinstance(payload, list):
        return None, [row for row in payload if isinstance(row, dict)], prov
    if isinstance(payload, dict):
        return payload, [], prov
    # A scalar or string sidecar: keep it addressable rather than dropping it.
    return {"value": payload}, [], prov


def experiment_row(row: dict[str, Any], *, experiment_id: str, kind: str,
                   section: str, index: int, prov: dict[str, Any]) -> dict[str, Any]:
    """Keep source values without allowing them to overwrite loader identity."""
    metadata = {"experiment_id": experiment_id, "kind": kind, "section": section, "row": index, **prov}
    return protected_row(row, metadata)


def load_experiments() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Experiment metadata and its rows, as two collections.

    Rows are separate documents rather than an array: `cpcv_combos_results.csv`
    alone has 1,212 of them, and an array that large is both the unbounded-array
    antipattern and unaggregatable -- which would defeat the point of loading it.
    """
    results_dir = REPO / "research" / "results"
    if not results_dir.is_dir():
        return [], []

    experiments: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for path in sorted(results_dir.glob("*.csv")):
        name = path.stem
        kind = experiment_kind(name)
        if kind is None:
            continue
        table, prov = read_csv_snapshot(path)
        experiment_id = f"{kind}/{name}"

        summary, summary_rows, summary_prov = read_sidecar_snapshot(path.with_suffix(".json"))
        experiments.append(
            {
                "_id": experiment_id,
                "kind": kind,
                "name": name,
                "row_count": len(table),
                "summary_row_count": len(summary_rows),
                "columns": sorted({k for row in table for k in row}),
                "summary": summary,
                "summary_provenance": summary_prov,
                **prov,
            }
        )
        for index, row in enumerate(table):
            rows.append(experiment_row(row, experiment_id=experiment_id, kind=kind,
                                       section="result", index=index, prov=prov))
        for index, row in enumerate(summary_rows):
            rows.append(experiment_row(row, experiment_id=experiment_id, kind=kind,
                                       section="summary", index=index, prov=summary_prov))

    # JSON-only experiments: a sidecar with no CSV beside it still carries results.
    for path in sorted(results_dir.glob("*.json")):
        if path.with_suffix(".csv").exists():
            continue
        kind = experiment_kind(path.stem)
        if kind is None:
            continue
        experiment_id = f"{kind}/{path.stem}"
        summary, summary_rows, prov = read_sidecar_snapshot(path)
        experiments.append(
            {
                "_id": experiment_id,
                "kind": kind,
                "name": path.stem,
                "row_count": 0,
                "summary_row_count": len(summary_rows),
                "columns": [],
                "summary": summary,
                "summary_provenance": prov,
                **prov,
            }
        )
        for index, row in enumerate(summary_rows):
            rows.append(experiment_row(row, experiment_id=experiment_id, kind=kind,
                                       section="summary", index=index, prov=prov))

    return experiments, rows


DOCUMENT_SOURCES: tuple[tuple[str, str], ...] = (
    ("research/coin-intelligence", "coin-intelligence"),
    ("research", "research"),
    ("docs", "component"),
    ("backtester/strategy_cards", "strategy-cards"),
)


def first_heading(text: str, fallback: str) -> str:
    """The document's first markdown heading, or `fallback`."""
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip() or fallback
    return fallback


def load_documents() -> list[dict[str, Any]]:
    """Markdown reference material: coin spokes, research prose, component docs."""
    docs = []
    seen: set[str] = set()
    for rel_dir, kind in DOCUMENT_SOURCES:
        directory = REPO / rel_dir
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            slug = path.stem
            key = f"{kind}/{slug}"
            if key in seen:
                continue
            seen.add(key)
            raw, prov = source_snapshot(path)
            body = raw.decode("utf-8")
            docs.append(
                {
                    "_id": key,
                    "kind": kind,
                    "slug": slug,
                    "title": first_heading(body, slug),
                    "body": body,
                    "words": len(body.split()),
                    **prov,
                }
            )
    return docs


# A suite result comes from a live run, so there is no file to checksum; the
# provenance fields carry the test directory and say so explicitly rather than
# leaving a checksum that looks like a hash of something.
SUITE_PATHS: dict[str, str] = {
    "backtester": "backtester/tests",
    "soltui": "soltui/tests",
    "extension": "extension/test",
}

SUITE_COMMANDS: dict[str, list[str]] = {
    # An explicit venv interpreter does not activate its directory on PATH.
    # Keep test observations in the same environment as the loader.
    "backtester": [sys.executable, "-m", "unittest", "discover", "-s", "backtester/tests", "-t", "."],
    "soltui": [sys.executable, "-m", "unittest", "discover", "-s", "soltui/tests", "-t", "."],
}


def load_test_results(*, run_suites: bool, skip: Iterable[str] = ()) -> list[dict[str, Any]]:
    """Suite counts and outcomes, from an actual run.

    `run_suites=False` records nothing rather than recording a count with a guessed
    `ok`. A test result that was never observed is not a test result.
    """
    if not run_suites:
        return []
    sha = git_sha()
    docs = []
    skip = set(skip)

    for suite, command in SUITE_COMMANDS.items():
        if suite in skip:
            continue
        done = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        match = re.search(r"^Ran (\d+) tests?", done.stderr, re.MULTILINE)
        docs.append(
            {
                "suite": suite,
                "count": int(match.group(1)) if match else 0,
                "ok": done.returncode == 0,
                "recorded_at": datetime.now(UTC),
                "git_sha": sha,
                "command": " ".join(command),
                "source_path": SUITE_PATHS[suite],
                "source_sha256": "live-run-not-a-file",
                "loaded_at": LOADED_AT,
            }
        )

    if "extension" not in skip:
        done = subprocess.run(
            ["npm", "test"], cwd=REPO / "extension", capture_output=True, text=True, check=False
        )
        match = re.search(r"^# tests (\d+)$", done.stdout, re.MULTILINE) or re.search(
            r"tests (\d+)", done.stdout
        )
        docs.append(
            {
                "suite": "extension",
                "count": int(match.group(1)) if match else 0,
                "ok": done.returncode == 0,
                "recorded_at": datetime.now(UTC),
                "git_sha": sha,
                "command": "npm test",
                "source_path": SUITE_PATHS["extension"],
                "source_sha256": "live-run-not-a-file",
                "loaded_at": LOADED_AT,
            }
        )
    return docs


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------

# Collection -> callable returning its documents. `experiments` is special-cased
# because it produces two collections from one pass over the files.
SIMPLE_LOADERS: dict[str, Any] = {
    "bars": load_bars,
    "spot_prices": load_spot_prices,
    "strategies": load_strategies,
    "signals": load_signals,
    "indicators": load_indicators,
    "decisions": load_decisions,
    "backtest_runs": load_backtest_runs,
    "equity_points": load_equity_points,
    "trades": load_trades,
    "documents": load_documents,
}


def build_all(
    only: set[str] | None, *, run_suites: bool, skip_suites: Iterable[str] = ()
) -> dict[str, list[dict[str, Any]]]:
    """Every document to insert, keyed by collection."""
    wanted = (
        set(SIMPLE_LOADERS) | {"experiments", "experiment_rows", "test_results"}
        if only is None
        else only
    )
    batches: dict[str, list[dict[str, Any]]] = {}

    backtest_names = {"backtest_runs", "equity_points", "trades"}
    context = run_context() if wanted & backtest_names else None
    for name, loader in SIMPLE_LOADERS.items():
        if name in wanted:
            batches[name] = ([] if context is None else loader(run_snapshot=context)) if name in backtest_names else loader()

    if {"experiments", "experiment_rows"} & wanted:
        experiments, rows = load_experiments()
        if "experiments" in wanted:
            batches["experiments"] = experiments
        if "experiment_rows" in wanted:
            batches["experiment_rows"] = rows

    if "test_results" in wanted and run_suites:
        batches["test_results"] = load_test_results(
            run_suites=run_suites, skip=skip_suites
        )

    return batches


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog="Example: .venv/bin/python mongo/load.py --dry-run --only signals,indicators")
    ap.add_argument("--uri", default="mongodb://localhost:27017")
    ap.add_argument(
        "--only",
        default=None,
        help="comma-separated collection names; default is every collection",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="build the documents and report counts without touching the server",
    )
    ap.add_argument(
        "--run-tests",
        action="store_true",
        help="run the suites and record real counts into test_results (~85s)",
    )
    ap.add_argument(
        "--skip-suite",
        action="append",
        default=[],
        choices=["backtester", "soltui", "extension"],
        help="repeatable; with --run-tests, skip this suite",
    )
    args = ap.parse_args(argv)

    only = None
    if args.only is not None:
        from mongo.schema import ALL_COLLECTIONS

        names = [name.strip() for name in args.only.split(",")]
        if not all(names):
            print("error: --only requires a nonempty list of collection names", file=sys.stderr)
            return 2
        only = set(names)
        unknown = only - set(ALL_COLLECTIONS)
        if unknown:
            print(f"error: unknown collection(s): {sorted(unknown)}", file=sys.stderr)
            return 2

    batches = build_all(only, run_suites=args.run_tests, skip_suites=args.skip_suite)
    from mongo.schema import validate_batches
    validate_batches(batches)

    if args.dry_run:
        for name, docs in sorted(batches.items()):
            print(f"{name:<18} {len(docs):>7,} documents")
        print(f"{'TOTAL':<18} {sum(len(d) for d in batches.values()):>7,}")
        return 0

    db = connect(args.uri)[DB_NAME]
    # Schema changes, indexes and drops all obey the same explicit selection.
    rebuilt = set(batches) - {"test_results"}
    if rebuilt:
        create(db, drop=True, only=rebuilt)
    if batches.get("test_results"):
        # Test receipts are original observations, rather than derived source
        # artifacts. Retain previous commits and suites omitted by --skip-suite.
        create(db, drop=False, only={"test_results"})

    for name, docs in sorted(batches.items()):
        if name == "test_results":
            for doc in docs:
                db[name].replace_one({"git_sha": doc["git_sha"], "suite": doc["suite"]}, doc, upsert=True)
        elif docs:
            db[name].insert_many(docs, ordered=False)
        print(f"{name:<18} {len(docs):>7,} documents")

    print(f"\n{DB_NAME}: {sum(len(d) for d in batches.values()):,} documents loaded")
    return 0


if __name__ == "__main__":
    from mongo.cli import run_cli
    raise SystemExit(run_cli(main, REPO))
