"""Exercise the load fixture's cleanup helper without spawning a worker."""
import unittest
from types import SimpleNamespace

from tests.test_load import _close_supervisor_and_optimizer


class LoadCleanupTests(unittest.TestCase):
    def test_optimizer_is_reaped_even_if_supervisor_close_fails(self):
        events = []
        failure = RuntimeError('fixture close failed')
        def fail():
            raise failure
        supervisor = SimpleNamespace(close=fail)
        stop = SimpleNamespace(set=lambda: events.append('stop'))
        optimizer = SimpleNamespace(join=lambda seconds: events.append(('join', seconds)),
                                    is_alive=lambda: True, kill=lambda: events.append('kill'),
                                    exitcode=0, close=lambda: events.append('close'))
        with self.assertRaisesRegex(RuntimeError, 'fixture close failed') as raised:
            _close_supervisor_and_optimizer(supervisor, stop, optimizer)
        self.assertIs(raised.exception, failure)
        self.assertEqual(events, ['stop', ('join', 5), 'kill', ('join', 2), 'close'])
