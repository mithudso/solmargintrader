"""Shared, read-only Jupiter ZEC oracle comparison window; not TV market data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from research.oracle_reversal_inputs import decode_history
from research.pine_bar_emulator import Bar
from research.reversal_history import read_archive, validated_rows
from research.shape_study import protected_intervals, refuse_reserved

SOURCE_SHA256 = "8b5eb4f54851fad81c28137bda85e643e34c93da349c3c0178b8df271948b2bc"
SOURCE_ARTIFACT = "art:daf887a414eb6078d63bbb2e557fbe6ebfc29433c43feaec69506a884bfda896"
START = 1791666000  # 2026-10-10 21:00 UTC
STOP = 1794164400   # 2026-11-08 19:00 UTC, exclusive
ALIASES = ("ZEC", "ZECUSD", "ZECUSDC", "ZECUSDC.P")


def load_window(source: Path, ledger: Path) -> tuple[list[list[float]], dict[str, object]]:
    """Verify native and raw page hashes, exact minute coverage and holdouts.

    Call this again immediately after a study to recheck the shared holdout
    ledger. The source is historical Jupiter oracle USD, never a Coinbase
    USDC perpetual substitute. Its volume has no qualified meaning.
    """
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("source hash mismatch")
    if not ledger.is_file():
        raise ValueError("holdout ledger missing")
    data = read_archive(source)
    if data.get("coin") != "ZEC" or data.get("venue") != "Jupiter fixed_rate@200ms oracle history":
        raise ValueError("unexpected source identity")
    rows = validated_rows(data["rows"])
    reconstructed = []
    for page in data["pages"]:
        body = page["raw"].encode()
        if len(body) != page["bytes"] or hashlib.sha256(body).hexdigest() != page["sha256"]:
            raise ValueError("raw page integrity mismatch")
        reconstructed.extend(decode_history(json.loads(body), page["from"], page["last_inclusive"]))
    if len(data["pages"]) != 14 or len(rows) != 41680 or reconstructed != rows:
        raise ValueError("raw pages do not match frozen minute rows")
    selected = [row for row in rows if START <= row[0] < STOP]
    if (len(selected) != (STOP-START)//60 or selected[0][0] != START or
            any(row[0] != START+60*i for i, row in enumerate(selected))):
        raise ValueError("common full-hour window is incomplete")
    reservations = protected_intervals(ledger, ALIASES)
    refuse_reserved(pd.DataFrame({"timestamp": [int(row[0]) for row in selected]}), "1m", reservations)
    return selected, {"source_artifact_id": SOURCE_ARTIFACT, "source_sha256": SOURCE_SHA256,
                      "start": START, "stop_exclusive": STOP, "minutes": len(selected),
                      "reservations": reservations,
                      "limitation": "previously observed Jupiter ZEC/USD oracle, not Coinbase USDC perpetual"}


def aggregate(rows: list[list[float]], step: int) -> list[Bar]:
    """Aggregate complete 1-minute rows into contiguous aligned chart bars."""
    if step not in (600, 900) or not rows or len(rows) % (step//60):
        raise ValueError("requires complete 10- or 15-minute groups")
    size = step//60
    result = []
    for i in range(0, len(rows), size):
        group = rows[i:i+size]
        if group[0][0] % step or any(row[0] != group[0][0]+60*j for j, row in enumerate(group)):
            raise ValueError("unaligned or incomplete minute group")
        result.append(Bar(int(group[0][0]), group[0][1], max(x[2] for x in group),
                          min(x[3] for x in group), group[-1][4]))
    return result


def equal_notional_qty(signal_close: float, target_usd: float = 1000.) -> float:
    """Fix quantity on the completed signal close, assuming unit multiplier 1."""
    import math
    if not math.isfinite(signal_close) or signal_close <= 0 or not math.isfinite(target_usd) or target_usd <= 0:
        raise ValueError("signal close and target must be finite and positive")
    return target_usd / signal_close
