"""The swap pipeline end to end against an in-memory chain: dry-run, live, and every way a send can go wrong."""

import fcntl
import json
import os

import pytest
from conftest import (
    ATTACKER,
    delta_native,
    delta_token,
    jup_http_for,
    make_engine,
    swap_instructions,
    sys_transfer,
    tx_json,
)

from executor import txverify
from executor.config import VALIDATION_STRATEGY
from executor.errors import Ambiguous, BadParams, ExecutorError, Refused
from executor.tokens import USDC_MINT, WSOL_MINT

AMOUNT_UI = "0.01"
AMOUNT = 10_000_000
FEE = 10_000  # 5,000 base + 100,000 CU at 50,000 micro-lamports/CU
OUT = 900_000


def sell_setup(owner, cfg, chain, out=OUT):
    """SOL -> USDC: owner pays AMOUNT + FEE lamports and receives `out` USDC."""
    chain.mods[owner] = delta_native(-(AMOUNT + FEE))
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = delta_token(out, USDC_MINT, owner)
    chain.tx_meta = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (100_000_000, 100_000_000 + out)})
    return jup_http_for(owner, WSOL_MINT, USDC_MINT, AMOUNT)


def live_cfg(cfg):
    cfg.mode = "live"
    cfg.validation.enabled = True
    return cfg


def swap(engine, **kw):
    kw.setdefault("strategy", VALIDATION_STRATEGY)
    return engine.swap("SOL", "USDC", AMOUNT_UI, **kw)


def kinds(engine):
    return [(r["kind"], r["id"]) for r in engine.journal.records()]


# -- dry run ---------------------------------------------------------------------------------------------------


def test_dry_run_simulates_and_sends_nothing(cfg, chain, owner):
    cfg.validation.enabled = True
    http = sell_setup(owner, cfg, chain)
    engine = make_engine(cfg, chain, http)
    out = swap(engine)
    assert out["mode"] == "dry-run" and out["sent"] is False and out["would_send"] is True
    assert chain.sent == [] and chain.simulations == 1
    assert out["economic"]["output_token_delta_raw"] == OUT
    assert [k for k, _ in kinds(engine)] == ["dry_run"]
    soak = json.loads((engine.root / "soak.json").read_text())
    assert soak["strategies"][VALIDATION_STRATEGY]["dry_runs"] == 1  # a clean dry-run counts toward the soak


def test_mode_live_without_the_live_flag_is_still_a_dry_run(cfg, chain, owner):
    live_cfg(cfg)
    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain))
    out = swap(engine)
    assert out["mode"] == "dry-run" and chain.sent == []


def test_live_flag_with_dry_run_config_is_refused(cfg, chain, owner):
    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain))
    with pytest.raises(Refused, match='config mode is not "live"'):
        swap(engine, live=True, reason="x")
    assert chain.sent == []


def test_live_needs_a_reason(cfg, chain, owner):
    live_cfg(cfg)
    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain))
    with pytest.raises(BadParams, match="reason"):
        swap(engine, live=True)


def test_dry_run_refuses_what_live_would_refuse(cfg, chain, owner):
    chain.mods[owner] = delta_native(-(AMOUNT + FEE))
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = delta_token(1, USDC_MINT, owner)  # far below minOut
    engine = make_engine(cfg, chain, jup_http_for(owner, WSOL_MINT, USDC_MINT, AMOUNT))
    with pytest.raises(Refused, match="below minOut"):
        swap(engine, strategy=None)
    assert (engine.root / "soak.json").exists() is False  # a refused dry-run earns no soak credit


def test_quote_problem_stops_before_a_transaction_is_built(cfg, chain, owner):
    http = jup_http_for(owner, WSOL_MINT, USDC_MINT, AMOUNT, impact="0.05")  # 500 bps
    engine = make_engine(cfg, chain, http)
    with pytest.raises(Refused, match="price impact"):
        swap(engine, strategy=None)
    assert not any("/swap/v1/swap" in url for _, url, _ in http.calls)


def test_missing_sol_price_refuses(cfg, chain, owner):
    http = sell_setup(owner, cfg, chain)
    http.on("/price/v3", {USDC_MINT: {"usdPrice": 1.0}})
    with pytest.raises(Refused, match="no independent price reference"):
        swap(make_engine(cfg, chain, http), strategy=None)


def test_malicious_transaction_is_refused_before_the_key_is_read(cfg, chain, owner):
    live_cfg(cfg)
    ixs = [*swap_instructions(owner, WSOL_MINT, USDC_MINT, AMOUNT), sys_transfer(owner, ATTACKER, 5_000_000)]
    http = jup_http_for(owner, WSOL_MINT, USDC_MINT, AMOUNT, instructions=ixs)
    loaded = []
    engine = make_engine(cfg, chain, http)
    engine.key_loader = lambda *a: loaded.append(a) or pytest.fail("the key must not be read")
    with pytest.raises(Refused, match="verifier"):
        swap(engine, live=True, reason="t")
    assert loaded == [] and chain.sent == [] and chain.simulations == 0


# -- live ------------------------------------------------------------------------------------------------------


def live_engine(cfg, chain, owner, **kw):
    live_cfg(cfg)
    return make_engine(cfg, chain, sell_setup(owner, cfg, chain, **kw))


def test_live_happy_path_journals_before_and_after_sending(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    out = swap(engine, live=True, reason="prove the live path")
    assert out["sent"] is True and out["post_verify_ok"] is True
    assert out["in_raw"] == AMOUNT and out["out_raw"] == OUT and out["fee_lamports"] == FEE
    assert len(chain.sent) == 1
    seq = kinds(engine)
    assert [k for k, _ in seq] == ["intent", "sending", "result"]
    recs = list(engine.journal.records())
    assert recs[0]["reason"] == "prove the live path" and recs[0]["evidence"]["economic"]
    assert recs[1]["signature"] == out["signature"] == recs[2]["signature"]
    assert recs[2]["status"] == "confirmed" and recs[2]["base_raw"] == AMOUNT
    assert chain.simulations == 2  # the unsigned build, then the exact signed bytes with signature verification
    unsigned, signed = chain.simulation_calls
    assert unsigned["sig_verify"] is False and unsigned["replace_blockhash"] is True
    assert signed["sig_verify"] is True and signed["replace_blockhash"] is False
    assert signed["tx_b64"] == chain.sent[0]
    assert signed["watch"] == unsigned["watch"]
    assert not (engine.root / "KILL").exists()


def test_the_signed_transaction_is_the_verified_message(cfg, chain, owner):
    from executor.txverify import decode_b64, message_hash

    engine = live_engine(cfg, chain, owner)
    out = swap(engine, live=True, reason="t")
    sent = decode_b64(chain.sent[0])
    assert message_hash(sent) == out["message_sha256"]
    assert str(sent.signatures[0]) == out["signature"] and str(sent.signatures[0]) != "1" * 64


def test_live_state_after_a_confirmed_buy_feeds_the_position_rails(cfg, chain, owner):
    live_cfg(cfg)
    chain.mods[owner] = delta_native(11_100_000 - FEE)
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    chain.tx_meta = tx_json(owner, 11_100_000 - FEE, FEE, {USDC_MINT: (100_000_000, 99_000_000)})
    http = jup_http_for(owner, USDC_MINT, WSOL_MINT, 1_000_000, out_amount=11_100_000)
    engine = make_engine(cfg, chain, http)
    out = engine.swap("USDC", "SOL", "1", strategy=VALIDATION_STRATEGY, live=True, reason="buy")
    assert out["sent"] and out["in_raw"] == 1_000_000 and out["out_raw"] == 11_100_000
    from executor import ledger

    pos = ledger.positions(engine.journal.states(), VALIDATION_STRATEGY)[WSOL_MINT]
    assert pos.qty_raw == 11_100_000 and str(pos.cost_usd) == "1.000000"


def test_node_rejection_is_definite_and_does_not_block(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.send_behaviour = "reject"
    with pytest.raises(ExecutorError, match="rejected"):
        swap(engine, live=True, reason="t")
    states = engine.journal.states()
    assert [s["state"] for s in states.values()] == ["result"] and engine.journal.unresolved() == []
    assert [r["status"] for r in engine.journal.records() if r["kind"] == "result"] == ["rejected"]


def test_ambiguous_send_is_unknown_never_retried_and_blocks_new_swaps(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.send_behaviour = "timeout"
    with pytest.raises(Ambiguous) as ei:
        swap(engine, live=True, reason="t")
    assert ei.value.code == "ambiguous" and "NOT retried" in ei.value.message
    assert len(chain.sent) == 1  # exactly one attempt
    assert [s["state"] for s in engine.journal.states().values()] == ["unknown"]
    chain.send_behaviour = "ok"
    with pytest.raises(Refused, match="unresolved send"):
        swap(engine, live=True, reason="again")
    assert len(chain.sent) == 1  # still one: nothing retried it
    assert swap(engine)["mode"] == "dry-run"  # a dry-run is still fine


def test_unconfirmed_send_becomes_unknown_then_reconcile_confirms_it(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = None  # never appears within the timeout
    with pytest.raises(Ambiguous, match="not confirmed"):
        swap(engine, live=True, reason="t")
    assert len(chain.sent) == 1 and [s["state"] for s in engine.journal.states().values()] == ["unknown"]
    # Later the transaction is found on chain.
    chain.default_status = {"confirmationStatus": "finalized", "err": None}
    res = engine.reconcile()
    assert res["results"][0]["outcome"] == "confirmed" and res["still_blocking"] == 0
    rec = [r for r in engine.journal.records() if r["kind"] == "reconciled"][0]
    assert rec["status"] == "confirmed" and rec["out_raw"] == OUT and rec["post_verify_ok"] is True
    assert len(chain.sent) == 1  # reconcile never re-sends


def test_reconcile_failed_dropped_and_still_pending(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = None
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="t")
    # Not found and the blockhash may still be valid: stays blocking.
    chain.height = 1100
    assert engine.reconcile()["results"][0]["outcome"] == "still_unknown" and engine.journal.unresolved()
    # Not found and the blockhash is long expired: it can never land.
    chain.height = 1200 + 151
    assert engine.reconcile()["results"][0]["outcome"] == "dropped" and not engine.journal.unresolved()


def test_reconcile_failed_on_chain(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = None
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="t")
    chain.default_status = {"confirmationStatus": "confirmed", "err": {"InstructionError": [4, {"Custom": 1}]}}
    chain.tx_meta["meta"]["err"] = chain.default_status["err"]
    assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"
    assert not engine.journal.unresolved()


def test_failed_on_chain_is_a_definite_failure(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = {"confirmationStatus": "confirmed", "err": {"InstructionError": [4, {"Custom": 6001}]}}
    chain.tx_meta["meta"]["err"] = chain.default_status["err"]
    with pytest.raises(ExecutorError, match="failed on chain"):
        swap(engine, live=True, reason="t")
    assert engine.journal.unresolved() == []
    assert [r["status"] for r in engine.journal.records() if r["kind"] == "result"] == ["failed"]


def test_confirmed_but_unreadable_balances_are_unknown(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.tx_available = False
    with pytest.raises(Ambiguous, match="balances could not be read"):
        swap(engine, live=True, reason="t")
    assert [s["state"] for s in engine.journal.states().values()] == ["unknown"]


def test_post_trade_mismatch_trips_the_kill_file(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.tx_meta = tx_json(
        owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (100_000_000, 100_000_000 + 10)}
    )  # far under minOut
    out = swap(engine, live=True, reason="t")
    assert out["post_verify_ok"] is False
    assert (engine.root / "KILL").exists()
    with pytest.raises(Refused, match="KILL"):
        swap(engine, live=True, reason="again")


def test_node_returning_another_signature_is_unknown(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.send_behaviour = "wrong_sig"
    with pytest.raises(Ambiguous, match="expected"):
        swap(engine, live=True, reason="t")
    assert engine.journal.unresolved()


def test_stale_quote_is_refused_before_sending(cfg, chain, owner):
    live_cfg(cfg)
    t = {"now": 1_800_000_000.0}

    def clock():
        t["now"] += 30.0  # every look at the clock costs 30 s
        return t["now"]

    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain), clock=clock)
    with pytest.raises(Refused, match="s old"):
        swap(engine, live=True, reason="t")
    assert chain.sent == [] and kinds(engine) == []


def test_expiring_blockhash_is_refused(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.height = 1190
    with pytest.raises(Refused, match="blockhash is about to expire"):
        swap(engine, live=True, reason="t")
    assert chain.sent == [] and kinds(engine) == []


def test_resimulation_of_the_signed_bytes_can_still_refuse(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    first = chain.mods[txverify.ata_address(owner, USDC_MINT)]
    bad = delta_token(1, USDC_MINT, owner)
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = lambda acc: first(acc) if chain.simulations <= 1 else bad(acc)
    with pytest.raises(Refused, match="signed tx"):
        swap(engine, live=True, reason="t")
    assert chain.sent == [] and kinds(engine) == []


def test_kill_file_blocks_live(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    engine.root.mkdir(parents=True, exist_ok=True)
    (engine.root / "KILL").write_text("stop")
    with pytest.raises(Refused, match="KILL file present"):
        swap(engine, live=True, reason="t")
    assert chain.sent == []


def test_concurrent_swap_is_refused(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    engine.root.mkdir(parents=True, exist_ok=True)
    fd = os.open(engine.root / "swap.lock", os.O_WRONLY | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(Refused, match="another swap is in progress"):
            swap(engine, live=True, reason="t")
    finally:
        os.close(fd)


def test_wrong_key_file_stops_live(cfg, chain, owner, tmp_path):
    from conftest import write_keyfile
    from solders.keypair import Keypair

    live_cfg(cfg)
    cfg.key_file = write_keyfile(tmp_path / "other.json", Keypair.from_seed(bytes([9] * 32)))
    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain))
    with pytest.raises(ExecutorError, match="does not match"):
        swap(engine, live=True, reason="t")
    assert chain.sent == []


def test_slippage_can_only_be_tightened(cfg, chain, owner):
    engine = make_engine(cfg, chain, sell_setup(owner, cfg, chain, out=901_000))
    with pytest.raises(Refused, match="only tightens"):
        swap(engine, strategy=None, slippage_bps=cfg.rails.max_slippage_bps + 1)
    out = swap(engine, strategy=None, slippage_bps=10)
    assert out["quote"]["slippage_bps"] == 10
