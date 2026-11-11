"""Credential boundary regressions; protocol acceptance uses the real SDK."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts import mcp_remote_client as client


class CredentialBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.token_file = Path(self.directory.name) / "token"
        self.token_file.write_text("test-only-credential\n")
        self.token_file.chmod(0o600)

    def test_headers_mode_produces_only_the_client_header(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = client.main(["headers", "--token-file", str(self.token_file)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()), {"Authorization": "Bearer test-only-credential"})
        self.assertEqual(err.getvalue(), "")

    def test_shared_file_is_refused_without_credential_output(self) -> None:
        self.token_file.chmod(0o640)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = client.main(["headers", "--token-file", str(self.token_file)])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("test-only-credential", err.getvalue())

    def test_symlink_is_refused(self) -> None:
        link = self.token_file.with_name("linked-token")
        link.symlink_to(self.token_file)
        with self.assertRaises(client.ConfigurationError):
            client.authorization_headers(link)

    def test_fifo_is_refused_without_waiting_for_a_writer(self) -> None:
        fifo = self.token_file.with_name("fifo-token")
        os.mkfifo(fifo, 0o600)
        with self.assertRaises(client.ConfigurationError):
            client.authorization_headers(fifo)

    def test_empty_oversized_and_header_injection_tokens_are_refused(self) -> None:
        for token in ["", "x" * 4097, "abc\r\nX-Injected: yes", "abc def", "non-ascii-\u00e9"]:
            with self.subTest(token_length=len(token)):
                self.token_file.write_text(token)
                with self.assertRaises(client.ConfigurationError):
                    client.authorization_headers(self.token_file)

    def test_credentials_are_not_sent_to_unsafe_urls(self) -> None:
        for url in ["http://m5.tail0781b8.ts.net/mcp", "https://user:password@example.com/mcp",
                    "https://example.com/mcp?token=value", "https://example.com/mcp#token", ""]:
            with self.subTest(url=url), self.assertRaises(client.ConfigurationError):
                client.validate_endpoint(url)
        client.validate_endpoint("https://m5.tail0781b8.ts.net/mcp")


if __name__ == "__main__":
    unittest.main()
