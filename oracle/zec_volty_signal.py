"""Public GUM observations and the frozen ZEC five-minute Volty breakout."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from http.client import HTTPException
from itertools import pairwise
from typing import Literal, NamedTuple
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

STRATEGY_ID = "zec-gum-volty-10-1.5"
WINDOW_SEC = 300
MARK_MAX_AGE_SEC = 20
_MARK_MAX_GAP_SEC = 45
_MINUTE_SEC = 60
_CANDLE_SETTLE_SEC = 5
_RANGE_LENGTH = 10
_RANGE_MULTIPLIER = 1.5
_WARMUP_SEC = (_RANGE_LENGTH + 1) * WINDOW_SEC
_GUM = "https://api.gum.ag/app/perps/"
_MAX_BYTES = 256 * 1024

Side = Literal["buy", "sell"]


class VoltyDataError(RuntimeError):
    """A symbolic market-data error suitable for operator status."""


@dataclass(frozen=True)
class VoltyObservation:
    window_start: int
    mark_at: int
    mark: float
    upper: float
    lower: float


@dataclass(frozen=True)
class VoltySignal:
    side: Side
    at: int
    event_id: str
    mark: float
    upper: float
    lower: float


class _Candle(NamedTuple):
    open: float
    high: float
    low: float
    close: float


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VoltyDataError("gum_public_redirect_refused")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VoltyDataError("gum_public_duplicate_key")
        result[key] = value
    return result


def _get_json(url):
    request = Request(
        url,
        headers={"Accept": "application/json", "Cache-Control": "no-cache"},
        method="GET",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=6) as response:
            raw = response.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise VoltyDataError("gum_public_response_too_large")
        return json.loads(raw, object_pairs_hook=_unique_keys)
    except (HTTPException, OSError, ValueError, RecursionError):
        raise VoltyDataError("gum_public_read_unavailable") from None


def _price(value) -> float:
    if type(value) in (int, float):
        try:
            if math.isfinite(value) and value > 0:
                return float(value)
        except OverflowError:
            pass
    raise VoltyDataError("gum_invalid_price")


def _window(now: float) -> int:
    return math.floor(now / WINDOW_SEC) * WINDOW_SEC


def _five_minute_bars(payload, boundary: int) -> list[_Candle]:
    if not isinstance(payload, list) or len(payload) > 128:
        raise VoltyDataError("gum_invalid_candle_response")
    start = boundary - _WARMUP_SEC
    minutes = {}
    for row in payload:
        if not isinstance(row, dict):
            raise VoltyDataError("gum_invalid_candle")
        opened_ms = row.get("t")
        if (
            row.get("s") != "ZEC"
            or row.get("i") != "1m"
            or type(opened_ms) is not int
            or opened_ms % (_MINUTE_SEC * 1000)
            or type(row.get("T")) is not int
            or row["T"] != opened_ms + _MINUTE_SEC * 1000
        ):
            raise VoltyDataError("gum_invalid_candle")
        candle = _Candle(*(_price(row.get(key)) for key in ("o", "h", "l", "c")))
        if candle.low > min(candle.open, candle.close) or candle.high < max(
            candle.open, candle.close
        ):
            raise VoltyDataError("gum_invalid_candle_range")
        opened = opened_ms // 1000
        if start <= opened < boundary:
            if opened in minutes and minutes[opened] != candle:
                raise VoltyDataError("gum_conflicting_candles")
            minutes[opened] = candle

    bars = []
    for opened in range(start, boundary, WINDOW_SEC):
        try:
            batch = [
                minutes[minute]
                for minute in range(opened, opened + WINDOW_SEC, _MINUTE_SEC)
            ]
        except KeyError:
            raise VoltyDataError("gum_closed_candles_incomplete") from None
        bars.append(
            _Candle(
                batch[0].open,
                max(bar.high for bar in batch),
                min(bar.low for bar in batch),
                batch[-1].close,
            )
        )
    return bars


def _bands(payload, boundary: int) -> tuple[float, float]:
    bars = _five_minute_bars(payload, boundary)
    ranges = [
        max(bar.high - bar.low, abs(bar.high - prior.close), abs(bar.low - prior.close))
        for prior, bar in pairwise(bars)
    ]
    close = bars[-1].close
    offset = _RANGE_MULTIPLIER * sum(ranges) / _RANGE_LENGTH
    upper, lower = _price(close + offset), _price(close - offset)
    if not lower < close < upper:
        raise VoltyDataError("gum_volty_invalid_bands")
    return upper, lower


def _mark(payload) -> tuple[int, float]:
    if not isinstance(payload, list) or len(payload) > 128:
        raise VoltyDataError("gum_invalid_market_catalog")
    rows = [
        row for row in payload if isinstance(row, dict) and row.get("symbol") == "ZEC"
    ]
    if len(rows) != 1 or type(rows[0].get("timestamp")) is not int:
        raise VoltyDataError("gum_invalid_zec_mark")
    return rows[0]["timestamp"], _price(rows[0].get("markPrice"))


def _validate_observation(observation: VoltyObservation, now: float) -> None:
    if (
        observation.window_start != _window(now)
        or type(observation.mark_at) is not int
        or not observation.window_start <= observation.mark_at <= now
        or now - observation.mark_at > MARK_MAX_AGE_SEC
    ):
        raise VoltyDataError("gum_zec_mark_stale")
    _price(observation.mark)
    if _price(observation.lower) >= _price(observation.upper):
        raise VoltyDataError("gum_volty_invalid_bands")


class GumVoltySource:
    """Read GUM trade candles and mark from fixed, unauthenticated GET endpoints."""

    def __init__(self, *, clock=time.time, read_json=None):
        self._clock = clock
        self._read_json = _get_json if read_json is None else read_json
        self._closed_bands: tuple[int, float, float] | None = None

    def read(self) -> VoltyObservation:
        now = self._clock()
        boundary = _window(now)
        if self._closed_bands is None or boundary != self._closed_bands[0]:
            # The newest one-minute trade candle can arrive just after its close.
            if now - boundary < _CANDLE_SETTLE_SEC:
                raise VoltyDataError("gum_waiting_for_closed_candles")
            query = urlencode(
                {"from": boundary - _WARMUP_SEC, "to": boundary, "interval": "1m"}
            )
            upper, lower = _bands(self._read_json(f"{_GUM}ohlcv/ZEC?{query}"), boundary)
            self._closed_bands = boundary, upper, lower
        _, upper, lower = self._closed_bands
        mark_at, mark = _mark(self._read_json(f"{_GUM}markets"))
        observation = VoltyObservation(boundary, mark_at, mark, upper, lower)
        _validate_observation(observation, self._clock())
        return observation


class VoltySignalEngine:
    """Emit one event for each distinct sampled crossing of the eligible bands."""

    def __init__(self):
        self._latest: VoltyObservation | None = None
        self._baseline: VoltyObservation | None = None

    def reset(self) -> None:
        """Require a new baseline after a data interruption. Keep the watermark."""
        self._baseline = None

    def observe(
        self, observation: VoltyObservation, *, now: float
    ) -> VoltySignal | None:
        try:
            _validate_observation(observation, now)
            return self._observe(observation)
        except VoltyDataError:
            self.reset()
            raise

    def _observe(self, observation: VoltyObservation) -> VoltySignal | None:
        latest = self._latest
        if latest is not None:
            if observation.mark_at <= latest.mark_at:
                if observation == latest:
                    return None
                raise VoltyDataError("gum_zec_mark_replayed")
            if observation.window_start == latest.window_start and (
                observation.upper != latest.upper or observation.lower != latest.lower
            ):
                raise VoltyDataError("gum_volty_bands_changed")
        previous = self._baseline
        self._latest = self._baseline = observation
        if (
            previous is None
            or observation.window_start != previous.window_start
            or observation.mark_at - previous.mark_at > _MARK_MAX_GAP_SEC
        ):
            return None

        side: Side
        if previous.mark < observation.upper <= observation.mark:
            side = "buy"
        elif previous.mark > observation.lower >= observation.mark:
            side = "sell"
        else:
            return None
        return VoltySignal(
            side,
            observation.mark_at,
            f"{STRATEGY_ID}:{observation.window_start}:{observation.mark_at}:{side}",
            observation.mark,
            observation.upper,
            observation.lower,
        )
