"""Read-only market adapters with explicit source and clock semantics.

No adapter starts the shared recorder, loads a signing key, or obtains a swap.
Jupiter's Price V3 API supplies USD reference prices, not a SOL/USDC execution
quote or a push stream. Its response has block IDs but no market-event timestamp.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUPITER_PRICE_URL = f"https://api.jup.ag/price/v3?ids={SOL_MINT},{USDC_MINT}"
MAX_RESPONSE_BYTES = 1_048_576
INSTRUMENT = re.compile(r"[A-Za-z][A-Za-z0-9]{0,15}/[A-Za-z][A-Za-z0-9]{0,15}\Z")
MINT = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}\Z")


def validate_instrument(value: str) -> str:
    """Canonicalize an explicit pair without inferring quote equivalence."""
    if not isinstance(value, str) or not INSTRUMENT.fullmatch(value):
        raise ValueError("invalid_instrument")
    base, quote = value.upper().split("/")
    if base == quote:
        raise ValueError("invalid_instrument")
    return f"{base}/{quote}"


class FeedUnavailable(RuntimeError):
    """A symbolic, credential-free feed failure safe for a public response."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _number(value: Any, *, positive: bool = True) -> float:
    if type(value) not in (int, float):
        raise FeedUnavailable("invalid_market_data")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise FeedUnavailable("invalid_market_data") from None
    if not math.isfinite(result):
        raise FeedUnavailable("invalid_market_data")
    if result <= 0 if positive else result < 0:
        raise FeedUnavailable("invalid_market_data")
    return result


def _identity(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: Any, headers: Any, newurl: Any
    ) -> None:
        # Never carry the provider credential to a redirect destination.
        return None


def _get_json(
    url: str, headers: Mapping[str, str], timeout: float, max_bytes: int
) -> dict:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise FeedUnavailable("provider_response_too_large")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise FeedUnavailable("invalid_market_data")
        return payload
    except FeedUnavailable:
        raise
    except HTTPError as exc:
        code = (
            "provider_auth_failed"
            if exc.code in (401, 403)
            else "provider_rate_limited"
            if exc.code == 429
            else "provider_http_error"
        )
        raise FeedUnavailable(code) from None
    except Exception:  # noqa: BLE001 - provider exceptions must not expose request credentials.
        # Network/decoder errors can contain URLs, bodies or header values.
        raise FeedUnavailable("provider_unavailable") from None


class RecorderFeed:
    """Read only the shared recorder's explicitly selected exact pair.

    No source starts or quote substitutions occur. A missing requested pair
    produces instrument_unavailable even when another quote currency exists.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        clock: Callable[[], float] = time.time,
        max_age: float = 15,
        instrument: str = "SOL/USDC",
    ) -> None:
        self.instrument = validate_instrument(instrument)
        self.product = self.instrument.replace("/", "-")
        configured = Path(
            os.environ.get("SOLTUI_CONFIG_DIR") or Path.home() / ".config" / "soltui"
        )
        self.root = Path(root) if root is not None else configured / "prices"
        self.clock = clock
        self.max_age = _number(max_age)
        self._last_id: str | None = None

    def poll(self) -> dict | None:
        now = _number(self.clock(), positive=False)
        try:
            with (self.root / "latest.json").open("rb") as handle:
                raw = handle.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise FeedUnavailable("recorder_response_too_large")
            latest = json.loads(raw)
        except FeedUnavailable:
            raise
        except Exception:  # noqa: BLE001 - malformed external files cross a sanitized boundary.
            raise FeedUnavailable("recorder_unavailable") from None
        if not isinstance(latest, dict) or not isinstance(latest.get("q"), dict):
            raise FeedUnavailable("invalid_market_data")
        stamp = _number(latest.get("t"), positive=False)
        if not 0 <= now - stamp <= self.max_age:
            raise FeedUnavailable("recorder_stale")
        quote = latest["q"].get(self.product)
        if not isinstance(quote, list) or len(quote) < 6:
            raise FeedUnavailable("instrument_unavailable")
        bid, ask = _number(quote[0]), _number(quote[1])
        quoted_at = _number(quote[5], positive=False)
        if bid > ask:
            raise FeedUnavailable("invalid_market_data")
        if not 0 <= now - quoted_at <= self.max_age:
            raise FeedUnavailable("quote_stale")
        event_id = _identity(["coinbase_recorder", self.product, quoted_at, bid, ask])
        if event_id == self._last_id:
            return None
        self._last_id = event_id
        return {
            "source": "coinbase_recorder",
            "instrument": self.instrument,
            "venue": "coinbase_exchange",
            "kind": "stream_snapshot_mid",
            "event_id": event_id,
            "observed_at": quoted_at,
            "received_at": now,
            "price": bid / 2 + ask / 2,
            "bid": bid,
            "ask": ask,
            "timestamp_semantics": "recorder_quote_clock",
            "upstream_recency_verified": False,
        }


class JupiterPriceFeed:
    """Poll Jupiter reference prices with an explicit environment credential.

    Block changes provide local progress evidence only; the API does not supply
    enough information to certify initial upstream event age. Each token must
    continue progressing within max_block_idle, or polling fails closed.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        transport: Callable[[str, Mapping[str, str], float, int], dict] | None = None,
        timeout: float = 5,
        max_block_idle: float = 15,
        instrument: str = "SOL/USDC",
        mints: Mapping[str, str] | None = None,
    ) -> None:
        self.instrument = validate_instrument(instrument)
        base, quote = self.instrument.split("/")
        if "USD" in (base, quote):
            raise FeedUnavailable("instrument_not_onchain")
        mapping = (
            {"SOL": SOL_MINT, "USDC": USDC_MINT}
            if mints is None and self.instrument == "SOL/USDC"
            else mints
        )
        if not isinstance(mapping, Mapping):
            raise FeedUnavailable("instrument_mapping_required")
        selected = [mapping.get(base), mapping.get(quote)]
        if (
            any(
                not isinstance(mint, str) or not MINT.fullmatch(mint)
                for mint in selected
            )
            or selected[0] == selected[1]
        ):
            raise FeedUnavailable("instrument_mapping_invalid")
        self.base_mint, self.quote_mint = selected
        self.url = f"https://api.jup.ag/price/v3?ids={self.base_mint},{self.quote_mint}"
        self.clock = clock
        self.transport = transport or _get_json
        self.timeout = min(_number(timeout), 15)
        self.max_block_idle = _number(max_block_idle)
        self._blocks: dict[str, tuple[int, float]] = {}
        self._last_id: str | None = None

    def poll(self) -> dict | None:
        key = os.environ.get("JUPITER_API_KEY", "")
        if (
            not key
            or key != key.strip()
            or any(ord(c) < 33 or ord(c) > 126 for c in key)
        ):
            raise FeedUnavailable("jupiter_credentials_missing_or_invalid")
        now = _number(self.clock(), positive=False)
        try:
            payload = self.transport(
                self.url,
                {"x-api-key": key, "Accept": "application/json"},
                self.timeout,
                MAX_RESPONSE_BYTES,
            )
        except FeedUnavailable:
            raise
        except Exception:  # noqa: BLE001 - injected provider transports may include secrets in any exception.
            raise FeedUnavailable("provider_unavailable") from None
        if not isinstance(payload, dict):
            raise FeedUnavailable("invalid_market_data")
        prices: dict[str, float] = {}
        blocks: dict[str, int] = {}
        updates = {}
        for mint in (self.base_mint, self.quote_mint):
            entry = payload.get(mint)
            if not isinstance(entry, dict):
                raise FeedUnavailable("instrument_unavailable")
            prices[mint] = _number(entry.get("usdPrice"))
            block = entry.get("blockId")
            if type(block) is not int or block <= 0:
                raise FeedUnavailable("upstream_block_unavailable")
            blocks[mint] = block
            previous = self._blocks.get(mint)
            if previous is not None:
                if block < previous[0]:
                    raise FeedUnavailable("upstream_block_regressed")
                if now < previous[1]:
                    raise FeedUnavailable("clock_regressed")
                if block == previous[0] and now - previous[1] > self.max_block_idle:
                    raise FeedUnavailable("upstream_block_stalled")
            updates[mint] = (
                block,
                now if previous is None or block > previous[0] else previous[1],
            )
        price = prices[self.base_mint] / prices[self.quote_mint]
        _number(price)
        provider_id = _identity(["jupiter_price_v3", self.instrument, blocks, prices])
        self._blocks = updates
        if provider_id == self._last_id:
            return None
        self._last_id = provider_id
        # The upstream response carries no event timestamp. This ID identifies
        # our receipt sample, so a new process observing the same provider state
        # does not claim the old event ID with a different observation clock.
        event_id = _identity([provider_id, now])
        return {
            "source": "jupiter_price_v3",
            "instrument": self.instrument,
            "venue": "jupiter",
            "kind": "polled_reference_ratio",
            "event_id": event_id,
            "observed_at": now,
            "received_at": now,
            "price": price,
            "timestamp_semantics": "local_receipt_upstream_event_time_unknown",
            "upstream_recency_verified": False,
            "provider_block_ids": blocks,
            "provider": "https://api.jup.ag/price/v3",
            "base_usd_price": prices[self.base_mint],
            "quote_usd_price": prices[self.quote_mint],
        }
