"""Past-only features, purged temporal splits and an explicit correlation search."""

from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = (1, 5, 10, 15, 30, 60)
SEED = 20261117


def features(
    primary: pd.DataFrame, references: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Every row is known at that minute's close; timestamps are never filled."""
    p = primary.set_index("timestamp")
    log_price = np.log(p.close)
    result = pd.DataFrame(index=p.index)
    for lag in (1, 5, 15, 60):
        result[f"return_{lag}m"] = log_price.diff(lag)
    result["body_return"] = np.log(p.close / p.open)
    result["range_fraction"] = (p.high - p.low) / p.close
    result["log_volume"] = np.log1p(p.volume)
    result["volatility_30m"] = log_price.diff().rolling(30, min_periods=30).std()
    result["volume_relative_60m"] = (
        p.volume / p.volume.rolling(60, min_periods=60).mean()
    )
    high, low = (
        p.high.rolling(48, min_periods=48).max(),
        p.low.rolling(48, min_periods=48).min(),
    )
    result["range_position_48m"] = (p.close - low) / (high - low)
    for coin, frame in sorted(references.items()):
        # Reindex to the exact primary clock before differencing. Missing
        # benchmark minutes invalidate the relevant lag rather than bridge it.
        close = frame.set_index("timestamp").close.reindex(p.index)
        for lag in (1, 5, 15, 60):
            value = np.log(close).diff(lag)
            count = close.rolling(lag + 1, min_periods=lag + 1).count()
            result[f"{coin}_return_{lag}m"] = value.where(count == lag + 1)
    return result.replace([np.inf, -np.inf], np.nan)


def split_indices(n: int) -> dict[str, tuple[int, int]]:
    return {
        "train": (0, int(n * 0.6)),
        "validation": (int(n * 0.6), int(n * 0.8)),
        "test": (int(n * 0.8), n),
    }


def sample_indices(n: int, horizon: int, left: int, right: int) -> np.ndarray:
    """Targets must end inside their own split; adjacent targets do not overlap."""
    return np.arange(left, min(right, n) - horizon, horizon, dtype=int)


def standardized(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = values - values.mean(axis=0)
    norm = np.sqrt(np.sum(centered * centered, axis=0))
    valid = norm > 1e-14
    return np.divide(centered, norm, out=np.zeros_like(centered), where=valid), valid


def permute_blocks(values: np.ndarray, block: int, rng) -> np.ndarray:
    chunks = [values[i : i + block] for i in range(0, len(values), block)]
    return np.concatenate([chunks[i] for i in rng.permutation(len(chunks))])


def analyze(
    primary: pd.DataFrame,
    references: dict[str, pd.DataFrame],
    replicates: int,
    *,
    family_multiplier: int = 1,
) -> dict:
    """A max-statistic null covers all reported validation/test feature searches.

    Block permutation is an approximate stationary no-association null. It is
    neither a causal identification method nor a calibrated trading probability.
    """
    if not isinstance(family_multiplier, int) or family_multiplier < 1:
        raise ValueError("correlation family multiplier must be a positive integer")
    f = features(primary, references)
    names = list(f.columns)
    values = f.to_numpy(float)
    close = primary.close.to_numpy(float)
    rows, null_maximum = [], np.zeros(replicates)
    for split, (left, right) in split_indices(len(primary)).items():
        for horizon in HORIZONS:
            indices = sample_indices(len(primary), horizon, left, right)
            target = np.log(close[indices + horizon] / close[indices])
            x = values[indices]
            block = max(1, int(np.ceil(60 / horizon)))
            groups = {}
            for j in range(len(names)):
                good = np.isfinite(x[:, j]) & np.isfinite(target)
                key = np.packbits(good).tobytes()
                groups.setdefault(key, (good, []))[1].append(j)
            permuted = None
            for good, columns in groups.values():
                n = int(good.sum())
                blocks = int(np.ceil(n / block))
                if n < 30 or blocks < 8:
                    rows.extend(
                        {
                            "split": split,
                            "feature": names[j],
                            "horizon_minutes": horizon,
                            "n": n,
                            "blocks": blocks,
                            "pearson": None,
                            "spearman_descriptive": None,
                            "status": "insufficient_nonoverlapping_observations",
                        }
                        for j in columns
                    )
                    continue
                xx, xvalid = standardized(x[good][:, columns])
                yy, yvalid = standardized(target[good, None])
                correlation = xx.T @ yy[:, 0]
                rank_x, _ = standardized(
                    pd.DataFrame(x[good][:, columns]).rank().to_numpy(float)
                )
                rank_y, _ = standardized(
                    pd.Series(target[good]).rank().to_numpy(float)[:, None]
                )
                spearman = rank_x.T @ rank_y[:, 0]
                null = None
                if split != "train" and yvalid[0]:
                    if permuted is None:
                        rng = np.random.default_rng(
                            SEED + horizon + (100 if split == "validation" else 200)
                        )
                        # Shuffle the regular target clock BEFORE masking each
                        # feature group. Sparse benchmarks never compress gaps
                        # into artificial adjacent target blocks.
                        permuted = np.stack(
                            [
                                permute_blocks(target, block, rng)
                                for _ in range(replicates)
                            ]
                        )
                    selected = permuted[:, good]
                    centered = selected - selected.mean(axis=1, keepdims=True)
                    norm = np.sqrt(np.sum(centered * centered, axis=1, keepdims=True))
                    normalized = np.divide(
                        centered, norm, out=np.zeros_like(centered), where=norm > 1e-14
                    )
                    null = normalized @ xx
                    null_maximum = np.maximum(null_maximum, np.abs(null).max(axis=1))
                for k, j in enumerate(columns):
                    valid = bool(xvalid[k] and yvalid[0])
                    row = {
                        "split": split,
                        "feature": names[j],
                        "horizon_minutes": horizon,
                        "n": n,
                        "blocks": blocks,
                        "pearson": float(correlation[k]) if valid else None,
                        "spearman_descriptive": float(spearman[k]) if valid else None,
                        "status": "computed" if valid else "constant_feature_or_target",
                    }
                    if null is not None and valid:
                        row["p_block_permutation"] = float(
                            (1 + np.sum(np.abs(null[:, k]) >= abs(correlation[k])))
                            / (replicates + 1)
                        )
                    rows.append(row)
    for row in rows:
        if "p_block_permutation" in row:
            row["p_maxT_validation_and_test"] = float(
                (1 + np.sum(null_maximum >= abs(row["pearson"]))) / (replicates + 1)
            )
            row["p_familywise"] = min(
                1.0, row["p_maxT_validation_and_test"] * family_multiplier
            )
    by_key = {(r["feature"], r["horizon_minutes"], r["split"]): r for r in rows}
    training = sorted(
        (r for r in rows if r["split"] == "train" and r["pearson"] is not None),
        key=lambda r: (-abs(r["pearson"]), r["feature"], r["horizon_minutes"]),
    )
    shortlist = []
    for r in training[:12]:
        related = {
            s: by_key[(r["feature"], r["horizon_minutes"], s)]
            for s in split_indices(len(primary))
        }
        a, b, c = (related[s]["pearson"] for s in ("train", "validation", "test"))
        same_sign = b is not None and c is not None and a * b > 0 and a * c > 0
        shortlist.append(
            {
                "feature": r["feature"],
                "horizon_minutes": r["horizon_minutes"],
                "splits": related,
                "same_sign_all_splits": same_sign,
                "corrected_test_association": same_sign
                and related["test"].get("p_familywise", 1) <= 0.05,
            }
        )
    contemporaneous = []
    for coin, frame in sorted(references.items()):
        ref = frame.set_index("timestamp").close.reindex(primary.timestamp)
        pair = pd.DataFrame(
            {
                "primary": np.log(close[1:] / close[:-1]),
                "reference": np.log(ref.to_numpy()[1:] / ref.to_numpy()[:-1]),
            }
        ).dropna()
        contemporaneous.append(
            {
                "reference": coin,
                "n": len(pair),
                "pearson_descriptive": float(pair.primary.corr(pair.reference))
                if len(pair) > 1 and pair.primary.std() > 0 and pair.reference.std() > 0
                else None,
                "qualification": "same-minute return co-movement; does not establish a leading signal",
            }
        )
    coverage = []
    for split in ("validation", "test"):
        for horizon in HORIZONS:
            tests = [
                r
                for r in rows
                if r["split"] == split and r["horizon_minutes"] == horizon
            ]
            coverage.append(
                {
                    "split": split,
                    "horizon_minutes": horizon,
                    "computed": sum(r["status"] == "computed" for r in tests),
                    "insufficient": sum(
                        r["status"] == "insufficient_nonoverlapping_observations"
                        for r in tests
                    ),
                    "constant": sum(
                        r["status"] == "constant_feature_or_target" for r in tests
                    ),
                    "minimum_n": min(r["n"] for r in tests),
                    "maximum_n": max(r["n"] for r in tests),
                }
            )
    return {
        "schema": "weekly-correlations/v2",
        "features": names,
        "horizons_minutes": list(HORIZONS),
        "splits": split_indices(len(primary)),
        "replicates": replicates,
        "family_multiplier": family_multiplier,
        "seed": SEED,
        "method": "Pearson; nonoverlapping outcomes; targets purged at split ends; feature-specific finite observations; full-clock 60-minute target-block permutations before feature masking; shared max statistic over every validation/test feature and horizon",
        "limits": [
            "One week and two short held-out windows cannot establish robustness across regimes.",
            "Approximate stationary block-permutation null; nonstationary or longer dependence can invalidate its p-values.",
            "Spearman and same-minute correlations are descriptive; no corrected significance claim is attached to them.",
            "A correlation is not a trade, profit probability, causal effect or execution result.",
        ],
        "coverage": coverage,
        "rows": rows,
        "training_only_shortlist": shortlist,
        "contemporaneous": contemporaneous,
        "corrected_test_findings": sum(
            r["split"] == "test" and r.get("p_familywise", 1) <= 0.05 for r in rows
        ),
    }
