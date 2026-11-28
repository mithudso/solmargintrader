"""The experiment grid on recorded ticks, and a causal replay of the weighted aggregate.

The 1s scalp window keeps testing every setting in ``scalp_1s_features.VARIANTS``
at every horizon on live ticks. This module gives it a starting point (each
setting's hit rate on the base recording) and checks, without looking ahead,
whether weighting each tile by its running hit rate beats the plain vote.
"""

from __future__ import annotations

import math

import numpy as np

from research import scalp_1s_features as F

# The running rate decays with this half-life and is blended with a recorded prior
# worth PRIOR_SECONDS of calls. The extension uses the same three numbers.
WEIGHT_HALF_LIFE_S = 7200
PRIOR_SECONDS = 300
WEIGHTED_STRONG, WEIGHTED_LEAN = 0.75, 0.375


def variant_votes(frame_list) -> None:
    """Attach every variant's vote to each frame as int8 (0 = neutral or not ready)."""
    for fr in frame_list:
        seg = {k: fr[k] for k in ("time", "open", "high", "low", "close")}
        fr["variants"] = {
            variant["id"]: np.nan_to_num(
                F.vote(F.variant_values(seg, variant)), nan=0.0
            ).astype(np.int8)
            for variant in F.VARIANTS
        }


def forward_sign(close, horizon: int):
    """Sign of the move from each close to the close `horizon` seconds later; 0 where unknown or flat."""
    out = np.zeros(close.size, dtype=np.int8)
    if close.size > horizon:
        out[: close.size - horizon] = np.sign(
            close[horizon:] - close[:-horizon]
        ).astype(np.int8)
    return out


def _window(fr, horizon, lo, hi, span):
    if span is None:
        return np.ones(fr["time"].size, dtype=bool)
    a = span[0] + lo * (span[1] - span[0])
    b = span[0] + hi * (span[1] - span[0])
    # A call counts only when its outcome also falls inside the slice.
    return (fr["time"] >= a) & (fr["time"] + horizon < b)


def experiment_table(frame_list, lo=0.0, hi=1.0, span=None) -> dict:
    """Hit rate of every variant at every horizon: {id: {horizon: [hit_rate, calls]}}."""
    table = {variant["id"]: {} for variant in F.VARIANTS}
    for horizon in F.EXPERIMENT_HORIZONS:
        hits = dict.fromkeys(table, 0)
        calls = dict.fromkeys(table, 0)
        for fr in frame_list:
            sign = forward_sign(fr["close"], horizon)
            keep = (sign != 0) & _window(fr, horizon, lo, hi, span)
            for key, vote in fr["variants"].items():
                m = keep & (vote != 0)
                calls[key] += int(m.sum())
                hits[key] += int((vote[m] == sign[m]).sum())
        for key, row in table.items():
            row[horizon] = [hits[key] / calls[key] if calls[key] else None, calls[key]]
    return table


# When a setting may take a slot from the one in use. The extension uses the same numbers.
PROMOTE_MIN_EFF = (
    40  # independent-equivalent calls both settings need (calls / horizon)
)
PROMOTE_Z = 1.64  # the challenger's cautious (Wilson lower) estimate must beat the incumbent's rate
PROMOTE_MIN_RATE = 0.52
PROMOTE_PRIOR_SLACK = 0.002  # the recording must not say the opposite
PROMOTE_LOCK_S = 600  # a slot that just changed is left alone this long
PROMOTE_EVERY_S = 30
# A setting that needs more bars than this is tested and listed but never switched in: the grid's
# warm-up after opening, or after a feed break, must not grow. It is the starting grid's own need.
PROMOTE_MAX_NEED = 78
# Seconds ahead at which the average move after a call is measured, for the chart's likely line.
PATH_STEPS = (5, 10, 15, 20, 25, 30)


def wilson_lower(rate: float, n: float, z: float = PROMOTE_Z) -> float:
    """Lower end of a Wilson interval for a rate seen over n independent trials."""
    if not n > 0:
        return 0.0
    z2 = z * z
    return (
        rate + z2 / (2 * n) - z * math.sqrt((rate * (1 - rate) + z2 / (4 * n)) / n)
    ) / (1 + z2 / n)


def find_promotions(
    assign, hit, calls, prior, kinds, locks, now, horizon, need
) -> list:
    """Slots whose setting is clearly beaten by an unused setting of the same kind: [(slot, variant)]."""
    used = set(assign)
    out = []
    for slot, incumbent in enumerate(assign):
        if (
            now - locks[slot] < PROMOTE_LOCK_S
            or calls[incumbent] / horizon < PROMOTE_MIN_EFF
        ):
            continue
        mine = hit[incumbent] / calls[incumbent]
        best = None
        for v, kind in enumerate(kinds):
            if (
                kind != kinds[incumbent]
                or v in used
                or need[v] > PROMOTE_MAX_NEED
                or calls[v] / horizon < PROMOTE_MIN_EFF
            ):
                continue
            rate = hit[v] / calls[v]
            if (
                rate < PROMOTE_MIN_RATE
                or prior[v] < prior[incumbent] - PROMOTE_PRIOR_SLACK
            ):
                continue
            lower = wilson_lower(rate, calls[v] / horizon)
            if lower > mine and (best is None or lower > best[1]):
                best = (v, lower)
        if best:
            used.discard(incumbent)
            used.add(best[0])
            out.append((slot, best[0]))
    return out


def settle(hit, calls, correct, counted, t, horizon, decay) -> None:
    """One second of the running record, in place: every count fades, then the calls made
    `horizon` seconds ago are scored. The extension's ExperimentBook does the same, in this order."""
    hit *= decay
    calls *= decay
    if t >= horizon:
        hit += correct[t - horizon]
        calls += counted[t - horizon]


def outcomes(frame, ids, horizon):
    """Per second and variant: its vote, the later move's sign, whether the call can be scored, and whether it was right."""
    votes = np.column_stack([frame["variants"][key] for key in ids]).astype(np.float64)
    sign = forward_sign(frame["close"], horizon).astype(np.float64)
    counted = (votes != 0) & (sign[:, None] != 0)
    return votes, sign, counted, counted & (votes == sign[:, None])


def decayed_counts(frame, horizon) -> dict:
    """Every variant's running record after the whole frame: {id: [hit, calls]}."""
    ids = [variant["id"] for variant in F.VARIANTS]
    _, _, counted, correct = outcomes(frame, ids, horizon)
    decay = math.exp(-math.log(2) / WEIGHT_HALF_LIFE_S)
    hit = np.zeros(len(ids))
    calls = np.zeros(len(ids))
    for t in range(counted.shape[0]):
        settle(hit, calls, correct, counted, t, horizon, decay)
    return {key: [float(hit[k]), float(calls[k])] for k, key in enumerate(ids)}


def blend(hit, calls, prior):
    """The running rate pulled toward the recorded one, which counts as PRIOR_SECONDS calls."""
    return (hit + PRIOR_SECONDS * prior) / (calls + PRIOR_SECONDS)


def weights_of(blended) -> np.ndarray:
    """Each tile's say: its edge over a coin flip as a share of all edges; equal shares when nobody has one."""
    edge = np.maximum(0.0, np.asarray(blended, dtype=np.float64) - 0.5)
    total = edge.sum()
    return edge / total if total > 0 else np.full(edge.size, 1.0 / edge.size)


def tier_of(score: float) -> str:
    return (
        "strong"
        if abs(score) >= WEIGHTED_STRONG
        else "lean"
        if abs(score) >= WEIGHTED_LEAN
        else "mixed"
    )


def replay(groups, slot_ids, prior, horizon, lo=0.0, hi=1.0, span=None) -> dict:
    """Replay three aggregates without looking ahead, by tier: the plain vote, the
    hit-rate-weighted vote, and the weighted vote with clear winners switched in.

    ``groups`` is one list of frames per market: running rates are per market and
    survive a feed break, as in the extension. A setting's rate at second t counts
    only calls made `horizon` or more seconds earlier. ``prior`` maps a variant id
    to its recorded rate at the call horizon. A score under the lean threshold is
    still scored by its sign and reported as "mixed"; the window shows no direction
    for it.
    """
    ids = [variant["id"] for variant in F.VARIANTS]
    index = {key: k for k, key in enumerate(ids)}
    kinds = [variant["kind"] for variant in F.VARIANTS]
    need = np.array([variant["need"] for variant in F.VARIANTS])
    r0 = np.array([prior[key] for key in ids])
    decay = math.exp(-math.log(2) / WEIGHT_HALF_LIFE_S)
    names = ("plain", "weighted", "tuned")
    tiers = ("mixed", "lean", "strong")
    tally = {name: {tier: [0, 0, 0.0] for tier in tiers} for name in names}
    # Sum of the move in the direction of the call at each step ahead, for the likely-price line.
    path = {name: {tier: np.zeros(len(PATH_STEPS)) for tier in tiers} for name in names}
    seconds = 0
    changes = []
    start = [index[key] for key in slot_ids]
    for frames in groups:
        hit = np.zeros(len(ids))
        calls = np.zeros(len(ids))
        tuned = list(start)
        locks = [-math.inf] * len(start)
        for fr in frames:
            votes, sign, counted, correct = outcomes(fr, ids, horizon)
            close = fr["close"]
            ahead = np.full((close.size, len(PATH_STEPS)), np.nan)
            for k, step in enumerate(PATH_STEPS):
                ahead[: close.size - step, k] = (
                    close[step:] / close[:-step] - 1.0
                ) * 1e4
            keep = (sign != 0) & _window(fr, horizon, lo, hi, span)
            for t in range(votes.shape[0]):
                settle(hit, calls, correct, counted, t, horizon, decay)
                now = int(fr["time"][t])
                if now % PROMOTE_EVERY_S == 0:
                    for slot, variant in find_promotions(
                        tuned, hit, calls, r0, kinds, locks, now, horizon, need
                    ):
                        changes.append(
                            {"time": now, "from": ids[tuned[slot]], "to": ids[variant]}
                        )
                        tuned[slot] = variant
                        locks[slot] = now
                # Every tile of both grids must have a reading, as the window requires.
                if not keep[t] or t + 1 < max(need[start].max(), need[tuned].max()):
                    continue
                seconds += 1
                blended = blend(hit, calls, r0)
                scores = {"plain": float(votes[t, start].mean())}
                for name, slots in (("weighted", start), ("tuned", tuned)):
                    scores[name] = float(weights_of(blended[slots]) @ votes[t, slots])
                for name, value in scores.items():
                    if value == 0:
                        continue
                    row = tally[name][tier_of(value)]
                    row[0] += int(np.sign(value) == sign[t])
                    row[1] += 1
                    row[2] += float(np.sign(value) * fr["fwd"][t])
                    path[name][tier_of(value)] += np.sign(value) * ahead[t]
    result = {"seconds": seconds, "changes": len(changes), "change_log": changes[:40]}
    for name, by_tier in tally.items():
        result[name] = {}
        for tier, (hits, n, moved) in by_tier.items():
            result[name][tier] = (
                {
                    "n": n,
                    "share": n / seconds,
                    "hit": hits / n,
                    "hit_se": math.sqrt(0.25 / max(1.0, n / horizon)),
                    "mean_follow_bps": moved / n,
                    "path_bps": [
                        [step, float(path[name][tier][k] / n)]
                        for k, step in enumerate(PATH_STEPS)
                    ],
                }
                if n >= 300
                else {"n": n}
            )
    return result


def rule_fixture(frame, prior, slot_ids, horizon) -> dict:
    """Numbers the extension's tests reproduce with its own code: the running record after the
    frame, the weighted call at its last bar, and what the switch rule does with a made-up record."""
    ids = [variant["id"] for variant in F.VARIANTS]
    index = {key: k for k, key in enumerate(ids)}
    kinds = [variant["kind"] for variant in F.VARIANTS]
    need = np.array([variant["need"] for variant in F.VARIANTS])
    r0 = np.array([prior[key] for key in ids])
    counts = decayed_counts(frame, horizon)
    hit = np.array([counts[key][0] for key in ids])
    calls = np.array([counts[key][1] for key in ids])
    slots = [index[key] for key in slot_ids]
    weights = weights_of(blend(hit, calls, r0)[slots])
    votes = np.array([frame["variants"][key][-1] for key in slot_ids], dtype=np.float64)
    # A made-up record with plenty of calls everywhere and rates that differ by setting, so the
    # rule has real choices to make: several clear winners, near misses and contradicted ones.
    many = np.full(len(ids), 9000.0)
    rates = np.array([0.5 + 0.09 * math.sin(1.7 * k + 0.4) for k in range(len(ids))])
    start = list(slots)
    switches = find_promotions(
        start, rates * many, many, r0, kinds, [-math.inf] * len(slots), 0, horizon, need
    )
    return {
        "horizon": horizon,
        "counts": {key: [round(value, 9) for value in counts[key]] for key in ids},
        "weights": [float(value) for value in weights],
        "votes": [int(value) for value in votes],
        "score": float(weights @ votes),
        "tier": tier_of(float(weights @ votes)),
        "made_up": {
            "calls": 9000.0,
            "rates": [float(value) for value in rates],
            "weights": [
                float(value)
                for value in weights_of(blend(rates * many, many, r0)[slots])
            ],
        },
        "switches": [[slot_ids[slot], ids[variant]] for slot, variant in switches],
    }


def experiments_model(tile_keys, table, horizon, weighted) -> dict:
    """What the extension ships: the grid, the slots and each variant's recorded hit rate per horizon."""
    return {
        "version": 2,
        "horizons": list(F.EXPERIMENT_HORIZONS),
        "call_horizon_s": horizon,
        "half_life_s": WEIGHT_HALF_LIFE_S,
        "prior_seconds": PRIOR_SECONDS,
        "strong": WEIGHTED_STRONG,
        "lean": WEIGHTED_LEAN,
        "promotion": {
            "min_eff": PROMOTE_MIN_EFF,
            "z": PROMOTE_Z,
            "min_rate": PROMOTE_MIN_RATE,
            "prior_slack": PROMOTE_PRIOR_SLACK,
            "lock_s": PROMOTE_LOCK_S,
            "every_s": PROMOTE_EVERY_S,
            "max_need": PROMOTE_MAX_NEED,
        },
        "slots": [{"key": key, "variant": F.TILE_VARIANTS[key]} for key in tile_keys],
        # How the weighted aggregate did, tier by tier, when replayed without looking ahead.
        "measured": weighted,
        "variants": [
            {
                **variant,
                "prior": [
                    None
                    if table[variant["id"]][h][0] is None
                    else round(table[variant["id"]][h][0], 4)
                    for h in F.EXPERIMENT_HORIZONS
                ],
            }
            for variant in F.VARIANTS
        ],
    }
