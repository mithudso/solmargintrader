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
"""

from __future__ import annotations

import math
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from web3 import Web3

from . import addresses
from .allocator import gas_topup_needed, plan_allocation, plan_graduation
from .chain import ZERO, AeroChain, PoolState, PositionGone, PositionState
from .config import Config
from .engine import Engine, Evaluation
from .executor import LiveRunner, RebalanceError, Rebalancer, RebalanceResult, SimRunner, runner_tokens
from .ledger import Ledger
from .market import MarketData
from .metrics import KNOWN_TOKENS
from .scout import load_scout, run_scout
from .state import atomic_write_json, home
from .strategy import target_range

STATUS_SCHEMA = "aero-lp-status/1"
SYMBOL_TO_ADDR = {v: Web3.to_checksum_address(k) for k, v in KNOWN_TOKENS.items()}


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
        self.ledger = Ledger(self.root / "ledger.sqlite")
        self.rb = Rebalancer(self.chain, cfg.owner, cfg.execution)
        self.timers = Timers()
        self.decisions: dict[str, dict[str, Any]] = {}
        self.wallet: dict[str, Any] = {}

    # ------------------------------------------------------------------ helpers

    @property
    def killed(self) -> bool:
        return (self.root / "KILL").exists()

    def acting(self) -> bool:
        return self.live and not self.killed

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
            gas_usd = res.fee_wei / 1e18 * self.prices().get(addresses.WETH.lower(), 0.0)
        self.ledger.event(
            kind, slot, gas_usd=gas_usd, reward_usd=reward_usd, detail=detail, tx=res.tx_hashes if res else None
        )
        print(time.strftime("%H:%M:%S"), kind, slot or "-", detail, flush=True)

    def prices(self) -> dict[str, float]:
        tokens = [SYMBOL_TO_ADDR[s] for s in self.cfg.allocator.allowed_tokens if s in SYMBOL_TO_ADDR]
        return self.market.token_prices_usd(tokens + [addresses.AERO_TOKEN, addresses.WETH])

    def runner(self, tokens: list[str], pool: str | None) -> Any:
        if self.acting():
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

    # ------------------------------------------------------------------ wallet

    def read_wallet(self) -> dict[str, Any]:
        owner = Web3.to_checksum_address(self.cfg.owner)
        syms = [s for s in self.cfg.allocator.allowed_tokens if s in SYMBOL_TO_ADDR]
        addrs = [SYMBOL_TO_ADDR[s] for s in syms]
        raw = self.chain.erc20_balances(owner, addrs) if addrs else []
        prices = self.prices()
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
                out.append({**t, "idle_amount": idle, "idle_raw": int(t["raw"] * frac), "idle_usd": t["usd"] * frac})
        return out

    # ------------------------------------------------------------------ positions

    def register_config_positions(self) -> None:
        """Positions listed in config.token_ids enter the ledger at their current value the first time."""
        for tid in self.cfg.token_ids:
            if self.ledger.slot_row(str(tid)) is not None:
                continue
            try:
                pos = self.chain.position(tid, owner_hint=self.cfg.owner)
            except PositionGone:
                continue
            p = self.prices()
            a0, a1 = pos.human_amounts()
            usd = a0 * p.get(pos.pool.token0.address.lower(), 0) + a1 * p.get(pos.pool.token1.address.lower(), 0)
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

    def manage_slot(self, slot: str, now: float) -> None:
        row = self.ledger.slot_row(slot)
        try:
            ev, res = self.engine.step(int(slot), live=self.acting(), signer=self.signer if self.acting() else None)
        except PositionGone:
            self.ledger.close_slot(slot)
            self.log("closed", "position no longer exists (closed outside the daemon)", slot)
            return
        except RebalanceError as e:
            self.log("error", f"rebalance failed: {e}", slot, e.partial)
            if e.partial.new_token_id:
                self.ledger.set_token_id(slot, e.partial.new_token_id)
            return
        p = self.prices()
        if res is not None and self.acting():
            reward = res.aero_claimed / 1e18 * p.get(addresses.AERO_TOKEN.lower(), 0.0)
            if res.new_token_id:
                self.ledger.set_token_id(slot, res.new_token_id)
            self.log("rebalance", f"{ev.decision.reason} -> #{res.new_token_id}", slot, res, reward)
        elif res is not None:
            self.decisions.setdefault(slot, {})["simulated"] = " -> ".join(res.stages)
        self.record(slot, ev, row, now)

    def record(self, slot: str, ev: Evaluation, row: Any, now: float) -> None:
        pos, pool = ev.pos, ev.pos.pool
        p = self.prices()
        u0, u1 = p.get(pool.token0.address.lower(), 0.0), p.get(pool.token1.address.lower(), 0.0)
        d0, d1 = self.ledger.deposited_amounts(slot)
        hodl = d0 * u0 + d1 * u1
        unclaimed = pos.earned_aero / 1e18 * p.get(addresses.AERO_TOKEN.lower(), 0.0)
        if self.timers.due(f"snap:{slot}", self.cfg.allocator.snapshot_interval_min * 60, now):
            self.ledger.snapshot(slot, pos.token_id, ev.value_usd, hodl, unclaimed)
        lo, hi = pos.price_bounds()
        self.decisions[slot] = {
            **self.decisions.get(slot, {}),
            "token_id": pos.token_id,
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
        }

    # ------------------------------------------------------------------ compounding

    def compound_slot(self, slot: str) -> None:
        d = self.decisions.get(slot)
        if not d:
            return
        pos: PositionState = d["_pos"]
        ev: Evaluation = d["_ev"]
        if not pos.in_range:
            return
        a = self.cfg.allocator
        p = self.prices()
        u0, u1 = p.get(pos.pool.token0.address.lower(), 0.0), p.get(pos.pool.token1.address.lower(), 0.0)
        aero_usd = p.get(addresses.AERO_TOKEN.lower(), 0.0)
        gas_usd = ev.gas_usd  # a full rebalance's worth; a compound is cheaper, so this is conservative
        if pos.staked:
            reward = pos.earned_aero / 1e18 * aero_usd
            if pos.penalty_blocks_left > 0 or reward < max(a.compound_min_usd, a.compound_gas_multiple * gas_usd):
                return
            if not self.acting():
                self.log("skip", f"would compound ${reward:.2f} AERO (dry-run)", slot)
                return
            res = self.rb.claim(
                pos, self.runner(runner_tokens(pos.pool.token0.address, pos.pool.token1.address), pos.pool.address)
            )
            claimed = res.aero_claimed
            self.log("claim", f"claimed {claimed / 1e18:.4f} AERO", slot, res, reward_usd=claimed / 1e18 * aero_usd)
            if claimed <= 0:
                return
            amt0, amt1 = self._convert_into(pos.pool, addresses.AERO_TOKEN, claimed, slot)
        else:
            fees_usd = pos.fees0 / 10**pos.pool.token0.decimals * u0 + pos.fees1 / 10**pos.pool.token1.decimals * u1
            if fees_usd < max(a.compound_min_usd, a.compound_gas_multiple * gas_usd):
                return
            if not self.acting():
                self.log("skip", f"would compound ${fees_usd:.2f} fees (dry-run)", slot)
                return
            res = self.rb.collect(
                pos, self.runner(runner_tokens(pos.pool.token0.address, pos.pool.token1.address), pos.pool.address)
            )
            amt0, amt1 = (max(0, x) for x in res.amounts_in_position)
            self.log("collect", f"collected fees worth ${fees_usd:.2f}", slot, res, reward_usd=fees_usd)
        if amt0 <= 0 and amt1 <= 0:
            return
        fresh = self.chain.position(pos.token_id, owner_hint=self.cfg.owner)
        res = self.rb.topup(
            fresh,
            amt0,
            amt1,
            self.runner(runner_tokens(pos.pool.token0.address, pos.pool.token1.address), pos.pool.address),
            u0,
            u1,
        )
        e0, e1 = res.amounts_in_position
        h0, h1 = e0 / 10**pos.pool.token0.decimals, e1 / 10**pos.pool.token1.decimals
        self.ledger.flow(slot, "topup", h0, h1, h0 * u0 + h1 * u1)
        self.log("compound", f"added ${h0 * u0 + h1 * u1:.2f} back into #{pos.token_id}", slot, res)

    def _convert_into(self, pool: PoolState, token: str, amount: int, slot: str | None) -> tuple[int, int]:
        """Turn `amount` of `token` into the pool's token(s); returns (amount0, amount1) designated for it."""
        t0, t1 = pool.token0.address, pool.token1.address
        if token.lower() == t0.lower():
            return amount, 0
        if token.lower() == t1.lower():
            return 0, amount
        for target in (t0, t1):
            route = self.best_direct_pool(token, target)
            if route is None:
                continue
            raw_p = route.raw_price
            fwd = token.lower() == route.token0.address.lower()
            expected = amount * raw_p * (1 - route.fee) if fwd else amount / raw_p * (1 - route.fee)
            min_out = int(expected * (1 - self.cfg.execution.max_slippage_bps / 1e4))
            tokens = runner_tokens(t0, t1)
            if token not in tokens:
                tokens = tokens + [Web3.to_checksum_address(token)]
            before = self.chain.erc20_balances(self.cfg.owner, [target])[0]
            res = self.rb.swap_exact(
                route, Web3.to_checksum_address(token), amount, self.runner(tokens, route.address), min_out
            )
            got = self.chain.erc20_balances(self.cfg.owner, [target])[0] - before if self.acting() else min_out
            self.log(
                "swap",
                f"{amount} {KNOWN_TOKENS.get(token.lower(), token[:8])} -> "
                f"{KNOWN_TOKENS.get(target.lower(), target[:8])}",
                slot,
                res,
            )
            return (got, 0) if target == t0 else (0, got)
        self.log("skip", f"no direct pool to convert {token[:8]} into the pool's tokens; left in wallet", slot)
        return 0, 0

    # ------------------------------------------------------------------ allocation

    def allocate(self, wallet: dict[str, Any]) -> None:
        a = self.cfg.allocator
        weth = next((t for t in wallet["tokens"] if t["symbol"] == "WETH"), None)
        need = gas_topup_needed(wallet["eth"], weth["amount"] if weth else 0.0, a)
        if need > 0:
            if self.acting():
                res = self.rb.unwrap_weth(
                    int(need * 1e18), self.runner(runner_tokens(addresses.WETH, addresses.AERO_TOKEN), None)
                )
                self.log("unwrap", f"unwrapped {need:.6f} WETH for gas", None, res)
            else:
                self.log("skip", f"would unwrap {need:.6f} WETH for gas (dry-run)")
        doc = load_scout(self.root / "scout.json")
        if not doc:
            self.log("skip", "allocation waits for the first scout run")
            return
        idle = self.idle_tokens(wallet)
        idle_usd = sum(t["idle_usd"] for t in idle)
        deployed = sum(d.get("value_usd", 0.0) for d in self.decisions.values())
        held = {d["pool"] for d in self.decisions.values() if "pool" in d}
        plan = plan_allocation(doc["pools"], idle_usd, deployed, a, held)
        if not plan.arms:
            if self.timers.due("alloc-reason", 6 * 3600, time.time()):
                self.log("skip", f"idle ${idle_usd:,.2f}: {plan.reason}")
            return
        exp_id = None
        if plan.experiment:
            exp_id = time.strftime("exp-%Y%m%d-%H%M")
            self.ledger.start_experiment(exp_id, plan.reason)
        for arm in plan.arms:
            try:
                self.deploy_arm(arm, idle, exp_id)
            except Exception as e:  # noqa: BLE001 - one failed arm must not stop the loop
                partial = e.partial if isinstance(e, RebalanceError) else None
                self.log("error", f"deploy into {arm.candidate.pair} failed: {e}", None, partial)
                traceback.print_exc()

    def deploy_arm(self, arm: Any, idle: list[dict[str, Any]], exp_id: str | None) -> None:
        c = arm.candidate
        pool = self.chain.pool_state(c.pool)
        p = self.prices()
        u0, u1 = p.get(pool.token0.address.lower(), 0.0), p.get(pool.token1.address.lower(), 0.0)
        if not (u0 and u1):
            raise RuntimeError("missing USD price for a pool token")
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
            take_raw = int(t["idle_raw"] * take_usd / t["idle_usd"])
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
        rng = target_range(pool.tick, pool.tick_spacing, math.log1p(c.half_width_pct / 100))
        stake = c.best_mode == "aero" and pool.gauge_alive
        res = self.rb.deploy(
            pool,
            rng,
            stake,
            amt0,
            amt1,
            self.runner(runner_tokens(pool.token0.address, pool.token1.address), pool.address),
            u0,
            u1,
        )
        e0, e1 = res.amounts_in_position
        h0, h1 = e0 / 10**pool.token0.decimals, e1 / 10**pool.token1.decimals
        usd = h0 * u0 + h1 * u1
        if not self.acting():
            self.log(
                "skip",
                f"would deploy ${usd:,.2f} into {c.pair} ±{c.half_width_pct:.3f}% "
                f"({'staked' if stake else 'fees'}) (dry-run, simulated OK)",
            )
            return
        slot = str(res.new_token_id)
        self.ledger.open_slot(
            slot,
            pool.address,
            c.pair,
            pool.token0.address,
            pool.token1.address,
            pool.token0.decimals,
            pool.token1.decimals,
            res.new_token_id,
            experiment=exp_id,
        )
        self.ledger.flow(slot, "deposit", h0, h1, usd)
        self.log(
            "deploy",
            f"${usd:,.2f} into {c.pair} ±{c.half_width_pct:.3f}% "
            f"(model {c.model_apr:+.1f}%, backtest {c.backtest_apr:+.1f}%)",
            slot,
            res,
        )

    def graduate(self) -> None:
        for exp in self.ledger.experiments():
            arms = [x for x in (self.ledger.pnl(s) for s in exp["arms"]) if x]
            winner, losers = plan_graduation(exp, arms, self.cfg.allocator)
            if winner is None:
                continue
            for slot in losers:
                row = self.ledger.slot_row(slot)
                if not row or row["closed_at"] is not None:
                    continue
                if not self.acting():
                    self.log("skip", f"would close losing arm {slot} of {exp['id']} (dry-run)", slot)
                    continue
                pos, res, _ = self.engine.withdraw(int(row["token_id"]), True, self.signer)
                pr = self.prices()
                r0, r1 = res.amounts_in_position
                h0, h1 = r0 / 10**pos.pool.token0.decimals, r1 / 10**pos.pool.token1.decimals
                usd = h0 * pr.get(pos.pool.token0.address.lower(), 0) + h1 * pr.get(pos.pool.token1.address.lower(), 0)
                self.ledger.flow(slot, "withdraw", h0, h1, usd)
                self.ledger.close_slot(slot)
                self.log("withdraw", f"closed losing arm of {exp['id']} (winner {winner})", slot, res)
            if self.acting() or not losers:
                self.ledger.graduate(exp["id"], winner)
                self.log("graduate", f"{exp['id']}: winner {winner}", winner)

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
        if self.timers.due("compound", a.compound_interval_h * 3600, now):
            for row in self.ledger.open_slots():
                try:
                    self.compound_slot(row["slot"])
                except Exception as e:  # noqa: BLE001
                    partial = e.partial if isinstance(e, RebalanceError) else None
                    self.log("error", f"compound failed: {e}", row["slot"], partial)
        if a.enabled and self.timers.due("scout", a.scout_interval_h * 3600, now):
            try:
                deposit = max(a.min_position_usd, sum(t["usd"] for t in wallet["tokens"]))
                run_scout(
                    self.chain,
                    self.market,
                    deposit,
                    self.cfg.strategy,
                    top_by_volume=a.scout_top_by_volume,
                    out=self.root / "scout.json",
                    gas_units=self.cfg.gas_units_estimate,
                    l1_fee_usd=self.cfg.l1_fee_usd_estimate,
                )
                self.log("scout", f"scored pools for a ${deposit:,.2f} deposit")
            except Exception as e:  # noqa: BLE001
                self.log("error", f"scout failed: {e}")
        if a.enabled and self.timers.due("allocate", a.allocate_interval_h * 3600, now):
            try:
                self.allocate(self.read_wallet())
                self.graduate()
            except Exception as e:  # noqa: BLE001
                self.log("error", f"allocation failed: {e}")
                traceback.print_exc()
        self.write_status(self.read_wallet())

    def run(self, once: bool = False) -> None:
        while True:
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001 - the loop survives RPC outages; funds stay where they are
                self.log("error", f"tick failed: {type(e).__name__}: {e}")
                traceback.print_exc()
            if once:
                return
            time.sleep(max(self.cfg.poll_seconds, self.cfg.safety.min_check_interval_s))
