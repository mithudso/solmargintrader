"""Read existing normalized quote captures without starting a recorder."""

from __future__ import annotations

import json
import math
import re
import zlib
from pathlib import Path


class QuoteBars:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.files = {}
        self.bars = {"BTC": {}, "ZEC": {}}

    def read(self, now, budget=2 * 1024 * 1024):
        # At most four recent UTC hours; follow an unfinished gzip stream incrementally.
        paths = sorted(self.directory.glob("dual-quotes-*.jsonl.gz"))[-4:]
        for path in paths:
            if not re.fullmatch(
                r"dual-quotes-\d{8}T\d{2}-[0-9a-f]+\.jsonl\.gz", path.name
            ):
                continue
            state = self.files.setdefault(
                path, {"offset": 0, "z": zlib.decompressobj(31), "partial": b""}
            )
            try:
                with path.open("rb") as stream:
                    stream.seek(state["offset"])
                    chunk = stream.read(budget)
                state["offset"] += len(chunk)
                budget -= len(chunk)
                parts = []
                while chunk:
                    parts.append(state["z"].decompress(chunk))
                    chunk = state["z"].unused_data
                    if state["z"].eof:
                        state["z"] = zlib.decompressobj(31)
                    else:
                        break
                decoded = b"".join(parts)
                lines = (state["partial"] + decoded).split(b"\n")
                state["partial"] = lines.pop()[-65536:]
                for line in lines:
                    try:
                        row = json.loads(line)
                        self._add(row, now)
                    except (ValueError, TypeError):
                        continue
            except (OSError, zlib.error):
                continue
            if budget <= 0:
                break
        return {asset: self._view(asset, now) for asset in self.bars}

    def _add(self, row, now):
        if (
            not isinstance(row, dict)
            or row.get("venue") != "jupiter"
            or row.get("asset") not in self.bars
        ):
            return
        stamp, price = row.get("exchange_at"), row.get("price")
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v)
                for v in (stamp, price)
            )
            or price <= 0
            or stamp > now + 1
            or stamp < now - 14400
        ):
            return
        start = int(stamp // 600) * 600
        rows = self.bars[row["asset"]]
        bar = rows.get(start)
        if bar is None:
            rows[start] = {
                "start": start,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "first": stamp,
                "last": stamp,
                "gap": 0.0,
            }
        elif stamp > bar["last"]:
            bar["gap"] = max(bar["gap"], stamp - bar["last"])
            bar["last"] = stamp
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
        for key in list(rows):
            if key < start - 14400:
                del rows[key]

    def _view(self, asset, now):
        rows = self.bars[asset]
        boundary = int(now // 600) * 600

        def valid(bar, end):
            return (
                bar is not None
                and bar["first"] <= bar["start"] + 5
                and bar["last"] >= end - 5
                and bar["gap"] <= 5
            )

        complete = [
            b for t, b in sorted(rows.items()) if t < boundary and valid(b, t + 600)
        ]
        ranges = [b["high"] - b["low"] for b in complete[-20:]]
        baseline = sum(ranges) / len(ranges) if ranges else None
        previous = rows.get(boundary - 600)
        prior_ranges = [
            b["high"] - b["low"] for b in complete if b["start"] < boundary - 600
        ][-20:]
        prior_baseline = sum(prior_ranges) / len(prior_ranges) if prior_ranges else None
        current = rows.get(boundary)
        return {
            "previous": {**previous, "baseline_range": prior_baseline}
            if valid(previous, boundary)
            else None,
            "current": {
                **current,
                "baseline_range": baseline,
                "progress": (now - boundary) / 600,
            }
            if valid(current, now)
            else None,
        }
