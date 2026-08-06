#!/usr/bin/env python3
"""Cost economics of SHORT-HORIZON leveraged perpetuals on Jupiter Perps.

Sibling of research/leverage_economics.py, which stops at a 1-hour hold. Below an hour
the cost picture inverts: carry becomes a rounding error and three terms that
leverage_economics.py explicitly does not model -- per-transaction Solana cost, required
edge per trade, and the barrier's position inside the noise band -- become the whole story.

Generates every table in docs/short-horizon-leverage-concept-family.md. No network, no
data files: closed-form arithmetic over published venue parameters plus ONE clearly
labelled volatility assumption, so it reproduces exactly.

    python3 research/short_horizon_economics.py             # print all tables
    python3 research/short_horizon_economics.py --markdown  # emit the doc's tables
    python3 research/short_horizon_economics.py --self-test # assert load-bearing claims

The result that organises the document:

    toll_per_round_trip = fee_rt + rate*util*hours + 2*fixed_tx_cost/notional

At a 1-minute hold the middle term is ~0.1% of the toll. Turnover, not leverage, is what
kills this family -- and leverage is the only term that makes the FIXED cost cheaper per
unit of collateral, which is the one place the usual intuition runs backwards.

VENUE PARAMETERS (as of 2026-08-06 -- verify against docs.jup.ag before relying on them)
----------------------------------------------------------------------------------------
  base fee            0.06% each way = 12 bps round trip, on notional
  borrow rate         hourly, never negative, paid by BOTH sides, linear in utilisation
  max hourly (SOL)    ~0.016%/hr   <- longs borrow the volatile custody
  max hourly (stable) ~0.003%/hr   <- shorts borrow the stable custody
  liquidation         forfeits 100% of REMAINING collateral

THE ONE ASSUMPTION THAT IS NOT A VENUE PARAMETER
-------------------------------------------------
  VOL_ANNUAL = 0.70 -- an order-of-magnitude stand-in for SOL annualised volatility, used
  ONLY in table 5. It is NOT a measurement from this repo: the repo's entire evidence base
  is 1-hour bars (see research/SWEEP-9COIN.md), which cannot resolve minute-scale paths.
  Table 5 is a scaling argument, not a backtest. Override with --vol to see the sensitivity.

NOT MODELLED (each one makes the real picture WORSE, never better)
-------------------------------------------------------------------
  * price-impact fee -- per-custody factor/exp/threshold are on-chain and undocumented.
  * request-to-fill drift: the keeper flow is two transactions and Jupiter publishes no
    latency figure, so the fill price is the oracle print at an unknown later moment.
  * failed transactions, which cost the fee and deliver no position.
  * the liquidation penalty itself -- table 5 shows when the barrier is REACHED.
"""
from __future__ import annotations

import argparse
import math

FEE_RT = 0.0012          # 6 bps each way, on notional
R_LONG = 0.00016         # per hour, SOL custody, at 100% utilisation
R_SHORT = 0.00003        # per hour, stable custody, at 100% utilisation
UTIL = 0.5               # utilisation assumption, matches leverage_economics.py
VOL_ANNUAL = 0.70        # SEE DOCSTRING -- assumption, not a measurement
HOURS_PER_YEAR = 24 * 365

HORIZONS = [
    ("10 s", 10 / 3600),
    ("30 s", 30 / 3600),
    ("1 min", 1 / 60),
    ("5 min", 5 / 60),
    ("15 min", 15 / 60),
    ("1 h", 1.0),
    ("4 h", 4.0),
]
# Fixed per-transaction Solana cost scenarios, USD. A trader submits the request
# transaction; the keeper submits fulfilment. Tips are the trader's choice and dominate.
TX_COSTS = [("base fee only", 0.0002), ("modest priority", 0.01), ("contested/Jito", 0.50)]
NOTIONALS = [500, 2_000, 10_000, 50_000, 250_000]
LEVS = [2, 5, 10, 20, 50, 100, 250]


def carry(hours: float, rate: float = R_LONG, util: float = UTIL) -> float:
    """Borrow cost over a holding period, as a fraction of notional."""
    return rate * util * hours


def fixed_cost_frac(notional: float, tx_usd: float, tx_per_round_trip: int = 2) -> float:
    """Per-transaction Solana cost as a fraction of notional. Open and close are separate."""
    return tx_per_round_trip * tx_usd / notional


def toll(hours: float, notional: float, tx_usd: float, rate: float = R_LONG) -> float:
    """Total round-trip cost as a fraction of notional: fee + carry + fixed."""
    return FEE_RT + carry(hours, rate) + fixed_cost_frac(notional, tx_usd)


def required_win_rate(move: float, toll_frac: float) -> float:
    """Win rate needed to break even on a symmetric +/- `move` trade paying `toll_frac`.

    p*move - (1-p)*move - toll = 0  =>  p = 0.5 + toll/(2*move).
    Returns >1 exactly when the toll exceeds the move, i.e. no win rate can rescue it:
    even winning every trade nets move - toll < 0.
    """
    return 0.5 + toll_frac / (2 * move)


def sigma(hours: float, vol_annual: float = VOL_ANNUAL) -> float:
    """Driftless standard deviation of the price move over `hours`, sqrt-of-time scaled."""
    return vol_annual * (hours / HOURS_PER_YEAR) ** 0.5


def liquidation_move(lev: int) -> float:
    """Approximate adverse move that exhausts collateral, ignoring accrued fees."""
    return 1.0 / lev


def hours_to_one_sigma(lev: int, vol_annual: float = VOL_ANNUAL) -> float:
    """Holding time at which one sigma of ordinary noise equals the liquidation move."""
    return HOURS_PER_YEAR * (liquidation_move(lev) / vol_annual) ** 2


def _fmt_dur(hours: float) -> str:
    if hours < 1 / 60:
        return f"{hours * 3600:.0f} s"
    if hours < 1:
        return f"{hours * 60:.0f} min"
    if hours < 24:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} d"


def tables(md: bool = False, vol_annual: float = VOL_ANNUAL) -> str:
    b = "**" if md else ""
    out: list[str] = []
    p = out.append

    p(f"\n{b}1. The toll below an hour — carry stops mattering{b}")
    p("   (fraction of notional, util 50%, long/SOL custody, fixed tx cost excluded)")
    if md:
        p("\n| Hold | Fee | Carry | Toll | Carry share of toll |\n|---|---:|---:|---:|---:|")
        for lab, h in HORIZONS:
            c = carry(h)
            p(f"| {lab} | {FEE_RT*100:.3f}% | {c*100:.4f}% | {(FEE_RT+c)*100:.3f}% | "
              f"{c/(FEE_RT+c)*100:.2f}% |")
    else:
        p(f"   {'hold':>8s} {'fee':>9s} {'carry':>10s} {'toll':>9s} {'carry share':>13s}")
        for lab, h in HORIZONS:
            c = carry(h)
            p(f"   {lab:>8s} {FEE_RT*100:>8.3f}% {c*100:>9.4f}% {(FEE_RT+c)*100:>8.3f}% "
              f"{c/(FEE_RT+c)*100:>12.2f}%")

    p(f"\n{b}2. Fixed Solana cost per round trip, in bps of notional{b}")
    p("   (two transactions per round trip; the fee above is 12.0 bps for comparison)")
    if md:
        p("\n| Notional | " + " | ".join(n for n, _ in TX_COSTS) + " |\n|---|"
          + "---:|" * len(TX_COSTS))
        for n in NOTIONALS:
            p(f"| ${n:,} | " + " | ".join(f"{fixed_cost_frac(n, c)*10000:.2f} bps"
                                          for _, c in TX_COSTS) + " |")
    else:
        p(f"   {'notional':>10s}" + "".join(f"{nm:>18s}" for nm, _ in TX_COSTS))
        for n in NOTIONALS:
            p(f"   {'$'+format(n, ','):>10s}"
              + "".join(f"{fixed_cost_frac(n, c)*10000:>14.2f} bps" for _, c in TX_COSTS))

    p(f"\n{b}3. Win rate required to break even on a symmetric trade{b}")
    p("   (toll = 12 bps fee + 1-minute carry + modest priority fee on $10,000 notional;")
    p("    '—' means no win rate suffices: the toll exceeds the target move itself)")
    tgt = toll(1 / 60, 10_000, 0.01)
    moves = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]
    if md:
        p(f"\n   Toll = {tgt*10000:.2f} bps.\n")
        p("\n| Target move | Required win rate |\n|---|---:|")
        for m in moves:
            w = required_win_rate(m, tgt)
            p(f"| {m*100:.2f}% | " + (f"{w*100:.1f}%" if w <= 1 else "— impossible") + " |")
    else:
        p(f"   toll = {tgt*10000:.2f} bps")
        for m in moves:
            w = required_win_rate(m, tgt)
            p(f"   move {m*100:>5.2f}%   " + (f"{w*100:>5.1f}%" if w <= 1 else "  — impossible"))

    p(f"\n{b}4. Daily fee burn as a share of collateral, by turnover{b}")
    p("   (fee only; a strategy continuously deployed at one round trip per interval)")
    intervals = [("1 min", 1440), ("5 min", 288), ("15 min", 96), ("1 h", 24), ("4 h", 6)]
    cols = [1, 5, 10, 20]
    if md:
        p("\n| Interval | Round trips/day | " + " | ".join(f"{L}x" for L in cols) + " |\n|---|---:|"
          + "---:|" * len(cols))
        for lab, n in intervals:
            p(f"| {lab} | {n:,} | " + " | ".join(f"{FEE_RT*n*L*100:,.0f}%" for L in cols) + " |")
    else:
        p(f"   {'interval':>9s} {'rt/day':>8s}" + "".join(f"{str(L)+'x':>10s}" for L in cols))
        for lab, n in intervals:
            p(f"   {lab:>9s} {n:>8,d}" + "".join(f"{FEE_RT*n*L*100:>9,.0f}%" for L in cols))

    p(f"\n{b}5. Where the liquidation barrier sits inside the noise band{b}")
    p(f"   (ASSUMPTION, not a measurement: annualised vol {vol_annual:.0%}. sqrt-of-time,")
    p("    driftless. 'time to 1 sigma' = when ordinary noise alone equals the barrier)")
    if md:
        p("\n| Leverage | Adverse move to liquidate | Time for 1σ to reach it | Barrier in σ of a 1-min move |"
          "\n|---|---:|---:|---:|")
        for L in LEVS:
            p(f"| {L}x | {liquidation_move(L)*100:.2f}% | "
              f"{_fmt_dur(hours_to_one_sigma(L, vol_annual))} | "
              f"{liquidation_move(L)/sigma(1/60, vol_annual):.1f}σ |")
    else:
        p(f"   {'leverage':>9s} {'liq move':>10s} {'time to 1σ':>13s} {'barrier in 1-min σ':>21s}")
        for L in LEVS:
            p(f"   {L:>8}x {liquidation_move(L)*100:>9.2f}% "
              f"{_fmt_dur(hours_to_one_sigma(L, vol_annual)):>13s} "
              f"{liquidation_move(L)/sigma(1/60, vol_annual):>20.1f}σ")
    return "\n".join(out)


def self_test() -> int:
    """Assert the claims the doc leans on. Catches a silent constant edit."""
    ok = True

    def chk(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"   [{'PASS' if cond else 'FAIL'}] {name}{'  ' + detail if detail else ''}")

    # 1. carry is negligible below an hour -- the claim that reframes the family
    share = carry(1 / 60) / (FEE_RT + carry(1 / 60))
    chk("carry is under 0.2% of the 1-minute toll", share < 0.002, f"({share*100:.3f}%)")

    # 2. the fee is leverage-independent per unit notional but the FIXED cost is not
    chk("fixed cost falls as notional rises",
        fixed_cost_frac(250_000, 0.50) < fixed_cost_frac(500, 0.50))
    chk("a contested tip on $500 notional exceeds the 12 bps venue fee",
        fixed_cost_frac(500, 0.50) > FEE_RT,
        f"({fixed_cost_frac(500, 0.50)*10000:.0f} bps vs {FEE_RT*10000:.0f} bps)")

    # 3. small targets are unreachable at any win rate
    t = toll(1 / 60, 10_000, 0.01)
    chk("a 5 bps target is impossible at any win rate", required_win_rate(0.0005, t) > 1.0,
        f"(needs {required_win_rate(0.0005, t)*100:.0f}%)")
    chk("a 1% target needs a plausible-looking win rate",
        0.5 < required_win_rate(0.01, t) < 0.60,
        f"({required_win_rate(0.01, t)*100:.1f}%)")

    # 4. turnover, not leverage, is the killer
    burn = FEE_RT * 1440 * 10
    chk("1-minute turnover at 10x burns >1000% of collateral per day in fees",
        burn > 10, f"({burn*100:,.0f}%)")
    chk("1-minute turnover at 1x still burns more than the whole account",
        FEE_RT * 1440 * 1 > 1.0, f"({FEE_RT*1440*100:,.0f}%)")

    # 5. the barrier sits inside the noise band at high leverage
    h250 = hours_to_one_sigma(250)
    chk("at 250x one sigma reaches the barrier in under 30 minutes", h250 < 0.5,
        f"({h250*60:.0f} min)")
    chk("at 250x the barrier is under 5 sigma of a single 1-minute move",
        liquidation_move(250) / sigma(1 / 60) < 5,
        f"({liquidation_move(250)/sigma(1/60):.1f}σ)")

    # 6. sanity on the scaling helper
    chk("sigma scales as sqrt of time", abs(sigma(4) / sigma(1) - 2.0) < 1e-12)

    print(f"\n   {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", action="store_true", help="emit tables as markdown")
    ap.add_argument("--self-test", action="store_true", help="assert the doc's load-bearing claims")
    ap.add_argument("--vol", type=float, default=VOL_ANNUAL,
                    help="annualised volatility assumption for table 5, must be > 0 "
                         "(default 0.70; ignored by --self-test, which asserts the defaults)")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(self_test())
    # Table 5 divides by vol: zero raises, and a negative or NaN vol prints a table that
    # looks plausible but is meaningless. Refuse rather than emit a number nobody can use.
    if not math.isfinite(a.vol) or a.vol <= 0:
        ap.error(f"--vol must be a finite number greater than 0 (got {a.vol})")
    print("SHORT-HORIZON ECONOMICS — Jupiter Perps (params as of 2026-08-06; verify at docs.jup.ag)")
    print(tables(a.markdown, a.vol))
    print("\nTable 5 rests on a volatility ASSUMPTION, not a measurement. This repo's evidence")
    print("base is 1-hour bars and cannot resolve minute-scale paths — see the module docstring.")


if __name__ == "__main__":
    main()
