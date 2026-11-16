"""Bounded Coinbase Exchange public reads for the paper-only forward worker."""

from __future__ import annotations

import json
import math
import time
from datetime import UTC, datetime
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://api.exchange.coinbase.com"
VENUE = "Coinbase Exchange"
MAX_BYTES = 2 * 1024 * 1024
CACHE_MINUTES = 24 * 60


class MarketError(RuntimeError):
    """Only safe, stable reason codes cross the public-source boundary."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise MarketError("market_redirect_refused")


def _reject_constant(value):
    raise ValueError("nonfinite_json")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat().replace("+00:00", "Z")


def _number(value):
    if isinstance(value, bool):
        raise MarketError("ticker_schema_invalid")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise MarketError("ticker_schema_invalid") from None
    if not math.isfinite(number) or number <= 0:
        raise MarketError("ticker_schema_invalid")
    return number


def _asset(asset):
    if asset not in ("BTC", "ZEC"):
        raise MarketError("unsupported_paper_market")
    return f"{asset}-USD"


def parse_minutes(payload, start, end):
    """Coinbase rows are time, low, high, open, close, volume."""
    if not isinstance(payload, list) or len(payload) > 300:
        raise MarketError("candle_schema_invalid")
    result = {}
    for row in payload:
        if (
            not isinstance(row, list)
            or len(row) != 6
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in row)
        ):
            raise MarketError("candle_schema_invalid")
        stamp, low, high, opening, close, volume = row
        if (
            stamp != int(stamp)
            or stamp % 60
            or volume < 0
            or not 0 < low <= min(opening, close) <= max(opening, close) <= high
        ):
            raise MarketError("candle_schema_invalid")
        if start <= stamp < end:
            normalized = [int(stamp), opening, high, low, close, volume]
            if int(stamp) in result and result[int(stamp)] != normalized:
                raise MarketError("candle_duplicate_conflict")
            result[int(stamp)] = normalized
    return result


class LiveMarket:
    def __init__(
        self, *, base_url=BASE_URL, timeout=8, max_bytes=MAX_BYTES, clock=time.time
    ):
        parsed = urlsplit(base_url)
        local = parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "::1")
        if (
            (base_url != BASE_URL and not local)
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise MarketError("unapproved_market_base_url")
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 8
        ):
            raise MarketError("invalid_market_timeout")
        if type(max_bytes) is not int or not 64 <= max_bytes <= MAX_BYTES:
            raise MarketError("invalid_market_byte_limit")
        self.base_url = base_url.rstrip("/")
        self.venue = (
            VENUE if base_url == BASE_URL else "Loopback fixture (Coinbase schema)"
        )
        self.timeout, self.max_bytes, self.clock = timeout, max_bytes, clock
        self.opener = build_opener(NoRedirect())
        self.windows = {}

    def _get(self, path, parameters=None):
        url = self.base_url + path
        if parameters:
            url += "?" + urlencode(parameters)
        deadline = time.monotonic() + self.timeout
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "OraclePaperForward/1",
            },
            method="GET",
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise MarketError("market_http_error")
                body = bytearray()
                while True:
                    if response.isclosed():
                        break
                    if time.monotonic() >= deadline:
                        raise MarketError("market_deadline_exceeded")
                    socket = getattr(
                        getattr(getattr(response, "fp", None), "raw", None),
                        "_sock",
                        None,
                    )
                    if socket is None:
                        raise MarketError("market_timeout_control_unavailable")
                    socket.settimeout(max(0.001, deadline - time.monotonic()))
                    chunk = response.read1(min(65536, self.max_bytes + 1 - len(body)))
                    if not chunk:
                        if response.length not in (None, 0):
                            raise MarketError("market_response_incomplete")
                        break
                    body.extend(chunk)
                    if len(body) > self.max_bytes:
                        raise MarketError("market_response_limit")
            return json.loads(
                body.decode("utf-8"),
                parse_constant=_reject_constant,
                object_pairs_hook=_unique,
            )
        except MarketError:
            raise
        except HTTPError:
            raise MarketError("market_http_error") from None
        except (URLError, OSError, TimeoutError, HTTPException):
            raise MarketError("market_transport_unavailable") from None
        except (UnicodeError, ValueError, RecursionError):
            raise MarketError("market_json_invalid") from None

    def fetch(self, asset, start, end, *, cancelled=lambda: False):
        product = _asset(asset)
        if (
            type(start) is not int
            or type(end) is not int
            or start % 60
            or end % 60
            or not 0 < end - start <= CACHE_MINUTES * 60
        ):
            raise MarketError("invalid_candle_window")
        result = {}
        for left in range(start, end, 299 * 60):
            if cancelled():
                raise MarketError("market_cancelled")
            right = min(end, left + 299 * 60)
            payload = self._get(
                f"/products/{product}/candles",
                {"granularity": 60, "start": _iso(left), "end": _iso(right)},
            )
            result.update(parse_minutes(payload, left, right))
        if cancelled():
            raise MarketError("market_cancelled")
        return result

    def history(self, asset, interval_minutes, *, cancelled=lambda: False):
        _asset(asset)
        if interval_minutes not in (5, 10, 15, 20):
            raise MarketError("unsupported_bar_interval")
        now = self.clock()
        end = int(now // 60) * 60
        interval = interval_minutes * 60
        initial = end // interval * interval - 52 * interval
        window = self.windows.setdefault(
            asset, {"rows": {}, "end": None, "retry_at": 0, "error": None}
        )
        if cancelled():
            raise MarketError("market_cancelled")
        if window["end"] != end and now >= window["retry_at"]:
            start = (
                initial
                if not window["rows"]
                else max(
                    end - CACHE_MINUTES * 60, min(initial, max(window["rows"]) - 3 * 60)
                )
            )
            # Bootstrap once; subsequent polls overlap the last three minutes.
            if window["rows"] and min(window["rows"]) <= initial:
                start = max(end - CACHE_MINUTES * 60, max(window["rows"]) - 3 * 60)
            try:
                rows = self.fetch(asset, start, end, cancelled=cancelled)
                window["rows"].update(rows)
                window["error"] = None
                if end - 60 in rows:
                    window["end"] = end
                    window["retry_at"] = 0
                else:
                    window["error"] = "last_completed_minute_unavailable"
                    window["retry_at"] = now + 5
            except MarketError as error:
                window["error"] = str(error)
                window["retry_at"] = now + 15
                if not window["rows"]:
                    raise
        cutoff = end - CACHE_MINUTES * 60
        window["rows"] = {
            t: row for t, row in window["rows"].items() if cutoff <= t < end
        }
        return [window["rows"][t] for t in sorted(window["rows"])]

    def quote(self, asset):
        product = _asset(asset)
        payload = self._get(f"/products/{product}/ticker")
        if not isinstance(payload, dict):
            raise MarketError("ticker_schema_invalid")
        bid, ask = _number(payload.get("bid")), _number(payload.get("ask"))
        if bid > ask:
            raise MarketError("ticker_crossed_market")
        try:
            value = payload["time"]
            if not isinstance(value, str) or len(value) > 64:
                raise ValueError("invalid_time")
            instant = datetime.fromisoformat(value)
            if instant.tzinfo is None:
                raise ValueError("missing_timezone")
            stamp = instant.timestamp()
        except (KeyError, TypeError, ValueError, OverflowError):
            raise MarketError("ticker_time_invalid") from None
        now = self.clock()
        if not math.isfinite(stamp) or stamp > now:
            raise MarketError("ticker_time_in_future")
        if now - stamp > 15:
            raise MarketError("ticker_stale")
        return {
            "asset": asset,
            "product": product,
            "venue": self.venue,
            "quote_currency": "USD",
            "price": bid / 2 + ask / 2,
            "bid": bid,
            "ask": ask,
            "event_at": stamp,
            "observed_at": now,
            "source_url": f"{self.base_url}/products/{product}/ticker",
        }

    def cache_status(self, asset):
        window = self.windows.get(asset, {})
        rows = window.get("rows", {})
        return {
            "venue": self.venue,
            "product": _asset(asset),
            "quote_currency": "USD",
            "source": "public 1m trade candles and ticker bid/ask midpoint",
            "cached_minutes": len(rows),
            "first_minute": min(rows) if rows else None,
            "last_minute": max(rows) if rows else None,
            "candle_error": window.get("error"),
            "retry_at": window.get("retry_at", 0),
        }
