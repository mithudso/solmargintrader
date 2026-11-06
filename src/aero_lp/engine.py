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
from .chain import MAX_HEAD_LAG_S, AeroChain, PositionState, realized_vol_daily
from .config import Config
from .executor import (
    LiveRunner,
    RebalanceError,
    Rebalancer,
    RebalanceResult,
    SimRunner,
    StageHook,
    gas_cost_usd,
    runner_tokens,
)
from .market import MarketData, PoolEconomics, earn_usd_per_day, liquidity_for_usd, vol_from_closes
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
        p = self.chain._c(pos.pool.address, abi.CL_POOL)
        try:
            cums, _ = p.functions.observe([600, 0]).call(block_identifier=pos.pool.block)
        except Exception:  # noqa: BLE001 - oracle history too short
            return None
        return abs(pos.pool.tick - (cums[1] - cums[0]) / 600)

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
        if deviation_bps is None:
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
        if live and not (ev.econ.price0_usd and ev.econ.price1_usd and ev.eth_usd):
            # With a price missing, value_usd and gas_usd are understated and the two limits below pass vacuously.
            out.append("missing USD price for a pool token or ETH: max_position_usd / max_gas_usd cannot be enforced")
        if live and ev.value_usd > sc.max_position_usd:
            out.append(f"position ${ev.value_usd:,.0f} > safety.max_position_usd ${sc.max_position_usd:,.0f}")
        if live and ev.gas_usd > sc.max_gas_usd:
            out.append(f"gas estimate ${ev.gas_usd:.2f} > safety.max_gas_usd ${sc.max_gas_usd:.2f}")
        return out

    def rebalance(
        self, ev: Evaluation, live: bool, signer: Any = None, on_stage: StageHook | None = None
    ) -> RebalanceResult:
        """Always simulates the full sequence first; broadcasts only when live=True."""
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
        # The gas limit is checked against the simulated gas, not only the config's fixed estimate.
        sim_gas_usd = gas_cost_usd(
            sum(sim.gas_used.values()), self.chain.gas_price_wei(), ev.eth_usd, self.cfg.l1_fee_usd_estimate
        )
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
        with defer_sigint():
            return rb.rebalance(
                fresh,
                ev.decision.new_range,
                ev.stake_new,
                LiveRunner(self.chain, signer, tokens, self.cfg.execution, pool.address),
                ev.econ.price0_usd,
                ev.econ.price1_usd,
                on_stage=on_stage,
            )

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
        return ev, result


@contextlib.contextmanager
def defer_sigint() -> Iterator[None]:
    """Hold Ctrl-C until a live transaction sequence finishes; interrupting between the burn and the
    mint would leave the funds out of any position. A second Ctrl-C still exits immediately."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    pending: list[int] = []

    def handler(signum: int, frame: Any) -> None:
        if pending:
            raise KeyboardInterrupt
        pending.append(signum)
        print("\nCtrl-C received: finishing the in-flight rebalance first (press again to force quit)")

    previous = signal.signal(signal.SIGINT, handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)
    if pending:
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
