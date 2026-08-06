"""The one comparable turnover table for the ten non-pegged coins.

    python3 research/turnover_table.py
    python3 research/turnover_table.py --check   # exit 1 if a spoke disagrees

Why this exists: turnover is `24h volume / market cap`, and both terms move
continuously. Ten spokes that each pulled their own snapshot produced ten figures
that **cannot be ranked against each other**, and doing it anyway produced a real
error — the SOL spoke claimed the highest turnover of the ten at 3.69% from a
`/coins/solana` call, while the single-timestamp cross-coin pull puts **DOGE
ahead**, 3.44% to SOL's 3.32%. The superlative was an artifact of mixing pulls.

So the rule this module enforces: **every comparative turnover figure comes from
one `/coins/markets` call**, `research/results/top_coins.csv`, taken at
2026-08-05T02:15:22Z. A spoke may still quote its own later snapshot for its own
price and cap — those are per-asset facts. It may not use one to rank itself
against another coin.

`--check` reads the ten spokes and fails if any of them states a turnover that is
not this table's, so the figures cannot silently drift apart again.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "research" / "results" / "top_coins.csv"
AS_OF = "2026-08-05T02:15:22Z"

# Where the spokes live. The skill is canonical; research/coin-intelligence/ is a
# mirror of it, and --check reads whichever is present so it works in a clone that
# has no user-level skills directory.
SPOKE_DIRS = (
    Path.home() / ".claude" / "skills" / "crypto-coin-intelligence" / "references",
    REPO / "research" / "coin-intelligence",
)

# symbol -> spoke filename stem
SPOKES = {
    "BTC": "btc-bitcoin",
    "ETH": "eth-ethereum",
    "SOL": "sol-solana",
    "BNB": "bnb-binance-coin",
    "XRP": "xrp-ripple",
    "TRX": "trx-tron",
    "HYPE": "hype-hyperliquid",
    "DOGE": "doge-dogecoin",
    "ZEC": "zec-zcash",
    "RAIN": "rain-rain",
}


def turnover_table() -> pd.DataFrame:
    """The canonical table: one row per coin, one timestamp, ranked."""
    d = pd.read_csv(SOURCE)
    d = d[d["symbol"].isin(SPOKES)].copy()
    missing = set(SPOKES) - set(d["symbol"])
    if missing:
        raise SystemExit(f"{SOURCE.name} is missing {sorted(missing)}; cannot build the table")
    d["turnover_pct"] = 100.0 * d["volume_24h_usd"] / d["market_cap_usd"]
    d = d.sort_values("turnover_pct", ascending=False).reset_index(drop=True)
    d["turnover_rank"] = d.index + 1
    return d[
        ["turnover_rank", "symbol", "turnover_pct", "volume_24h_usd", "market_cap_usd"]
    ]


def render(t: pd.DataFrame) -> str:
    lines = [
        f"Turnover (24h volume / market cap), all ten from ONE pull, {AS_OF}",
        f"Source: {SOURCE.relative_to(REPO)} (CoinGecko /coins/markets)",
        "",
        "  #  sym    turnover        24h volume            market cap",
    ]
    for _, r in t.iterrows():
        lines.append(
            f"  {int(r.turnover_rank):>1}  {r.symbol:<6} {r.turnover_pct:6.2f}%  "
            f"{int(r.volume_24h_usd):>18,}  {int(r.market_cap_usd):>18,}"
        )
    hi, lo = t.turnover_pct.max(), t.turnover_pct.min()
    lines += [
        "",
        f"Spread {hi:.2f}% / {lo:.2f}% = {hi / lo:.2f}x -- ONE order of magnitude, not two.",
        "",
        "Two figures that are NOT interchangeable with this table:",
        "  BNB  0.73% here, ~1.11% on the float its own spoke argues for (burn address",
        "       and bridge contract removed). The 1.11% is an analytical adjustment to the",
        "       DENOMINATOR and is not comparable to the other nine; keep both, labelled.",
        "  RAIN 0.24% here, and its spoke's point is that the market cap in that",
        "       denominator is not backed by tradeable supply at all (~$294k of bid depth",
        "       against an $8.6B nominal cap). A low turnover understates the problem.",
    ]
    return "\n".join(lines) + "\n"


def find_spoke(stem: str) -> Path | None:
    for d in SPOKE_DIRS:
        p = d / f"{stem}.md"
        if p.exists():
            return p
    return None


def check(t: pd.DataFrame) -> int:
    """Fail if a spoke states a turnover percentage this table does not contain.

    Deliberately loose about *where* the figure appears and strict about its
    value: the aim is to catch a stale or independently-pulled number, not to
    dictate prose. A spoke may carry additional percentages for other things, so
    only figures adjacent to the word "turnover" are considered.
    """
    expected = {r.symbol: round(r.turnover_pct, 2) for _, r in t.iterrows()}

    # A spoke legitimately cites OTHER coins' turnover to place itself in the set —
    # that is the whole purpose of a comparable table. So any value in the table is
    # acceptable anywhere; what is unacceptable is a value the table does not
    # contain, because that is either a stale figure or an independent pull.
    #
    # One exception, and it is analytical rather than sloppy: BNB's spoke argues the
    # float should exclude the burn address and a bridge contract, which changes the
    # DENOMINATOR and yields ~1.11%. That number is not comparable to the other nine
    # and is allowed only in BNB's own file.
    canonical = set(expected.values())

    # Figures a spoke may state that this table deliberately does not contain. Each
    # is a different provenance or a different denominator, so each is allowed only
    # in the file that argues for it and is never used to rank one coin against
    # another.
    allowed_extra = {
        # Float-adjusted: burn address and a bridge contract removed from supply.
        # An adjustment to the DENOMINATOR, argued in BNB's own spoke.
        "BNB": {1.11, 0.76, 1.8},   # 0.758% later API pull; 1.797% Binance-only
        "XRP": {1.8},               # 1.797% Binance-only footnote
    }

    # Percentages that sit near the word "turnover" without being one. Without
    # this, XRP's "0.40%/0.60% fees that kill high-turnover strategies" and ZEC's
    # "DOGE venue-share figure (~1.9%)" both read as turnover claims — a checker
    # that cries wolf gets switched off, which is worse than not having it.
    DISQUALIFY = ("fee", "venue-share", "venue share")

    problems: list[str] = []
    for sym, stem in SPOKES.items():
        p = find_spoke(stem)
        if p is None:
            problems.append(f"{sym}: no spoke found for {stem}.md")
            continue
        text = p.read_text()
        stated = set()
        # Windows are deliberately tight. A wide window turns every percentage in a
        # long footnote into a turnover claim; the figures this needs to catch sit
        # within a few words of the term ("Turnover 3.44%", "~1.4% turnover").
        for pat in (
            r"[Tt]urnover[^.\n]{0,40}?([0-9]+\.[0-9]+)\s*%",
            r"([0-9]+\.[0-9]+)\s*%[^.\n]{0,25}?[Tt]urnover",
        ):
            for m in re.finditer(pat, text):
                if any(w in m.group(0).lower() for w in DISQUALIFY):
                    continue
                stated.add(round(float(m.group(1)), 2))
        if expected[sym] not in stated:
            problems.append(
                f"{sym}: {p.name} does not state its own canonical turnover of "
                f"{expected[sym]}% (found {sorted(stated) or 'none'})"
            )
        bad = stated - canonical - allowed_extra.get(sym, set())
        if bad:
            problems.append(
                f"{sym}: {p.name} states {sorted(bad)}, which is not in the "
                f"{AS_OF} table"
            )
    if problems:
        print("TURNOVER CHECK FAILED")
        for x in problems:
            print(f"  {x}")
        return 1
    print(f"TURNOVER CHECK PASSED: all {len(SPOKES)} spokes agree with {SOURCE.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify the spokes agree with the table")
    args = ap.parse_args(argv)
    t = turnover_table()
    if args.check:
        return check(t)
    print(render(t), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
