"""Past-only visible Coinbase L2 imbalance for the frozen exit50 diagnostic.

Inputs are retained receipt-time snapshots, not order counts or an exchange-wide book.
"""

from __future__ import annotations

import math

import numpy as np

NS = 1_000_000_000
MAX_AGE_NS = 2 * NS
BAND_BPS = 10.0


def book_feature(quote_ns, books, gaps, decision_ns):
    """Return the most recent valid 40-level snapshot no later than decision time."""
    stamps = np.asarray(quote_ns, dtype=np.int64)
    if len(stamps) != len(books) or (
        len(stamps) > 1 and np.any(stamps[1:] <= stamps[:-1])
    ):
        raise ValueError("invalid_quote_sequence")
    index = int(np.searchsorted(stamps, decision_ns, side="right")) - 1
    if index < 0:
        return {"status": "no_prior_book"}
    quote_at = int(stamps[index])
    age_ns = int(decision_ns) - quote_at
    if age_ns < 0 or age_ns > MAX_AGE_NS:
        return {"status": "stale", "quote_ns": quote_at}
    for start, end, kind in gaps:
        if (
            kind in {"connection_gap", "connection_open", "receipt_gap"}
            and int(start) <= decision_ns
            and int(end) >= quote_at
        ):
            return {"status": "connection_or_receipt_gap", "quote_ns": quote_at}
    book = np.asarray(books[index], dtype=float)
    if book.shape != (2, 40, 2) or not np.isfinite(book).all() or np.any(book < 0):
        return {"status": "invalid_book", "quote_ns": quote_at}
    sides = []
    for side in book:
        valid = side[(side[:, 0] > 0) & (side[:, 1] > 0)]
        if not len(valid):
            return {"status": "invalid_book", "quote_ns": quote_at}
        sides.append(valid)
    bid, ask = sides
    if (
        np.any(np.diff(bid[:, 0]) >= 0)
        or np.any(np.diff(ask[:, 0]) <= 0)
        or bid[0, 0] >= ask[0, 0]
    ):
        return {"status": "invalid_book", "quote_ns": quote_at}
    mid = (bid[0, 0] + ask[0, 0]) / 2
    low, high = mid * (1 - BAND_BPS / 10000), mid * (1 + BAND_BPS / 10000)
    b = float(np.sum(bid[bid[:, 0] >= low, 0] * bid[bid[:, 0] >= low, 1]))
    a = float(np.sum(ask[ask[:, 0] <= high, 0] * ask[ask[:, 0] <= high, 1]))
    if not math.isfinite(a + b) or a + b <= 0:
        return {"status": "invalid_book", "quote_ns": quote_at}
    complete = bool(bid[-1, 0] <= low and ask[-1, 0] >= high)
    return {
        "status": "ready" if complete else "truncated_visible_band",
        "quote_ns": quote_at,
        "age_seconds": age_ns / NS,
        "mid": mid,
        "band_bps": BAND_BPS,
        "bid_notional": b,
        "ask_notional": a,
        "imbalance": (b - a) / (b + a),
        "band_covered_by_visible_levels": complete,
        "depth_cap": 40,
        "semantics": "visible Coinbase L2 notional; not order counts or all venues",
    }


def taker_quote_imbalance(klines):
    """Three completed one-minute taker quote imbalance, never an L2 order count.

    Input is original Binance Spot kline arrays in chronological order. Zero quote
    volume or a missing minute resets the three-minute warmup.
    """
    out = []
    previous = None
    window = []
    for row in klines:
        if not isinstance(row, list) or len(row) != 12:
            raise ValueError("invalid_kline_fields")
        stamp = int(row[0])
        if stamp % 60000 or int(row[6]) != stamp + 59999:
            raise ValueError("invalid_kline_clock")
        if previous is not None and stamp <= previous:
            raise ValueError("nonmonotonic_kline_clock")
        if previous is not None and stamp != previous + 60000:
            window = []
        total, buy = float(row[7]), float(row[10])
        if (
            not math.isfinite(total)
            or not math.isfinite(buy)
            or total < 0
            or buy < 0
            or buy > total
        ):
            raise ValueError("invalid_kline_quote_volume")
        value = (2 * buy - total) / total if total > 0 else None
        if value is None:
            window = []
        else:
            window = (window + [value])[-3:]
        out.append(
            {
                "available_at_ms": stamp + 60000,
                "imbalance": value,
                "sma3": sum(window) / 3 if len(window) == 3 else None,
            }
        )
        previous = stamp
    return out
