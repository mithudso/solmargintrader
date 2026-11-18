"""Descriptive candle-color counts. No execution or prospective accuracy claim.

Adapted only to accept input paths from native artifact
art:b7b9b518c0c9baf5243a63fb39db79e5c2f2afdae3324cda691456811468074f.
Requires Python 3 and NumPy. Prints the original results schema unchanged.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(
    description="Reproduce the fixed-day ZEC streak counts; reads immutable private inputs and prints JSON."
)
parser.add_argument(
    "--capture-dir",
    type=Path,
    required=True,
    help="Directory containing accepted tape.npz and capture.json",
)
parser.add_argument(
    "--wal", type=Path, required=True, help="Original events.jsonl WAL, read-only"
)
args = parser.parse_args()
ROOT = args.capture_dir
info = json.loads((ROOT / "capture.json").read_text())
tape_path = ROOT / "tape.npz"
with tape_path.open("rb") as f:
    tape_hash = hashlib.file_digest(f, "sha256").hexdigest()
assert (
    tape_hash
    == info["tape_sha256"]
    == "21db6ff5a1b6fdd12f887ef506f654ff634af3c355ca898d2f0838de09fd6f4c"
)
wal = args.wal
with wal.open("rb") as f:
    wal_hash = hashlib.file_digest(f, "sha256").hexdigest()
assert (
    wal_hash
    == info["wal_sha256"]
    == "eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31"
)
with np.load(tape_path, allow_pickle=False) as a:
    times = a["trade_ns"]
    prices = a["price"]
assert len(times) == 134746 and len(prices) == len(times)
assert (
    np.all(times[1:] >= times[:-1])
    and np.all(np.isfinite(prices))
    and np.all(prices > 0)
)
assert times[0] >= info["start_ns"] and times[-1] < info["end_ns"]
NS = 10**9


def descriptive(values):
    return {
        "count": len(values),
        "mean": sum(values) / len(values) if values else None,
        "median": float(np.median(values)) if values else None,
        "max": max(values) if values else None,
        "histogram": dict(sorted(Counter(values).items())),
    }


def summarize(colors, valid):
    n = len(colors)
    out = {
        "eligible_bars": int(valid.sum()),
        "up": int(np.sum((colors == 1) & valid)),
        "down": int(np.sum((colors == -1) & valid)),
        "flat": int(np.sum((colors == 0) & valid)),
        "runs": {},
        "conditional": {},
    }
    for wanted, name in [(1, "up"), (-1, "down")]:
        opposite_ended = []
        all_ended = []
        flat_ended = []
        left = right = 0
        i = 0
        while i < n:
            if not valid[i] or colors[i] != wanted:
                i += 1
                continue
            j = i + 1
            while j < n and valid[j] and colors[j] == wanted:
                j += 1
            lc = i == 0 or not valid[i - 1]
            rc = j == n or not valid[j]
            left += int(lc)
            right += int(rc)
            if not lc and not rc:
                all_ended.append(j - i)
                if colors[j] == -wanted:
                    opposite_ended.append(j - i)
                elif colors[j] == 0:
                    flat_ended.append(j - i)
            i = j
        out["runs"][name] = {
            "ending_opposite": descriptive(opposite_ended),
            "ending_either_opposite_or_flat": descriptive(all_ended),
            "ending_flat": descriptive(flat_ended),
            "left_censored_runs": left,
            "right_censored_runs": right,
        }
        for k in (1, 2, 3):
            for exact in [False, True] if k == 2 else [False]:
                next_values = []
                for i in range(k, n):
                    if (
                        not valid[i - k : i + 1].all()
                        or not (colors[i - k : i] == wanted).all()
                    ):
                        continue
                    if exact and (
                        i <= k or not valid[i - k - 1] or colors[i - k - 1] != -wanted
                    ):
                        continue
                    next_values.append(int(colors[i]))
                counts = Counter(next_values)
                total = len(next_values)
                out["conditional"][
                    name + str(k) + ("_exact_after_opposite" if exact else "")
                ] = {
                    "n": total,
                    "next_up": counts[1],
                    "next_down": counts[-1],
                    "next_flat": counts[0],
                    "same_rate": counts[wanted] / total if total else None,
                    "opposite_rate": counts[-wanted] / total if total else None,
                }
    assert out["up"] + out["down"] + out["flat"] == out["eligible_bars"]
    return out


result = {
    "schema": 1,
    "input": {
        "wal_sha256": wal_hash,
        "tape_sha256": tape_hash,
        "capture_metadata_sha256": hashlib.sha256(
            (ROOT / "capture.json").read_bytes()
        ).hexdigest(),
        "start_ns": info["start_ns"],
        "end_ns": info["end_ns"],
        "trades": len(times),
        "clock": "receive time, matching accepted backtest tape; no forward-filled buckets",
    },
    "definitions": {
        "body": "up=close>open, down=close<open, flat=close==open",
        "close_to_close": "up/down relative to preceding close; prior/current bars must be valid",
        "gap_safe": "Any bucket overlapping any recorded gap interval is excluded; points exclude containing bucket. This conservatively includes receipt-silence and trade-ID-gap candidates, not all proven loss.",
        "average": "Fully observed same-color runs ending directly in opposite color; flats separate; first/last runs touching capture/gap bounds censored.",
        "last_two": "All overlapping last-two-color opportunities, including inside longer runs; next flat kept in denominator.",
        "exact_two": "Two-color run immediately preceded by opposite color; only all-four-valid windows.",
        "limits": "Single previously examined day. Frequencies are descriptive, not calibrated prospective probabilities; overlapping opportunities and serial/regime dependence remain.",
    },
    "results": [],
}
for step in (10, 60, 300, 600, 3600):
    width = step * NS
    start = (info["start_ns"] + width - 1) // width * width
    end = info["end_ns"] // width * width
    stamps = np.arange(start, end, width, dtype=np.int64)
    lo = np.searchsorted(times, stamps)
    hi = np.searchsorted(times, stamps + width)
    present = hi > lo
    opens = np.zeros(len(stamps))
    closes = np.zeros(len(stamps))
    opens[present] = prices[lo[present]]
    closes[present] = prices[hi[present] - 1]
    safe = present.copy()
    for a, b, kind in info["gaps"]:
        hit = (
            (stamps <= a) & (a < stamps + width)
            if a == b
            else (stamps < b) & (stamps + width > a)
        )
        safe[hit] = False
    body = np.sign(closes - opens).astype(int)
    cc = np.zeros(len(stamps), dtype=int)
    cc[1:] = np.sign(closes[1:] - closes[:-1]).astype(int)
    for mask_name, mask in [("all_observed", present), ("gap_safe", safe)]:
        for definition, d in [("body", body), ("close_to_close", cc)]:
            valid = mask.copy()
            if definition == "close_to_close":
                valid[0] = False
                valid[1:] &= mask[:-1]
            row = {
                "interval_seconds": step,
                "mask": mask_name,
                "definition": definition,
                "complete_buckets": len(stamps),
                "empty_buckets": int((~present).sum()),
                "gap_excluded_observed_buckets": int((present & ~safe).sum()),
            }
            row.update(summarize(d, valid))
            result["results"].append(row)
print(json.dumps(result, separators=(",", ":")))
