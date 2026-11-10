from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from botmanager.domain import ManagerError
from botmanager.oracle_data import advance, capture, prepare_descriptor

START = 1700000040


def archive(path, seconds=120):
    from oracle.engine import OracleEngine

    owner = OracleEngine(path, instrument="SOL/USD")
    append(owner, 0, seconds)
    return owner


def append(owner, start, end):
    for second in range(start, end):
        t = START + second
        owner.ingest(
            {
                "event_id": f"obs-{second}",
                "source": "coinbase_recorder",
                "venue": "coinbase_exchange",
                "instrument": "SOL/USD",
                "kind": "stream_snapshot_mid",
                "observed_at": t,
                "received_at": t,
                "price": 100 + second % 10,
                "timestamp_semantics": "recorder_quote_clock",
            },
            now=t,
        )


class ArchiveTests(unittest.TestCase):
    def test_graph_archive_schema_v2_keeps_observation_pages_readable(self):
        from botmanager.oracle_data import read_page

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            archive(p, 120)
            page = read_page(p, now=START + 120)

            self.assertEqual(page["policy"]["schema_version"], 2)
            self.assertEqual(len(page["observations"]), 120)

    def test_absent_archive_read_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "absent" / "history.sqlite3"
            with self.assertRaises(ManagerError):
                prepare_descriptor(p, capital_quote=1000, strategy_id="grid", now=START)
            self.assertFalse(p.parent.exists())

    def test_activation_completed_bins_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            d = prepare_descriptor(
                p, capital_quote=1000, strategy_id="grid", now=START + 120
            )
            data = capture(d, now=START + 120)
            self.assertEqual(data["bars"], [])
            append(owner, 120, 241)
            data = advance(data, now=START + 241)
            self.assertEqual(
                [b["ts"] for b in data["bars"]], [START + 120, START + 180]
            )
            self.assertFalse(any("volume" in b for b in data["bars"]))
            self.assertEqual(advance(data, now=START + 241)["bars"], data["bars"])
            self.assertTrue(
                all(
                    o["observation"]["observed_at"] >= d["activation_at"]
                    for o in data["prospective"]["observations"]
                )
            )

    def test_stale_input_holds_without_consuming_or_duplicating(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            data = capture(
                prepare_descriptor(
                    p, capital_quote=1000, strategy_id="grid", now=START + 120
                ),
                now=START + 120,
            )
            append(owner, 120, 181)
            held = advance(data, now=START + 300)
            self.assertEqual(held["prospective"]["health"], "source_stale")
            self.assertEqual(held["bars"], [])
            self.assertEqual(
                held["prospective"]["cursor"], data["prospective"]["cursor"]
            )

    def test_closed_capture_refuses_missing_edges_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            archive(p, 121)
            d = prepare_descriptor(
                p,
                capital_quote=1000,
                strategy_id="grid",
                now=START + 121,
                mode="historical",
                start_ts=START,
                end_ts=START + 120,
            )
            data = capture(d, now=START + 121)
            self.assertEqual(len(data["bars"]), 2)
            self.assertEqual(len(data["observations"]), 120)
            with self.assertRaises(ManagerError):
                capture({**d, "quote_currency": "USDC"}, now=START + 121)


class ProspectiveWorkerTests(unittest.TestCase):
    def test_atomic_crash_restart_two_accounts_and_stopped_generation(self):
        from uuid import uuid4

        from botmanager.ledger import RuntimeLedger
        from botmanager.worker import prospective_tick

        from tests.test_paper import grid

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "history.sqlite3"
            owner = archive(p, 120)
            data = capture(
                prepare_descriptor(
                    p, capital_quote=1000, strategy_id="grid", now=START + 120
                ),
                now=START + 120,
            )
            ledger = RuntimeLedger(root / "manager")
            a, b = grid("a"), grid("b")
            generations = {}
            for spec in (a, b):
                ledger.register(spec, data)
                ledger.control(spec, "start", str(uuid4()))
                generations[spec.bot_id] = ledger.claim(spec.bot_id, "owner")
            append(owner, 120, 241)
            row = ledger.get(a.bot_id)

            def crash():
                raise RuntimeError("injected crash before commit")

            with self.assertRaises(RuntimeError):
                prospective_tick(
                    ledger,
                    row,
                    generations[a.bot_id],
                    now=START + 241,
                    before_commit=crash,
                )
            self.assertEqual(ledger.get(a.bot_id)["input"], data)
            self.assertIsNotNone(ledger.get(a.bot_id)["tick_started"])
            ledger.recover("crash-restart")
            for spec in (a, b):
                generations[spec.bot_id] = ledger.claim(spec.bot_id, "crash-restart")
            for spec in (a, b):
                prospective_tick(
                    ledger,
                    ledger.get(spec.bot_id),
                    generations[spec.bot_id],
                    now=START + 241,
                )
            self.assertEqual(ledger.fills(a.bot_id), ledger.fills(b.bot_id))
            self.assertIsNone(ledger.get(a.bot_id)["tick_started"])
            self.assertIsNone(ledger.get(b.bot_id)["tick_started"])
            before = ledger.fills(a.bot_id)
            ledger.recover("restart")
            gen = ledger.claim(a.bot_id, "restart")
            prospective_tick(ledger, ledger.get(a.bot_id), gen, now=START + 241)
            self.assertEqual(ledger.fills(a.bot_id), before)
            self.assertIsNone(ledger.get(a.bot_id)["tick_started"])
            ledger.control(a, "stop", str(uuid4()))
            with self.assertRaises(ManagerError):
                prospective_tick(ledger, ledger.get(a.bot_id), gen, now=START + 241)
            self.assertEqual(ledger.get(a.bot_id)["desired"], "stopped")

    def test_prospective_no_data_poll_marks_intent_and_clears_atomically(self):
        from unittest.mock import patch
        from uuid import uuid4

        from botmanager.ledger import RuntimeLedger
        from botmanager.worker import prospective_tick

        from tests.test_paper import grid

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "oracle.sqlite3"
            archive(path, 120)
            data = capture(
                prepare_descriptor(
                    path, capital_quote=1000, strategy_id="grid", now=START + 120
                ),
                now=START + 120,
            )
            ledger = RuntimeLedger(root / "manager")
            spec = grid()
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            generation = ledger.claim(spec.bot_id, "owner")

            def observe_marker(current, **kwargs):
                self.assertIsNotNone(ledger.get(spec.bot_id)["tick_started"])
                return advance(current, **kwargs)

            with patch(
                "botmanager.oracle_data.advance", side_effect=observe_marker
            ) as reader:
                prospective_tick(
                    ledger, ledger.get(spec.bot_id), generation, now=START + 120
                )
                reader.assert_called_once()
            row = ledger.get(spec.bot_id)
            self.assertIsNone(row["tick_started"])
            self.assertIsNone(row["checkpoint"])
            self.assertEqual(row["cursor"], 0)
            self.assertEqual(row["reason"], "waiting_for_completed_bin")
            ledger.control(spec, "stop", str(uuid4()))
            with patch("botmanager.oracle_data.advance") as reader:
                with self.assertRaises(ManagerError):
                    prospective_tick(ledger, row, generation, now=START + 120)
                reader.assert_not_called()


class ArchiveAdversarialTests(unittest.TestCase):
    def test_out_of_order_raw_event_never_becomes_accepted_input(self):
        from botmanager.oracle_data import read_page

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            owner.ingest(
                {
                    "event_id": "late-raw",
                    "source": "coinbase_recorder",
                    "venue": "coinbase_exchange",
                    "instrument": "SOL/USD",
                    "kind": "stream_snapshot_mid",
                    "observed_at": START + 30,
                    "received_at": START + 120,
                    "price": 999,
                },
                now=START + 120,
            )
            page = read_page(p, now=START + 120)
            self.assertEqual(len(page["observations"]), 120)
            self.assertFalse(
                any(o["observation"]["price"] == 999 for o in page["observations"])
            )
            self.assertGreater(
                page["high_watermark"], page["observations"][-1]["sequence"]
            )

    def test_archive_schema_policy_future_and_gaps_refuse(self):
        import sqlite3

        from botmanager.oracle_data import read_page

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            d = prepare_descriptor(
                p, capital_quote=1000, strategy_id="grid", now=START + 120
            )
            with self.assertRaises(ManagerError):
                read_page(p, now=START + 10)
            data = capture(d, now=START + 120)
            append(owner, 130, 241)
            data = advance(data, now=START + 241)
            self.assertEqual(data["prospective"]["health"], "source_gap")
            self.assertEqual(data["bars"], [])
            with sqlite3.connect(p) as db:
                db.execute("PRAGMA user_version=99")
            with self.assertRaises(ManagerError):
                read_page(p, now=START + 241)

    def test_resource_bound_holds_preserving_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            d = prepare_descriptor(
                p, capital_quote=1000, strategy_id="grid", now=START + 120
            )
            d["max_bars"] = 1
            data = capture(d, now=START + 120)
            append(owner, 120, 241)
            data = advance(data, now=START + 241)
            self.assertEqual(len(data["bars"]), 1)
            self.assertEqual(data["prospective"]["health"], "resource_limit")
            held = advance(data, now=START + 242)
            self.assertEqual(held["bars"], data["bars"])
            self.assertEqual(
                held["prospective"]["cursor"], data["prospective"]["cursor"]
            )

    def test_prepare_and_check_commands_preserve_consent(self):
        from unittest.mock import patch

        from botmanager.registry import CommandContext, dispatch
        from botmanager.store import ManagerStore

        from tests.test_paper import grid

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "history.sqlite3"
            archive(p, 120)
            context = CommandContext(home=root / "manager")
            spec = grid()
            ManagerStore(context.home).create_spec(spec)
            args = {
                "identity": spec.bot_id,
                "archive": str(p),
                "output": str(root / "descriptor.json"),
            }
            self.assertFalse(dispatch("prepare-input", args, context)["ok"])
            with patch("time.time", return_value=START + 120):
                result = dispatch("prepare-input", {**args, "reference": True}, context)
                self.assertTrue(result["ok"], result)
                self.assertFalse(
                    dispatch("prepare-input", {**args, "reference": True}, context)[
                        "ok"
                    ]
                )
                checked = dispatch(
                    "data-check",
                    {"identity": spec.bot_id, "descriptor": args["output"]},
                    context,
                )
                self.assertEqual(checked["data"]["state"], "reference_only")
                self.assertTrue(
                    dispatch(
                        "register-input",
                        {"identity": spec.bot_id, "descriptor": args["output"]},
                        context,
                    )["ok"]
                )
            self.assertFalse((context.home / "supervisor.lock").exists())

    def test_page_snapshot_keeps_watermark_coherent_during_append(self):
        import sqlite3
        from unittest.mock import patch

        from botmanager.oracle_data import read_page

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            owner = archive(p, 120)
            with sqlite3.connect(p) as db:
                db.execute("PRAGMA journal_mode=WAL")
            connect = sqlite3.connect
            inserted = []

            def reader(*args, **kwargs):
                db = connect(*args, **kwargs)
                if kwargs.get("uri"):

                    def trace(sql):
                        if "coalesce(max(sequence)" in sql and not inserted:
                            inserted.append(True)
                            append(owner, 120, 121)

                    db.set_trace_callback(trace)
                return db

            with patch("botmanager.oracle_data.sqlite3.connect", side_effect=reader):
                first = read_page(p, now=START + 121)
            second = read_page(p, now=START + 121)
            self.assertEqual(len(first["observations"]), 120)
            self.assertEqual(len(second["observations"]), 121)
            self.assertLess(first["high_watermark"], second["high_watermark"])
