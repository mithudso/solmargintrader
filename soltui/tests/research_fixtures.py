from __future__ import annotations

import gzip
import json
from pathlib import Path

from botmanager.config import resolve_config
from botmanager.domain import BotSpec


def recording(root: Path, count: int = 8) -> dict:
    path = root / "recording.jsonl.gz"
    with gzip.open(path, "wt") as out:
        for second in range(count * 60):
            price = [100, 92, 101, 108][(second // 60) % 4]
            out.write(
                json.dumps(
                    {
                        "t": 1700000040 + second,
                        "q": {
                            "SOL-USD": [
                                price - 0.1,
                                price + 0.1,
                                price,
                                10,
                                10,
                                1700000040 + second,
                            ]
                        },
                    }
                )
                + "\n"
            )
    return {
        "schema_version": 1,
        "installation_id": "fixture-recorder",
        "source": "coinbase_exchange_recorder",
        "paths": [str(path)],
        "product": "SOL-USD",
        "quote_currency": "USD",
        "bar_seconds": 60,
        "start_ts": 1700000040,
        "end_ts": 1700000040 + count * 60,
        "fee_bps": 6.0,
        "slippage_bps": 2.0,
        "carry_bps_per_hour": 0.0,
        "min_order_quote": 10.0,
        "capital_quote": 1000.0,
    }


def grid(name="grid"):
    return BotSpec.create(name, "grid", resolve_config("grid", {}, {}, None))


def packet():
    return {
        "version": 2,
        "policy": {
            "minimum_trades": 30,
            "maximum_drawdown": 0.2,
            "drawdown_weight": 0.5,
        },
        "candidates": [
            {
                "id": c * 32,
                "cells": [
                    {
                        "block": i,
                        "net_return": ret,
                        "drawdown": 0.01,
                        "turnover": 1.0,
                        "trades": 3,
                        "uncertainty": 0.01,
                        "coverage": True,
                        "certified": True,
                        "cost_stress": True,
                    }
                    for i in range(10)
                ],
            }
            for c, ret in [("a", 0.02), ("b", 0.03)]
        ],
    }
