"""aero-lp command line.

aero-lp verify                         check contract addresses + RPC freshness
aero-lp pools                          top Aero Slipstream pools on Base (GeckoTerminal)
aero-lp positions --owner 0x.. [--pool 0x..]
aero-lp status   -c config.toml        state + decision for every configured position (read-only)
aero-lp simulate -c config.toml [--force] [--token-id N]
                                       full rebalance via eth_simulateV1 (nothing signed)
aero-lp run      -c config.toml [--live] [--once]
                                       loop: evaluate, simulate, and (only with --live) execute
aero-lp backtest --pool 0x.. [--widths 2,5,8,15] [--hours 720] [--value 10000] [--mode aero|fees]
aero-lp providers [--chain base] [--deposit-usd 50] [--top 25] [--max-pools N]
                                       compare every liquidity provider on a chain (read-only); writes
                                       providers.json and providers-report.md
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import traceback

from . import __version__, addresses, backtest, clmath
from .chain import DEFAULT_RPCS, AeroChain
from .config import Config, load
from .engine import Engine, Evaluation
from .executor import RebalanceError, RebalanceResult, fmt_amount
from .market import (
    MarketData,
    PoolEconomics,
    earn_usd_per_day,
    liquidity_for_usd,
    vol_from_closes,
    with_realized_fees,
)
from .strategy import Action


def _print_eval(ev: Evaluation) -> None:
    p, pool = ev.pos, ev.pos.pool
    lo, hi = p.price_bounds()
    a0, a1 = p.human_amounts()
    t0, t1 = pool.token0.symbol, pool.token1.symbol
    d = ev.decision
    print(f"── position #{p.token_id}  {t0}/{t1}  CL{pool.tick_spacing}  pool {pool.address}")
    print(
        f"   price {pool.price:,.6g} {t1}/{t0}   range [{lo:,.6g} – {hi:,.6g}]   ticks [{p.tick_lower},{p.tick_upper})"
    )
    status = "IN RANGE" if p.in_range else "OUT OF RANGE"
    print(f"   {status}   staked(AERO)={p.staked}   value ${ev.value_usd:,.2f}  ({a0:,.6g} {t0} + {a1:,.6g} {t1})")
    if p.staked:
        left = p.penalty_blocks_left
        print(
            f"   unclaimed AERO {p.earned_aero / 1e18:,.4f}   gauge penalty {p.penalty_rate:.0%} "
            f"within {p.penalty_min_blocks} blocks of deposit ({left} blocks left)"
        )
    deferred = p.extra.get("deferred_aero", 0)
    if deferred:
        print(f"   deferred AERO {deferred / 1e18:,.4f} held by the gauge (an earlier reward mint reverted)")
    if not p.staked:
        print(
            f"   uncollected fees {fmt_amount(p.fees0, pool.token0.decimals)} {t0} + "
            f"{fmt_amount(p.fees1, pool.token1.decimals)} {t1}"
        )
    sig = f"{ev.sigma_daily * 100:.2f}%/day" if ev.sigma_daily else "n/a"
    print(f"   volatility {sig} ({ev.sigma_source})   pool fee {pool.fee * 100:.4f}%   gauge active={pool.gauge_alive}")
    apr = lambda usd_day: usd_day * 365 / ev.value_usd * 100 if ev.value_usd else 0.0  # noqa: E731
    print(
        f"   earning now ${ev.earn_now_usd_day:,.2f}/day ({apr(ev.earn_now_usd_day):.1f}% APR)   "
        f"new range would earn: AERO ${ev.earn_new['aero']:,.2f}/day ({apr(ev.earn_new['aero']):.1f}%), "
        f"fees ${ev.earn_new['fees']:,.2f}/day ({apr(ev.earn_new['fees']):.1f}%) -> "
        f"{'stake for AERO' if ev.stake_new else 'earn fees (unstaked)'}"
    )
    if ev.width_scores:
        parts = []
        for name, sc in ev.width_scores.items():
            parts.append(
                f"{name}: +/-{(math.exp(sc.half_width) - 1) * 100:.1f}% yield {sc.yield_frac_day * 36500:.1f}% "
                f"- LVR {sc.lvr_frac_day * 36500:.1f}% - rebal {sc.rebalance_cost_frac_day * 36500:.1f}% "
                f"= net {sc.net_frac_day * 36500:+.1f}% APR"
            )
        print("   width model  " + " | ".join(parts))
    if ev.twap_deviation_bps is not None:
        print(f"   spot vs 10-min TWAP: {ev.twap_deviation_bps:.0f} bps   est. rebalance gas ${ev.gas_usd:.3f}")
    print(f"   DECISION: {d.action.value.upper()} — {d.reason}")
    if d.new_range:
        nlo = clmath.human_price(
            clmath.price_from_tick(d.new_range.tick_lower), pool.token0.decimals, pool.token1.decimals
        )
        nhi = clmath.human_price(
            clmath.price_from_tick(d.new_range.tick_upper), pool.token0.decimals, pool.token1.decimals
        )
        print(f"   proposed range [{nlo:,.6g} – {nhi:,.6g}]  ticks [{d.new_range.tick_lower},{d.new_range.tick_upper})")
    if d.breakdown:
        print("   " + "  ".join(f"{k}={v:,.3f}" for k, v in d.breakdown.items()))
    for n in ev.notes:
        print(f"   note: {n}")


def _print_result(res: RebalanceResult) -> None:
    print(f"   stages: {' -> '.join(res.stages)}   new token id: {res.new_token_id}   staked: {res.staked}")
    print(f"   AERO claimed: {res.aero_claimed / 1e18:,.4f}   gas used: {sum(res.gas_used.values()):,}")
    for h in res.tx_hashes:
        print(f"   tx: https://basescan.org/tx/{h}")
    for n in res.notes:
        print(f"   note: {n}")


def cmd_verify(a: argparse.Namespace) -> int:
    chain = AeroChain(a.rpc)
    problems = chain.verify_deployment()
    for name, addr in addresses.ALL_CONTRACTS.items():
        print(f"{name:28} {addr}")
    print("OK: all contracts present, RPC fresh" if not problems else "\n".join(f"PROBLEM: {p}" for p in problems))
    return 1 if problems else 0


def cmd_pools(a: argparse.Namespace) -> int:
    m = MarketData()
    pools = m.top_pools()
    print(f"{'pool':44} {'name':34} {'TVL':>14} {'24h vol':>14}")
    for p in pools[: a.top]:
        print(f"{p['address']:44} {p['name'][:34]:34} {p['reserve_usd']:>14,.0f} {p['volume_24h_usd']:>14,.0f}")
    return 0


def cmd_positions(a: argparse.Namespace) -> int:
    chain = AeroChain(a.rpc)
    ids = chain.positions_of(a.owner, a.pool or [])
    if not ids:
        print("no Slipstream positions found (staked positions need --pool <pool address>)")
    for tid in ids:
        pos = chain.position(tid, owner_hint=a.owner)
        lo, hi = pos.price_bounds()
        print(
            f"#{tid}  {pos.pool.token0.symbol}/{pos.pool.token1.symbol} CL{pos.pool.tick_spacing}  "
            f"[{lo:,.6g} – {hi:,.6g}]  {'in' if pos.in_range else 'OUT of'} range  staked={pos.staked}"
        )
    return 0


def _engine(a: argparse.Namespace) -> tuple[Config, Engine]:
    cfg = load(a.config)
    return cfg, Engine(cfg)


def cmd_status(a: argparse.Namespace) -> int:
    cfg, eng = _engine(a)
    for tid in cfg.token_ids:
        _print_eval(eng.evaluate(eng.state.slot(tid)))
    return 0


def cmd_simulate(a: argparse.Namespace) -> int:
    cfg, eng = _engine(a)
    ids = [a.token_id] if a.token_id else cfg.token_ids
    for tid in ids:
        ev, res = eng.step(tid, live=False, force=a.force)
        _print_eval(ev)
        if res:
            print("   SIMULATED REBALANCE (eth_simulateV1, nothing broadcast):")
            _print_result(res)
        elif ev.decision.action != Action.REBALANCE:
            print("   (no rebalance needed; use --force to simulate one anyway)")
    return 0


def cmd_withdraw(a: argparse.Namespace) -> int:
    cfg, eng = _engine(a)
    tid = a.token_id or (eng.state.slot(cfg.token_ids[0]).current_token_id if cfg.token_ids else None)
    if not tid:
        print("no token id: pass --token-id")
        return 1
    signer = None
    if a.live:
        from .wallet import load_signer

        problems = eng.chain.verify_deployment()
        if problems:
            print("refusing live mode:\n" + "\n".join(problems))
            return 2
        signer = load_signer(cfg.owner, cfg.key_file or None)
        print(f"LIVE: withdrawing #{tid} to {signer.address}")
    else:
        print(f"DRY RUN: simulating withdrawal of #{tid}. Add --live to sign and broadcast.")
    try:
        pos, res, gas_usd = eng.withdraw(tid, a.live, signer)
    except RebalanceError as e:
        print(f"WITHDRAW FAILED: {e}", file=sys.stderr)
        _print_result(e.partial)
        return 1
    t0, t1 = pos.pool.token0, pos.pool.token1
    r0, r1 = res.amounts_in_position
    print(f"   position #{pos.token_id} {t0.symbol}/{t1.symbol} CL{pos.pool.tick_spacing} staked={pos.staked}")
    print(
        f"   {'received' if a.live else 'would receive'}: {fmt_amount(r0, t0.decimals)} {t0.symbol} + "
        f"{fmt_amount(r1, t1.decimals)} {t1.symbol}   (simulated gas ${gas_usd:.3f})"
    )
    _print_result(res)
    return 0


def cmd_scout(a: argparse.Namespace) -> int:
    from .scout import candidate_pools, format_report, run_scout
    from .state import home

    chain = AeroChain(a.rpc)
    market = MarketData()
    pools = a.pool or candidate_pools(chain, market, a.top_by_volume)
    print(f"scoring {len(pools)} pools for a ${a.deposit_usd:,.2f} deposit (about 15 s each)...", flush=True)
    doc = run_scout(
        chain, market, a.deposit_usd, pools=pools, out=home() / "scout.json", progress=lambda m: print(m, flush=True)
    )
    print()
    print(format_report(doc, a.top))
    print(f"\nwritten: {home() / 'scout.json'}")
    return 0


def cmd_providers(a: argparse.Namespace) -> int:
    from . import providers
    from .providers_report import pool_table, provider_table
    from .state import home

    chain = AeroChain(a.rpc) if a.chain == "base" else None
    if chain is None:
        print(f"on-chain (Tier 1) scoring reads Base only: {a.chain} gets quoted (Tier 2) rows only", flush=True)
    market = MarketData(min_interval=2.2)  # GeckoTerminal allows about 30 requests a minute
    out_json, out_report = home() / "providers.json", home() / "providers-report.md"
    print(
        f"comparing providers on {a.chain} for a ${a.deposit_usd:,.2f} deposit (time budget {a.budget_s:.0f}s)...",
        flush=True,
    )
    doc = providers.run_providers(
        chain,
        market,
        a.deposit_usd,
        chain_name=a.chain,
        min_tvl_usd=a.min_tvl,
        min_volume_usd=a.min_volume,
        max_pools=a.max_pools,
        aero_pools=a.aero_pools,
        probe=not a.no_probe,
        max_seconds=a.budget_s,
        refresh=a.refresh,
        progress=lambda m: print(m, flush=True),
        out_json=out_json,
        out_report=out_report,
    )
    print()
    print("\n".join(provider_table(doc)))
    print()
    print("\n".join(pool_table(doc, a.top)))
    print(f"\nwritten: {out_json}\n         {out_report}")
    return 0


def cmd_daemon(a: argparse.Namespace) -> int:
    from .daemon import Daemon

    cfg = load(a.config)
    signer = None
    if a.live:
        from .wallet import load_signer

        problems = AeroChain(cfg.rpc_url).verify_deployment()
        if problems:
            print("refusing live mode:\n" + "\n".join(problems))
            return 2
        signer = load_signer(cfg.owner, cfg.key_file or None)
        print(f"LIVE daemon: signing as {signer.address}. Kill switch: touch $AERO_LP_HOME/KILL", flush=True)
    else:
        print("DRY-RUN daemon: plans and simulations only. Add --live to act.", flush=True)
    Daemon(cfg, a.live, signer).run(once=a.once)
    return 0


def cmd_pnl(a: argparse.Namespace) -> int:
    from .ledger import Ledger
    from .state import home

    lg = Ledger(home() / "ledger.sqlite")
    rows = [lg.pnl(r["slot"]) for r in lg.db.execute("SELECT slot FROM slots ORDER BY opened_at")]
    if not rows:
        print("no positions in the ledger yet")
        return 0
    print(
        f"{'slot':>9} {'pair':14} {'state':7} {'deposited':>10} {'value':>9} {'rewards':>8} {'gas':>6} "
        f"{'P&L':>8} {'vs HODL':>8} {'APR':>7}  experiment"
    )
    for p in rows:
        if p is None:
            continue
        print(
            f"{p.slot:>9} {p.pair[:14]:14} {'closed' if p.closed_at else 'open':7} {p.deposited_usd:>10.2f} "
            f"{p.value_usd:>9.2f} {p.rewards_usd:>8.2f} {p.gas_usd:>6.3f} {p.pnl_usd:>+8.2f} "
            f"{p.pnl_vs_hodl_usd:>+8.2f} {p.apr_realized:>+6.1f}%  {p.experiment or ''}"
        )
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    cfg, eng = _engine(a)
    signer = None
    if a.live:
        from .wallet import load_signer

        problems = eng.chain.verify_deployment()
        if problems:
            print("refusing live mode:\n" + "\n".join(problems))
            return 2
        signer = load_signer(cfg.owner, cfg.key_file or None)
        print(f"LIVE MODE: signing as {signer.address}. Ctrl-C to stop.")
    else:
        print("DRY RUN: decisions + eth_simulateV1 only. Add --live to sign and broadcast.")
    while True:
        for tid in cfg.token_ids:
            try:
                ev, res = eng.step(tid, live=a.live, signer=signer)
                print(time.strftime("%Y-%m-%d %H:%M:%S"))
                _print_eval(ev)
                if res:
                    print("   REBALANCED:" if a.live else "   SIMULATED REBALANCE:")
                    _print_result(res)
            except Exception as e:  # noqa: BLE001 - keep the loop alive; funds stay in the wallet on failure
                print(f"error on slot {tid}: {e}", file=sys.stderr)
                if isinstance(e, RebalanceError) and e.partial.tx_hashes:
                    # A live rebalance stopped half-way: print what is already on chain so it can be inspected.
                    print(f"   stages done: {' -> '.join(e.partial.stages) or 'none'}", file=sys.stderr)
                    print(f"   new token id: {e.partial.new_token_id}", file=sys.stderr)
                    for h in e.partial.tx_hashes:
                        print(f"   tx: https://basescan.org/tx/{h}", file=sys.stderr)
                traceback.print_exc()
        if a.once:
            return 0
        time.sleep(max(cfg.poll_seconds, cfg.safety.min_check_interval_s))


def cmd_backtest(a: argparse.Namespace) -> int:
    chain = AeroChain(a.rpc)
    m = MarketData()
    pool = chain.pool_state(a.pool)
    closes = m.hourly_closes(a.pool, a.hours)
    if len(closes) < 24:
        print("not enough price history")
        return 1
    prices = m.token_prices_usd([pool.token0.address, pool.token1.address, addresses.AERO_TOKEN, addresses.WETH])
    aero_day = chain.gauge_aero_per_day(pool.gauge, pool.block)
    info = m.pool_info(a.pool)
    econ = PoolEconomics(
        volume_usd_per_day=info["volume_24h_usd"],
        fee=pool.fee,
        unstaked_fee_share=pool.unstaked_fee_pips / 1e6,
        aero_per_day=aero_day,
        aero_usd=prices.get(addresses.AERO_TOKEN.lower(), 0.0),
        active_liquidity=pool.liquidity,
        staked_liquidity=pool.staked_liquidity,
        price0_usd=prices.get(pool.token0.address.lower(), 0.0),
        price1_usd=prices.get(pool.token1.address.lower(), 0.0),
        dec0=pool.token0.decimals,
        dec1=pool.token1.decimals,
    )
    econ = with_realized_fees(chain, a.pool, pool.block, econ)
    staked = a.mode == "aero"

    def yield_curve(hw: float) -> float:
        tl = clmath.floor_tick(pool.tick - hw / clmath.LOG_BASE, pool.tick_spacing)
        tu = clmath.ceil_tick(pool.tick + hw / clmath.LOG_BASE, pool.tick_spacing)
        liq = liquidity_for_usd(a.value, pool.sqrt_price_x96, tl, tu, econ)
        return earn_usd_per_day(liq, staked, True, econ, already_counted=False) / a.value

    gas = 2_700_000 * chain.gas_price_wei() / 1e18 * prices.get(addresses.WETH.lower(), 0.0) + 0.05
    sigma = vol_from_closes(closes)
    days = (len(closes) - 1) / 24
    print(
        f"{pool.token0.symbol}/{pool.token1.symbol} CL{pool.tick_spacing}: {len(closes)} hourly closes "
        f"({days:.1f} days), realized vol {sigma * 100 if sigma else float('nan'):.2f}%/day, "
        f"mode={a.mode}, start value {a.value:,.0f}, gas/rebalance ${gas:.3f}"
    )
    print("Assumes today's volume / emissions / competing liquidity for the whole window.\n")
    results = []
    for w in a.widths:
        hw = math.log1p(w / 100)
        results.append(backtest.run(closes, hw, yield_curve, start_value=a.value, gas_cost=gas, pool_fee=pool.fee))
    print(backtest.format_table(results, days))
    best = max(results, key=lambda r: r.pnl_vs_hodl)
    print(f"\nbest net of costs vs HODL over this window: {best.label}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aero-lp", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def with_rpc(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--rpc", default=DEFAULT_RPCS[0], help="Base RPC URL")
        return p

    with_rpc(sub.add_parser("verify")).set_defaults(fn=cmd_verify)
    p = sub.add_parser("pools")
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(fn=cmd_pools)
    p = with_rpc(sub.add_parser("positions"))
    p.add_argument("--owner", required=True)
    p.add_argument("--pool", action="append", help="pool address whose gauge to scan for staked positions")
    p.set_defaults(fn=cmd_positions)
    for name, fn in (("status", cmd_status), ("simulate", cmd_simulate), ("run", cmd_run), ("withdraw", cmd_withdraw)):
        p = sub.add_parser(name)
        p.add_argument("-c", "--config", default="config.toml")
        if name == "simulate":
            p.add_argument("--force", action="store_true", help="simulate a rebalance even if not triggered")
            p.add_argument("--token-id", type=int)
        if name == "withdraw":
            p.add_argument("--token-id", type=int, help="position to exit (default: first configured slot)")
            p.add_argument("--live", action="store_true", help="sign and broadcast transactions")
        if name == "run":
            p.add_argument("--live", action="store_true", help="sign and broadcast transactions")
            p.add_argument("--once", action="store_true")
        p.set_defaults(fn=fn)
    p = with_rpc(sub.add_parser("scout", help="rank pools by likely profit for a deposit size"))
    p.add_argument("--deposit-usd", type=float, default=50.0)
    p.add_argument("--pool", action="append", help="score only these pools (repeatable)")
    p.add_argument("--top-by-volume", type=int, default=20)
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(fn=cmd_scout)
    p = with_rpc(sub.add_parser("providers", help="compare every liquidity provider on a chain (read-only)"))
    p.add_argument("--chain", default="base", help="DefiLlama chain; only base is scored on chain")
    p.add_argument("--deposit-usd", type=float, default=50.0)
    p.add_argument("--top", type=int, default=25, help="rows in the top-pools table")
    p.add_argument("--max-pools", type=int, default=60, help="most non-Aero pools read on chain")
    p.add_argument("--aero-pools", type=int, default=12, help="most Aero Slipstream pools scored")
    p.add_argument("--min-tvl", type=float, default=100_000.0)
    p.add_argument("--min-volume", type=float, default=10_000.0, help="minimum 24h volume (USD) for non-vault pools")
    p.add_argument("--budget-s", type=float, default=1500.0, help="time budget for the on-chain part")
    p.add_argument("--no-probe", action="store_true", help="skip probing unregistered Uniswap-v3 forks")
    p.add_argument("--refresh", action="store_true", help="ignore the cached DefiLlama pools")
    p.set_defaults(fn=cmd_providers)
    p = sub.add_parser("daemon", help="manage, compound, scout and allocate in one loop")
    p.add_argument("-c", "--config", default="~/.aero-lp/config.toml")
    p.add_argument("--live", action="store_true", help="sign and broadcast")
    p.add_argument("--once", action="store_true", help="one tick, then exit")
    p.set_defaults(fn=cmd_daemon)
    sub.add_parser("pnl", help="per-slot P&L from the ledger").set_defaults(fn=cmd_pnl)
    p = with_rpc(sub.add_parser("backtest"))
    p.add_argument("--pool", required=True)
    p.add_argument("--widths", type=lambda s: [float(x) for x in s.split(",")], default=[2, 4, 8, 15, 30])
    p.add_argument("--hours", type=int, default=720)
    p.add_argument("--value", type=float, default=10_000.0)
    p.add_argument("--mode", choices=["aero", "fees"], default="aero")
    p.set_defaults(fn=cmd_backtest)
    a = ap.parse_args(argv)
    return int(a.fn(a))


if __name__ == "__main__":
    raise SystemExit(main())
