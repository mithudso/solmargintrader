"""The scalp read-out, market by market: is the call right more often on one coin?

Reads recorded Jupiter oracle ticks (the live recorder's JSONL, and optionally the
base capture), builds the same one-second bars and the same weighted call the
window makes, and scores each market apart. Nothing here trades or reads the
network.

Two cautions are written into the output. The starting rates (`prior_file`) and
the tile set were both chosen on the base capture, so scoring that capture with
them is in-sample (`in_sample_sources`). And with several markets one of them is
always highest: each market carries a p-value adjusted for how many were
compared.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np

from research import scalp_1s_experiments as X
from research import scalp_1s_features as F
from research import scalp_1s_study as S

HORIZON = S.HORIZON
SHIPPED = (
    Path(__file__).resolve().parents[1] / "json/scalp-1s-20261127/experiments.json"
)
BASE_SOURCE = "base"


def shipped_prior(path: Path = SHIPPED) -> dict:
    """The recorded hit rate of every setting at the call horizon, as the extension ships it."""
    model = json.loads(path.read_text(encoding="utf-8"))
    if model["call_horizon_s"] != HORIZON:
        raise ValueError(
            f"its rates are for {model['call_horizon_s']} seconds, not {HORIZON}"
        )
    at = model["horizons"].index(model["call_horizon_s"])
    rates = {}
    for variant in model["variants"]:
        if len(variant["prior"]) != len(model["horizons"]):
            raise ValueError(f"{variant['id']} has no rate for every horizon")
        rate = variant["prior"][at]
        rates[variant["id"]] = rate if rate is not None else 0.5
    return rates


def _tier(replayed: dict, name: str, key: str) -> dict:
    """One tier of one aggregate. A tier with too few calls to rate carries its count only."""
    row = replayed[name].get(key, {})
    if "hit" not in row:
        return {"n": row.get("n", 0)}
    out = {field: row[field] for field in ("hit", "hit_se", "n")}
    for field in ("share", "mean_follow_bps"):
        if field in row:
            out[field] = row[field]
    return out


def coin_row(groups, slot_ids, prior) -> dict:
    """One market: `groups` is a list of recordings of it, each a list of frames with
    every setting's vote attached (``X.variant_votes``)."""
    frames = [fr for group in groups for fr in group]
    replayed = X.replay(groups, slot_ids, prior, HORIZON)
    table = X.experiment_table(frames)
    moves = np.concatenate([np.abs(fr["fwd"][np.isfinite(fr["fwd"])]) for fr in frames])
    seconds = int(sum(fr["close"].size for fr in frames))
    breakout, calls = table["breakout_60"][HORIZON]
    return {
        "hours": seconds / 3600.0,
        "scored_seconds": replayed["seconds"],
        "median_move_bps": float(np.median(moves)) if moves.size else None,
        # A second whose price is unchanged 30 seconds later is not scored for anyone. A market
        # whose oracle moves rarely has more of them, so its hit rates rest on fewer seconds.
        "flat_share": float((moves == 0).mean()) if moves.size else None,
        # The call as the window makes it by default, then without switching, then unweighted.
        "strong": _tier(replayed, "best", "strong"),
        "strong_no_switching": _tier(replayed, "weighted", "strong"),
        "strong_one_vote_each": _tier(replayed, "plain", "strong"),
        "any_call": _tier(replayed, "best", "any"),
        "lean": _tier(replayed, "best", "lean"),
        # Every second the breakout spoke, from the first bar it could: not the tiers' warmed-up seconds.
        "breakout_60": {
            "hit": breakout,
            "n": calls,
            "hit_se": math.sqrt(0.25 / max(1.0, calls / HORIZON)) if calls else None,
        },
        "switches": replayed["changes"]["best"],
    }


def compare(rows: dict, key: str = "strong") -> dict:
    """Each market's hit rate against all the others pooled, in standard errors (`z`).

    One of several markets is always the highest. If they were all alike, the highest
    of five would reach z = 2 about one time in nine, and some market would be that far
    from the rest in either direction about one time in five. `p_adjusted` is the
    two-sided p-value multiplied by the number of markets compared (Bonferroni):
    read that, not `z` alone.
    """
    rated = {coin: row[key] for coin, row in rows.items() if "hit" in row[key]}
    out = {}
    for coin, mine in rated.items():
        rest = [row for other, row in rated.items() if other != coin]
        if not rest:
            continue
        n = sum(row["n"] for row in rest)
        pooled = sum(row["hit"] * row["n"] for row in rest) / n
        se = math.hypot(mine["hit_se"], math.sqrt(0.25 / max(1.0, n / HORIZON)))
        z = (mine["hit"] - pooled) / se
        out[coin] = {
            "hit": mine["hit"],
            "others": pooled,
            "difference": mine["hit"] - pooled,
            "z": z,
            "coins_compared": len(rated),
            "p_adjusted": min(1.0, len(rated) * math.erfc(abs(z) / math.sqrt(2.0))),
        }
    return out


def study(recordings: dict, slot_ids=None, prior=None) -> dict:
    """``recordings`` maps a market to a list of its recordings (each a list of frames
    with votes attached). A market with no frames is left out."""
    slot_ids = slot_ids or [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
    prior = prior or shipped_prior()
    rows = {
        coin: coin_row(groups, slot_ids, prior)
        for coin, groups in sorted(recordings.items())
        if any(groups)
    }
    return {
        "horizon_s": HORIZON,
        "coins": rows,
        "strong_against_the_others": compare(rows, "strong"),
        "any_call_against_the_others": compare(rows, "any_call"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--ticks",
        type=Path,
        action="append",
        default=[],
        help="a live tick recording (JSON lines, may be gzipped); repeatable",
    )
    parser.add_argument(
        "--base", type=Path, help="folder of hourly dual-quote captures"
    )
    parser.add_argument(
        "--prior",
        type=Path,
        default=SHIPPED,
        help="experiments.json holding each setting's recorded hit rate",
    )
    parser.add_argument("--out", type=Path, required=True, help="result JSON to write")
    args = parser.parse_args(argv)
    if not args.ticks and not args.base:
        parser.error("give at least one --ticks file or --base")
    if len({path.resolve() for path in args.ticks}) != len(args.ticks):
        parser.error("the same --ticks file was given twice; it would be counted twice")
    # Read the rates first: a missing file should fail before the ticks are read, not after.
    try:
        prior = shipped_prior(args.prior)
    except (OSError, KeyError, ValueError) as error:
        parser.error(f"--prior {args.prior}: {error}")
    missing = {variant["id"] for variant in F.VARIANTS} - set(prior)
    if missing:
        parser.error(
            f"--prior {args.prior} lacks {len(missing)} settings, such as {min(missing)}"
        )

    sources = []
    for path in args.ticks:
        try:
            sources.append((path.name, S.read_live(path)))
        except OSError as error:
            parser.error(f"--ticks {path}: {error}")
    if args.base:
        if not args.base.is_dir():
            parser.error(f"--base {args.base} is not a folder")
        sources.append((BASE_SOURCE, S.read_base(args.base)))

    recordings: dict[str, list] = {}
    too_short: dict[str, int] = {}
    for _, ticks in sources:
        for coin, series in ticks.items():
            frames = S.frames(series)
            if not frames:
                # No stretch of 600 seconds without a gap: the market is named, not dropped unseen.
                too_short[coin] = too_short.get(coin, 0) + int(series[0].size)
                continue
            X.variant_votes(frames)
            recordings.setdefault(coin, []).append(frames)
    if not recordings:
        print(
            json.dumps({"error": "no market had 600 seconds of ticks without a gap"}),
            flush=True,
        )
        return 1

    result = {
        "sources": [name for name, _ in sources],
        "prior_file": str(args.prior),
        # The rates and the tiles were chosen on the base capture: scoring it with them is in-sample.
        "in_sample_sources": [name for name, _ in sources if name == BASE_SOURCE],
        "too_short_ticks": too_short,
    } | study(recordings, prior=prior)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    partial = args.out.with_name(args.out.name + ".tmp")
    partial.write_text(
        json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(partial, args.out)
    brief = {
        coin: [
            round(row["hours"], 2),
            round(row["strong"]["hit"], 4) if "hit" in row["strong"] else None,
            round(row["strong"]["hit_se"], 4) if "hit" in row["strong"] else None,
        ]
        for coin, row in result["coins"].items()
    }
    print(
        json.dumps(
            {
                "written": str(args.out),
                "hours_strong_se": brief,
                "too_short": sorted(too_short),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
