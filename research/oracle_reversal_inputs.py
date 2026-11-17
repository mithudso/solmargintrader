"""Bounded public oracle OHLC acquisition for the frozen second-turn study."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from research.reversal_history import canonical, pack, validated_rows
from research.reversal_shapes import START, STOP

ENDPOINT = "https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history"
PAGE_MINUTES = 3000
MAX_BYTES = 512 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unexpected_oracle_redirect")


def decode_history(data, start, last):
    if data.get("s") != "ok" or any(
        not isinstance(data.get(k), list) for k in ("t", "o", "h", "l", "c", "v")
    ):
        raise ValueError("invalid_oracle_history")
    count = len(data["t"])
    if any(len(data[k]) != count for k in ("o", "h", "l", "c", "v")):
        raise ValueError("unequal_oracle_arrays")
    rows = validated_rows(
        [
            list(row)
            for row in zip(
                *(data[k] for k in ("t", "o", "h", "l", "c", "v")), strict=True
            )
        ]
    )
    if [r[0] for r in rows] != list(range(start, last + 60, 60)):
        raise ValueError("incomplete_or_extra_oracle_minutes")
    return rows


def acquire(asset):
    if asset not in ("BTC", "ZEC"):
        raise ValueError("unsupported_oracle_asset")
    opener = urllib.request.build_opener(NoRedirect())
    rows, pages = [], []
    for start in range(START, STOP, PAGE_MINUTES * 60):
        last = min(STOP - 60, start + (PAGE_MINUTES - 1) * 60)
        url = (
            ENDPOINT
            + "?"
            + urllib.parse.urlencode(
                {"symbol": asset + "USD", "resolution": "1", "from": start, "to": last}
            )
        )
        with opener.open(url, timeout=8) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES:
                raise ValueError("oracle_response_unavailable_or_large")
        decoded = decode_history(json.loads(raw), start, last)
        rows.extend(decoded)
        pages.append(
            {
                "url": url,
                "from": start,
                "last_inclusive": last,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "raw": raw.decode(),
            }
        )
    if len(rows) != (STOP - START) // 60:
        raise ValueError("oracle_total_count_mismatch")
    return {
        "schema": "oracle-reversal-history/v1",
        "coin": asset,
        "venue": "Jupiter fixed_rate@200ms oracle history",
        "quote": "USD",
        "feed_id": 1 if asset == "BTC" else 66,
        "source_url": ENDPOINT,
        "fetched_at": datetime.now(UTC).isoformat(),
        "study_start": START,
        "study_stop_exclusive": STOP,
        "volume_semantics": "Provider volume semantics unqualified; unavailable as a feature or activity filter.",
        "rows": rows,
        "pages": pages,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", choices=("ZEC", "BTC"), required=True)
    args = parser.parse_args(argv)
    print(canonical(pack(acquire(args.asset))))


if __name__ == "__main__":
    main()
