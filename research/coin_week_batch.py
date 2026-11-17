"""Frozen native-market combination studies; acquisition precedes simulation."""

from __future__ import annotations

import fcntl
import itertools
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from research.coin_week_data import (
    PROVIDERS,
    analysis_window,
    coin_symbol,
    digest,
    download,
    frame_from,
    load,
    market_product,
    read_url,
    save,
    verify_snapshot,
    week_bounds,
)
from research.reversal_history import iso

CATALOGUE_URLS = {
    "coinbase": "https://api.exchange.coinbase.com/products",
    "binance": "https://data-api.binance.vision/api/v3/exchangeInfo",
}


def coin_list(values: list[str]) -> list[str]:
    result = list(
        dict.fromkeys(
            coin_symbol(token)
            for value in values
            for token in value.replace(",", " ").split()
        )
    )
    if not result or len(result) > 12:
        raise ValueError(
            "provide 1..12 distinct coins; each market runs the complete study"
        )
    return result


def catalogue_rows(raw: bytes, provider: str) -> list[dict]:
    body = json.loads(raw)
    entries = body if provider == "coinbase" else body["symbols"]
    if not isinstance(entries, list) or not entries or len(entries) > 50000:
        raise ValueError("invalid native product catalogue")
    result, seen = [], set()
    for entry in entries:
        base_key, quote_key = (
            ("base_currency", "quote_currency")
            if provider == "coinbase"
            else ("baseAsset", "quoteAsset")
        )
        # Symbols outside the CLI's asset grammar cannot be selected. Keep their
        # exact source bytes, but do not turn an unrelated instrument into a pair.
        try:
            base, quote = coin_symbol(entry[base_key]), coin_symbol(entry[quote_key])
        except ValueError:
            continue
        product = entry["id"] if provider == "coinbase" else entry["symbol"]
        if product != market_product(base, quote, provider) or product in seen:
            raise ValueError("ambiguous or malformed native product catalogue")
        seen.add(product)
        status = entry["status"]
        active = (
            (status == "online" and not entry.get("trading_disabled", False))
            if provider == "coinbase"
            else (status == "TRADING" and entry.get("isSpotTradingAllowed") is True)
        )
        result.append(
            {
                "base": base,
                "quote": quote,
                "product": product,
                "active": active,
                "venue_status": status,
            }
        )
    if not result:
        raise ValueError("catalogue contains no supported native spot products")
    return result


def acquire_catalogue(provider: str, path: Path) -> dict:
    if path.exists():
        source = load(path)
    else:
        url = CATALOGUE_URLS[provider]
        raw = read_url(url, max_bytes=16 * 1024 * 1024)
        catalogue_rows(raw, provider)
        source = {
            "provider": provider,
            "url": url,
            "raw": raw.decode(),
            "sha256": digest(raw),
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        save(path, source)
    verify_catalogue(source, provider)
    return source


def verify_catalogue(source: dict, provider: str) -> list[dict]:
    if (
        source["provider"] != provider
        or source["url"] != CATALOGUE_URLS[provider]
        or digest(source["raw"].encode()) != source["sha256"]
    ):
        raise ValueError("native catalogue integrity mismatch")
    return catalogue_rows(source["raw"].encode(), provider)


def combinations(coins: list[str], cash: str, products: list[dict]) -> list[dict]:
    """One unordered pair per asset combination; use the venue's real orientation."""
    assets = list(dict.fromkeys([*coins, cash]))
    lookup = {(p["base"], p["quote"]): p for p in products}
    result = []
    for a, b in itertools.combinations(assets, 2):
        base, quote = (b, a) if a == cash else (a, b)
        options = [lookup[k] for k in ((base, quote), (quote, base)) if k in lookup]
        native = next(
            (p for p in options if p["active"]), options[0] if options else None
        )
        result.append(
            {
                "requested_pair": f"{base}/{quote}",
                "base": native["base"] if native else base,
                "quote": native["quote"] if native else quote,
                "product": native["product"] if native else None,
                "status": "planned"
                if native and native["active"]
                else "inactive"
                if native
                else "not_listed",
                "venue_status": native["venue_status"]
                if native
                else "absent from frozen venue catalogue",
            }
        )
    return result


def shared_path(output: Path, market: dict) -> Path:
    return output / "shared-inputs" / f"{market['base']}-{market['quote']}.json.zlib"


def ledger(output: Path) -> dict:
    paths = [
        output / "batch-plan.json.zlib",
        output / "market-catalogue.json.zlib",
        *sorted((output / "shared-inputs").glob("*.json.zlib")),
    ]
    return {str(p.relative_to(output)): digest(p.read_bytes()) for p in paths}


def frozen_ledger(output: Path) -> dict:
    value = ledger(output)
    path = output / "input-binding.json"
    if path.exists() and load(path) != value:
        raise ValueError("frozen batch inputs changed")
    if not path.exists():
        save(path, value)
    return value


def batch_report(summary: dict) -> str:
    p = summary["plan"]
    lines = [
        "# Native market combination backtests",
        "",
        "Report version: 2.0.0",
        "",
        "## Exactly what was requested",
        "",
        f"Coins: **{', '.join(p['coins'])}**. Added cash quote: **{p['quote']}**. Venue: **{p['venue']}**.",
        f"Requested acquisition: **{iso(p['start'])} to {iso(p['end_exclusive'])}**, exclusive. Each available native market downloads real one-minute candles once. No cross-pair OHLC is synthesized.",
        f"The frozen universe contains **{len(p['markets'])} unordered combinations**. Opposite pair order is not a second test: if the exchange lists BTC/ETH instead of ETH/BTC, that native orientation and its quote currency are reported below. Self-pairs are excluded. Delisted and absent products remain visible.",
        "The catalogue is a current listing snapshot, not a reconstruction of historical listings. An unavailable current product is not proof that it never traded during the requested week.",
        f"Backtest history policy: **{p['gap_policy']}**, with at least **1,440 consecutive real minutes**. Reduced windows are labelled per market. Missing minutes are never interpolated.",
        f"{summary['completed_markets']} native markets backtested; {summary['unavailable_markets']} unavailable or insufficient; {summary['failed_markets']} failed. Status: **{summary['status']}**.",
        "",
    ]
    if p["candidate_limit"]:
        lines += [
            f"**INCOMPLETE SMOKE TEST:** first {p['candidate_limit']} templates only; this is not a complete catalogue run.",
            "",
        ]
    lines += [
        "## Market-by-market coverage",
        "",
        "| Requested combination | Actual native market/product | Account currency | Status/reason | Actual backtest input UTC (end exclusive) | Real minutes | Report |",
        "|---|---|---|---|---|---:|---|",
    ]
    for row in summary["markets"]:
        window = row.get("analysis_window")
        actual = (
            f"{row['base']}/{row['quote']} (`{row['product']}`)"
            if row["product"]
            else "No native listing"
        )
        dates = (
            f"{iso(window['analysis_start'])} to {iso(window['analysis_end_exclusive'])}"
            if window
            else "—"
        )
        reason = row.get("reason", row["venue_status"])
        if window and not window["complete_requested_window"]:
            reason += "; **REDUCED WINDOW**"
        link = (
            f"[Detailed market report]({row['directory']}/report.md)"
            if row["status"] == "completed"
            else "—"
        )
        lines.append(
            f"| {row['requested_pair']} | {actual} | {row['quote']} | {row['status']}: {reason} | {dates} | {window['analyzed_minutes'] if window else '—'} | {link} |"
        )
    lines += [
        "",
        "## Tests inside each market report",
        "",
        "Each completed native market runs the ZEC candle-supported spot catalogue in six filter/control variants at 1m, 5m, 10m and 1h, four fee scenarios plus 2 bps execution allowance, cash/passive controls, synthetic Volty and canonical grid/DCA reference simulations, cycle diagnostics and reversal studies. The detailed reports spell out every selected strategy's member parameters, internal gates, fallback, persistence, weighting and additional shape/harmonic/linear filter.",
        "Training/validation/final test are chronological 60/20/20. Validation alone selects policies with at least ten validation exits. Test results never rerank candidates. Short-window strategy profits remain exploratory and have no multiple-search profitability qualification.",
        "Return-correlation diagnostics compare future returns of the actual target market with past-only features and reference markets sharing its quote. They are separate from native pair trading tests. Same-minute co-movement is descriptive, not a leading signal.",
        f"Every future-return correlation uses the within-market max-statistic correction, then a conservative Bonferroni multiplier of **{len(p['markets'])} planned combinations**, including unavailable ones. Cycle Holm corrections are within-market only; no batch-wide cycle significance claim is made.",
        "Quote units differ across native pairs: ETH/BTC returns and fees are in BTC, while ETH/USD uses USD. Reference accounts begin with 10,000 of their own quote units without a capacity model. Their P&L cannot be added or compared as a common dollar account without a separate conversion/execution model.",
        "",
        "## Correlation findings by target market",
        "",
        "| Actual target | Computed / insufficient / constant final-test feature tests | Batch-family corrected final-test associations (p ≤ 0.05) |",
        "|---|---:|---:|",
    ]
    for row in summary["markets"]:
        if row["status"] == "completed":
            lines.append(
                f"| {row['base']}/{row['quote']} | {row['test_correlation_coverage']['computed']} / {row['test_correlation_coverage']['insufficient']} / {row['test_correlation_coverage']['constant']} | {row['corrected_test_findings']} |"
            )
    lines += [
        "",
        "## Integrity and continuation",
        "",
        "batch-plan.json.zlib freezes the combination census, analytical options, source identity and current catalogue. market-catalogue.json.zlib preserves the exact catalogue response. shared-inputs retain exact candle pages; each market receives byte-identical input copies. input-binding.json freezes acquisition before analysis. batch-manifest.json binds parent and child artifacts; offline verification rechecks every child report, source normalization, count and market identity.",
        "Use --resume with this output to continue its frozen plan. Use --phase verify to verify offline. Finished studies are immutable; choose a new output to change coins or options. An acquisition or analysis failure leaves a partial report and a nonzero exit status; it is not relabelled as an absent market.",
        "",
    ]
    return "\n".join(lines)


def test_coverage(correlations: dict) -> dict:
    return {
        k: sum(row[k] for row in correlations["coverage"] if row["split"] == "test")
        for k in ("computed", "insufficient", "constant")
    }


def summary_payload(plan: dict, rows: list[dict], *, failed: bool = False) -> dict:
    completed = sum(r["status"] == "completed" for r in rows)
    unavailable = sum(
        r["status"] in ("inactive", "not_listed", "insufficient_history") for r in rows
    )
    return {
        "version": "2.0.0",
        "plan": {k: v for k, v in plan.items() if k not in ("catalogue", "identity")},
        "markets": rows,
        "completed_markets": completed,
        "unavailable_markets": unavailable,
        "failed_markets": sum(r["status"] == "failed" for r in rows),
        "status": "partial"
        if failed or completed + unavailable != len(rows)
        else "completed"
        if completed
        else "no_backtests",
    }


def write_summary(
    output: Path, plan: dict, rows: list[dict], *, failed: bool = False
) -> dict:
    summary = summary_payload(plan, rows, failed=failed)
    save(output / "batch-summary.json", summary)
    (output / "report.md").write_text(batch_report(summary))
    return summary


def study_market(
    output: Path, plan: dict, row: dict, available: list[dict], workers: int
) -> dict:
    from research.coin_week import analyze, make_plan, verify_run

    directory = f"markets/{row['base']}-{row['quote']}"
    child = output / directory
    child.mkdir(parents=True, exist_ok=True)
    # A user can invoke the single-market CLI on this same directory. The
    # parent lock does not exclude that writer; the child lock does.
    with (child / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        references = [
            r
            for r in available
            if r["quote"] == row["quote"] and r["base"] != row["base"]
        ]
        child_path = child / "run-plan.json.zlib"
        expected = make_plan(
            coin=row["base"],
            provider=plan["provider"],
            quote=row["quote"],
            references=[r["base"] for r in references],
            start=plan["start"],
            stop=plan["end_exclusive"],
            days=plan["days"],
            replicates=plan["replicates"],
            candidate_limit=plan["candidate_limit"],
            workers=workers,
            gap_policy=plan["gap_policy"],
            family_multiplier=len(plan["markets"]),
            catalogue=plan["catalogue"],
        )
        if child_path.exists():
            child_plan = load(child_path)
            if {
                k: v
                for k, v in child_plan.items()
                if k not in ("source_commit", "workers")
            } != {
                k: v
                for k, v in expected.items()
                if k not in ("source_commit", "workers")
            }:
                raise ValueError("child plan differs from frozen batch protocol")
        else:
            child_plan = expected
            save(child_path, child_plan)
            save(child / "coverage.json", child_plan["coverage"])
        (child / "inputs").mkdir(exist_ok=True)
        for source in [row, *references]:
            dest = child / "inputs" / f"{source['base']}.json.zlib"
            if dest.exists() and digest(dest.read_bytes()) != digest(
                shared_path(output, source).read_bytes()
            ):
                raise ValueError("child input differs from frozen batch snapshot")
            if not dest.exists():
                shutil.copyfile(shared_path(output, source), dest)
        if not (child / "manifest.json").exists():
            analyze(child_plan, child, workers)
        verify_run(child)
        return {"directory": directory, "summary": load(child / "summary.json")}


def verify_batch(output: Path) -> dict:
    from research.coin_week import verify_run

    manifest = load(output / "batch-manifest.json")
    for name, sha in manifest["artifacts"].items():
        if digest((output / name).read_bytes()) != sha:
            raise ValueError(f"batch artifact integrity mismatch: {name}")
    plan = load(output / "batch-plan.json.zlib")
    products = verify_catalogue(
        load(output / "market-catalogue.json.zlib"), plan["provider"]
    )
    if combinations(plan["coins"], plan["quote"], products) != plan["markets"]:
        raise ValueError("native combination census mismatch")
    if not (output / "input-binding.json").exists():
        raise ValueError("batch is missing its frozen input ledger")
    frozen_ledger(output)
    summary = load(output / "batch-summary.json")
    if summary_payload(plan, summary["markets"]) != summary or len(
        summary["markets"]
    ) != len(plan["markets"]):
        raise ValueError("batch summary counts or frozen plan mismatch")
    if (output / "report.md").read_text() != batch_report(summary):
        raise ValueError("batch report no longer reproduces")
    for row, frozen in zip(summary["markets"], plan["markets"]):
        if any(row[k] != v for k, v in frozen.items() if k != "status"):
            raise ValueError("batch summary market census mismatch")
        if frozen["status"] != "planned":
            if row["status"] != frozen["status"]:
                raise ValueError("unavailable market status mismatch")
        elif row["status"] not in ("completed", "insufficient_history"):
            raise ValueError("unfinished market in finalized batch")
        if row["status"] not in ("completed", "insufficient_history"):
            continue
        source = load(shared_path(output, row))
        verify_snapshot(
            source, row["base"], plan["start"], plan["end_exclusive"], row["quote"]
        )
        if (
            source["provider"] != plan["provider"]
            or source["product"] != row["product"]
        ):
            raise ValueError("batch native product mismatch")
        try:
            _, window = analysis_window(
                frame_from(source),
                plan["start"],
                plan["end_exclusive"],
                plan["gap_policy"],
            )
        except ValueError:
            if row["status"] != "insufficient_history":
                raise
            continue
        if window != row["analysis_window"] or (
            (window["analyzed_minutes"] >= 1440) != (row["status"] == "completed")
        ):
            raise ValueError("batch analyzed window/status mismatch")
        if row["status"] == "completed":
            child = output / row["directory"]
            verify_run(child)
            child_plan, child_summary = (
                load(child / "run-plan.json.zlib"),
                load(child / "summary.json"),
            )
            if (
                child_plan["coin"],
                child_plan["quote"],
                child_plan["provider"],
                child_plan["start"],
                child_plan["end_exclusive"],
                child_plan["correlation_family_multiplier"],
            ) != (
                row["base"],
                row["quote"],
                plan["provider"],
                plan["start"],
                plan["end_exclusive"],
                len(plan["markets"]),
            ):
                raise ValueError("child market or family mismatch")
            if (
                row["corrected_test_findings"]
                != child_summary["correlations"]["corrected_test_findings"]
                or row["strategy_rows"] != child_summary["strategy_rows"]
                or row["test_correlation_coverage"]
                != test_coverage(child_summary["correlations"])
            ):
                raise ValueError("parent findings/counts differ from child results")
            if (
                digest((child / "inputs" / f"{row['base']}.json.zlib").read_bytes())
                != digest(shared_path(output, row).read_bytes())
                or child_summary["analysis_window"] != row["analysis_window"]
            ):
                raise ValueError("child source/window mismatch")
    return {
        "status": "verified",
        "completed_markets": summary["completed_markets"],
        "planned_combinations": len(plan["markets"]),
        "artifacts": len(manifest["artifacts"]),
    }


def run_batch(args, output: Path) -> int:
    from research.coin_week import (
        ROOT,
        VERSION,
        expanded,
        identity,
    )

    if args.phase == "verify":
        print(json.dumps(verify_batch(output), indent=2))
        return 0
    if getattr(args, "references", None) is not None:
        raise ValueError(
            "--references is single-coin only; batch comparisons use available native markets from --coins"
        )
    if not 1 <= args.workers <= 16 or args.replicates < 199 or args.candidate_limit < 0:
        raise ValueError(
            "workers must be 1..16, null replicates >=199, candidate limit >=0"
        )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "batch-manifest.json").exists():
            if not args.resume:
                raise ValueError(
                    "finished batch is immutable; use --resume to verify it"
                )
            print(json.dumps(verify_batch(output), indent=2))
            return 0
        path = output / "batch-plan.json.zlib"
        if path.exists():
            if not args.resume and args.phase != "analyze":
                raise ValueError("unfinished batch exists; use --resume")
            plan = load(path)
            if args.coins and coin_list(args.coins) != plan["coins"]:
                raise ValueError("resume coins do not match frozen batch")
            if args.quote and coin_symbol(args.quote) != plan["quote"]:
                raise ValueError("resume quote does not match frozen batch")
            if identity() != plan["identity"]:
                raise ValueError("batch source/runtime changed; use a new output")
        else:
            if args.phase == "analyze":
                raise ValueError("offline analysis needs an acquired batch plan")
            if (output / "run-plan.json.zlib").exists():
                raise ValueError("single-coin study already owns this output")
            coins = coin_list(args.coins)
            provider = args.venue or (
                "binance" if (args.quote or "").upper() == "USDT" else "coinbase"
            )
            cash = coin_symbol(args.quote or PROVIDERS[provider]["quote"])
            start, stop = week_bounds(args.end, args.days)
            products = verify_catalogue(
                acquire_catalogue(provider, output / "market-catalogue.json.zlib"),
                provider,
            )
            markets = combinations(coins, cash, products)
            if not markets:
                raise ValueError(
                    "the list needs at least one asset different from the quote"
                )
            plan = {
                "version": VERSION,
                "coins": coins,
                "provider": provider,
                "venue": PROVIDERS[provider]["venue"],
                "quote": cash,
                "start": start,
                "end_exclusive": stop,
                "days": args.days,
                "replicates": args.replicates,
                "candidate_limit": args.candidate_limit,
                "gap_policy": args.gap_policy or "longest",
                "markets": markets,
                "identity": identity(),
                "catalogue": expanded.catalogue(ROOT),
            }
            save(path, plan)
        rows = [dict(m) for m in plan["markets"]]
        failed = False
        for row in rows:
            if row["status"] != "planned":
                continue
            print(
                f"Acquire native {row['base']}/{row['quote']} ({row['product']})",
                flush=True,
            )
            try:
                if args.phase == "analyze" and not shared_path(output, row).exists():
                    raise ValueError(
                        "offline analysis is missing an acquired native market"
                    )
                download(
                    row["base"],
                    plan["start"],
                    plan["end_exclusive"],
                    shared_path(output, row),
                    provider=plan["provider"],
                    quote=row["quote"],
                )
            except (OSError, ValueError) as exc:
                row.update(
                    status="failed", reason=f"acquisition {type(exc).__name__}: {exc}"
                )
                failed = True
        write_summary(output, plan, rows, failed=True)
        if failed:
            print(f"Partial acquisition preserved: {output / 'report.md'}", flush=True)
            return 1
        if args.phase == "fetch":
            print(
                f"Acquired batch; run --phase analyze with --output {output}",
                flush=True,
            )
            return 0
        frozen_ledger(output)
        available = [r for r in rows if r["status"] == "planned"]
        for row in available:
            try:
                _, window = analysis_window(
                    frame_from(load(shared_path(output, row))),
                    plan["start"],
                    plan["end_exclusive"],
                    plan["gap_policy"],
                )
            except ValueError as exc:
                row.update(status="insufficient_history", reason=str(exc))
                continue
            row["analysis_window"] = window
            if window["analyzed_minutes"] < 1440:
                row.update(
                    status="insufficient_history",
                    reason="fewer than 1440 consecutive real minutes; no candles filled",
                )
                continue
            try:
                result = study_market(output, plan, row, available, args.workers)
                child_summary = result["summary"]
                row.update(
                    status="completed",
                    directory=result["directory"],
                    reason="native candles, full transferred analysis",
                    corrected_test_findings=child_summary["correlations"][
                        "corrected_test_findings"
                    ],
                    strategy_rows=child_summary["strategy_rows"],
                    test_correlation_coverage=test_coverage(
                        child_summary["correlations"]
                    ),
                )
            except (OSError, ValueError, RuntimeError) as exc:
                row.update(
                    status="failed", reason=f"analysis {type(exc).__name__}: {exc}"
                )
                failed = True
            write_summary(output, plan, rows, failed=True)
        summary = write_summary(output, plan, rows, failed=failed)
        frozen_ledger(output)
        if failed:
            return 1
        if identity() != plan["identity"]:
            raise ValueError("batch source/runtime changed during analysis")
        artifacts = {
            str(p.relative_to(output)): digest(p.read_bytes())
            for p in sorted(output.rglob("*"))
            if p.is_file()
            and p.name not in ("batch-manifest.json", "run.lock")
            and not p.name.endswith((".log", ".tmp", ".partial"))
        }
        save(
            output / "batch-manifest.json", {"version": VERSION, "artifacts": artifacts}
        )
        print(json.dumps(verify_batch(output), indent=2))
        print(str(output / "report.md"), flush=True)
        return 0 if summary["completed_markets"] else 1
