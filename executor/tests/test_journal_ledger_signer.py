import json
import os
import stat
from decimal import Decimal

import pytest
from conftest import write_keyfile
from solders.keypair import Keypair

from executor import ledger
from executor.errors import ExecutorError, WalletError
from executor.journal import Journal, require_clear
from executor.signer import check_key_file_mode, load_keypair
from executor.tokens import WSOL_MINT

# -- journal ---------------------------------------------------------------------------------------------------


def test_journal_is_append_only_fsynced_and_mode_600(tmp_path):
    j = Journal(tmp_path / "sub" / "journal.jsonl")
    a = j.append("intent", "a", strategy="s")
    b = j.append("sending", "a", signature="sig")
    assert (a["seq"], b["seq"]) == (1, 2)
    assert stat.S_IMODE(os.stat(j.path).st_mode) == 0o600
    first = j.path.read_text()
    j.append("result", "a", status="confirmed")
    assert j.path.read_text().startswith(first)  # earlier lines are never rewritten


def test_states_replay(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "abandoned")
    j.append("intent", "inflight")
    j.append("sending", "inflight", signature="s1")
    j.append("intent", "ambiguous")
    j.append("sending", "ambiguous", signature="s2")
    j.append("unknown", "ambiguous", signature="s2", reason="timeout")
    j.append("intent", "done")
    j.append("sending", "done", signature="s3")
    j.append("result", "done", status="confirmed")
    st = j.states()
    assert {k: v["state"] for k, v in st.items()} == {
        "abandoned": "intent", "inflight": "sending", "ambiguous": "unknown", "done": "result",
    }  # fmt: skip
    assert sorted(s["id"] for s in j.unresolved()) == ["ambiguous", "inflight"]


def test_unknown_blocks_until_reconciled_and_never_clears_itself(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "x")
    j.append("sending", "x", signature="s")
    j.append("unknown", "x", signature="s", reason="timeout")
    with pytest.raises(ExecutorError, match="unresolved") as ei:
        require_clear(j)
    assert ei.value.code == "refused"
    j.append("reconciled", "x", status="dropped")
    require_clear(j)


def test_a_late_unknown_does_not_reopen_a_terminal_state(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "x")
    j.append("sending", "x", signature="s")
    j.append("result", "x", status="confirmed")
    j.append("unknown", "x", signature="s", reason="late duplicate")
    assert j.states()["x"]["state"] == "result" and j.unresolved() == []


def test_torn_line_is_surfaced_not_skipped(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "a")
    with open(j.path, "a") as fh:
        fh.write('{"seq": 2, "kind": "sendi')  # a crash mid-write
    assert j.corrupt_lines() == 1
    with pytest.raises(ExecutorError, match="unparseable"):
        require_clear(j)
    assert j.states()["a"]["state"] == "intent"  # the intact records still read


def test_records_carry_no_key_material(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "a", reason="r")
    assert "key" not in j.path.read_text().lower().replace("keys", "")


# -- ledger ----------------------------------------------------------------------------------------------------


def trade(j, i, strategy, side, base_raw, usd, ts, fee="0"):
    iid = f"t{i}"
    j.append("intent", iid, ts=ts, strategy=strategy, side=side, base_mint=WSOL_MINT)
    j.append("sending", iid, ts=ts, signature=f"s{i}")
    j.append(
        "result", iid, ts=ts, status="confirmed", signature=f"s{i}", base_raw=base_raw, quote_usd=str(usd), fee_usd=fee
    )


def test_average_cost_positions_and_realized_pnl(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    t = 1_800_000_000
    trade(j, 1, "s", "buy", 1_000_000_000, 100, t)  # 1 SOL for $100
    trade(j, 2, "s", "buy", 1_000_000_000, 120, t + 1)  # 1 SOL for $120: average cost $110
    trade(j, 3, "s", "sell", 1_000_000_000, 130, t + 2, fee="0.5")  # sell 1 SOL for $130: realized +$20, fee $0.5
    st = j.states()
    pos = ledger.positions(st, "s")[WSOL_MINT]
    assert pos.qty_raw == 1_000_000_000 and pos.cost_usd == Decimal(110)
    assert ledger.realized_pnl_usd(st, ledger.utc_day(t), "s") == Decimal("19.5")
    assert ledger.positions(st, "other") == {}


def test_failed_and_unknown_trades_do_not_count(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "a", ts=1, strategy="s", side="buy", base_mint=WSOL_MINT)
    j.append("sending", "a", ts=1, signature="x")
    j.append("result", "a", ts=2, status="failed", error="InstructionError")
    j.append("intent", "b", ts=3, strategy="s", side="buy", base_mint=WSOL_MINT)
    j.append("sending", "b", ts=3, signature="y")
    j.append("unknown", "b", ts=4, signature="y", reason="timeout")
    assert ledger.positions(j.states(), "s") == {}


def test_a_sell_beyond_the_tracked_quantity_realizes_no_phantom_profit(tmp_path):
    j = Journal(tmp_path / "j.jsonl")
    trade(j, 1, "s", "sell", 1_000_000_000, 90, 1_800_000_000)  # only possible for the validation strategy
    assert ledger.realized_pnl_usd(j.states(), ledger.utc_day(1_800_000_000), "s") == Decimal(0)


# -- signer ----------------------------------------------------------------------------------------------------


def test_key_file_must_be_mode_600(tmp_path, owner_kp, owner):
    path = tmp_path / "k.json"
    write_keyfile(path, owner_kp, 0o600)
    assert load_keypair(str(path), owner).pubkey() == owner_kp.pubkey()
    for bad in (0o640, 0o644, 0o604, 0o660, 0o777):
        path.chmod(bad)
        with pytest.raises(WalletError, match="mode 600"):
            load_keypair(str(path), owner)
    path.chmod(0o400)  # stricter is fine
    check_key_file_mode(path)


def test_key_file_must_match_the_configured_owner(tmp_path, owner_kp):
    path = tmp_path / "k.json"
    write_keyfile(path, owner_kp)
    other = str(Keypair.from_seed(bytes([9] * 32)).pubkey())
    with pytest.raises(WalletError, match="does not match the configured owner"):
        load_keypair(str(path), other)


def test_base58_key_format_and_garbage(tmp_path, owner_kp, owner):
    path = tmp_path / "k.b58"
    path.write_text(str(owner_kp) + "\n")
    path.chmod(0o600)
    assert load_keypair(str(path), owner).pubkey() == owner_kp.pubkey()
    path.write_text("not a key")
    with pytest.raises(WalletError, match="not a valid Solana keypair"):
        load_keypair(str(path), owner)


def test_errors_never_contain_key_bytes(tmp_path, owner_kp, owner):
    path = tmp_path / "k.json"
    path.write_text(json.dumps(list(bytes(owner_kp))[:63]))  # truncated
    path.chmod(0o600)
    with pytest.raises(WalletError) as ei:
        load_keypair(str(path), owner)
    secret_markers = [str(owner_kp), json.dumps(list(bytes(owner_kp)))[:40]]
    assert not any(m in str(ei.value) for m in secret_markers)


def test_symlink_and_directory_and_foreign_paths_are_refused(tmp_path, owner_kp, owner):
    real = tmp_path / "real.json"
    write_keyfile(real, owner_kp)
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(WalletError):
        load_keypair(str(link), owner)  # O_NOFOLLOW: a swapped-in symlink is refused
    with pytest.raises(WalletError):
        load_keypair(str(tmp_path), owner)
    with pytest.raises(WalletError, match="not readable"):
        load_keypair(str(tmp_path / "missing.json"), owner)
