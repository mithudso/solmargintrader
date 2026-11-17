"""Exclusive local paper session owner and observed-tick state machine."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import queue
import socket
import threading
import time
import uuid
from contextlib import closing
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from oracle_leverage import autotrade_engine as engine
from oracle_leverage.autotrade_advice import Advice, AsyncAdvice
from oracle_leverage.autotrade_feed import ExecutionFeed
from oracle_leverage.autotrade_memory import MODEL_VERSION as MEMORY_MODEL_VERSION
from oracle_leverage.autotrade_memory import LearningMemory
from oracle_leverage.autotrade_memory import score as memory_score


def pack(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _usdc(value):
    if not _positive(value):
        return False
    try:
        amount = Decimal(str(value))
        return amount >= Decimal("0.000001") and amount == amount.quantize(
            Decimal("0.000001")
        )
    except InvalidOperation:
        return False


def policy(config):
    if not isinstance(config, dict) or set(config) - {
        "mode",
        "asset",
        "venue",
        "base_collateral_usd",
        "max_collateral_usd",
        "max_session_loss_usd",
        "advice_enabled",
    }:
        raise ValueError("Invalid configuration fields")
    p = {
        "mode": "paper",
        "asset": "BTC",
        "venue": "jupiter-cli-10x",
        "base_collateral_usd": 10.0,
        "max_collateral_usd": 15.0,
        "max_session_loss_usd": 50.0,
        "advice_enabled": False,
    }
    p.update(config)
    if p["mode"] != "paper" and p["venue"] == "jupiter-sdk-1000x":
        raise ValueError(
            "1000x live auto-opening unavailable: close, queue and payout unverified"
        )
    if p["mode"] != "paper":
        raise ValueError(
            "Live unavailable: CLI position rows lack validated owner, market, side and submit-signature binding; exit fill, fees and net settlement lack verified receipts"
        )
    if p["venue"] not in ("jupiter-cli-10x", "jupiter-sdk-1000x") or p["asset"] not in (
        "BTC",
        "ZEC",
    ):
        raise ValueError("Paper proxy supports BTC and ZEC only")
    if type(p["advice_enabled"]) is not bool:
        raise ValueError("Advice setting must be boolean")
    leverage = 1000 if p["venue"] == "jupiter-sdk-1000x" else 10
    if not all(
        _usdc(p[k])
        for k in ("base_collateral_usd", "max_collateral_usd", "max_session_loss_usd")
    ):
        raise ValueError(
            "Amounts require positive USDC values representable to six decimals"
        )
    if any(
        p[k] > 1_000_000
        for k in ("base_collateral_usd", "max_collateral_usd", "max_session_loss_usd")
    ):
        raise ValueError("Paper engineering cap is 1000000 USD")
    if (
        p["base_collateral_usd"] > p["max_collateral_usd"]
        or engine.worst_loss(p["base_collateral_usd"], leverage)
        > p["max_session_loss_usd"]
    ):
        raise ValueError("Base collateral exceeds configured caps or loss reserve")
    p.update(
        leverage=leverage,
        product="1000x paper proxy" if leverage == 1000 else "10x paper proxy",
        execution_model="exit50-proxy-v1" if leverage == 1000 else "linear-10x-v1",
        cooldown_seconds=30,
        max_positions=1,
        max_hold_seconds=900,
        price_basis="jupiter-oracle-usd",
        model="observed oracle price path; provider may coalesce updates",
        boost_multiplier=1.5,
        boost_cooldown_seconds=15,
        boost_min_samples=100,
        boost_max_brier=0.20,
        boost_min_wilson=0.55,
        learning_model=MEMORY_MODEL_VERSION,
    )
    return p


def boost_eligible(learner, score, session, direction):
    """Engineering gate, not evidence of a future edge or a live authorization."""
    n = learner["samples"]
    if (
        n < 100
        or score < 0.75
        or learner["net_pnl_usd"] <= 0
        or session["net_pnl_usd"] <= 0
    ):
        return False
    if (
        learner.get("availability_failures", 0)
        or session.get("loss_streak", 0) >= 3
        or session.get("integrity_failure", False)
    ):
        return False
    if (
        session.get("peak_net_usd", 0.0) - session["net_pnl_usd"]
        > 0.25 * session["policy"]["max_session_loss_usd"]
    ):
        return False
    if learner["brier_sum"] / n > 0.20:
        return False
    high_n = learner.get("high_n", 0)
    if (
        high_n < 30
        or abs(learner["high_score_sum"] / high_n - learner["high_wins"] / high_n)
        > 0.10
    ):
        return False
    rate = learner["wins"] / n
    z = 1.96
    lower = (
        rate
        + z * z / (2 * n)
        - z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n))
    ) / (1 + z * z / n)
    if lower < 0.55:
        return False
    side = learner.get("sides", {}).get(direction, {})
    sn = side.get("samples", 0)
    hn = side.get("high_n", 0)
    if sn < 100 or hn < 30 or side.get("net_pnl_usd", 0) <= 0:
        return False
    if (
        side.get("brier_sum", 0) / sn > 0.20
        or abs(side.get("high_score_sum", 0) / hn - side.get("high_wins", 0) / hn)
        > 0.10
    ):
        return False
    sr = side.get("wins", 0) / sn
    sl = (
        sr
        + z * z / (2 * sn)
        - z * math.sqrt(sr * (1 - sr) / sn + z * z / (4 * sn * sn))
    ) / (1 + z * z / sn)
    return sl >= 0.55


def public_state(state):
    """Allowlisted projection; model parameters and feature vectors stay private."""
    keys = (
        "state",
        "mode",
        "session_id",
        "position",
        "reason",
        "first_entry_deadline",
        "policy_hash",
        "last_event",
        "defaults",
        "configuration",
        "readiness",
        "policy",
        "cohort_id",
        "started_at",
        "net_pnl_usd",
        "entries",
        "first_entry_at",
        "next_entry_at",
        "coverage",
        "forecast",
        "learner",
        "coinbase_comparison",
        "accepted",
        "request_id",
        "replayed",
        "original_session_id",
        "history",
        "cleanup",
        "learning_memory",
    )
    out = {key: copy.deepcopy(state[key]) for key in keys if key in state}

    def project(value, names):
        return (
            {key: value[key] for key in names if key in value}
            if isinstance(value, dict)
            else value
        )

    forecast_keys = (
        "version",
        "source",
        "advisory_forecast_id",
        "momentum",
        "direction",
        "score",
        "samples",
        "calibrated",
        "forced",
        "at",
        "boost_eligible",
        "boost_reason",
    )
    learner_keys = (
        "version",
        "samples",
        "wins",
        "losses",
        "liquidations",
        "net_pnl_usd",
        "brier_sum",
        "availability_failures",
        "high_n",
        "high_wins",
        "high_score_sum",
        "sides",
    )
    position_keys = (
        "plan",
        "state",
        "opened_at",
        "last_at",
        "last_price",
        "close_at",
        "submit_at",
        "trigger",
        "trigger_price",
        "exit_price",
        "net_pnl_usd",
        "pnl_scope",
        "outcome",
        "reason",
        "exited_at",
        "forecast",
        "fees_usd",
        "borrow_usd",
        "gross_pnl_usd",
        "exit_observed_price",
        "modeled_payout_usd",
        "modeled_close_fee_usd",
        "modeled_win_fee_usd",
    )
    plan_keys = (
        "version",
        "model_version",
        "created_at",
        "direction",
        "reference_price",
        "target_entry",
        "entry_fill",
        "collateral_usd",
        "leverage",
        "minimum_hold_seconds",
        "max_hold_seconds",
        "close_delay_seconds",
        "max_observation_gap_seconds",
        "fee_rate_per_side",
        "slippage_rate",
        "borrow_rate_per_hour",
        "entry_fee_usd",
        "max_borrow_usd",
        "price_basis",
        "entry_latency_seconds",
        "cost_scope",
        "assumptions",
        "liquidation_price",
        "stop_price",
        "target_price",
        "asset",
        "policy_hash",
        "intent_id",
    )
    out["training"] = (
        "saved per-coin paper model; no new outcome labels while entries are paused"
        if out.get("state") != "running"
        else "saved per-coin paper model with observed outcomes; uncalibrated"
    )
    if "learner" in out:
        out["learner"] = project(out["learner"], learner_keys)
        if isinstance(out["learner"], dict) and isinstance(
            out["learner"].get("sides"), dict
        ):
            side_keys = (
                "samples",
                "wins",
                "losses",
                "net_pnl_usd",
                "brier_sum",
                "high_n",
                "high_wins",
                "high_score_sum",
            )
            out["learner"]["sides"] = {
                k: project(v, side_keys)
                for k, v in out["learner"]["sides"].items()
                if k in ("long", "short")
            }
    if "forecast" in out:
        out["forecast"] = project(out["forecast"], forecast_keys)
    if "learning_memory" in out:
        memory = out["learning_memory"]
        if not isinstance(memory, dict):
            out["learning_memory"] = None
        else:
            memory = project(memory, ("version", "asset", "profile", "coins", "storage", "scope"))
            profile_keys = ("asset", "venue", "model_version", "samples", "updated_at")
            memory["profile"] = project(memory.get("profile", {}), profile_keys)
            memory["storage"] = project(memory.get("storage", {}), (
                "kind", "durable", "name", "last_saved_at", "legacy_index_complete",
                "unattributed_cohorts",
            ))
            coins = memory.get("coins", {})
            memory["coins"] = {}
            if isinstance(coins, dict):
                for asset in ("BTC", "ZEC"):
                    if not isinstance(coins.get(asset), dict):
                        continue
                    coin = project(coins[asset], (
                        "samples", "wins", "losses", "net_pnl_usd", "cohorts", "profiles",
                    ))
                    profiles = coin.get("profiles", {})
                    coin["profiles"] = {
                        venue: project(profiles[venue], profile_keys)
                        for venue in ("jupiter-cli-10x", "jupiter-sdk-1000x")
                        if isinstance(profiles, dict) and isinstance(profiles.get(venue), dict)
                    }
                    memory["coins"][asset] = coin
            out["learning_memory"] = memory
    if isinstance(out.get("position"), dict):
        out["position"] = project(out["position"], position_keys)
        if "plan" in out["position"]:
            out["position"]["plan"] = project(out["position"]["plan"], plan_keys)
        if "forecast" in out["position"]:
            out["position"]["forecast"] = project(
                out["position"]["forecast"], forecast_keys
            )
    if "coinbase_comparison" in out:
        out["coinbase_comparison"] = project(
            out["coinbase_comparison"],
            (
                "asset",
                "price",
                "received_at",
                "exchange_at",
                "source",
                "quote_currency",
                "kind",
                "status",
            ),
        )
    return out


def guard_state(fn):
    def guarded(self, *args, **kwargs):
        names = (
            "s",
            "learner",
            "learner_asset",
            "last_exchange",
            "previous_price",
            "momentum",
            "memory_profile",
            "memory_policy",
        )
        before = {
            name: copy.deepcopy(getattr(self, name))
            for name in names
            if hasattr(self, name)
        }
        try:
            return fn(self, *args, **kwargs)
        except BaseException:
            self.db.rollback()
            for name, value in before.items():
                setattr(self, name, value)
            raise

    return guarded


class Session:
    def __init__(self, db, clock=time.time):
        self.db, self.clock = db, clock
        db.executescript("""CREATE TABLE IF NOT EXISTS session (singleton INTEGER PRIMARY KEY CHECK(singleton=1), value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, session_id TEXT, at REAL, kind TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS learner (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS learner_assets (asset TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS learner_cohorts (cohort TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS forecasts (id TEXT PRIMARY KEY, payload TEXT NOT NULL);""")
        self.memory_store = LearningMemory(db)
        self.last_memory_import_at = None
        existing_session = db.execute(
            "SELECT value FROM session WHERE singleton=1"
        ).fetchone()
        existing = json.loads(existing_session[0]) if existing_session else {}
        self.learner_asset = existing.get("cohort_id", "unselected")
        row = db.execute(
            "SELECT value FROM learner_cohorts WHERE cohort=?", (self.learner_asset,)
        ).fetchone()
        self.learner = (
            json.loads(row[0])
            if row
            else {
                "version": "paper-net-outcome-v1",
                "samples": 0,
                "wins": 0,
                "losses": 0,
                "liquidations": 0,
                "net_pnl_usd": 0.0,
                "brier_sum": 0.0,
                "availability_failures": 0,
                "high_n": 0,
                "high_wins": 0,
                "high_score_sum": 0.0,
                "weights": [0.0, 0.0, 0.0],
                "sides": {},
            }
        )
        for key, default in (
            ("high_n", 0),
            ("high_wins", 0),
            ("high_score_sum", 0.0),
            ("availability_failures", 0),
            ("sides", {}),
        ):
            self.learner.setdefault(key, default)
        self.previous_price = None
        self.momentum = 0.0
        row = db.execute("SELECT value FROM session WHERE singleton=1").fetchone()
        self.s = (
            json.loads(row[0])
            if row
            else {
                "state": "stopped",
                "mode": "paper",
                "session_id": None,
                "position": None,
                "reason": None,
                "first_entry_deadline": None,
                "policy_hash": None,
                "last_event": None,
                "defaults": policy({}),
                "configuration": {
                    key: policy({})[key]
                    for key in (
                        "mode",
                        "asset",
                        "venue",
                        "base_collateral_usd",
                        "max_collateral_usd",
                        "max_session_loss_usd",
                        "advice_enabled",
                    )
                },
                "readiness": {
                    "paper": "available when fresh observed feed connects",
                    "live": "unavailable: no verified position, fill and settlement binding",
                    "1000x": "paper proxy available; live close, queue and payout unverified",
                    "advice": "off by default; private credential checked only on advisory call",
                },
            }
        )
        previous_policy = self.s.get("policy")
        if isinstance(previous_policy, dict) and self.s.get("cohort_id"):
            previous_at = (self.s.get("last_event") or {}).get("at", self.clock())
            self.memory_store.register(self.s["cohort_id"], previous_policy, previous_at)
        self.memory_store.import_legacy()
        self.memory_policy = previous_policy if isinstance(previous_policy, dict) else policy(
            self.s.get("configuration", {})
        )
        self.memory_profile = self.memory_store.profile(self.memory_policy, self.clock())
        self._refresh_memory()
        if self.s["state"] in ("running", "stopping"):
            self.s["state"] = "blocked"
            self.s["reason"] = (
                "Owner restarted; prior feed continuity and any open position are unknown"
            )
            if self.s.get("position") and self.s["position"]["state"] in (
                "open",
                "closing",
            ):
                self.s["position"]["state"] = "unknown"
                self.s["position"]["outcome"] = "unknown"
            self.learner["availability_failures"] += 1
            self._save_learner()
            self._save("recovery_unknown", {})
        db.commit()
        self.last_exchange = None
        self.connected = False

    def _save(self, kind, payload):
        now = self.clock()
        self.s["last_event"] = {"kind": kind, "at": now}
        self.db.execute(
            "INSERT INTO session VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value",
            (pack(self.s),),
        )
        self.db.execute(
            "INSERT INTO events(session_id,at,kind,payload) VALUES(?,?,?,?)",
            (self.s.get("session_id"), now, kind, pack(payload)),
        )

    def _validate_forecast(self, f):
        fields = {
            "forecast_id",
            "asset",
            "horizon_seconds",
            "source_basis",
            "market_address",
            "kind",
            "stream",
            "model_version",
            "target_type",
            "cutoff_at",
            "target_at",
            "issued_at",
            "reference_price",
            "p_up",
            "sample_count",
            "mode",
        }
        if not isinstance(f, dict) or set(f) != fields:
            raise ValueError("Invalid forecast fields")
        fid = f["forecast_id"]
        if (
            not isinstance(fid, str)
            or not 1 <= len(fid) <= 128
            or not fid.isascii()
            or not all(c.isalnum() or c in "-_." for c in fid)
        ):
            raise ValueError("Invalid forecast ID")
        if (
            f["asset"] not in ("BTC", "ZEC")
            or f["source_basis"]
            != {"BTC": "jupiter-pyth:1", "ZEC": "jupiter-pyth:66"}.get(f["asset"])
            or f["market_address"]
            != {
                "BTC": "BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7",
                "ZEC": "4ohWGDrmqdiEHinL5Kf2BYzM9UVSe3RJ1bzoveHehiwj",
            }.get(f["asset"])
            or f["kind"] != "oracle-ohlc"
            or f["stream"] != "fixed_rate@200ms"
            or f["model_version"] != "projected-logit-l2-v1"
            or f["target_type"] != "closed-price-up-vs-nonup-v1"
            or f["mode"] != "active"
        ):
            raise ValueError("Unsupported forecast identity or baseline")
        if (
            type(f["horizon_seconds"]) is not int
            or f["horizon_seconds"] not in (60, 300, 600, 900, 1200, 3600)
            or type(f["sample_count"]) is not int
            or not 20 <= f["sample_count"] <= 2**53 - 1
            or type(f["cutoff_at"]) is not int
            or f["cutoff_at"] % 60
            or f["target_at"] != f["cutoff_at"] + f["horizon_seconds"]
            or not _positive(f["issued_at"])
            or not 0 <= f["issued_at"] - f["cutoff_at"] <= 15
            or not 0 <= self.clock() - f["issued_at"] <= 30
            or f["target_at"] <= self.clock()
            or not _positive(f["reference_price"])
            or type(f["p_up"]) not in (int, float)
            or not math.isfinite(f["p_up"])
            or not 0 <= f["p_up"] <= 1
        ):
            raise ValueError("Stale or invalid forecast")
        return dict(f)

    @guard_state
    def request(self, request_id, action, config):
        if (
            not isinstance(request_id, str)
            or not 1 <= len(request_id) <= 128
            or not request_id.isascii()
            or not all(c.isalnum() or c in "-_." for c in request_id)
        ):
            raise ValueError("Invalid request ID")
        fp = hashlib.sha256(
            pack({"action": action, "config": config}).encode()
        ).hexdigest()
        with self.db:
            row = self.db.execute(
                "SELECT fingerprint,result FROM requests WHERE id=?", (request_id,)
            ).fetchone()
            if row:
                if row[0] != fp:
                    raise ValueError("Request ID already used for another request")
                original = json.loads(row[1])
                return public_state(
                    {
                        **self.s,
                        "accepted": original.get("accepted", False),
                        "request_id": request_id,
                        "replayed": True,
                        "original_session_id": original.get("session_id"),
                    }
                )
            if action == "start":
                if not isinstance(config, dict):
                    raise ValueError("Invalid configuration fields")
                user_config = {**self.s.get("configuration", {}), **config}
                p = policy(user_config)
                if self.s["state"] not in ("stopped", "failed"):
                    raise ValueError(
                        "Existing session requires resolution before start"
                    )
                cohort = hashlib.sha256(pack(p).encode()).hexdigest()
                self._select_learner(cohort, p)
                now = self.clock()
                sid = uuid.uuid4().hex
                pending_forecast = self.s.get("advisory_forecast")
                self.s = {
                    "state": "running",
                    "advisory_forecast": pending_forecast,
                    "mode": "paper",
                    "defaults": policy({}),
                    "configuration": user_config,
                    "readiness": {
                        "paper": "observed path simulation",
                        "live": "unavailable: no verified position, fill and settlement binding",
                        "1000x": "paper proxy available; live close, queue and payout unverified",
                        "advice": "enabled; private credential checked on call; fallback is immediate"
                        if p["advice_enabled"]
                        else "off",
                    },
                    "session_id": sid,
                    "position": None,
                    "reason": None,
                    "first_entry_deadline": now + 900,
                    "policy": p,
                    "cohort_id": cohort,
                    "started_at": now,
                    "warmup_samples": 0,
                    "policy_hash": hashlib.sha256(pack(p).encode()).hexdigest(),
                    "net_pnl_usd": 0.0,
                    "history": self._history_summary(),
                    "peak_net_usd": 0.0,
                    "loss_streak": 0,
                    "integrity_failure": False,
                    "last_exit_at": None,
                    "entries": 0,
                    "first_entry_at": None,
                    "next_entry_at": now,
                    "last_event": None,
                    "coverage": "observed stream; provider may coalesce updates",
                }
                self.last_exchange = None
                self.previous_price = None
                self.momentum = 0.0
                self.s["learner"] = dict(self.learner)
                self._refresh_memory()
                self._save("start_accepted", {"request_id": request_id})
            elif action == "stop":
                if self.s["state"] == "running":
                    self.s["state"] = (
                        "stopping" if self.s.get("position") else "stopped"
                    )
                    self._save("stop_requested", {"request_id": request_id})
                elif self.s["state"] == "blocked":
                    position = self.s.get("position") or {}
                    unknown = position.get("state") == "unknown"
                    if unknown and (
                        not isinstance(config, dict)
                        or config.get("acknowledge_unknown") is not True
                    ):
                        raise ValueError(
                            "Unknown paper position requires explicit acknowledge_unknown"
                        )
                    self.s["state"] = "stopped"
                    self.s["reason"] = (
                        "Paper unknown acknowledged; outcome remains unknown"
                        if unknown
                        else "Paper session ended; outcomes retained"
                    )
                    self._save("paper_session_ended", {"unknown_acknowledged": unknown})
            elif action == "forecast":
                if self.s["state"] not in ("stopped", "failed", "running"):
                    raise ValueError("Forecast unavailable while stopping or blocked")
                forecast = self._validate_forecast(config)
                old = self.db.execute(
                    "SELECT payload FROM forecasts WHERE id=?",
                    (forecast["forecast_id"],),
                ).fetchone()
                if old and old[0] != pack(forecast):
                    raise ValueError("Forecast ID reused with changed payload")
                if not old:
                    self.db.execute(
                        "INSERT INTO forecasts VALUES(?,?)",
                        (forecast["forecast_id"], pack(forecast)),
                    )
                self.s["advisory_forecast"] = forecast
                self._save("forecast_ingested", forecast)
            elif action == "configure":
                if self.s["state"] not in ("stopped", "failed"):
                    raise ValueError("Cannot change a frozen active policy")
                if not isinstance(config, dict):
                    raise ValueError("Invalid configuration fields")
                user_config = {**self.s.get("configuration", {}), **config}
                p = policy(user_config)
                self.s["configuration"] = {
                    key: p[key]
                    for key in (
                        "mode",
                        "asset",
                        "venue",
                        "base_collateral_usd",
                        "max_collateral_usd",
                        "max_session_loss_usd",
                        "advice_enabled",
                    )
                }
                self.s["readiness"]["advice"] = (
                    "enabled; private credential checked on call; fallback is immediate"
                    if p["advice_enabled"]
                    else "off"
                )
                self.memory_policy = p
                self.memory_profile = self.memory_store.profile(p, self.clock())
                self._refresh_memory()
                self._save("configuration_updated", {"policy": p})
            else:
                raise ValueError("Invalid command")
            result = public_state(
                {**self.s, "accepted": True, "request_id": request_id}
            )
            self.db.execute(
                "INSERT INTO requests VALUES(?,?,?,?)",
                (request_id, fp, pack(result), self.clock()),
            )
            return result

    @guard_state
    def error(self, reason):
        if self.s["state"] not in ("running", "stopping"):
            return
        with self.db:
            self.learner["availability_failures"] += 1
            self._save_learner()
            self.s["learner"] = dict(self.learner)
            self.s["history"] = self._history_summary()
            p = self.s.get("position")
            if p and p["state"] in ("open", "closing"):
                p.update(state="unknown", outcome="unknown", reason=reason)
                self.s.update(state="blocked", reason=reason)
            else:
                self.s.update(state="failed", reason=reason)
            self._save("feed_failure", {"reason": reason})

    @guard_state
    def tick(self, tick):
        if self.s["state"] not in ("running", "stopping"):
            return
        now = self.clock()
        config = self.s["policy"]
        if tick.get("asset") != config["asset"]:
            return
        at, ex, price = (
            tick.get("received_at"),
            tick.get("exchange_at"),
            tick.get("price"),
        )
        if (_positive(at) and at < self.s["started_at"]) or (
            _positive(ex) and ex < self.s["started_at"]
        ):
            return
        if self.s["first_entry_at"] is None and now >= self.s["first_entry_deadline"]:
            self.error(
                "First-entry deadline expired without a valid connected Jupiter quote"
            )
            return
        if (
            not _positive(at)
            or not _positive(ex)
            or not _positive(price)
            or not 0 <= now - at <= 1
            or not -0.25 <= at - ex <= 1
            or tick.get("feed_id") != {"BTC": 1, "ZEC": 66}[config["asset"]]
            or tick.get("quote_currency") != "USD"
            or (self.last_exchange is not None and ex < self.last_exchange)
        ):
            self.error("stale, invalid or out-of-order Jupiter quote")
            return
        previous_exchange = self.last_exchange
        self.last_exchange = ex
        if self.s["first_entry_at"] is None and (
            previous_exchange is None or ex > previous_exchange
        ):
            self.s["warmup_samples"] += 1
        if self.previous_price is not None:
            change = price / self.previous_price - 1
            self.momentum = 0.2 * change + 0.8 * self.momentum
        self.previous_price = price
        with self.db:
            p = self.s.get("position")
            if p and p["state"] in ("open", "closing"):
                p = engine.step(
                    p, at=at, price=price, stop=self.s["state"] == "stopping"
                )
                self.s["position"] = p
                if p["state"] == "unknown":
                    self.learner["availability_failures"] += 1
                    self._save_learner()
                    self.s["learner"] = dict(self.learner)
                    self.s["history"] = self._history_summary()
                    self.s.update(state="blocked", reason=p["reason"])
                elif p["state"] in ("closed", "liquidated"):
                    if not self._learn(p):
                        self.s.update(
                            state="blocked",
                            reason="This outcome is already saved; reconciliation is required",
                        )
                        self._save("duplicate_saved_outcome", {})
                        return
                    self.s["net_pnl_usd"] += p["net_pnl_usd"]
                    self.s["peak_net_usd"] = max(
                        self.s["peak_net_usd"], self.s["net_pnl_usd"]
                    )
                    self.s["loss_streak"] = (
                        0 if p["outcome"] == "win" else self.s["loss_streak"] + 1
                    )
                    self._save("position_outcome", p)
                    if self.s["state"] == "stopping":
                        self.s["state"] = "stopped"
                    elif self.s["net_pnl_usd"] <= -config["max_session_loss_usd"]:
                        self.s.update(
                            state="blocked", reason="Session loss limit reached"
                        )
                    elif self._history_summary()["net_pnl_usd"] <= 0:
                        self.s.update(
                            state="blocked",
                            reason="Paper outcomes are not overall profitable; entries paused",
                        )
                    else:
                        self.s["position"] = None
                        self.s["last_exit_at"] = at
                        self.s["next_entry_at"] = at + 15
            elif (
                self.s["state"] == "running"
                and at >= self.s["next_entry_at"]
                and (
                    self.s["first_entry_at"] is not None
                    or self.s["warmup_samples"] >= 2
                    or at - self.s["started_at"] >= 3
                    or at >= self.s["first_entry_deadline"] - 2
                )
            ):
                # Reserve collateral and estimated costs against the session loss budget.
                remaining = config["max_session_loss_usd"] + self.s["net_pnl_usd"]
                if (
                    engine.worst_loss(config["base_collateral_usd"], config["leverage"])
                    > remaining
                ):
                    self.s.update(
                        state="blocked",
                        reason="Remaining session loss budget cannot cover another position",
                    )
                    self._save("risk_stop", {})
                    return
                signal = (
                    1 if self.momentum > 1e-8 else -1 if self.momentum < -1e-8 else 0
                )
                direction = "long" if signal >= 0 else "short"
                scores = {
                    side: self._memory_score([1.0, sign, sign * signal])
                    for side, sign in (("long", 1.0), ("short", -1.0))
                }
                if (
                    self._memory_samples() >= 20
                    and abs(scores["long"] - scores["short"]) > 0.01
                ):
                    direction = max(scores, key=scores.get)
                advisory = self.s.get("advisory_forecast")
                valid_advisory = (
                    advisory
                    and advisory["asset"] == config["asset"]
                    and at - advisory["issued_at"] >= 0
                    and at - advisory["issued_at"] <= 30
                    and at < advisory["target_at"]
                    and abs(price / advisory["reference_price"] - 1) <= 0.005
                    and advisory["p_up"] != 0.5
                )
                advice = self.s.get("advice_observation") or {}
                advice_direction = (advice.get("result") or {}).get("direction")
                valid_advice = (
                    not valid_advisory
                    and advice_direction in ("long", "short")
                    and 0 <= at - advice.get("at", 0) <= 3
                    and _positive(advice.get("reference_price"))
                    and abs(price / advice["reference_price"] - 1) <= 0.005
                )
                if valid_advisory:
                    direction = "long" if advisory["p_up"] > 0.5 else "short"
                elif valid_advice:
                    direction = advice_direction
                sign = 1.0 if direction == "long" else -1.0
                features = [1.0, sign, sign * signal]
                forecast = {
                    "version": MEMORY_MODEL_VERSION,
                    "source": "Chrome Oracle advisory"
                    if valid_advisory
                    else "Anthropic advisory"
                    if valid_advice
                    else "causal Jupiter tick EMA",
                    "advisory_forecast_id": advisory["forecast_id"]
                    if valid_advisory
                    else None,
                    "momentum": self.momentum,
                    "direction": direction,
                    "features": features,
                    "score": scores[direction],
                    "samples": self._memory_samples(),
                    "calibrated": False,
                    "forced": signal == 0 and not valid_advisory and not valid_advice,
                    "at": at,
                }
                boost = boost_eligible(
                    self.learner, scores[direction], self.s, direction
                )
                last_exit = self.s.get("last_exit_at")
                if (
                    not boost
                    and last_exit is not None
                    and at < last_exit + config["cooldown_seconds"]
                ):
                    self._save(
                        "observed_tick",
                        {
                            "at": at,
                            "exchange_at": ex,
                            "price": price,
                            "feed_id": tick["feed_id"],
                        },
                    )
                    return
                collateral = float(
                    (
                        Decimal(str(config["base_collateral_usd"]))
                        * (Decimal("1.5") if boost else Decimal(1))
                    ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
                )
                if (
                    collateral > config["max_collateral_usd"]
                    or engine.worst_loss(collateral, config["leverage"]) > remaining
                ):
                    boost = False
                    collateral = config["base_collateral_usd"]
                    if (
                        last_exit is not None
                        and at < last_exit + config["cooldown_seconds"]
                    ):
                        self._save(
                            "observed_tick",
                            {
                                "at": at,
                                "exchange_at": ex,
                                "price": price,
                                "feed_id": tick["feed_id"],
                            },
                        )
                        return
                forecast["boost_eligible"] = boost
                forecast["boost_reason"] = (
                    "execution-aware engineering gate met"
                    if boost
                    else "base size: calibration, performance, integrity, or risk cap gate not met"
                )
                plan = engine.make_plan(
                    at=at,
                    price=price,
                    direction=direction,
                    collateral=collateral,
                    leverage=config["leverage"],
                )
                plan["asset"] = config["asset"]
                plan["policy_hash"] = self.s["policy_hash"]
                plan["intent_id"] = uuid.uuid4().hex
                self.s["position"] = engine.open_position(plan, at)
                self.s["position"]["forecast"] = forecast
                self.s["forecast"] = forecast
                self.s["entries"] += 1
                if self.s["first_entry_at"] is None:
                    self.s["first_entry_at"] = at
                self._save("entry", {"plan": plan, "forecast": forecast})
            self._save(
                "observed_tick",
                {
                    "at": at,
                    "exchange_at": ex,
                    "price": price,
                    "feed_id": tick["feed_id"],
                },
            )

    def _score(self, features):
        z = sum(w * x for w, x in zip(self.learner["weights"], features))
        return 1 / (1 + math.exp(-max(-20.0, min(20.0, z))))

    def _memory_samples(self):
        return self.memory_profile["samples"] or self.learner["samples"]

    def _memory_score(self, features):
        if self.memory_profile["samples"]:
            return memory_score(self.memory_profile["weights"], features)
        return self._score(features)

    def _refresh_memory(self):
        self.memory_profile = self.memory_store.profile(self.memory_policy, self.clock())
        self.s["learning_memory"] = self.memory_store.summary(self.memory_policy, self.clock())

    def _history_summary(self):
        rows = [
            json.loads(row[0])
            for row in self.db.execute("SELECT value FROM learner_cohorts")
        ]
        return {
            "cohorts": len(rows),
            "samples": sum(row["samples"] for row in rows),
            "net_pnl_usd": sum(row["net_pnl_usd"] for row in rows),
            "availability_failures": sum(
                row.get("availability_failures", 0) for row in rows
            ),
            "scope": "modeled paper outcomes across policy cohorts; no live proof",
        }

    def _select_learner(self, asset, selected_policy):
        if asset != self.learner_asset:
            self.learner_asset = asset
            row = self.db.execute(
                "SELECT value FROM learner_cohorts WHERE cohort=?", (asset,)
            ).fetchone()
            self.learner = json.loads(row[0]) if row else {
                "version": "paper-net-outcome-v1",
                "samples": 0,
                "wins": 0,
                "losses": 0,
                "liquidations": 0,
                "net_pnl_usd": 0.0,
                "brier_sum": 0.0,
                "availability_failures": 0,
                "high_n": 0,
                "high_wins": 0,
                "high_score_sum": 0.0,
                "weights": [0.0, 0.0, 0.0],
                "sides": {},
            }
        self.memory_policy = selected_policy
        self.memory_profile = self.memory_store.select(selected_policy, asset, self.clock())

    def _save_learner(self):
        self.db.execute(
            "INSERT INTO learner_cohorts VALUES(?,?) ON CONFLICT(cohort) DO UPDATE SET value=excluded.value",
            (self.learner_asset, pack(self.learner)),
        )

    def _learn(self, position):
        if not self.memory_store.record(self.s["policy"], position, self.clock()):
            return False
        forecast = position["forecast"]
        features = forecast["features"]
        won = position["outcome"] == "win"
        current = self._score(features)
        self.learner["weights"] = [
            max(-5.0, min(5.0, w + 0.05 * (int(won) - current) * x))
            for w, x in zip(self.learner["weights"], features)
        ]
        self.learner["samples"] += 1
        self.learner["wins" if won else "losses"] += 1
        if position["state"] == "liquidated":
            self.learner["liquidations"] += 1
        self.learner["net_pnl_usd"] += position["net_pnl_usd"]
        self.learner["brier_sum"] += (forecast["score"] - int(won)) ** 2
        side = self.learner.setdefault("sides", {}).setdefault(
            forecast["direction"],
            {
                "samples": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl_usd": 0.0,
                "brier_sum": 0.0,
                "high_n": 0,
                "high_wins": 0,
                "high_score_sum": 0.0,
            },
        )
        side["samples"] += 1
        side["wins" if won else "losses"] += 1
        side["net_pnl_usd"] += position["net_pnl_usd"]
        side["brier_sum"] += (forecast["score"] - int(won)) ** 2
        if forecast["score"] >= 0.75:
            side["high_n"] += 1
            side["high_wins"] += int(won)
            side["high_score_sum"] += forecast["score"]
        if forecast["score"] >= 0.75:
            self.learner["high_n"] += 1
            self.learner["high_wins"] += int(won)
            self.learner["high_score_sum"] += forecast["score"]
        self._save_learner()
        self.s["learner"] = dict(self.learner)
        self.s["history"] = self._history_summary()
        self._refresh_memory()
        return True

    def handle_tick(self, tick):
        try:
            self.tick(tick)
        except (ValueError, TypeError, KeyError, ArithmeticError, AttributeError):
            self.error(
                "Internal paper model or feed processing failure; no further entries"
            )

    @guard_state
    def _import_memory(self, now):
        with self.db:
            if self.memory_store.import_legacy():
                self._refresh_memory()
                self._save("learning_memory_checkpoint", {})
        self.last_memory_import_at = now

    def timer(self):
        now = self.clock()
        if self.last_memory_import_at is None or now - self.last_memory_import_at >= 1:
            # Each guarded operation restores only its own transaction. A
            # subsequent feed-error write must not undo committed import RAM.
            self._import_memory(now)
        if (
            self.s["state"] == "running"
            and self.s["first_entry_at"] is None
            and now >= self.s["first_entry_deadline"]
        ):
            self.error(
                "First-entry deadline expired without a valid connected Jupiter quote"
            )
        p = self.s.get("position")
        if (
            self.s["state"] in ("running", "stopping")
            and p
            and p["state"] in ("open", "closing")
            and now - p["last_at"] > 2
        ):
            self.error("Jupiter quote stream gap while position was at risk")


class ResourceRetirement:
    """Close one detached generation without blocking the owner IPC loop."""

    def __init__(self, feed, advisor):
        self.error = False
        self.finished = threading.Event()

        def run():
            try:
                for resource in (feed, advisor):
                    if resource is not None:
                        try:
                            resource.close()
                        except Exception:  # noqa: BLE001 - cleanup failure fences the next start
                            self.error = True
            finally:
                self.finished.set()

        self.thread = threading.Thread(
            target=run, name="autotrade-resource-retirement", daemon=True
        )
        self.thread.start()


def serve():
    from oracle_leverage.autotrade import _connect, _home

    home = _home()
    db = _connect(home)
    lockfd = os.open(home / "owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    lockinfo = os.fstat(lockfd)
    if lockinfo.st_uid != os.getuid() or lockinfo.st_mode & 0o077:
        raise ValueError("Invalid owner lock")
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lockfd)
        db.close()
        return
    path = home / "owner.sock"
    feed = None
    advisor = None
    retirement = None
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
        with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as server:
            server.bind(str(path))
            os.chmod(path, 0o600)
            server.listen(8)
            server.settimeout(0.05)
            session = Session(db)
            while True:
                if feed is not None:
                    for _ in range(128):
                        try:
                            kind, value = feed.events.get_nowait()
                        except queue.Empty:
                            break
                        if kind == "tick":
                            if not isinstance(value, dict):
                                session.error("Invalid execution feed event")
                                continue
                            if (
                                advisor is not None
                                and session.s.get("state") == "running"
                                and (
                                    not session.s.get("position")
                                    or session.s.get("entries", 0) == 0
                                )
                                and value.get("received_at", 0)
                                >= session.s.get("next_entry_at", 0) - 3
                                and value.get("asset")
                                == session.s.get("policy", {}).get("asset")
                            ):
                                advisor.offer(
                                    {
                                        "price": value.get("price"),
                                        "momentum": session.momentum,
                                    },
                                    value.get("received_at", 0),
                                )
                            session.handle_tick(value)
                        elif kind == "error":
                            session.error(value)
                        elif kind == "comparison":
                            if value.get("asset") == session.s.get("policy", {}).get(
                                "asset"
                            ):
                                session.s["coinbase_comparison"] = value
                        elif kind == "comparison_error":
                            session.s["coinbase_comparison"] = {"status": value}
                if advisor is not None:
                    observation = advisor.poll()
                    if observation is not None:
                        session.s["advice_observation"] = observation
                session.timer()
                if session.s.get("state") in ("stopped", "blocked", "failed") and (
                    feed is not None or advisor is not None
                ):
                    # Detached references are exclusively owned by this retirement generation.
                    retirement = ResourceRetirement(feed, advisor)
                    feed = None
                    advisor = None
                if retirement is None:
                    session.s["cleanup"] = "idle"
                elif not retirement.finished.is_set():
                    session.s["cleanup"] = "in_progress"
                elif retirement.error:
                    session.s["cleanup"] = (
                        "failed; restart is fenced until cleanup is resolved"
                    )
                else:
                    retirement = None
                    session.s["cleanup"] = "idle"
                try:
                    client, _ = server.accept()
                except TimeoutError:
                    continue
                with closing(client):
                    client.settimeout(1)
                    try:
                        data = bytearray()
                        while b"\n" not in data and len(data) <= 65536:
                            part = client.recv(4096)
                            if not part:
                                break
                            data.extend(part)
                        if len(data) > 65536 or b"\n" not in data:
                            raise ValueError("Invalid request")
                        req = json.loads(data.split(b"\n", 1)[0])
                        if not isinstance(req, dict):
                            raise TypeError("Invalid request")
                        action = req.get("action")
                        if action == "status":
                            result = public_state(session.s)
                        else:
                            if action == "start" and retirement is not None:
                                prior = session.db.execute(
                                    "SELECT 1 FROM requests WHERE id=?",
                                    (req.get("request_id"),),
                                ).fetchone()
                                if prior is None:
                                    raise ValueError(
                                        "Previous session cleanup is in progress or failed; retry after cleanup"
                                    )
                            previous_session_id = session.s.get("session_id")
                            result = session.request(
                                req.get("request_id"), action, req.get("config")
                            )
                            new_start = (
                                action == "start"
                                and session.s.get("session_id") != previous_session_id
                            )
                            if (
                                new_start
                                and result["accepted"]
                                and (feed is None or not feed.thread.is_alive())
                            ):
                                if feed is not None:
                                    feed.close()
                                feed = ExecutionFeed()
                                feed.start()
                            if new_start and result["accepted"]:
                                advisor = AsyncAdvice(
                                    Advice(
                                        enabled=session.s["policy"]["advice_enabled"]
                                    )
                                )
                        response = {"ok": True, "result": result}
                    except ValueError as error:
                        response = {"ok": False, "error": str(error)}
                    except (TypeError, KeyError, TimeoutError, OSError):
                        response = {
                            "ok": False,
                            "error": "Invalid request or session unavailable",
                        }
                    try:
                        client.sendall(pack(response).encode() + b"\n")
                    except OSError:
                        pass
    finally:
        if feed:
            feed.close()
        if path.exists() or path.is_symlink():
            path.unlink()
        db.close()
        os.close(lockfd)


if __name__ == "__main__":
    serve()
