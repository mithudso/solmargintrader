"""Exercise the opt-in network fixture itself with every external seam inert."""

from unittest.mock import patch

import test_network
from conftest import jup_http_for, make_engine

from executor.tokens import USDC_MINT, WSOL_MINT


def test_network_fixture_forces_dry_run_and_enrolls_its_disposable_authority(cfg, chain, owner, monkeypatch, isolated):
    engine = make_engine(cfg, chain, jup_http_for(owner, USDC_MINT, WSOL_MINT, 1))
    cfg.dry_run = False
    monkeypatch.setattr(test_network, "load_config", lambda: cfg)
    monkeypatch.setattr(test_network, "Engine", lambda _: engine)
    with patch.object(engine.authority, "register", wraps=engine.authority.register) as register:
        observed_cfg, observed_engine = test_network.live.__wrapped__(isolated)
    assert observed_cfg is cfg and observed_engine is engine
    assert cfg.dry_run is True
    register.assert_called_once_with("100", [{"root": str(engine.root), "aware": True}], True)
    assert chain.sent == []
