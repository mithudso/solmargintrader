"""The liquidity daemon: one loop that manages every position, compounds, scouts and allocates.

Each tick, in order:
  1. Kill switch. If `$AERO_LP_HOME/KILL` exists, the tick takes no on-chain action; it still reads and
     reports.
  2. Wallet snapshot: balances of the allowed tokens plus native ETH, recorded in the ledger for idle
     detection.
  3. Every open slot: evaluate, then rebalance when the strategy says so (Engine.step). Results go to the
     ledger.
  4. Compounding (every compound_interval_h): claim AERO, or collect fees, and add them back to the
     position when the reward is at least `compound_gas_multiple` times the gas.
  5. Scout (every scout_interval_h): writes scout.json.
  6. Allocation (every allocate_interval_h): keep the gas reserve, deploy idle coins into qualifying
     pools (or a side-by-side experiment), and graduate finished experiments.
  7. status.json for soltui.

In dry-run mode every on-chain step is planned or simulated and logged, never broadcast.

Safety rules the code below keeps:
  * `runner()` is the only place a LiveRunner is built, and it refuses while the kill switch exists. Every step
    that can sign checks `acting()` first and builds its runner afterwards, so a KILL file created between the
    two stops the step instead of being ignored. The engine re-checks it right before it broadcasts.
  * Funds are only ever moved in designated amounts (a claim, a collect, idle coins); a failure leaves them in
    the wallet and is logged as an `error` action with the partial result, so the gas is booked too.
  * Bookkeeping never depends on the price feed: it falls back to the last good prices, so a feed outage cannot
    drop a ledger entry for a transaction that already happened.
"""

from __future__ import annotations

import math
import signal
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from web3 import Web3

from . import addresses
from .allocator import gas_topup_needed, plan_allocation, plan_graduation
from .chain import ZERO, AeroChain, PoolState, PositionGone, PositionState
from .config import Config
from .engine import Engine, Evaluation, defer_sigint
from .executor import (
    LiveRunner,
    RebalanceError,
    Rebalancer,
    RebalanceResult,
    SimRunner,
    gas_cost_usd,
    runner_tokens,
)
from .ledger import Ledger
from .market import MarketData
from .metrics import KNOWN_TOKENS
from .scout import load_scout, run_scout
from .state import atomic_write_json, home
from .strategy import target_range

STATUS_SCHEMA = "aero-lp-status/1"
SYMBOL_TO_ADDR = {v: Web3.to_checksum_address(k) for k, v in KNOWN_TOKENS.items()}
# A conversion swap is refused when the pool's price implies an output worth this much less than the input at
# market prices (the pool's own price is what the min-out is built from, so a pushed pool would pass its own check).
CONVERT_PRICE_TOLERANCE = 0.02
# The allocator ignores a scout file older than this many scout intervals.
SCOUT_MAX_AGE_INTERVALS = 3
# Bookkeeping re-asks a failing price feed no sooner than this.
PRICE_RETRY_S = 60.0
# One scout run may block the loop (positions are not managed meanwhile) for at most this long.
SCOUT_BUDGET_S = 600.0


class KillSwitchEngaged(RuntimeError):
    """Raised instead of building a live runner while `$AERO_LP_HOME/KILL` exists."""


@dataclass
class Timers:
    last: dict[str, float] = field(default_factory=dict)

    def due(self, name: str, every_s: float, now: float) -> bool:
        if now - self.last.get(name, 0.0) >= every_s:
            self.last[name] = now
            return True
        return False


class Daemon:
    def __init__(self, cfg: Config, live: bool, signer: Any = None, root: Path | None = None):
        if live and signer is None:
            raise ValueError("live mode needs a signer")
        self.cfg, self.live, self.signer = cfg, live, signer
        self.root = root or home()
        self.chain = AeroChain(cfg.rpc_url)
        self.market = MarketData()
        self.engine = Engine(cfg, chain=self.chain, market=self.market)
        self.engine.gate = self.assert_acting
        self.engine.on_stop = self._request_stop
        self._stop_signal: int | None = None
        self._wake = threading.Event()
        self.ledger = Ledger(self.root / "ledger.sqlite")
        self.rb = Rebalancer(self.chain, cfg.owner, cfg.execution)
        self.timers = Timers()
        self.decisions: dict[str, dict[str, Any]] = {}
        self.wallet: dict[str, Any] = {}
        self._last_prices: dict[str, float] = {}
        self._prices_failed_at = 0.0

    # ------------------------------------------------------------------ helpers

    @property
    def killed(self) -> bool:
        return (self.root / "KILL").exists()

    def acting(self) -> bool:
        return self.live and not self.killed

    def assert_acting(self) -> None:
        """Raise unless a live transaction may be sent right now (the engine calls this before it broadcasts)."""
        if self.live and self.killed:
            raise KillSwitchEngaged("kill switch engaged: no on-chain action")

    @property
    def paused_reason(self) -> str:
        return "dry-run" if not self.live else "kill switch"

    def log(
        self,
        kind: str,
        detail: str,
        slot: str | None = None,
        res: RebalanceResult | None = None,
        reward_usd: float = 0.0,
    ) -> None:
        gas_usd = 0.0
        if res is not None and res.fee_wei:
            gas_usd = res.fee_wei / 1e18 * self.eth_usd()
        self.ledger.event(
            kind, slot, gas_usd=gas_usd, reward_usd=reward_usd, detail=detail, tx=res.tx_hashes if res else None
        )
        print(time.strftime("%H:%M:%S"), kind, slot or "-", detail, flush=True)

    def prices(self) -> dict[str, float]:
        """Fresh USD prices (raises if the feed is down). Use this for anything that sizes or gates a trade."""
        tokens = [SYMBOL_TO_ADDR[s] for s in self.cfg.allocator.allowed_tokens if s in SYMBOL_TO_ADDR]
        out = self.market.token_prices_usd(tokens + [addresses.AERO_TOKEN, addresses.WETH])
        self._last_prices = out
        return out

    def known_prices(self) -> dict[str, float]:
        """`prices()`, or the last good set when the feed is down. Bookkeeping only, never for sizing a trade.

        After a failure the feed is not asked again for a minute: a rate-limited feed can block a call for
        half a minute, and bookkeeping runs several times per tick.
        """
        if time.time() - self._prices_failed_at < PRICE_RETRY_S:
            return self._last_prices
        try:
            return self.prices()
        except Exception:  # noqa: BLE001 - the ledger must still record a transaction that already happened
            self._prices_failed_at = time.time()
            return self._last_prices

    def eth_usd(self) -> float:
        return self.known_prices().get(addresses.WETH.lower(), 0.0)

    def runner(self, tokens: list[str], pool: str | None) -> Any:
        if self.live:
            self.assert_acting()
            return LiveRunner(self.chain, self.signer, tokens, self.cfg.execution, pool)
        return SimRunner(self.chain, self.cfg.owner, tokens, pool)

    def best_direct_pool(self, a: str, b: str) -> PoolState | None:
        best: PoolState | None = None
        for ts in self.chain.factory.functions.tickSpacings().call():
            addr = self.chain.pool_address(a, b, int(ts))
            if addr == ZERO:
                continue
            ps = self.chain.pool_state(addr)
            if ps.liquidity > 0 and (best is None or ps.liquidity > best.liquidity):
                best = ps
        return best

    def _preflight(self, pool: PoolState, run: Callable[[SimRunner], RebalanceResult]) -> str | None:
        """Simulate a sequence on live state before signing it. Returns why it must not be sent, or None.

        Checks what `Engine.rebalance` checks for a rebalance: the whole sequence simulates, its gas is within
        `safety.max_gas_usd`, and the wallet holds enough ETH to pay for every stage with a 3x margin.
        """
        sim = run(
            SimRunner(self.chain, self.cfg.owner, runner_tokens(pool.token0.address, pool.token1.address), pool.address)
        )
        eth_usd = self.eth_usd()
        if not eth_usd:
            return "ETH price unavailable; cannot enforce safety.max_gas_usd"
        gas_units = sum(sim.gas_used.values())
        gas_price = self.chain.gas_price_wei()
        gas_usd = gas_cost_usd(gas_units, gas_price, eth_usd, self.cfg.l1_fee_usd_estimate)
        if gas_usd > self.cfg.safety.max_gas_usd:
            return f"simulated gas ${gas_usd:.2f} > safety.max_gas_usd ${self.cfg.safety.max_gas_usd:.2f}"
        need_wei = 3 * gas_units * gas_price
        have_wei = int(self.chain.w3.eth.get_balance(Web3.to_checksum_address(self.cfg.owner)))
        if have_wei < need_wei:
            return f"wallet holds {have_wei / 1e18:.6f} ETH, below the {need_wei / 1e18:.6f} ETH gas reserve"
        return None

    def _send(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a live transaction sequence with Ctrl-C and SIGTERM held until it ends (see defer_sigint). A held
        signal only sets a flag; the caller books the result and the loop stops at the next safe point."""
        with defer_sigint(self._request_stop):
            return fn(*args, **kwargs)

    def _request_stop(self, signum: int) -> None:
        self._stop_signal = self._stop_signal or signum
        self._wake.set()

    def _on_signal(self, signum: int, frame: Any) -> None:
        """Signal handler for the idle loop: the first signal asks for a stop at the next safe point, a second one
        (the operator insists) leaves at once."""
        if self._stop_signal is not None:
            raise KeyboardInterrupt
        self._request_stop(signum)

    def _check_stop(self) -> None:
        """Called between steps, where nothing is in flight and everything done so far is booked."""
        sig = self._stop_signal
        if sig is None:
            return
        print(f"{time.strftime('%H:%M:%S')} stop: signal {sig} received; exiting between steps", flush=True)
        raise SystemExit(128 + sig)

    # ------------------------------------------------------------------ wallet

    def read_wallet(self) -> dict[str, Any]:
        owner = Web3.to_checksum_address(self.cfg.owner)
        syms = [s for s in self.cfg.allocator.allowed_tokens if s in SYMBOL_TO_ADDR]
        addrs = [SYMBOL_TO_ADDR[s] for s in syms]
        raw = self.chain.erc20_balances(owner, addrs) if addrs else []
        try:
            prices = self.prices()
        except Exception as e:  # noqa: BLE001 - positions must keep being managed while the price feed is down
            prices = {}
            if self.timers.due("prices-down", 3600, time.time()):
                self.log(
                    "error", f"price feed unavailable ({type(e).__name__}); USD figures are 0, nothing is allocated"
                )
        tokens = []
        human: dict[str, float] = {}
        for sym, addr, amt in zip(syms, addrs, raw, strict=True):
            dec = self.chain.token(addr).decimals
            h = amt / 10**dec
            human[addr] = h
            tokens.append(
                {
                    "symbol": sym,
                    "address": addr,
                    "amount": h,
                    "usd": h * prices.get(addr.lower(), 0.0),
                    "raw": amt,
                    "decimals": dec,
                }
            )
        eth = int(self.chain.w3.eth.get_balance(owner)) / 1e18
        return {"eth": eth, "tokens": tokens, "human": human}

    def idle_tokens(self, wallet: dict[str, Any]) -> list[dict[str, Any]]:
        window = self.cfg.allocator.idle_window_hours * 3600
        out = []
        for t in wallet["tokens"]:
            if t["symbol"] in self.cfg.allocator.exclude_tokens:
                continue
            idle = self.ledger.idle_amount(t["address"], t["amount"], window)
            if idle > 0:
                frac = idle / t["amount"] if t["amount"] else 0.0
                # Whole balance idle: use the exact integer. `int(raw * 1.0)` rounds an 18-decimal amount above ~0.009
                # to a double that can exceed the balance, and the swap or mint would then revert every hour.
                raw = t["raw"] if idle >= t["amount"] else min(t["raw"], int(t["raw"] * frac))
                out.append({**t, "idle_amount": idle, "idle_raw": raw, "idle_usd": t["usd"] * frac})
        return out

    # ------------------------------------------------------------------ positions

    def register_config_positions(self) -> None:
        """Positions listed in config.token_ids enter the ledger at their current value the first time."""
        for tid in self.cfg.token_ids:
            if self.ledger.slot_row(str(tid)) is not None:
                continue
            try:
                self._register(tid)
            except PositionGone:
                continue
            except Exception as e:  # noqa: BLE001 - one unreadable position must not stop the others
                if self.timers.due(f"register:{tid}", 3600, time.time()):
                    self.log("error", f"cannot track position #{tid} yet: {type(e).__name__}: {e}", str(tid))

    def _register(self, tid: int) -> None:
        pos = self.chain.position(tid, owner_hint=self.cfg.owner)
        p = self.prices()
        a0, a1 = pos.human_amounts()
        usd = a0 * p.get(pos.pool.token0.address.lower(), 0) + a1 * p.get(pos.pool.token1.address.lower(), 0)
        if not usd > 0:
            raise RuntimeError("no USD value (a pool token has no price)")
        self.ledger.open_slot(
            str(tid),
            pos.pool.address,
            f"{pos.pool.token0.symbol}/{pos.pool.token1.symbol}",
            pos.pool.token0.address,
            pos.pool.token1.address,
            pos.pool.token0.decimals,
            pos.pool.token1.decimals,
            tid,
            source="config",
        )
        self.ledger.flow(str(tid), "deposit", a0, a1, usd)
        self.log("register", f"tracking existing position #{tid} at ${usd:,.2f}", str(tid))

    @staticmethod
    def _pool_has_aero(pool: PoolState) -> bool:
        return addresses.AERO_TOKEN.lower() in (pool.token0.address.lower(), pool.token1.address.lower())

    def _aero_reward_usd(self, res: RebalanceResult, pool: PoolState) -> float:
        """AERO claimed as a side effect of an unstake, in USD, when it lands in the wallet as a separate reward.

        If AERO is one of the pool's tokens, the claimed AERO is part of the redeposit (rebalance) or of the
        received amounts (withdraw), so it already shows up as value or as a withdrawal. Counting it again as a
        reward would count it twice.
        """
        if self._pool_has_aero(pool) or res.aero_claimed <= 0:
            return 0.0
        return res.aero_claimed / 1e18 * self.known_prices().get(addresses.AERO_TOKEN.lower(), 0.0)

    def _close_gone(self, slot: str) -> None:
        """The NFT no longer exists (burned by a rebalance that failed afterwards, or closed by the owner)."""
        pnl = self.ledger.pnl(slot)
        est = pnl.value_usd if pnl else 0.0
        if est > 0:
            # Its coins are in the wallet. Without a withdrawal the slot would show a total loss and the same
            # money would count again as a new deposit once it is redeployed.
            self.ledger.flow(slot, "withdraw", 0.0, 0.0, est)
        self.ledger.close_slot(slot)
        self.decisions.pop(slot, None)
        self.log(
            "closed",
            f"position no longer exists (closed outside the daemon); last known value ${est:,.2f} booked as withdrawn",
            slot,
        )

    def _nft_exists(self, token_id: int) -> bool:
        try:
            self.chain.position(token_id, owner_hint=self.cfg.owner)
        except PositionGone:
            return False
        return True

    def _align_token_id(self, slot: str, create: bool = False) -> None:
        """Make the engine's state file and the ledger agree on which NFT the slot holds.

        The engine saves the new id the moment a rebalance mints; the ledger learns it when the step returns. If
        the process stopped in between, the ledger is behind. If the engine's state file was lost, the engine is
        behind (a fresh entry points at the slot's original NFT). Which side is behind is decided by the chain:
        the one whose NFT still exists is right. If both or neither exist, nothing is changed here.
        """
        state = getattr(self.engine, "state", None)
        row = self.ledger.slot_row(slot)
        if state is None or row is None or row["token_id"] is None:
            return
        # `create`: the engine is about to step this slot and would otherwise start a fresh entry at the slot's
        # original NFT id, which may be a burned one.
        st = state.slot(int(slot)) if create else state.slots.get(slot)
        if st is None or st.current_token_id == row["token_id"]:
            return
        engine_alive, ledger_alive = self._nft_exists(st.current_token_id), self._nft_exists(int(row["token_id"]))
        if engine_alive and not ledger_alive:
            self.ledger.set_token_id(slot, st.current_token_id)
        elif ledger_alive and not engine_alive:
            st.current_token_id = int(row["token_id"])

    def manage_slot(self, slot: str, now: float) -> None:
        self._align_token_id(slot, create=True)
        row = self.ledger.slot_row(slot)
        acting = self.acting()  # read once: the same answer for the live flag and for the signer
        try:
            ev, res = self.engine.step(int(slot), live=acting, signer=self.signer if acting else None)
        except PositionGone:
            self._close_gone(slot)
            return
        except RebalanceError as e:
            self.log("error", f"rebalance failed: {e}", slot, e.partial)
            if e.partial.new_token_id:
                self.ledger.set_token_id(slot, e.partial.new_token_id)
            if slot in self.decisions:
                self.decisions[slot]["_stale"] = True  # it describes an NFT that no longer exists
            return
        rebalanced_to: int | None = None
        if res is not None and acting:
            # Book the transaction first; nothing below may fail before the ledger knows about it.
            if res.new_token_id:
                self.ledger.set_token_id(slot, res.new_token_id)
                rebalanced_to = res.new_token_id
            self.log(
                "rebalance",
                f"{ev.decision.reason} -> #{res.new_token_id}",
                slot,
                res,
                self._aero_reward_usd(res, ev.pos.pool),
            )
        elif res is not None:
            self.decisions.setdefault(slot, {})["simulated"] = " -> ".join(res.stages)
        self.record(slot, ev, row, now, rebalanced_to)

    def record(self, slot: str, ev: Evaluation, row: Any, now: float, rebalanced_to: int | None = None) -> None:
        pos, pool = ev.pos, ev.pos.pool
        p = self.known_prices()
        u0, u1 = p.get(pool.token0.address.lower(), 0.0), p.get(pool.token1.address.lower(), 0.0)
        d0, d1 = self.ledger.deposited_amounts(slot)
        hodl = d0 * u0 + d1 * u1
        unclaimed = pos.earned_aero / 1e18 * p.get(addresses.AERO_TOKEN.lower(), 0.0)
        token_id = rebalanced_to or pos.token_id
        # A snapshot taken without both prices would store a value of 0 and book a total loss.
        if u0 and u1 and self.timers.due(f"snap:{slot}", self.cfg.allocator.snapshot_interval_min * 60, now):
            self.ledger.snapshot(slot, token_id, ev.value_usd, hodl, unclaimed)
        lo, hi = pos.price_bounds()
        self.decisions[slot] = {
            **{k: v for k, v in self.decisions.get(slot, {}).items() if k == "simulated"},
            "token_id": token_id,
            "pool": pool.address,
            "pair": f"{pool.token0.symbol}/{pool.token1.symbol}",
            "tick_spacing": pool.tick_spacing,
            "staked": pos.staked,
            "in_range": pos.in_range,
            "range": [lo, hi],
            "price": pool.price,
            "value_usd": ev.value_usd,
            "decision": ev.decision.action.value,
            "reason": ev.decision.reason,
            "_pos": pos,
            "_ev": ev,
            # After a rebalance `_pos` is the burned NFT; compounding waits for the next evaluation.
            "_stale": rebalanced_to is not None,
        }

    def snapshot_now(self, slot: str) -> None:
        """Value the slot's position now and store it, so P&L figures that drive a decision are not 15 min old."""
        self._align_token_id(slot)
        row = self.ledger.slot_row(slot)
        if row is None or row["closed_at"] is not None or row["token_id"] is None:
            return
        pos = self.chain.position(int(row["token_id"]), owner_hint=self.cfg.owner)
        p = self.prices()
        u0, u1 = p.get(pos.pool.token0.address.lower(), 0.0), p.get(pos.pool.token1.address.lower(), 0.0)
        if not (u0 and u1):
            raise RuntimeError("missing USD price for a pool token")
        a0, a1 = pos.human_amounts()
        d0, d1 = self.ledger.deposited_amounts(slot)
        unclaimed = pos.earned_aero / 1e18 * p.get(addresses.AERO_TOKEN.lower(), 0.0)
        self.ledger.snapshot(slot, pos.token_id, a0 * u0 + a1 * u1, d0 * u0 + d1 * u1, unclaimed)

    def _slot_value_usd(self, slot: str) -> float:
        d = self.decisions.get(slot)
        if d and not d.get("_stale") and "value_usd" in d:
            return float(d["value_usd"])
        pnl = self.ledger.pnl(slot)
        return pnl.value_usd if pnl else 0.0

    # ------------------------------------------------------------------ compounding

    def compound_slot(self, slot: str) -> None:
        d = self.decisions.get(slot)
        if not d or d.get("_stale"):
            return
        pos: PositionState = d["_pos"]
        ev: Evaluation = d["_ev"]
        if not pos.in_range:
            return
        a = self.cfg.allocator
        p = self.prices()
        d0, d1 = pos.pool.token0.decimals, pos.pool.token1.decimals
        u0, u1 = p.get(pos.pool.token0.address.lower(), 0.0), p.get(pos.pool.token1.address.lower(), 0.0)
        aero_usd = p.get(addresses.AERO_TOKEN.lower(), 0.0)
        gas_usd = ev.gas_usd  # a full rebalance's worth; a compound is cheaper, so this is conservative
        if pos.staked:
            reward = pos.earned_aero / 1e18 * aero_usd
            if pos.penalty_blocks_left > 0 or reward < max(a.compound_min_usd, a.compound_gas_multiple * gas_usd):
                return
            what = f"${reward:.2f} AERO"
        else:
            fees_usd = pos.fees0 / 10**d0 * u0 + pos.fees1 / 10**d1 * u1
            if fees_usd < max(a.compound_min_usd, a.compound_gas_multiple * gas_usd):
                return
            what = f"${fees_usd:.2f} fees"
        if not self.acting():
            self.log("skip", f"would compound {what} ({self.paused_reason})", slot)
            return
        blocks = self.engine.pool_blocks(pos.pool, live=True)
        if blocks:
            self.log("skip", f"compounding waits: {'; '.join(blocks)}", slot)
            return
        toks = runner_tokens(pos.pool.token0.address, pos.pool.token1.address)
        if pos.staked:
            res = self._send(lambda: self.rb.claim(pos, self.runner(toks, pos.pool.address)))
            claimed = res.aero_claimed
            self.log("claim", f"claimed {claimed / 1e18:.4f} AERO", slot, res, reward_usd=claimed / 1e18 * aero_usd)
            if claimed <= 0:
                return
            amt0, amt1 = self._convert_into(pos.pool, addresses.AERO_TOKEN, claimed, slot)
        else:
            res = self._send(lambda: self.rb.collect(pos, self.runner(toks, pos.pool.address)))
            amt0, amt1 = (max(0, x) for x in res.amounts_in_position)
            # Booked from the amounts that actually arrived, not from the estimate that triggered the collect.
            got_usd = amt0 / 10**d0 * u0 + amt1 / 10**d1 * u1
            self.log("collect", f"collected fees worth ${got_usd:.2f}", slot, res, reward_usd=got_usd)
        if amt0 <= 0 and amt1 <= 0:
            return
        fresh = self.chain.position(pos.token_id, owner_hint=self.cfg.owner)
        if not fresh.in_range:
            self.log("skip", "price left the range during the compound; the coins stay in the wallet", slot)
            return
        why = self._preflight(fresh.pool, lambda sim: self.rb.topup(fresh, amt0, amt1, sim, u0, u1))
        if why:
            self.log("skip", f"compound not sent: {why}; the coins stay in the wallet", slot)
            return
        try:
            res = self._send(lambda: self.rb.topup(fresh, amt0, amt1, self.runner(toks, pos.pool.address), u0, u1))
        except RebalanceError as e:
            if "increase" in e.partial.stages:  # the liquidity was added; only the restake failed
                self._book_topup(slot, e.partial, pos.pool, u0, u1)
            raise
        # (The AERO that accrued in the seconds between the claim and this unstake is not booked: it is dust.)
        usd = self._book_topup(slot, res, pos.pool, u0, u1)
        self.log("compound", f"added ${usd:.2f} back into #{pos.token_id}", slot, res)

    def _book_topup(self, slot: str, res: RebalanceResult, pool: PoolState, u0: float, u1: float) -> float:
        e0, e1 = res.amounts_in_position
        h0, h1 = e0 / 10**pool.token0.decimals, e1 / 10**pool.token1.decimals
        usd = h0 * u0 + h1 * u1
        self.ledger.flow(slot, "topup", h0, h1, usd)
        return usd

    def _conversion_price_problem(
        self, route: PoolState, token: str, target: str, amount: int, expected_out: float
    ) -> str | None:
        """Compare what the pool would pay with market prices; None when they agree."""
        p = self.prices()
        fwd = token.lower() == route.token0.address.lower()
        dec_in = (route.token0 if fwd else route.token1).decimals
        dec_out = (route.token1 if fwd else route.token0).decimals
        pin, pout = p.get(token.lower(), 0.0), p.get(target.lower(), 0.0)
        if not (pin and pout):
            return "no USD price for both tokens"
        in_usd = amount / 10**dec_in * pin
        out_usd = expected_out / 10**dec_out * pout
        if out_usd < in_usd * (1 - CONVERT_PRICE_TOLERANCE):
            return (
                f"the pool would pay ${out_usd:.2f} for ${in_usd:.2f} "
                f"(more than {CONVERT_PRICE_TOLERANCE:.0%} below market)"
            )
        return None

    def _convert_into(self, pool: PoolState, token: str, amount: int, slot: str | None) -> tuple[int, int]:
        """Turn `amount` of `token` into the pool's token(s); returns (amount0, amount1) designated for it.

        The output is what the swap itself produced (the runner's balance change), never a wallet balance diff,
        so it is the same measure in dry run (simulated) and live (read at the receipt's block).
        """
        t0, t1 = pool.token0.address, pool.token1.address
        if token.lower() == t0.lower():
            return amount, 0
        if token.lower() == t1.lower():
            return 0, amount
        problem = None
        for target in (t0, t1):
            route = self.best_direct_pool(token, target)
            if route is None:
                continue
            raw_p = route.raw_price
            fwd = token.lower() == route.token0.address.lower()
            # Output is the other token of the route: token1 when selling token0, token0 when selling token1.
            expected = amount * raw_p * (1 - route.fee) if fwd else amount / raw_p * (1 - route.fee)
            problem = self._conversion_price_problem(route, token, target, amount, expected)
            if problem:
                continue
            min_out = int(expected * (1 - self.cfg.execution.max_slippage_bps / 1e4))
            tokens = runner_tokens(t0, t1)
            if Web3.to_checksum_address(token) not in tokens:
                tokens = tokens + [Web3.to_checksum_address(token)]
            runner = self.runner(tokens, route.address)
            res = self._send(self.rb.swap_exact, route, Web3.to_checksum_address(token), amount, runner, min_out)
            got = res.amount_out
            self.log(
                "swap",
                f"{amount} {KNOWN_TOKENS.get(token.lower(), token[:8])} -> {got} "
                f"{KNOWN_TOKENS.get(target.lower(), target[:8])}",
                slot,
                res,
            )
            if got <= 0:
                return 0, 0
            return (got, 0) if target.lower() == t0.lower() else (0, got)
        why = f"conversion refused: {problem}" if problem else "no direct pool to convert"
        self.log("skip", f"{why} ({token[:8]} into the pool's tokens); left in wallet", slot)
        return 0, 0

    # ------------------------------------------------------------------ allocation

    def scout_deposit_usd(self, wallet: dict[str, Any]) -> float:
        """The size to score pools at: what one arm of an experiment would get. Gas is a fixed cost, so a pool scored
        at the whole wallet looks better than it is for a third of it. A lone, larger position only does better."""
        a = self.cfg.allocator
        total = sum(t["usd"] for t in wallet["tokens"])
        return max(a.min_position_usd, min(a.max_position_usd, total / a.max_arms))

    def allocate(self, wallet: dict[str, Any]) -> None:
        if self.live and self.killed:
            if self.timers.due("alloc-killed", 6 * 3600, time.time()):
                self.log("skip", "allocation paused: kill switch engaged")
            return
        a = self.cfg.allocator
        weth = next((t for t in wallet["tokens"] if t["symbol"] == "WETH"), None)
        need = gas_topup_needed(wallet["eth"], weth["amount"] if weth else 0.0, a)
        if need > 0 and weth is not None:
            if self.acting():
                amount = min(int(need * 1e18), int(weth["raw"]))  # float round-off must not exceed the balance
                res = self._send(
                    lambda: self.rb.unwrap_weth(
                        amount, self.runner(runner_tokens(addresses.WETH, addresses.AERO_TOKEN), None)
                    )
                )
                self.log("unwrap", f"unwrapped {amount / 1e18:.6f} WETH for gas", None, res)
                wallet = self.read_wallet()  # the idle amounts below must not include the WETH just unwrapped
            elif self.timers.due("unwrap-dry", 6 * 3600, time.time()):
                self.log("skip", f"would unwrap {need:.6f} WETH for gas ({self.paused_reason})")
        doc = load_scout(self.root / "scout.json")
        if not doc:
            self.log("skip", "allocation waits for the first scout run")
            return
        age = time.time() - float(doc.get("generated_at") or 0)
        if age > SCOUT_MAX_AGE_INTERVALS * a.scout_interval_h * 3600:
            if self.timers.due("alloc-stale", 6 * 3600, time.time()):
                self.log("skip", f"scout data is {age / 3600:.1f} h old; allocation waits for a fresh scout run")
            return
        idle = self.idle_tokens(wallet)
        idle_usd = sum(t["idle_usd"] for t in idle)
        # From the ledger, not from this process's last evaluations: a slot whose evaluation failed this tick, or
        # one that was just closed, must still (or no longer) count against the caps.
        open_rows = self.ledger.open_slots()
        deployed = sum(self._slot_value_usd(r["slot"]) for r in open_rows)
        held = {r["pool"] for r in open_rows}
        plan = plan_allocation(doc["pools"], idle_usd, deployed, a, held, scored_usd=doc.get("deposit_usd"))
        if not plan.arms:
            if self.timers.due("alloc-reason", 6 * 3600, time.time()):
                self.log("skip", f"idle ${idle_usd:,.2f}: {plan.reason}")
            return
        exp_id = time.strftime("exp-%Y%m%d-%H%M") if plan.experiment else None
        for arm in plan.arms:
            self._check_stop()
            if self.live and self.killed:
                self.log("skip", "allocation stopped: kill switch engaged")
                break
            try:
                self.deploy_arm(arm, idle, exp_id, plan.reason)
            except Exception as e:  # noqa: BLE001 - one failed arm must not stop the loop
                partial = e.partial if isinstance(e, RebalanceError) else None
                slot = str(partial.new_token_id) if partial and partial.new_token_id else None
                self.log("error", f"deploy into {arm.candidate.pair} failed: {e}", slot, partial)
                traceback.print_exc()

    def deploy_arm(self, arm: Any, idle: list[dict[str, Any]], exp_id: str | None, exp_note: str = "") -> None:
        c = arm.candidate
        pool = self.chain.pool_state(c.pool)
        p = self.prices()
        u0, u1 = p.get(pool.token0.address.lower(), 0.0), p.get(pool.token1.address.lower(), 0.0)
        if not (u0 and u1):
            raise RuntimeError("missing USD price for a pool token")
        live = self.acting()
        if live:
            blocks = self.engine.pool_blocks(pool, live=True)
            if blocks:
                self.log("skip", f"not deploying into {c.pair}: {'; '.join(blocks)}")
                return
        remaining = arm.usd
        amt0 = amt1 = 0
        # Prefer the pool's own tokens, then convert other idle coins.
        ordered = sorted(
            idle, key=lambda t: t["address"].lower() not in (pool.token0.address.lower(), pool.token1.address.lower())
        )
        for t in ordered:
            if remaining <= 0.01 or t["idle_usd"] <= 0:
                continue
            take_usd = min(remaining, t["idle_usd"])
            if take_usd >= t["idle_usd"]:
                take_raw = t["idle_raw"]  # all of it: exact, no float round-trip
            else:
                take_raw = min(t["idle_raw"], int(t["idle_raw"] * take_usd / t["idle_usd"]))
            if take_raw <= 0:
                continue
            a0, a1 = self._convert_into(pool, t["address"], take_raw, None)
            amt0, amt1 = amt0 + a0, amt1 + a1
            t["idle_usd"] -= take_usd
            t["idle_raw"] -= take_raw
            remaining -= take_usd
        if amt0 <= 0 and amt1 <= 0:
            self.log("skip", f"nothing usable to deploy into {c.pair}")
            return
        # The conversions took seconds; size the range and anchor the min-outs on the pool as it is now.
        pool = self.chain.pool_state(c.pool)
        rng = target_range(pool.tick, pool.tick_spacing, math.log1p(c.half_width_pct / 100))
        stake = c.best_mode == "aero" and pool.gauge_alive
        toks = runner_tokens(pool.token0.address, pool.token1.address)
        if not live:
            b0, b1 = self.chain.erc20_balances(self.cfg.owner, [pool.token0.address, pool.token1.address])
            if b0 < amt0 or b1 < amt1:
                # A conversion was only simulated, so the wallet does not hold its output and the deposit cannot
                # be simulated end to end. Say so instead of logging a revert that real funds would not hit.
                self.log("skip", f"would convert and deploy ~${arm.usd - remaining:,.2f} into {c.pair} (dry-run)")
                return
            res = self.rb.deploy(
                pool, rng, stake, amt0, amt1, SimRunner(self.chain, self.cfg.owner, toks, pool.address), u0, u1
            )
            h0, h1 = (
                x / 10**d
                for x, d in zip(res.amounts_in_position, (pool.token0.decimals, pool.token1.decimals), strict=True)
            )
            self.log(
                "skip",
                f"would deploy ${h0 * u0 + h1 * u1:,.2f} into {c.pair} ±{c.half_width_pct:.3f}% "
                f"({'staked' if stake else 'fees'}) ({self.paused_reason}, simulated OK)",
            )
            return
        why = self._preflight(pool, lambda sim: self.rb.deploy(pool, rng, stake, amt0, amt1, sim, u0, u1))
        if why:
            self.log("skip", f"deploy into {c.pair} not sent: {why}; the coins stay in the wallet")
            return
        opened: list[tuple[str, float]] = []

        def on_stage(stage: str, partial: RebalanceResult) -> None:
            # Track the NFT the moment it exists. If the process dies between the mint and the stake, the ledger
            # (and so the next start) already knows the position; otherwise it would sit in the wallet unmanaged.
            if stage == "mint" and partial.new_token_id and not opened:
                opened.append(self._open_slot(pool, c.pair, partial, exp_id, exp_note, u0, u1))

        try:
            res = self._send(
                lambda: self.rb.deploy(
                    pool, rng, stake, amt0, amt1, self.runner(toks, pool.address), u0, u1, on_stage=on_stage
                )
            )
        except RebalanceError as e:
            if e.partial.new_token_id and not opened:  # minted, then something failed: the NFT is real
                opened.append(self._open_slot(pool, c.pair, e.partial, exp_id, exp_note, u0, u1))
            raise
        slot, usd = opened[0] if opened else self._open_slot(pool, c.pair, res, exp_id, exp_note, u0, u1)
        self.log(
            "deploy",
            f"${usd:,.2f} into {c.pair} ±{c.half_width_pct:.3f}% "
            f"(model {c.model_apr:+.1f}%, backtest {c.backtest_apr:+.1f}%)",
            slot,
            res,
        )

    def _open_slot(
        self, pool: PoolState, pair: str, res: RebalanceResult, exp_id: str | None, exp_note: str, u0: float, u1: float
    ) -> tuple[str, float]:
        """Register a position the daemon just minted. The experiment row is created only now, so an allocation
        that deploys nothing (dry run, kill switch, every arm failing) leaves no empty experiment behind."""
        assert res.new_token_id is not None
        slot = str(res.new_token_id)
        if exp_id:
            self.ledger.start_experiment(exp_id, exp_note)
        self.ledger.open_slot(
            slot,
            pool.address,
            pair,
            pool.token0.address,
            pool.token1.address,
            pool.token0.decimals,
            pool.token1.decimals,
            res.new_token_id,
            experiment=exp_id,
        )
        e0, e1 = res.amounts_in_position
        h0, h1 = e0 / 10**pool.token0.decimals, e1 / 10**pool.token1.decimals
        usd = h0 * u0 + h1 * u1
        self.ledger.flow(slot, "deposit", h0, h1, usd)
        return slot, usd

    def graduate(self) -> None:
        if self.live and self.killed:
            return
        a = self.cfg.allocator
        for exp in self.ledger.experiments():
            if exp["status"] != "running" or time.time() - exp["started_at"] < a.experiment_days * 86400:
                continue
            try:  # the ranking drives which position is closed: value every arm now, not 15 min ago
                for s in exp["arms"]:
                    self.snapshot_now(s)
            except Exception as e:  # noqa: BLE001
                self.log("error", f"graduation of {exp['id']} waits: cannot value an arm ({type(e).__name__}: {e})")
                continue
            arms = [x for x in (self.ledger.pnl(s) for s in exp["arms"]) if x]
            winner, losers = plan_graduation(exp, arms, a)
            if winner is None:
                continue
            all_closed = True
            for slot in losers:
                self._check_stop()
                row = self.ledger.slot_row(slot)
                if not row or row["closed_at"] is not None:
                    continue
                if not self.acting():
                    self.log("skip", f"would close losing arm {slot} of {exp['id']} ({self.paused_reason})", slot)
                    all_closed = False
                    continue
                try:
                    self._close_arm(row, exp["id"], winner)
                except Exception as e:  # noqa: BLE001 - the other losers and experiments go on; funds stay put
                    partial = e.partial if isinstance(e, RebalanceError) else None
                    self.log("error", f"closing losing arm {slot} failed: {e}", slot, partial)
                    all_closed = False
            if all_closed:
                self.ledger.graduate(exp["id"], winner)
                self.log("graduate", f"{exp['id']}: winner {winner}", winner)

    def _close_arm(self, row: Any, exp_id: str, winner: str) -> None:
        slot = row["slot"]
        self._align_token_id(slot)
        token_id = int(self.ledger.slot_row(slot)["token_id"])
        try:
            pos, res, _ = self.engine.withdraw(token_id, True, self.signer)
        except PositionGone:
            self._close_gone(slot)
            return
        pr = self.known_prices()
        r0, r1 = res.amounts_in_position
        h0, h1 = r0 / 10**pos.pool.token0.decimals, r1 / 10**pos.pool.token1.decimals
        usd = h0 * pr.get(pos.pool.token0.address.lower(), 0) + h1 * pr.get(pos.pool.token1.address.lower(), 0)
        self.ledger.flow(slot, "withdraw", h0, h1, usd)
        self.ledger.close_slot(slot)
        self.decisions.pop(slot, None)
        self.log(
            "withdraw",
            f"closed losing arm of {exp_id} (winner {winner})",
            slot,
            res,
            self._aero_reward_usd(res, pos.pool),
        )

    # ------------------------------------------------------------------ status

    def write_status(self, wallet: dict[str, Any]) -> None:
        positions = []
        for row in self.ledger.open_slots():
            slot = row["slot"]
            pnl = self.ledger.pnl(slot)
            d = {k: v for k, v in self.decisions.get(slot, {}).items() if not k.startswith("_")}
            if pnl is None:
                continue
            positions.append(
                {
                    "slot": slot,
                    **d,
                    "value_usd": d.get("value_usd", pnl.value_usd),
                    "deposited_usd": pnl.deposited_usd,
                    "withdrawn_usd": pnl.withdrawn_usd,
                    "hodl_usd": pnl.hodl_usd,
                    "rewards_usd": pnl.rewards_usd,
                    "gas_usd": pnl.gas_usd,
                    "pnl_usd": pnl.pnl_usd,
                    "pnl_vs_hodl_usd": pnl.pnl_vs_hodl_usd,
                    "apr_realized": pnl.apr_realized,
                    "opened_at": pnl.opened_at,
                    "experiment": pnl.experiment,
                }
            )
        experiments = []
        for exp in self.ledger.experiments():
            arms = []
            for s in exp["arms"]:
                x = self.ledger.pnl(s)
                if x:
                    arms.append(
                        {
                            "slot": s,
                            "pair": x.pair,
                            "pool": x.pool,
                            "deposited_usd": x.deposited_usd,
                            "pnl_usd": x.pnl_usd,
                            "pnl_pct": x.pnl_usd / x.deposited_usd * 100 if x.deposited_usd else 0.0,
                            "apr_realized": x.apr_realized,
                            "closed": x.closed_at is not None,
                        }
                    )
            experiments.append({**exp, "arms": arms})
        idle = self.idle_tokens(wallet)
        doc = {
            "schema": STATUS_SCHEMA,
            "generated_at": time.time(),
            "mode": "live" if self.live else "dry-run",
            "killed": self.killed,
            "owner": self.cfg.owner,
            "last_scout_at": (load_scout(self.root / "scout.json") or {}).get("generated_at"),
            "wallet": {
                "eth": wallet["eth"],
                "idle_usd": sum(t["idle_usd"] for t in idle),
                "deployed_usd": sum(p.get("value_usd", 0.0) for p in positions),
                "tokens": [
                    {
                        "symbol": t["symbol"],
                        "address": t["address"],
                        "amount": t["amount"],
                        "usd": t["usd"],
                        "idle": any(i["address"] == t["address"] for i in idle),
                    }
                    for t in wallet["tokens"]
                    if t["amount"] > 0
                ],
            },
            "positions": positions,
            "experiments": experiments,
            "actions": self.ledger.recent_events(50),
        }
        atomic_write_json(self.root / "status.json", doc)

    # ------------------------------------------------------------------ loop

    def tick(self) -> None:
        now = time.time()
        a = self.cfg.allocator
        self._check_stop()
        self.chain.check_fresh()
        wallet = self.read_wallet()
        if self.timers.due("wallet", 600, now):
            self.ledger.wallet_snapshot(wallet["human"])
        self.register_config_positions()
        for row in self.ledger.open_slots():
            try:
                self.manage_slot(row["slot"], now)
            except Exception as e:  # noqa: BLE001 - keep managing the other slots
                self.log("error", f"{type(e).__name__}: {e}", row["slot"])
                traceback.print_exc()
            self._check_stop()
        self._check_stop()
        if self.timers.due("compound", a.compound_interval_h * 3600, now):
            for row in self.ledger.open_slots():
                try:
                    self.compound_slot(row["slot"])
                except Exception as e:  # noqa: BLE001
                    partial = e.partial if isinstance(e, RebalanceError) else None
                    self.log("error", f"compound failed: {e}", row["slot"], partial)
                self._check_stop()
        if a.enabled and self.timers.due("scout", a.scout_interval_h * 3600, now):
            try:
                deposit = self.scout_deposit_usd(wallet)
                run_scout(
                    self.chain,
                    self.market,
                    deposit,
                    self.cfg.strategy,
                    top_by_volume=a.scout_top_by_volume,
                    out=self.root / "scout.json",
                    gas_units=self.cfg.gas_units_estimate,
                    l1_fee_usd=self.cfg.l1_fee_usd_estimate,
                    max_seconds=SCOUT_BUDGET_S,
                    progress=lambda _msg: self._check_stop(),  # a stop request ends a long scan between pools
                )
                self.log("scout", f"scored pools for a ${deposit:,.2f} deposit")
            except Exception as e:  # noqa: BLE001
                self.log("error", f"scout failed: {e}")
        self._check_stop()
        if a.enabled and self.timers.due("allocate", a.allocate_interval_h * 3600, now):
            try:
                self.allocate(self.read_wallet())
            except Exception as e:  # noqa: BLE001
                self.log("error", f"allocation failed: {e}")
                traceback.print_exc()
            try:  # a failed allocation must not stop a finished experiment from graduating
                self.graduate()
            except Exception as e:  # noqa: BLE001
                self.log("error", f"graduation failed: {e}")
                traceback.print_exc()
        self.write_status(self.read_wallet())

    def run(self, once: bool = False) -> None:
        # While idle (between sequences) a stop request must not wait for the poll interval or kill the process
        # between a transaction and its bookkeeping: handlers set a flag, the loop exits between steps.
        handlers: dict[int, Any] = {}
        if threading.current_thread() is threading.main_thread():
            handlers = {sig: signal.signal(sig, self._on_signal) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            while True:
                try:
                    self.tick()
                except Exception as e:  # noqa: BLE001 - the loop survives RPC outages; funds stay where they are
                    self.log("error", f"tick failed: {type(e).__name__}: {e}")
                    traceback.print_exc()
                self._check_stop()
                if once:
                    return
                self._wake.wait(max(self.cfg.poll_seconds, self.cfg.safety.min_check_interval_s))
                self._check_stop()
        finally:
            for sig, old in handlers.items():
                signal.signal(sig, old)
