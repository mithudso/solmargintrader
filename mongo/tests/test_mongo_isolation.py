"""Offline capability/opt-in regressions: fake clients only, never a socket."""

from __future__ import annotations

import builtins
import contextlib
import copy
import io
import socket
import unittest
from unittest import mock

from mongo import load, schema
from mongo.tests import mongo_fixture as fixture


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.iterator = iter(self.rows)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iterator)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, count):
        return FakeCursor(self.rows[:count])

    def close(self):
        pass


class FakeCollection:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.rows = []
        self.spec = {}

    def options(self):
        return self.spec

    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, doc):
        self.rows.append(copy.deepcopy(doc))

    def insert_many(self, docs, **kwargs):
        self.rows.extend(copy.deepcopy(docs))

    def replace_one(self, key, doc, **kwargs):
        self.rows = [
            r for r in self.rows if not all(r.get(k) == v for k, v in key.items())
        ] + [copy.deepcopy(doc)]

    def count_documents(self, query):
        return len(self.rows)

    def find_one(self, *args, **kwargs):
        return self.rows[0] if self.rows else None

    def find(self, *args, **kwargs):
        return FakeCursor(self.rows)

    def aggregate(self, *args, **kwargs):
        return FakeCursor(self.rows)

    def drop(self):
        self.db.drop_collection(self.name)


class FakeDatabase:
    def __init__(self, raw, name):
        self.raw, self.name, self.collections = raw, name, {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection(self, name))

    def command(self, command, *args, **kwargs):
        self.raw.events.append((command, self.name))
        if command == "ping" and self.raw.fail_ping:
            raise ConnectionError("synthetic unavailable server")
        return {"ok": 1}

    def drop_collection(self, name):
        self.collections.pop(name, None)

    def create_collection(self, name, **kwargs):
        from pymongo.errors import CollectionInvalid

        if name in self.collections:
            raise CollectionInvalid("fixture exists")
        collection = self[name]
        collection.spec = kwargs
        return collection

    def list_collection_names(self, **kwargs):
        return list(self.collections)


class FakeRawClient:
    def __init__(self, events, *, fail_ping=False, fail_drop=False):
        self.events, self.fail_ping, self.fail_drop = events, fail_ping, fail_drop
        self.databases = {}
        self.closed = False

    def __getitem__(self, name):
        self.events.append(("select", name))
        return self.databases.setdefault(name, FakeDatabase(self, name))

    def drop_database(self, name):
        self.events.append(("drop", name))
        if self.fail_drop:
            raise RuntimeError("synthetic drop failure")
        self.databases.pop(name, None)

    def close(self):
        self.events.append(("close",))
        self.closed = True


class OptInTests(unittest.TestCase):
    def test_unset_skips_before_import_or_factory_even_with_legacy_flag(self):
        for env in ({}, {"MARKET_CAPTURE_REQUIRE_MONGO": "1"}):
            with (
                mock.patch.object(
                    builtins,
                    "__import__",
                    side_effect=AssertionError("imported driver"),
                ),
                mock.patch.object(fixture, "DisposableMongoFixture") as constructor,
            ):
                with self.assertRaises(unittest.SkipTest):
                    fixture.require_test_uri(env)
                constructor.assert_not_called()
        factory = mock.Mock(side_effect=AssertionError("constructed client"))
        with self.assertRaises(unittest.SkipTest):
            fixture.DisposableMongoFixture.for_test(
                self, environ={}, client_factory=factory
            )
        factory.assert_not_called()

    def test_only_bare_loopback_uris_are_accepted_before_driver(self):
        for uri in (
            "mongodb://127.0.0.1",
            "mongodb://localhost:27017",
            "mongodb://[::1]:65535",
        ):
            self.assertEqual(fixture.require_test_uri({fixture.KEY: uri}), uri)
        for uri in (
            "",
            " ",
            "mongodb+srv://localhost",
            "mongodb://user@localhost",
            "mongodb://remote.invalid",
            "mongodb://127.0.0.1/",
            "mongodb://localhost/db",
            "mongodb://localhost?tls=false",
            "mongodb://localhost#x",
            "mongodb://localhost:",
            "mongodb://localhost:0",
            "mongodb://localhost:65536",
            "mongodb://localhost,127.0.0.1",
            "mongodb://localhost\\evil",
            "mongodb://local%68ost",
            "mongodb://[::1",
            "mongodb://localhost\n",
        ):
            factory = mock.Mock()
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                fixture.DisposableMongoFixture.for_test(
                    self, environ={fixture.KEY: uri}, client_factory=factory
                )
            factory.assert_not_called()

    def test_explicit_unreachable_fails_instead_of_skipping_and_closes(self):
        events = []
        raw = FakeRawClient(events, fail_ping=True)
        factory = mock.Mock(return_value=raw)
        with self.assertRaises(ConnectionError):
            fixture.DisposableMongoFixture.for_test(
                self,
                environ={fixture.KEY: "mongodb://127.0.0.1"},
                client_factory=factory,
            )
        self.assertTrue(raw.closed)
        self.assertFalse(any(event[0] == "drop" for event in events))
        factory.assert_called_once_with(
            "mongodb://127.0.0.1",
            connect=False,
            directConnection=True,
            tz_aware=True,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=1500,
        )

    def test_explicit_missing_driver_is_error(self):
        original = builtins.__import__

        def importer(name, *args, **kwargs):
            if name == "pymongo":
                raise ImportError("synthetic missing driver")
            return original(name, *args, **kwargs)

        with (
            mock.patch.object(builtins, "__import__", side_effect=importer),
            self.assertRaises(ImportError),
        ):
            fixture.DisposableMongoFixture.for_test(
                self, environ={fixture.KEY: "mongodb://localhost"}
            )


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.raw = FakeRawClient(self.events)
        self.fixture = fixture.DisposableMongoFixture.for_test(
            self,
            environ={fixture.KEY: "mongodb://localhost"},
            client_factory=lambda *a, **k: self.raw,
        )

    def test_namespace_and_returned_handles_cannot_select_other_databases(self):
        c = self.fixture._primary
        for name in (
            "solmargintrader",
            "market_capture",
            "admin",
            "local",
            "config",
            "solmargintrader_test_" + "f" * 32,
        ):
            with self.subTest(name=name):
                for action in (
                    lambda name=name: c[name],
                    lambda name=name: c.get_database(name),
                    lambda name=name: c.drop_database(name),
                ):
                    before = list(self.events)
                    with self.assertRaises(ValueError):
                        action()
                    self.assertEqual(self.events, before)
        with self.assertRaises(AttributeError):
            _ = c.admin
        with self.assertRaises(AttributeError):
            c.get_default_database()
        col = self.fixture.db.get_collection("signals")
        self.assertIs(col.database.client, c)
        self.assertIs(col.find().collection, col)
        self.assertIs(col.aggregate([]).collection, col)
        with self.assertRaises(ValueError):
            col.database.client["solmargintrader"]
        for command in (
            {"dropDatabase": 1},
            "dropDatabase",
            "renameCollection",
            "eval",
        ):
            with self.assertRaises(ValueError):
                self.fixture.db.command(command)
        for pipeline in (
            [{"$out": "signals"}],
            [{"$merge": {"into": {"db": "solmargintrader", "coll": "signals"}}}],
            [{"$facet": {"x": [{"$lookup": {"from": "elsewhere"}}]}}],
        ):
            with self.assertRaises(ValueError):
                col.aggregate(pipeline)
        with self.assertRaises(AttributeError):
            col.rename("elsewhere")

    def test_bindings_restore_and_production_default_uri_fails_before_factory(self):
        originals = schema.DB_NAME, load.DB_NAME, schema.connect, load.connect
        self.fixture.bind_store()
        self.assertEqual(schema.DB_NAME, self.fixture.db_name)
        self.assertEqual(load.DB_NAME, self.fixture.db_name)
        self.assertEqual(schema.connect, load.connect)
        with self.assertRaises(ValueError):
            load.connect("mongodb://localhost:27017/solmargintrader")
        with self.assertRaises(TypeError):
            schema.connect()
        self.fixture.close()
        self.assertEqual(
            (schema.DB_NAME, load.DB_NAME, schema.connect, load.connect), originals
        )
        drops = [e[1] for e in self.events if e[0] == "drop"]
        self.assertEqual(drops, [self.fixture.db_name])
        self.fixture.close()
        self.assertEqual([e[1] for e in self.events if e[0] == "drop"], drops)

    def test_seed_uses_real_loaders_and_only_disposable_inputs(self):
        with mock.patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ):
            self.fixture.seed_store()
        db = self.fixture.db
        self.assertEqual(db.bars.count_documents({}), 2)
        self.assertGreater(db.strategies.count_documents({}), 1)
        self.assertGreater(db.decisions.count_documents({}), 0)
        self.assertEqual(db.experiment_rows.count_documents({}), 4)
        receipts = list(db.test_results.find())
        self.assertEqual([(r["count"], r["ok"]) for r in receipts], [(1, True)])
        self.assertTrue(
            all(
                event[1] == self.fixture.db_name
                for event in self.events
                if event[0] != "close"
            )
        )

    def test_schema_cli_uses_guarded_binding_and_explicit_uri(self):
        self.fixture.bind_store()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(schema.main(["--create", "--uri", self.fixture.uri]), 0)
        self.assertTrue(self.fixture.db.list_collection_names())
        with self.assertRaises(ValueError):
            schema.main(["--create"])


class CleanupTests(unittest.TestCase):
    def test_cleanup_registered_before_client_construction(self):
        events = []
        owner = mock.Mock()
        owner.addCleanup.side_effect = lambda callback: events.append("registered")

        def factory(*args, **kwargs):
            events.append("client")
            raise RuntimeError("synthetic setup failure")

        with self.assertRaises(RuntimeError):
            fixture.DisposableMongoFixture.for_test(
                owner,
                environ={fixture.KEY: "mongodb://localhost"},
                client_factory=factory,
            )
        self.assertEqual(events, ["registered", "client"])

    def test_drop_failure_still_closes_all_clients_and_restores_bindings(self):
        events = []
        clients = []

        def factory(*args, **kwargs):
            raw = FakeRawClient(events, fail_drop=True)
            clients.append(raw)
            return raw

        f = fixture.DisposableMongoFixture.for_test(
            self, environ={fixture.KEY: "mongodb://localhost"}, client_factory=factory
        )
        original = schema.DB_NAME
        f.bind_store()
        f.connect(f.uri)
        with self.assertRaises(RuntimeError):
            f.close()
        self.assertTrue(all(c.closed for c in clients))
        self.assertEqual(schema.DB_NAME, original)


class DiscoverySafetyTests(unittest.TestCase):
    def test_native_setup_skips_before_any_driver_probe_even_with_legacy_flag(self):
        import os
        import runpy
        from pathlib import Path

        original_import = builtins.__import__

        def importer(name, *args, **kwargs):
            if name == "pymongo" or name.startswith("pymongo."):
                raise AssertionError("native opt-out imported driver")
            return original_import(name, *args, **kwargs)

        root = Path(__file__).resolve().parents[2]
        with (
            mock.patch.dict(
                os.environ, {"MARKET_CAPTURE_REQUIRE_MONGO": "1"}, clear=True
            ),
            mock.patch.object(builtins, "__import__", side_effect=importer),
            mock.patch.object(
                schema, "connect", side_effect=AssertionError("schema connect")
            ),
            mock.patch.object(
                load, "connect", side_effect=AssertionError("load connect")
            ),
            mock.patch.object(
                socket.socket, "connect", side_effect=AssertionError("socket")
            ),
        ):
            loaded = runpy.run_path(str(root / "mongo/tests/test_load.py"))
            with self.assertRaises(unittest.SkipTest):
                loaded["TestLoadedStore"].setUpClass()
            with self.assertRaises(unittest.SkipTest):
                loaded["TestIdempotency"](
                    "test_two_loads_leave_identical_counts"
                ).setUp()
            capture = runpy.run_path(str(root / "scripts/test_capture_market.py"))
            with self.assertRaises(unittest.SkipTest):
                capture["NativeMongoTests"](
                    "test_real_time_series_insert_checkpoint_and_readback"
                ).setUp()
