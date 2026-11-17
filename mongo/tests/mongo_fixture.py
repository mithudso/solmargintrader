"""Explicit, namespace-guarded native Mongo fixtures. Importing this module does no I/O.

Unset SOLMARGINTRADER_MONGO_TEST_URI skips before importing the driver. An explicit
URI must be bare loopback and failures are errors. The facade prevents accidental
namespace escapes; it is not a sandbox against malicious Python introspection.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

KEY = "SOLMARGINTRADER_MONGO_TEST_URI"
_URI = re.compile(
    r"mongodb://(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?\Z", re.ASCII
)


def require_test_uri(environ=None):
    env = os.environ if environ is None else environ
    if KEY not in env:
        raise unittest.SkipTest(
            "native Mongo tests require explicit SOLMARGINTRADER_MONGO_TEST_URI"
        )
    uri = env[KEY]
    match = _URI.fullmatch(uri) if isinstance(uri, str) else None
    if not match or (match.group(1) and not 1 <= int(match.group(1)) <= 65535):
        raise ValueError(
            "Mongo test URI must be bare loopback without auth, path, query or fragment"
        )
    return uri


def _name(name):
    if (
        not isinstance(name, str)
        or not name
        or not re.fullmatch(r"[a-zA-Z0-9_-]+", name)
    ):
        raise ValueError("invalid test collection name")
    return name


def _pipeline(pipeline):
    if not isinstance(pipeline, list):
        raise TypeError("test pipeline must be a list")

    def inspect(value):
        if isinstance(value, dict):
            if set(value) & {
                "$out",
                "$merge",
                "$lookup",
                "$unionWith",
                "$changeStream",
            }:
                raise ValueError(
                    "cross-namespace/write pipeline is outside the test fixture"
                )
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(pipeline)


class GuardedCursor:
    def __init__(self, raw, collection):
        self._raw, self.collection = raw, collection

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._raw)

    def sort(self, *args, **kwargs):
        self._raw = self._raw.sort(*args, **kwargs)
        return self

    def limit(self, count):
        self._raw = self._raw.limit(count)
        return self

    def close(self):
        self._raw.close()


class GuardedCollection:
    def __init__(self, raw, database):
        self._raw, self.database = raw, database

    def options(self):
        return self._raw.options()

    def create_index(self, *args, **kwargs):
        return self._raw.create_index(*args, **kwargs)

    def insert_one(self, *args, **kwargs):
        return self._raw.insert_one(*args, **kwargs)

    def insert_many(self, *args, **kwargs):
        return self._raw.insert_many(*args, **kwargs)

    def replace_one(self, *args, **kwargs):
        return self._raw.replace_one(*args, **kwargs)

    def count_documents(self, *args, **kwargs):
        return self._raw.count_documents(*args, **kwargs)

    def find_one(self, *args, **kwargs):
        return self._raw.find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        return GuardedCursor(self._raw.find(*args, **kwargs), self)

    def aggregate(self, pipeline, **kwargs):
        _pipeline(pipeline)
        if kwargs:
            raise ValueError("aggregation options are outside the test fixture")
        return GuardedCursor(self._raw.aggregate(pipeline), self)

    def drop(self):
        return self._raw.drop()


class GuardedDatabase:
    def __init__(self, raw, client):
        self._raw, self.client, self.name = raw, client, client.db_name

    def __getitem__(self, name):
        return GuardedCollection(self._raw[_name(name)], self)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def get_collection(self, name):
        return self[name]

    def drop_collection(self, name):
        return self._raw.drop_collection(_name(name))

    def create_collection(self, name, **kwargs):
        if set(kwargs) - {
            "timeseries",
            "validator",
            "validationLevel",
            "validationAction",
        }:
            raise ValueError("collection options are outside the test fixture")
        return GuardedCollection(
            self._raw.create_collection(_name(name), **kwargs), self
        )

    def list_collection_names(self, **kwargs):
        if set(kwargs) - {"filter"}:
            raise ValueError("listing options are outside the test fixture")
        return self._raw.list_collection_names(**kwargs)

    def command(self, command, *args, **kwargs):
        if command == "ping" and not args and not kwargs:
            return self._raw.command("ping")
        if command == "listCollections" and not args and set(kwargs) <= {"filter"}:
            return self._raw.command(command, **kwargs)
        if (
            command == "collMod"
            and len(args) == 1
            and set(kwargs) <= {"validator", "validationLevel", "validationAction"}
        ):
            return self._raw.command(command, _name(args[0]), **kwargs)
        raise ValueError("database command is outside the test fixture")


class GuardedClient:
    def __init__(self, raw, db_name):
        if not re.fullmatch(r"solmargintrader_test_[0-9a-f]{32}", db_name):
            raise ValueError("fixture database must be generated internally")
        self._raw, self.db_name = raw, db_name

    def __getitem__(self, name):
        if name != self.db_name:
            raise ValueError("database is outside this disposable fixture")
        return GuardedDatabase(self._raw[name], self)

    def get_database(self, name):
        return self[name]

    def drop_database(self, name):
        if name != self.db_name:
            raise ValueError("database is outside this disposable fixture")
        return self._raw.drop_database(name)

    def close(self):
        self._raw.close()


class DisposableMongoFixture:
    def __init__(self, uri, *, client_factory=None):
        self.uri = require_test_uri({KEY: uri})
        self.db_name = "solmargintrader_test_" + uuid.uuid4().hex
        self._factory = client_factory
        self._clients = []
        self._stack = contextlib.ExitStack()
        self._opened = False
        self._closed = False
        self._primary = None

    @classmethod
    def for_test(cls, owner, *, class_scope=False, environ=None, client_factory=None):
        # This check precedes driver import, object creation and all connection probes.
        fixture = cls(require_test_uri(environ), client_factory=client_factory)
        (owner.addClassCleanup if class_scope else owner.addCleanup)(fixture.close)
        fixture.open()
        return fixture

    def _new_client(self):
        if self._factory is None:
            from pymongo import MongoClient

            self._factory = MongoClient
        raw = self._factory(
            self.uri,
            connect=False,
            directConnection=True,
            tz_aware=True,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=1500,
        )
        self._clients.append(raw)  # tracked before ping or namespace use
        return GuardedClient(raw, self.db_name)

    def open(self):
        if self._closed:
            raise RuntimeError("fixture is closed")
        self._primary = self._new_client()
        try:
            self.db = self._primary[self.db_name]
            self.db.command("ping")
            self._opened = True
        except Exception:
            self.close()
            raise
        return self

    def connect(self, uri):
        if uri != self.uri or self._closed or not self._opened:
            raise ValueError("connector requires this fixture's explicit approved URI")
        return self._new_client()

    def patch(self, obj, name, value):
        return self._stack.enter_context(mock.patch.object(obj, name, value))

    def bind_store(self):
        from mongo import load, schema

        for module in (schema, load):
            self.patch(module, "DB_NAME", self.db_name)
            self.patch(module, "connect", self.connect)

    def seed_store(self):
        """Real loader/schema against synthetic two-bar inputs; no owner data enumeration."""
        from backtester.core import strategy_cards
        from mongo import load

        self.bind_store()
        source_root = Path(__file__).resolve().parents[2]
        temporary = self._stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mongo-test-input-")
        )
        root = Path(temporary)
        for subdir in ("data", "research/results", "backtester/strategy_cards"):
            (root / subdir).mkdir(parents=True, exist_ok=True)
        (root / "data/SOL_1d.csv").write_text(
            "timestamp,open,high,low,close,volume\n86400,10,12,9,11,100\n172800,11,13,10,12,120\n"
        )
        (root / "data/JLP_spot.csv").write_text("symbol,price\n")
        for source in Path(strategy_cards.CARD_DIR).glob("*.md"):
            shutil.copyfile(source, root / "backtester/strategy_cards" / source.name)
        shutil.copyfile(source_root / "research/decide.py", root / "research/decide.py")
        (root / "research/results/cpcv_fixture.csv").write_text(
            "horizon,pbo,score\nshort,0.1,nan\nlong,0.2,1\n"
        )
        (root / "research/results/cpcv_fixture.json").write_text(
            json.dumps(
                [{"horizon": "short", "pbo": 0.1}, {"horizon": "long", "pbo": 0.2}]
            )
        )
        self.patch(load, "REPO", root)
        self.patch(strategy_cards, "CARD_DIR", root / "backtester/strategy_cards")
        selection = (
            "bars,strategies,signals,indicators,decisions,experiments,experiment_rows"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            if load.main(["--uri", self.uri, "--only", selection]) != 0:
                raise RuntimeError("fixture loader failed")
        # Observe one real, bounded, purely synthetic existing test through the real receipt parser.
        command = [
            sys.executable,
            "-m",
            "unittest",
            "backtester.tests.test_engine.TestBuyAndHoldIdentity.test_zero_cost_identity",
        ]
        with (
            mock.patch.object(load, "REPO", source_root),
            mock.patch.object(load, "SUITE_COMMANDS", {"backtester": command}),
        ):
            receipts = load.load_test_results(
                run_suites=True, skip=("soltui", "extension")
            )
        if len(receipts) != 1 or receipts[0]["count"] != 1 or not receipts[0]["ok"]:
            raise RuntimeError("bounded fixture test receipt was not successful")
        from mongo import schema

        schema.create(self.db, drop=False, only={"test_results"})
        for doc in receipts:
            self.db.test_results.replace_one(
                {"git_sha": doc["git_sha"], "suite": doc["suite"]}, doc, upsert=True
            )

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if self._opened and self._primary is not None:
                self._primary.drop_database(self.db_name)
        finally:
            try:
                with contextlib.ExitStack() as closing:
                    for client in self._clients:
                        closing.callback(client.close)
            finally:
                self._stack.close()
