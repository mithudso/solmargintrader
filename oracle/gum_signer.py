"""Private, owner-bound Ed25519 signing for locally constructed GUM Actions."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path


def _decode(value: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for char in value:
        number = number * 58 + alphabet.index(char)
    return b"\0" * (len(value) - len(value.lstrip("1"))) + number.to_bytes(
        (number.bit_length() + 7) // 8, "big"
    )


def load_signer(path: Path, expected_owner: str):
    """Load only at live submission, without returning or logging key material.

    The caller constructs and validates the economic Action before invoking this
    signer. This signer must never sign an upstream transaction or JSON request.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("gum_key_file_must_be_private")
        raw = os.read(fd, 4097)
    finally:
        os.close(fd)
    try:
        if len(raw) > 4096:
            raise ValueError
        text = raw.decode().strip()
        if text.startswith("["):
            data = json.loads(text)
            if not (
                isinstance(data, list)
                and len(data) == 64
                and all(type(v) is int and 0 <= v <= 255 for v in data)
            ):
                raise ValueError
            key_bytes = bytes(data)
        else:
            key_bytes = _decode(text)
        if len(key_bytes) != 64:
            raise ValueError
        key = Ed25519PrivateKey.from_private_bytes(key_bytes[:32])
        public = key.public_key().public_bytes_raw()
        if public != key_bytes[32:] or public != _decode(expected_owner):
            raise ValueError
    except (ValueError, UnicodeError, TypeError, OverflowError):
        raise ValueError("gum_key_invalid_or_owner_mismatch") from None
    return key.sign
