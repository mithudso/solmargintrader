"""Causal, exploratory multi-timeframe UU reversal study; no execution."""

from __future__ import annotations

import argparse
import bisect
from collections import Counter
from pathlib import Path

from research.reversal_history import canonical, pack, read_archive
from research.reversal_second_turn import aggregate, crosses
from research.reversal_shapes import INTERVALS, boundaries, color, shape_labels, wilson

THRESHOLDS = (0.5, 0.525, 0.55, 0.6)
BARRIERS = (5, 7.5, 9.8, 10)


def frame_index(rows):
    out = {}
    for minutes in INTERVALS:
        bars = aggregate(rows, minutes, require_volume=False)
        out[str(minutes)] = (
            bars,
            shape_labels(bars, minutes),
            [b[0] + minutes * 60 for b in bars],
        )
    return out


def context_at(index, at):
    frames = {}
    for key, (bars, labels, ends) in index.items():
        i = bisect.bisect_right(ends, at) - 1
        pair = None
        if i >= 1 and bars[i][0] - bars[i - 1][0] == int(key) * 60:
            pair = "".join(
                {"UP": "U", "DOWN": "D", "FLAT": "F"}[color(bars[j])]
                for j in (i - 1, i)
            )
        stale = i < 0 or at >= ends[i] + int(key) * 60
        frames[key] = {
            "shape": labels[i] if not stale else "unknown",
            "pair": pair if not stale else None,
            "closed_at": ends[i] if i >= 0 else None,
        }
    return {"at": at, "frames": frames}


def live_context(rows, at):
    return context_at(frame_index(rows), at)


def score_context(model, base_minutes, context):
    base = model["base_models"][str(base_minutes)]
    result = {
        "status": "insufficient",
        "score_down": None,
        "components": [],
        "base_down_rate": None,
    }
    if base["n"] < 40 or any(
        context["frames"][str(m)]["shape"] == "unknown" for m in INTERVALS
    ):
        return result
    p = base["down"] / base["n"]
    result["base_down_rate"] = p
    for m in INTERVALS:
        shape = context["frames"][str(m)]["shape"]
        cell = base["contexts"][str(m)].get(shape, {"n": 0, "down": 0})
        n, down = cell["n"], cell["down"]
        if n >= model["min_cell_n"]:
            a = model["alpha"]
            result["components"].append(
                {
                    "minutes": m,
                    "shape": shape,
                    "n": n,
                    "down": down,
                    "posterior_down": (down + a * p) / (n + a),
                    "weight": n / (n + a),
                    "wilson": wilson(down, n),
                }
            )
    if len(result["components"]) >= model["min_components"]:
        components = result["components"]
        result.update(
            status="ready",
            score_down=(p + sum(c["weight"] * c["posterior_down"] for c in components))
            / (1 + sum(c["weight"] for c in components)),
        )
    return result


def classify(score_down, threshold):
    if score_down is None:
        return None
    if score_down > 0.5 and score_down >= threshold:
        return "DOWN"
    if score_down < 0.5 and score_down <= 1 - threshold:
        return "UP"
    return None


def make_events(index):
    cuts = boundaries()
    result = []
    for m in INTERVALS:
        bars, _, _ = index[str(m)]
        for i in range(1, len(bars) - 1):
            if (
                bars[i][0] - bars[i - 1][0] != m * 60
                or bars[i + 1][0] - bars[i][0] != m * 60
                or any(color(bars[j]) != "UP" for j in (i - 1, i))
            ):
                continue
            start, end = bars[i + 1][0], bars[i + 1][0] + m * 60
            split = next(
                (
                    name
                    for name, left, right in zip(
                        ("train", "validation", "test"), cuts, cuts[1:]
                    )
                    if left <= start and end <= right
                ),
                None,
            )
            if split is None:
                continue
            context = context_at(index, start)
            if any(f["shape"] == "unknown" for f in context["frames"].values()):
                continue
            result.append(
                {
                    "minutes": m,
                    "split": split,
                    "signal_at": start,
                    "target_end": end,
                    "context": context,
                    "target": bars[i + 1],
                    "target_color": color(bars[i + 1]),
                }
            )
    return result


def fit(events, asset):
    models = {}
    for m in INTERVALS:
        es = [e for e in events if e["minutes"] == m and e["split"] == "train"]
        contexts = {}
        for frame in INTERVALS:
            counts = {}
            for e in es:
                shape = e["context"]["frames"][str(frame)]["shape"]
                cell = counts.setdefault(shape, {"n": 0, "down": 0})
                cell["n"] += 1
                cell["down"] += e["target_color"] == "DOWN"
            contexts[str(frame)] = counts
        models[str(m)] = {
            "n": len(es),
            "down": sum(e["target_color"] == "DOWN" for e in es),
            "contexts": contexts,
        }
    return {
        "schema": "mtf-reversal-model/v1",
        "asset": asset,
        "trained_through": boundaries()[1],
        "alpha": 20,
        "min_cell_n": 20,
        "min_components": 2,
        "base_models": models,
        "selected": None,
    }


def metrics(events, decisions, scores=None):
    taken = [(e, d) for e, d in zip(events, decisions) if d]
    hits = sum(e["target_color"] == d for e, d in taken)
    joint = {
        str(b): sum(
            e["target_color"] == d and not crosses(e["target"], d, b) for e, d in taken
        )
        for b in BARRIERS
    }
    n = len(taken)
    return {
        "eligible": len(events),
        "n": n,
        "coverage": n / len(events) if events else None,
        "directions": dict(Counter(d for _, d in taken)),
        "hits": hits,
        "direction_rate": hits / n if n else None,
        "direction_wilson": wilson(hits, n),
        "joint_by_bps": joint,
        "joint_rate_9.8": joint["9.8"] / n if n else None,
        "joint_wilson_9.8": wilson(joint["9.8"], n),
        "crossed_by_bps": {
            str(b): sum(crosses(e["target"], d, b) for e, d in taken) for b in BARRIERS
        },
        "brier_descriptive": sum(
            (s - (e["target_color"] == "DOWN")) ** 2
            for e, s in zip(events, scores)
            if s is not None
        )
        / sum(s is not None for s in scores)
        if scores and any(s is not None for s in scores)
        else None,
    }


def hypothesis(context):
    f = context["frames"]
    down = f["20"]["shape"] in ("bowl", "trend_down")
    up = f["15"]["shape"] == "cap" or f["5"]["shape"] == "cap"
    return "DOWN" if down and not up else "UP" if up and not down else None


def select(variants):
    eligible = [
        v
        for v in variants
        if v["mode"] == "all"
        and v["splits"]["train"]["strategy"]["n"] >= 40
        and v["splits"]["validation"]["strategy"]["n"] >= 20
    ]
    if not eligible:
        return None
    winner = min(
        eligible,
        key=lambda v: (
            -v["splits"]["validation"]["strategy"]["joint_wilson_9.8"][0],
            -v["splits"]["validation"]["strategy"]["n"],
            v["id"],
        ),
    )
    return {k: winner[k] for k in ("minutes", "threshold", "id")}


def analyze(rows, asset):
    events = make_events(frame_index(rows))
    model = fit(events, asset)
    variants = []
    for mode in ("all", "current"):
        for m in INTERVALS:
            es = [e for e in events if e["minutes"] == m]
            records = []
            for e in es:
                scored = score_context(model, m, e["context"])
                if mode == "current":
                    scored = score_context(
                        {**model, "min_components": 1}, m, e["context"]
                    )
                    components = [c for c in scored["components"] if c["minutes"] == m]
                    if components:
                        c = components[0]
                        p = scored["base_down_rate"]
                        scored.update(
                            status="ready",
                            score_down=(p + c["weight"] * c["posterior_down"])
                            / (1 + c["weight"]),
                            components=components,
                        )
                    else:
                        scored.update(
                            status="insufficient", score_down=None, components=[]
                        )
                records.append(scored)
            for threshold in THRESHOLDS:
                ident = f"{mode}:{m}:{threshold:g}"
                splits = {}
                for split in ("train", "validation", "test"):
                    subset = [
                        (e, r) for e, r in zip(es, records) if e["split"] == split
                    ]
                    se, sr = (
                        [x[0] for x in subset],
                        [x[1]["score_down"] for x in subset],
                    )
                    ds = [classify(s, threshold) for s in sr]
                    splits[split] = {
                        "strategy": metrics(se, ds, sr),
                        "all_uu_down": metrics(se, ["DOWN"] * len(se)),
                        "same_taken_down": metrics(
                            se, ["DOWN" if d else None for d in ds]
                        ),
                        "literal_hypothesis": metrics(
                            se, [hypothesis(e["context"]) for e in se]
                        ),
                    }
                variants.append(
                    {
                        "id": ident,
                        "mode": mode,
                        "minutes": m,
                        "threshold": threshold,
                        "splits": splits,
                    }
                )
            for e, r in zip(es, records):
                e.setdefault("scores", {})[mode] = r
    model["selected"] = select(variants)
    return {
        "schema": "mtf-reversal-results/v1",
        "asset": asset,
        "qualification": "exploratory retrospective; histories seen before hypothesis; oracle price basis, full-bar OHLC proxy, unqualified historical fees/fills/keeper path; not calibrated probability",
        "model": model,
        "variants": variants,
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = read_archive(args.oracle)
    result = analyze(source["rows"], source["coin"])
    Path(args.output).write_text(canonical(pack(result)))


if __name__ == "__main__":
    main()
