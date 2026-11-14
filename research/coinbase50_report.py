"""Render audited numerical artifacts; the report never reruns a strategy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from research.coinbase50_data import save, sha


def table(rows, headers):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + ["| " + " | ".join(str(x) for x in row) + " |" for row in rows])


def coin_ranking(run, eligible, scenario, gate):
    rows = []
    for symbol in eligible:
        value, hold = 1.0, 1.0
        rounds = 0
        data = json.loads((run / f"{symbol}_grid.json").read_text())
        for fold in range(3):
            with np.load(run / f"{symbol}_f{fold}_{scenario}.npz") as x:
                value *= float(x["equity"][gate, -1])
                hold *= float(x["passive"][-1])
            cell = next(c for c in data["folds"][fold]["scenarios"] if c["scenario"] == scenario)
            rounds += cell["gates"][gate]["round_trips"]
        rows.append({"symbol": symbol, "grid_return_pct": (value - 1) * 100, "hold_return_pct": (hold - 1) * 100, "round_trips": rounds})
    return sorted(rows, key=lambda x: -x["grid_return_pct"])


def verify_inputs(run, manifest):
    if manifest.get("status") != "complete":
        raise ValueError("study did not complete")
    checksums = {}
    for name, expected in manifest["artifacts"].items():
        local = Path(name).name
        if local in checksums:
            raise ValueError("duplicate artifact identity")
        checksums[local] = expected
    required = {"cycle_summary.json", "clock_tests.json", "portfolios.json", "baselines.json",
                "selection.json", "portfolio_curves.npz"}
    for symbol in manifest["grid_eligible"]:
        required.add(f"{symbol}_grid.json")
        required.update(f"{symbol}_f{fold}_{scenario}.npz" for fold in range(3)
                        for scenario in ("zero_2", "zero_25"))
    if required - checksums.keys():
        raise ValueError("missing artifact checksum")
    for name, expected in checksums.items():
        path = run / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    data = Path(manifest["data"])
    for name in ("universe", "protocol"):
        if sha(data / (name + ".json")) != manifest[name + "_sha256"]:
            raise ValueError(name + " binding changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    run, dest = args.run, args.results
    manifest = json.loads((run / "manifest.json").read_text())
    verify_inputs(run, manifest)
    dest.mkdir(parents=True, exist_ok=True)
    root = Path(manifest["data"])
    universe = json.loads((root / "universe.json").read_text())
    cycles = json.loads((run / "cycle_summary.json").read_text())
    clocks = json.loads((run / "clock_tests.json").read_text())
    portfolios = json.loads((run / "portfolios.json").read_text())
    baselines = json.loads((run / "baselines.json").read_text())
    selection = json.loads((run / "selection.json").read_text())
    eligible = manifest["grid_eligible"]
    rankings = {f"{scenario}_{gate}": coin_ranking(run, eligible, scenario, gate) for scenario in ("zero_2", "zero_25") for gate in (0, 15)}
    compact = {"run_manifest": str((run / "manifest.json").resolve()), "run_manifest_sha256": sha(run / "manifest.json"), "universe": universe["assets"], "grid_eligible": eligible, "grid_excluded": manifest["grid_excluded"], "cycle_summary": cycles, "clock_tests": clocks, "portfolios": portfolios, "baselines": baselines, "selection": selection, "coin_rankings": rankings}
    save(dest / "coinbase50_20261111_summary.json", compact)
    # UTC profiles show all directional50; direction and activity use different units.
    directional = [x["symbol"] for x in universe["assets"] if x["directional50"]]
    fig, axes = plt.subplots(1, 3, figsize=(15, 14), sharey=True, constrained_layout=True)
    for axis, metric, title in zip(axes, ("direction", "absolute_return", "log_quote_volume"), ("Hourly direction (basis points)", "Absolute hourly return (basis points)", "Log quote-volume deviation"), strict=True):
        values = []
        for symbol in directional:
            row = next(x for x in clocks if x["symbol"] == symbol and x["clock"] == "UTC" and x["metric"] == metric)
            profile = np.array(row.get("profile", [np.nan] * 24))
            values.append(profile * (10000 if metric != "log_quote_volume" else 1))
        values = np.asarray(values)
        bound = np.nanquantile(np.abs(values), 0.98)
        artist = axis.imshow(values, aspect="auto", cmap="RdBu_r", vmin=-bound, vmax=bound)
        axis.set_xticks(np.arange(0, 24, 3), np.arange(0, 24, 3))
        axis.set_xlabel("UTC candle opening hour")
        axis.set_title(title)
        fig.colorbar(artist, ax=axis, shrink=0.5)
    axes[0].set_yticks(range(len(directional)), directional)
    fig.suptitle("Complete-day demeaned profiles; color alone does not establish predictability")
    fig.savefig(dest / "coinbase50_20261111_hours.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), constrained_layout=True)
    for axis, interval in zip(axes, ("5m", "1h"), strict=True):
        rows = [x for x in cycles if x["interval"] == interval and x["mode"] == "market_calendar_residual" and x.get("windows", 0) >= 4]
        for row in rows:
            axis.scatter(row["log2_period_iqr"], row["forecast_mse_ratio"], s=20)
            axis.annotate(row["symbol"], (row["log2_period_iqr"], row["forecast_mse_ratio"]), fontsize=6)
        axis.axhline(1, color="black", linestyle="--", linewidth=1)
        axis.set_xlabel("Period variability: IQR in octaves (smaller = steadier)")
        axis.set_ylabel("Frozen wave MSE / last-price MSE (smaller = better)")
        axis.set_title(f"{interval}: market and UTC-hour residual controls")
    fig.savefig(dest / "coinbase50_20261111_cycles.png", dpi=160)
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    with np.load(run / "portfolio_curves.npz") as curves:
        dates = pd.to_datetime(curves["timestamp"], unit="s", utc=True)
        for mask in (0, 1, 3, 7, 15, 31):
            axis.plot(dates, (curves[f"zero_2_m{mask:02d}"] / 10000 - 1) * 100, label=f"mask{mask}: " + ("+".join(next(x for x in portfolios if x["scenario"] == "zero_2" and x["mask"] == mask)["factors"]) or "unfiltered marketcap10"))
        axis.plot(dates, (curves["zero_2_hold_0"] / 10000 - 1) * 100, "--", label="marketcap10 liquidated hold")
    axis.set_ylabel("Total account return (%)")
    axis.legend(fontsize=8)
    axis.set_title("Later-time spot portfolios; zero commission +2bps per side; all idle cash counted")
    fig.savefig(dest / "coinbase50_20261111_portfolios.png", dpi=160)
    plt.close(fig)
    tested = [x for x in clocks if x["status"] == "tested"]
    clock_counts = {m: sum(x["holm_p"] <= 0.05 for x in tested if x["metric"] == m) for m in ("direction", "absolute_return", "log_quote_volume")}
    primary = {x["mask"]: x for x in portfolios if x["scenario"] == "zero_2"}
    strategy_finding = f"At zero commission +2bps execution per side, the unfiltered marketcap10 grid returns {primary[0]['return_pct']:.2f}%, training-ranked coin selection returns {primary[1]['return_pct']:.2f}%, and all five factors together return {primary[31]['return_pct']:.2f}%. The selection gain is {primary[1]['gain_vs_unfiltered_grid_pp']:.2f} percentage points with adjusted p={primary[1]['holm_p_vs_grid']:.2f}; it is not established as a repeatable advantage. The selected passive cohort returns {primary[1]['same_selection_hold_return_pct']:.2f}%. Combining every filter lowers exposure and drawdown, but does not produce superior profit in this test. Do not promote the full combination on these results."
    text = ["# Coinbase top50: wavelengths, grid selection, shapes, topology and time of day", "", "This is a current-survivor, complete-feed historical experiment. It does not establish future profit or an executable live edge. No orders, runtime universe, or armed settings changed.", "", "## Main findings", "", strategy_finding, "", f"The 300-test family finds {clock_counts['direction']} significant direction tests, {clock_counts['absolute_return']} volatility tests and {clock_counts['log_quote_volume']} volume tests at Holm-adjusted p≤0.05. Counts cover 50 coins × two clocks; the same coin can appear twice. Activity seasonality does not by itself identify a profitable buy hour.", "", f"Grid simulation admits {len(eligible)}/50 directional assets with complete 116-day15m histories. Missing/short histories remain cash in the all50 portfolio and appear below. Selection chooses up to10 eligible coins using only the preceding26days. The selection-off comparator uses the10largest eligible market-cap coins, with the same budget. Separate all50 controls leave incomplete coins as cash; an all-eligible control invests across the admitted cohort. This retrospective complete-feed cohort is not a point-in-time investable universe.", "", "## Later-time portfolio comparison", "", "Three consecutive30day tests end2026-11-08 19:00UTC, before every unsealed holdout. Each uses26days training. Capital is$10,000 with no borrowing. All32 factorial portfolios use the same dates and ledger. Existing exits remain active while entry gates are closed. All inventory is sold with costs at each fold boundary; accounts compound across folds.", "", table([[x['scenario'], x['mask'], '+'.join(x['factors']) or 'unfiltered', f"{x['return_pct']:.2f}", f"{x['max_drawdown_pct']:.2f}", f"{x['same_selection_hold_return_pct']:.2f}", f"{x['gain_vs_unfiltered_grid_pp']:.2f}", f"{x['holm_p_vs_grid']:.4f}"] for x in portfolios if x["mask"] in (0, 1, 3, 5, 9, 17, 31)], ["Cost scenario", "Mask", "Factors", "Return%", "MaxDD%", "Same-selection hold%", "Gain vs unfiltered pp", "Adjusted p"]), "", "All128 cells, including unfavorable results, are in the compact JSON. Correction spans32masks×4costs. Paired seven-day bootstrap blocks use the same sampled dates for all variants. Confidence intervals describe daily log-growth differences, not guaranteed returns. Ninety test days give few independent clusters. The winning historical mask is not a preselected strategy.", "", "![Portfolio curves](results/coinbase50_20261111_portfolios.png)", "", "## Most profitable coins in this test", "", "These rankings use the fixed unfiltered grid, not a hindsight choice among16gates. Coin sleeves compound independently over the same three folds; the passive comparison pays both entry and terminal exit costs. Earlier eight-coin shape-study rankings used different dates and policies and are not directly comparable.", "", table([[x['symbol'], f"{x['grid_return_pct']:.2f}", f"{x['hold_return_pct']:.2f}", x['round_trips']] for x in rankings['zero_2_0']], ["Coin", "Grid return% zero+2bps", "Hold return%", "Completed exits"]), "", "## Wavelength consistency", "", "Full-window periods are descriptive. Every spectrum searches periods containing at least four cycles and six observations per cycle. A half-window fit freezes its period, phase and amplitude, then predicts the other half. The forecast is anchored at the last observed value; it excludes fitted linear drift. The comparison is last-price persistence. No minimum pivot spacing manufactures a rhythm. Stable period selection can result from a bounded search or market/calendar effects; consistency alone is not validation.", "", "Many periods cluster near the upper search boundary. That concentration can be caused by detrending, calendar removal and the candidate-period grid; a low period IQR does not validate a clock. The controlled series residualizes hourly-calendar effects and BTC beta. Each forecast fits those nuisance coefficients on training rows only. Descriptive full-window coefficients may use their entire window and never become trading signals. BTC residualized against itself is degenerate, so its controlled cycle/H1 features are unavailable and those entry gates fail closed. A residual-energy floor prevents numerical regression noise from becoming a normalized topology signal. Fast and slow analyses cover different periods and cannot be compared as if they were simultaneous.", "", table([[x['symbol'], x['interval'], x['windows'], f"{x.get('period_median_hours', float('nan')):.2f}", f"{x.get('log2_period_iqr', float('nan')):.2f}", f"{x.get('forecast_mse_ratio', float('nan')):.2f}", f"{x.get('forecast_wins', 0)}/{x['windows']}"] for x in sorted(cycles, key=lambda r: (r['interval'], r.get('log2_period_iqr', 99), r['symbol'])) if x['mode'] == 'market_calendar_residual'], ["Coin", "Bars", "Windows", "Median period hours", "Period IQR octaves", "Future MSE / persistence", "Future wins"]), "", "![Period stability and later error](results/coinbase50_20261111_cycles.png)", "", "## Time of day", "", "Hourly open-to-close log returns measure direction. Absolute returns measure activity. log(1+close×basevolume) measures quote-volume activity. Each complete24hour day is demeaned, so an overall rising day does not manufacture a buy hour. Missing, duplicated DST,23hour and25hour days are excluded without interpolation. UTC and America/New_York are separate dependent clock tests. Direction uses seven-day cluster sign flips; volatility and volume use daily hour-label rotations. All tests use9,999draws and a maximum across24hours, then Holm correction across all300coin/clock/metrictests. Insufficient histories receive p=1. Monte Carlo draws do not create extra independent days.", "", "The first half of complete available days selects a profile; the second half checks its stability. Raw direction may include a common market effect. It is not coin-specific evidence. The grid's separate UTC-hour gate fits only its own preceding26day training window and buys in the12highest mean-return hours; it does not import later full-sample clock findings.", "", table([[x['symbol'], x['clock'], x['metric'], x['days'], f"{x['holm_p']:.4f}", f"{x.get('later_profile_correlation',0):.2f}", x.get('train_best_hour','—'), x.get('test_best_hour','—')] for x in sorted(clocks, key=lambda x:(x['metric'],x['holm_p'],x['symbol']))], ["Coin", "Clock", "Metric", "Days", "Adjusted p", "Later profile correlation", "Train peak hour", "Later peak hour"]), "", "![UTC hourly profiles](results/coinbase50_20261111_hours.png)", "", "## What each factor does", "", "- Coin selection: completed2% dip/recovery cycles per day, penalized by price-path efficiency and weighted by range occupancy and log quote volume. Unfinished recoveries remain right-censored. Historical volume is not order-book depth. These are hypotheses motivated by the prior grid/DCA research; that research did not prove these thresholds or superior coin rankings.", "- Frequency: once per UTCday fit the preceding7days of hourly market/calendar-residual cumulative returns. Require successive daily period estimates within0.5octave and an extrapolated rising phase below its harmonic center. Missing hourly continuity resets the fit.", "- Shape:48completed15m bars; permit range, bowl or V-rebound in the lower two-thirds of the observed range. Labels and observed positions are causal geometric hypotheses, not predictions of a pattern's eventual endpoint.", "- Time: entry hours ranked using training-only demeaned mean returns. Existing inventory exits at any hour.", "- H1: genuine Vietoris–Rips persistent homology, coefficient field2, Euclidean distance, full filtration through dimension1 with triangles. Use96past hourly residual returns embedded in3dimensions with lag2, center and divide by global RMS. Score is maximum finiteH1lifetime divided by cloud diameter. Gate is at least the training median. No embedding crosses a timestamp gap. This is separate from chart geometry and is not a reconstruction theorem or crash predictor. Raw-volatility correlation is included in per-coin evidence.", "", "A fixed7rung geometric ladder uses training5th/95th percentiles expanded to bracket the last training close by at least2%. Each rung uses10% of its coin budget. Orders planned at the preceding close fill only on later candles. Buys cannot be funded by same-bar sells, and a same-bar round trip cannot count. Forced fold-end liquidation is distinct from completed grid exits.", "", "## Costs and execution limits", "", "zero_2/zero_10/zero_25 charge0commission plus2/10/25bps adverse execution per side. fee10_2 charges10bps commission plus2bps execution per side. These are stress scenarios, not observed spreads. Coinbase One does not waive Advanced Trade fees and retains spread; zero commission is conditional on the user's eligible product, plan and remaining allowance. Subscription cost is not charged here. Tick/quantity rounding, queue priority, market impact, historical product limits and order-book depth are unmodeled. OHLC touches do not prove a live fill. Cash and residual inventory are included in every equity curve. The exposure-matched passive comparator uses realized average inventory exposure and is descriptive, not an investable timing rule.", "", "Economic-unit normalization freezes s=100/trainingmedianprice per asset/fold, appliesP′=sP,V′=V/s,Q′=Q/s and restores nativeQ=sQ′. It preserves USD accounting and avoids the canonical ladder's absolute1e-6order-key collision for tiny coins. Tests cover tiny/huge native prices, costs, paused entries and insufficient cash. This does not prove native Coinbase tick/size executability.", "", "## Universe, coverage and exclusions", "", "Current online Coinbase USD spot products are joined to CoinGecko market-cap IDs using the venue's own ticker mapping, not ticker text alone. Literal50 includes peggedUSDT and endsBEAM. Directional50 excludesUSDT and addsCOMP. LIGHTER uses a different Coinbase base ticker from the market-cap symbol. AERO/EDGE ambiguous-symbol market-cap matches are rejected. USDT remains a cycle control; it is not ranked as a directional grid coin. This is current membership, with survivorship and full-period feed availability conditioning.", "", table([[x['symbol'], x['rank'], 'yes' if x['literal50'] else 'replacement', 'grid' if x['symbol'] in eligible else ('peg control' if not x['directional50'] else 'cash: incomplete history')] for x in universe['assets']], ["Coin", "Global market-cap rank", "Literal50", "Grid disposition"]), "", "## Evidence and reproduction", "", f"Full run manifest: `{run / 'manifest.json'}`. Raw request/chunk hashes, coverage and identity snapshots: `{root}`. Frozen protocol: `{root / 'protocol.json'}`. Compact JSON: `research/results/coinbase50_20261111_summary.json`. The package-risk evidence for ripser0.6.15 is UNKNOWN because Endor intelligence is unavailable; the isolated research environment is not a security certification.", "", "Prior mechanics references: `/Users/mitch/.agents/skills/trading-and-investing/references/crypto-coin-selection-for-grid-and-dca-strategies.md` and `/Users/mitch/.global-ai-hub/research/crypto-coin-selection-for-grid-and-dca-strategies`. No unsupported efficacy percentage is imported from the earlier geometry dossier.", "", "```sh", "# Use a fresh directory for a replay; original absolute cache bindings are immutable.", "for phase in diagnostics grid aggregate; do", "  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /Users/mitch/.venvs/coinbase50-20261111/bin/python -m research.coinbase50_study --data " + str(root) + " --output " + str(run.parent / "fresh-replay") + " --phase \"$phase\" || break", "done", "```", ""]
    args.report.write_text("\n".join(text))
    save(dest / "coinbase50_20261111_report_manifest.json", {"run_manifest_sha256": sha(run / "manifest.json"), "report": {str(args.report.resolve()): sha(args.report)}, "artifacts": {str(x.resolve()): sha(x) for x in sorted(dest.glob("coinbase50_20261111*")) if x.name != "coinbase50_20261111_report_manifest.json"}})
    print(args.report)


if __name__ == "__main__":
    main()
