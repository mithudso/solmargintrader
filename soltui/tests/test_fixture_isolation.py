"""Disposable canaries for test fixture escape; no owner paths or process actions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from soltui import portfolio_agent
from soltui.tests import test_portfolio as portfolio_tests

class FixtureIsolationTests(unittest.TestCase):
    def test_suite_import_overrides_inherited_owner_state_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = Path(tmp) / 'synthetic-owner'
            owner.mkdir()
            canary = owner / 'config.yaml'
            canary.write_text('synthetic owner canary\n')
            env = {**os.environ, 'SOLTUI_CONFIG_DIR': str(owner),
                   'SOLTUI_LOG_DIR': str(owner), 'SOLTUI_SUPPORT_DIR': str(owner),
                   'HOME': str(owner), 'SOLTUI_RESEARCH_AUTHORITY': str(owner),
                   'SOLTUI_RESEARCH_REGISTRY': str(owner / 'authority.json'),
                   'INDEX_NO_AUTO': '1'}
            code = "import json; import soltui.tests; from soltui import config; config.save_settings(config.Settings()); print(json.dumps({'path': str(config.CONFIG_PATH), 'home': __import__('os').environ['HOME'], 'authority': __import__('os').environ.get('SOLTUI_RESEARCH_AUTHORITY'), 'registry': __import__('os').environ.get('SOLTUI_RESEARCH_REGISTRY')}))"
            result = subprocess.run([sys.executable, '-c', code], env=env,
                                    capture_output=True, text=True, check=True)
            evidence = json.loads(result.stdout)
            self.assertNotEqual(Path(evidence['path']).parent, owner)
            self.assertNotEqual(Path(evidence['home']), owner)
            self.assertIsNone(evidence['authority'])
            self.assertNotEqual(evidence['registry'], str(owner / 'authority.json'))
            self.assertEqual(canary.read_text(), 'synthetic owner canary\n')

    def test_portfolio_agent_fixture_never_escapes_to_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            portfolio_agent, 'log_path', return_value=Path(tmp) / 'logs' / 'portfolio.log'
        ), mock.patch.object(portfolio_agent.subprocess, 'run',
                             side_effect=AssertionError('process boundary escaped')) as run:
            result = unittest.TestResult()
            portfolio_tests.AgentTests('test_install_writes_the_plist_without_starting_it').run(result)
            self.assertEqual(result.errors, [])
            self.assertEqual(result.failures, [])
            run.assert_not_called()
