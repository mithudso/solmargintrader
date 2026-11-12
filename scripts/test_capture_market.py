"""Durability, namespace and ambiguous-write regressions; no live network or DB."""
import importlib.util
import io
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

SPEC = importlib.util.spec_from_file_location("capture_market", Path(__file__).with_name("capture_market.py"))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "run"
        self.cfg = m.prepare(self.home, "ZEC-USD", 86400, self.root / "env", self.root / "client.pem")

    def spool(self, raw='{"type":"match","time":"2026-11-12T00:00:00.123456Z","price":"23.123456789","trade_id":1}'):
        s = m.Spool(self.home, self.cfg)
        try:
            return s.append(raw, "connection-a")
        finally:
            s.close()

    def test_upload_missing_dependency_names_its_isolated_setup_command(self):
        for missing, package in (("pymongo", "pymongo"), ("dotenv", "python-dotenv")):
            stderr = io.StringIO()
            with self.subTest(missing=missing), redirect_stderr(stderr), patch(
                "importlib.util.find_spec", side_effect=lambda name: None if name == missing else object()
            ), patch.object(m, "upload", return_value=0) as upload:
                self.assertEqual(m.main(["upload", "--home", str(self.home)]), 3)
                upload.assert_not_called()
                result = json.loads(stderr.getvalue())
                self.assertEqual(result["missing_package"], package)
                self.assertIn("uv run --with-requirements", result["setup_command"])
                self.assertIn(str(m.ROOT / "scripts/requirements-market-capture.txt"), result["setup_command"])
                self.assertIn("--help", result["setup_command"])

    def test_deadline_is_persisted_and_prepare_refuses_overwrite(self):
        self.assertEqual(self.cfg["deadline_epoch"] - self.cfg["start_epoch"], 86400)
        with self.assertRaises(FileExistsError):
            m.prepare(self.home, "ZEC-USD", 10, self.root / "env", self.root / "client.pem")
        self.assertEqual(m.config(self.home), self.cfg)

    def test_reject_nonfinite_and_nonpositive_duration(self):
        for i, value in enumerate([0, -1, math.inf, math.nan]):
            with self.subTest(value=value), self.assertRaises(m.CaptureError):
                m.prepare(self.root / str(i), "ZEC-USD", value, "env", "pem")

    def test_raw_message_precision_and_original_timestamp_are_preserved(self):
        row = self.spool()
        self.assertEqual(row["exchange_time_raw"], "2026-11-12T00:00:00.123456Z")
        doc = m.mongo_document(row, self.cfg)
        self.assertEqual(doc["payload"]["price"], "23.123456789")
        self.assertEqual(doc["received_ns"], row["received_ns"])
        self.assertEqual(doc["meta"]["product"], "ZEC-USD")

    def test_invalid_message_type_retains_raw_without_interrupting_spool(self):
        for value in ([], {}, 4, None, True, ""):
            with self.subTest(value=value):
                raw = json.dumps({"type": value, "price": "23.1"})
                row = self.spool(raw)
                self.assertEqual(row["type"], "unparsed")
                self.assertEqual(row["raw"], raw)
                m.atomic_json(self.home / "status.json", {"types": {row["type"]: 1}})
        rows, _ = m.read_batch(self.home / "events.jsonl", 0)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["seq"] for r in rows], list(range(1, 7)))

    def test_unparsed_payload_is_retained(self):
        row = self.spool('not JSON 🚀')
        self.assertEqual(m.mongo_document(row, self.cfg)["raw_unparsed"], 'not JSON 🚀')

    def test_repair_only_incomplete_tail_and_continue_sequence(self):
        row = self.spool()
        path = self.home / "events.jsonl"
        before = path.read_bytes()
        with path.open("ab") as f:
            f.write(b'{"partial":')
        s = m.Spool(self.home, self.cfg)
        self.assertEqual(path.read_bytes(), before)
        self.assertGreater(s.repaired_bytes, 0)
        self.assertEqual(s.append('{}', 'b')["seq"], row["seq"] + 1)
        s.close()

    def test_reader_does_not_checkpoint_incomplete_line(self):
        self.spool()
        path = self.home / "events.jsonl"
        size = path.stat().st_size
        with path.open("ab") as f:
            f.write(b'{"unfinished"')
        rows, offset = m.read_batch(path, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(offset, size)

    def test_wrong_run_refused(self):
        row = self.spool()
        row["run_id"] = "another"
        with self.assertRaises(m.CaptureError):
            m.mongo_document(row, self.cfg)

    def test_loader_database_and_arbitrary_namespace_refused(self):
        cfg = dict(self.cfg, database="solmargintrader")
        m.atomic_json(self.home / "config.json", cfg)
        with self.assertRaises(m.CaptureError):
            m.config(self.home)

    def test_existing_client_ca_and_other_parameters_are_preserved(self):
        ca = self.root / "ca.pem"
        ca.write_text("fixture")
        uri = m.normalise_uri(f'mongodb://localhost/?tlsCAFile={ca}&appName=research&tlsCertificateKeyFile=/stale.pem')
        query = parse_qs(urlsplit(uri).query)
        self.assertEqual(query["tlsCAFile"], [str(ca)])
        self.assertEqual(query["appName"], ["research"])
        self.assertNotIn("tlsCertificateKeyFile", query)

    def test_missing_ca_uses_system_trust_and_insecure_options_refused(self):
        self.assertNotIn("tlsCAFile", m.normalise_uri('mongodb://localhost/?tlsCAFile=/missing/capture-ca.pem'))
        for key in ['tlsInsecure', 'tlsAllowInvalidCertificates', 'tlsAllowInvalidHostnames']:
            with self.subTest(key=key), self.assertRaises(m.CaptureError):
                m.normalise_uri(f'mongodb://localhost/?{key}=true')

    def test_unused_uri_database_does_not_override_dedicated_namespace(self):
        uri = m.normalise_uri('mongodb://localhost/invalid%20default?authSource=%24external&tls=true')
        self.assertEqual(urlsplit(uri).path, '/')
        self.assertEqual(parse_qs(urlsplit(uri).query)['authSource'], ['$external'])
        self.assertEqual(self.cfg['database'], 'market_capture')

    def test_second_role_owner_refused(self):
        with m.lock(self.home / 'test.lock'), self.assertRaises(m.CaptureError), m.lock(self.home / 'test.lock'):
            self.fail('second owner acquired the lock')

    def test_ambiguous_insert_keeps_raw_and_blocks_automatic_retry(self):
        self.spool()
        target = type('Target', (), {'insert_many': lambda *a, **k: (_ for _ in ()).throw(TimeoutError())})()
        client = type('Client', (), {'close': lambda self: None})()
        with patch.object(m, 'collection', return_value=target), self.assertRaises(TimeoutError):
            m.upload_once(self.home, lambda _: client)
        pending = m.read_json(self.home / 'upload-progress.json')
        self.assertTrue(pending['inflight'])
        with self.assertRaises(m.CaptureError):
            m.upload_once(self.home, lambda _: self.fail('retried ambiguous insert'))
        self.assertEqual(len(m.read_batch(self.home / 'events.jsonl', 0)[0]), 1)

    def test_failure_before_insert_leaves_no_ambiguous_marker(self):
        self.spool()
        def offline(_):
            raise ConnectionError()
        with self.assertRaises(ConnectionError):
            m.upload_once(self.home, offline)
        self.assertFalse((self.home / 'upload-progress.json').exists())

    def test_successful_upload_advances_once(self):
        self.spool()
        calls = []
        target = type('Target', (), {'insert_many': lambda self, docs, **kw: calls.append(docs)})()
        client = type('Client', (), {'close': lambda self: None})()
        with patch.object(m, 'collection', return_value=target):
            progress, changed = m.upload_once(self.home, lambda _: client)
            again, changed_again = m.upload_once(self.home, lambda _: client)
        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(progress['records'], 1)
        self.assertEqual(again, progress)
        self.assertEqual(len(calls), 1)

    def test_expired_capture_does_not_connect_or_extend_deadline(self):
        cfg = dict(self.cfg, deadline_epoch=0)
        m.atomic_json(self.home / 'config.json', cfg)
        self.assertEqual(m.capture(self.home, ws_factory=lambda: self.fail('connected past deadline')), 0)
        self.assertEqual(m.read_json(self.home / 'capture-status.json')['state'], 'completed')
        self.assertEqual(m.config(self.home)['deadline_epoch'], 0)

    def test_all_received_messages_and_trade_jump_survive_without_database(self):
        outer = self
        ack = json.dumps({'type': 'subscriptions', 'channels': [
            {'name': 'level2_50' if c == 'level2_batch' else c,
             'product_ids': ['ZEC-USD']} for c in m.CHANNELS]})
        messages = [ack, '{"type":"snapshot","bids":[],"asks":[]}',
                    '{"type":"match","trade_id":1}', '{"type":"match","trade_id":3}']
        class Feed:
            def open(self):
                pass
            def settimeout(self, _):
                pass
            def send_text(self, raw):
                outer.assertEqual(json.loads(raw)['product_ids'], ['ZEC-USD'])
            def recv_text(self):
                raw = messages.pop(0)
                if not messages:
                    (outer.home / 'stop-requested').touch()
                return raw
            def close(self):
                pass
        self.assertEqual(m.capture(self.home, ws_factory=Feed), 0)
        rows, _ = m.read_batch(self.home / 'events.jsonl', 0)
        self.assertEqual([r['seq'] for r in rows], list(range(1, len(rows) + 1)))
        self.assertEqual(sum(r['type'] == 'match' for r in rows), 2)
        self.assertEqual(sum(r['type'] == 'trade_gap_candidate' for r in rows), 1)
        self.assertEqual(m.read_json(self.home / 'capture-status.json')['state'], 'stopped_early')


class NativeMongoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from pymongo import MongoClient
            cls.client_factory = staticmethod(lambda: MongoClient(
                'mongodb://127.0.0.1:27017', serverSelectionTimeoutMS=1500, tz_aware=True))
            client = cls.client_factory()
            try:
                client.admin.command('ping')
            finally:
                client.close()
        except Exception as error:
            if os.environ.get('MARKET_CAPTURE_REQUIRE_MONGO') == '1':
                raise
            raise unittest.SkipTest('local MongoDB fixture unavailable') from error

    def test_real_time_series_insert_checkpoint_and_readback(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / 'run'
            cfg = m.prepare(home, 'ZEC-USD', 5, 'fixture.env', 'fixture.pem')
            spool = m.Spool(home, cfg)
            spool.append('{"type":"match","price":"23.123456789","trade_id":100}', 'a')
            spool.append('{"type":"l2update","changes":[["buy","23.1","2"]]}', 'a')
            spool.close()
            reader = self.client_factory()
            target = reader[cfg['database']][cfg['collection']]
            try:
                progress, changed = m.upload_once(home, lambda _: self.client_factory())
                self.assertTrue(changed)
                self.assertEqual(progress['records'], 2)
                self.assertEqual(target.options()['timeseries']['timeField'], 'received_at')
                rows = list(target.find().sort('seq', 1))
                self.assertEqual([r['seq'] for r in rows], [1, 2])
                self.assertEqual(rows[0]['payload']['price'], '23.123456789')
                self.assertEqual(rows[1]['meta']['product'], 'ZEC-USD')
                self.assertIsInstance(rows[0]['received_ns'], int)
                self.assertFalse(m.upload_once(home, lambda _: self.client_factory())[1])
                self.assertEqual(target.count_documents({}), 2)
            finally:
                # Only this fixture's unique collection is owned by the test.
                target.drop()
                reader.close()


if __name__ == '__main__':
    unittest.main()
