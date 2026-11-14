"""Pool scout: find the Aero Slipstream pools most likely to be profitable for a deposit of a given size.

Candidates come from two places, because the most profitable pools for a small passive deposit are
usually *not* the highest-volume ones:
  1. the top pools by 24h volume on GeckoTerminal (dex `aero-slipstream-base`);
  2. on-chain discovery of every tick spacing for a curated list of correlated / stable pairs
     (LST/ETH, stable/stable), where the pair's price ratio barely moves, so loss-versus-rebalancing
     is small and fee + AERO income can dominate.

Each candidate is scored by `metrics.evaluate_pool`, and the results are written atomically to
`$AERO_LP_HOME/scout.json` (schema `aero-lp-scout/1`, see STATE_FILES.md) sorted by
expected net APR.
"""

from __future__ import annotations

import json
import signal
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from web3 import Web3

from .chain import ZERO, AeroChain
from .diagnostics import safe_error
from .market import MarketData
from .metrics import KNOWN_TOKENS, PoolMetrics, evaluate_pool
from .state import atomic_write_json
from .strategy import StrategyConfig
from .validation import finite_number

SCHEMA = "aero-lp-scout/1"


class ScoutDeadline(BaseException):
    """Do not let provider fallback handlers swallow the whole-run read-only deadline."""


@contextmanager
def _budget(seconds: float | None):
    if seconds is None:
        yield
        return
    finite_number(seconds, "max_seconds", positive=True)
    if threading.current_thread() is not threading.main_thread():
        raise ValueError("bounded scout requires the main thread")
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ValueError("bounded scout cannot replace another active process timer")
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise ScoutDeadline

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


_SYM = {v: k for k, v in KNOWN_TOKENS.items()}
# Pairs whose price ratio is (nearly) pegged. Order does not matter.
CORRELATED_PAIRS: list[tuple[str, str]] = [
    ("WETH", "wstETH"),
    ("WETH", "cbETH"),
    ("WETH", "weETH"),
    ("WETH", "rETH"),
    ("wstETH", "cbETH"),
    ("USDC", "USDT"),
    ("USDC", "USDbC"),
    ("USDC", "DAI"),
    ("USDT", "DAI"),
]


def discover_correlated(chain: AeroChain, pairs: Iterable[tuple[str, str]] = CORRELATED_PAIRS) -> list[str]:
    """Every existing Slipstream pool for the curated pairs, across all enabled tick spacings."""
    spacings = chain.factory.functions.tickSpacings().call()
    found: list[str] = []
    for a, b in pairs:
        ta, tb = Web3.to_checksum_address(_SYM[a]), Web3.to_checksum_address(_SYM[b])
        for ts in spacings:
            addr = chain.pool_address(ta, tb, int(ts))
            if addr != ZERO:
                found.append(addr)
    return found


def candidate_pools(chain: AeroChain, market: MarketData, top_by_volume: int = 20) -> list[str]:
    seen: dict[str, None] = {}
    try:
        for p in market.top_pools(1)[:top_by_volume]:
            seen.setdefault(Web3.to_checksum_address(p["address"]), None)
    except Exception:  # noqa: BLE001 - GeckoTerminal down: on-chain discovery still runs
        pass
    for addr in discover_correlated(chain):
        seen.setdefault(Web3.to_checksum_address(addr), None)
    return list(seen)


def rank(results: list[PoolMetrics]) -> list[PoolMetrics]:
    """High/medium-confidence pools first, by expected net APR; low-confidence pools after them.

    A low-confidence row (tiny TVL, no price history, unlisted token) can show an absurd model APR. With no
    sigma the LVR term is 0. Such a row must not top the list a human reads first. The allocator rejects it
    anyway.
    """
    return sorted(results, key=lambda m: (m.confidence == "low", -m.expected_net_apr))


def run_scout(
    chain: AeroChain,
    market: MarketData,
    deposit_usd: float,
    cfg: StrategyConfig | None = None,
    pools: list[str] | None = None,
    top_by_volume: int = 20,
    out: Path | None = None,
    progress: Callable[[str], None] | None = None,
    gas_units: int = 2_700_000,
    l1_fee_usd: float = 0.005,
    max_seconds: float | None = None,
) -> dict[str, Any]:
    """Bound discovery and evaluation together; partial reads never claim complete coverage.

    A bounded call runs on the main thread without an existing real-time timer. It interrupts only
    this read-only scout, never a transaction sequence or a worker left running in the background.
    """
    results: list[PoolMetrics] = []
    errors: list[dict[str, str]] = []
    started = time.monotonic()
    remaining = list(pools) if pools is not None else []
    exhausted = False
    try:
        with _budget(max_seconds):
            if pools is None:
                remaining = candidate_pools(chain, market, top_by_volume)
            total = len(remaining)
            while remaining:
                if max_seconds is not None and time.monotonic() - started >= max_seconds:
                    raise ScoutDeadline
                addr = remaining[0]
                try:
                    m = evaluate_pool(chain, market, addr, deposit_usd, cfg, gas_units=gas_units, l1_fee_usd=l1_fee_usd)
                    results.append(m)
                    if progress:
                        progress(f"[{total - len(remaining) + 1}/{total}] {m.pair}: net {m.expected_net_apr:+.1f}% APR")
                except Exception as error:  # noqa: BLE001 -- one bad pool must not end the scan
                    errors.append({"pool": addr, "error": safe_error(error)})
                    if progress:
                        progress(f"{addr}: error {type(error).__name__}")
                remaining.pop(0)
    except ScoutDeadline:
        exhausted = True
        errors.extend({"pool": addr, "error": "skipped: scout time budget used up"} for addr in remaining)
        if not remaining:
            errors.append({"pool": "discovery", "error": "scout time budget used up during discovery"})
    doc = {
        "schema": SCHEMA,
        "generated_at": time.time(),
        "deposit_usd": deposit_usd,
        "pools": [m.to_json() for m in rank(results)],
        "errors": errors,
        "budget_exhausted": exhausted,
        "complete": not exhausted and not errors,
    }
    if out is not None:
        atomic_write_json(out, doc)
    return doc


def load_scout(path: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) and doc.get("schema") == SCHEMA else None


def format_report(doc: dict[str, Any], top: int = 15) -> str:
    rows = [
        f"Aero pool scout for a ${doc['deposit_usd']:,.0f} deposit "
        f"({time.strftime('%Y-%m-%d %H:%M', time.localtime(doc['generated_at']))})",
        f"{'pair':16} {'CL':>4} {'TVL':>11} {'fee%':>5} {'σ/day':>6} {'fee':>6} {'AERO':>6} {'LVR':>7} "
        f"{'edge':>6} {'mode':>4} {'±w':>5} {'net APR':>8} {'conf':>6}  flags",
    ]
    for p in doc["pools"][:top]:
        sig = f"{p['sigma_daily_pct']:.2f}%" if p.get("sigma_daily_pct") is not None else "n/a"
        rows.append(
            f"{p['pair'][:16]:16} {p['tick_spacing']:>4} {p['tvl_usd']:>11,.0f} {p['fee_pct']:>5.3f} {sig:>6} "
            f"{p['fee_apr_ref']:>5.1f}% {p['aero_apr_ref']:>5.1f}% {p['lvr_apr_ref']:>6.1f}% "
            f"{min(p['edge_ratio'], 999):>6.2f} {p['best_mode']:>4} {p['best_half_width_pct']:>4.1f}% "
            f"{p['expected_net_apr']:>+7.1f}% {p['confidence']:>6}  {'; '.join(p['flags'])}"
        )
    rows.append("APRs at +/-10% (fee/AERO/LVR) are annualized % of deposit; net APR is at the optimized width.")
    if doc.get("errors"):
        rows.append(f"{len(doc['errors'])} pool(s) failed to evaluate")
    return "\n".join(rows)
