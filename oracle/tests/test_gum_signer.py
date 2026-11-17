"""The live signer rejects replaced, public, malformed and wrong-owner keys."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from oracle.gum_signer import load_signer


def encode(raw):
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(raw, "big")
    result = ""
    while number:
        number, digit = divmod(number, 58)
        result = alphabet[digit] + result
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + result


class GumSignerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test-key.json"
        self.seed = bytes(range(32))
        self.key = Ed25519PrivateKey.from_private_bytes(self.seed)
        self.public = self.key.public_key().public_bytes_raw()
        self.owner = encode(self.public)
        self.raw = self.seed + self.public
        self.path.write_text(json.dumps(list(self.raw)))
        self.path.chmod(0o600)

    def test_owner_bound_signature_verifies(self):
        signature = load_signer(self.path, self.owner)(b"locally constructed action")
        self.key.public_key().verify(signature, b"locally constructed action")

    def test_base58_key_format(self):
        self.path.write_text(encode(self.raw))
        signature = load_signer(self.path, self.owner)(b"action")
        self.key.public_key().verify(signature, b"action")

    def test_public_file_and_symlink_are_refused(self):
        self.path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "must_be_private"):
            load_signer(self.path, self.owner)
        self.path.chmod(0o600)
        link = self.path.with_suffix(".link")
        os.symlink(self.path, link)
        with self.assertRaises(OSError):
            load_signer(link, self.owner)

    def test_wrong_owner_or_inconsistent_public_half_is_refused(self):
        with self.assertRaisesRegex(ValueError, "owner_mismatch"):
            load_signer(self.path, encode(bytes(32)))
        self.path.write_text(json.dumps(list(self.seed + bytes(32))))
        with self.assertRaisesRegex(ValueError, "owner_mismatch"):
            load_signer(self.path, self.owner)

    def test_malformed_input_does_not_enter_error(self):
        for value in ["private-test-material!", json.dumps([True] * 64), "x" * 4097]:
            with self.subTest(length=len(value)):
                self.path.write_text(value)
                with self.assertRaisesRegex(
                    ValueError, "gum_key_invalid_or_owner_mismatch"
                ) as caught:
                    load_signer(self.path, self.owner)
                self.assertEqual(str(caught.exception), "gum_key_invalid_or_owner_mismatch")
                self.assertNotIn(value, str(caught.exception))
