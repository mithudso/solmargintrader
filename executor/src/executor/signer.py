"""Signing key loading. The key is never printed, logged, hashed, copied, or included in an exception message.

The file must be a regular file, owned by the current user, with no group or other permission bits (mode 600 or
stricter). The same open file descriptor is used for the checks and the read, so the file cannot be swapped in
between. The derived public key must equal the configured owner, or the key is refused.

Accepted formats: the Solana CLI keypair JSON (an array of 64 integers) or a base58 string of the 64 key bytes.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from .errors import WalletError


def check_key_file_mode(path: Path) -> None:
    """Raise unless `path` is a regular file owned by us with mode 600 or stricter."""
    fd = _open(path)
    try:
        _check_fd(fd, path)
    finally:
        os.close(fd)


def _open(path: Path) -> int:
    try:
        return os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise WalletError(f"key file {path} is not readable: {exc.strerror}") from None


def _check_fd(fd: int, path: Path) -> None:
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        raise WalletError(f"key file {path} is not a regular file")
    if st.st_uid != os.getuid():
        raise WalletError(f"key file {path} is not owned by the current user")
    if st.st_mode & 0o077:
        raise WalletError(f"key file {path} must be mode 600 (is {oct(stat.S_IMODE(st.st_mode))}); chmod 600 it")


def load_keypair(path_str: str, expected_owner: str) -> Keypair:
    path = Path(path_str).expanduser()
    fd = _open(path)
    try:
        _check_fd(fd, path)
        with os.fdopen(os.dup(fd), "rb") as fh:
            raw = fh.read(4096)
    finally:
        os.close(fd)
    try:
        text = raw.decode().strip()
        if text.startswith("["):
            data = json.loads(text)
            if not (
                isinstance(data, list) and len(data) == 64 and all(isinstance(b, int) and 0 <= b < 256 for b in data)
            ):
                raise ValueError
            kp = Keypair.from_bytes(bytes(data))
        else:
            kp = Keypair.from_base58_string(text)
    except Exception:  # noqa: BLE001 - never echo anything derived from the file
        raise WalletError(f"key file {path} is not a valid Solana keypair") from None
    if kp.pubkey() != Pubkey.from_string(expected_owner):
        raise WalletError("the key file's public key does not match the configured owner; refusing to sign")
    return kp
