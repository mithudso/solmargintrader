"""Signing key loading. The key is never printed, logged or written to disk by this program.

Sources, in order:
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


def load_signer(owner: str) -> LocalAccount:
    key = _from_keychain(owner) or os.environ.get("AERO_LP_PRIVATE_KEY")
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
