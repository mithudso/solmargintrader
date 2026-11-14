"""Unsigned Jupiter previews, structural checks and conservative historic recovery."""
from __future__ import annotations

import base64
import json
import struct
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from executor import txverify
from soltui import jupiter_manual as jm
from soltui import jupiter_tokens

OWNER_KEYPAIR = Keypair()
OWNER = str(OWNER_KEYPAIR.pubkey())
OTHER_MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK-like test mint


def make_test_tx(instructions: list[Instruction], payer: str, signers: list[Keypair] | None = None) -> str:
    msg = Message.new_with_blockhash(instructions, Pubkey.from_string(payer), Hash.default())
    tx = VersionedTransaction(msg, signers or [OWNER_KEYPAIR])
    return base64.b64encode(bytes(tx)).decode("utf-8")


def valid_swap_ixs(owner: str, mint_in: str, mint_out: str, amount_in: int) -> list[Instruction]:
    cu_lim = Instruction(Pubkey.from_string(txverify.COMPUTE_BUDGET), bytes([2]) + struct.pack("<I", 100_000), [])
    cu_prc = Instruction(Pubkey.from_string(txverify.COMPUTE_BUDGET), bytes([3]) + struct.pack("<Q", 50_000), [])
    wsol_ata = txverify.ata_address(owner, jm.WSOL_MINT)
    ata_ix = Instruction(
        Pubkey.from_string(txverify.ATA_PROGRAM),
        b"\x01",
        [
            AccountMeta(Pubkey.from_string(owner), True, True),
            AccountMeta(Pubkey.from_string(wsol_ata), False, True),
            AccountMeta(Pubkey.from_string(owner), False, False),
            AccountMeta(Pubkey.from_string(jm.WSOL_MINT), False, False),
            AccountMeta(Pubkey.from_string(txverify.SYSTEM_PROGRAM), False, False),
            AccountMeta(Pubkey.from_string(txverify.TOKEN_PROGRAM), False, False),
        ]
    )
    # Valid ExactIn discriminator (e517cb977ae3ad2a)
    jup_route = (bytes.fromhex("e517cb977ae3ad2a") + struct.pack("<I", 1)
                 + bytes([48, 100, 0, 1]) + struct.pack("<QQHB", amount_in, int(amount_in * 0.99), 0, 0))
    jup_ix = Instruction(
        Pubkey.from_string(txverify.JUPITER_V6),
        jup_route,
        [
            AccountMeta(Pubkey.from_string(owner), True, False),
            AccountMeta(Pubkey.from_string(txverify.ata_address(owner, mint_in)), False, True),
            AccountMeta(Pubkey.from_string(txverify.ata_address(owner, mint_out)), False, True),
        ]
    )
    return [cu_lim, cu_prc, ata_ix, jup_ix]


class MockHttpClient:
    def __init__(self, owner: str):
        self.owner = owner
        self.sol_balance = 1_000_000_000  # 1 SOL
        self.spl_balance = 500_000_000  # 500 USDC
        self.execute_status = "Success"
        self.execute_error = None
        self.execute_timeout = False
        self.simulated_tx_b64: str | None = None
        self.calls: list[tuple[str, Any]] = []

    def rpc(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("rpc", body))
        method = body.get("method")
        params = body.get("params", [])
        if method == "getBalance":
            return {"result": {"value": self.sol_balance}}
        if method == "getTokenAccountsByOwner":
            mint = (params[1] if len(params) > 1 else {}).get("mint")
            return {
                "result": {
                    "value": [
                        {
                            "account": {
                                "data": {
                                    "parsed": {
                                        "info": {
                                            "mint": mint,
                                            "tokenAmount": {
                                                "amount": str(self.spl_balance),
                                                "decimals": 6,
                                                "uiAmount": self.spl_balance / 1e6
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        if method == "getMultipleAccounts":
            return {"result": {"value": []}}
        if method == "getSignatureStatuses":
            return {"result": {"value": [{"confirmationStatus": "confirmed", "err": None}]}}
        raise NotImplementedError(method)

    def get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("get", url, params))
        in_amt = int(params["amount"])
        out_amt = int(in_amt * 0.99)
        tx_b64 = self.simulated_tx_b64 or make_test_tx(
            valid_swap_ixs(self.owner, params["inputMint"], params["outputMint"], in_amt),
            self.owner
        )
        return {
            "transaction": tx_b64,
            "requestId": "req-123",
            "inAmount": str(in_amt),
            "outAmount": str(out_amt),
            "otherAmountThreshold": str(out_amt),
            "priceImpactPct": "0.001",
            "routePlan": [{"swapInfo": {"label": "Raydium"}}],
        }

    def post(self, url: str, json: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("post", url, json))
        if self.execute_timeout:
            raise TimeoutError("connection timed out")
        if self.execute_status == "Success":
            return {"status": "Success", "signature": "5Hx...validSignature"}
        return {"status": "Failed", "error": self.execute_error or "simulation failed"}


class JupiterManualOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p_dir = mock.patch.object(jm, "_storage_dir", return_value=Path(self.tmp.name))
        p_dir.start()
        self.addCleanup(p_dir.stop)

        self.key_path = Path(self.tmp.name) / "never-read.private"

        self.http = MockHttpClient(OWNER)

    def preview(self, product="SOL-USDC", side="BUY", size="1", unit="quote"):
        params = {"product_id": product, "side": side, "size": size, "size_currency": unit}
        return jm.order_preview(params, OWNER, http_client=self.http)

    def test_preview_validates_and_persists_unexpired_preview(self):
        res = self.preview()
        self.assertEqual(res["venue"], "jupiter")
        self.assertEqual(res["side"], "BUY")
        self.assertTrue(res["preview_id"])
        self.assertGreater(res["expires_at"], time.time())

        # Verify disk record
        path = jm._preview_path(res["preview_id"])
        self.assertTrue(path.is_file())
        rec = jm._read(path)
        self.assertEqual(rec["state"], "preview")
        self.assertEqual(rec["taker"], OWNER)

    def test_zero_decimals_preserved_and_missing_decimals_refused(self):
        with mock.patch.object(jupiter_tokens, "resolve", return_value={
            "mint": OTHER_MINT, "symbol": "BONK", "name": "Bonk", "decimals": 0, "verified": True, "usdPrice": 0.00001
        }):
            res = jm.order_preview({"product_id": "BONK-USDC", "side": "SELL", "size": "100", "size_currency": "base"},
                                   OWNER, http_client=self.http)
            self.assertEqual(res["side"], "SELL")

        with mock.patch.object(jupiter_tokens, "resolve", return_value={
            "mint": OTHER_MINT, "symbol": "BAD", "name": "Bad", "decimals": None, "verified": True
        }):
            with self.assertRaisesRegex(ValueError, "decimal precision"):
                jm.order_preview({"product_id": "BAD-USDC", "side": "SELL", "size": "1", "size_currency": "base"},
                                 OWNER, http_client=self.http)

    def test_unverified_token_is_refused(self):
        with mock.patch.object(jupiter_tokens, "resolve", return_value={
            "mint": OTHER_MINT, "symbol": "UNVER", "name": "Unverified", "decimals": 6, "verified": False
        }):
            with self.assertRaisesRegex(ValueError, "not verified"):
                jm.order_preview({"product_id": "UNVER-USDC", "side": "SELL", "size": "1", "size_currency": "base"},
                                 OWNER, http_client=self.http)

    def test_missing_usd_price_on_buy_base_sizing_refused(self):
        with mock.patch.object(jupiter_tokens, "resolve", return_value={
            "mint": OTHER_MINT, "symbol": "NO_PRICE", "name": "No Price", "decimals": 6, "verified": True, "usdPrice": None
        }):
            with self.assertRaisesRegex(ValueError, "verified price"):
                jm.order_preview({"product_id": "NO_PRICE-USDC", "side": "BUY", "size": "10", "size_currency": "base"},
                                 OWNER, http_client=self.http)

    def test_max_quote_cap_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.preview(size="101", unit="quote")

    def test_insufficient_sol_reserve_refused(self):
        self.http.sol_balance = 2_000_000  # < 0.005 SOL
        with self.assertRaisesRegex(ValueError, "Insufficient SOL balance"):
            self.preview(size="1", unit="quote")

    def test_insufficient_spl_token_balance_refused(self):
        self.http.spl_balance = 500  # < 1 USDC (1,000,000 raw)
        with self.assertRaisesRegex(ValueError, "Insufficient USDC balance"):
            self.preview(size="1", unit="quote")

    def test_structural_verification_catches_unauthorized_program(self):
        # Create a malicious transaction with an unknown program (drain attempt)
        bad_ix = Instruction(Pubkey.from_string("11111111111111111111111111111112"), b"\x00", [
            AccountMeta(Pubkey.from_string(OWNER), True, True)
        ])
        malicious_tx = make_test_tx(
            valid_swap_ixs(OWNER, jm.USDC_MINT, jm.WSOL_MINT, 1_000_000) + [bad_ix],
            OWNER
        )
        self.http.simulated_tx_b64 = malicious_tx
        with self.assertRaisesRegex(ValueError, "structural safety verification"):
            self.preview()

    def test_structural_verification_catches_wrong_fee_payer(self):
        other_payer = Keypair()
        bad_tx = make_test_tx(
            valid_swap_ixs(OWNER, jm.USDC_MINT, jm.WSOL_MINT, 1_000_000),
            str(other_payer.pubkey()),
            [other_payer, OWNER_KEYPAIR]
        )
        self.http.simulated_tx_b64 = bad_tx
        with self.assertRaisesRegex(ValueError, "structural safety verification"):
            self.preview()

    def test_submit_remains_disabled_without_reading_a_key(self):
        prev = self.preview()
        for _ in range(2):
            with mock.patch.object(jm, "load_keypair") as load:
                with self.assertRaisesRegex(ValueError, "economic verification"):
                    jm.order_submit(prev["preview_id"], str(self.key_path), OWNER, http_client=self.http)
                load.assert_not_called()
        self.assertEqual(jm._read(jm._preview_path(prev["preview_id"]))["state"], "preview")
        self.assertFalse(any(c[0] == "post" for c in self.http.calls))

    def test_historical_unknown_state_blocks_further_orders(self):
        prev = self.preview()
        path = jm._preview_path(prev["preview_id"])
        record = jm._read(path)
        record.update(state="unknown", submit_started_at=1)
        jm._save(path, record)
        self.assertTrue(jm.state()["unresolved"])
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.preview()

    def test_reconcile_resolves_historical_unknown_order_from_chain_evidence(self):
        prev = self.preview()
        path = jm._preview_path(prev["preview_id"])
        record = jm._read(path)
        record.update(state="unknown", signature="sig123", submit_started_at=1)
        jm._save(path, record)
        rec_result = jm.order_reconcile("sig123", http_client=self.http)
        self.assertEqual(rec_result["status"], "FILLED")
        self.assertFalse(rec_result["unresolved"])


if __name__ == "__main__":
    unittest.main()
