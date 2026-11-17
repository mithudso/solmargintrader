"""Maintenance regressions at accounting, permission and verification boundaries.

Every chain/transport is synthetic and every file belongs to pytest's temp tree.
"""

import struct
from decimal import localcontext
from uuid import uuid4

import pytest
from conftest import ATTACKER, jup_http_for, make_engine
from test_authority import seed
from test_rails import check, report
from test_txverify import econ_setup, honest_sell_mods, run_econ

from executor import ledger, txverify
from executor.config import VALIDATION_STRATEGY, Config
from executor.errors import Ambiguous, BadParams, Refused
from executor.tokens import USDC_MINT, WSOL_MINT, ui_to_raw


def test_legacy_strategyless_exposure_cannot_escape_shared_cap(cfg, chain, owner):
    engine = make_engine(cfg, chain, jup_http_for(owner, USDC_MINT, WSOL_MINT, 20_000_000))
    seed(engine, strategy=None, cost="90", quantity=1_000_000_000)
    with engine.authority.lock(), pytest.raises(Refused, match="unclassified|portfolio cap"):
        engine.authority.budget(report("buy", 20), 1_000_000_000, 0, reserve=False)
    assert chain.sent == []


def test_validation_cannot_label_untracked_wallet_sale_as_a_kill_exempt_exit(tmp_path):
    cfg = Config(mode="live")
    cfg.validation.enabled = True
    # This is the pure rail, with key-file inspection stubbed by live=False.
    # Its reduce-only contract applies in dry-run as well as live mode.
    with pytest.raises(Refused, match="tracked|open quantity"):
        check(cfg, tmp_path, report("sell", 1), strategy=VALIDATION_STRATEGY, exit_only=True, kill_present=True)
    assert check(cfg, tmp_path, report("sell", 1), strategy=VALIDATION_STRATEGY).side == "sell"


@pytest.mark.parametrize("precision", [6, 28, 60])
def test_base_unit_conversion_rejects_precision_lost_by_decimal_context(precision):
    with localcontext() as ctx:
        ctx.prec = precision
        with pytest.raises(BadParams):
            ui_to_raw("1.00000000000000000000000000001", 6)
        assert ui_to_raw("1234567890123.000001", 6) == 1234567890123000001
        assert ui_to_raw("1.230000", 6) == 1_230_000


def confirmed(**fields):
    return {
        "x": {
            "state": "result",
            "intent": {"strategy": "grid", "side": "buy", "base_mint": WSOL_MINT},
            "outcome": {"status": "confirmed", "ts": 1_800_000_000, "base_raw": 1, "quote_usd": "1", **fields},
        }
    }


@pytest.mark.parametrize("fee", [None, "-1", "NaN", "Infinity", True])
def test_confirmed_fees_cannot_be_unknown_negative_or_nonfinite(fee):
    fields = {} if fee is None else {"fee_usd": fee}
    with pytest.raises(Refused, match="fee"):
        ledger.realized_pnl_usd(confirmed(**fields), ledger.utc_day(1_800_000_000), "grid")


@pytest.mark.parametrize(
    "fields",
    [{"base_raw": -1}, {"base_raw": True}, {"quote_usd": "-1"}, {"quote_usd": "NaN"}, {"quote_usd": "Infinity"}],
)
def test_confirmed_accounting_cannot_create_invalid_positions(fields):
    state = confirmed(fee_usd="0", **fields)
    with pytest.raises(Refused):
        ledger.positions(state, "grid")
    with pytest.raises(Refused):
        ledger.realized_pnl_usd(state, ledger.utc_day(1_800_000_000), "grid")


@pytest.mark.parametrize("offset", [72, 129])
def test_swap_cannot_install_persistent_token_authority(owner, offset):
    chain, facts, exp, info = econ_setup(owner)
    honest_sell_mods(chain, owner)
    address = txverify.ata_address(owner, USDC_MINT)
    original = chain.mods[address]

    def delegated(account):
        changed = original(account)
        data = bytearray(changed["data"])
        data[offset : offset + 4] = struct.pack("<I", 1)
        data[offset + 4 : offset + 36] = bytes(txverify.Pubkey.from_string(ATTACKER))
        if offset == 72:
            data[121:129] = struct.pack("<Q", 1)
        return {**changed, "data": bytes(data)}

    chain.mods[address] = delegated
    problems, _ = run_econ(chain, facts, exp, info)
    assert any("authority" in p or "delegate" in p for p in problems)
    assert chain.sent == []


def test_anchor_failure_preserves_primary_unknown_and_resets_request_state(cfg, chain, owner, monkeypatch, caplog):
    engine = make_engine(cfg, chain, jup_http_for(owner, WSOL_MINT, USDC_MINT, 1_000_000))
    request_id = str(uuid4())
    primary = Ambiguous("synthetic unknown outcome")

    def uncertain(*args):
        journal = engine.journal
        journal.append("intent", "pending", strategy="grid", side="sell", base_mint=WSOL_MINT)
        journal.append("sending", "pending", signature="synthetic")
        journal.append("unknown", "pending", signature="synthetic")
        engine.authority.update(request_id, "executing", reserved="1", intent_id="pending")
        raise primary

    monkeypatch.setattr(engine, "_swap_locked", uncertain)
    monkeypatch.setattr(engine.authority, "save_anchor", lambda: (_ for _ in ()).throw(OSError("synthetic-secret")))
    with pytest.raises(Ambiguous) as caught:
        engine.swap("SOL", "USDC", "0.001", strategy="grid", live=True, reason="synthetic only", request_id=request_id)
    assert caught.value is primary
    assert engine.cfg is cfg
    assert engine._caller_request is None and engine._caller_reserved is None
    assert engine._entry_admission is None and engine._reviewed_cfg is None
    state = engine.authority.status(request_id)["request"]
    assert state["state"] == "unknown" and state["reserved_usd"] == "1"
    assert engine.journal.states()["pending"]["state"] == "unknown"
    assert chain.sent == []
    assert "anchor_persist_failed" in caplog.text and "synthetic-secret" not in caplog.text


def test_fake_chain_refuses_unsigned_bytes_when_signature_verification_is_requested(chain, owner):
    from conftest import make_tx, swap_instructions, tx_b64

    unsigned = tx_b64(make_tx(swap_instructions(owner, WSOL_MINT, USDC_MINT, 10_000_000), owner))
    assert chain.simulate(unsigned, [owner], False, True)["err"] is None
    assert chain.simulate(unsigned, [owner], True, False)["err"] is not None
    assert chain.sent == []
