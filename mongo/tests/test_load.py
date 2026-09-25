"""Tests for the local MongoDB research store.

The load is destructive by design, so the test that matters most asserts it is
therefore *idempotent*: loading twice must leave identical counts. Without that,
the time series collections would silently double on a second run -- they accept no
unique index, so nothing else would catch it.

Tests needing a server skip cleanly when one is not listening, and they only ever
touch the `solmargintrader` database.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

try:
    from pymongo.errors import ServerSelectionTimeoutError, WriteError

    HAVE_PYMONGO = True
except ImportError:  # pragma: no cover - exercised on a checkout without the driver
    HAVE_PYMONGO = False

from mongo import schema  # noqa: E402

if HAVE_PYMONGO:
    from mongo import load  # noqa: E402


def server_available() -> bool:
    """True when a local mongod answers, so the integration tests can run."""
    if not HAVE_PYMONGO:
        return False
    client = schema.connect()
    try:
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False
    finally:
        # Closed explicitly: an abandoned client emits a ResourceWarning that
        # buries real test output in a traceback that looks like a failure.
        client.close()


SERVER = server_available()
needs_server = unittest.skipUnless(
    SERVER, "no mongod on localhost:27017; start one or skip these"
)
needs_pymongo = unittest.skipUnless(HAVE_PYMONGO, "pymongo not installed")


class TestPureHelpers(unittest.TestCase):
    """No server, no files -- just the coercion rules."""

    @needs_pymongo
    def test_clean_drops_non_finite_numbers(self) -> None:
        """NaN becomes None, not a value a later query would rank against.

        A NaN that reaches the store is worse than a gap: `$sort` and `$group` will
        happily order around it, and the reader sees a number-shaped hole.
        """
        self.assertIsNone(load.clean(float("nan")))
        self.assertIsNone(load.clean(float("inf")))
        self.assertEqual(load.clean(1.5), 1.5)
        self.assertEqual(load.clean({"a": [float("nan"), 2]}), {"a": [None, 2]})

    @needs_pymongo
    def test_clean_converts_numpy_scalars(self) -> None:
        """pymongo cannot encode a numpy scalar, so they must be unwrapped."""
        import numpy as np

        self.assertIsInstance(load.clean(np.float64(2.5)), float)
        self.assertIsInstance(load.clean(np.int64(3)), int)
        self.assertIsNone(load.clean(np.float64("nan")))

    @needs_pymongo
    def test_maybe_number_keeps_text_as_text(self) -> None:
        """A strategy name must not become a float."""
        self.assertEqual(load.maybe_number("42"), 42)
        self.assertEqual(load.maybe_number("2.5"), 2.5)
        self.assertEqual(load.maybe_number("ma_crossover"), "ma_crossover")
        self.assertIsNone(load.maybe_number(""))
        self.assertIsNone(load.maybe_number("nan"))

    @needs_pymongo
    def test_bar_files_excludes_the_spot_snapshot(self) -> None:
        """`JLP_spot.csv` is not a bar series and must not be loaded as one."""
        names = [path.name for path, _, _ in load.bar_files()]
        self.assertNotIn("JLP_spot.csv", names)
        if names:
            self.assertTrue(all(n.endswith(".csv") for n in names))

    @needs_pymongo
    def test_experiment_kind_prefers_the_longest_prefix(self) -> None:
        """`cpcv_all25_*` is a cross-asset run, not a plain cpcv one."""
        self.assertEqual(load.experiment_kind("cpcv_all25_1h"), "cross-asset")
        self.assertEqual(load.experiment_kind("cpcv_combos_results"), "cpcv")
        self.assertEqual(load.experiment_kind("cpcv_results"), "cpcv")
        self.assertEqual(load.experiment_kind("sweep_results"), "sweep")
        self.assertIsNone(load.experiment_kind("tables"))

    @needs_pymongo
    def test_a_list_sidecar_becomes_rows_not_a_blob(self) -> None:
        """The PBO-per-horizon case, which the validator caught during development.

        `cpcv_pbo.json` is a list of results. Stored as one opaque `summary`, the
        most queried number in the research set would need client-side parsing to
        reach.
        """
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cpcv_pbo.json"
            path.write_text(
                json.dumps([{"horizon": "short", "pbo": 0.34}, {"horizon": "long", "pbo": 0.7}]),
                encoding="utf-8",
            )
            summary, rows = load.read_sidecar(path)
            self.assertIsNone(summary)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["horizon"], "short")

            path.write_text(json.dumps({"pbo": 0.5}), encoding="utf-8")
            summary, rows = load.read_sidecar(path)
            self.assertEqual(summary, {"pbo": 0.5})
            self.assertEqual(rows, [])

            self.assertEqual(load.read_sidecar(Path(tmp) / "absent.json"), (None, []))


class TestSchemaLayout(unittest.TestCase):
    """The layout is inspectable without a server."""

    def test_describe_needs_no_server_or_driver(self) -> None:
        """`--describe` documents the store from a bare checkout."""
        text = schema.describe()
        self.assertIn("solmargintrader", text)
        for name in schema.ALL_COLLECTIONS:
            self.assertIn(name, text)

    def test_every_regular_collection_requires_provenance(self) -> None:
        """A document without provenance is not worth storing, so it is rejected."""
        for name, spec in schema.COLLECTIONS.items():
            with self.subTest(collection=name):
                required = spec["validator"]["$jsonSchema"]["required"]
                for field in ("source_path", "source_sha256", "loaded_at"):
                    self.assertIn(field, required)

    def test_time_series_collections_carry_no_validator(self) -> None:
        """MongoDB accepts neither $jsonSchema nor a unique index on a time series
        collection; asserting it here records *why* the loader must drop and reload."""
        for name, spec in schema.TIME_SERIES.items():
            with self.subTest(collection=name):
                self.assertNotIn("validator", spec)
                self.assertIn("timeField", spec["timeseries"])
                self.assertIn("metaField", spec["timeseries"])


@needs_server
class TestLoadedStore(unittest.TestCase):
    """Assertions against the store as loaded by `python3 mongo/load.py`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = schema.connect()
        cls.db = cls.client[schema.DB_NAME]
        if cls.db.strategies.count_documents({}) == 0:
            raise unittest.SkipTest("store is empty; run `python3 mongo/load.py` first")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_bars_is_a_native_time_series_collection(self) -> None:
        """Not a regular collection that merely holds timestamps."""
        info = self.db.command("listCollections", filter={"name": "bars"})
        entry = info["cursor"]["firstBatch"][0]
        self.assertEqual(entry["type"], "timeseries")
        self.assertEqual(entry["options"]["timeseries"]["timeField"], "ts")
        self.assertEqual(entry["options"]["timeseries"]["metaField"], "series")

    def test_every_document_has_provenance(self) -> None:
        """Sampled across every collection, including the time series ones."""
        for name in schema.ALL_COLLECTIONS:
            with self.subTest(collection=name):
                doc = self.db[name].find_one()
                if doc is None:
                    continue
                self.assertIn("loaded_at", doc)
                # Time series measurements carry path and checksum on the metaField,
                # where MongoDB stores it once per bucket instead of once per bar.
                meta_field = (
                    schema.TIME_SERIES.get(name, {}).get("timeseries", {}).get("metaField")
                )
                holder = doc.get(meta_field) if meta_field else doc
                self.assertIn("source_path", holder)
                self.assertIn("source_sha256", holder)

    def test_validation_is_strict(self) -> None:
        """A document missing provenance is refused by the server, not just by us."""
        with self.assertRaises(WriteError):
            self.db.signals.insert_one({"_id": "not-a-real-signal", "rule": "x"})

    def test_strategy_cards_keep_their_own_vocabulary(self) -> None:
        """45 cards, exactly 25 with a registry key, every key real.

        No invented `registered` flag: the 20 without a key are not simply
        unregistered -- the ladder grid is `implemented` and has no key because it is
        not a `Strategy` at all.
        """
        from backtester.core.strategies import REGISTRY

        self.assertEqual(self.db.strategies.count_documents({}), 45)
        keyed = list(self.db.strategies.find({"registry_key": {"$type": "string"}}))
        self.assertEqual(len(keyed), len(REGISTRY))
        for doc in keyed:
            self.assertIn(doc["registry_key"], REGISTRY)
            self.assertIsNotNone(doc["registry"], doc["_id"])
        self.assertEqual(
            self.db.strategies.count_documents({"registry_key": None}),
            45 - len(REGISTRY),
        )

    def test_signal_and_indicator_counts_track_decide_py(self) -> None:
        """A rule added to the readout must be reloaded, not silently missing here."""
        from research import decide

        self.assertEqual(self.db.signals.count_documents({}), len(decide.SIGNAL_RULES))
        self.assertEqual(
            self.db.indicators.count_documents({"reported": True}),
            len(decide.INDICATOR_ROWS),
        )
        self.assertEqual(
            self.db.indicators.count_documents({"reported": False}),
            len(decide.INDICATOR_SKIP),
        )

    def test_decisions_are_stored_as_the_readout_emits_them(self) -> None:
        """Same shape as `decide.build_report()`, so the two cannot disagree."""
        if self.db.decisions.count_documents({}) == 0:
            self.skipTest("decisions load from gitignored data/; CI loads only the tracked collections")
        doc = self.db.decisions.find_one({"interval": "1d"})
        self.assertIsNotNone(doc)
        for key in ("asset", "interval", "bars", "decision_bar", "execution", "disclaimer"):
            self.assertIn(key, doc)
        self.assertIn("stale", doc["decision_bar"])
        from backtester.core.strategies import REGISTRY

        self.assertEqual(len(doc["strategies"]), len(REGISTRY))

    def test_no_non_finite_numbers_reached_the_store(self) -> None:
        """NaN in, None out -- checked on the collection most likely to carry it."""
        for doc in self.db.experiment_rows.find({"section": "summary"}).limit(50):
            for key, value in doc.items():
                if isinstance(value, float):
                    self.assertTrue(math.isfinite(value), f"{doc['_id']}.{key}")

    def test_pbo_by_horizon_is_queryable(self) -> None:
        """The query the list-sidecar split exists to make possible."""
        if self.db.experiment_rows.count_documents({}) == 0:
            self.skipTest("experiment_rows load from gitignored results/; CI loads only the tracked collections")
        rows = list(
            self.db.experiment_rows.aggregate(
                [
                    {"$match": {"section": "summary", "pbo": {"$ne": None}}},
                    {"$group": {"_id": "$horizon", "n": {"$sum": 1}}},
                ]
            )
        )
        self.assertTrue(rows, "no summary rows carry a pbo")

    def test_test_results_are_from_real_runs(self) -> None:
        """`ok` is observed, never assumed; a count with a guessed outcome is not data."""
        for doc in self.db.test_results.find():
            with self.subTest(suite=doc["suite"]):
                self.assertIsInstance(doc["ok"], bool)
                self.assertGreater(doc["count"], 0)
                self.assertEqual(doc["source_sha256"], "live-run-not-a-file")


@needs_server
class TestIdempotency(unittest.TestCase):
    """Loading twice must not double anything.

    Run on a subset so the test costs seconds rather than the four minutes a full
    double load takes; the mechanism under test -- drop then insert -- is the same
    for every collection.
    """

    SUBSET = "strategies,signals,indicators"

    def test_two_loads_leave_identical_counts(self) -> None:
        """The check that the module docstring's claim rests on."""
        client = schema.connect()
        self.addCleanup(client.close)
        db = client[schema.DB_NAME]
        names = self.SUBSET.split(",")

        self.assertEqual(load.main(["--only", self.SUBSET]), 0)
        first = {name: db[name].count_documents({}) for name in names}

        self.assertEqual(load.main(["--only", self.SUBSET]), 0)
        second = {name: db[name].count_documents({}) for name in names}

        self.assertEqual(first, second)
        self.assertTrue(all(count > 0 for count in first.values()), first)

    def test_a_subset_load_leaves_other_collections_alone(self) -> None:
        """`--only` must not wipe the rest of the store."""
        client = schema.connect()
        self.addCleanup(client.close)
        db = client[schema.DB_NAME]
        before = db.bars.count_documents({})
        if before == 0:
            self.skipTest("bars not loaded; run a full load first")
        self.assertEqual(load.main(["--only", "signals"]), 0)
        self.assertEqual(db.bars.count_documents({}), before)


if __name__ == "__main__":
    unittest.main()
