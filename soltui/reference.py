"""Static reference content for the Research and Signals tabs.

Kept out of `tui.py` so the command registry (`research.get`, `signals.reference`) can serve the same
data to every surface without importing Textual.
"""

from __future__ import annotations

# The Research tab's content. Kept here as data rather than fetched or computed:
# these are the questions each driver answers and what it actually established,
# and both are stable facts about the study. Figures match docs/SCRIPTS.md and
# research/CROSS-ASSET-TRANSFER.md; `python3 research/verify_numbers.py` is the
# gate that keeps the underlying documents honest.
RESEARCH_DRIVERS = [
    ("research/cpcv_sweep.py", "Is a configuration any good?",
     "PBO 0.700 at both daily horizons vs a 0.500 noise line"),
    ("research/cross_asset_cpcv.py", "Does it transfer to another coin?",
     "All 10 top-5 transfers to DOGE/ZEC degraded; none improved"),
    ("research/perturb.py", "Was it fitted to noise?",
     "Pairs are ~2.6x more parameter-sensitive than long-horizon singles"),
    ("research/geometry.py", "Is the leaderboard an artifact of block count?",
     "8->9 blocks moved the best pair -0.441, more than any parameter"),
    ("research/decide.py", "What does each rule say right now?",
     "Targets provably match what the engine would have acted on"),
    ("research/dso_audit.py", "Which results are below the evidence floor?",
     "BTC's rank-1 ou_reversion sits on 6 trades"),
    ("research/sweep.py", "The single 70/30 split it all replaced",
     "In-sample window ended on the highest close in the series"),
    ("research/verify_numbers.py", "Do the docs match their CSVs?",
     "950 figures checked; CI fails the build on drift"),
    ("research/turnover_table.py", "One comparable turnover table",
     "DOGE 3.44% leads SOL 3.32% on a single-timestamp pull"),
]

RESEARCH_FINDINGS = [
    "In-sample rank is anti-informative: PBO 0.700, and Spearman rho(IS, OOS) is "
    "-0.419 at the medium horizon.",
    "The five recommended configurations do not transfer. Only #3 and #4 stayed "
    "positive on all three assets; #2 is 100% positive on SOL and 0% on DOGE "
    "across the same 15 paths.",
    "Path counts are 15 or 21, never the nominal 28 — only buy_and_hold, which "
    "needs no warm-up, reached 28.",
    "The dataset explains more than the strategy: the same 25 strategies score "
    "25/25 on BTC daily and 0/25 on SOL hourly.",
    "Buy-and-hold medians +0.534 on SOL with zero parameters, 2nd of 25 — and on "
    "ZEC it beat all five recommended configurations.",
]

# One-line description per signal family, for the Signals tab. Sourced from the
# taxonomy in research/STRATEGIES.md so the two do not drift into disagreement.
FAMILY_NOTES = {
    "baseline": "The null hypothesis. Any strategy that cannot beat it is a cost-generating machine.",
    "trend": "Bets that direction persists. Fails in chop, where every oscillation is a whipsaw pair.",
    "momentum": "Sign of past return predicts the next period. Its risk is momentum crashes.",
    "regime-filter": "Answers 'bull or bear'. Its value is avoiding drawdowns, not making returns.",
    "breakout": "Bets on range expansion. ~30-35% win rate; a few large winners pay for the false starts.",
    "oscillator-reversion": "Buys exhaustion. In a strong trend the reading stays pinned and it gets run over.",
    "mean-reversion": "Buys distance from a mean. Fails when the mean itself shifts.",
    "volume-flow": "Reads participation, not price. Price-blind, which is why it pairs well.",
    "risk-overlay": "Changes position size, not direction. Reshapes the equity curve.",
    "sma-gated": "One entry rule -- close above its SMA -- under four sizing schemes. "
                 "Measured 0.92-1.00 correlated, so treat them as one bet, not four.",
}

# Indicator functions exposed on the Signals tab, with their equations.
SIGNAL_REFERENCE = [
    ("SMA(n)", "mean of last n closes", "trend"),
    ("EMA(span)", "alpha=2/(span+1), recursive", "trend"),
    ("RSI(p)", "100 - 100/(1+RS), RS=avgGain/avgLoss (Wilder)", "oscillator-reversion"),
    ("MACD(f,s,sig)", "EMA(f)-EMA(s), signal=EMA(sig) of that line", "trend"),
    ("Bollinger(n,k)", "mid +/- k*stdev(ddof=0); bandwidth=(u-l)/mid", "mean-reversion"),
    ("ATR(p)", "Wilder smoothing of max(H-L,|H-pC|,|L-pC|)", "breakout"),
    ("Stochastic(k,d)", "%K=(c-min)/(max-min)*100, %D=SMA(d) of %K", "oscillator-reversion"),
    ("OBV", "cumulative sign(dC) * volume", "volume-flow"),
    ("VWAP(n)", "sum(TP*V)/sum(V), TP=(H+L+C)/3", "mean-reversion"),
    ("Z-score(n)", "(c - mean)/stdev(ddof=1)", "mean-reversion"),
    ("ROC(n)", "c_t/c_{t-n} - 1", "momentum"),
    ("RealisedVol(n)", "stdev(log returns)*sqrt(periods_per_year)", "risk-overlay"),
]
