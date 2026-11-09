"""Glue: read chain + market state, decide, preflight-simulate, and (in live mode) execute."""

from __future__ import annotations

import contextlib
import dataclasses
import math
import signal
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from web3 import Web3

from . import abi, addresses, clmath
from .chain import MAX_HEAD_LAG_S, AeroChain, PoolState, PositionState, realized_vol_daily
from .config import Config
from .executor import (
    LiveRunner,
    RebalanceError,
    Rebalancer,
    RebalanceResult,
    SimRunner,
    StageHook,
    gas_cost_usd,
    minted_token_id,
    runner_tokens,
)
from .ledger import Ledger
from .market import (
    MarketData,
    PoolEconomics,
    earn_usd_per_day,
    liquidity_for_usd,
    vol_from_closes,
    with_realized_fees,
)
from .recovery import LedgerRecovery
from .state import SlotState, State
from .strategy import (
    Action,
    CostInputs,
    Decision,
    EarnInputs,
    Range,
    StrategyConfig,
    WidthScore,
    best_width,
    decide,
    half_width_log,
    lvr_fraction_per_day,
    score_widths,
    target_range,
)
from .submissions import SubmissionJournal
from .validation import measured_gas

_signal_scope = threading.local()


def _finite(value: object, *, positive: bool = False) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0)
    )


@dataclass
class Evaluation:
    pos: PositionState
    econ: PoolEconomics
    sigma_daily: float | None
    sigma_source: str
    value_usd: float
    earn_now_usd_day: float
    earn_new: dict[str, float]  # reward mode -> USD/day for the proposed range
    stake_new: bool
    decision: Decision
    twap_deviation_bps: float | None
    gas_usd: float
    notes: list[str] = field(default_factory=list)
    half_width: float = 0.0
    width_scores: dict[str, WidthScore] = field(default_factory=dict)
    lvr_new_usd_day: float = 0.0
    eth_usd: float = 0.0  # 0 = price unavailable (gas cost then excludes the ETH leg)


class Engine:
    def __init__(self, cfg: Config, chain: AeroChain | None = None, market: MarketData | None = None):
        self.cfg = cfg
        self.chain = chain or AeroChain(cfg.rpc_url)
        self.market = market or MarketData()
        self.state = State(cfg.state_file)
        # Called right before any transaction is broadcast; it raises to stop the sequence. The daemon uses it
        # so a kill switch created while a rebalance is being simulated still stops that rebalance.
        self.gate: Callable[[], None] | None = None
        # Called with the signal number when Ctrl-C or SIGTERM arrived during a live sequence. Without it the
        # signal is raised after the sequence, which discards the sequence's result before the caller has booked it.
        self.on_stop: Callable[[int], None] | None = None

    def submission_journal(self) -> SubmissionJournal:
        if not hasattr(self, "journal"):
            self.journal = SubmissionJournal(self.cfg.state_file.with_name("submissions.json"), self.cfg.owner)
        return self.journal

    def recover_submission(self, record: dict[str, Any], group: list[dict[str, Any]]) -> None:
        receipt = record["receipt"]
        if receipt["status"] != 1:
            return
        kind = record["intent"]["kind"]
        if kind == "remove" and not any(r["intent"]["kind"] == "mint" and r["receipt"]["status"] == 1 for r in group):
            for slot in self.state.slots.values():
                if slot.current_token_id == record["intent"]["token_id"] and not any(
                    record["hash"] in h.get("tx", []) for h in slot.history
                ):
                    slot.history.append(
                        {
                            "ts": time.time(),
                            "withdrawn": slot.current_token_id,
                            "tx": [record["hash"]],
                            "stages": ["remove"],
                            "recovered": True,
                        }
                    )
            self.state.save()
            return
        if kind != "mint":
            return
        token_id = minted_token_id(receipt["logs"], addresses.NONFUNGIBLE_POSITION_MANAGER, self.cfg.owner)
        if token_id is None:
            raise RuntimeError("confirmed mint has no verified recipient Transfer receipt")
        pos = self.chain.position(token_id, owner_hint=self.cfg.owner)
        if pos.owner.lower() != self.cfg.owner.lower() or pos.pool.address.lower() != record["pool"].lower():
            raise RuntimeError("confirmed mint ownership or pool does not match the recorded intent")
        old_ids = {r["intent"]["token_id"] for r in group if r["intent"]["kind"] == "remove"}
        for configured in self.cfg.token_ids:
            if configured in old_ids:
                self.state.slot(configured)
        for slot in self.state.slots.values():
            if slot.current_token_id in old_ids or slot.current_token_id == token_id:
                slot.current_token_id = token_id
                if not any(record["hash"] in h.get("tx", []) for h in slot.history):
                    recovered_at = time.time()
                    slot.last_rebalance_ts = recovered_at
                    slot.edge_checks = 0
                    slot.history.append(
                        {"ts": recovered_at, "new": token_id, "tx": [record["hash"]], "recovered": True}
                    )
        self.state.save()

    def reconcile_submissions(self) -> None:
        journal = self.submission_journal()
        recovery_ledger = None

        def apply(record: dict[str, Any], group: list[dict[str, Any]]) -> None:
            nonlocal recovery_ledger
            self.recover_submission(record, group)
            callback = getattr(self, "recovery_handler", None)
            if callback is not None:
                callback(record, group)
            else:
                # CLI calls must not consume the journal without applying the daemon's monetary effects.
                if recovery_ledger is None:
                    recovery_ledger = Ledger(journal.ledger_file())
                tokens = {t for r in group for t in r["tokens"]} | {addresses.AERO_TOKEN, addresses.WETH}
                for r in group:
                    if r["intent"]["kind"] == "mint":
                        tokens.update((r["intent"]["token0"], r["intent"]["token1"]))

                def prices():
                    return self.market.token_prices_usd(list(tokens))

                LedgerRecovery(self.cfg, self.chain, recovery_ledger, prices).apply(record, group)

        try:
            journal.reconcile(self.chain, apply)
        finally:
            if recovery_ledger is not None:
                recovery_ledger.db.close()

    def _live_runner(self, signer: Any, tokens: list[str], pool: str, *, wallet: bool = False) -> LiveRunner:
        return LiveRunner(
            self.chain,
            signer,
            tokens,
            self.cfg.execution,
            pool,
            journal=self.submission_journal(),
            accounting={"scope": "wallet"} if wallet else None,
        )

    def _gate(self) -> None:
        if self.gate is not None:
            self.gate()

    # ------------------------------------------------------------------ inputs

    def sigma(self, pool: str) -> tuple[float | None, str]:
        try:
            s = vol_from_closes(self.market.hourly_closes(pool, 72))
            if s:
                return s, "geckoterminal 72h hourly"
        except Exception:  # noqa: BLE001
            pass
        ticks = self.chain.twap_tick_series(pool, hours=12, step_s=600)
        s = realized_vol_daily(ticks, step_s=600)
        return (s, "onchain 10-min TWAP") if s else (None, "none (fixed width)")

    def twap_deviation_bps(self, pos: PositionState) -> float | None:
        """|spot tick - 10-min TWAP tick|. One tick is a 0.01% price move, so ticks ~= bps."""
        return self.pool_twap_deviation_bps(pos.pool)

    def pool_twap_deviation_bps(self, pool: PoolState) -> float | None:
        p = self.chain._c(pool.address, abi.CL_POOL)
        try:
            cums, _ = p.functions.observe([600, 0]).call(block_identifier=pool.block)
        except Exception:  # noqa: BLE001 - oracle history too short
            return None
        return abs(pool.tick - (cums[1] - cums[0]) / 600)

    def pool_blocks(self, pool: PoolState, live: bool) -> list[str]:
        """Manipulation-guard reasons (empty = clear) for sending a swap or deposit into `pool` now."""
        return self._twap_blocks(self.pool_twap_deviation_bps(pool), live)

    # ------------------------------------------------------------------ evaluate

    def evaluate(self, slot: SlotState) -> Evaluation:
        self.chain.check_fresh()
        pos = self.chain.position(slot.current_token_id, owner_hint=self.cfg.owner)
        if pos.owner.lower() != self.cfg.owner.lower():
            raise RuntimeError(f"token {pos.token_id} belongs to {pos.owner}, not the configured owner")
        pool = pos.pool
        t0, t1 = pool.token0, pool.token1
        prices = self.market.token_prices_usd([t0.address, t1.address, addresses.AERO_TOKEN, addresses.WETH])
        usd0 = prices.get(t0.address.lower(), 0.0)
        usd1 = prices.get(t1.address.lower(), 0.0)
        aero_usd = prices.get(addresses.AERO_TOKEN.lower(), 0.0)
        eth_usd = prices.get(addresses.WETH.lower(), 0.0)
        notes = []
        if not (usd0 and usd1):
            notes.append("missing USD price for a pool token; USD figures are unreliable")

        try:
            info = self.market.pool_info(pool.address)
        except Exception:  # noqa: BLE001
            info = {"volume_24h_usd": 0.0}
            notes.append("GeckoTerminal pool volume unavailable; fee estimate = 0")
        econ = PoolEconomics(
            volume_usd_per_day=info["volume_24h_usd"],
            fee=pool.fee,
            unstaked_fee_share=pool.unstaked_fee_pips / 1e6,
            aero_per_day=self.chain.gauge_aero_per_day(pool.gauge, pool.block),
            aero_usd=aero_usd,
            active_liquidity=pool.liquidity,
            staked_liquidity=pool.staked_liquidity,
            price0_usd=usd0,
            price1_usd=usd1,
            dec0=t0.decimals,
            dec1=t1.decimals,
        )
        econ = with_realized_fees(self.chain, pool.address, pool.block, econ)
        a0, a1 = pos.human_amounts()
        value_usd = a0 * usd0 + a1 * usd1
        sigma, sigma_src = self.sigma(pool.address)
        s = self.cfg.strategy
        gas_usd = gas_cost_usd(
            self.cfg.gas_units_estimate, self.chain.gas_price_wei(), eth_usd, self.cfg.l1_fee_usd_estimate
        )

        def yield_curve(staked: bool) -> Callable[[float], float]:
            def f(w: float) -> float:
                if value_usd <= 0 or (staked and not pool.gauge_alive):
                    return 0.0
                r = target_range(pool.tick, pool.tick_spacing, w)
                liq = liquidity_for_usd(value_usd, pool.sqrt_price_x96, r.tick_lower, r.tick_upper, econ)
                return earn_usd_per_day(liq, staked, True, econ, already_counted=False) / value_usd

            return f

        per_rebalance = (gas_usd / value_usd if value_usd else 0.0) + 0.5 * (
            pool.fee + s.expected_price_impact_bps / 1e4
        )
        modes = {"aero": True, "fees": False}
        best: dict[str, WidthScore] = {}
        for name, staked in modes.items():
            if s.width_mode == "optimal" and sigma:
                best[name] = best_width(score_widths(yield_curve(staked), sigma, per_rebalance, s))
            else:
                hw0 = half_width_log(s, sigma)
                best[name] = score_widths(
                    yield_curve(staked), sigma, per_rebalance, _single_width_cfg(s, hw0), points=1
                )[0]
        mode = self.cfg.reward_mode
        if mode == "keep":
            stake_new = pos.staked
        elif mode == "auto":
            stake_new = pool.gauge_alive and best["aero"].net_frac_day >= best["fees"].net_frac_day
        else:
            stake_new = mode == "aero"
        chosen = best["aero" if stake_new else "fees"]
        hw = chosen.half_width
        proposed = target_range(pool.tick, pool.tick_spacing, hw)
        earn_new = {name: yield_curve(st)(hw) * value_usd for name, st in modes.items()}
        earn_now = earn_usd_per_day(pos.liquidity, pos.staked, pos.in_range, econ, already_counted=True)
        lvr_new = lvr_fraction_per_day(hw, sigma) * value_usd
        cur_hw = (pos.tick_upper - pos.tick_lower) / 2 * clmath.LOG_BASE
        lvr_now = lvr_fraction_per_day(cur_hw, sigma) * value_usd if pos.in_range else 0.0
        if chosen.net_frac_day < 0:
            notes.append(
                f"expected edge is negative at every width (best {chosen.net_frac_day * 365 * 100:+.1f}% APR "
                f"after LVR + rebalance costs): LPing this pool is a bet on low volatility right now"
            )

        # Share of value that must be swapped to reach the new ratio.
        raw_p = pool.raw_price
        target0 = clmath.value0_fraction(
            raw_p, clmath.price_from_tick(proposed.tick_lower), clmath.price_from_tick(proposed.tick_upper)
        )
        have0 = (a0 * usd0) / value_usd if value_usd else 0.0
        cost = CostInputs(
            value_usd=value_usd,
            pool_fee=pool.fee,
            gas_usd=gas_usd,
            swap_fraction=abs(have0 - target0),
            unclaimed_aero_usd=pos.earned_aero / 1e18 * aero_usd,
            penalty_rate=pos.penalty_rate,
            penalty_blocks_left=pos.penalty_blocks_left,
        )
        earn = EarnInputs(
            earn_usd_per_day_new=earn_new["aero" if stake_new else "fees"],
            earn_usd_per_day_current=earn_now,
            lvr_usd_per_day_new=lvr_new,
            lvr_usd_per_day_current=lvr_now,
        )
        d = decide(
            tick=pool.tick,
            current=Range(pos.tick_lower, pos.tick_upper),
            spacing=pool.tick_spacing,
            sigma_daily=sigma,
            cfg=s,
            cost=cost,
            earn=earn,
            consecutive_edge_checks=slot.edge_checks,
            minutes_since_last_rebalance=slot.minutes_since_rebalance(),
            half_width=hw,
        )
        return Evaluation(
            pos,
            econ,
            sigma,
            sigma_src,
            value_usd,
            earn_now,
            earn_new,
            stake_new,
            d,
            self.twap_deviation_bps(pos),
            gas_usd,
            notes,
            half_width=hw,
            width_scores=best,
            lvr_new_usd_day=lvr_new,
            eth_usd=eth_usd,
        )

    # ------------------------------------------------------------------ act

    def _twap_blocks(self, deviation_bps: float | None, live: bool) -> list[str]:
        sc = self.cfg.safety
        if deviation_bps is None or not _finite(deviation_bps):
            # The guard cannot run (oracle history too short, or the RPC call failed). A dry run only reports
            # it; live mode must not trade with the manipulation guard silently off.
            if live:
                return ["10-min TWAP unavailable (short oracle history or RPC error): manipulation guard cannot run"]
            return []
        if deviation_bps > sc.max_twap_deviation_bps:
            return [f"spot is {deviation_bps:.0f} bps from the 10-min TWAP (> {sc.max_twap_deviation_bps})"]
        return []

    def safety_blocks(self, ev: Evaluation, live: bool) -> list[str]:
        sc = self.cfg.safety
        out = self._twap_blocks(ev.twap_deviation_bps, live)
        if live and not all(_finite(p, positive=True) for p in (ev.econ.price0_usd, ev.econ.price1_usd, ev.eth_usd)):
            # With a price missing, value_usd and gas_usd are understated and the two limits below pass vacuously.
            out.append("missing USD price for a pool token or ETH: max_position_usd / max_gas_usd cannot be enforced")
        if live and not all(_finite(v) for v in (ev.value_usd, ev.gas_usd)):
            out.append("invalid position value or gas estimate; safety caps cannot be enforced")
        if live and ev.value_usd > sc.max_position_usd:
            out.append(f"position ${ev.value_usd:,.0f} > safety.max_position_usd ${sc.max_position_usd:,.0f}")
        if live and ev.gas_usd > sc.max_gas_usd:
            out.append(f"gas estimate ${ev.gas_usd:.2f} > safety.max_gas_usd ${sc.max_gas_usd:.2f}")
        return out

    def rebalance(
        self, ev: Evaluation, live: bool, signer: Any = None, on_stage: StageHook | None = None
    ) -> RebalanceResult:
        """Always simulates the full sequence first; broadcasts only when live=True."""
        if live:
            self.reconcile_submissions()
        assert ev.decision.new_range is not None
        pool = ev.pos.pool
        tokens = runner_tokens(pool.token0.address, pool.token1.address)
        rb = Rebalancer(self.chain, self.cfg.owner, self.cfg.execution)
        sim = rb.rebalance(
            ev.pos,
            ev.decision.new_range,
            ev.stake_new,
            SimRunner(self.chain, self.cfg.owner, tokens, pool.address),
            ev.econ.price0_usd,
            ev.econ.price1_usd,
        )
        if not live:
            sim.notes.append("dry run: simulated with eth_simulateV1, nothing signed or broadcast")
            return sim
        if signer is None:
            raise RuntimeError("live mode needs a signer")
        if not _finite(ev.eth_usd, positive=True):
            raise RuntimeError("ETH price unavailable or invalid; cannot enforce safety.max_gas_usd")
        # The gas limit is checked against the simulated gas, not only the config's fixed estimate.
        sim_gas_usd = gas_cost_usd(
            measured_gas(sim.gas_used), self.chain.gas_price_wei(), ev.eth_usd, self.cfg.l1_fee_usd_estimate
        )
        if not _finite(sim_gas_usd):
            raise RuntimeError("invalid simulated gas cost; safety.max_gas_usd cannot be enforced")
        if sim_gas_usd > self.cfg.safety.max_gas_usd:
            raise RuntimeError(
                f"simulated gas ${sim_gas_usd:.2f} > safety.max_gas_usd ${self.cfg.safety.max_gas_usd:.2f}"
            )
        # The simulation ignores balances, so check the wallet can pay for gas on every stage (3x margin);
        # running dry after the old NFT is burned would strand the funds.
        need_wei = 3 * sum(sim.gas_used.values()) * self.chain.gas_price_wei()
        have_wei = int(self.chain.w3.eth.get_balance(Web3.to_checksum_address(self.cfg.owner)))
        if have_wei < need_wei:
            raise RuntimeError(
                f"wallet holds {have_wei / 1e18:.6f} ETH, below the {need_wei / 1e18:.6f} ETH gas reserve"
            )
        # Re-check everything time-sensitive on state read right before sending.
        self.chain.check_fresh()
        fresh = self.chain.position(ev.pos.token_id, owner_hint=self.cfg.owner)
        if fresh.owner.lower() != self.cfg.owner.lower():
            raise RuntimeError(f"token {fresh.token_id} belongs to {fresh.owner}, not the configured owner")
        age = time.time() - fresh.pool.timestamp
        if age > MAX_HEAD_LAG_S:
            raise RuntimeError(f"position read at a block {age:.0f}s old (> {MAX_HEAD_LAG_S}s); RPC is stale")
        if not ev.decision.new_range.contains(fresh.pool.tick):
            raise RuntimeError("price left the proposed range since evaluation; re-evaluate before sending")
        blocks = self._twap_blocks(self.twap_deviation_bps(fresh), live=True)
        if blocks:
            raise RuntimeError("blocked before broadcast: " + "; ".join(blocks))
        fresh_prices = self.market.token_prices_usd([fresh.pool.token0.address, fresh.pool.token1.address])
        u0, u1 = (fresh_prices.get(t.address.lower(), 0.0) for t in (fresh.pool.token0, fresh.pool.token1))
        if not all(_finite(p, positive=True) for p in (u0, u1)):
            raise RuntimeError("fresh USD price unavailable or invalid; cannot enforce safety.max_position_usd")
        a0, a1 = fresh.human_amounts()
        fresh_value = a0 * u0 + a1 * u1
        if not _finite(fresh_value) or fresh_value > self.cfg.safety.max_position_usd:
            raise RuntimeError(
                f"fresh position value ${fresh_value} exceeds safety.max_position_usd "
                f"${self.cfg.safety.max_position_usd}"
            )
        if not any(slot.current_token_id == fresh.token_id for slot in self.state.slots.values()):
            self.state.slot(fresh.token_id)
        self.state.save()  # persist the old-slot mapping before a burn or ambiguous mint can be broadcast
        self._gate()
        with defer_sigint(self.on_stop):
            return rb.rebalance(
                fresh,
                ev.decision.new_range,
                ev.stake_new,
                self._live_runner(signer, tokens, pool.address),
                u0,
                u1,
                on_stage=on_stage,
            )

    def withdraw(self, token_id: int, live: bool, signer: Any = None) -> tuple[PositionState, RebalanceResult, float]:
        """Exit `token_id` to the wallet. Always simulates first; broadcasts only when live=True.

        Returns (position before exit, result, simulated gas in USD).
        """
        if live:
            self.reconcile_submissions()
        self.chain.check_fresh()
        pos = self.chain.position(token_id, owner_hint=self.cfg.owner)
        if pos.owner.lower() != self.cfg.owner.lower():
            raise RuntimeError(f"token {token_id} belongs to {pos.owner}, not the configured owner")
        tokens = runner_tokens(pos.pool.token0.address, pos.pool.token1.address)
        rb = Rebalancer(self.chain, self.cfg.owner, self.cfg.execution)
        sim = rb.withdraw(pos, SimRunner(self.chain, self.cfg.owner, tokens, pos.pool.address))
        eth_usd = self.market.token_prices_usd([addresses.WETH]).get(addresses.WETH.lower(), 0.0)
        if live and not _finite(eth_usd, positive=True):
            raise RuntimeError("ETH price unavailable or invalid; cannot enforce safety.max_gas_usd")
        sim_gas = measured_gas(sim.gas_used)
        sim_gas_usd = gas_cost_usd(sim_gas, self.chain.gas_price_wei(), eth_usd, self.cfg.l1_fee_usd_estimate)
        if not live:
            sim.notes.append("dry run: simulated with eth_simulateV1, nothing signed or broadcast")
            return pos, sim, sim_gas_usd
        if signer is None:
            raise RuntimeError("live mode needs a signer")
        if not eth_usd:
            raise RuntimeError("ETH price unavailable; cannot enforce safety.max_gas_usd")
        if not _finite(sim_gas_usd):
            raise RuntimeError("invalid simulated gas cost; safety.max_gas_usd cannot be enforced")
        if sim_gas_usd > self.cfg.safety.max_gas_usd:
            raise RuntimeError(
                f"simulated gas ${sim_gas_usd:.2f} > safety.max_gas_usd ${self.cfg.safety.max_gas_usd:.2f}"
            )
        need_wei = 3 * sim_gas * self.chain.gas_price_wei()
        have_wei = int(self.chain.w3.eth.get_balance(Web3.to_checksum_address(self.cfg.owner)))
        if have_wei < need_wei:
            raise RuntimeError(
                f"wallet holds {have_wei / 1e18:.6f} ETH, below the {need_wei / 1e18:.6f} ETH gas reserve"
            )
        fresh = self.chain.position(token_id, owner_hint=self.cfg.owner)
        self.state.save()
        self._gate()
        with defer_sigint(self.on_stop):
            try:
                res = rb.withdraw(fresh, self._live_runner(signer, tokens, pos.pool.address))
            except RebalanceError as e:
                self._record_withdraw(token_id, e.partial, error=str(e))
                raise
            self._record_withdraw(token_id, res)
        return pos, res, sim_gas_usd

    def _record_withdraw(self, token_id: int, result: RebalanceResult, error: str = "") -> None:
        for slot in self.state.slots.values():
            if slot.current_token_id == token_id:
                entry: dict[str, Any] = {
                    "ts": time.time(),
                    "withdrawn": token_id,
                    "tx": result.tx_hashes,
                    "stages": result.stages,
                }
                if error:
                    entry["error"] = error
                slot.history.append(entry)
        self.state.save()

    def _record_rebalance(self, slot: SlotState, ev: Evaluation, result: RebalanceResult, error: str = "") -> None:
        """Point the slot at the newly minted NFT and log the rebalance."""
        new = ev.decision.new_range
        entry: dict[str, Any] = {
            "ts": time.time(),
            "old": ev.pos.token_id,
            "new": result.new_token_id,
            "range": [new.tick_lower, new.tick_upper] if new else None,
            "tx": result.tx_hashes,
            "staked": result.staked,
        }
        if error:
            entry["error"] = error
            entry["stages"] = result.stages
        slot.history.append(entry)
        if result.new_token_id:
            slot.current_token_id = result.new_token_id
            slot.last_rebalance_ts = time.time()
            slot.edge_checks = 0

    def _record_partial(self, slot: SlotState, ev: Evaluation, err: RebalanceError) -> None:
        """A live rebalance broadcast transactions and then failed. Keep what is on chain on record, and if the
        new NFT was already minted (e.g. only the stake stage failed) track it instead of the burned one."""
        self._record_rebalance(slot, ev, err.partial, error=str(err))

    def step(
        self, configured_id: int, live: bool, signer: Any = None, force: bool = False
    ) -> tuple[Evaluation, RebalanceResult | None]:
        if force and live:
            raise ValueError("force skips the strategy's triggers and is only allowed for dry runs")
        if live:
            self.reconcile_submissions()
        slot = self.state.slot(configured_id)
        ev = self.evaluate(slot)
        if force and ev.decision.action != Action.REBALANCE:
            ev.notes.append(f"forced (strategy said: {ev.decision.action.value} - {ev.decision.reason})")
            ev.decision = forced_decision(ev, self.cfg)
        d = ev.decision
        if d.action == Action.WAIT_CONFIRM:
            slot.edge_checks += 1
        elif d.action == Action.HOLD:
            slot.edge_checks = 0
        result = None
        if d.action == Action.REBALANCE:
            blocks = self.safety_blocks(ev, live)
            if blocks:
                ev.notes.extend(f"BLOCKED: {b}" for b in blocks)
            else:

                def persist(stage: str, partial: RebalanceResult) -> None:
                    # Save the moment the new NFT exists, so a crash before the stake stage or before the
                    # end-of-step save cannot leave the slot pointing at the burned token.
                    if live and stage == "mint" and partial.new_token_id:
                        slot.current_token_id = partial.new_token_id
                        self.state.save()

                with defer_sigint(self.on_stop) if live else contextlib.nullcontext():
                    try:
                        result = self.rebalance(ev, live, signer, on_stage=persist)
                    except RebalanceError as e:
                        if live and e.partial.tx_hashes:
                            self._record_partial(slot, ev, e)
                            self.state.save()
                        raise
                    if live and result.new_token_id:
                        self._record_rebalance(slot, ev, result)
                    self.state.save()

        self.state.save()
        return ev, result


@contextlib.contextmanager
def defer_sigint(on_stop: Callable[[int], None] | None = None) -> Iterator[None]:
    """Hold Ctrl-C and SIGTERM (what `launchctl bootout` sends) until a live transaction sequence finishes;
    interrupting between the burn and the mint would leave the funds out of any position. A second signal
    still exits immediately.

    Afterwards a held signal is handed to `on_stop(signum)` (also when the block raised), so the caller can book
    the result and stop at a safe point. Without `on_stop` it is raised once the block has finished normally
    (KeyboardInterrupt for Ctrl-C, SystemExit for SIGTERM).
    """
    if threading.current_thread() is not threading.main_thread() or getattr(_signal_scope, "active", False):
        yield
        return
    pending: list[int] = []

    def handler(signum: int, frame: Any) -> None:
        if pending:
            raise KeyboardInterrupt
        pending.append(signum)
        print("\nstop requested: finishing the in-flight transaction sequence first (send it again to force quit)")

    previous = {sig: signal.signal(sig, handler) for sig in (signal.SIGINT, signal.SIGTERM)}
    _signal_scope.active = True
    try:
        yield
    finally:
        _signal_scope.active = False
        for sig, old in previous.items():
            signal.signal(sig, old)
        if pending and on_stop is not None:
            on_stop(pending[0])
    if pending and on_stop is None:
        if pending[0] == signal.SIGTERM:
            raise SystemExit(128 + signal.SIGTERM)
        raise KeyboardInterrupt


def _single_width_cfg(s: StrategyConfig, half_width: float) -> StrategyConfig:
    pct = (math.exp(half_width) - 1) * 100
    return dataclasses.replace(s, min_half_width_pct=pct, max_half_width_pct=pct)


def forced_decision(ev: Evaluation, cfg: Config) -> Decision:
    """A REBALANCE decision to the proposed range regardless of the triggers (for `simulate --force`)."""
    pool = ev.pos.pool
    hw = ev.half_width or half_width_log(cfg.strategy, ev.sigma_daily)
    new = target_range(pool.tick, pool.tick_spacing, hw)
    return Decision(
        Action.REBALANCE, "forced", new, ev.decision.cost_usd, ev.decision.benefit_usd, dict(ev.decision.breakdown)
    )
