"""Shared, idempotent ledger recovery for daemon and CLI submission journals.

Construct LedgerRecovery with the recorded ledger and a fresh-price callback, then pass apply
as the journal's reconciliation callback. It never broadcasts or retries a transaction.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import addresses
from .chain import AeroChain, PoolState, PositionGone, PositionState
from .config import Config
from .executor import increased_amounts, minted_token_id, receipt_fee_wei, token_delta
from .ledger import Ledger
from .submissions import PendingSubmission
from .validation import finite_number


class LedgerRecovery:
    def __init__(
        self,
        cfg: Config,
        chain: AeroChain,
        ledger: Ledger,
        prices: Callable[[], dict[str, float]],
        decisions: dict[str, Any] | None = None,
    ):
        self.cfg, self.chain, self.ledger, self.prices = cfg, chain, ledger, prices
        self.decisions = decisions if decisions is not None else {}

    def _require_owner(self, pos: PositionState) -> None:
        if pos.owner.lower() != self.cfg.owner.lower():
            raise PendingSubmission("recovered position is not owned by the configured wallet")

    def _pool_prices(self, pool: PoolState, prices: dict[str, float]) -> tuple[float, float]:
        u0, u1 = (prices.get(t.address.lower(), 0.0) for t in (pool.token0, pool.token1))
        finite_number(u0, "token0 recovery price", positive=True)
        finite_number(u1, "token1 recovery price", positive=True)
        return u0, u1

    @staticmethod
    def _pool_has_aero(pool: PoolState | None) -> bool:
        if pool is None:
            raise PendingSubmission("unstake recovery has no recorded pool")
        return addresses.AERO_TOKEN.lower() in (pool.token0.address.lower(), pool.token1.address.lower())

    def _group_slot(self, group: list[dict[str, Any]]) -> str | None:
        """Resolve once from durable identities, then persist before closing/replacing an NFT."""
        slots = {s for r in group if (s := self.ledger.transaction_slot(r["hash"])) is not None}
        wallet_scope = False
        for record in group:
            context = record.get("accounting")
            if context is None:
                continue
            if not isinstance(context, dict):
                raise PendingSubmission("invalid receipt accounting attribution")
            if context.get("scope") == "wallet":
                wallet_scope = True
            elif context.get("scope") == "slot" and isinstance(context.get("slot"), str) and context["slot"].strip():
                slots.add(context["slot"])
            else:
                raise PendingSubmission("invalid receipt accounting attribution")
        token_ids = {
            tid
            for r in group
            for tid in ([r["intent"]["token_id"]] if "token_id" in r["intent"] else r["intent"].get("token_ids", []))
        }
        minted = {
            tid
            for r in group
            if r["intent"]["kind"] == "mint" and r["receipt"]["status"] == 1
            if (tid := minted_token_id(r["receipt"]["logs"], addresses.NONFUNGIBLE_POSITION_MANAGER, self.cfg.owner))
            is not None
        }
        slots.update(self.ledger.token_slots(token_ids | minted))
        if not slots and minted:
            slots.update(str(tid) for tid in minted)
        if len(slots) > 1:
            raise PendingSubmission("receipt group belongs to multiple strategy slots; cannot allocate its effects")
        slot = next(iter(slots), None)
        if slot is None and not wallet_scope:
            raise PendingSubmission("receipt group lacks provable accounting attribution; reconcile its origin first")
        # A wallet-funded deployment acquires a slot only if its own receipt proves a new NFT.
        # If it fails at an approval, its explicit wallet context still identifies the gas expense.
        if slot is not None and wallet_scope and not (minted and token_ids <= minted):
            raise PendingSubmission("receipt group has conflicting wallet and slot attribution")
        if slot is not None and not minted and self.ledger.slot_row(slot) is None:
            raise PendingSubmission("receipt accounting attribution names an unknown strategy slot")
        if slot is not None:
            self.ledger.bind_transaction_slots([r["hash"] for r in group], slot)
        return slot

    def apply(self, record: dict[str, Any], group: list[dict[str, Any]]) -> None:
        """Replay only measured effects, with SQLite receipt keys protecting every monetary write."""
        receipt, intent, tx_hash = record["receipt"], record["intent"], record["hash"]
        kind = intent["kind"]
        pool = self.chain.pool_state(record["pool"]) if record["pool"] else None
        prices = self.prices()
        eth_price = prices.get(addresses.WETH.lower(), 0.0)
        finite_number(eth_price, "ETH recovery price", positive=True)
        slot = self._group_slot(group)
        reward = 0.0
        token_id = intent.get("token_id")
        if token_id is None and kind == "claim" and len(intent["token_ids"]) == 1:
            token_id = intent["token_ids"][0]
        if receipt["status"] == 1:
            if kind == "mint":
                gone = False
                tid = minted_token_id(receipt["logs"], addresses.NONFUNGIBLE_POSITION_MANAGER, self.cfg.owner)
                if tid is None or pool is None:
                    raise PendingSubmission("mint receipt lacks verified NFT/pool evidence")
                try:
                    pos = self.chain.position(tid, owner_hint=self.cfg.owner)
                except PositionGone:
                    gone = True
                    # A later withdrawal can burn this NFT before its historical mint is booked.
                    # The journal intent and verified mint Transfer retain the original identity.
                    if (
                        intent.get("recipient", "").lower() != self.cfg.owner.lower()
                        or intent.get("token0", "").lower() != pool.token0.address.lower()
                        or intent.get("token1", "").lower() != pool.token1.address.lower()
                    ):
                        raise PendingSubmission(
                            "burned mint lacks verified historical pool/recipient identity"
                        ) from None
                else:
                    self._require_owner(pos)
                    if pos.pool.address.lower() != pool.address.lower():
                        raise PendingSubmission("recovered NFT pool does not match the submitted intent")
                a0, a1 = increased_amounts(receipt["logs"], addresses.NONFUNGIBLE_POSITION_MANAGER, tid)
                old_ids = {r["intent"]["token_id"] for r in group if r["intent"]["kind"] == "remove"}
                if old_ids and slot is not None and self.ledger.slot_row(slot) is not None:
                    self.ledger.set_token_id(slot, tid)
                else:
                    slot = str(tid)
                    self.ledger.open_slot(
                        slot,
                        pool.address,
                        f"{pool.token0.symbol}/{pool.token1.symbol}",
                        pool.token0.address,
                        pool.token1.address,
                        pool.token0.decimals,
                        pool.token1.decimals,
                        tid,
                        source="recovered",
                    )
                    u0, u1 = self._pool_prices(pool, prices)
                    h0, h1 = a0 / 10**pool.token0.decimals, a1 / 10**pool.token1.decimals
                    self.ledger.flow(slot, "deposit", h0, h1, h0 * u0 + h1 * u1, receipt_hash=tx_hash)
                if gone:
                    self.ledger.close_slot(slot)
            elif kind == "increase":
                if slot is None or pool is None:
                    raise PendingSubmission("confirmed increase belongs to an untracked position")
                try:
                    self._require_owner(self.chain.position(token_id, owner_hint=self.cfg.owner))
                except PositionGone:
                    row = self.ledger.slot_row(slot)
                    if row is None or row["pool"].lower() != pool.address.lower():
                        raise PendingSubmission("burned increase has no matching historical slot/pool") from None
                a0, a1 = increased_amounts(receipt["logs"], addresses.NONFUNGIBLE_POSITION_MANAGER, token_id)
                u0, u1 = self._pool_prices(pool, prices)
                h0, h1 = a0 / 10**pool.token0.decimals, a1 / 10**pool.token1.decimals
                self.ledger.flow(slot, "topup", h0, h1, h0 * u0 + h1 * u1, receipt_hash=tx_hash)
            elif kind == "remove":
                minted = any(r["intent"]["kind"] == "mint" and r["receipt"]["status"] == 1 for r in group)
                if not minted and slot is not None and pool is not None:
                    logs = [
                        lg
                        for r in group
                        if r["intent"]["kind"] in ("remove", "unstake") and r["receipt"]["status"] == 1
                        for lg in r["receipt"]["logs"]
                    ]
                    a0, a1 = (token_delta(logs, t.address, self.cfg.owner) for t in (pool.token0, pool.token1))
                    u0, u1 = self._pool_prices(pool, prices)
                    h0, h1 = a0 / 10**pool.token0.decimals, a1 / 10**pool.token1.decimals
                    self.ledger.flow(slot, "withdraw", h0, h1, h0 * u0 + h1 * u1, receipt_hash=tx_hash)
                    basis0, basis1 = self.ledger.deposited_amounts(slot)
                    self.ledger.snapshot(slot, token_id, 0.0, basis0 * u0 + basis1 * u1, 0.0)
                    self.ledger.close_slot(slot)
            removed = any(r["intent"]["kind"] == "remove" and r["receipt"]["status"] == 1 for r in group)
            if kind in ("claim", "unstake") and (kind == "claim" or not self._pool_has_aero(pool) or not removed):
                claimed = token_delta(receipt["logs"], addresses.AERO_TOKEN, self.cfg.owner)
                if claimed:
                    price = prices.get(addresses.AERO_TOKEN.lower(), 0.0)
                    finite_number(price, "AERO recovery price", positive=True)
                    reward = claimed / 1e18 * price
            elif kind == "collect" and pool is not None:
                u0, u1 = self._pool_prices(pool, prices)
                reward = (
                    token_delta(receipt["logs"], pool.token0.address, self.cfg.owner) / 10**pool.token0.decimals * u0
                    + token_delta(receipt["logs"], pool.token1.address, self.cfg.owner) / 10**pool.token1.decimals * u1
                )
        self.ledger.event(
            "reconciled",
            slot,
            detail=f"confirmed {kind}: {tx_hash}",
            tx=[tx_hash],
            receipt_fees={tx_hash: receipt_fee_wei(receipt) / 1e18 * eth_price},
            receipt_rewards={tx_hash: reward},
        )
        if slot in self.decisions:
            self.decisions[slot]["_stale"] = True
