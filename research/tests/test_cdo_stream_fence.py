"""A disabled subscription cannot be resurrected by an in-flight send."""

import threading
import unittest

from research.zec_tui_stream import TradeStream


class StreamFenceTests(unittest.TestCase):
    def test_disable_during_subscription_send_stays_hidden(self):
        for raises in (False, True):
            with self.subTest(send_raises=raises):
                self._check_send_race(raises)

    def _check_send_race(self, raises):
        sending, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        class Socket:
            close_count = 0

            def open(self):
                pass

            def settimeout(self, value):
                pass

            def send_text(self, value):
                sending.set()
                release.wait(2)
                if raises:
                    raise OSError("closed during send")

            def close(self):
                self.close_count += 1
                if self.close_count == 2:
                    finished.set()

        stream = TradeStream(ws_factory=lambda *a, **k: Socket(), clock=lambda: 1000)
        self.addCleanup(stream.close)
        stream.start()
        self.assertTrue(sending.wait(1))
        stream.set_enabled(False)
        release.set()
        self.assertTrue(finished.wait(1))
        self.assertFalse(stream.snapshot("1m")["connected"])
        self.assertEqual(stream.snapshot("1m")["reason"], "stream_hidden")
