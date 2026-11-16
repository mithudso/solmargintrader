#!/usr/bin/env python3
"""Freeze vectors from the independent Python research functions; no network.

Run with the existing research environment. Node tests consume the frozen JSON
and verify the Python source bindings, so npm test needs no Python dependencies.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from oracle_leverage.exit50 import minute_features  # noqa: E402
from research.shape_study import detect_shapes  # noqa: E402


def rows_for(name: str, count: int = 96, step: int = 300) -> list[list[float | int]]:
    rows = []
    for i in range(count):
        x = (i - (count - 48)) * 2 / 47 - 1
        log_close = {
            "range": 0.006 * math.sin(i * 1.7),
            "trend_up": i * 0.001,
            "trend_down": -i * 0.001,
            "bowl": 0.05 * x * x,
            "cap": -0.05 * x * x,
            "v_rebound": -0.05 if abs(x) < 0.15 else 0.0,
            "inverted_v": 0.05 if abs(x) < 0.15 else 0.0,
            "compression": 0.0002 * math.sin(i * 1.3),
            "flat": 0.0,
        }[name]
        close = 100 * math.exp(log_close)
        spread = (0.01 - i * 0.00009) if name == "compression" else 0.001
        rows.append([1800000000 + i * step, close, close * math.exp(spread),
                     close * math.exp(-spread), close, 0])
    return rows


def main() -> None:
    source_files = ["oracle_leverage/exit50.py", "research/shape_study.py"]
    result = {"schema": "1000x-python-parity/v1", "source_sha256": {
        file: hashlib.sha256((ROOT / file).read_bytes()).hexdigest() for file in source_files
    }, "shapes": [], "momentum": []}
    for name in ("range", "trend_up", "trend_down", "bowl", "cap", "v_rebound", "inverted_v", "compression", "flat"):
        rows = rows_for(name)
        frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        expected = []
        for count in (48, 61, 96):
            row = detect_shapes(frame.iloc[:count]).iloc[-1]
            expected.append({"count": count, "shape": row["shape"], "zone": row["zone"],
                             "range_position": float(row["range_position"]),
                             "efficiency": float(row["path_efficiency"]), "r2": float(row["quadratic_r2"])})
        result["shapes"].append({"name": name, "rows": rows, "expected": expected})
    for mode in ("oscillating", "constant"):
        rows = []
        previous = 100.0
        for i in range(120):
            close = 100.0 if mode == "constant" else 100 * math.exp(0.012 * math.sin(i / 9) + i / 100000)
            low, high = min(close, previous) - 0.01, max(close, previous) + 0.01
            if i % 17 == 0:
                previous = close
                low = high = close
            rows.append([1800000000 + i * 60, previous, high, low, close, 0])
            previous = close
        features = minute_features(rows)
        expected = {str(i): features[rows[i][0] + 60] for i in (77, 78, 95, 119)}
        result["momentum"].append({"name": mode, "rows": rows, "expected": expected})
    target = ROOT / "extension/test/fixtures/1000x-python-parity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"Wrote {len(result['shapes'])} shape cases and {len(result['momentum'])} momentum cases to {target}")


if __name__ == "__main__":
    main()
