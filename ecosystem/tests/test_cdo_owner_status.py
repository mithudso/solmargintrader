"""Unavailable owner status must not be presented as a verified stop."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ecosystem.control import ControlPlane


class OwnerStatusTests(unittest.TestCase):
    def test_owner_failures_are_unknown_and_healthy_stopped_is_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            plane = object.__new__(ControlPlane)
            plane.experiment_home = lambda _run: Path(directory)
            plane.pipeline_status = lambda _run: {'supervisor_running': False, 'phase': 'not_initialized'}
            plane.experiments = list
            plane.actions = lambda: {'actions': []}
            plane._manager = lambda *_args: (_ for _ in ()).throw(OSError('fixture'))
            with (patch('ecosystem.control.runtime_settings', return_value={'revision': 1, 'oracle_enabled': False}),
                  patch('ecosystem.control.recorder_recovery_enabled', return_value=False),
                  patch('ecosystem.performance.recording', return_value={}),
                  patch('ecosystem.data.universe', return_value=[]),
                  patch('soltui.pricefeed.status', side_effect=OSError('fixture'))):
                servers = {row['id']: row for row in plane.snapshot()['servers']}
            for name in ('recorder', 'manager'):
                self.assertEqual(servers[name]['state'], 'unavailable')
                self.assertIsNone(servers[name]['running'])
            plane._manager = lambda *_args: {}
            with (patch('ecosystem.control.runtime_settings', return_value={'revision': 1, 'oracle_enabled': False}),
                  patch('ecosystem.control.recorder_recovery_enabled', return_value=False),
                  patch('ecosystem.performance.recording', return_value={}),
                  patch('ecosystem.data.universe', return_value=[]),
                  patch('soltui.pricefeed.status', return_value={'running': False})):
                servers = {row['id']: row for row in plane.snapshot()['servers']}
            self.assertEqual(servers['manager']['state'], 'unavailable')
            self.assertIsNone(servers['manager']['running'])
            plane._manager = lambda operation, _params: {'supervisor_lock_held': False} if operation == 'service' else {}
            with (patch('ecosystem.control.runtime_settings', return_value={'revision': 1, 'oracle_enabled': False}),
                  patch('ecosystem.control.recorder_recovery_enabled', return_value=False),
                  patch('ecosystem.performance.recording', return_value={}),
                  patch('ecosystem.data.universe', return_value=[]),
                  patch('soltui.pricefeed.status', return_value={'running': False})):
                servers = {row['id']: row for row in plane.snapshot()['servers']}
            for name in ('recorder', 'manager'):
                self.assertEqual(servers[name]['state'], 'stopped')
                self.assertIs(servers[name]['running'], False)
