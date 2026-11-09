"""The new native host owns its protocol registration for its serve lifetime."""
from __future__ import annotations

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from soltui import config, native_host, prediction_recovery as recovery


class NativeHostRegistration(unittest.TestCase):
    def run_main(self, *, failure=False):
        with TemporaryDirectory() as temporary, patch.object(config, "CONFIG_DIR", Path(temporary)), patch.object(
                recovery, "_process_identity", return_value="fixture-native-host"):
            handles = []
            register = recovery.register_console

            def capture():
                handle = register()
                handles.append(handle)
                return handle

            def serve(source, output):
                self.assertTrue(recovery._registered_console(recovery.os.getpid()))
                if failure:
                    raise RuntimeError("fixture serve failed")
                native_host_serve(source, output)

            native_host_serve = native_host.serve
            with patch.object(recovery, "register_console", side_effect=capture), patch.object(
                    native_host, "serve", side_effect=serve), patch.object(native_host.sys, "stdin", io.TextIOWrapper(io.BytesIO())), patch.object(
                    native_host.sys, "stdout", io.TextIOWrapper(io.BytesIO())), patch.object(native_host.sys, "stderr", io.StringIO()):
                if failure:
                    with self.assertRaisesRegex(RuntimeError, "fixture serve failed"):
                        native_host.main()
                else:
                    self.assertEqual(native_host.main(), 0)
            self.assertEqual(len(handles), 1)
            self.assertTrue(handles[0].closed)
            self.assertFalse(recovery._registered_console(recovery.os.getpid()))

    def test_registration_is_released_after_eof(self):
        self.run_main()

    def test_registration_is_released_after_serve_failure(self):
        self.run_main(failure=True)


if __name__ == "__main__":
    unittest.main()
