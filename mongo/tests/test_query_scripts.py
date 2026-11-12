"""Run mongosh examples against inert cursors; never connect to a database."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from mongo import load, schema


QUERY_DIR = Path(__file__).resolve().parents[1] / "queries"
REPO = QUERY_DIR.parents[1]
NODE = shutil.which("node")
MOCK_SHELL = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const records = JSON.parse(process.argv[2]);
const messages = []; const pipelines = [];
const cursor = () => ({
  sort() { return this; }, limit() { return this; },
  toArray() { return []; }, forEach() {},
});
const db = new Proxy({}, { get(_, name) {
  return {
    find: cursor,
    findOne() { return records[name] || null; },
    aggregate(pipeline) { pipelines.push({ name, pipeline }); return cursor(); },
    distinct() { return []; }, countDocuments() { return 0; }, getIndexes() { return []; },
  };
}});
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {
  db, print(...args) { messages.push(args.join(' ')); }, printjson() {},
}, { timeout: 1000 });

// MongoDB's comparator treats two NaN values as equal, unlike JS ===.
// https://github.com/mongodb/mongo/blob/master/src/mongo/base/compare_numbers.h#L35
const equal = (a, b) => a === b || (Number.isNaN(a) && Number.isNaN(b));
function predicate(expression, value) {
  if (expression === '$$field.v') return value;
  if (Array.isArray(expression)) return expression.map(item => predicate(item, value));
  if (!expression || typeof expression !== 'object') return expression;
  const [operator, argument] = Object.entries(expression)[0];
  const args = predicate(argument, value);
  if (operator === '$type') return typeof args === 'number' ? 'double' : typeof args;
  if (operator === '$and') return args.every(Boolean);
  if (operator === '$eq') return equal(...args);
  if (operator === '$ne') return !equal(...args);
  if (operator === '$in') return args[1].some(item => equal(item, args[0]));
  throw new Error('unsupported mock expression: ' + operator);
}
const health = pipelines.find(({ pipeline }) => pipeline.some(stage => stage.$count === 'nonFiniteRows'));
const specimens = [0, 2.5, NaN, Infinity, -Infinity, null, 'NaN', 'Infinity', {}, []];
const nonFinite = health ? specimens.map(value => predicate(
  health.pipeline[0].$match.$expr.$anyElementTrue.$map.in, value,
)) : [];
process.stdout.write(JSON.stringify({ messages, nonFinite }));
"""


@unittest.skipUnless(NODE, "Node.js is required for the inert mongosh script harness")
class QueryScriptRegressions(unittest.TestCase):
    def run_script(self, filename, records=None):
        result = subprocess.run(
            [NODE, "-e", MOCK_SHELL, str(QUERY_DIR / filename), json.dumps(records or {})],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_missing_example_records_do_not_abort_later_sections(self):
        examples = [
            ("02-strategies-and-cards.js", "No breakout strategy card", "every card's provenance"),
            ("04-decisions.js", "No SOL 1d readout", "indicators with no directional reading"),
            ("05-backtests.js", "No backtest run", "first and last few fills"),
        ]
        for filename, missing, final_section in examples:
            with self.subTest(filename=filename):
                output = "\n".join(self.run_script(filename)["messages"])
                self.assertIn(missing, output)
                self.assertIn(final_section, output)

    def test_present_example_records_keep_their_output(self):
        records = {
            "strategies": {"_id": "fixture_card", "name": "Fixture", "status": "measured",
                           "family": "test", "registry": {}, "presets": {}, "source_path": "fixture.md", "body": "fixture prose"},
            "decisions": {"decision_bar": {"utc": "fixture-time", "close": 10},
                          "execution": {"applies_to": "fixture-bar"}, "strategies": []},
            "backtest_runs": {"_id": "fixture_run", "manifest": {}, "results": []},
        }
        for filename, marker in [("02-strategies-and-cards.js", "fixture_card"),
                                 ("04-decisions.js", "fixture-time"),
                                 ("05-backtests.js", "per-strategy results")]:
            with self.subTest(filename=filename):
                self.assertIn(marker, "\n".join(self.run_script(filename, records)["messages"]))

    def test_health_predicate_detects_nan_and_both_infinities_only(self):
        observed = self.run_script("08-provenance-and-health.js")["nonFinite"]
        self.assertEqual(observed, [False, False, True, True, True, False, False, False, False, False])


class NativeFixtureIsolation(unittest.TestCase):
    def client(self):
        client = mock.MagicMock()
        def select(name):
            db = mock.MagicMock()
            db.name = name
            db.client = client
            db.strategies.count_documents.return_value = 1
            db.bars.count_documents.return_value = 1
            db.__getitem__.return_value.count_documents.return_value = 1
            return db
        client.__getitem__.side_effect = select
        return client

    def assert_owned_namespace(self, client):
        names = [call.args[0] for call in client.__getitem__.call_args_list]
        self.assertTrue(names)
        for name in names:
            self.assertRegex(name, rf"^{schema.DB_NAME}_test_[0-9a-f]{{32}}$")
        self.assertNotIn(schema.DB_NAME, names)
        self.assertEqual(len(set(names)), 1)
        client.drop_database.assert_called_once_with(names[0])
        client.close.assert_called_once()
        return names[0]

    def test_loaded_store_class_owns_only_its_generated_database(self):
        from mongo.tests.test_load import TestLoadedStore
        for setup_fails in [False, True]:
            client = self.client()
            with self.subTest(setup_fails=setup_fails), mock.patch.object(schema, "connect", return_value=client), \
                    mock.patch.object(schema, "create", side_effect=RuntimeError("fixture setup failed") if setup_fails else None), \
                    mock.patch.object(load, "build_all", return_value={}):
                try:
                    if setup_fails:
                        with self.assertRaisesRegex(RuntimeError, "fixture setup failed"):
                            TestLoadedStore.setUpClass()
                    else:
                        TestLoadedStore.setUpClass()
                finally:
                    TestLoadedStore.doClassCleanups()
                self.assert_owned_namespace(client)

    def test_cleanup_closes_client_even_if_owned_database_deletion_fails(self):
        from mongo.tests.test_load import isolated_store
        client = self.client()
        client.drop_database.side_effect = RuntimeError("fixture cleanup failed")
        with mock.patch.object(schema, "connect", return_value=client), self.assertRaisesRegex(RuntimeError, "fixture cleanup failed"):
            with isolated_store():
                pass
        self.assert_owned_namespace(client)

    def test_idempotency_loaders_receive_only_the_owned_database(self):
        from mongo.tests.test_load import TestIdempotency
        for method in ["test_two_loads_leave_identical_counts", "test_a_subset_load_leaves_other_collections_alone"]:
            client = self.client(); namespaces = []
            def load_main(argv):
                namespaces.append(load.DB_NAME)
                self.assertIs(load.connect(), client)
                return 0
            case = TestIdempotency(method)
            with self.subTest(method=method), mock.patch.object(schema, "connect", return_value=client), \
                    mock.patch.object(load, "connect"), \
                    mock.patch.object(load, "main", side_effect=load_main):
                try:
                    getattr(case, method)()
                finally:
                    case.doCleanups()
                name = self.assert_owned_namespace(client)
                self.assertTrue(namespaces)
                self.assertEqual(set(namespaces), {name})


class LoaderInterpreterRegression(unittest.TestCase):
    def test_python_suite_receipts_use_the_running_environment(self):
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, "", "Ran 2 tests in 0.01s\nOK\n")
        with mock.patch.object(load, "git_sha", return_value="fixture"), \
                mock.patch.object(load.subprocess, "run", side_effect=run):
            receipts = load.load_test_results(run_suites=True, skip={"extension"})
        self.assertEqual(len(receipts), 2)
        self.assertTrue(all(row["ok"] and row["count"] == 2 for row in receipts))
        self.assertEqual([command[0] for command in commands], [sys.executable, sys.executable])


class CLIPrerequisiteRegressions(unittest.TestCase):
    def invoke(self, script, arguments, missing="pymongo"):
        bootstrap = """
import builtins, runpy, sys, types
script, missing = sys.argv[1:3]
sys.argv = [script, *sys.argv[3:]]
original_import = builtins.__import__
def refused(name, *args, **kwargs):
    if name.split('.')[0] == 'pymongo':
        if missing == 'server':
            error_type = type('ServerSelectionTimeoutError', (Exception,), {'__module__': 'pymongo.errors'})
            class UnavailableClient:
                def __getitem__(self, name):
                    raise error_type('private-server-error-canary')
            return types.SimpleNamespace(MongoClient=lambda *a, **kw: UnavailableClient())
        raise ModuleNotFoundError('Refused prerequisite import', name=missing)
    return original_import(name, *args, **kwargs)
builtins.__import__ = refused
runpy.run_path(script, run_name='__main__')
"""
        return subprocess.run([sys.executable, "-c", bootstrap, str(REPO / "mongo" / script), missing, *arguments],
                              cwd=REPO, capture_output=True, text=True, timeout=10)

    def test_missing_prerequisites_name_an_isolated_fix_without_tracebacks(self):
        for script, arguments in [("load.py", ["--only", "test_results"]), ("schema.py", ["--create"])]:
            for module, package in [("pymongo", "pymongo"), ("dotenv", "python-dotenv")]:
                with self.subTest(script=script, module=module):
                    result = self.invoke(script, arguments, module)
                    self.assertEqual(result.returncode, 3, result.stderr)
                    self.assertIn(package, result.stderr)
                    self.assertIn("uv pip install --python", result.stderr)
                    self.assertIn(str(REPO / ".venv" / "bin" / "python"), result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_help_bad_arguments_and_describe_work_without_driver_imports(self):
        for script in ["load.py", "schema.py"]:
            with self.subTest(script=script):
                help_result = self.invoke(script, ["--help"])
                self.assertEqual(help_result.returncode, 0, help_result.stderr)
                self.assertIn("Example:", help_result.stdout)
                self.assertIn(".venv/bin/python", help_result.stdout)
                bad = self.invoke(script, ["--unknown-argument"])
                self.assertEqual(bad.returncode, 2)
                self.assertIn("usage:", bad.stderr)
                self.assertNotIn("Traceback", bad.stderr)
        describe = self.invoke("schema.py", ["--describe"])
        self.assertEqual(describe.returncode, 0, describe.stderr)
        self.assertIn("database: solmargintrader", describe.stdout)

    def test_library_imports_still_work_without_site_packages(self):
        result = subprocess.run([sys.executable, "-S", "-c", "import mongo.load, mongo.schema"],
                                cwd=REPO, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unavailable_server_has_a_redacted_cli_message(self):
        for script, arguments in [("load.py", ["--only", "test_results"]), ("schema.py", ["--create"])]:
            with self.subTest(script=script):
                result = self.invoke(script, arguments, "server")
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertIn("MongoDB server is unavailable", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("private-server-error-canary", result.stderr)
