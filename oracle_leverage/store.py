"""Durable paper decisions and explicit venue intents; no private keys."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def default_home():
    return Path.home() / ".local/state/oracle-leverage"


class Store:
    def __init__(self, home):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.home.stat().st_uid != os.getuid() or self.home.stat().st_mode & 0o077:
            raise ValueError("Oracle leverage directory must be owner-only (0700)")
        self.path = self.home / "ledger.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS predictions(
                  id TEXT PRIMARY KEY, asset TEXT NOT NULL, rule_id TEXT NOT NULL,
                  target_start INTEGER NOT NULL, target_end INTEGER NOT NULL,
                  decision_at REAL NOT NULL, entry_price REAL NOT NULL, entry_time REAL NOT NULL,
                  direction TEXT NOT NULL, rule_json TEXT NOT NULL, status TEXT NOT NULL,
                  exit_price REAL, correct INTEGER, gross_bps REAL, net_bps REAL,
                  UNIQUE(asset,target_start,target_end));
                CREATE TABLE IF NOT EXISTS intents(
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                  created_at REAL NOT NULL, updated_at REAL NOT NULL,
                  request_json TEXT NOT NULL, response_json TEXT NOT NULL);
            """)
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def meta(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put_meta(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, allow_nan=False)),
            )

    def add_prediction(self, value):
        keys = (
            "id",
            "asset",
            "rule_id",
            "target_start",
            "target_end",
            "decision_at",
            "entry_price",
            "entry_time",
            "direction",
            "rule_json",
            "status",
        )
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO predictions("
                + ",".join(keys)
                + ") VALUES("
                + ",".join("?" for _ in keys)
                + ")",
                tuple(value[k] for k in keys),
            )

    def predictions(self, status=None):
        with self.connect() as db:
            if status:
                rows = db.execute(
                    "SELECT * FROM predictions WHERE status=? ORDER BY target_start",
                    (status,),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM predictions ORDER BY target_start DESC LIMIT 2000"
                ).fetchall()
        return [dict(r) for r in rows]

    def settle(self, identity, *, exit_price, correct, gross_bps, net_bps):
        with self.connect() as db:
            db.execute(
                "UPDATE predictions SET status='settled',exit_price=?,correct=?,gross_bps=?,net_bps=? WHERE id=? AND status='open'",
                (exit_price, int(correct), gross_bps, net_bps, identity),
            )

    def intent(self, identity):
        with self.connect() as db:
            row = db.execute("SELECT * FROM intents WHERE id=?", (identity,)).fetchone()
        return dict(row) if row else None

    def intents(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM intents ORDER BY created_at DESC LIMIT 100"
                )
            ]

    def unresolved_intents(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM intents WHERE status IN ('submitting','submitted','unknown')"
                )
            ]

    def performance(self):
        with self.connect() as db:
            total = dict(
                db.execute(
                    "SELECT count(*) AS n,coalesce(sum(correct),0) AS correct,avg(net_bps) AS mean_net_bps FROM predictions WHERE status='settled'"
                ).fetchone()
            )
            total["open"] = db.execute(
                "SELECT count(*) FROM predictions WHERE status='open'"
            ).fetchone()[0]
            total["by_asset"] = {
                r["asset"]: dict(r)
                for r in db.execute(
                    "SELECT asset,count(*) AS n,coalesce(sum(correct),0) AS correct,avg(net_bps) AS mean_net_bps FROM predictions WHERE status='settled' GROUP BY asset"
                )
            }
        return total

    def put_intent(self, identity, kind, status, request, response):
        now = time.time()
        with self.connect() as db:
            db.execute(
                "INSERT INTO intents VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at,response_json=excluded.response_json",
                (
                    identity,
                    kind,
                    status,
                    now,
                    now,
                    json.dumps(request, allow_nan=False),
                    json.dumps(response, allow_nan=False),
                ),
            )
