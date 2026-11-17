"""Durable PAPER observer for the frozen joint multi-timeframe oracle model.

Entry and exit prices are fresh observed oracle proxies, never keeper fills.
Only an exact complete public 200ms path can qualify final survival. This
module has no signing, execution adapter, wallet, or funded-service imports.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import signal
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path

from oracle_leverage.store import Store, default_home
from research.oracle_reversal_inputs import ENDPOINT as HISTORY_URL
from research.oracle_reversal_inputs import decode_history

PRICES_URL = "https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/prices"
STREAM_URL = "wss://perps-api.jup.ag/v1/pyth/stream"
INTERVALS = (5, 10, 15, 20)
FEEDS = {"BTC": 1, "ZEC": 66}
GRID_US = 200_000
MAX_MODEL_BYTES = 2 * 1024 * 1024
MAX_PATH_BYTES = 2 * 1024 * 1024
MAX_HISTORY_BYTES = 512 * 1024
# A 20-minute position plus at most one minute of observed exit delay. Longer
# outages remain unscored instead of querying an unbounded historical path.
MAX_PATH_SECONDS = 21 * 60
LIQUIDATION_BPS = Decimal("9.8")


class MtfError(RuntimeError):
    """Fixed public diagnostic codes; raw network errors are never published."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib does not close the response when redirect_request raises.
        fp.close()
        raise MtfError("unexpected_public_redirect")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _json(raw):
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise MtfError("invalid_public_json") from None


def _finite(value, *, positive=False):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and (not positive or value > 0)
    )


def _epoch(value):
    if _finite(value, positive=True):
        return float(value)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError()
        result = parsed.timestamp()
        if not math.isfinite(result) or result <= 0:
            raise ValueError()
        return result
    except (ValueError, TypeError, OverflowError):
        raise MtfError("invalid_model_training_timestamp") from None


def _decimal_price(quote):
    if not isinstance(quote, dict) or not _finite(quote.get("price"), positive=True):
        raise MtfError("invalid_proxy_price")
    raw, exponent = quote.get("raw_price"), quote.get("exponent")
    if raw is None and exponent is None:
        return Decimal(str(quote["price"]))
    if (
        not isinstance(raw, str)
        or not 1 <= len(raw) <= 16
        or not raw.isascii()
        or not raw.isdecimal()
        or not 0 < int(raw) <= 2**53 - 1
        or type(exponent) is not int
        or not -12 <= exponent <= 0
    ):
        raise MtfError("invalid_raw_proxy_units")
    price = Decimal(raw) * Decimal(10) ** exponent
    if not math.isclose(float(price), quote["price"], rel_tol=2e-15, abs_tol=0):
        raise MtfError("raw_proxy_price_mismatch")
    return price


def load_models(value):
    if isinstance(value, (str, Path)):
        with Path(value).open("rb") as stream:
            raw = stream.read(MAX_MODEL_BYTES + 1)
    else:
        try:
            raw = canonical(value).encode()
        except (TypeError, ValueError, RecursionError):
            raise MtfError("invalid_model_bundle") from None
    if len(raw) > MAX_MODEL_BYTES:
        raise MtfError("model_bundle_size_limit")
    bundle = _json(raw)
    if (
        not isinstance(bundle, dict)
        or bundle.get("schema") != "mtf-reversal-live-bundle/v1"
        or not isinstance(bundle.get("models"), dict)
        or set(bundle["models"]) != set(FEEDS)
    ):
        raise MtfError("invalid_model_bundle")
    for asset, model in bundle["models"].items():
        if (
            not isinstance(model, dict)
            or model.get("schema") != "mtf-reversal-model/v1"
            or model.get("asset") != asset
            or model.get("alpha") != 20
            or model.get("min_cell_n") != 20
            or model.get("min_components") != 2
            or not isinstance(model.get("base_models"), dict)
            or set(model["base_models"]) != {str(n) for n in INTERVALS}
        ):
            raise MtfError("invalid_frozen_model")
        _epoch(model.get("trained_through"))
        selected = model.get("selected")
        if selected is not None and (
            not isinstance(selected, dict)
            or type(selected.get("minutes")) is not int
            or selected["minutes"] not in INTERVALS
            or not _finite(selected.get("threshold"))
            or not 0.5 <= selected["threshold"] < 1
            or not isinstance(selected.get("id"), str)
            or not 0 < len(selected["id"]) <= 128
        ):
            raise MtfError("invalid_model_selection")
    return bundle, hashlib.sha256(raw).hexdigest()


def path_grid(entry_at, exit_at):
    if (
        not _finite(entry_at, positive=True)
        or not _finite(exit_at, positive=True)
        or not 0 <= exit_at - entry_at <= MAX_PATH_SECONDS
    ):
        raise MtfError("path_span_exceeds_bounded_window")
    first = int(
        (Decimal(str(entry_at)) * 1_000_000).to_integral_value(rounding=ROUND_CEILING)
    )
    last = int(
        (Decimal(str(exit_at)) * 1_000_000).to_integral_value(rounding=ROUND_FLOOR)
    )
    first = (first + GRID_US - 1) // GRID_US * GRID_US
    last = last // GRID_US * GRID_US
    if first > last:
        raise MtfError("path_has_no_public_grid")
    return first, last


def decode_samples(value, asset, first, last):
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise MtfError("invalid_oracle_samples")
    rows = value["data"]
    expected_count = (last - first) // GRID_US + 1
    if len(rows) != expected_count or expected_count > MAX_PATH_SECONDS * 5 + 1:
        raise MtfError("incomplete_or_extra_sample_grid")
    result = []
    for index, row in enumerate(rows):
        stamp = first + index * GRID_US
        if (
            not isinstance(row, dict)
            or type(row.get("price_feed_id")) is not int
            or row["price_feed_id"] != FEEDS[asset]
            or type(row.get("publish_time")) is not int
            or row["publish_time"] != stamp
            or type(row.get("feed_update_timestamp")) is not int
            or not 0 <= stamp - row["feed_update_timestamp"] <= 1_000_000
            or type(row.get("price")) is not int
            or not 0 < row["price"] <= 2**53 - 1
            or type(row.get("exponent")) is not int
            or not -12 <= row["exponent"] <= 0
        ):
            raise MtfError("invalid_or_missing_sample_grid_point")
        price = Decimal(row["price"]) * Decimal(10) ** row["exponent"]
        result.append({"publish_time_us": stamp, "price": str(price)})
    return result


class OraclePublic:
    """Only the two fixed public GET endpoints; bounded body and wall-clock read."""

    def __init__(self, *, opener=None, clock=time.time, timeout=8):
        if not _finite(timeout, positive=True) or timeout > 8:
            raise MtfError("invalid_public_timeout")
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.clock = clock
        self.timeout = timeout

    def _get(self, url, maximum, cancelled):
        if cancelled():
            raise MtfError("public_request_cancelled")
        deadline = time.monotonic() + self.timeout
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "oracle-mtf-paper/1",
                },
            )
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise MtfError("public_http_status")
                length = response.headers.get("Content-Length")
                if length is not None and (
                    not length.isdigit() or int(length) > maximum
                ):
                    raise MtfError("public_response_size_limit")
                chunks, size = [], 0
                while True:
                    remaining = deadline - time.monotonic()
                    if cancelled():
                        raise MtfError("public_request_cancelled")
                    if remaining <= 0:
                        raise MtfError("public_request_timeout")
                    sock = getattr(
                        getattr(getattr(response, "fp", None), "raw", None),
                        "_sock",
                        None,
                    )
                    if sock is not None:
                        sock.settimeout(remaining)
                    reader = getattr(response, "read1", response.read)
                    chunk = reader(min(65536, maximum + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > maximum:
                        raise MtfError("public_response_size_limit")
                raw = b"".join(chunks)
                if length is not None and len(raw) != int(length):
                    raise MtfError("public_response_truncated")
        except MtfError:
            raise
        except urllib.error.HTTPError as error:
            error.close()
            raise MtfError("public_http_status") from None
        except Exception:  # noqa: BLE001 - no raw public provider errors reach status.
            raise MtfError("public_request_unavailable") from None
        return raw, {
            "url": url,
            "received_at": self.clock(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }

    def history(self, asset, start, last, *, cancelled):
        if asset not in FEEDS:
            raise MtfError("unsupported_oracle_asset")
        url = (
            HISTORY_URL
            + "?"
            + urllib.parse.urlencode(
                {"symbol": asset + "USD", "resolution": "1", "from": start, "to": last}
            )
        )
        raw, proof = self._get(url, MAX_HISTORY_BYTES, cancelled)
        try:
            rows = decode_history(_json(raw), start, last)
        except (ValueError, TypeError, KeyError, MtfError):
            raise MtfError("incomplete_or_invalid_oracle_history") from None
        return {"rows": rows, "proof": proof}

    def path(self, asset, entry_at, exit_at, *, cancelled):
        if asset not in FEEDS:
            raise MtfError("unsupported_oracle_asset")
        first, last = path_grid(entry_at, exit_at)
        url = (
            PRICES_URL
            + "?"
            + urllib.parse.urlencode(
                {"feedId": FEEDS[asset], "fromMs": first // 1000, "toMs": last // 1000}
            )
        )
        raw, proof = self._get(url, MAX_PATH_BYTES, cancelled)
        proof.update({"first_us": first, "last_us": last})
        try:
            points = decode_samples(_json(raw), asset, first, last)
            return {"status": "complete", "points": points, "proof": proof, "raw": raw}
        except MtfError as error:
            return {
                "status": "pending",
                "error": str(error),
                "proof": proof,
                "raw": raw,
            }


class Ledger:
    def __init__(self, root):
        self.home = Path(root) / "mtf"
        self.home.mkdir(mode=0o700, exist_ok=True)
        stat = self.home.lstat()
        if self.home.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise MtfError("mtf_directory_permissions_invalid")
        self.path = self.home / "ledger.sqlite3"
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        stat = os.fstat(descriptor)
        os.close(descriptor)
        if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise MtfError("mtf_ledger_permissions_invalid")
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions(
                    id TEXT PRIMARY KEY,asset TEXT NOT NULL,model_sha TEXT NOT NULL,
                    base_minutes INTEGER NOT NULL,target_start INTEGER NOT NULL,target_end INTEGER NOT NULL,
                    direction TEXT NOT NULL,status TEXT NOT NULL,decision_at REAL NOT NULL,
                    committed_at REAL,entry_price REAL NOT NULL,entry_quote_json TEXT NOT NULL,
                    context_json TEXT NOT NULL,scores_json TEXT NOT NULL,selection_json TEXT NOT NULL,
                    observed_liquidation INTEGER NOT NULL DEFAULT 0,observed_touch_json TEXT,
                    exit_decision_at REAL,exit_price REAL,exit_quote_json TEXT,
                    direction_correct INTEGER,survived INTEGER,paper_win INTEGER,gross_bps REAL,
                    path_json TEXT,last_error TEXT,
                    UNIQUE(asset,target_start));
                CREATE UNIQUE INDEX IF NOT EXISTS one_unresolved_asset ON decisions(asset)
                    WHERE status IN ('open','pending');
                CREATE TABLE IF NOT EXISTS path_attempts(
                    id INTEGER PRIMARY KEY,decision_id TEXT NOT NULL,at REAL NOT NULL,
                    status TEXT NOT NULL,error TEXT,proof_json TEXT NOT NULL,raw_zlib BLOB);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def bind(self, bundle, sha):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT value FROM meta WHERE key='model_sha256'"
            ).fetchone()
            if row and json.loads(row[0]) != sha:
                raise MtfError("mtf_model_change_refused")
            saved = db.execute("SELECT value FROM meta WHERE key='models'").fetchone()
            if saved and canonical(json.loads(saved[0])) != canonical(bundle):
                raise MtfError("mtf_stored_model_binding_mismatch")
            for key, value in (("model_sha256", sha), ("models", bundle)):
                db.execute(
                    "INSERT OR IGNORE INTO meta VALUES(?,?)", (key, canonical(value))
                )

    def rows(self, *, unresolved=False):
        with self.connect() as db:
            suffix = "WHERE status IN ('open','pending')" if unresolved else ""
            rows = db.execute(
                "SELECT * FROM decisions "
                + suffix
                + " ORDER BY decision_at DESC LIMIT 200"
            ).fetchall()
        return [dict(row) for row in rows]

    def performance(self):
        with self.connect() as db:
            query = """SELECT count(*) AS decisions,
                coalesce(sum(status='open'),0) AS open,
                coalesce(sum(status='pending'),0) AS pending_unscored,
                coalesce(sum(status='settled'),0) AS settled,
                coalesce(sum(paper_win),0) AS paper_wins,
                coalesce(sum(direction_correct),0) AS directional_correct,
                coalesce(sum(observed_liquidation),0) AS observed_failures,
                coalesce(sum(status='settled' AND survived=0),0) AS verified_liquidations,
                avg(CASE WHEN status='settled' THEN gross_bps END) AS mean_unlevered_gross_bps
                FROM decisions"""
            overall = dict(db.execute(query).fetchone())
            by_asset = {
                asset: dict(db.execute(query + " WHERE asset=?", (asset,)).fetchone())
                for asset in FEEDS
            }
        for values in [overall, *by_asset.values()]:
            count = values["settled"]
            values.update(
                {
                    "correct": values["paper_wins"],
                    "direction_correct": values["directional_correct"],
                    "hit_rate": values["paper_wins"] / count if count else None,
                    "direction_hit_rate": values["directional_correct"] / count
                    if count
                    else None,
                    "mean_gross_bps": values["mean_unlevered_gross_bps"],
                    "mean_net_bps": None,
                    "gross_semantics": "Unlevered directional close return; liquidation reported separately",
                    "net_semantics": "Unavailable: keeper fills and fees are not qualified",
                }
            )
        return {**overall, "overall": overall, "by_asset": by_asset}


def adverse_touch(direction, entry, price):
    entry, price = Decimal(str(entry)), Decimal(str(price))
    adverse = (entry - price) if direction == "UP" else (price - entry)
    return adverse * 10_000 >= entry * LIQUIDATION_BPS


class MtfForward:
    def __init__(
        self,
        home,
        models,
        *,
        public=None,
        analysis=None,
        clock=time.time,
        stop_event=None,
    ):
        self.parent = Store(home)
        self.ledger = Ledger(self.parent.home)
        self.bundle, self.model_sha = load_models(models)
        if analysis is None:
            from research import mtf_reversal as analysis
        self.analysis = analysis
        self.public = public or OraclePublic(clock=clock)
        self.clock = clock
        self.stop_event = stop_event or threading.Event()
        self._lock = None
        self._pool = None
        self._publisher = None
        self._state_lock = threading.Lock()
        self._state = {
            "status": "starting",
            "assets": {
                asset: {
                    "status": "waiting-completed-history",
                    "frames": {},
                    "scores": {},
                    "selected": copy.deepcopy(self.bundle["models"][asset]["selected"]),
                    "trained_through": self.bundle["models"][asset]["trained_through"],
                    "minimum_supported_contexts": 2,
                }
                for asset in FEEDS
            },
        }
        self._rows = {asset: {} for asset in FEEDS}
        self._contexts, self._scores = {}, {}
        self._history = {}
        self._history_due = dict.fromkeys(FEEDS, 0.0)
        self._paths, self._path_due = {}, {}
        self._started = False

    def start(self):
        if self._started:
            return
        descriptor = os.open(
            self.ledger.home / "observer.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        lock = os.fdopen(descriptor, "a+")
        try:
            stat = os.fstat(descriptor)
            if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
                raise MtfError("mtf_lock_permissions_invalid")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise MtfError("mtf_observer_already_running") from None
            self.ledger.bind(self.bundle, self.model_sha)
            self._lock = lock
            self._pool = ThreadPoolExecutor(
                max_workers=3, thread_name_prefix="mtf-public"
            )
            self._started = True
        except BaseException:
            lock.close()
            raise

    def _asset_state(self, asset, **values):
        with self._state_lock:
            self._state["assets"].setdefault(asset, {}).update(values)

    def snapshot(self, status=None):
        with self._state_lock:
            result = copy.deepcopy(self._state)
        result.update(
            {
                "at": self.clock(),
                "pid": os.getpid(),
                "status": status or result["status"],
                "model_sha256": self.model_sha,
                "paper_only": True,
                "source": "Jupiter fixed_rate@200ms oracle USD",
                "fill_semantics": "Observed fresh oracle proxies; no guaranteed keeper fills",
                "liquidation_bound_bps": float(LIQUIDATION_BPS),
                "performance": self.ledger.performance(),
            }
        )
        result["decisions"] = []
        for row in self.ledger.rows()[:12]:
            public = {
                key: row[key]
                for key in (
                    "id",
                    "asset",
                    "base_minutes",
                    "target_start",
                    "target_end",
                    "direction",
                    "status",
                    "decision_at",
                    "committed_at",
                    "entry_price",
                    "observed_liquidation",
                    "exit_decision_at",
                    "exit_price",
                    "direction_correct",
                    "survived",
                    "paper_win",
                    "gross_bps",
                    "last_error",
                )
            }
            public["entry_quote"] = _json(row["entry_quote_json"])
            public["exit_quote"] = (
                _json(row["exit_quote_json"]) if row["exit_quote_json"] else None
            )
            result["decisions"].append(public)
        return result

    def _publish(self):
        while not self.stop_event.is_set():
            try:
                self.parent.put_meta("mtf_forward", self.snapshot())
            except Exception:  # noqa: BLE001 - a failed heartbeat is never fabricated.
                with self._state_lock:
                    self._state["error"] = "mtf_heartbeat_write_failed"
            self.stop_event.wait(1)

    def _quote(self, metadata, asset, now, *, boundary):
        if (
            not isinstance(metadata, dict)
            or not _finite(metadata.get("at"))
            or not 0 <= now - metadata["at"] <= 2
            or metadata.get("status") == "stopped"
        ):
            return None
        connected, feeds = metadata.get("connected"), metadata.get("feeds")
        if (
            not isinstance(connected, dict)
            or connected.get("jupiter") is not True
            or not isinstance(feeds, dict)
        ):
            return None
        jupiter = feeds.get("jupiter")
        quote = jupiter.get(asset) if isinstance(jupiter, dict) else None
        if (
            not isinstance(quote, dict)
            or quote.get("asset") != asset
            or type(quote.get("feed_id")) is not int
            or quote["feed_id"] != FEEDS[asset]
            or quote.get("endpoint") != STREAM_URL
            or quote.get("quote_currency") != "USD"
            or not _finite(quote.get("price"), positive=True)
        ):
            return None
        if (
            any(
                not _finite(quote.get(key)) or not 0 <= now - quote[key] <= 1
                for key in ("exchange_at", "received_at")
            )
            or quote["exchange_at"] < boundary
        ):
            return None
        try:
            exact_price = _decimal_price(quote)
        except MtfError:
            return None
        result = copy.deepcopy(quote)
        result.update(
            {
                "price_decimal": str(exact_price),
                "price_precision": "raw_oracle_units"
                if quote.get("raw_price") is not None
                else "float_proxy_without_raw",
                "decision_at": now,
                "exchange_age_seconds": now - quote["exchange_at"],
                "received_age_seconds": now - quote["received_at"],
                "transport_latency_seconds": quote["received_at"]
                - quote["exchange_at"],
                "boundary_delay_seconds": now - boundary,
                "fill_semantics": "Observed oracle price proxy; no guaranteed keeper fill",
            }
        )
        return result

    def _schedule_history(self, asset, now):
        if asset in self._history or now < self._history_due[asset]:
            return
        last = int(now // 60) * 60 - 60
        existing = self._rows[asset]
        start = max(existing) + 60 if existing else last - 1439 * 60
        if start > last:
            self._history_due[asset] = last + 121
            return
        if last - start >= 1440 * 60:
            start = last - 1439 * 60
        self._history_due[asset] = int(now // 60) * 60 + 61
        self._history[asset] = (
            start,
            last,
            self._pool.submit(
                self.public.history,
                asset,
                start,
                last,
                cancelled=self.stop_event.is_set,
            ),
        )
        self._asset_state(asset, status="updating-completed-history")

    def _poll_history(self, now):
        for asset, (start, last, future) in list(self._history.items()):
            if not future.done():
                continue
            del self._history[asset]
            try:
                value = future.result()
                rows = value["rows"]
                # Keep the same strict complete-minute decoder contract even
                # for injected transports, and never accept future candles.
                if [row[0] for row in rows] != list(range(start, last + 60, 60)) or any(
                    row[0] + 60 > now for row in rows
                ):
                    raise MtfError("incomplete_or_future_history")
                self._rows[asset].update({row[0]: row for row in rows})
                cutoff = int(now // 60) * 60 - 1440 * 60
                self._rows[asset] = {
                    stamp: row
                    for stamp, row in self._rows[asset].items()
                    if stamp >= cutoff
                }
                ordered = [row for _, row in sorted(self._rows[asset].items())]
                context = self.analysis.live_context(ordered, now)
                model = self.bundle["models"][asset]
                scores = {
                    str(minutes): self.analysis.score_context(model, minutes, context)
                    for minutes in INTERVALS
                }
                self._contexts[asset], self._scores[asset] = context, scores
                self._asset_state(
                    asset,
                    status="observing",
                    frames=context.get("frames", {}),
                    scores=scores,
                    cached_completed_minutes=len(ordered),
                    history_proof=value.get("proof"),
                    error=None,
                )
            except Exception as error:  # noqa: BLE001 - scorers/providers never leak untrusted errors.
                self._asset_state(
                    asset,
                    status="history-unavailable",
                    error=str(error)
                    if isinstance(error, MtfError)
                    else "completed_history_or_score_unavailable",
                )

    def _enter(self, asset, metadata, now):
        model = self.bundle["models"][asset]
        selected = model.get("selected")
        if selected is None:
            self._asset_state(asset, status="no-selected-model")
            return
        minutes, threshold = selected["minutes"], selected["threshold"]
        target = int(now // (minutes * 60)) * minutes * 60
        if not 0 <= now - target <= 30 or _epoch(model["trained_through"]) >= target:
            return
        context, scores = self._contexts.get(asset), self._scores.get(asset)
        if not context or not scores:
            return
        frame = context.get("frames", {}).get(str(minutes), {})
        score = scores.get(str(minutes), {})
        components = score.get("components", [])
        supported = [
            row
            for row in components
            if isinstance(row, dict)
            and type(row.get("n")) is int
            and row["n"] >= 20
            and _finite(row.get("weight"), positive=True)
        ]
        if (
            frame.get("pair") != "UU"
            or frame.get("closed_at") != target
            or score.get("status") != "ready"
            or len(supported) < 2
            or not _finite(score.get("score_down"))
            or not 0 <= score["score_down"] <= 1
        ):
            return
        direction = self.analysis.classify(score["score_down"], threshold)
        if direction not in ("UP", "DOWN"):
            return
        with self.ledger.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM decisions WHERE asset=? AND (status IN ('open','pending') OR target_start=?)",
                (asset, target),
            ).fetchone():
                return
            decision_at = self.clock()
            if not 0 <= decision_at - target <= 30:
                return
            quote = self._quote(metadata, asset, decision_at, boundary=target)
            if quote is None:
                return
            identity = f"{self.model_sha[:16]}:{asset}:{target}"
            db.execute(
                """INSERT INTO decisions(id,asset,model_sha,base_minutes,target_start,target_end,direction,status,decision_at,entry_price,entry_quote_json,context_json,scores_json,selection_json)
                          VALUES(?,?,?,?,?,?,?,'open',?,?,?,?,?,?)""",
                (
                    identity,
                    asset,
                    self.model_sha,
                    minutes,
                    target,
                    target + minutes * 60,
                    direction,
                    decision_at,
                    quote["price"],
                    canonical(quote),
                    canonical(context),
                    canonical(scores),
                    canonical(selected),
                ),
            )
        # The independent connection can see the decision before this receipt
        # and before any path query or outcome evaluation begins.
        with self.ledger.connect() as db:
            db.execute(
                "UPDATE decisions SET committed_at=? WHERE id=?",
                (self.clock(), identity),
            )
        self._asset_state(asset, status="paper-open", decision_id=identity)

    def _observe_open(self, metadata, now):
        for row in self.ledger.rows(unresolved=True):
            if row["status"] != "open":
                continue
            quote = self._quote(
                metadata, row["asset"], now, boundary=row["target_start"]
            )
            if quote is None:
                self._asset_state(row["asset"], status="waiting-fresh-oracle-quote")
                continue
            if (
                quote["received_at"] >= row["decision_at"]
                and not row["observed_liquidation"]
                and adverse_touch(
                    row["direction"],
                    _decimal_price(_json(row["entry_quote_json"])),
                    quote["price_decimal"],
                )
            ):
                with self.ledger.connect() as db:
                    db.execute(
                        "UPDATE decisions SET observed_liquidation=1,observed_touch_json=? WHERE id=?",
                        (canonical(quote), row["id"]),
                    )
            if now < row["target_end"] or quote["exchange_at"] < row["target_end"]:
                continue
            exit_quote = self._quote(
                metadata, row["asset"], self.clock(), boundary=row["target_end"]
            )
            if exit_quote is None:
                continue
            with self.ledger.connect() as db:
                db.execute(
                    "UPDATE decisions SET status='pending',exit_decision_at=?,exit_price=?,exit_quote_json=? WHERE id=? AND status='open'",
                    (
                        exit_quote["decision_at"],
                        exit_quote["price"],
                        canonical(exit_quote),
                        row["id"],
                    ),
                )
            self._asset_state(row["asset"], status="verifying-full-path")

    def _schedule_paths(self, now):
        for row in self.ledger.rows(unresolved=True):
            if row["status"] != "pending" or row["id"] in self._paths:
                continue
            if row["id"] not in self._path_due:
                with self.ledger.connect() as db:
                    saved = db.execute(
                        "SELECT value FROM meta WHERE key=?",
                        ("path_next:" + row["id"],),
                    ).fetchone()
                self._path_due[row["id"]] = json.loads(saved[0]) if saved else 0
            if now < self._path_due[row["id"]]:
                continue
            self._path_due[row["id"]] = now + 60
            with self.ledger.connect() as db:
                db.execute(
                    "INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    ("path_next:" + row["id"], canonical(now + 60)),
                )
            self._paths[row["id"]] = (
                row,
                self._pool.submit(
                    self.public.path,
                    row["asset"],
                    row["decision_at"],
                    row["exit_decision_at"],
                    cancelled=self.stop_event.is_set,
                ),
            )

    def _poll_paths(self):
        for identity, (row, future) in list(self._paths.items()):
            if not future.done():
                continue
            del self._paths[identity]
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001 - bounded retries only, never a guessed outcome.
                result = {
                    "status": "pending",
                    "error": str(error)
                    if isinstance(error, MtfError)
                    else "full_oracle_path_unavailable",
                    "proof": {},
                    "raw": b"",
                }
            if not isinstance(result, dict):
                result = {
                    "status": "pending",
                    "error": "invalid_path_result",
                    "proof": {},
                    "raw": b"",
                }
            proof, raw = result.get("proof", {}), result.get("raw", b"")
            if not isinstance(raw, bytes) or len(raw) > MAX_PATH_BYTES:
                result = {
                    "status": "pending",
                    "error": "invalid_path_evidence",
                    "proof": {},
                    "raw": b"",
                }
                proof, raw = {}, b""
            complete = result.get("status") == "complete"
            points = []
            if complete:
                try:
                    first, last = path_grid(row["decision_at"], row["exit_decision_at"])
                    expected_url = (
                        PRICES_URL
                        + "?"
                        + urllib.parse.urlencode(
                            {
                                "feedId": FEEDS[row["asset"]],
                                "fromMs": first // 1000,
                                "toMs": last // 1000,
                            }
                        )
                    )
                    if (
                        not isinstance(proof, dict)
                        or proof.get("sha256") != hashlib.sha256(raw).hexdigest()
                        or proof.get("bytes") != len(raw)
                        or proof.get("first_us") != first
                        or proof.get("last_us") != last
                        or proof.get("url") != expected_url
                        or not _finite(proof.get("received_at"))
                        or proof["received_at"] < row["exit_decision_at"]
                    ):
                        raise ValueError()
                    points = decode_samples(_json(raw), row["asset"], first, last)
                except (ValueError, TypeError, KeyError, ArithmeticError, MtfError):
                    complete = False
                    result["error"] = "incomplete_or_invalid_verified_path"
            if complete:
                try:
                    entry_exact = _decimal_price(_json(row["entry_quote_json"]))
                    exit_exact = _decimal_price(_json(row["exit_quote_json"]))
                except MtfError:
                    complete = False
                    result["error"] = "unqualified_entry_or_exit_proxy_units"
            with self.ledger.connect() as db:
                db.execute(
                    "INSERT INTO path_attempts(decision_id,at,status,error,proof_json,raw_zlib) VALUES(?,?,?,?,?,?)",
                    (
                        identity,
                        self.clock(),
                        "complete" if complete else "pending",
                        result.get("error"),
                        canonical(proof),
                        zlib.compress(raw, 3),
                    ),
                )
                if not complete:
                    db.execute(
                        "UPDATE decisions SET last_error=? WHERE id=?",
                        (result.get("error", "incomplete_path"), identity),
                    )
                    self._asset_state(
                        row["asset"],
                        status="pending-unscored-path",
                        error=result.get("error"),
                    )
                    continue
                current = db.execute(
                    "SELECT observed_liquidation FROM decisions WHERE id=?", (identity,)
                ).fetchone()
                touched = bool(current[0]) or any(
                    adverse_touch(row["direction"], entry_exact, point["price"])
                    for point in [
                        *points,
                        {"price": entry_exact},
                        {"price": exit_exact},
                    ]
                )
                sign = 1 if row["direction"] == "UP" else -1
                exact_gross = sign * (exit_exact / entry_exact - 1) * 10_000
                gross = float(exact_gross)
                correct = exact_gross > 0
                proof.update(
                    {
                        "complete_grid": True,
                        "sample_count": len(points),
                        "liquidation_bound_bps": float(LIQUIDATION_BPS),
                        "path_start_semantics": "ceil(decision wall time / 200ms); entry and exit quote endpoints included",
                    }
                )
                db.execute(
                    "UPDATE decisions SET status='settled',direction_correct=?,survived=?,paper_win=?,gross_bps=?,path_json=?,last_error=NULL WHERE id=? AND status='pending'",
                    (
                        int(correct),
                        int(not touched),
                        int(correct and not touched),
                        gross,
                        canonical(proof),
                        identity,
                    ),
                )
            self._asset_state(
                row["asset"], status="paper-settled", decision_id=identity, error=None
            )

    def tick(self):
        self.start()
        now = self.clock()
        self._poll_history(now)
        self._poll_paths()
        metadata = self.parent.meta("dual_quotes", {})
        self._observe_open(metadata, now)
        for asset in FEEDS:
            if self.stop_event.is_set():
                break
            self._enter(asset, metadata, now)
            self._schedule_history(asset, now)
        self._schedule_paths(now)
        with self._state_lock:
            self._state["status"] = "observing"
        return self.snapshot()

    def close(self):
        self.stop_event.set()
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=True)
            self._pool = None
        if (
            self._publisher is not None
            and self._publisher is not threading.current_thread()
        ):
            self._publisher.join(6)
            if self._publisher.is_alive():
                raise MtfError("mtf_publisher_shutdown_incomplete")
        if self._lock is not None:
            try:
                self.parent.put_meta("mtf_forward", self.snapshot("stopped"))
            finally:
                self._lock.close()
                self._lock = None
        self._started = False

    def run(self):
        self.start()
        self._publisher = threading.Thread(
            target=self._publish, name="mtf-status", daemon=True
        )
        self._publisher.start()
        try:
            while not self.stop_event.is_set():
                self.tick()
                self.stop_event.wait(0.2)
        finally:
            self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=default_home())
    parser.add_argument("--models", required=True, type=Path)
    args = parser.parse_args(argv)
    worker = MtfForward(args.home, args.models)
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: worker.stop_event.set())
    try:
        worker.run()
    except MtfError as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
