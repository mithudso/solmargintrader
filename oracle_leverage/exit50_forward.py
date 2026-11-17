"""Separate, prospective 10m reversal paper observer; no signing or venue calls.

Outcomes use the shared replay kernel and exact archived 200ms oracle samples.
A quote is an observed price proxy, not a transaction or keeper fill.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import math
import os
import signal
import sqlite3
import sys
import threading
import time
import zlib
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from oracle_leverage.exit50 import (
    GRID_US,
    PAPER_MARGIN,
    graph_snapshot,
    minute_features,
    quote_position,
    signal_snapshot,
    start_position,
    step_position,
)
from oracle_leverage.exit50 import (
    shape_tilts as core_shape_tilts,
)
from oracle_leverage.mtf_forward import (
    FEEDS,
    STREAM_URL,
    MtfError,
    OraclePublic,
    _decimal_price,
    _epoch,
    _finite,
    _json,
    canonical,
    decode_samples,
)
from oracle_leverage.store import Store, default_home


def load_family_models(path):
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("family_bundle_too_large")
    bundle = _json(raw)
    if (
        not isinstance(bundle, dict)
        or bundle.get("schema") != "exit50-family-model-bundle/v1"
        or not isinstance(bundle.get("models"), dict)
        or set(bundle["models"]) != set(FEEDS)
    ):
        raise ValueError("invalid_family_bundle")
    for asset, families in bundle["models"].items():
        if not isinstance(families, dict) or set(families) != {
            "confirmed_uu",
            "near_end",
        }:
            raise ValueError("invalid_family_models")
        for family, model in families.items():
            if (
                not isinstance(model, dict)
                or model.get("schema") != "mtf-reversal-model/v1"
                or model.get("asset") != asset
                or model.get("entry_family") != family
                or model.get("alpha") != 20
                or model.get("min_cell_n") != 20
                or model.get("min_components") != 2
                or not isinstance(model.get("base_models"), dict)
                or "10" not in model["base_models"]
            ):
                raise ValueError("invalid_family_model")
            _epoch(model.get("trained_through"))
    return bundle, hashlib.sha256(raw).hexdigest()


def load_selected_policy(path, model_sha):
    if path is None:
        bundle = {
            "schema": "exit50-selected-policy/v1",
            "model_bundle_sha256": model_sha,
            "assets": {
                asset: {
                    "id": f"experimental-{asset}-confirmed-uu-shape-bop",
                    "family": "confirmed_uu",
                    "filter": "shape_bop",
                    "policy": "target_momentum",
                    "delay_seconds": 10,
                    "selection_status": "experimental",
                    "validation_n": None,
                    "validation_mean_roe": None,
                }
                for asset in FEEDS
            },
        }
        raw = canonical(bundle).encode()
    else:
        raw = Path(path).read_bytes()
        if len(raw) > 256 * 1024:
            raise ValueError("selected_policy_too_large")
        bundle = _json(raw)
    if (
        not isinstance(bundle, dict)
        or bundle.get("schema") != "exit50-selected-policy/v1"
        or bundle.get("model_bundle_sha256") != model_sha
        or not isinstance(bundle.get("assets"), dict)
        or set(bundle["assets"]) != set(FEEDS)
    ):
        raise ValueError("invalid_selected_policy_binding")
    for asset, policy in bundle["assets"].items():
        if (
            not isinstance(policy, dict)
            or not isinstance(policy.get("id"), str)
            or not policy["id"]
            or policy.get("family") not in ("confirmed_uu", "near_end")
            or policy.get("filter") not in ("shape", "shape_bop")
            or policy.get("policy") != "target_momentum"
            or policy.get("delay_seconds") != 10
            or policy.get("selection_status")
            not in ("experimental", "validation-selected")
        ):
            raise ValueError(f"invalid_selected_policy_{asset}")
        if policy["selection_status"] == "validation-selected" and (
            type(policy.get("validation_n")) is not int
            or policy["validation_n"] < 30
            or not _finite(policy.get("validation_mean_roe"))
        ):
            raise ValueError(f"unqualified_selected_policy_{asset}")
    return bundle, hashlib.sha256(raw).hexdigest()


def price_int(value):
    price = Decimal(str(value)) * 10**12
    if not price.is_finite() or price <= 0 or price != price.to_integral_value():
        raise ValueError("invalid_exact_oracle_price")
    return int(price)


def bar_display(rows, now, mark=None, opening=None):
    """Use shared completed-bar graph; optionally add the fresh observed mark."""
    graph = graph_snapshot(rows, int(now))
    prior_graph = graph_snapshot(rows, int(now) - 600)
    boundary = graph["bar_start"]

    def convert(row, baseline, progress):
        if row is None:
            return None
        return {
            "start": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "progress": progress,
            "baseline_range": baseline,
        }

    prior = convert(graph["previous"], prior_graph["mean_range"], 1.0)
    current = convert(
        graph["developing"], graph["mean_range"], min(1, max(0, (now - boundary) / 600))
    )
    if current is None and opening is not None and mark is not None:
        current = convert(
            [boundary, opening, opening, opening, opening],
            graph["mean_range"],
            min(1, max(0, (now - boundary) / 600)),
        )
    if current and mark is not None:
        current.update(
            close=mark,
            high=max(current["high"], mark),
            low=min(current["low"], mark),
            live=True,
        )
    return {"previous": prior, "current": current}


def shape_tilts(model, context):
    """Raw family-conditional UP uplift derived from shared model counts."""
    result = {}
    for item in core_shape_tilts(model, context):
        n, down, baseline = item["n"], item["down"], item["base_up"]
        if (
            item["supported"]
            and type(n) is int
            and n >= 20
            and type(down) is int
            and 0 <= down <= n
            and _finite(baseline)
        ):
            result[str(item["minutes"])] = {
                "uplift_pp": ((1 - down / n) - baseline) * 100,
                "n": n,
                "shape": item["shape"],
                "condition": "next 10m IF UU",
            }
    return result


class PaperLedger:
    def __init__(self, root, binding, clock=time.time):
        self.home = Path(root) / "exit50"
        self.home.mkdir(mode=0o700, exist_ok=True)
        info = self.home.lstat()
        if self.home.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("unsafe_paper_directory")
        self.clock = clock
        self.path = self.home / "ledger.sqlite3"
        if self.path.exists():
            info = self.path.lstat()
            if (
                self.path.is_symlink()
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
            ):
                raise ValueError("unsafe_paper_ledger")
            db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            try:
                current = db.execute(
                    "SELECT value FROM meta WHERE key='binding'"
                ).fetchone()
                if current is None or current[0] != canonical(binding):
                    raise ValueError("paper_binding_changed")
            finally:
                db.close()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        os.close(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("unsafe_paper_ledger")
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions(
                    id TEXT PRIMARY KEY, asset TEXT NOT NULL, decision_s INTEGER NOT NULL,
                    committed_us INTEGER NOT NULL, cap_us INTEGER NOT NULL,
                    status TEXT NOT NULL, state_json TEXT, signal_json TEXT NOT NULL,
                    reason TEXT, UNIQUE(asset, decision_s));
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_asset ON decisions(asset)
                    WHERE status IN ('waiting_entry','open','close_pending');
                CREATE TABLE IF NOT EXISTS proof(
                    id INTEGER PRIMARY KEY, decision_id TEXT NOT NULL, first_us INTEGER NOT NULL,
                    last_us INTEGER NOT NULL, sha256 TEXT NOT NULL, evidence_json TEXT NOT NULL, raw_zlib BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS candles(asset TEXT NOT NULL, start_s INTEGER NOT NULL, row_json TEXT NOT NULL, PRIMARY KEY(asset,start_s));
                CREATE TABLE IF NOT EXISTS candle_batches(id INTEGER PRIMARY KEY, asset TEXT NOT NULL, first_s INTEGER NOT NULL, last_s INTEGER NOT NULL, evidence_json TEXT NOT NULL);
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(decisions)")}
            if "commit_observed_us" not in columns:
                db.execute(
                    "ALTER TABLE decisions ADD COLUMN commit_observed_us INTEGER"
                )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS one_inflight_asset_v2 ON decisions(asset) WHERE status IN ('committing','waiting_entry','open','close_pending')"
            )
            current = db.execute(
                "SELECT value FROM meta WHERE key='binding'"
            ).fetchone()
            if current and current[0] != canonical(binding):
                raise ValueError("paper_binding_changed")
            db.execute(
                "INSERT OR IGNORE INTO meta VALUES('binding',?)", (canonical(binding),)
            )

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

    def recover_interrupted_commits(self):
        with self.connect() as db:
            db.execute(
                "UPDATE decisions SET status='unscored',reason='commit_timestamp_unverified' WHERE status IN ('committing','waiting_entry') AND commit_observed_us IS NULL"
            )

    def history(self, asset):
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT row_json FROM candles WHERE asset=? ORDER BY start_s",
                    (asset,),
                )
            ]

    def append_history(self, asset, rows, proof):
        from research.reversal_history import validated_rows

        checked = validated_rows(rows)
        if len(checked) != len(rows) or [r[0] for r in checked] != [r[0] for r in rows]:
            raise ValueError("invalid_history_rows")
        if not checked:
            return
        with self.connect() as db:
            for row in checked:
                encoded = canonical(row)
                saved = db.execute(
                    "SELECT row_json FROM candles WHERE asset=? AND start_s=?",
                    (asset, row[0]),
                ).fetchone()
                if saved is not None and saved[0] != encoded:
                    raise ValueError("persisted_history_changed")
                db.execute(
                    "INSERT OR IGNORE INTO candles VALUES(?,?,?)",
                    (asset, row[0], encoded),
                )
            db.execute(
                "INSERT INTO candle_batches(asset,first_s,last_s,evidence_json) VALUES(?,?,?,?)",
                (asset, checked[0][0], checked[-1][0], canonical(proof)),
            )

    def active(self):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM decisions WHERE status IN ('waiting_entry','open','close_pending')"
                )
            ]

    def commit(self, asset, decision_s, now_us, snapshot):
        cap_us = (
            decision_s + (660 if snapshot.get("family") == "near_end" else 600)
        ) * 1_000_000
        identity = f"{asset}:{decision_s}"
        # Persist intent before sampling a post-commit upper bound on its wall time.
        with self.connect() as db:
            try:
                db.execute(
                    "INSERT INTO decisions(id,asset,decision_s,committed_us,cap_us,status,state_json,signal_json,reason,commit_observed_us) VALUES(?,?,?,?,?,'committing',NULL,?,NULL,NULL)",
                    (identity, asset, decision_s, 0, cap_us, canonical(snapshot)),
                )
            except sqlite3.IntegrityError:
                return False
        committed_after_us = max(now_us, int(self.clock() * 1_000_000))
        eligible_us = (
            (max(decision_s * 1_000_000, committed_after_us) + GRID_US + GRID_US - 1)
            // GRID_US
        ) * GRID_US
        fresh = (
            0 <= committed_after_us - decision_s * 1_000_000 <= 30_000_000
            and eligible_us < cap_us
        )
        with self.connect() as db:
            db.execute(
                "UPDATE decisions SET committed_us=?, commit_observed_us=?, status=?, reason=? WHERE id=? AND status='committing'",
                (
                    eligible_us,
                    committed_after_us,
                    "waiting_entry" if fresh else "unscored",
                    None if fresh else "late_signal_commit",
                    identity,
                ),
            )
        return fresh

    def save(self, row, status, state, proof=None, raw=None, reason=None):
        with self.connect() as db:
            db.execute(
                "UPDATE decisions SET status=?,state_json=?,reason=? WHERE id=?",
                (
                    status,
                    canonical(state) if state is not None else None,
                    reason,
                    row["id"],
                ),
            )
            if proof:
                db.execute(
                    "INSERT INTO proof(decision_id,first_us,last_us,sha256,evidence_json,raw_zlib) VALUES(?,?,?,?,?,?)",
                    (
                        row["id"],
                        proof["first_us"],
                        proof["last_us"],
                        proof["sha256"],
                        canonical(proof),
                        zlib.compress(raw, 3),
                    ),
                )

    def performance(self):
        with self.connect() as db:
            rows = db.execute("SELECT status,state_json FROM decisions").fetchall()
        result = {
            "open": 0,
            "close_pending": 0,
            "unscored": 0,
            "settled": 0,
            "profitable": 0,
            "target_touched": 0,
            "target_filled": 0,
            "modeled_realized_pnl_usd": 0.0,
        }
        for row in rows:
            status = row["status"]
            if status in ("waiting_entry", "open"):
                result["open"] += 1
            elif status in ("close_pending", "unscored"):
                result[status] += 1
            elif status in ("closed_proxy", "liquidated"):
                result["settled"] += 1
                state = json.loads(row["state_json"])
                result["profitable"] += int(state.get("payout", 0) > PAPER_MARGIN)
                result["target_touched"] += int(
                    state.get("target_first_us") is not None
                )
                result["target_filled"] += int(bool(state.get("target_filled")))
                result["modeled_realized_pnl_usd"] += (
                    state.get("payout", 0) - PAPER_MARGIN
                ) / 1_000_000
        return result


class Exit50Forward:
    def __init__(
        self,
        home,
        models,
        *,
        policies=None,
        profile=None,
        public=None,
        clock=time.time,
        stop_event=None,
    ):
        self.bundle, self.model_sha = load_family_models(models)
        self.selected, self.policy_sha = load_selected_policy(policies, self.model_sha)
        self.clock = clock
        self.stop_event = stop_event or threading.Event()
        self.public = public or OraclePublic(clock=clock)
        core_path = Path(__file__).with_name("exit50.py")
        self.binding = {
            "model_sha256": self.model_sha,
            "core_sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
            "schema": "exit50-forward-v1",
            "policy_sha256": self.policy_sha,
            "selected_policies": self.selected["assets"],
            "margin_micro_usd": PAPER_MARGIN,
            "leverage": 1000,
            "delay_s": 10,
        }
        self.not_before_s = 0
        if profile is not None:
            raw = Path(profile).read_bytes()
            spec = _json(raw)
            if (
                not isinstance(spec, dict)
                or spec.get("schema") != "exit50-paper-profile/v1"
                or spec.get("model_sha256") != self.model_sha
                or spec.get("policy_sha256") != self.policy_sha
                or spec.get("core_sha256") != self.binding["core_sha256"]
                or spec.get("observer_sha256")
                != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                or not isinstance(spec.get("not_before_s"), int)
                or isinstance(spec.get("not_before_s"), bool)
                or spec["not_before_s"] <= 0
            ):
                raise ValueError("invalid_paper_profile")
            self.not_before_s = spec["not_before_s"]
            self.binding["profile_sha256"] = hashlib.sha256(raw).hexdigest()
            self.binding["not_before_s"] = self.not_before_s
        root = Path(home)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        paper_home = root / "exit50"
        paper_home.mkdir(mode=0o700, exist_ok=True)
        info = paper_home.lstat()
        if (
            paper_home.is_symlink()
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("unsafe_paper_directory")
        fd = os.open(
            paper_home / "observer.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            os.close(fd)
            raise ValueError("unsafe_observer_lock")
        self._lock = os.fdopen(fd, "a+")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock.close()
            raise ValueError("exit50_observer_already_running") from None
        try:
            self.ledger = PaperLedger(root, self.binding, clock=clock)
            self.parent = Store(home)
        except BaseException:
            self._lock.close()
            self._lock = None
            raise
        self.rows = {asset: self.ledger.history(asset) for asset in FEEDS}
        self.history_due = dict.fromkeys(FEEDS, 0.0)
        self.assets = {
            asset: {
                "signal": "waiting-completed-history",
                "selected_policy": self.selected["assets"][asset],
                "model_sha256": self.model_sha,
                "policy_sha256": self.policy_sha,
            }
            for asset in FEEDS
        }
        self.process_start_s = None
        self._bar_open = {}
        self._signal_cache = {}

    def start(self):
        if self._lock is None or self._lock.closed or self.process_start_s is not None:
            raise ValueError("observer_not_owned_or_already_started")
        self.process_start_s = math.ceil(self.clock())
        with self.ledger.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO meta VALUES('trial_first_start_s',?)",
                (str(self.process_start_s),),
            )
        self.ledger.recover_interrupted_commits()

    def quote(self, asset, now):
        data = self.parent.meta("dual_quotes", {})
        if (
            not isinstance(data, dict)
            or not _finite(data.get("at"))
            or not 0 <= now - data["at"] <= 2
            or data.get("status") == "stopped"
        ):
            return None
        connected, feeds = data.get("connected"), data.get("feeds")
        if (
            not isinstance(connected, dict)
            or connected.get("jupiter") is not True
            or not isinstance(feeds, dict)
        ):
            return None
        source = feeds.get("jupiter", {})
        row = source.get(asset) if isinstance(source, dict) else None
        if (
            not isinstance(row, dict)
            or row.get("asset") != asset
            or row.get("feed_id") != FEEDS[asset]
            or row.get("endpoint") != STREAM_URL
            or row.get("quote_currency") != "USD"
            or row.get("fresh", True) is not True
        ):
            return None
        if any(
            not _finite(row.get(k)) or not 0 <= now - row[k] <= 1
            for k in ("exchange_at", "received_at")
        ):
            return None
        try:
            return price_int(_decimal_price(row))
        except (ValueError, MtfError, ArithmeticError):
            return None

    def refresh_history(self, asset, now):
        if now < self.history_due[asset]:
            return
        self.history_due[asset] = now + 3
        last = int(now // 60) * 60 - 60
        existing = self.rows[asset]
        first = (
            max(existing[-1][0] + 60, last - 1439 * 60)
            if existing
            else last - 1439 * 60
        )
        try:
            if first <= last:
                value = self.public.history(
                    asset, first, last, cancelled=self.stop_event.is_set
                )
                rows = value["rows"]
                if [r[0] for r in rows] != list(range(first, last + 60, 60)):
                    raise ValueError("incomplete_closed_history")
                self.ledger.append_history(asset, rows, value.get("proof", {}))
                self.rows[asset] = self.ledger.history(asset)
            rows = self.rows[asset]
            if not rows or rows[-1][0] != last:
                raise ValueError("latest_closed_history_missing")
            snapshot = signal_snapshot(
                rows,
                last + 60,
                "confirmed_uu",
                self.bundle["models"][asset]["confirmed_uu"],
            )
            score = snapshot.get("score") or {}
            seed = rows[0][0]
            for previous, current in itertools.pairwise(rows):
                if current[0] - previous[0] != 60:
                    seed = current[0]
            self.assets[asset].update(
                frames=snapshot.get("context", {}).get("frames", {}),
                indicators=snapshot.get("features") or {},
                score=score.get("score_down"),
                tilts=shape_tilts(
                    self.bundle["models"][asset]["confirmed_uu"], snapshot["context"]
                ),
                history="persistent-prefix",
                indicator_seed_s=seed,
                indicator_last_s=rows[-1][0],
                indicator_note="EMA/MACD seeded from saved contiguous history; bootstrap may differ from research seed",
            )
            self.history_due[asset] = (last + 120) + 0.2
        except (ValueError, MtfError, KeyError, TypeError, OSError, sqlite3.Error):
            self.assets[asset]["history"] = "waiting-valid-completed-history"

    def observe_signal(self, asset, now):
        rows = self.rows[asset]
        if not rows:
            return
        boundary = int(now // 600) * 600
        elapsed = now - boundary
        family = (
            "confirmed_uu"
            if elapsed <= 30
            else "near_end"
            if 540 <= elapsed < 600
            else None
        )
        if family is None:
            self.assets[asset]["signal"] = "waiting-next-10m-setup"
            return
        decision = boundary if family == "confirmed_uu" else boundary + 540
        if self.process_start_s is None or decision < max(
            self.not_before_s, self.process_start_s
        ):
            return
        if (
            rows[-1][0] + 60 != decision
            or _epoch(self.bundle["models"][asset][family]["trained_through"])
            >= decision
        ):
            return
        cache_key = (asset, decision, family)
        snap = self._signal_cache.get(cache_key)
        if snap is None:
            snap = signal_snapshot(
                rows, decision, family, self.bundle["models"][asset][family]
            )
            self._signal_cache = {
                key: value
                for key, value in self._signal_cache.items()
                if key[0] != asset
            }
            self._signal_cache[cache_key] = snap
        indicators = snap.get("features") or {}
        score = snap.get("score") or {}
        self.assets[asset].update(
            signal=(family if snap["eligible"] else "no-matching-setup"),
            frames=snap.get("context", {}).get("frames", {}),
            indicators=indicators,
            score=score.get("score_down"),
            score_family=family,
            shape_filter=snap.get("shape_filter"),
            bop_filter=snap.get("bop_filter"),
            partial_second_direction=snap.get("partial_second_direction"),
            decision_s=decision,
        )
        if family == "confirmed_uu":
            self.assets[asset]["tilts"] = shape_tilts(
                self.bundle["models"][asset]["confirmed_uu"], snap["context"]
            )
        # Commit before observing the first entry-path sample.
        policy = self.selected["assets"][asset]
        if (
            family == policy["family"]
            and snap["eligible"]
            and snap["shape_filter"]
            and (policy["filter"] == "shape" or snap["bop_filter"])
            and self.quote(asset, self.clock()) is not None
        ):
            self.ledger.commit(asset, decision, int(self.clock() * 1_000_000) + 1, snap)

    def advance(self, row, now):
        state = json.loads(row["state_json"]) if row["state_json"] else None
        first = state["last_us"] + GRID_US if state else row["committed_us"]
        if state is None and (
            row.get("commit_observed_us") is None
            or first
            < max(row["decision_s"] * 1_000_000, row["commit_observed_us"]) + GRID_US
            or now * 1_000_000 - first > 5_000_000
        ):
            self.ledger.save(
                row, "unscored", None, reason="entry_commit_or_observation_stale"
            )
            return
        last = (int((now - 1) * 1_000_000) // GRID_US) * GRID_US
        if last < first:
            return
        # The initial observation is verified separately; later requests are bounded by now.
        last = min(
            last,
            row["cap_us"] + 10_000_000,
            first if state is None else first + 120_000_000,
        )
        if last < first:
            return
        try:
            while True:
                result = self.public.path(
                    row["asset"],
                    first / 1_000_000,
                    last / 1_000_000,
                    cancelled=self.stop_event.is_set,
                )
                try:
                    if result.get("status") != "complete":
                        raise ValueError("incomplete_path")
                    proof, raw = result["proof"], result["raw"]
                    if (
                        not isinstance(raw, bytes)
                        or proof.get("first_us") != first
                        or proof.get("last_us") != last
                        or proof.get("sha256") != hashlib.sha256(raw).hexdigest()
                        or not _finite(proof.get("received_at"))
                        or proof["received_at"] * 1_000_000 < last
                    ):
                        raise ValueError("invalid_path_proof")
                    wire = _json(raw)
                    points = decode_samples(wire, row["asset"], first, last)
                    if state is None:
                        received = proof.get("received_at")
                        source_us = wire["data"][0]["feed_update_timestamp"]
                        if (
                            not _finite(received)
                            or received * 1_000_000 < first
                            or received * 1_000_000 - first > 5_000_000
                            or source_us <= row["commit_observed_us"]
                        ):
                            self.ledger.save(
                                row,
                                "unscored",
                                None,
                                reason="entry_observation_stale_or_precommit",
                            )
                            return
                    break
                except (ValueError, MtfError, KeyError, TypeError):
                    if last == first:
                        raise ValueError("incomplete_or_invalid_path") from None
                    # A gap after a terminal sample must not erase an already closed position.
                    last = first + ((last - first) // GRID_US // 2) * GRID_US
            flags = minute_features(self.rows[row["asset"]])
            for point in points:
                at = point["publish_time_us"]
                if state is None:
                    state = start_position(
                        at,
                        price_int(point["price"]),
                        row["cap_us"],
                        "target_momentum",
                        10,
                    )
                    state.update(
                        signal_decision_us=row["decision_s"] * 1_000_000,
                        commit_observed_us=row["commit_observed_us"],
                        entry_eligible_us=row["committed_us"],
                        entry_publish_us=at,
                        entry_feed_update_us=source_us,
                        entry_received_at=received,
                        decision_to_entry_us=at - row["decision_s"] * 1_000_000,
                        entry_semantics="post-commit archived oracle observation; no fill asserted",
                    )
                if (
                    at % 60_000_000 == 0
                    and at > state["entry_us"]
                    and at // 1_000_000 not in flags
                ):
                    raise ValueError("missing_closed_minute_momentum")
                had_intent = state.get("intent") is not None
                state = step_position(
                    state,
                    at,
                    price_int(point["price"]),
                    flags.get(at // 1_000_000, {}) if at % 60_000_000 == 0 else {},
                )
                if not had_intent and state.get("intent") is not None:
                    state.update(
                        intent_event_us=at,
                        intent_detected_at=proof["received_at"],
                        intent_detection_lag_s=proof["received_at"] - at / 1_000_000,
                    )
                if state["status"] != "open":
                    state.update(
                        exit_detected_at=proof["received_at"],
                        exit_detection_lag_s=proof["received_at"] - at / 1_000_000,
                    )
                    break
            status = state["status"]
            if status == "open" and state["intent"]:
                status = "close_pending"
            self.ledger.save(row, status, state, proof, raw)
        except (MtfError, ValueError, TypeError, KeyError, OSError, ArithmeticError):
            if now > row["cap_us"] / 1_000_000 + 60:
                self.ledger.save(
                    row, "unscored", state, reason="path_unavailable_or_invalid"
                )

    def tick(self):
        for asset in FEEDS:
            self.refresh_history(asset, self.clock())
            self.observe_signal(asset, self.clock())
        for row in self.ledger.active():
            self.advance(row, self.clock())
        for asset in FEEDS:
            current_now = self.clock()
            mark = self.quote(asset, current_now)
            boundary = int(current_now // 600) * 600
            opening = self._bar_open.get(asset)
            if opening and opening[0] != boundary:
                self._bar_open.pop(asset, None)
                opening = None
            if (
                opening is None
                and mark is not None
                and 0 <= current_now - boundary <= 1
            ):
                metadata = self.parent.meta("dual_quotes", {})
                feeds = metadata.get("feeds", {}) if isinstance(metadata, dict) else {}
                jupiter = feeds.get("jupiter", {}) if isinstance(feeds, dict) else {}
                quote = jupiter.get(asset, {}) if isinstance(jupiter, dict) else {}
                if (
                    isinstance(quote, dict)
                    and _finite(quote.get("exchange_at"))
                    and quote["exchange_at"] >= boundary
                ):
                    opening = self._bar_open[asset] = (boundary, mark / 10**12)
            self.assets[asset]["bars"] = bar_display(
                self.rows[asset],
                current_now,
                mark / 10**12 if mark is not None else None,
                opening[1] if opening else None,
            )
            self.assets[asset].update(
                position_status="waiting", intent=None, roe=None, pnl_usd=None
            )
        for row in self.ledger.active():
            state = json.loads(row["state_json"]) if row["state_json"] else None
            data = self.assets[row["asset"]]
            display_status = row["status"]
            if state and state.get("intent") and state.get("submit_us"):
                display_status = (
                    "waiting-15s-guard"
                    if self.clock() * 1_000_000 < state["submit_us"]
                    else "close-pending-10s"
                )
            data.update(
                position_status=display_status,
                intent=state.get("intent") if state else None,
                submit_us=state.get("submit_us") if state else None,
                deadline_us=state.get("deadline_us") if state else None,
                roe=None,
            )
            mark = self.quote(row["asset"], self.clock())
            if state and mark and state["status"] == "open":
                q = quote_position(
                    PAPER_MARGIN,
                    PAPER_MARGIN * 1000,
                    state["entry_price"],
                    mark,
                    "SHORT",
                )
                data["roe"] = (q["payout"] - PAPER_MARGIN) / PAPER_MARGIN
                data["pnl_usd"] = (q["payout"] - PAPER_MARGIN) / 1_000_000
        self.parent.put_meta("exit50_forward", self.snapshot())

    def snapshot(self, status="observing"):
        positions = []
        for row in self.ledger.active():
            state = json.loads(row["state_json"]) if row["state_json"] else {}
            asset_data = self.assets.get(row["asset"], {})
            positions.append(
                {
                    "id": row["id"],
                    "asset": row["asset"],
                    "side": "short",
                    "status": asset_data.get("position_status", row["status"]),
                    "roe": asset_data.get("roe"),
                    "pnl_usd": asset_data.get("pnl_usd"),
                    "target_roe": 0.5,
                    "intent": state.get("intent"),
                    "target_touched": state.get("target_first_us") is not None,
                    "target_filled": bool(state.get("target_filled")),
                    "source": "PAPER",
                }
            )
        return {
            "at": self.clock(),
            "status": status,
            "positions": positions,
            "paper_only": True,
            "binding": self.binding,
            "assets": self.assets,
            "performance": self.ledger.performance(),
            "semantics": "Sampled oracle proxy; prices between 200ms samples and keeper behavior are unknown. Simulated 10s delay is not measured fill latency. Modeled trade fees only; chain and keeper fees excluded; no fills verified.",
        }

    def run(self):
        try:
            self.start()
            while not self.stop_event.is_set():
                self.tick()
                self.stop_event.wait(0.2)
        finally:
            failed = sys.exc_info()[0] is not None
            try:
                if self.process_start_s is not None:
                    try:
                        self.parent.put_meta("exit50_forward", self.snapshot("stopped"))
                    except Exception:
                        if not failed:
                            raise
            finally:
                if self._lock:
                    unwinding = sys.exc_info()[0] is not None
                    try:
                        self._lock.close()
                    except Exception:
                        if not unwinding:
                            raise
                    finally:
                        self._lock = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=default_home())
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument(
        "--profile", required=True, type=Path, help="Frozen prospective paper profile"
    )
    parser.add_argument(
        "--policies",
        type=Path,
        help="Frozen validation-selected per-asset policy; omission uses explicit experimental fallback",
    )
    args = parser.parse_args(argv)
    worker = Exit50Forward(
        args.home, args.models, policies=args.policies, profile=args.profile
    )
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: worker.stop_event.set())
    worker.run()


if __name__ == "__main__":
    main()
