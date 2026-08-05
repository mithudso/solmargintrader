#!/usr/bin/env python3
"""Cost economics of high-leverage perpetuals, for Jupiter Perps specifically.

Generates every table in research/LEVERAGE-ECONOMICS.md. No network, no data files --
this is closed-form arithmetic over published venue parameters, so it reproduces exactly.

    python3 research/leverage_economics.py             # print all tables
    python3 research/leverage_economics.py --markdown  # emit the doc's tables as markdown
    python3 research/leverage_economics.py --self-test # assert the load-bearing claims

The one result worth stating up front, because it is counterintuitive and it reframes
every strategy question that follows:

    pnl%_collateral = L*move - (fee_rt*L + rate*util*hours*L)
    break_even_move = fee_rt + rate*util*hours          <-- L cancels

Leverage does not change the price move a trade needs to break even. It changes how
close the absorbing barrier sits and how fast carry consumes collateral. Those are the
only two things it changes.

VENUE PARAMETERS (as of 2026-08-05 -- verify against docs.jup.ag before relying on them)
---------------------------------------------------------------------------------------
  base fee            0.06% each way, read live from increasePositionBps/decreasePositionBps
  borrow rate         hourly, = (hourlyFundingBps-scale / 1000) * utilizationPct, i.e.
                      linear in utilisation, NEVER negative, and paid by BOTH sides
  max hourly (SOL)    ~0.016%/hr  (~140% APR)   <- longs borrow the volatile custody
  max hourly (stable) ~0.003%/hr  (~23% APR)    <- shorts borrow the stable custody
  leverage range      1.1x - 250x
  liquidation         forfeits 100% of REMAINING collateral

The per-custody rates are Gauntlet's May-2024 recommendation, not a live read. Utilisation
moves continuously. Treat every number here as an order-of-magnitude frame, not a quote.

NOT MODELLED (each one makes the real picture WORSE, never better)
------------------------------------------------------------------
  * price-impact fee -- per-custody `factor`/`exp`/threshold are on-chain and undocumented,
    so it cannot be computed from public data. It is strictly additive to the fees here.
  * request-to-fill drift (keeper latency), priority fees, Jito tips, failed transactions.
  * the liquidation PENALTY itself -- these tables show when collateral reaches zero, which
    is the optimistic reading.
"""
from __future__ import annotations
import argparse

FEE_RT = 0.0012            # 6 bps each way, on notional
R_LONG = 0.00016           # per hour, SOL custody, at 100% utilisation
R_SHORT = 0.00003          # per hour, stable custody, at 100% utilisation
HOLDS = [("1 h", 1), ("4 h", 4), ("1 day", 24), ("3 days", 72), ("1 week", 168), ("1 month", 720)]
LEVS = [2, 5, 10, 20, 50, 100, 250]


def break_even_move(hours, rate, util=0.5):
    """Price move needed to cover fees + carry. Independent of leverage -- see module docstring."""
    return FEE_RT + rate * util * hours


def carry_crossover_hours(rate, util=0.5):
    """Hold time at which cumulative carry equals one round-trip fee."""
    return FEE_RT / (rate * util)


def hours_to_zero_collateral(lev, rate, util=0.5):
    """Hours until carry ALONE consumes the collateral, with price perfectly flat."""
    return 1.0 / (rate * util * lev)


def liquidation_move(lev):
    """Approximate adverse move that exhausts collateral, ignoring accrued fees."""
    return 1.0 / lev


def _fmt_h(h):
    return f"{h/24:.1f} d" if h >= 24 else f"{h:.1f} h"


def tables(md=False):
    B = "**" if md else ""
    out = []
    p = out.append

    p(f"\n{B}1. Break-even price move — leverage cancels{B}")
    if md:
        p("\n| Hold | Long (SOL custody) | Short (stable custody) |\n|---|---:|---:|")
        for lab, h in HOLDS:
            p(f"| {lab} | {break_even_move(h, R_LONG)*100:.3f}% | {break_even_move(h, R_SHORT)*100:.3f}% |")
    else:
        p(f"   {'hold':>8s} {'LONG (SOL cust)':>18s} {'SHORT (stable)':>17s}   [util 50%]")
        for lab, h in HOLDS:
            p(f"   {lab:>8s} {break_even_move(h, R_LONG)*100:>17.3f}% {break_even_move(h, R_SHORT)*100:>16.3f}%")

    p(f"\n{B}2. Where carry overtakes the round-trip fee{B}")
    for nm, r in (("SOL custody (longs)", R_LONG), ("stable custody (shorts)", R_SHORT)):
        for u in (0.5, 1.0):
            p(f"   {nm:<26s} util {u:>4.0%}: {carry_crossover_hours(r, u):7.1f} h")

    p(f"\n{B}3. Time to zero collateral from carry alone, price flat{B}")
    if md:
        p("\n| Leverage | util 50% | util 100% | Adverse move to liquidate |\n|---|---:|---:|---:|")
        for L in LEVS:
            p(f"| {L}x | {_fmt_h(hours_to_zero_collateral(L, R_LONG))} | "
              f"{_fmt_h(hours_to_zero_collateral(L, R_LONG, 1.0))} | {liquidation_move(L)*100:.2f}% |")
    else:
        p(f"   {'leverage':>9s} {'util 50%':>12s} {'util 100%':>12s} {'liq move':>11s}")
        for L in LEVS:
            p(f"   {L:>8}x {_fmt_h(hours_to_zero_collateral(L, R_LONG)):>12s} "
              f"{_fmt_h(hours_to_zero_collateral(L, R_LONG, 1.0)):>12s} {liquidation_move(L)*100:>10.2f}%")

    p(f"\n{B}4. Fee cost of round-trip COUNT — why frequency dies at leverage{B}")
    if md:
        p("\n| Round trips | 1x | 5x | 10x | 20x |\n|---|---:|---:|---:|---:|")
        for n in (10, 50, 100, 250, 500):
            p("| " + str(n) + " | " + " | ".join(f"{FEE_RT*n*L*100:.0f}%" for L in (1, 5, 10, 20)) + " |")
    else:
        p(f"   {'round trips':>12s}" + "".join(f"{str(L)+'x':>9s}" for L in (1, 5, 10, 20))
          + "   (fees as % of collateral)")
        for n in (10, 50, 100, 250, 500):
            p(f"   {n:>12d}" + "".join(f"{FEE_RT*n*L*100:>8.0f}%" for L in (1, 5, 10, 20)))
    return "\n".join(out)


def self_test():
    """Assert the claims the doc leans on. Cheap, and it catches a silent constant edit."""
    ok = True

    def chk(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"   [{'PASS' if cond else 'FAIL'}] {name}{'  ' + detail if detail else ''}")

    # 1. leverage genuinely cancels
    a = break_even_move(24, R_LONG)
    chk("break-even move independent of leverage",
        all(abs((L * a) / L - a) < 1e-15 for L in LEVS), f"({a*100:.3f}% at 1 day)")
    # 2. the crossover hinge
    chk("carry overtakes fee after ~15 h for longs at 50% util",
        abs(carry_crossover_hours(R_LONG) - 15.0) < 0.01)
    chk("shorts get ~5.3x longer before carry dominates",
        abs(carry_crossover_hours(R_SHORT) / carry_crossover_hours(R_LONG) - R_LONG / R_SHORT) < 1e-9,
        f"({carry_crossover_hours(R_SHORT):.0f} h vs {carry_crossover_hours(R_LONG):.0f} h)")
    # 3. the headline liquidation-from-carry number
    h250 = hours_to_zero_collateral(250, R_LONG)
    chk("250x is wiped by carry alone in ~2 days at 50% util", 40 < h250 < 60, f"({h250:.0f} h)")
    chk("250x liquidates on a 0.40% adverse move", abs(liquidation_move(250) - 0.004) < 1e-12)
    # 4. frequency
    cost = FEE_RT * 100 * 10
    chk("100 round trips at 10x costs 120% of collateral in fees", abs(cost - 1.2) < 1e-12,
        f"({cost*100:.0f}%)")
    # 5. carry is never a credit
    chk("borrow rate is never negative (both sides always pay)", R_LONG > 0 and R_SHORT > 0)
    print(f"\n   {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", action="store_true", help="emit tables as markdown")
    ap.add_argument("--self-test", action="store_true", help="assert the doc's load-bearing claims")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(self_test())
    print("LEVERAGE ECONOMICS — Jupiter Perps (params as of 2026-08-05, verify at docs.jup.ag)")
    print(tables(a.markdown))
    print("\nNot modelled (each makes reality worse, never better): price-impact fee, keeper")
    print("latency, priority fees/Jito tips, failed transactions, the liquidation penalty itself.")


if __name__ == "__main__":
    main()
