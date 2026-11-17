"""A stop cannot acknowledge the previous identity during worker startup."""
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from soltui import f5_batch


class BatchStopRaceTests(unittest.TestCase):
    def test_stop_waits_for_start_token_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'batch.sqlite3').touch()
            (directory / 'worker-token').write_text('a' * 32)
            paused, release, finish, stop_started, reaped = (threading.Event() for _ in range(5))
            actual_write = Path.write_text
            inherited = []
            def delayed_write(path, *args, **kwargs):
                if path.name == 'worker-token':
                    paused.set()
                    if not release.wait(2):
                        raise RuntimeError('fixture timeout')
                return actual_write(path, *args, **kwargs)
            class Process:
                pid = 12345
                def __init__(self, *args, **kwargs):
                    inherited.extend(os.dup(fd) for fd in kwargs['pass_fds'])
                def wait(self):
                    finish.wait(2)
                    for fd in inherited:
                        os.close(fd)
                    reaped.set()
            result = {}
            with (patch.object(f5_batch, '_directory', return_value=directory),
                  patch.object(f5_batch, '_root', return_value=directory),
                  patch.object(f5_batch, '_SOURCE_EPOCH') as epoch,
                  patch.object(f5_batch.subprocess, 'Popen', Process),
                  patch.object(Path, 'write_text', delayed_write)):
                epoch.verify.return_value = None
                starter = threading.Thread(target=lambda: f5_batch.start('fixture', root=directory))
                def request_stop():
                    stop_started.set()
                    result.update(f5_batch.stop('fixture', root=directory))
                stopper = threading.Thread(target=request_stop)
                try:
                    starter.start()
                    self.assertTrue(paused.wait(1))
                    stopper.start()
                    self.assertTrue(stop_started.wait(1))
                    stopper.join(0.05)
                    self.assertTrue(stopper.is_alive())
                    release.set()
                    starter.join(1)
                    stopper.join(1)
                    self.assertFalse(starter.is_alive())
                    self.assertFalse(stopper.is_alive())
                    token = (directory / 'worker-token').read_text()
                    self.assertTrue(result['stopping'])
                    self.assertTrue((directory / ('stop-' + token)).exists())
                    self.assertFalse((directory / ('stop-' + 'a' * 32)).exists())
                finally:
                    release.set()
                    starter.join(1)
                    if stop_started.is_set():
                        stopper.join(1)
                    finish.set()
                    if inherited:
                        reaped.wait(1)
