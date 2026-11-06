"""Exit to safe: take every managed LP position out and leave the coins in the wallet.

This is separate from the kill switch. KILL only halts the daemon: positions stay open and keep losing money.
`exit-to-safe` removes the liquidity (unstake, remove, collect fees, burn the empty NFT), and can optionally convert
the withdrawn coins into a stable coin.

Rules this module keeps:
  * Dry run is the default. It prints the exact plan and signs nothing. `--live` is required to send.
  * Every position goes through `Engine.withdraw`: an `eth_simulateV1` of the whole sequence, `safety.max_gas_usd`,
    the wallet's ETH reserve and a fail-closed ETH price. Before it, the TWAP manipulation guard must pass (a missing
    TWAP counts as a failure in live mode).
  * `safety.max_position_usd` is not applied: it caps new exposure, and an exit only reduces exposure.
  * The research and soak gates are not applied (see gates.py): de-risking is always allowed.
  * Live mode creates `$AERO_LP_HOME/KILL` first, so the daemon cannot redeploy the returned coins or compete for the
    wallet nonce. The file stays in place afterwards; the owner decides when to resume.
  * Conversion (`[safe_exit].convert_to` or `--convert-to`) is off by default. It spends only the amounts the
    withdrawal returned, only through a direct pool, only when the pool's price is within `CONVERT_PRICE_TOLERANCE`
    of market prices, and each swap is simulated against the real post-withdrawal balances before it is sent.
    A swap that is refused leaves the coins in the wallet.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from web3 import Web3

from . import addresses
from .chain import ZERO, PoolState, PositionState
from .config import SAFE_EXIT_TARGETS, Config
from .engine import Engine
from .executor import RebalanceError, RebalanceResult, SimRunner, fmt_amount, gas_cost_usd, runner_tokens
from .metrics import KNOWN_TOKENS
from .state import atomic_write_json
from .validation import measured_gas

REPORT_SCHEMA = "aero-lp-exit-to-safe/1"
# Same tolerance the daemon uses for conversion swaps.
CONVERT_PRICE_TOLERANCE = 0.02
SYMBOL_TO_ADDRESS = {v: Web3.to_checksum_address(k) for k, v in KNOWN_TOKENS.items()}


@dataclass
class ConvertStep:
    token: str  # symbol
    token_address: str
    amount_raw: int
    route_pool: str = ""
    expected_out_raw: int = 0
    min_out_raw: int = 0
    refused: str = ""  # why this conversion will not run
    tx_hashes: list[str] = field(default_factory=list)
    out_raw: int = 0


@dataclass
class PositionPlan:
    token_id: int
    pair: str
    staked: bool
    status: str  # ready | blocked | exited | failed
    reason: str = ""
    value_usd: float | None = None
    receive: tuple[int, int] = (0, 0)
    decimals: tuple[int, int] = (18, 18)
    symbols: tuple[str, str] = ("?", "?")
    aero_claimed_raw: int = 0
    gas_usd: float = 0.0
    stages: list[str] = field(default_factory=list)
    tx_hashes: list[str] = field(default_factory=list)
    converts: list[ConvertStep] = field(default_factory=list)


@dataclass
class ExitReport:
    live: bool
    started_at: float
    convert_to: str
    positions: list[PositionPlan] = field(default_factory=list)
    killed_by_exit: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        wanted = "exited" if self.live else "ready"
        return not self.error and all(p.status == wanted for p in self.positions)


def managed_token_ids(cfg: Config, eng: Engine, ledger_token_ids: list[int], explicit: list[int] | None) -> list[int]:
    """Every NFT the bot manages: explicit ids, or configured slots (at their current NFT) plus ledger slots."""
    if explicit:
        return list(dict.fromkeys(explicit))
    ids = [eng.state.slot(t).current_token_id for t in cfg.token_ids]
    ids += ledger_token_ids
    return list(dict.fromkeys(i for i in ids if i))


def best_direct_pool(eng: Engine, a: str, b: str) -> PoolState | None:
    best: PoolState | None = None
    for ts in eng.chain.factory.functions.tickSpacings().call():
        addr = eng.chain.pool_address(a, b, int(ts))
        if addr == ZERO:
            continue
        ps = eng.chain.pool_state(addr)
        if ps.liquidity > 0 and (best is None or ps.liquidity > best.liquidity):
            best = ps
    return best


def plan_conversion(eng: Engine, token: str, amount: int, target: str, prices: dict[str, float]) -> ConvertStep:
    """Pick the route and min-out for one conversion, or say why it is refused. Pure reads; fail closed."""
    step = ConvertStep(KNOWN_TOKENS.get(token.lower(), token[:10]), token, amount)
    if amount <= 0:
        step.refused = "nothing to convert"
        return step
    route = best_direct_pool(eng, token, target)
    if route is None:
        step.refused = "no direct pool to the target coin (multi-hop routes are not used)"
        return step
    fwd = token.lower() == route.token0.address.lower()
    dec_in, dec_out = (
        (route.token0.decimals, route.token1.decimals) if fwd else (route.token1.decimals, route.token0.decimals)
    )
    raw_p = route.raw_price
    expected = amount * raw_p * (1 - route.fee) if fwd else amount / raw_p * (1 - route.fee)
    pin, pout = prices.get(token.lower(), 0.0), prices.get(target.lower(), 0.0)
    if not (pin > 0 and pout > 0):
        step.refused = "no USD price for both coins: cannot check the pool price"
        return step
    in_usd, out_usd = amount / 10**dec_in * pin, expected / 10**dec_out * pout
    if out_usd < in_usd * (1 - CONVERT_PRICE_TOLERANCE):
        step.refused = (
            f"pool would pay ${out_usd:.2f} for ${in_usd:.2f} (more than {CONVERT_PRICE_TOLERANCE:.0%} below market)"
        )
        return step
    if in_usd < eng.cfg.execution.min_swap_usd:
        step.refused = f"${in_usd:.2f} is below execution.min_swap_usd"
        return step
    step.route_pool = route.address
    step.expected_out_raw = int(expected)
    step.min_out_raw = int(expected * (1 - eng.cfg.execution.max_slippage_bps / 1e4))
    return step


def _value_usd(pos: PositionState, prices: dict[str, float], amounts: tuple[int, int]) -> float | None:
    p0, p1 = prices.get(pos.pool.token0.address.lower(), 0.0), prices.get(pos.pool.token1.address.lower(), 0.0)
    if not (p0 > 0 and p1 > 0):
        return None
    return amounts[0] / 10**pos.pool.token0.decimals * p0 + amounts[1] / 10**pos.pool.token1.decimals * p1


def build_plan(eng: Engine, token_id: int, convert_to: str, prices_fn: Any) -> PositionPlan:
    """Simulate the withdrawal (eth_simulateV1, nothing signed) and apply the pre-send checks."""
    cfg = eng.cfg
    try:
        pos, sim, gas_usd = eng.withdraw(token_id, False)
    except Exception as e:  # noqa: BLE001 - one unreadable position must not hide the others
        return PositionPlan(token_id, "?", False, "blocked", f"simulation failed: {type(e).__name__}: {e}")
    t0, t1 = pos.pool.token0, pos.pool.token1
    plan = PositionPlan(
        token_id,
        f"{t0.symbol}/{t1.symbol} CL{pos.pool.tick_spacing}",
        pos.staked,
        "ready",
        receive=tuple(sim.amounts_in_position),
        decimals=(t0.decimals, t1.decimals),
        symbols=(t0.symbol, t1.symbol),
        aero_claimed_raw=sim.aero_claimed,
        gas_usd=gas_usd,
        stages=list(sim.stages),
    )
    blocks: list[str] = []
    try:
        prices = prices_fn([t0.address, t1.address, addresses.AERO_TOKEN, addresses.WETH])
    except Exception as e:  # noqa: BLE001
        prices = {}
        blocks.append(f"USD prices unavailable ({e}): cannot size the exit")
    plan.value_usd = _value_usd(pos, prices, plan.receive)
    blocks += eng.pool_blocks(pos.pool, live=True)
    if not math.isfinite(gas_usd) or gas_usd > cfg.safety.max_gas_usd:  # NaN or over the cap
        blocks.append(f"simulated gas ${gas_usd:.2f} > safety.max_gas_usd ${cfg.safety.max_gas_usd:.2f}")
    if blocks:
        plan.status, plan.reason = "blocked", "; ".join(blocks)
        return plan
    if convert_to:
        target = SYMBOL_TO_ADDRESS[convert_to]
        pending = [(t0.address, plan.receive[0]), (t1.address, plan.receive[1])]
        if plan.aero_claimed_raw and addresses.AERO_TOKEN.lower() not in (t0.address.lower(), t1.address.lower()):
            pending.append((addresses.AERO_TOKEN, plan.aero_claimed_raw))
        for token, amount in pending:
            if token.lower() == target.lower() or amount <= 0:
                continue
            plan.converts.append(plan_conversion(eng, Web3.to_checksum_address(token), amount, target, prices))
    return plan


def format_plan(report: ExitReport) -> str:
    lines = [
        f"EXIT TO SAFE: {'LIVE' if report.live else 'DRY RUN (nothing signed; add --live to send)'}"
        f"{'  convert to ' + report.convert_to if report.convert_to else '  (no conversion)'}"
    ]
    if not report.positions:
        lines.append("  no managed positions found")
    for p in report.positions:
        value = f"${p.value_usd:,.2f}" if p.value_usd is not None else "value unknown"
        lines.append(f"  #{p.token_id} {p.pair} staked={p.staked} [{p.status.upper()}] {value}")
        if p.status == "blocked":
            lines.append(f"      refused: {p.reason}")
            continue
        lines.append(f"      stages: {' -> '.join(p.stages) or 'n/a'}   simulated gas ${p.gas_usd:.3f}")
        lines.append(
            f"      wallet receives: {fmt_amount(p.receive[0], p.decimals[0])} {p.symbols[0]} + "
            f"{fmt_amount(p.receive[1], p.decimals[1])} {p.symbols[1]}"
            + (f" + {p.aero_claimed_raw / 1e18:,.4f} AERO claimed" if p.aero_claimed_raw else "")
        )
        for c in p.converts:
            if c.refused:
                lines.append(f"      convert {c.token}: SKIPPED, {c.refused}; stays in the wallet")
            else:
                lines.append(
                    f"      convert {c.token}: {c.amount_raw} raw via pool {c.route_pool}, "
                    f"expect >= {c.min_out_raw} raw "
                    f"{report.convert_to} (swap is simulated on the real balances right before it is sent)"
                )
        for h in p.tx_hashes:
            lines.append(f"      tx: https://basescan.org/tx/{h}")
        for c in p.converts:
            for h in c.tx_hashes:
                lines.append(f"      tx: https://basescan.org/tx/{h}")
    if report.live:
        lines.append("  KILL file is set: the daemon stays halted until `scripts/aero-lp-service resume`.")
    if report.error:
        lines.append(f"  ERROR: {report.error}")
    return "\n".join(lines)


def _convert_live(eng: Engine, plan: PositionPlan, step: ConvertStep, target: str, signer: Any, prices_fn: Any) -> None:
    """Re-plan on fresh state, simulate on the real balances, then send one swap."""
    from .executor import Rebalancer

    token = Web3.to_checksum_address(step.token_address)
    fresh = plan_conversion(eng, token, step.amount_raw, target, prices_fn([token, target]))
    if fresh.refused:
        step.refused = fresh.refused
        return
    route = eng.chain.pool_state(fresh.route_pool)
    if blocks := eng.pool_blocks(route, live=True):
        step.refused = "; ".join(blocks)
        return
    tokens = runner_tokens(route.token0.address, route.token1.address)
    rb = Rebalancer(eng.chain, eng.cfg.owner, eng.cfg.execution)
    eth_usd = prices_fn([addresses.WETH]).get(addresses.WETH.lower(), 0.0)
    sim = rb.swap_exact(
        route, token, step.amount_raw, SimRunner(eng.chain, eng.cfg.owner, tokens, route.address), fresh.min_out_raw
    )
    gas = gas_cost_usd(measured_gas(sim.gas_used), eng.chain.gas_price_wei(), eth_usd, eng.cfg.l1_fee_usd_estimate)
    if not eth_usd > 0 or not math.isfinite(gas) or gas > eng.cfg.safety.max_gas_usd:
        step.refused = f"simulated gas ${gas:.2f} cannot be checked against or exceeds safety.max_gas_usd"
        return
    eng._gate()
    res = rb.swap_exact(
        route, token, step.amount_raw, eng._live_runner(signer, tokens, route.address), fresh.min_out_raw
    )
    step.route_pool, step.tx_hashes, step.out_raw = fresh.route_pool, res.tx_hashes, res.amount_out


def run_exit(
    eng: Engine,
    token_ids: list[int],
    *,
    live: bool,
    signer: Any = None,
    convert_to: str = "",
    root: Path,
    prices_fn: Any = None,
    now: float | None = None,
) -> ExitReport:
    """Plan every position; in live mode set KILL, then exit them one by one and convert if asked."""
    if convert_to and convert_to not in SAFE_EXIT_TARGETS:
        raise ValueError(f"convert_to must be one of {SAFE_EXIT_TARGETS}")
    if live and signer is None:
        raise ValueError("live mode needs a signer")
    prices_fn = prices_fn or eng.market.token_prices_usd
    report = ExitReport(live, time.time() if now is None else now, convert_to)
    report.positions = [build_plan(eng, t, convert_to, prices_fn) for t in token_ids]
    if not live:
        return report
    kill = root / "KILL"
    if not kill.exists():
        root.mkdir(parents=True, exist_ok=True)
        kill.write_text(
            f"set by exit-to-safe at {time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(report.started_at))}\n"
        )
        report.killed_by_exit = True
    target = SYMBOL_TO_ADDRESS[convert_to] if convert_to else ""
    for plan in report.positions:
        if plan.status != "ready":
            continue
        try:
            _pos, res, _gas = eng.withdraw(plan.token_id, True, signer)
        except RebalanceError as e:
            _record_failure(plan, e.partial, str(e))
            report.error = f"#{plan.token_id}: {e}; stopped, remaining positions untouched"
            break
        except Exception as e:  # noqa: BLE001 - e.g. ETH reserve or price check refused before any send
            plan.status, plan.reason = "failed", f"{type(e).__name__}: {e}"
            report.error = f"#{plan.token_id}: {e}; stopped, remaining positions untouched"
            break
        plan.status, plan.tx_hashes, plan.stages = "exited", res.tx_hashes, res.stages
        plan.receive, plan.aero_claimed_raw = tuple(res.amounts_in_position), res.aero_claimed
        for step in plan.converts:
            if step.refused:
                continue
            try:
                _convert_live(eng, plan, step, target, signer, prices_fn)
            except Exception as e:  # noqa: BLE001 - the coins are already in the wallet; leave them there
                step.refused = f"{type(e).__name__}: {e}"
    return report


def _record_failure(plan: PositionPlan, partial: RebalanceResult, message: str) -> None:
    plan.status, plan.reason = "failed", message
    plan.tx_hashes, plan.stages = list(partial.tx_hashes), list(partial.stages)


def write_report(root: Path, report: ExitReport) -> Path:
    path = root / "exit-to-safe.json"
    doc = asdict(report)
    doc["schema"] = REPORT_SCHEMA
    doc["ok"] = report.ok
    atomic_write_json(path, doc)
    return path
