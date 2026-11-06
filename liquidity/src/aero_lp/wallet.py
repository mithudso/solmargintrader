"""Signing key loading. The key is never printed, logged or written to disk by this program.

Sources, in order:
  0. `key_file` in the config (or AERO_LP_KEY_FILE): a file holding the hex key. It must be owned by the
     current user and not readable by group or others (chmod 600), or it is refused.
  1. macOS Keychain generic password, service "aero-lp", account = owner address (lowercase).
     Store it with:  security add-generic-password -s aero-lp -a <owner-lowercase> -w
     (omit the value after -w so `security` prompts for it and it stays out of shell history)
  2. Environment variable AERO_LP_PRIVATE_KEY.

Use a dedicated hot wallet that holds only the managed position. Never use a wallet that holds
your other funds.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from eth_account import Account
from eth_account.signers.local import LocalAccount


class WalletError(RuntimeError):
    pass


def _from_keychain(owner: str) -> str | None:
    if shutil.which("security") is None:
        return None
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "aero-lp", "-a", owner.lower(), "-w"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _from_file(path: str) -> str:
    p = os.path.expanduser(path)
    try:
        st = os.stat(p)
    except OSError as e:
        raise WalletError(f"key file {p} is not readable: {e.strerror}") from None
    if st.st_uid != os.getuid():
        raise WalletError(f"key file {p} is owned by uid {st.st_uid}, not you; fix: sudo chown $USER {p}")
    if st.st_mode & 0o077:
        raise WalletError(
            f"key file {p} is readable by other users (mode {oct(st.st_mode & 0o777)}); fix: chmod 600 {p}"
        )
    with open(p) as f:
        return f.read().strip()


def load_signer(owner: str, key_file: str | None = None) -> LocalAccount:
    key_file = key_file or os.environ.get("AERO_LP_KEY_FILE")
    key = _from_file(key_file) if key_file else (_from_keychain(owner) or os.environ.get("AERO_LP_PRIVATE_KEY"))
    if not key:
        raise WalletError(
            "no signing key: add it to the macOS Keychain (service 'aero-lp', account = owner address) "
            "or set AERO_LP_PRIVATE_KEY"
        )
    try:
        acct: LocalAccount = Account.from_key(key)
    except Exception:  # noqa: BLE001 - never echo the key or its parse error details
        raise WalletError("signing key is not a valid private key") from None
    if acct.address.lower() != owner.lower():
        raise WalletError(f"signing key controls {acct.address}, but config owner is {owner}")
    return acct
