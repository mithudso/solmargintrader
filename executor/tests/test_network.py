"""Live, READ-ONLY checks (run with `pytest -m network`). They quote, build and simulate against mainnet; none signs
or sends anything, and none needs the key. They use the owner's public address only to build a transaction."""

import pytest

from executor.config import load_config
from executor.engine import Engine
from executor.http import HttpxHttp
from executor.rpc import Rpc

pytestmark = pytest.mark.network


@pytest.fixture
def live():
    cfg = load_config()
    return cfg, Engine(cfg)


def test_live_quote_is_acceptable_and_has_a_second_price(live):
    _, engine = live
    q = engine.quote("SOL", "USDC", "0.01")
    assert q["acceptable"] is True, q["problems"]
    assert q["reference"]["source"] == "jupiter-price-api" and q["route"]
    assert q["min_out_raw"] <= q["out_raw"] and abs(q["deviation_bps"]) < 100


def test_live_price_impact_units_agree_with_the_independent_reference(live):
    """A large order shows impact; the reference deviation must move the same way. Guards the fraction-vs-percent reading."""
    _, engine = live
    q = engine.quote("SOL", "USDC", "5000")
    assert q["price_impact_bps"] >= 0
    if q["price_impact_bps"] > 1:
        assert q["deviation_bps"] > 0  # the quote is worse than spot when impact is real


def test_live_dry_run_swap_builds_verifies_and_simulates(live):
    cfg, engine = live
    out = engine.swap("SOL", "USDC", "0.005", strategy=None)
    assert out["mode"] == "dry-run" and out["sent"] is False
    assert out["economic"]["output_token_delta_raw"] >= out["quote"]["min_out_raw"]
    assert set(out["static"]["programs"]) <= {
        "11111111111111111111111111111111",
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
        "ComputeBudget111111111111111111111111111111",
        "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    }


def test_live_cross_chain_quote_is_quote_only(live):
    _, engine = live
    q = engine.quote("USDC", "USDC", "5", to_chain="base")
    assert q["executable"] is False and float(q["out_amount"]) > 0


def test_live_rpc_reads(live):
    cfg, _ = live
    rpc = Rpc(cfg.rpc_url, HttpxHttp())
    assert rpc.balance(cfg.owner) >= 0 and rpc.block_height() > 0
