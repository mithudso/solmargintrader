"""Offline fixtures must never select an inherited owner wallet or state directory."""

import pytest

from aero_lp import wallet


@pytest.fixture(autouse=True)
def isolated_owner_inputs(monkeypatch, tmp_path):
    monkeypatch.delenv("AERO_LP_KEY_FILE", raising=False)
    monkeypatch.delenv("AERO_LP_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path / "lp-home"))
    monkeypatch.setattr(wallet, "_from_keychain", lambda owner: None)
