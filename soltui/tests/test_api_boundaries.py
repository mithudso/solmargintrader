"""Exercise loopback HTTP framing with synthetic tokens and an inert registry."""
import socket
import threading
import unittest
from unittest import mock
from soltui import api


class HttpBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.dispatch = self.enterContext(mock.patch.object(api.commands, 'dispatch'))
        self.server = api.create_server(0, token='synthetic-token')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, headers, suffix=b''):
        with socket.create_connection(self.server.server_address, timeout=1) as sock:
            sock.settimeout(0.3)
            sock.sendall(headers + suffix)
            return sock.recv(65536)

    def test_negative_and_duplicate_lengths_refuse_before_dispatch(self):
        for framing in (b'Content-Length: -1\r\n', b'Content-Length: 0\r\nContent-Length: 1\r\n', b'Transfer-Encoding: chunked\r\n'):
            with self.subTest(framing=framing):
                response = self.request(b'POST /v1/settings.get HTTP/1.1\r\nHost: fixture\r\nAuthorization: Bearer synthetic-token\r\n' + framing + b'\r\n')
                self.assertIn(b'400', response.split(b'\r\n', 1)[0])
        self.dispatch.assert_not_called()

    def test_early_unauthorized_post_closes_before_pipeline_bytes(self):
        response = self.request(b'POST /v1/list HTTP/1.1\r\nHost: fixture\r\nContent-Length: 5\r\n\r\n', b'abcdeGET /v1/health HTTP/1.1\r\nHost: fixture\r\n\r\n')
        self.assertIn(b'401', response)
        self.assertIn(b'connection: close', response.lower())
        self.dispatch.assert_not_called()

    def test_incomplete_body_is_bounded_and_never_dispatches(self):
        # A new disposable server reads its configured timeout at accept time.
        with mock.patch.object(api, 'REQUEST_TIMEOUT_S', 0.05, create=True):
            response = self.request(b'POST /v1/settings.get HTTP/1.1\r\nHost: fixture\r\nAuthorization: Bearer synthetic-token\r\nContent-Length: 10\r\n\r\n', b'{')
        self.assertTrue(response == b'' or response.startswith(b'HTTP/1.1 400 '))
        self.dispatch.assert_not_called()
