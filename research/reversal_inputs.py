"""Acquire an exact public BTC minute snapshot; never trade or synthesize bars."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from research.reversal_history import canonical, pack, validated_rows
from research.reversal_shapes import START, STOP

BASE = "https://data-api.binance.vision/api/v3/klines"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unexpected history redirect")


def fetch(get=None, pause=time.sleep):
    opener = build_opener(NoRedirect())

    def read(url):
        with opener.open(
            Request(url, headers={"User-Agent": "Oracle-empirical-study/1"}), timeout=8
        ) as response:
            raw = response.read(512 * 1024 + 1)
            if response.status != 200 or len(raw) > 512 * 1024:
                raise ValueError("invalid historical response")
            return raw

    get = get or read
    pages, rows = [], []
    for left in range(START, STOP, 1000 * 60):
        right = min(STOP, left + 1000 * 60)
        url = (
            BASE
            + "?"
            + urlencode(
                {
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "startTime": left * 1000,
                    "endTime": right * 1000 - 1,
                    "limit": 1000,
                }
            )
        )
        raw = get(url)
        body = json.loads(raw)
        if not isinstance(body, list) or not body:
            raise ValueError("missing historical page")
        page_rows = []
        for item in body:
            if (
                len(item) < 7
                or int(item[0]) % 60000
                or int(item[6]) != int(item[0]) + 59999
            ):
                raise ValueError("invalid kline timestamps")
            stamp = int(item[0]) // 1000
            if not left <= stamp < right:
                raise ValueError("historical page outside requested window")
            page_rows.append([stamp, *map(float, item[1:6])])
        page_rows = validated_rows(page_rows)
        if len(page_rows) != (right - left) // 60:
            raise ValueError("incomplete historical page")
        pages.append(
            {
                "start": left,
                "end_exclusive": right,
                "url": url,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "raw_utf8": raw.decode(),
            }
        )
        rows.extend(page_rows)
        pause(0.15)
    return {
        "schema": "reversal-history/v1",
        "coin": "BTC",
        "venue": "Binance spot",
        "quote": "USDT",
        "product": "BTCUSDT",
        "clock": "exchange UTC minute open",
        "source_url": BASE,
        "fetched_at": datetime.now(UTC).isoformat(),
        "study_start": START,
        "study_end_exclusive": STOP,
        "input_start": START,
        "input_end_exclusive": STOP,
        "rows": validated_rows(rows),
        "pages": pages,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport-output",
        type=Path,
        required=True,
        help="Ephemeral transport only; archive in Mongo before analysis/projection",
    )
    args = parser.parse_args(argv)
    value = fetch()
    args.transport_output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.transport_output.write_text(canonical(pack(value)) + "\n")
    print(
        json.dumps(
            {
                "rows": len(value["rows"]),
                "pages": len(value["pages"]),
                "source_sha256": hashlib.sha256(canonical(value).encode()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
