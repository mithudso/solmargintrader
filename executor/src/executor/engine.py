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
from contextlib import suppress
from decimal import Decimal, InvalidOperation
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
        from .authority import WalletAuthority

        self.authority = WalletAuthority(cfg, self.root)
        if self.authority.policy_path.is_file():
            self.journal = self.authority.journal
        self._caller_request = None
        self._caller_reserved = None
        self._entry_admission = None
        self._reviewed_cfg = None

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
        request_id: str | None = None,
        caller_context: dict | None = None,
        admission=None,
    ) -> dict[str, Any]:
        token_in, token_out = resolve(frm), resolve(to)
        in_raw = ui_to_raw(amount, token_in.decimals)
        slip = self._slippage(slippage_bps)
        if live and not (reason and reason.strip()):
            raise BadParams("a live swap needs a reason: it is written to the journal before sending")
        if strategy is not None and not strategy.strip():
            raise BadParams("strategy may not be blank")
        with self._swap_lock():
            if not live:
                if admission is not None:
                    admission()
                return self._swap_locked(
                    token_in, token_out, in_raw, strategy, live, exit_only, (reason or "").strip(), slip
                )
            from .authority import STRATEGIES, identity

            if strategy not in STRATEGIES and not exit_only:
                raise Refused("live strategy must be a canonical executor risk family")
            with self.authority.lock():
                self.authority.check()
                original_cfg = self.cfg
                effective_cfg = self.authority.effective_config()
                self.journal = self.authority.journal
                request_id = request_id or str(uuid.uuid4())
                body = {
                    "from": token_in.mint,
                    "to": token_out.mint,
                    "in_raw": in_raw,
                    "strategy": strategy,
                    "exit": exit_only,
                    "reason": (reason or "").strip(),
                    "slippage_bps": slip,
                    "owner": identity(original_cfg),
                    "context": caller_context,
                }
                old = self.authority.bind(request_id, body)
                if old:
                    self.cfg = original_cfg
                    return self.authority.replay(old)
                self._caller_request = request_id
                self._caller_reserved = None
                self._entry_admission = admission
                self._reviewed_cfg = original_cfg
                try:
                    self.cfg = effective_cfg
                    self.authority.require_no_pending(request_id, exit_only=exit_only)
                    if admission is not None:
                        # Identity binds the caller's reviewed config, not the
                        # conservative cross-client cap projection below.
                        self.cfg = original_cfg
                        admission()
                        self.cfg = self.authority.effective_config()
                    result = self._swap_locked(
                        token_in, token_out, in_raw, strategy, live, exit_only, (reason or "").strip(), slip
                    )
                    result["request_id"] = request_id
                    self.authority.update(request_id, "terminal", result=result)
                    return result
                except Exception as exc:
                    state = self.authority.status(request_id)["request"]
                    intent = self.journal.states().get(state["intent_id"])
                    uncertain = intent and intent["state"] in ("sending", "unknown")
                    result = {
                        "request_id": request_id,
                        "state": "unknown" if uncertain else "refused",
                        "sent": None if uncertain else False,
                        "error": {
                            "code": getattr(exc, "code", "failed"),
                            "message": "executor request requires reconciliation"
                            if uncertain
                            else "executor refused; nothing sent",
                        },
                    }
                    self.authority.update(
                        request_id,
                        "unknown" if uncertain else "terminal",
                        reserved=state["reserved_usd"] if uncertain else "0",
                        result=result,
                    )
                    raise
                finally:
                    self.authority.save_anchor()
                    self.cfg = original_cfg
                    self._caller_request = None
                    self._caller_reserved = None
                    self._entry_admission = None
                    self._reviewed_cfg = None

    def _check_entry_admission(self):
        if self._entry_admission is not None:
            effective = self.cfg
            self.cfg = self._reviewed_cfg
            try:
                self._entry_admission()
            finally:
                self.cfg = effective

    def _kill_present(self):
        return (self.root / "KILL").exists() or self.authority.killed()

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
            kill_present=self._kill_present(), native_lamports=native, now=now,
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
        self._caller_reserved = self.authority.budget(
            report, native, facts.fee_lamports, request_id=self._caller_request, exit_only=exit_only
        )
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
        self._check_entry_admission()
        intent_id = f"swap-{int(self.clock())}-{uuid.uuid4().hex[:8]}"
        self.authority.update(self._caller_request, "executing", reserved=self._caller_reserved, intent_id=intent_id)
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
        if not 0 <= age <= cfg.rails.max_quote_age_s:
            raise Refused(f"quote is {age:.1f} s old, over max_quote_age_s {cfg.rails.max_quote_age_s:g}")
        if self._kill_present() and not exit_only:
            raise Refused("KILL file appeared while the swap was being prepared")
        height = self.rpc.block_height()
        if built["lastValidBlockHeight"] - height < BLOCKHASH_MARGIN:
            raise Refused("the blockhash is about to expire; try again")
        native_now = self.rpc.balance(cfg.owner)
        # Re-run the position rails against the journal as it is NOW (a concurrent writer cannot have raced past the lock).
        decision = rails.check_trade(
            cfg, self.root, self.journal, report, strategy=strategy, live=True, exit_only=exit_only,
            kill_present=self._kill_present(), native_lamports=native_now, now=self.clock(),
        )  # fmt: skip
        base_evidence["decision"] = decision.to_dict()
        # Every final RPC and gate read precedes the last pre-journal safety check.
        age = self.clock() - report.fetched_at
        if not 0 <= age <= cfg.rails.max_quote_age_s:
            raise Refused(f"quote is {age:.1f} s old, over max_quote_age_s {cfg.rails.max_quote_age_s:g}")
        if self._kill_present() and not exit_only:
            raise Refused("KILL file appeared while the swap was being prepared")

        self.authority.budget(
            report, native_now, facts.fee_lamports, request_id=self._caller_request, exit_only=exit_only
        )
        self._check_entry_admission()
        base_raw, quote_usd = self._base_and_quote(decision.side, report)
        self.journal.append(
            "intent", intent_id,
            strategy=strategy, side=decision.side, base_mint=decision.base_mint, exit=exit_only, reason=reason,
            caller_request_id=self._caller_request,
            from_mint=report.token_in.mint, to_mint=report.token_out.mint, in_raw=report.quote.in_raw,
            min_out_raw=report.quote.min_out_raw, in_usd=str(round(report.in_usd, 6)),
            sol_price_usd=str(report.sol_price_usd), evidence={**base_evidence, "signed_check": evidence2},
            gate_notes=list(decision.notes), expected_base_raw=base_raw, expected_quote_usd=quote_usd,
        )  # fmt: skip
        self.journal.append(
            "sending", intent_id, signature=signature, last_valid_block_height=built["lastValidBlockHeight"]
        )
        # Both journal writes can block on disk. A stop or expired quote during either write still wins.
        age = self.clock() - report.fetched_at
        refusal = None
        if self._kill_present() and not exit_only:
            refusal = "KILL file appeared while the intent was being journalled; nothing was sent"
        elif not 0 <= age <= cfg.rails.max_quote_age_s:
            refusal = f"quote is {age:.1f} s old after journalling; outside max_quote_age_s; nothing was sent"
        if not refusal:
            try:
                self._check_entry_admission()
            except Refused:
                refusal = "scoped admission changed before send; nothing was sent"
        if refusal:
            self.journal.append("result", intent_id, status="rejected", signature=signature, reason=refusal)
            raise Refused(refusal)
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

        try:
            status = self._confirm(signature)
            if status is None:
                self.journal.append(
                    "unknown", intent_id, signature=signature, reason="not confirmed within the timeout"
                )
                raise Ambiguous(
                    f"{signature} was not confirmed in {cfg.rails.confirm_timeout_s:g} s; it may still land. Run `executor reconcile`"
                )
            if status.get("err") is not None:
                fees = self._failed_fee_fields(signature, report.sol_price_usd)
                if fees is None:
                    self.journal.append(
                        "unknown", intent_id, signature=signature, reason="failed on chain but fee evidence unreadable"
                    )
                    raise Ambiguous(f"{signature} failed but its fees could not be read; run `executor reconcile`")
                self.journal.append(
                    "result", intent_id, status="failed", signature=signature, error=str(status["err"]), **fees
                )
                raise ExecutorError(f"transaction {signature} failed on chain: {status['err']}", "failed")
            realized = self._read_realized(
                signature, report.token_in, report.token_out, evidence2.get("retained_rent_lamports", 0)
            )
            if realized is None:
                self.journal.append(
                    "unknown", intent_id, signature=signature, reason="confirmed but balances unreadable"
                )
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
            if not outcome["post_verify_ok"]:
                (self.root / "KILL").write_text(f"auto-kill: post-trade check failed for {signature}\n")
            self.journal.append("result", intent_id, status="confirmed", signature=signature, **outcome)
            return {
                "mode": "live", "sent": True, "id": intent_id, "signature": signature, "strategy": strategy, "reason": reason,
                "post_verify_ok": outcome["post_verify_ok"], "in_raw": outcome["in_raw"], "out_raw": outcome["out_raw"],
                "fee_lamports": outcome["fee_lamports"], **base_evidence,
            }  # fmt: skip
        except Ambiguous:
            raise
        except Exception as exc:  # an accepted send stays ambiguous when a reader or persistence fails
            if self.journal.states().get(intent_id, {}).get("state") in ("result", "reconciled"):
                raise
            # The durable sending record still holds the block if storage itself failed.
            with suppress(Exception):
                self.journal.append(
                    "unknown", intent_id, signature=signature, reason=f"post-send raised {type(exc).__name__}"
                )
            raise Ambiguous(
                f"post-send outcome unknown for {signature}; it was NOT retried. Run `executor reconcile`"
            ) from None

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
            if isinstance(st, dict) and "err" in st and st.get("confirmationStatus") in ("confirmed", "finalized"):
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

    def _failed_fee_fields(self, signature: str, sol_price: Decimal | None) -> dict[str, Any] | None:
        if sol_price is None or not sol_price.is_finite() or sol_price <= 0:
            return None
        for _ in range(8):
            try:
                tx = self.rpc.transaction(signature)
            except RpcError:
                tx = None
            if isinstance(tx, dict) and isinstance(tx.get("meta"), dict):
                meta = tx["meta"]
                transaction = tx.get("transaction")
                message = transaction.get("message") if isinstance(transaction, dict) else None
                keys = message.get("accountKeys") if isinstance(message, dict) else None
                payer = keys[0] if isinstance(keys, list) and keys else None
                payer = payer.get("pubkey") if isinstance(payer, dict) else payer
                fee = meta.get("fee")
                if meta.get("err") is not None and payer == self.cfg.owner and type(fee) is int and 0 <= fee < 2**64:
                    return {"fee_lamports": fee, "fee_usd": str(raw_to_ui(fee, 9) * sol_price), "slot": tx.get("slot")}
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
        with self._swap_lock():
            if not self.authority.policy_path.is_file():
                return self._reconcile_locked()
            with self.authority.lock():
                self.authority.check()
                self.journal = self.authority.journal
                result = self._reconcile_locked()
                self.authority.reconcile_requests()
                self.authority.save_anchor()
                return result

    def _reconcile_locked(self) -> dict[str, Any]:
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
            terminal = (
                isinstance(status, dict)
                and "err" in status
                and status.get("confirmationStatus") in ("confirmed", "finalized")
            )
            if terminal and status["err"] is not None:
                fees = self._failed_fee_fields(signature, _recorded_sol_price(intent))
                if fees is None:
                    out.append(
                        {
                            "id": iid,
                            "signature": signature,
                            "outcome": "still_unknown",
                            "why": "failed fee evidence unreadable",
                        }
                    )
                    continue
                self.journal.append(
                    "reconciled", iid, status="failed", signature=signature, error=str(status["err"]), **fees
                )
                out.append({"id": iid, "signature": signature, "outcome": "failed_on_chain"})
            elif terminal:
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
                sol_price = _recorded_sol_price(intent)
                if sol_price is None:
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
                if not fields["post_verify_ok"]:
                    (self.root / "KILL").write_text(
                        f"auto-kill: reconciled trade {signature} did not match its quote\n"
                    )
                self.journal.append("reconciled", iid, status="confirmed", signature=signature, **fields)
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
                # Expiry prevents future inclusion; it cannot disprove an already observed processed transaction.
                if status is None and type(lvbh) is int and height > lvbh + 150:
                    self.journal.append("reconciled", iid, status="dropped", signature=signature,
                                        why=f"not on chain and block height {height} is past {lvbh}")  # fmt: skip
                    out.append({"id": iid, "signature": signature, "outcome": "dropped"})
                else:
                    out.append({"id": iid, "signature": signature, "outcome": "still_unknown",
                                "why": "no confirmed outcome yet; a present pending status remains unresolved"})  # fmt: skip
        return {"checked": len(out), "results": out, "still_blocking": len(self.journal.unresolved())}


def _recorded_sol_price(intent: dict[str, Any]) -> Decimal | None:
    try:
        price = Decimal(intent["sol_price_usd"])
    except (KeyError, ValueError, TypeError, InvalidOperation):
        return None
    return price if price.is_finite() and price > 0 else None


def _tokens(intent: dict[str, Any]) -> tuple[Token, Token]:
    return resolve(intent["from_mint"]), resolve(intent["to_mint"])


def realized_from_meta(
    tx: dict[str, Any], owner: str, token_in: Token, token_out: Token, retained_rent: int
) -> dict[str, Any] | None:
    """Exact owner deltas of a confirmed transaction, from its metadata. None when the metadata is unusable."""

    def unsigned(value: Any) -> int:
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError("invalid unsigned amount")
        return value

    def token_total(entries: Any, mint: str) -> int:
        if not isinstance(entries, list):
            raise ValueError("missing token balance evidence")
        total = 0
        indices: set[int] = set()
        for entry in entries:
            # An omitted owner cannot establish that a balance belongs to somebody else.
            if not isinstance(entry, dict) or not isinstance(entry.get("owner"), str) or not entry["owner"]:
                raise ValueError("unattributed token balance")
            if not isinstance(entry.get("mint"), str) or not entry["mint"]:
                raise ValueError("missing token mint")
            index = entry.get("accountIndex")
            if type(index) is not int or not 0 <= index < len(keys) or index in indices:
                raise ValueError("invalid or duplicate token account index")
            indices.add(index)
            amount = entry["uiTokenAmount"]["amount"]
            if not isinstance(amount, str) or not amount.isascii() or not amount.isdecimal():
                raise ValueError("invalid token amount")
            raw = unsigned(int(amount))
            if entry["owner"] == owner and entry["mint"] == mint:
                total += raw
        return total

    try:
        meta = tx["meta"]
        msg = tx["transaction"]["message"]
        if not isinstance(meta, dict) or "err" not in meta or meta["err"] is not None:
            return None
        keys = msg["accountKeys"]
        if not isinstance(keys, list):
            return None
        loaded = meta.get("loadedAddresses", {"writable": [], "readonly": []})
        keys = keys + loaded["writable"] + loaded["readonly"]
        keys = [key if isinstance(key, str) else key["pubkey"] for key in keys]
        if any(not isinstance(key, str) or not key for key in keys) or keys.count(owner) != 1:
            return None
        idx = keys.index(owner)
        before, after = meta["preBalances"], meta["postBalances"]
        if (
            not isinstance(before, list)
            or not isinstance(after, list)
            or len(before) != len(keys)
            or len(after) != len(keys)
        ):
            return None
        native_delta = unsigned(after[idx]) - unsigned(before[idx])
        fee = unsigned(meta["fee"])
        unsigned(retained_rent)  # Reject malformed persisted simulation evidence; actual rent is measured below.
        # Explicit empty arrays can describe a newly created token account. Missing arrays cannot.
        deltas = {
            tok.mint: token_total(meta["postTokenBalances"], tok.mint) - token_total(meta["preTokenBalances"], tok.mint)
            for tok in (token_in, token_out)
        }
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None

    # Actual owner token-account balances establish retained/refunded rent. A
    # simulated rent estimate cannot account for closing pre-existing WSOL.
    def rent_total(entries: list[dict[str, Any]], balances: list[int]) -> int:
        total = 0
        for entry in entries:
            if entry["owner"] != owner:
                continue
            index = entry["accountIndex"]
            amount = int(entry["uiTokenAmount"]["amount"]) if entry["mint"] == WSOL_MINT else 0
            account_rent = unsigned(balances[index]) - amount
            if account_rent < 0:
                raise ValueError("inconsistent wrapped-SOL balance")
            total += account_rent
        return total

    try:
        rent_delta = rent_total(meta["postTokenBalances"], after) - rent_total(meta["preTokenBalances"], before)
        wsol_delta = token_total(meta["postTokenBalances"], WSOL_MINT) - token_total(
            meta["preTokenBalances"], WSOL_MINT
        )
        sol_delta = native_delta + wsol_delta + fee + rent_delta
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    def side_amount(tok: Token, is_input: bool) -> int:
        if tok.mint == WSOL_MINT:
            return -sol_delta if is_input else sol_delta
        return -deltas[tok.mint] if is_input else deltas[tok.mint]

    return {
        "in_raw": side_amount(token_in, True),
        "out_raw": side_amount(token_out, False),
        "fee_lamports": fee,
        "native_delta_lamports": native_delta,
        "slot": tx.get("slot"),
    }


__all__ = ["Engine", "realized_from_meta", "QUOTE_MINT"]
