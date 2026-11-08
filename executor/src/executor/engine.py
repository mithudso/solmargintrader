"""The swap pipeline. Dry-run and live share every step up to the signature, so dry-run simulates exactly what live
would send (the same pattern as liquidity's Rebalancer/Runner).

    resolve -> quote + independent price -> rails -> /swap -> decode -> VERIFY (static) -> pre-state -> simulate
    -> VERIFY (economic)  ........ dry-run stops here ........
    -> load key (mode 600, owner match) -> sign -> re-check message -> fresh pre-state -> re-simulate the signed tx
    -> re-check rails -> journal intent -> journal sending (signature) -> send ONCE -> confirm -> read the chain
    -> verify post-trade balances -> journal result

Failure semantics:
  * anything before `sending` is journalled nowhere but returned as a refusal: nothing was sent;
  * a definite node rejection after `sending` is recorded as a failed result (the tx was not accepted);
  * any other send or confirmation problem is `unknown`: it may have landed. It is never retried; `reconcile`
    asks the chain.
"""

from __future__ import annotations

import fcntl
import os
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from solders.transaction import VersionedTransaction

from . import gates, lifi, rails, txverify
from .config import Config, home
from .errors import Ambiguous, BadParams, ExecutorError, Refused, RpcError, SendRejected
from .http import Http, HttpxHttp
from .journal import Journal
from .jupiter import Jupiter
from .quote import QuoteReport, fetch_report
from .rpc import Rpc
from .signer import load_keypair
from .tokens import QUOTE_MINT, WSOL_MINT, Token, raw_to_ui, resolve, ui_to_raw

LOOKUP_TABLE_PROGRAM = "AddressLookupTab1e1111111111111111111111111"
BLOCKHASH_MARGIN = 25  # refuse to send when fewer than this many blocks remain in the blockhash's life


class Engine:
    def __init__(
        self,
        cfg: Config,
        root: Path | None = None,
        http: Http | None = None,
        rpc: Rpc | None = None,
        jup: Jupiter | None = None,
        clock=time.time,
        sleep=time.sleep,
        key_loader=load_keypair,
    ):
        self.cfg = cfg
        self.root = root or home()
        http = http or HttpxHttp()
        self.http = http
        self.rpc = rpc or Rpc(cfg.rpc_url, http)
        self.jup = jup or Jupiter(cfg.jupiter_base_url, http)
        self.journal = Journal(self.root / "journal.jsonl")
        self.clock = clock
        self.sleep = sleep
        self.key_loader = key_loader

    # -- quote ---------------------------------------------------------------------------------------------

    def quote(
        self, frm: str, to: str, amount: str, to_chain: str | None = None, slippage_bps: int | None = None
    ) -> dict:
        token_in = resolve(frm)
        in_raw = ui_to_raw(amount, token_in.decimals)
        if to_chain and to_chain.lower() not in ("solana", "sol"):
            return lifi.quote_cross_chain(self.cfg, self.http, self.cfg.owner, token_in, in_raw, to_chain, to)
        token_out = resolve(to)
        report = fetch_report(self.cfg, self.jup, token_in, token_out, in_raw, self._slippage(slippage_bps))
        return {"venue": "jupiter-swap-v1", "chain": "solana", **report.to_dict()}

    def _slippage(self, requested: int | None) -> int:
        cap = self.cfg.rails.max_slippage_bps
        if requested is None:
            return cap
        if not isinstance(requested, int) or isinstance(requested, bool) or requested <= 0:
            raise BadParams("slippage_bps must be a positive integer")
        if requested > cap:
            raise Refused(f"slippage_bps {requested} exceeds max_slippage_bps {cap}; the executor only tightens it")
        return requested

    # -- swap ----------------------------------------------------------------------------------------------

    def swap(
        self,
        frm: str,
        to: str,
        amount: str,
        strategy: str | None = None,
        live: bool = False,
        exit_only: bool = False,
        reason: str | None = None,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        token_in, token_out = resolve(frm), resolve(to)
        in_raw = ui_to_raw(amount, token_in.decimals)
        slip = self._slippage(slippage_bps)
        if live and not (reason and reason.strip()):
            raise BadParams("a live swap needs a reason: it is written to the journal before sending")
        if strategy is not None and not strategy.strip():
            raise BadParams("strategy may not be blank")
        with self._swap_lock():
            return self._swap_locked(
                token_in, token_out, in_raw, strategy, live, exit_only, (reason or "").strip(), slip
            )

    def _swap_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        engine = self

        class _Lock:
            def __enter__(self):
                self.fd = os.open(engine.root / "swap.lock", os.O_WRONLY | os.O_CREAT, 0o600)
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    os.close(self.fd)
                    raise Refused("another swap is in progress") from None
                return self

            def __exit__(self, *exc):
                os.close(self.fd)  # closing releases the flock

        return _Lock()

    def _swap_locked(
        self, token_in: Token, token_out: Token, in_raw: int, strategy, live, exit_only, reason, slip
    ) -> dict:
        cfg = self.cfg
        now = self.clock()
        report = fetch_report(cfg, self.jup, token_in, token_out, in_raw, slip, now)
        if report.sol_price_usd is None:
            raise Refused("no SOL price reference to value network fees; refusing rather than guessing")
        native = self.rpc.balance(cfg.owner)
        decision = rails.check_trade(
            cfg, self.root, self.journal, report,
            strategy=strategy, live=live, exit_only=exit_only,
            kill_present=(self.root / "KILL").exists(), native_lamports=native, now=now,
        )  # fmt: skip
        built = self.jup.build_swap(report.quote, cfg.owner, cfg.rails.max_priority_fee_lamports)
        tx = txverify.decode_b64(built["swapTransaction"])
        facts = self._facts(tx)
        exp = txverify.Expectation(
            cfg.owner, token_in.mint, token_out.mint, in_raw, report.quote.min_out_raw,
            cfg.rails.max_priority_fee_lamports, cfg.rails.min_sol_reserve_lamports,
        )  # fmt: skip
        problems, info = txverify.check_static(facts, exp)
        if problems:
            raise Refused([f"verifier: {p}" for p in problems])
        econ, evidence = self._simulate_and_check(tx, facts, exp, info, built["swapTransaction"], sig_verify=False)
        base_evidence = {
            "quote": report.to_dict(),
            "decision": decision.to_dict(),
            "static": info,
            "economic": evidence,
            "message_sha256": txverify.message_hash(tx),
            "last_valid_block_height": built["lastValidBlockHeight"],
        }
        if econ:
            raise Refused([f"verifier: {p}" for p in econ])
        if not live:
            if strategy:
                gates.record_dry_run(self.root, cfg, strategy, now)
            self.journal.append("dry_run", f"dry-{uuid.uuid4().hex[:12]}", strategy=strategy, side=decision.side,
                                in_usd=str(round(report.in_usd, 6)), message_sha256=base_evidence["message_sha256"])  # fmt: skip
            return {"mode": "dry-run", "sent": False, "would_send": True, "strategy": strategy, **base_evidence}
        return self._send_live(
            tx, facts, exp, info, report, decision, strategy, reason, built, base_evidence, exit_only
        )

    def _facts(self, tx: VersionedTransaction) -> txverify.TxFacts:
        facts = txverify.inspect_tx(tx, {})
        if facts.lookup_tables:
            accs = self.rpc.accounts(facts.lookup_tables)
            tables: dict[str, list[str]] = {}
            for key, acc in zip(facts.lookup_tables, accs, strict=True):
                if acc is None or acc["owner"] != LOOKUP_TABLE_PROGRAM:
                    raise Refused(f"verifier: lookup table {key} is missing or not owned by the lookup-table program")
                tables[key] = txverify.lookup_table_addresses(acc["data"])
            facts = txverify.inspect_tx(tx, tables)
        return facts

    def _simulate_and_check(self, tx, facts, exp, info, tx_b64: str, sig_verify: bool):
        watch = txverify.watch_list(facts, exp)
        pre = self.rpc.accounts(watch)
        sim = self.rpc.simulate(tx_b64, watch, sig_verify=sig_verify, replace_blockhash=not sig_verify)
        return txverify.check_economics(facts, exp, info, watch, pre, sim)

    # -- live path -----------------------------------------------------------------------------------------

    def _send_live(
        self, tx, facts, exp, info, report: QuoteReport, decision, strategy, reason, built, base_evidence, exit_only
    ):
        import base64

        cfg = self.cfg
        kp = self.key_loader(cfg.key_file, cfg.owner)
        signed = VersionedTransaction(tx.message, [kp])
        if txverify.message_hash(signed) != base_evidence["message_sha256"]:
            raise Refused("signing changed the message; refusing")
        signature = str(signed.signatures[0])
        signed_b64 = base64.b64encode(bytes(signed)).decode()
        # Re-simulate the EXACT signed bytes with signature verification, on fresh pre-state.
        problems, evidence2 = self._simulate_and_check(signed, facts, exp, info, signed_b64, sig_verify=True)
        if problems:
            raise Refused([f"verifier (signed tx): {p}" for p in problems])
        age = self.clock() - report.fetched_at
        if age > cfg.rails.max_quote_age_s:
            raise Refused(f"quote is {age:.1f} s old, over max_quote_age_s {cfg.rails.max_quote_age_s:g}")
        if (self.root / "KILL").exists() and not exit_only:
            raise Refused("KILL file appeared while the swap was being prepared")
        height = self.rpc.block_height()
        if built["lastValidBlockHeight"] - height < BLOCKHASH_MARGIN:
            raise Refused("the blockhash is about to expire; try again")
        # Re-run the position rails against the journal as it is NOW (a concurrent writer cannot have raced past the lock).
        rails.check_trade(
            cfg, self.root, self.journal, report, strategy=strategy, live=True, exit_only=exit_only,
            kill_present=(self.root / "KILL").exists(), native_lamports=self.rpc.balance(cfg.owner), now=self.clock(),
        )  # fmt: skip

        intent_id = f"swap-{int(self.clock())}-{uuid.uuid4().hex[:8]}"
        base_raw, quote_usd = self._base_and_quote(decision.side, report)
        self.journal.append(
            "intent", intent_id,
            strategy=strategy, side=decision.side, base_mint=decision.base_mint, exit=exit_only, reason=reason,
            from_mint=report.token_in.mint, to_mint=report.token_out.mint, in_raw=report.quote.in_raw,
            min_out_raw=report.quote.min_out_raw, in_usd=str(round(report.in_usd, 6)),
            sol_price_usd=str(report.sol_price_usd), evidence={**base_evidence, "signed_check": evidence2},
            gate_notes=list(decision.notes), expected_base_raw=base_raw, expected_quote_usd=quote_usd,
        )  # fmt: skip
        self.journal.append(
            "sending", intent_id, signature=signature, last_valid_block_height=built["lastValidBlockHeight"]
        )
        try:
            sent_sig = self.rpc.send_transaction(signed_b64)
        except SendRejected as exc:
            self.journal.append("result", intent_id, status="rejected", signature=signature, error=exc.message)
            raise ExecutorError(
                f"the node rejected the transaction (nothing landed): {exc.message}", "failed"
            ) from None
        except Exception as exc:  # noqa: BLE001 - transport errors, timeouts: the outcome is unknown
            self.journal.append("unknown", intent_id, signature=signature, reason=f"send raised {type(exc).__name__}")
            raise Ambiguous(
                f"send outcome unknown for {signature}; it was NOT retried. Run `executor reconcile`"
            ) from None
        if sent_sig != signature:
            self.journal.append("unknown", intent_id, signature=signature, reason="node returned a different signature")
            raise Ambiguous(f"node returned signature {sent_sig}, expected {signature}; run `executor reconcile`")

        status = self._confirm(signature)
        if status is None:
            self.journal.append("unknown", intent_id, signature=signature, reason="not confirmed within the timeout")
            raise Ambiguous(
                f"{signature} was not confirmed in {cfg.rails.confirm_timeout_s:g} s; it may still land. Run `executor reconcile`"
            )
        if status.get("err") is not None:
            self.journal.append("result", intent_id, status="failed", signature=signature, error=str(status["err"]))
            raise ExecutorError(f"transaction {signature} failed on chain: {status['err']}", "failed")
        realized = self._read_realized(
            signature, report.token_in, report.token_out, evidence2.get("retained_rent_lamports", 0)
        )
        if realized is None:
            self.journal.append("unknown", intent_id, signature=signature, reason="confirmed but balances unreadable")
            raise Ambiguous(f"{signature} confirmed but its balances could not be read; run `executor reconcile`")
        outcome = self._outcome_fields(
            decision.side,
            report.token_in,
            report.token_out,
            realized,
            report.sol_price_usd,
            report.quote.min_out_raw,
            report.quote.in_raw,
        )
        self.journal.append("result", intent_id, status="confirmed", signature=signature, **outcome)
        if not outcome["post_verify_ok"]:
            (self.root / "KILL").write_text(f"auto-kill: post-trade check failed for {signature}\n")
        return {
            "mode": "live", "sent": True, "id": intent_id, "signature": signature, "strategy": strategy, "reason": reason,
            "post_verify_ok": outcome["post_verify_ok"], "in_raw": outcome["in_raw"], "out_raw": outcome["out_raw"],
            "fee_lamports": outcome["fee_lamports"], **base_evidence,
        }  # fmt: skip

    def _base_and_quote(self, side, report: QuoteReport):
        if side == "buy":
            return report.quote.out_raw, str(raw_to_ui(report.quote.in_raw, report.token_in.decimals))
        if side == "sell":
            return report.quote.in_raw, str(raw_to_ui(report.quote.out_raw, report.token_out.decimals))
        return None, None

    def _confirm(self, signature: str) -> dict[str, Any] | None:
        deadline = self.clock() + self.cfg.rails.confirm_timeout_s
        while self.clock() < deadline:
            try:
                st = self.rpc.signature_statuses([signature])[0]
            except RpcError:
                st = None
            if st and (st.get("err") is not None or st.get("confirmationStatus") in ("confirmed", "finalized")):
                return st
            self.sleep(1.0)
        return None

    def _read_realized(self, signature: str, token_in: Token, token_out: Token, retained_rent: int):
        for _ in range(8):
            try:
                tx = self.rpc.transaction(signature)
            except RpcError:
                tx = None
            if tx:
                return realized_from_meta(tx, self.cfg.owner, token_in, token_out, retained_rent)
            self.sleep(1.5)
        return None

    @staticmethod
    def _outcome_fields(
        side, token_in: Token, token_out: Token, realized: dict, sol_price: Decimal, min_out_raw: int, in_raw: int
    ):
        in_actual, out_actual = realized["in_raw"], realized["out_raw"]
        ok = in_actual == in_raw and out_actual >= min_out_raw
        base_raw = out_actual if side == "buy" else in_actual
        quote_amt = raw_to_ui(in_actual if side == "buy" else out_actual, 6)
        fee_usd = raw_to_ui(realized["fee_lamports"], 9) * sol_price
        return {
            "in_raw": in_actual, "out_raw": out_actual, "fee_lamports": realized["fee_lamports"],
            "base_raw": base_raw if side else 0, "quote_usd": str(quote_amt if side else Decimal(0)),
            "fee_usd": str(fee_usd), "post_verify_ok": ok, "slot": realized.get("slot"),
        }  # fmt: skip

    # -- reconcile -----------------------------------------------------------------------------------------

    def reconcile(self) -> dict[str, Any]:
        """Resolve every unknown send from the chain. The only way to clear the block; never re-sends anything."""
        out: list[dict[str, Any]] = []
        for st in self.journal.unresolved():
            iid = st["id"]
            sending = st.get("sending") or {}
            unk = st.get("unknown") or {}
            signature = sending.get("signature") or unk.get("signature")
            intent = st.get("intent") or {}
            if not signature:
                out.append({"id": iid, "outcome": "unresolvable", "why": "no signature was journalled"})
                continue
            status = self.rpc.signature_statuses([signature])[0]
            if status and status.get("err") is not None:
                self.journal.append("reconciled", iid, status="failed", signature=signature, error=str(status["err"]))
                out.append({"id": iid, "signature": signature, "outcome": "failed_on_chain"})
            elif status and status.get("confirmationStatus") in ("confirmed", "finalized"):
                token_in, token_out = _tokens(intent)
                evidence = (intent.get("evidence") or {}).get("signed_check") or {}
                realized = None
                tx = self.rpc.transaction(signature)
                if tx:
                    realized = realized_from_meta(
                        tx, self.cfg.owner, token_in, token_out, evidence.get("retained_rent_lamports", 0)
                    )
                if realized is None:
                    out.append(
                        {
                            "id": iid,
                            "signature": signature,
                            "outcome": "still_unknown",
                            "why": "transaction not readable yet",
                        }
                    )
                    continue
                sol_price = Decimal(intent.get("sol_price_usd") or "0")
                if sol_price <= 0:
                    out.append(
                        {
                            "id": iid,
                            "signature": signature,
                            "outcome": "still_unknown",
                            "why": "no recorded SOL price for fees",
                        }
                    )
                    continue
                fields = self._outcome_fields(
                    intent.get("side"),
                    token_in,
                    token_out,
                    realized,
                    sol_price,
                    int(intent["min_out_raw"]),
                    int(intent["in_raw"]),
                )
                self.journal.append("reconciled", iid, status="confirmed", signature=signature, **fields)
                if not fields["post_verify_ok"]:
                    (self.root / "KILL").write_text(
                        f"auto-kill: reconciled trade {signature} did not match its quote\n"
                    )
                out.append(
                    {
                        "id": iid,
                        "signature": signature,
                        "outcome": "confirmed",
                        "post_verify_ok": fields["post_verify_ok"],
                    }
                )
            else:
                lvbh = sending.get("last_valid_block_height")
                height = self.rpc.block_height()
                if isinstance(lvbh, int) and height > lvbh + 150:
                    self.journal.append("reconciled", iid, status="dropped", signature=signature,
                                        why=f"not on chain and block height {height} is past {lvbh}")  # fmt: skip
                    out.append({"id": iid, "signature": signature, "outcome": "dropped"})
                else:
                    out.append({"id": iid, "signature": signature, "outcome": "still_unknown",
                                "why": "not found yet and the blockhash may still be valid"})  # fmt: skip
        return {"checked": len(out), "results": out, "still_blocking": len(self.journal.unresolved())}


def _tokens(intent: dict[str, Any]) -> tuple[Token, Token]:
    return resolve(intent["from_mint"]), resolve(intent["to_mint"])


def realized_from_meta(
    tx: dict[str, Any], owner: str, token_in: Token, token_out: Token, retained_rent: int
) -> dict[str, Any] | None:
    """Exact owner deltas of a confirmed transaction, from its metadata. None when the metadata is unusable."""
    meta = tx.get("meta")
    msg = (tx.get("transaction") or {}).get("message") or {}
    if not meta or meta.get("err") is not None:
        return None
    keys = list(msg.get("accountKeys") or [])
    loaded = meta.get("loadedAddresses") or {}
    keys += list(loaded.get("writable") or []) + list(loaded.get("readonly") or [])
    keys = [k if isinstance(k, str) else k.get("pubkey") for k in keys]
    if owner not in keys:
        return None
    idx = keys.index(owner)
    try:
        native_delta = int(meta["postBalances"][idx]) - int(meta["preBalances"][idx])
        fee = int(meta["fee"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    def token_total(entries, mint) -> int:
        return sum(
            int(e["uiTokenAmount"]["amount"])
            for e in entries or []
            if e.get("owner") == owner and e.get("mint") == mint
        )

    def spl_delta(mint: str) -> int:
        return token_total(meta.get("postTokenBalances"), mint) - token_total(meta.get("preTokenBalances"), mint)

    def side_amount(tok: Token, is_input: bool) -> int:
        if tok.mint == WSOL_MINT:
            return -(native_delta + fee) - retained_rent if is_input else native_delta + fee + retained_rent
        return -spl_delta(tok.mint) if is_input else spl_delta(tok.mint)

    return {
        "in_raw": side_amount(token_in, True),
        "out_raw": side_amount(token_out, False),
        "fee_lamports": fee,
        "native_delta_lamports": native_delta,
        "slot": tx.get("slot"),
    }


__all__ = ["Engine", "realized_from_meta", "QUOTE_MINT"]
