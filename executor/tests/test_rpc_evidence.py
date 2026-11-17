"""Synthetic RPC-boundary counterexamples. No sockets, signing or owner files."""

import base64
import copy

import pytest
from conftest import OTHER_MINT, delta_token, ix, jupiter_ix, make_tx, meta, swap_instructions, token_account
from test_txverify import AMOUNT, econ_setup, honest_sell_mods

from executor import txverify as tv
from executor.errors import RpcError, SendRejected
from executor.rpc import Rpc, _account
from executor.tokens import USDC_MINT, WSOL_MINT

OWNER = "11111111111111111111111111111111"


class Http:
    def __init__(self, result=None, envelope=None):
        self.result = result
        self.envelope = envelope
        self.calls = []

    def post_json(self, url, body):
        self.calls.append(body)
        if self.envelope is not None:
            return self.envelope(body)
        return {"jsonrpc": "2.0", "id": body["id"], "result": self.result}


@pytest.mark.parametrize(
    "value",
    [
        False,
        [],
        "absent",
        {},
        {"lamports": 0, "owner": OWNER, "data": ["!!!", "base64"]},
        {"lamports": 0, "owner": OWNER, "data": ["", "base58"]},
        {"lamports": True, "owner": OWNER, "data": ["", "base64"]},
        {"lamports": -1, "owner": OWNER, "data": ["", "base64"]},
        {"lamports": 0, "owner": "not-a-key", "data": ["", "base64"]},
        {"lamports": 0, "owner": OWNER, "data": ["", "base64", "extra"]},
    ],
)
def test_malformed_account_is_not_absence_or_zero(value):
    with pytest.raises(RpcError):
        _account(value)


def test_actual_absence_and_empty_system_account_remain_valid():
    assert _account(None) is None
    assert _account({"lamports": 0, "owner": OWNER, "data": ["", "base64"]}) == {
        "lamports": 0,
        "owner": OWNER,
        "data": b"",
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda b: {"id": b["id"], "result": 7},
        lambda b: {"jsonrpc": "2.0", "id": b["id"] + 1, "result": 7},
        lambda b: {"jsonrpc": "2.0", "id": True, "result": 7},
        lambda b: {"jsonrpc": "2.0", "id": b["id"], "result": 7, "error": None},
    ],
)
def test_read_and_submit_require_correlated_unambiguous_envelopes(change):
    for method in ("read", "send"):
        http = Http(envelope=change)
        rpc = Rpc("https://offline.invalid", http, sleep=lambda _: None)
        with pytest.raises(RpcError) as caught:
            rpc.call("synthetic", []) if method == "read" else rpc.send_transaction("synthetic")
        assert not isinstance(caught.value, SendRejected)
        assert len(http.calls) == 1


@pytest.mark.parametrize(
    "method,result,args",
    [
        ("balance", {"value": True}, [OWNER]),
        ("balance", {"value": -1}, [OWNER]),
        ("accounts", {"value": []}, [[OWNER]]),
        ("signature_statuses", {"value": []}, [["signature"]]),
        ("signature_statuses", {"value": ["confirmed"]}, [["signature"]]),
        ("block_height", 1.5, []),
        ("transaction", "found", ["signature"]),
        ("simulate", {"value": {"err": None, "accounts": []}}, ["synthetic", [OWNER], False, True]),
    ],
)
def test_malformed_results_are_recoverable_rpc_errors(method, result, args):
    with pytest.raises(RpcError):
        getattr(Rpc("https://offline.invalid", Http(result)), method)(*args)


def test_malformed_rpc_bytes_cannot_hide_an_unrelated_token_debit():
    chain, facts, exp, info = econ_setup(OWNER)
    victim = tv.ata_address(OWNER, OTHER_MINT)
    chain.state[victim] = token_account(OTHER_MINT, OWNER, 50_000_000)
    ixs = list(swap_instructions(OWNER, WSOL_MINT, USDC_MINT, AMOUNT))
    ixs[-2] = ix(
        tv.JUPITER_V6, jupiter_ix(OWNER, WSOL_MINT, USDC_MINT).data, meta(OWNER, True, False), meta(victim, False, True)
    )
    facts = tv.inspect_tx(make_tx(ixs, OWNER), {})
    problems, info = tv.check_static(facts, exp)
    assert problems == []
    honest_sell_mods(chain, OWNER)
    chain.mods[victim] = delta_token(-50_000_000, OTHER_MINT, OWNER)
    watch = tv.watch_list(facts, exp)
    before = chain.accounts(watch)
    after = chain.simulate("synthetic", watch, False, True)
    assert tv.check_economics(facts, exp, info, watch, before, after)[0]

    def raw(accounts):
        return [
            None
            if a is None
            else {
                "lamports": a["lamports"],
                "owner": a["owner"],
                "data": [base64.b64encode(a["data"]).decode(), "base64"],
            }
            for a in accounts
        ]

    pre, post = raw(before), raw(after["accounts"])
    for encoded in ("!!!", base64.b64encode(b"\0" * 164).decode()):
        broken_pre, broken_post = copy.deepcopy(pre), copy.deepcopy(post)
        idx = watch.index(victim)
        broken_pre[idx]["data"] = broken_post[idx]["data"] = [encoded, "base64"]

        class AccountsHttp(Http):
            def post_json(self, url, body, pre=broken_pre, post=broken_post):
                result = (
                    {"value": pre}
                    if body["method"] == "getMultipleAccounts"
                    else {"value": {"err": None, "accounts": post}}
                )
                return {"jsonrpc": "2.0", "id": body["id"], "result": result}

        rpc = Rpc("https://offline.invalid", AccountsHttp())
        try:
            parsed_pre = rpc.accounts(watch)
            parsed_post = rpc.simulate("synthetic", watch, False, True)
        except RpcError:
            continue
        assert tv.check_economics(facts, exp, info, watch, parsed_pre, parsed_post)[0]
