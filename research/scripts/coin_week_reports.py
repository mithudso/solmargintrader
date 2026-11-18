"""Human-readable definitions of the actual weekly market tests (report v2)."""

from __future__ import annotations

import json
import math

from research.reversal_history import iso

MODE_LABELS = {
    "baseline": "Underlying strategy without an extra filter",
    "shape": "Underlying strategy + causal 48-bar shape filter",
    "shape_control": "Underlying strategy + shape-availability control",
    "frequency": "Underlying strategy + fitted harmonic direction filter",
    "frequency_control": "Underlying strategy + harmonic-fit availability control",
    "linear_control": "Underlying strategy + positive 64-bar log-price regression slope filter",
}


def resolved_policy(config: dict, step: int) -> dict:
    """Resolve defaults and the same cadence scaling used by member_signals."""
    from backtester.core.zec_ensemble import _Member

    result = json.loads(json.dumps(config))
    for spec in [
        *result["members"],
        *([result["gate"]] if "gate" in result else []),
        *([result["fallback"]] if "fallback" in result else []),
    ]:
        strategy = _Member(spec, interval="1m").strategy
        params = dict(strategy.params)
        if spec["strategy"] in {"voltarget", "garch_voltarget"}:
            params["target_vol"] = strategy.target_vol * math.sqrt(step / 60)
        spec["params"] = params
    return result


def spec_label(spec: dict) -> str:
    params = json.dumps(spec.get("params", {}), sort_keys=True, separators=(", ", ": "))
    return f"{spec['strategy'].replace('_', ' ')} {params}"


def policy_label(config: dict) -> str:
    members = "; ".join(spec_label(s) for s in config["members"])
    return f"{config['mode']} [{members}]"


def policy_details(config: dict) -> str:
    parts = [policy_label(config)]
    if "gate" in config:
        parts.append("internal permission signal > 0: " + spec_label(config["gate"]))
    if "fallback" in config:
        parts.append(
            "fallback when permission is false: " + spec_label(config["fallback"])
        )
    parts.append(
        f"persistence={config['persistence']} bars; exposure rebalance threshold={config['rebalance_threshold']}"
    )
    if config.get("weighting"):
        parts.append(
            f"weights fitted by {config['weighting']} on the initial max(member warmup + 64, 256) bars, before validation; configured seed weights are not the fitted weights"
        )
    elif "weights" in config:
        parts.append("fixed weights=" + json.dumps(config["weights"]))
    return ". ".join(parts)


def number(value) -> str:
    return "unavailable" if value is None else f"{value:.4f}"


def render_report(summary: dict) -> str:
    p, market, window, corr = (
        summary[k] for k in ("plan", "market", "analysis_window", "correlations")
    )
    pair = f"{p['coin']}/{p['quote']}"
    lines = [
        f"# {pair}: native spot market backtest and correlation study",
        "",
        f"Report version: {summary['version']}",
        "",
        "## Exactly what was tested",
        "",
        f"**Trading market: {pair}. Venue: {p['venue']}. Native product: {market['product']}. Prices, fees, cash and account equity use {p['quote']}.**",
        f"Each reference account starts with {market['initial_reference_equity_quote']:,} {p['quote']} units. This normalized simulation has no order-book capacity model; it does not assert that this size is executable.",
        f"Requested acquisition: **{iso(p['start'])} to {iso(p['end_exclusive'])}**, exclusive ({window['requested_minutes']:,} minutes).",
        f"Actual backtest input: **{iso(window['analysis_start'])} to {iso(window['analysis_end_exclusive'])}**, exclusive (**{window['analyzed_minutes']:,} consecutive real one-minute bars**). Gap policy: **{window['policy']}**.",
    ]
    if not window["complete_requested_window"]:
        lines += [
            f"**REDUCED WINDOW: this is not a complete-week backtest.** The venue supplied {window['observed_minutes']:,}/{window['requested_minutes']:,} minutes; {window['excluded_observed_minutes']:,} other observed bars were excluded. The longest continuous segment was selected by timestamp count, with the earliest segment breaking ties. No price or outcome determines the segment and no candles are filled."
        ]
    if p["candidate_limit"]:
        lines += [
            f"**INCOMPLETE SMOKE TEST:** only the first {p['templates']:,} templates were requested. This is not the full catalogue."
        ]
    lines += [
        "",
        "## Market strategy backtests",
        "",
        f"{p['templates']:,} underlying spot templates × six filter/control variants × 1m/5m/10m/1h bars × four cost scenarios. Each scenario charges 10, 15, 25 or 60 bps per fill plus 2 bps execution allowance. Closed-bar signals fill at the next open; spot exposure is long/cash. Cash and buy-and-hold controls use the same clock and cost model.",
        "The first 60% is the training prefix, the next 20% is validation and the last 20% is the final test. Full-window accounts are also descriptive. Selection ranks validation net return only, requires ten validation exits, and never reranks on test results. These short-window profits have no multiple-search profitability qualification.",
        f"Strategy matrix: {summary['strategy_rows']:,} rows; {summary['strategy_completed']:,} completed evaluations. Separate Volty/grid/DCA reference models: {summary['special_rows']:,} rows. Repeated overlapping candidates are not independent trials.",
        "",
        "### What each filter means",
        "",
        "The filter is applied to each underlying strategy; a filter name alone is not a complete strategy description.",
        "",
        "| Code in result files | Test definition |",
        "|---|---|",
    ]
    lines += [f"| `{code}` | {label} |" for code, label in MODE_LABELS.items()]
    lines += [
        "",
        "Shape classification uses only the past 48 closed bars. Its allowed shapes depend on the underlying strategy family; the frozen shape rules and catalogue are in the run plan. The shape control uses the identical known-shape clock but permits every known shape.",
        "The harmonic model fits intercept, trend and a selected sine/cosine period to 64 past closed log-price bars and freezes the fit for 16 bars. The frequency filter permits positive fitted harmonic increments after removing the trend. The linear control permits a positive slope from a separate intercept-plus-trend regression on those same 64 bars, frozen for the same 16 bars. The availability control permits all bars where the harmonic fit is available. Unknown features cannot authorize exposure.",
        "The underlying committee combines member exposures as follows: single/all = minimum; any = maximum; majority = strictly more than half positive; supermajority = at least two thirds positive; weighted = weighted exposure; other combination modes = mean. Internal gates, fallbacks, persistence and rebalance thresholds below remain part of the policy.",
        "",
        "### Frozen validation selections: underlying strategy plus filter",
        "",
        "| Cadence | Fee bps/fill (+2 bps) | Underlying strategy | Extra filter/control | Validation return | Final test return | Test exits |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    selected = [row for result in summary["strategies"] for row in result["selected"]]
    for row in selected:
        val, test = row["splits"]["validation"], row["splits"]["test"]
        lines.append(
            f"| {row['interval']} | {row['fee_bps_per_fill']} | {policy_label(row.get('resolved_config', row['config']))} (`{row['candidate_id']}`) | {MODE_LABELS[row['mode']]} | {val['total_return']:.2%} | {test['total_return']:.2%} | {test['trade_count']} |"
        )
    if not selected:
        lines.append(
            "| — | — | No policy met the validation-exit requirement | — | — | — | — |"
        )
    lines += [
        "",
        "Selected policy definitions (parameters are the frozen configuration):",
        "",
    ]
    seen = set()
    for row in selected:
        key = (row["candidate_id"], row["interval"])
        if key not in seen:
            lines.append(
                f"- `{row['candidate_id']}` at {row['interval']}: {policy_details(row.get('resolved_config', row['config']))}."
            )
            seen.add(key)
    lines += [
        "",
        "All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.",
        "",
        "## Return correlations: diagnostics separate from market backtests",
        "",
        f"Target: future **{pair} log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's {p['quote']} quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.",
        f"Searched {len(corr['features'])} features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon ({p['replicates']:,} replicates). The resulting p-values are then multiplied by {corr.get('family_multiplier', 1)} planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.",
        f"**Batch-family corrected final-test associations at p ≤ 0.05: {corr['corrected_test_findings']}.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.",
        "",
        "| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |",
        "|---|---:|---:|",
    ]
    for row in corr["contemporaneous"]:
        lines.append(
            f"| {pair} returns vs {row['reference']}/{p['quote']} returns | {number(row['pearson_descriptive'])} | {row['n']:,} |"
        )
    if not corr["contemporaneous"]:
        lines.append("| No separate reference market available | — | — |")
    lines += [
        "",
        "| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in corr["training_only_shortlist"]:
        s = row["splits"]
        lines.append(
            f"| {row['feature']} | {row['horizon_minutes']}m | {number(s['train']['pearson'])} | {number(s['validation']['pearson'])} | {number(s['test']['pearson'])} | {number(s['test'].get('p_familywise'))} |"
        )
    lines += [
        "",
        "### Correlation coverage: estimated versus unavailable tests",
        "",
        "A sparse reference invalidates only that reference's affected features. Target-only tests retain their own observations. Null blocks shuffle the complete regular target clock before each feature mask is applied. Zero corrected findings is not evidence that unavailable tests found no association.",
        "",
        "| Split | Future horizon | Computed feature tests | Insufficient history | Constant feature/target | Observations per feature (range) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in corr.get("coverage", []):
        lines.append(
            f"| {row['split']} | {row['horizon_minutes']}m | {row['computed']} | {row['insufficient']} | {row['constant']} | {row['minimum_n']}–{row['maximum_n']} |"
        )
    lines += [
        "",
        "## Other analyses and their limits",
        "",
        "Volty: 50 frozen settings, four cadences, four costs and three OHLC intrabar paths; synthetic 1x long/short with 0.1 bps/hour carry, not actual perpetual funding or fills. Grid/DCA: 20 frozen canonical configurations on 1m/5m/1h, with pessimistic OHLC execution; 10m is explicitly unsupported.",
        "Cycles: whole-search price/return spectra, confirmed pivot spacing, and forecasts fitted before evaluation (harmonic-plus-trend versus separate linear-trend and last-price persistence forecasts). These forecast controls are separate from the linear strategy filter above.",
        f"{summary['cycle_tests']:,} global/rolling cycle tests share a within-market Holm correction. Smallest corrected p: {summary['minimum_cycle_p_holm']:.6f}; first-test resolution floor: {summary['cycle_resolution_floor']:.6f}. A floor above 0.05 makes this inconclusive. Cycle results are exploratory per market; no batch-wide cycle significance claim is made.",
        "Reversals: frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m excursion horizons, nonoverlap controls and unconditional baselines. These descriptive excursions are not executable fills.",
        "Captured receive-time books, historical top50 universes, Oracle barrier/exit50 replay, long-history daily CPCV and the original long-history shape router require unavailable inputs. coverage.json maps every transferred study and exclusion. One week cannot establish robustness across regimes; modelled costs do not supply observed spreads, depth, latency, funding or fills. Annualized Sharpe is omitted.",
        "",
        "## Reproduction and integrity",
        "",
        "inputs/*.json.zlib retain exact provider pages and normalized candles. run-plan.json.zlib freezes products, options, code hashes and the complete catalogue. manifest.json binds generated artifacts. Offline verification rechecks candle normalization, hashes, report reproduction and result counts. A finished run is immutable. Acquire a new output directory to change markets or options.",
        "",
    ]
    return "\n".join(lines)
