"""Shared wallet authority, request replay and scoped admission adversarial tests."""

from __future__ import annotations

import hashlib
import json
import time
from decimal import Decimal
from uuid import uuid4

import pytest
from conftest import delta_native, delta_token, jup_http_for, make_engine, tx_json
from test_engine import FEE, live_engine, swap

from executor import authority, gates, manager, txverify
from executor.authority import WalletAuthority, digest, identity
from executor.errors import Ambiguous, Refused
from executor.tokens import USDC_MINT, WSOL_MINT


def request(engine, *, live=False):
    return {
        "version": 1,
        "request_id": str(uuid4()),
        "scope": {
            "strategy": "trend",
            "strategy_version": "sma-crossover-v1",
            "config_hash": "a" * 64,
            "bot_id": str(uuid4()),
            "runtime_id": str(uuid4()),
            "generation": 1,
            "revision": 1,
            "mints": [USDC_MINT, WSOL_MINT],
            "timeframe": 60,
            "execution_model": "next_open",
            "cost_model": "measured-v1",
            "data_model": "jupiter-measured-v1",
            "owner_identity": identity(engine.cfg),
        },
        "swap": {
            "from": "USDC",
            "to": "SOL",
            "amount": "1",
            "live": live,
            "exit": False,
            "reason": "synthetic fixture",
        },
    }


def certify(engine, req):
    """Synthetic evidence only; production has no automatic certificate issuer."""
    scope = req["scope"]
    cert = {
        "version": 1,
        "scope": scope,
        "research": {"certified": True, "scope_digest": digest(scope), "receipt_digest": "b" * 64},
        "shadow": {"certified": True, "scope_digest": digest(scope), "receipt_digest": "c" * 64},
        "input_healthy": True,
        "accounting_healthy": True,
        "issued_at": time.time() - 1,
        "expires_at": time.time() + 60,
    }
    path = engine.authority.root / "evidence" / (digest(scope) + ".json")
    path.parent.mkdir(exist_ok=True)
    receipts = path.parent / "receipts"
    receipts.mkdir(exist_ok=True)
    for kind in ("research", "shadow"):
        artifact = {
            "version": 1,
            "kind": kind,
            "scope": scope,
            "certified": True,
            "production_eligible": True,
            "result": "pass",
        }
        raw = json.dumps(artifact, sort_keys=True).encode()
        receipt_digest = hashlib.sha256(raw).hexdigest()
        (receipts / (receipt_digest + ".json")).write_bytes(raw)
        cert[kind]["receipt_digest"] = receipt_digest
    path.write_text(json.dumps(cert))
    return path, cert


def buyer(cfg, chain, owner):
    chain.mods[owner] = delta_native(11_100_000 - FEE)
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    chain.tx_meta = tx_json(owner, 11_100_000 - FEE, FEE, {USDC_MINT: (100_000_000, 99_000_000)})
    return make_engine(cfg, chain, jup_http_for(owner, USDC_MINT, WSOL_MINT, 1_000_000, out_amount=11_100_000))


def seed(engine, *, strategy="grid", cost="24", quantity=1_000_000):
    journal = engine.authority.journal
    iid = "seed-" + uuid4().hex
    journal.append("intent", iid, strategy=strategy, side="buy", base_mint=WSOL_MINT)
    journal.append("sending", iid, signature=iid)
    journal.append(
        "result", iid, status="confirmed", signature=iid, base_raw=quantity, quote_usd=cost, fee_usd="0", fee_lamports=0
    )
    engine.authority.save_anchor()


def test_new_home_cannot_select_new_wallet_authority(cfg, tmp_path):
    first = WalletAuthority(cfg, tmp_path / "home")
    other = WalletAuthority(cfg, tmp_path / "another-manager")
    assert first.root == other.root
    with pytest.raises(Refused, match="not enrolled"):
        other.check()


@pytest.mark.parametrize("cap", [None, 0, -1, "NaN", "Infinity", True])
def test_portfolio_cap_is_explicit_and_finite(cfg, cap, tmp_path):
    with pytest.raises(Refused, match="portfolio cap"):
        WalletAuthority(cfg, tmp_path / "home").register(cap, [{"root": str(tmp_path / "home"), "aware": True}], True)


def test_cap_cannot_be_increased_by_new_client_or_configuration(cfg, tmp_path):
    other = WalletAuthority(cfg, tmp_path / "new")
    with pytest.raises(Refused, match="cannot increase"):
        other.register("1000", [{"root": str(other.client), "aware": True}], True)
    cfg.rails.max_position_usd = 1000
    cfg.rails.max_trade_usd = 1000
    other.register("90", [{"root": str(other.client), "aware": True}], True)
    effective = other.effective_config()
    assert effective.rails.max_position_usd == 25
    assert effective.rails.max_trade_usd == 10


def test_unaware_writer_cannot_be_omitted_to_reopen_admission(cfg, tmp_path):
    wallet = WalletAuthority(cfg, tmp_path / "home")
    wallet.register(
        "100", [{"root": str(wallet.client), "aware": True}, {"root": str(tmp_path / "legacy"), "aware": False}], True
    )
    wallet.register("100", [{"root": str(wallet.client), "aware": True}], True)
    with pytest.raises(Refused, match="unaware"):
        wallet.check()


def test_missing_request_ledger_is_never_recreated(cfg, tmp_path):
    wallet = WalletAuthority(cfg, tmp_path / "home")
    (wallet.root / "requests.sqlite3").unlink()
    with pytest.raises(Refused, match="refusing recreation"):
        wallet.register("100", [{"root": str(wallet.client), "aware": True}], True)


def test_local_writer_history_change_blocks_shared_writer(cfg, tmp_path):
    wallet = WalletAuthority(cfg, tmp_path / "home")
    from executor.journal import Journal

    Journal(wallet.client / "journal.jsonl").append("intent", "legacy", strategy="grid")
    with pytest.raises(Refused, match="outside shared"):
        wallet.check()


def test_shared_journal_deletion_cannot_reset_position_caps(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    seed(engine)
    engine.authority.journal.path.unlink()
    with pytest.raises(Refused, match="disappeared"):
        engine.authority.check()


def test_cross_home_shared_lock_and_kill(cfg, tmp_path):
    first = WalletAuthority(cfg, tmp_path / "home")
    other = WalletAuthority(cfg, tmp_path / "other")
    other.register("100", [{"root": str(other.client), "aware": True}], True)
    with first.lock(), pytest.raises(Refused, match="another shared wallet writer"), other.lock():
        pass
    (first.client / "KILL").write_text("synthetic")
    assert other.killed()


def test_request_replay_sends_exactly_once_and_context_transplant_conflicts(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    rid = str(uuid4())
    result = swap(engine, live=True, reason="synthetic", request_id=rid, caller_context={"bot": "first"})
    assert swap(engine, live=True, reason="synthetic", request_id=rid, caller_context={"bot": "first"}) == result
    assert len(chain.sent) == 1
    with pytest.raises(Refused, match="conflicts"):
        swap(engine, live=True, reason="synthetic", request_id=rid, caller_context={"bot": "second"})
    assert len(chain.sent) == 1


def test_timeout_retains_reservation_replay_never_sends_and_reconcile_releases(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.send_behaviour = "timeout"
    rid = str(uuid4())
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic", request_id=rid)
    state = engine.authority.status(rid)["request"]
    assert state["state"] == "unknown" and Decimal(state["reserved_usd"]) > 0
    replay = swap(engine, live=True, reason="synthetic", request_id=rid)
    assert replay["sent"] is None and len(chain.sent) == 1
    engine.reconcile()
    assert engine.authority.status(rid)["request"]["reserved_usd"] == "0"
    assert len(chain.sent) == 1


def test_crash_before_signing_binds_request_and_requires_no_send_reconcile(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    rid = str(uuid4())

    def crash(*args):
        raise SystemExit("synthetic crash")

    engine.key_loader = crash
    with pytest.raises(SystemExit):
        swap(engine, live=True, reason="synthetic", request_id=rid)
    assert Decimal(engine.authority.status(rid)["request"]["reserved_usd"]) > 0
    assert swap(engine, live=True, reason="synthetic", request_id=rid)["state"] == "unknown"
    assert chain.sent == []
    engine.reconcile()
    assert engine.authority.status(rid)["request"]["result"]["sent"] is False


def test_shared_portfolio_budget_counts_positions_fees_and_reserve(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    wallet = engine.authority
    wallet.register("1.4", [{"root": str(wallet.client), "aware": True}], True)
    report = __import__("executor.quote", fromlist=["fetch_report"]).fetch_report(
        cfg,
        engine.jup,
        __import__("executor.tokens", fromlist=["resolve"]).resolve("USDC"),
        __import__("executor.tokens", fromlist=["resolve"]).resolve("SOL"),
        1_000_000,
        50,
    )
    rid = str(uuid4())
    wallet.bind(rid, {"fixture": True})
    with pytest.raises(Refused, match="portfolio cap"):
        wallet.budget(report, 1_000_000_000, FEE, request_id=rid)


def test_aggregate_canonical_position_cap_across_homes_and_revisions(cfg, chain, owner, tmp_path, monkeypatch):
    cfg.mode = "live"
    engine = buyer(cfg, chain, owner)
    seed(engine, cost="24.5")
    other_root = tmp_path / "other-home"
    other = WalletAuthority(cfg, other_root)
    other.register("100", [{"root": str(other_root), "aware": True}], True)
    engine.root = other_root
    engine.authority = other
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    with pytest.raises(Refused, match="max_position_usd"):
        engine.swap("USDC", "SOL", "1", strategy="grid", live=True, reason="another config")
    assert chain.sent == []


def test_missing_authority_refuses_before_key_or_network(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    engine.authority.policy_path.unlink()
    engine.key_loader = lambda *args: pytest.fail("no key loading")
    with pytest.raises(Refused, match="policy missing"):
        swap(engine, live=True, reason="synthetic")
    assert chain.sent == [] and chain.simulations == 0


def test_missing_current_scope_certificate_refuses_without_key_load(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    engine.key_loader = lambda *args: pytest.fail("no key loading")
    with pytest.raises(Refused, match="certification unavailable"):
        manager.execute(engine, req)
    assert chain.sent == [] and chain.simulations == 0


def test_certified_fixture_dryrun_uses_real_verifier_but_never_signs(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    certify(engine, req)
    engine.key_loader = lambda *args: pytest.fail("dry-run never signs")
    result = manager.execute(engine, req)
    assert result["mode"] == "dry-run" and result["sent"] is False
    assert chain.sent == [] and chain.simulations == 1


@pytest.mark.parametrize(
    "change", ["config_hash", "strategy_version", "mints", "cost_model", "data_model", "timeframe", "owner_identity"]
)
def test_evidence_scope_transplant_refused(cfg, chain, owner, change):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    certify(engine, req)
    req["scope"][change] = "changed" if change != "timeframe" else 300
    with pytest.raises(Refused):
        manager.admit(engine, req)


@pytest.mark.parametrize("field,value", [("input_healthy", False), ("accounting_healthy", None), ("expires_at", 1)])
def test_unhealthy_or_stale_certificate_refused(cfg, chain, owner, field, value):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    path, cert = certify(engine, req)
    cert[field] = value
    path.write_text(json.dumps(cert))
    with pytest.raises(Refused):
        manager.admit(engine, req)


def test_path_validation_manager_bypass_and_non_atomic_execution_refused(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    req["scope"]["strategy"] = "path-validation"
    with pytest.raises(Refused, match="unsupported manager strategy"):
        manager.admit(engine, req)
    req["scope"]["strategy"] = "grid"
    req["scope"]["execution_model"] = "swap-v2"
    with pytest.raises(Refused, match="Swap v1"):
        manager.admit(engine, req)


def test_manager_live_fixture_replays_exact_original_receipt(cfg, chain, owner, monkeypatch):
    cfg.mode = "live"
    engine = buyer(cfg, chain, owner)
    req = request(engine, live=True)
    certify(engine, req)
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    receipt = manager.execute(engine, req)
    assert receipt["sent"] is True
    assert manager.execute(engine, req) == receipt
    assert len(chain.sent) == 1


def test_scoped_evidence_revoked_after_journaling_cannot_send(cfg, chain, owner, monkeypatch):
    cfg.mode = "live"
    engine = buyer(cfg, chain, owner)
    req = request(engine, live=True)
    path, cert = certify(engine, req)
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    append = engine.journal.append

    def revoke(kind, *args, **kwargs):
        result = append(kind, *args, **kwargs)
        if kind == "sending":
            cert["input_healthy"] = False
            path.write_text(json.dumps(cert))
        return result

    monkeypatch.setattr(engine.journal, "append", revoke)
    with pytest.raises(Refused, match="admission changed"):
        manager.execute(engine, req)
    assert chain.sent == []
    state = engine.authority.status(req["request_id"])["request"]
    assert state["reserved_usd"] == "0"
    assert state["result"]["sent"] is False


def test_crash_during_application_send_retains_reservation_and_no_retry(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    rid = str(uuid4())

    def crash(payload):
        chain.sent.append(payload)
        raise SystemExit("crash after application send")

    chain.send_transaction = crash
    with pytest.raises(SystemExit):
        swap(engine, live=True, reason="fixture", request_id=rid)
    assert engine.journal.unresolved()
    assert Decimal(engine.authority.status(rid)["request"]["reserved_usd"]) > 0
    assert swap(engine, live=True, reason="fixture", request_id=rid)["sent"] is None
    assert len(chain.sent) == 1
    engine.reconcile()
    assert engine.authority.status(rid)["request"]["reserved_usd"] == "0"
    assert len(chain.sent) == 1


def test_canonical_daily_loss_survives_bot_and_config_change(cfg, chain, owner, monkeypatch):
    cfg.mode = "live"
    engine = buyer(cfg, chain, owner)
    iid = "failed-" + uuid4().hex
    engine.journal.append("intent", iid, strategy="grid", side="buy", base_mint=WSOL_MINT, ts=engine.clock())
    engine.journal.append("sending", iid, signature=iid, ts=engine.clock())
    engine.journal.append(
        "result", iid, status="failed", signature=iid, fee_lamports=100_000_000, fee_usd="10", ts=engine.clock()
    )
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    with pytest.raises(Refused, match="daily_loss_stop_usd"):
        engine.swap(
            "USDC",
            "SOL",
            "1",
            strategy="grid",
            live=True,
            reason="new config",
            caller_context={"bot_id": str(uuid4()), "config_hash": "f" * 64},
        )
    assert chain.sent == []


def test_default_legacy_wallet_home_is_known_unaware_unless_reviewed(cfg, tmp_path, monkeypatch):
    legacy = tmp_path / "default-legacy"
    legacy.mkdir()
    monkeypatch.setattr(authority, "default_client_root", lambda: legacy)
    wallet = WalletAuthority(cfg, tmp_path / "home")
    wallet.register("100", [{"root": str(wallet.client), "aware": True}], True)
    with pytest.raises(Refused, match="unaware"):
        wallet.check()


def test_home_environment_cannot_choose_another_wallet_namespace(cfg, monkeypatch):
    monkeypatch.undo()
    before = authority.wallet_root(cfg.owner)
    monkeypatch.setenv("HOME", "/tmp/untrusted-home")
    assert authority.wallet_root(cfg.owner) == before


def test_unknown_legacy_open_risk_cannot_be_relabelled_as_new_family(cfg, chain, owner, monkeypatch):
    cfg.mode = "live"
    engine = buyer(cfg, chain, owner)
    seed(engine, strategy="grid-old-bot", cost="1")
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    with pytest.raises(Refused, match="unclassified"):
        engine.swap("USDC", "SOL", "1", strategy="grid", live=True, reason="new bot")
    assert chain.sent == []


def test_reference_models_cannot_be_certified_into_live_compatibility(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    req["scope"]["data_model"] = "coinbase-usd-reference"
    certify(engine, req)
    with pytest.raises(Refused, match="reference"):
        manager.admit(engine, req)


def test_fabricated_digest_cannot_substitute_for_bound_receipt_bytes(cfg, chain, owner):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    path, cert = certify(engine, req)
    cert["research"]["receipt_digest"] = "f" * 64
    path.write_text(json.dumps(cert))
    with pytest.raises(Refused, match="receipt artifact unavailable"):
        manager.admit(engine, req)


@pytest.mark.parametrize("change", ["boolean_version", "unknown_metadata", "unknown_strategy"])
def test_strict_manager_request_schema_fails_closed(cfg, chain, owner, change):
    engine = buyer(cfg, chain, owner)
    req = request(engine)
    if change == "boolean_version":
        req["version"] = True
    elif change == "unknown_metadata":
        req["private"] = "not allowed"
    else:
        req["scope"]["strategy"] = {"malformed": True}
    with pytest.raises(Refused):
        manager.admit(engine, req)
    assert chain.sent == [] and chain.simulations == 0


def test_deleted_policy_cannot_be_reset_through_a_new_home(cfg, tmp_path):
    wallet = WalletAuthority(cfg, tmp_path / "home")
    wallet.policy_path.unlink()
    other = WalletAuthority(cfg, tmp_path / "new-home")
    with pytest.raises(Refused, match="refusing authority reset"):
        other.register("1000", [{"root": str(other.client), "aware": True}], True)
    with pytest.raises(Refused, match="retained requests"):
        other.status(str(uuid4()))


def test_manager_tracked_grid_exit_keeps_existing_exit_semantics(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    seed(engine, strategy="grid", cost="1", quantity=10_000_000)
    req = request(engine, live=True)
    req["scope"].update(
        strategy="grid",
        strategy_version="grid-ladder-v1",
        execution_model="trigger_ladder",
        mints=[WSOL_MINT, USDC_MINT],
    )
    req["swap"].update({"from": "SOL", "to": "USDC", "amount": "0.01", "exit": True})
    (engine.root / "KILL").write_text("fixture entry stop")
    assert manager.execute(engine, req)["sent"] is True
    assert len(chain.sent) == 1
