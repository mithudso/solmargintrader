"""Self-contained deterministic anonymous judge; copied into a deny-default sandbox."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys

MAX_PACKET = 1024 * 1024
POLICY = {"minimum_trades": 30, "maximum_drawdown": 0.2, "drawdown_weight": 0.5}


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("invalid anonymous schema")


def number(value, *, minimum=None):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or (minimum is not None and value < minimum)
    ):
        raise ValueError("invalid anonymous metric")


def _median(values):
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    lower, upper = values[middle - 1:middle + 1]
    return lower + (upper - lower) / 2 if (lower < 0) == (upper < 0) else lower / 2 + upper / 2


def decide(packet):
    keys(packet, ("version", "policy", "candidates"))
    if type(packet["version"]) is not int or packet["version"] != 2:
        raise ValueError("unsupported anonymous protocol")
    keys(packet["policy"], POLICY)
    # Policy changes require a newly reviewed protocol, never post-result tuning.
    if packet["policy"] != POLICY:
        raise ValueError("unsupported frozen policy")
    candidates = packet["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 32:
        raise ValueError("candidate budget exceeded")
    ids, alignment, ranking, rejected = set(), None, {}, []
    total = 0
    for candidate in candidates:
        keys(candidate, ("id", "cells"))
        cid, cells = candidate["id"], candidate["cells"]
        if (
            not isinstance(cid, str)
            or not re.fullmatch("[0-9a-f]{32}", cid)
            or cid in ids
        ):
            raise ValueError("invalid anonymous ID")
        ids.add(cid)
        if not isinstance(cells, list) or not cells:
            raise ValueError("missing anonymous cells")
        total += len(cells)
        if total > 1000:
            raise ValueError("cell budget exceeded")
        blocks = []
        for cell in cells:
            keys(
                cell,
                (
                    "block",
                    "net_return",
                    "drawdown",
                    "turnover",
                    "trades",
                    "uncertainty",
                    "coverage",
                    "certified",
                    "cost_stress",
                ),
            )
            if (
                type(cell["block"]) is not int
                or cell["block"] < 0
                or type(cell["trades"]) is not int
                or cell["trades"] < 0
            ):
                raise ValueError("invalid block or trade count")
            blocks.append(cell["block"])
            for field in ("net_return", "drawdown", "turnover", "uncertainty"):
                number(cell[field], minimum=None if field == "net_return" else 0)
            for field in ("coverage", "certified", "cost_stress"):
                if type(cell[field]) is not bool:
                    raise ValueError("invalid anonymous flag")
        if len(set(blocks)) != len(blocks) or (
            alignment is not None and alignment != sorted(blocks)
        ):
            raise ValueError("incomparable anonymous cells")
        alignment = sorted(blocks)
        eligible = all(
            c["coverage"]
            and c["certified"]
            and c["cost_stress"]
            and c["drawdown"] <= POLICY["maximum_drawdown"]
            for c in cells
        )
        if not eligible or sum(c["trades"] for c in cells) < POLICY["minimum_trades"]:
            rejected.append(cid)
            continue
        ranking[cid] = (
            _median(
                c["net_return"] - POLICY["drawdown_weight"] * c["drawdown"]
                for c in cells
            ),
            -_median(c["turnover"] for c in cells),
        )
    best = max(ranking.values(), default=None)
    body = {
        "version": 2,
        "packet_digest": digest(packet),
        "policy_digest": digest(packet["policy"]),
        "tied_ids": sorted(k for k, v in ranking.items() if v == best),
        "rejected_ids": sorted(rejected),
    }
    return {**body, "verdict_digest": digest(body)}


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_PACKET, MAX_PACKET))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    raw = sys.stdin.buffer.read(MAX_PACKET + 1)
    if len(raw) > MAX_PACKET:
        raise ValueError("packet size exceeded")
    print(json.dumps(decide(json.loads(raw)), allow_nan=False))
