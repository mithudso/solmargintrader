"""Exploratory publication-time event study on frozen local news and prices.

The analysis never fetches, fills missing candles, or submits orders. A minute
open is a bucket proxy; it is not the trade available at publication time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import re
import shlex
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

VERSION = "1.0.0"
SEED = 20261112
COINS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "ZEC")
HORIZONS = (1, 5, 15, 60, 240, 1440)
COIN_WORDS = {
    "BTC": r"\b(bitcoin|btc)\b",
    "ETH": r"\b(ethereum|ether|eth)\b",
    "SOL": r"\b(solana|sol)\b",
    "XRP": r"\b(xrp|ripple)\b",
    "DOGE": r"\b(dogecoin|doge)\b",
    "ZEC": r"\b(zcash|zec)\b",
}
EVENT_TYPES = {
    "security": r"hack|exploit|breach|stolen|theft|attack|halt|outage",
    "regulation": r"\bsec\b|court|lawsuit|sues?\b|approv|ruling|regulat|legal|ban\b",
    "institutional_access": r"\betf\b|filing|files?\b|listing|lists?\b|custody|treasury|grayscale|blackrock",
    "protocol_adoption": r"upgrad|mainnet|activat|hard fork|launch|partner|integrat|adopt|deploy|rollout",
}
COMMENTARY = re.compile(
    r"price|prediction|technical analysis|surge|rall(?:y|ies)|plung|crash|soar|"
    r"bullish|bearish|bull run|bear market|sell.?off|slumps?|pumps?|dumps?|"
    r"all.time high|\bath\b|support level|resistance|what happened|"
    r"^what is\b|^how to\b|\bexplained\b|presale|sponsored|press release",
    re.IGNORECASE,
)


class NewsPrerequisiteError(RuntimeError):
    """A named optional dependency failed before any study/report output writes."""


def _preflight(*, plotting=False):
    missing = []
    modules = ("numpy", "matplotlib", "matplotlib.pyplot") if plotting else ("numpy",)
    for name in modules:
        try:
            module = importlib.import_module(name)
            if name == "matplotlib":
                module.use("Agg")
        except Exception:  # noqa: BLE001 -- safe dependency boundary; no import payloads
            missing.append(name)
    if missing:
        raise NewsPrerequisiteError("Unavailable optional Python modules: " + ", ".join(missing))


def _bootstrap_and_reexec(script: Path, arguments):
    """Provision only the helper-owned research environment, then reexecute once."""
    if os.environ.get("ORACLEBOT_NEWS_REEXEC") == str(script):
        raise NewsPrerequisiteError("the private environment still cannot load optional modules")
    repo = script.parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from backtester.run import ensure_environment

    python = ensure_environment(
        script.parent,
        requirements=("numpy>=2.5.4", "matplotlib>=3.11.2"),
        required_modules=("numpy", "matplotlib"),
        owner="oraclebot-news-event-tools/v1", entrypoint=script,
    )
    os.execve(str(python), [str(python), str(script), *arguments],
              {**os.environ, "ORACLEBOT_NEWS_REEXEC": str(script)})


def _prepare_cli(script: Path, arguments, *, plotting=False):
    try:
        _preflight(plotting=plotting)
        return True
    except NewsPrerequisiteError as exc:
        missing = str(exc)
    if os.environ.get("TOOL_NO_VENV") != "1":
        try:
            _bootstrap_and_reexec(script, arguments)
        except Exception as exc:  # noqa: BLE001 -- safe CLI boundary; expose failure type only
            print(f"Private news tool setup failed ({type(exc).__name__})", file=sys.stderr)
    command = shlex.join([
        "uv", "run", "--no-project", "--with", "numpy>=2.5.4", "--with",
        "matplotlib>=3.11.2", "python", str(script), *arguments,
    ])
    print(f"{missing}. Run in an isolated environment:\n{command}", file=sys.stderr)
    return False


def epoch(value: str) -> int:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("publication timestamp needs an explicit timezone")
    return int(parsed.timestamp())


def iso(value: int) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("article needs an absolute HTTP URL")
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def entry_minute(published: int) -> int:
    """Always move forward, including a publication exactly on a boundary."""
    return (published // 60 + 1) * 60


def controls(coin: str) -> tuple[str, ...]:
    return tuple(c for c in ("BTC", "ETH") if c != coin)


def protected_window(start: int, end: int, assets, reservations) -> bool:
    return any(
        any(asset in r["coin"].split("-") for asset in assets)
        and start < r["end"]
        and end > r["start"]
        for r in reservations
    )


def select_events(articles, reservations, start: int, end: int, limit=20):
    """Initial keyword candidates; independent source/coin-role review is required."""
    by_url = defaultdict(list)
    for article in articles:
        by_url[canonical_url(article["url"])].append(article)
    decisions, candidates = [], []
    for url, variants in sorted(by_url.items()):
        times = {epoch(v["published_at"]) for v in variants}
        article = min(variants, key=lambda v: v["timestamp_source"] != "publisher_api")
        title = article["title"]
        published = epoch(article["published_at"])
        for coin, words in COIN_WORDS.items():
            if not re.search(words, title, re.IGNORECASE):
                continue
            row = {
                **article,
                "url": url,
                "coin": coin,
                "published": published,
                "entry": entry_minute(published),
                "duplicate_rows": len(variants) - 1,
            }
            reason = None
            kind = next(
                (
                    k
                    for k, pattern in EVENT_TYPES.items()
                    if re.search(pattern, title, re.IGNORECASE)
                ),
                None,
            )
            if len(times) > 1:
                reason = "conflicting_publication_times_for_url"
            elif not start <= published < end:
                reason = "outside_declared_dates"
            elif COMMENTARY.search(title):
                reason = "price_commentary_evergreen_or_promotion"
            elif kind is None:
                reason = "no_predeclared_catalyst_keyword"
            else:
                assets = (coin,) + controls(coin)
                for anchor in (row["entry"], row["entry"] - 7 * 86400):
                    if protected_window(
                        anchor - 3720, anchor + 86460, assets, reservations
                    ):
                        reason = "protected_event_or_prior_week_window"
                        break
            row["event_type"] = kind
            row["reason"] = reason
            if reason:
                decisions.append(row)
            else:
                candidates.append(row)
    selected = []
    for coin in COINS:
        last = -math.inf
        spaced = []
        for row in sorted(
            (r for r in candidates if r["coin"] == coin),
            key=lambda r: (r["published"], r["url"]),
        ):
            if row["entry"] - last < 86400:
                decisions.append({**row, "reason": "same_coin_24hour_cluster"})
            else:
                spaced.append(row)
                last = row["entry"]
        # A hash sample depends on the frozen URL/coin only, never future returns.
        ranked = sorted(
            spaced,
            key=lambda r: hashlib.sha256(
                f"{SEED}|{coin}|{r['url']}".encode()
            ).hexdigest(),
        )
        selected.extend({**r, "reason": "selected"} for r in ranked[:limit])
        decisions.extend({**r, "reason": "fixed_sample_cap"} for r in ranked[limit:])
    selected.sort(key=lambda r: (r["coin"], r["published"]))
    return selected, decisions


def event_returns(prices, entry: int, minutes: int):
    """Require exact minute keys; never advance by row count across a hole."""
    target = entry + minutes * 60
    if entry not in prices or target not in prices:
        return None
    a, b = float(prices[entry]), float(prices[target])
    if not all(math.isfinite(v) and v > 0 for v in (a, b)):
        raise ValueError("prices must be positive and finite")
    return 100 * (b / a - 1)


def relative_return(coin, prices, entry, minutes):
    import numpy as np

    own = event_returns(prices.get(coin, {}), entry, minutes)
    market = [event_returns(prices.get(c, {}), entry, minutes) for c in controls(coin)]
    if own is None or any(r is None for r in market):
        return own, None, None
    benchmark = float(np.mean(market))
    return own, benchmark, own - benchmark


def measure(events, prices):
    import numpy as np

    rows = []
    for event in events:
        coin, entry = event["coin"], event["entry"]
        for horizon in HORIZONS:
            own, market, excess = relative_return(coin, prices, entry, horizon)
            prior = entry - 7 * 86400
            placebo, placebo_market, placebo_excess = relative_return(
                coin, prices, prior, horizon
            )
            # The publication-minute open may itself be a later first trade.
            # End the pre-window at an entirely earlier bucket instead.
            pre_end = (event["published"] // 60 - 1) * 60
            before = event_returns(prices.get(coin, {}), pre_end - 3600, 60)
            before_market = [
                event_returns(prices.get(c, {}), pre_end - 3600, 60)
                for c in controls(coin)
            ]
            before_excess = (
                before - float(np.mean(before_market))
                if before is not None and all(r is not None for r in before_market)
                else None
            )
            rows.append(
                {
                    "coin": coin,
                    "url": event["url"],
                    "title": event["title"],
                    "source": event["source"],
                    "timestamp_source": event["timestamp_source"],
                    "published_at": event["published_at"],
                    "entry_utc": iso(entry),
                    "entry_delay_seconds": entry - event["published"],
                    "pre60_end_utc": iso(pre_end),
                    "event_type": event["event_type"],
                    "horizon_minutes": horizon,
                    "return_pct": own,
                    "benchmark_pct": market,
                    "excess_pp": excess,
                    "prior_week_return_pct": placebo,
                    "prior_week_benchmark_pct": placebo_market,
                    "prior_week_excess_pp": placebo_excess,
                    "pre60_return_pct": before,
                    "pre60_excess_pp": before_excess,
                    "paired_excess_delta_pp": (
                        excess - placebo_excess
                        if excess is not None and placebo_excess is not None
                        else None
                    ),
                    "paired_absolute_delta_pp": (
                        abs(own) - abs(placebo)
                        if own is not None and placebo is not None
                        else None
                    ),
                }
            )
    return rows


def cluster_interval(rows, field, replicates=1999):
    """Resample fixed seven-day UTC blocks, preserving nearby event dependence."""
    valid = [r for r in rows if r.get(field) is not None]
    if not valid:
        return None, None, 0
    groups = defaultdict(list)
    for row in valid:
        published = row["published_at"]
        # Preserve the date-only library input convention as midnight UTC.
        if len(published) == 10:
            published += "T00:00:00Z"
        block = epoch(published) // (7 * 86400)
        groups[block].append(float(row[field]))
    if len(groups) < 2:
        return None, None, len(groups)
    import numpy as np

    sums = np.array([sum(v) for v in groups.values()])
    sizes = np.array([len(v) for v in groups.values()])
    rng = np.random.default_rng(SEED)
    indices = rng.integers(0, len(groups), size=(replicates, len(groups)))
    means = sums[indices].sum(axis=1) / sizes[indices].sum(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi), len(groups)


def summarize(rows):
    import numpy as np

    result = []
    for coin in COINS + ("ALL",):
        for horizon in HORIZONS:
            group = [
                r
                for r in rows
                if r["horizon_minutes"] == horizon
                and (coin == "ALL" or r["coin"] == coin)
            ]
            observed = [r["return_pct"] for r in group if r["return_pct"] is not None]
            summary = {
                "coin": coin,
                "horizon_minutes": horizon,
                "selected": len(group),
                "n": len(observed),
            }
            summary["up_fraction"] = (
                float(np.mean(np.array(observed) > 0)) if observed else None
            )
            summary["median_return_pct"] = (
                float(np.median(observed)) if observed else None
            )
            for field in (
                "return_pct",
                "benchmark_pct",
                "excess_pp",
                "pre60_return_pct",
                "pre60_excess_pp",
                "prior_week_return_pct",
                "paired_excess_delta_pp",
                "paired_absolute_delta_pp",
            ):
                values = [r[field] for r in group if r[field] is not None]
                lo, hi, dates = cluster_interval(group, field)
                summary["mean_" + field] = float(np.mean(values)) if values else None
                summary[field + "_n"] = len(values)
                summary[field + "_ci_low"] = lo
                summary[field + "_ci_high"] = hi
                summary["seven_day_blocks"] = dates
            result.append(summary)
    return result


def write_csv(path, rows):
    path = Path(path)
    if not rows:
        path.write_text("")
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def reviewed_events(home: Path):
    """Refuse a changed or unreviewed cohort before computing any outcomes."""
    path = home / "events-frozen.json"
    events = json.loads(path.read_text())
    manifest = json.loads((home / "selection-v2-manifest.json").read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if manifest["files"].get(str(path)) != digest:
        raise ValueError("frozen event checksum differs")
    review_path = home / "eligibility-review-v2.json"
    if (
        manifest["files"].get(str(review_path))
        != hashlib.sha256(review_path.read_bytes()).hexdigest()
    ):
        raise ValueError("eligibility review checksum differs")
    review = json.loads(review_path.read_text())
    if (
        review["price_data_accessed"]
        or review["new_articles_added"]
        or review["rejected_rows_replaced"]
    ):
        raise ValueError("review was not the declared outcome-blind correction")
    included = {(r["coin"], r["url"]): r for r in review["decisions"] if r["include"]}
    identities = [(e["coin"], e["url"]) for e in events]
    if len(set(identities)) != len(events) or set(identities) != set(included):
        raise ValueError("cohort differs from the independently included identities")
    for e in events:
        r = included[(e["coin"], e["url"])]
        if (
            e["title"] != r["title"]
            or e["published_at"] != r["published_at"]
            or e["event_type"] != r["corrected_event_type"]
            or e["published"] != epoch(e["published_at"])
            or e["entry"] != entry_minute(e["published"])
        ):
            raise ValueError("reviewed identity or publication clock differs")
    return events


def run(home: Path, output: Path):
    _preflight()
    if output.exists():
        raise ValueError("use a fresh output directory")
    events = reviewed_events(home)
    prices = json.loads((home / "minute-open-prices.json").read_text())
    prices = {c: {int(t): p for t, p in rows.items()} for c, rows in prices.items()}
    output.mkdir(parents=True)
    rows = measure(events, prices)
    summary = summarize(rows)
    write_csv(output / "event-returns.csv", rows)
    write_csv(output / "summary.csv", summary)
    delayed = measure([{**e, "entry": e["entry"] + 300} for e in events], prices)
    delayed = [r for r in delayed if r["horizon_minutes"] <= 60]
    delayed_summary = [s for s in summarize(delayed) if s["horizon_minutes"] <= 60]
    write_csv(output / "latency5-event-returns.csv", delayed)
    write_csv(output / "latency5-summary.csv", delayed_summary)
    manifest = {
        "version": VERSION,
        "seed": SEED,
        "events": len(events),
        "events_per_coin": dict(Counter(r["coin"] for r in events)),
        "horizons_minutes": HORIZONS,
        "confidence_intervals": "exploratory percentile bootstrap by fixed seven-day UTC blocks; not simultaneous or causal",
        "inputs": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (home / "events-frozen.json", home / "minute-open-prices.json")
        },
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": summary,
        "latency5_results": delayed_summary,
    }
    (output / "results.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    return manifest


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(arguments)
    if not _prepare_cli(Path(__file__).resolve(), arguments):
        return 3
    print(
        json.dumps(
            {
                k: v
                for k, v in run(args.home, args.output).items()
                if k not in ("results", "latency5_results")
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
