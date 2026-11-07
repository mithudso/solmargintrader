"""Tune the frontier's promising rows without peeking at the out-of-sample window.

    /Users/mitch/.venvs/soltui/bin/python research/frontier_tune.py --run-id <frontier sweep run id>

Input: one `python -m soltui.compound sweep --frontier` run in the compound results file (every metric alone,
its strongest 2% of readings, held 1 h / 4 h / 24 h, unlevered, on every coin).

1. **Pick on in-sample only.** A (metric, hold) is a candidate when its in-sample Sharpe is positive on at least
   `--min-coins` coins; candidates are ranked by their median in-sample Sharpe across coins. The out-of-sample
   columns are not read until step 4.
2. **Tune on in-sample only.** For the top `--top` candidates, a grid over hold, entry quantile and the metric's
   first parameter (x0.5, x1, x2). The grid point with the best median in-sample Sharpe across coins wins.
3. **Related strategies.** The winner's settings are applied to the other metrics in its family and style, and
   to a small compound of the top candidates voting together: the "related and maybe better" question.
4. **Report out-of-sample once** for every chosen configuration, per coin, beside buying and holding the coin.
   Every configuration tried is counted: that count is the multiple-testing denominator.

Writes research/results/frontier-<date>.json. Simulation only; nothing here touches a venue.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core import compound as cbt  # noqa: E402
from backtester.core import scorecard as sc  # noqa: E402

HOLDS = (24, 48, 96, 144, 288, 576)
QUANTILES = (0.9, 0.95, 0.98, 0.995)
FACTORS = (0.5, 1.0, 2.0)


def results_file() -> Path:
    base = Path(os.environ.get("SOLTUI_CONFIG_DIR") or Path.home() / ".config" / "soltui")
    return base / "compound" / "backtests.jsonl"


def load_run(run_id: str) -> list[dict[str, Any]]:
    rows = []
    with results_file().open(encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("run_id") == run_id and "error" not in r and str(r.get("label", "")).startswith("frontier:"):
                rows.append(r)
    return rows


def is_sharpe(r: dict[str, Any]) -> float | None:
    return ((r.get("is") or {}).get("pnl") or {}).get("sharpe")


def oos(r: dict[str, Any]) -> dict[str, Any]:
    o = r.get("oos") or {}
    p = o.get("pnl") or {}
    return {"return": p.get("total_return"), "sharpe": p.get("sharpe"), "trades": p.get("trades"),
            "max_dd": p.get("max_drawdown"), "buy_hold": o.get("buy_hold_return"), "ranked": r.get("ranked")}


def candidates(rows: list[dict[str, Any]], min_coins: int) -> list[dict[str, Any]]:
    by: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for r in rows:
        parts = r["label"][9:].split()
        by.setdefault((parts[0], int(parts[1][5:])), []).append(r)
    out = []
    for (cid, hold), rs in by.items():
        s = [x for x in (is_sharpe(r) for r in rs) if x is not None]
        if len(s) < min_coins:
            continue
        positive = sum(1 for x in s if x > 0)
        if positive >= min_coins:
            out.append({"metric": cid, "hold": hold, "is_median_sharpe": round(statistics.median(s), 3),
                        "is_positive_coins": positive, "coins": len(s)})
    out.sort(key=lambda c: -c["is_median_sharpe"])
    # One entry per metric (its best in-sample hold): the tuning grid already varies the hold, and a
    # metric listed twice would run its grid twice and count every coin double.
    seen: set[str] = set()
    return [c for c in out if not (c["metric"] in seen or seen.add(c["metric"]))]


def config_for(metric: str, hold: int, quantile: float, factor: float = 1.0,
               metrics: tuple[str, ...] | None = None) -> dict[str, Any]:
    base = sc.default_config()
    ids = metrics or (metric,)
    if len(ids) == 1:
        cfg = sc.standalone_config(base, ids[0])
    else:
        cfg = sc.standalone_config(base, ids[0])
        for cid in ids[1:]:
            cfg["components"][cid]["enabled"] = True
            cfg["components"][cid]["weight"] = 1.0
    cfg["aggregate"].update(hold=hold, entry_quantile=quantile)
    cfg["execution"]["leverage"] = 1.0
    if factor != 1.0:
        spec = sc.BY_ID[metric].params[0]
        v = cfg["components"][metric]["params"][spec.name] * factor
        v = int(round(v)) if spec.kind == "int" else round(v, 6)
        cfg["components"][metric]["params"][spec.name] = min(max(v, spec.lo), spec.hi)
    return sc.normalise_config(cfg)


def _run_coin(job: tuple[str, list[tuple[str, dict[str, Any]]]]) -> list[dict[str, Any]]:
    asset, configs = job
    prep = cbt.prepare(asset)
    out = []
    for label, cfg in configs:
        try:
            r = cbt.run_compound(asset, cfg, label=label, prepared=prep)
            out.append({"asset": asset, "label": label, "is_sharpe": is_sharpe(r), "oos": oos(r)})
        except (cbt.CompoundDataError, sc.ScorecardError) as exc:
            out.append({"asset": asset, "label": label, "error": str(exc)})
    return out


def run_all(coins: list[str], configs: list[tuple[str, dict[str, Any]]], workers: int) -> list[dict[str, Any]]:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return [row for rows in pool.map(_run_coin, [(c, configs) for c in coins]) for row in rows]


def summarise(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    rs = [r for r in rows if r["label"] == label and "error" not in r]
    is_s = [r["is_sharpe"] for r in rs if r["is_sharpe"] is not None]
    oos_s = [r["oos"]["sharpe"] for r in rs if r["oos"]["sharpe"] is not None]
    beat = sum(1 for r in rs if r["oos"]["return"] is not None and r["oos"]["buy_hold"] is not None
               and r["oos"]["return"] > r["oos"]["buy_hold"])
    pos = sum(1 for r in rs if (r["oos"]["return"] or 0) > 0)
    return {"label": label, "coins": len(rs),
            "is_median_sharpe": None if not is_s else round(statistics.median(is_s), 3),
            "oos_median_sharpe": None if not oos_s else round(statistics.median(oos_s), 3),
            "oos_positive_coins": pos, "oos_beat_buy_hold_coins": beat,
            "per_coin": {r["asset"]: r["oos"] for r in rs}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-coins", type=int, default=6)
    ap.add_argument("--workers", type=int, default=max(1, min(10, (os.cpu_count() or 2) - 2)))
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    rows = load_run(args.run_id)
    if not rows:
        print(f"no frontier rows for run {args.run_id} in {results_file()}", file=sys.stderr)
        return 2
    coins = sorted({r["asset"] for r in rows})
    cands = candidates(rows, args.min_coins)
    print(f"{len(rows)} frontier rows on {len(coins)} coins; {len(cands)} candidates by in-sample Sharpe")
    top = cands[:args.top]
    tried = len(rows)

    # 2. tune on in-sample
    grid: list[tuple[str, dict[str, Any]]] = []
    for c in top:
        for hold in HOLDS:
            for q in QUANTILES:
                for f in FACTORS:
                    grid.append((f"tune:{c['metric']} hold={hold} q={q} x{f}", config_for(c["metric"], hold, q, f)))
    t0 = time.time()
    grid_rows = run_all(coins, grid, args.workers)
    tried += len(grid)
    print(f"tuning grid: {len(grid)} configurations x {len(coins)} coins in {time.time() - t0:.0f} s")
    chosen = []
    for c in top:
        labels = [label for label, _ in grid if label.startswith(f"tune:{c['metric']} ")]
        best = max(labels, key=lambda lb: summarise(grid_rows, lb)["is_median_sharpe"] or -1e9)
        parts = best.split()
        chosen.append({**c, "tuned_label": best, "hold_tuned": int(parts[1][5:]), "q_tuned": float(parts[2][2:]),
                       "factor": float(parts[3][1:])})

    # 3. related metrics and a mini-compound, at each winner's tuned hold and quantile
    related: list[tuple[str, dict[str, Any]]] = []
    for c in chosen:
        comp = sc.BY_ID[c["metric"]]
        usable = [x for x in sc.COMPONENTS if x.kind == "score" and not x.forward_only and x.id != comp.id]
        sibs = [x for x in usable if x.family == comp.family or x.style == comp.style]
        if not sibs:  # a family of one (htf_trend is "context"): compare with the directional followers
            sibs = [x for x in usable if x.style in ("trend", "momentum", "breakout")]
        for sib in sibs:
            related.append((f"related:{sib.id} like {c['metric']} hold={c['hold_tuned']} q={c['q_tuned']}",
                            config_for(sib.id, c["hold_tuned"], c["q_tuned"])))
        # The winner's own neighbours: every parameter halved and doubled, at the tuned hold and quantile.
        for spec in comp.params:
            for f in (0.5, 2.0):
                cfg = config_for(c["metric"], c["hold_tuned"], c["q_tuned"])
                v = cfg["components"][comp.id]["params"][spec.name] * f
                v = int(round(v)) if spec.kind == "int" else round(v, 6)
                if comp.id == "htf_trend" and spec.name == "tf_minutes":
                    v = max(10, int(round(v / 5)) * 5)  # must stay a multiple of 5 above 5
                cfg["components"][comp.id]["params"][spec.name] = min(max(v, spec.lo), spec.hi)
                try:
                    cfg = sc.normalise_config(cfg)
                except sc.ScorecardError:
                    continue
                related.append((f"variant:{comp.id} {spec.name}={v:g} hold={c['hold_tuned']} q={c['q_tuned']}", cfg))
    if len(chosen) >= 2:
        ids = tuple(dict.fromkeys(c["metric"] for c in chosen))
        hold = int(statistics.median(c["hold_tuned"] for c in chosen))
        related.append((f"blend:{'+'.join(ids)} hold={hold} q=0.98", config_for(ids[0], hold, 0.98, metrics=ids)))
    related = list({label: cfg for label, cfg in related}.items())
    rel_rows = run_all(coins, related, args.workers) if related else []
    tried += len(related)

    # 4. out-of-sample, once
    related_summary = sorted((summarise(rel_rows, label) for label, _ in related),
                             key=lambda s: -(s["is_median_sharpe"] or -1e9))
    chosen_summary = [{**c, "tuned": summarise(grid_rows, c["tuned_label"]),
                       "untuned": summarise(grid_rows, f"tune:{c['metric']} hold={c['hold']} q=0.98 x1.0")}
                      for c in chosen]
    report: dict[str, Any] = {
        "run_id": args.run_id, "coins": coins, "configurations_tried_per_coin": tried,
        "note": "Selection and tuning used in-sample Sharpe only; out-of-sample is reported, never used to choose.",
        "candidates": cands[:15],
        "chosen": chosen_summary,
        "related": related_summary,
        "grid_oos_stability": {c["metric"]: sorted(
            (summarise(grid_rows, label) for label, _ in grid if label.startswith(f"tune:{c['metric']} ")),
            key=lambda s: -(s["is_median_sharpe"] or -1e9))[:12] for c in chosen},
    }
    out = Path(args.out or REPO / "research" / "results" / f"frontier-{time.strftime('%Y-%m-%d')}.json")
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"wrote {out}")
    for c in chosen_summary:
        t = c["tuned"]
        print(f"{c['metric']}: in-sample pick hold={c['hold']} -> tuned {c['tuned_label']}; "
              f"OOS median Sharpe {t['oos_median_sharpe']}, positive on {t['oos_positive_coins']}/{t['coins']}, "
              f"beat buy-and-hold on {t['oos_beat_buy_hold_coins']}/{t['coins']}")
    for r in related_summary[:8]:
        print(f"  related {r['label']}: IS {r['is_median_sharpe']} OOS {r['oos_median_sharpe']} "
              f"pos {r['oos_positive_coins']}/{r['coins']} beat B&H {r['oos_beat_buy_hold_coins']}/{r['coins']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
