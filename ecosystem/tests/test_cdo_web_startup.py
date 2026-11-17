"""A failed control-room startup must release its already-started worker."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ecosystem.web import make_server


class StartupCleanupTests(unittest.TestCase):
    def test_failed_legacy_registration_closes_control_plane(self):
        class Plane:
            instance = None

            def __init__(self, home, manager_home):
                self.closed = False
                Plane.instance = self

            def register_legacy(self):
                raise OSError('registration unavailable')

            def close(self):
                self.closed = True

        with tempfile.TemporaryDirectory() as directory, patch('ecosystem.control.ControlPlane', Plane):
            with self.assertRaisesRegex(OSError, 'registration unavailable'):
                make_server(Path(directory), port=0)
            self.assertTrue(Plane.instance.closed)


if __name__ == '__main__':
    unittest.main()
