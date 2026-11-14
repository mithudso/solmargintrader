"""Render the frozen coin-news event study without fetching or selecting events."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.news_event_study import COINS, _preflight, _prepare_cli, write_csv

PREFIX = "news_events_20261112"


def number(value, places=3):
    return "unavailable" if value is None else f"{value:+.{places}f}"


def interval(row, field):
    lo, hi = row[field + "_ci_low"], row[field + "_ci_high"]
    return "unavailable" if lo is None else f"[{lo:+.3f}, {hi:+.3f}]"


def render(home: Path, analyzed: Path, repo: Path):
    _preflight(plotting=True)
    manifest = json.loads((analyzed / "results.json").read_text())
    selection = json.loads((home / "selection-v2-manifest.json").read_text())
    timing = json.loads((home / "timestamp-audit.json").read_text())
    review = json.loads((home / "eligibility-review-v2.json").read_text())
    acquisition = json.loads((home / "price-acquisition.json").read_text())
    summary = {(r["coin"], r["horizon_minutes"]): r for r in manifest["results"]}
    with (analyzed / "event-returns.csv").open() as handle:
        event_rows = list(csv.DictReader(handle))
    with (analyzed / "latency5-event-returns.csv").open() as handle:
        delay_rows = list(csv.DictReader(handle))
    paired = _paired_latency(event_rows, delay_rows)
    out = repo / "research" / "results"
    out.mkdir(exist_ok=True)
    for source, suffix in (
        ("summary.csv", "summary.csv"),
        ("event-returns.csv", "event_returns.csv"),
        ("latency5-summary.csv", "latency5_summary.csv"),
    ):
        shutil.copyfile(analyzed / source, out / f"{PREFIX}_{suffix}")
    write_csv(
        out / f"{PREFIX}_eligibility.csv",
        [
            {
                k: r[k]
                for k in (
                    "coin",
                    "url",
                    "title",
                    "published_at",
                    "include",
                    "reason",
                    "corrected_event_type",
                )
            }
            for r in review["decisions"]
        ],
    )
    write_csv(out / f"{PREFIX}_latency5_paired.csv", list(paired.values()))
    # Git normalizes text on checkout; bind the same LF bytes that CI will read.
    for path in out.glob(PREFIX + "*.csv"):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    _figure(summary, out / f"{PREFIX}_reactions.png")
    text = [
        "# Coin news publication and subsequent prices",
        "",
        "Version: 1.0.0",
        "Delta: initial measured, outcome-blind publication-time event study.",
        "",
        "## What was measured",
        "",
        "This exploratory study follows 61 reviewed coin/article events from August 14 through November 10, 2026 UTC (89 complete days). It measures subsequent Coinbase USD candle-open returns at 1, 5, 15, 60, 240 and 1,440 minutes. The primary horizon is one hour. It also measures a strictly prepublication 60-minute window and the same weekday/UTC time seven days earlier.",
        "",
        "Five publishers supplied 6,603 source rows: CoinDesk, Cointelegraph, Decrypt, CryptoSlate and CryptoPotato. A fixed catalyst-keyword screen, exclusions for price commentary/promotions, earliest-event spacing of 24 hours per coin and a deterministic maximum-20-per-coin hash sample produced 103 candidates. Independent source/coin-role review retained 61 and rejected 42 before event outcome prices were fetched. Rejected candidates were not replaced. The reviewed sample is not a census of all major news or a random sample of all crypto articles.",
        "",
        "DOGE has one retained event. Its row is an individual observation, not a coin-level estimate. The other counts are BTC 9, ETH 14, SOL 17, XRP 8 and ZEC 12. Some articles concern more than one coin; pooled rows are not independent stories. No bullish/bearish sentiment was inferred from event-type labels.",
        "",
        "## Measured returns",
        "",
        "Returns are percentages. Market-relative results are percentage points (pp). Counts show usable 1-minute / 1-hour / 24-hour observations; missing endpoints are never interpolated or replaced by the next observed row.",
        "",
        "| Coin | N: 1m / 1h / 24h | Mean 1m return % | Mean 1h return % | Mean 1h market-relative pp | Mean 24h return % |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for coin in COINS:
        a, b, c = (summary[(coin, h)] for h in (1, 60, 1440))
        text.append(
            f"| {coin} | {a['n']} / {b['n']} / {c['n']} | {number(a['mean_return_pct'])} | {number(b['mean_return_pct'])} | {number(b['mean_excess_pp'])} | {number(c['mean_return_pct'])} |"
        )
    text += [
        "",
        "![Mean one-hour price reaction and market-relative interval](results/"
        + PREFIX
        + "_reactions.png)",
        "",
        "The benchmark is the arithmetic mean of BTC and ETH simple percentage returns for SOL, XRP, DOGE and ZEC. BTC uses ETH as its benchmark; ETH uses BTC. Relative returns subtract the benchmark from the coin return. These are market controls, not beta-adjusted expected returns or causal counterfactuals.",
        "",
        "## One-hour uncertainty and prior movement",
        "",
        "Intervals below are exploratory, pointwise 95% percentile intervals from 1,999 resamples of epoch-anchored seven-day UTC publication blocks. They preserve same-block rows together. They are not simultaneous intervals across coins/horizons, and they do not establish an execution edge.",
        "",
        "| Coin | Prepublication mean 60m return % | One-hour relative mean pp | Relative interval pp | Mean relative change versus prior-week window pp | Prior-week difference interval pp |",
        "| --- | ---: | ---: | --- | ---: | --- |",
    ]
    for coin in COINS + ("ALL",):
        r = summary[(coin, 60)]
        text.append(
            f"| {coin} | {number(r['mean_pre60_return_pct'])} | {number(r['mean_excess_pp'])} | {interval(r, 'excess_pp')} | {number(r['mean_paired_excess_delta_pp'])} | {interval(r, 'paired_excess_delta_pp')} |"
        )
    r = summary[("ALL", 60)]
    text += [
        "",
        f"Across the retained rows, the mean one-hour market-relative return is {number(r['mean_excess_pp'])} pp, with interval {interval(r, 'excess_pp')}. The matched prior-week relative-return difference is {number(r['mean_paired_excess_delta_pp'])} pp, with interval {interval(r, 'paired_excess_delta_pp')}. The prior-week windows may themselves contain news and differ in market regime; this comparison is descriptive.",
        "",
        "## Timing and delayed-observation sensitivity",
        "",
        "The entry proxy is the open of the first minute bucket strictly after the declared publication timestamp. The one-minute measurement ends at the next minute bucket's open. A Coinbase bucket open is its first trade, whose within-minute time is not supplied here. Thus this is a minute-bar proxy, not an exact 60-second return from the first public release, an executable quote or an assumed immediate fill. The prepublication window ends at the open of a fully earlier bucket, so it cannot include the postpublication entry price.",
        "",
        f"Of the 61 retained rows, 18 publication times come directly from publisher APIs and 43 are archive-declared publisher times. For those 43, archive first_seen lagged the declared publication time by a median {timing['archive_first_seen_lag_minutes']['median']:.2f} minutes (range {timing['archive_first_seen_lag_minutes']['minimum']:.2f}–{timing['archive_first_seen_lag_minutes']['maximum']:.2f}). That archiver did not deliver those items at their declared release time. Its first_seen is not the first time any market participant saw the story. Three direct-publisher records show revisions after publication; current wording is not proof of the original headline. No historical sentiment claim is made.",
        "",
        "The predeclared five-minute delay check moves the entry and exit five minutes later while preserving the horizon. The comparison below uses the same available rows in both timing cases for each metric; it does not compare a full sample with a missing-endpoint subset. It is a sensitivity check, not a measured feed latency or a timing optimization.",
        "",
        "| Coin | Paired N: 1m / 1h | Immediate-proxy 1m mean % | Delayed-proxy 1m mean % | Immediate-proxy 1h relative pp | Delayed-proxy 1h relative pp |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for coin in COINS + ("ALL",):
        a, b = paired[(coin, 1)], paired[(coin, 60)]
        text.append(
            f"| {coin} | {a['n']} / {b['n']} | {number(a['immediate_mean'])} | {number(a['delayed_mean'])} | {number(b['immediate_mean'])} | {number(b['delayed_mean'])} |"
        )
    text += [
        "",
        "## Concrete article examples",
        "",
        "These examples illustrate different reported contexts. They are not selected trading rules, causal attribution or independent replications.",
    ]
    choices = (
        ("BTC", "wallet_data_breach", None),
        ("ETH", "remediated_vulnerability_disclosure", None),
        ("SOL", "protocol_activation", "Alpenglow"),
        ("XRP", "protocol_security_fix_scheduled", None),
        ("ZEC", "protocol_testnet_activation", None),
        ("ZEC", "institutional_product_listing", None),
    )
    for coin, event_type, keyword in choices:
        group = [
            r
            for r in event_rows
            if r["coin"] == coin
            and r["event_type"] == event_type
            and (keyword is None or keyword in r["title"])
        ]
        if not group:
            continue
        event = group[0]
        outcomes = {
            int(r["horizon_minutes"]): r for r in group if r["url"] == event["url"]
        }
        hour, day = outcomes[60], outcomes[1440]
        text += [
            "",
            f"{event['title']} — declared publication {event['published_at']}; {coin} return {float(hour['return_pct']):+.3f}% at one hour and {float(day['return_pct']):+.3f}% at 24 hours. One-hour market-relative return: {float(hour['excess_pp']):+.3f} pp.",
            event["url"],
        ]
    text += [
        "",
        "## Interpretation limits",
        "",
        "The results describe what happened after this selected set of reported articles. They do not show that publication caused the move. A filing, announcement, social post, leak or another publisher may have released the information first. Publication often follows an underlying event. Absolute movement and directional accuracy answer different questions. Positive average returns do not establish a rule that can choose direction in advance, and this timing study does not calibrate a 70% next-minute forecast.",
        "",
        "Selection was fixed before fetching outcome prices, but the publisher/keyword/availability sample remains selective. The reviewed event classes mix distinct economic mechanisms. No trading rule or sentiment model was fitted, and no fee-free profitability claim follows. Reserved unsealed price windows were excluded for the coin and its BTC/ETH controls, including the prior-week queries. Existing capture, paper/live owners, orders and paused inference/embedding services were left unchanged.",
        "",
        "## Reproduce and inspect",
        "",
        "```sh",
        "INDEX_NO_AUTO=1 /Users/mitch/.venvs/soltui/bin/python -m research.news_event_study --home /Users/mitch/.local/share/solmargintrader/research/news-events-20261112 --output /Users/mitch/.local/share/solmargintrader/research/news-events-20261112/reproduction-new",
        "```",
        "",
        "Use a fresh output directory. The CLI verifies that the frozen event identities and timestamps match the checksum-bound independent inclusion ledger before computing results. Private raw sources and price responses remain outside Git. The compact event-return CSV contains each article URL, declared publication time, timestamp source, entry proxy, usable outcomes and controls. The eligibility CSV explains each initial candidate's inclusion or rejection.",
        "",
        "The manifest distinguishes the source frozen before price retrieval from the executed analysis source. The later source adds cohort/checksum enforcement and quieter CLI output. The statistical and selection function ASTs are unchanged. Both source snapshots, their exact checksums and the complete delta are retained in the private evidence inventory; the historical freeze manifest was not rewritten.",
        "",
        "- Compact event returns: ["
        + PREFIX
        + "_event_returns.csv](results/"
        + PREFIX
        + "_event_returns.csv)",
        "- Summary and uncertainty: ["
        + PREFIX
        + "_summary.csv](results/"
        + PREFIX
        + "_summary.csv)",
        "- Eligibility audit: ["
        + PREFIX
        + "_eligibility.csv](results/"
        + PREFIX
        + "_eligibility.csv)",
        "- Bound manifest: ["
        + PREFIX
        + "_manifest.json](results/"
        + PREFIX
        + "_manifest.json)",
        "",
        "Primary interface documentation:",
        "https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles",
        "https://cryptocurrency.cv/api/archive",
        "https://github.com/nirholas/cryptocurrency.cv/blob/main/docs/reference/archive.md",
        "https://cryptoslate.com/wp-json/wp/v2/posts",
        "https://cryptopotato.com/wp-json/wp/v2/posts",
        "",
        "Shared canonical llms and graph retrieval are delivered separately from these reproducible source artifacts. The final delivery receipt identifies their exact shared path and verification. This report does not reopen the prior full-suite or claim a new saturation result.",
    ]
    report = repo / "research" / "NEWS-EVENT-STUDY.md"
    report.write_text("\n".join(text) + "\n")
    compact = {
        "version": 1,
        "delta": "initial source-bound empirical output",
        "study": manifest,
        "selection": selection,
        "price_acquisition": acquisition,
        "analysis_source_provenance": json.loads(
            (home / "analysis-source-delta.json").read_text()
        ),
        "timestamp_audit": timing,
        "event_types": dict(
            Counter(
                r["corrected_event_type"] for r in review["decisions"] if r["include"]
            )
        ),
        "private_evidence_home": str(home),
        "complete_private_inventory": str(home / "file-manifest.json"),
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "reporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs": {
            str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.glob(PREFIX + "*")
            if p.name != PREFIX + "_manifest.json"
        },
    }
    (out / f"{PREFIX}_manifest.json").write_text(
        json.dumps(compact, indent=2, allow_nan=False) + "\n"
    )
    return report


def _paired_latency(base, delayed):
    other = {(r["coin"], r["url"], r["horizon_minutes"]): r for r in delayed}
    result = {}
    for coin in COINS + ("ALL",):
        for horizon in (1, 60):
            field = "return_pct" if horizon == 1 else "excess_pp"
            pairs = []
            for row in base:
                if int(row["horizon_minutes"]) != horizon or (
                    coin != "ALL" and row["coin"] != coin
                ):
                    continue
                later = other.get((row["coin"], row["url"], row["horizon_minutes"]))
                if later and row[field] != "" and later[field] != "":
                    pairs.append((float(row[field]), float(later[field])))
            result[(coin, horizon)] = {
                "coin": coin,
                "horizon_minutes": horizon,
                "metric": field,
                "n": len(pairs),
                "immediate_mean": sum(a for a, b in pairs) / len(pairs)
                if pairs
                else None,
                "delayed_mean": sum(b for a, b in pairs) / len(pairs)
                if pairs
                else None,
            }
    return result


def _figure(summary, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = [summary[(coin, 60)] for coin in COINS]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), layout="constrained")
    axes[0].bar(
        x - 0.18,
        [r["mean_return_pct"] for r in rows],
        0.35,
        label="Coin return",
        color="#2878a0",
    )
    axes[0].bar(
        x + 0.18,
        [r["mean_benchmark_pct"] for r in rows],
        0.35,
        label="Market control",
        color="#8c9aab",
    )
    axes[0].set_ylabel("Mean one-hour return (%)")
    axes[0].legend(frameon=False)
    for i, r in enumerate(rows):
        mean = r["mean_excess_pp"]
        axes[1].scatter(i, mean, color="#9a4f20", zorder=3)
        lo, hi = r["excess_pp_ci_low"], r["excess_pp_ci_high"]
        if lo is not None:
            axes[1].vlines(i, lo, hi, color="#9a4f20", linewidth=2)
    axes[1].set_ylabel("One-hour coin minus control (pp)")
    axes[1].set_title("Exploratory 95% seven-day-block intervals", fontsize=10)
    for axis in axes:
        axis.axhline(0, color="#555555", linewidth=0.7)
        axis.set_xticks(x, [f"{c}\nn={r['n']}" for c, r in zip(COINS, rows)])
        axis.grid(axis="y", alpha=0.18)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Price movement after 61 reviewed crypto-news events, Aug–Nov 2026")
    fig.supxlabel(
        "Publisher-declared times; next-minute open proxy. DOGE n=1 is an individual observation.",
        fontsize=9,
    )
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--analyzed", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args(arguments)
    if not _prepare_cli(Path(__file__).resolve(), arguments, plotting=True):
        return 3
    print(render(args.home, args.analyzed, args.repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
