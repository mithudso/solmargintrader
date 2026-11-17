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
    primary: pd.DataFrame, references: dict[str, pd.DataFrame], replicates: int
) -> dict:
    """A max-statistic null covers all reported validation/test feature searches.

    Block permutation is an approximate stationary no-association null. It is
    neither a causal identification method nor a calibrated trading probability.
    """
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
            good = np.isfinite(x).all(axis=1) & np.isfinite(target)
            x, target = x[good], target[good]
            n, block = len(target), max(1, int(np.ceil(60 / horizon)))
            blocks = int(np.ceil(n / block))
            if n < 30 or blocks < 8:
                rows.extend(
                    {
                        "split": split,
                        "feature": name,
                        "horizon_minutes": horizon,
                        "n": n,
                        "blocks": blocks,
                        "pearson": None,
                        "spearman_descriptive": None,
                        "status": "insufficient_nonoverlapping_observations",
                    }
                    for name in names
                )
                continue
            xx, xvalid = standardized(x)
            yy, yvalid = standardized(target[:, None])
            correlation = xx.T @ yy[:, 0]
            ranked_x = pd.DataFrame(x).rank().to_numpy(float)
            ranked_y = pd.Series(target).rank().to_numpy(float)
            rank_x, _ = standardized(ranked_x)
            rank_y, _ = standardized(ranked_y[:, None])
            spearman = rank_x.T @ rank_y[:, 0]
            null = None
            if split != "train" and yvalid[0]:
                rng = np.random.default_rng(
                    SEED + horizon + (100 if split == "validation" else 200)
                )
                null = (
                    np.stack(
                        [
                            permute_blocks(yy[:, 0], block, rng)
                            for _ in range(replicates)
                        ]
                    )
                    @ xx
                )
                null_maximum = np.maximum(null_maximum, np.abs(null).max(axis=1))
            for j, name in enumerate(names):
                valid = bool(xvalid[j] and yvalid[0])
                row = {
                    "split": split,
                    "feature": name,
                    "horizon_minutes": horizon,
                    "n": n,
                    "blocks": blocks,
                    "pearson": float(correlation[j]) if valid else None,
                    "spearman_descriptive": float(spearman[j]) if valid else None,
                    "status": "computed" if valid else "constant_feature_or_target",
                }
                if null is not None and valid:
                    row["p_block_permutation"] = float(
                        (1 + np.sum(np.abs(null[:, j]) >= abs(correlation[j])))
                        / (replicates + 1)
                    )
                rows.append(row)
    for row in rows:
        if "p_block_permutation" in row:
            row["p_maxT_validation_and_test"] = float(
                (1 + np.sum(null_maximum >= abs(row["pearson"]))) / (replicates + 1)
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
                and related["test"].get("p_maxT_validation_and_test", 1) <= 0.05,
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
                "pearson_descriptive": float(pair.primary.corr(pair.reference)),
                "qualification": "same-minute return co-movement; does not establish a leading signal",
            }
        )
    return {
        "schema": "weekly-correlations/v1",
        "features": names,
        "horizons_minutes": list(HORIZONS),
        "splits": split_indices(len(primary)),
        "replicates": replicates,
        "seed": SEED,
        "method": "Pearson; nonoverlapping outcomes; targets purged at split ends; shared 60-minute block-permutation max statistic over every validation/test feature and horizon",
        "limits": [
            "One week and two short held-out windows cannot establish robustness across regimes.",
            "Approximate stationary block-permutation null; nonstationary or longer dependence can invalidate its p-values.",
            "Spearman and same-minute correlations are descriptive; no corrected significance claim is attached to them.",
            "A correlation is not a trade, profit probability, causal effect or execution result.",
        ],
        "rows": rows,
        "training_only_shortlist": shortlist,
        "contemporaneous": contemporaneous,
        "corrected_test_findings": sum(
            r["split"] == "test" and r.get("p_maxT_validation_and_test", 1) <= 0.05
            for r in rows
        ),
    }
