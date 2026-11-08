"""Jupiter Swap API v1 client (quote + swap) and the Jupiter Price API (the independent reference).

Verified 2026-11-07 against https://dev.jup.ag/docs/swap/get-quote: base URL `https://api.jup.ag` (key via the
`x-api-key` header) and the keyless `https://lite-api.jup.ag`, the host the extension's manifest also lists. Jupiter
now marks the v1 ("Metis") Swap API as no longer actively maintained and superseded by Swap V2. The owner chose v1
on 2026-11-07; moving to V2 is a recorded gap, not a silent change.

Nothing here decides whether a number is acceptable. `parse_quote` only turns a response into a typed object and
refuses one that is malformed or that does not echo the request; limits live in `quote.py` and `rails.py`.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import HttpError, Refused
from .http import Http


@dataclass(frozen=True)
class RouteLeg:
    label: str
    amm: str
    input_mint: str
    output_mint: str
    percent: int


@dataclass(frozen=True)
class Quote:
    input_mint: str
    output_mint: str
    in_raw: int
    out_raw: int
    min_out_raw: int
    slippage_bps: int
    price_impact_bps: Decimal  # Jupiter reports a fraction string ("0.0012" = 0.12%); read conservatively as such
    route: tuple[RouteLeg, ...]
    context_slot: int | None
    raw: dict[str, Any]  # the exact response, which /swap must be given back unchanged


def _int(v: Any, name: str) -> int:
    try:
        if isinstance(v, bool):
            raise ValueError
        n = int(str(v))
    except (TypeError, ValueError):
        raise Refused(f"quote field {name} is missing or not an integer: {v!r}") from None
    return n


def parse_quote(raw: Any, input_mint: str, output_mint: str, in_raw: int, slippage_bps: int) -> Quote:
    """Typed quote. Refuses anything that does not echo the request or lacks a number we need. Never guesses."""
    if not isinstance(raw, dict):
        raise Refused("quote response is not an object")
    if raw.get("inputMint") != input_mint or raw.get("outputMint") != output_mint:
        raise Refused("quote mints do not match the request")
    if raw.get("swapMode") != "ExactIn":
        raise Refused(f"quote swapMode is {raw.get('swapMode')!r}, expected ExactIn")
    got_in = _int(raw.get("inAmount"), "inAmount")
    if got_in != in_raw:
        raise Refused(f"quote inAmount {got_in} != requested {in_raw}")
    out_raw = _int(raw.get("outAmount"), "outAmount")
    min_out = _int(raw.get("otherAmountThreshold"), "otherAmountThreshold")
    if out_raw <= 0 or min_out <= 0 or min_out > out_raw:
        raise Refused("quote outAmount/otherAmountThreshold are not positive and ordered")
    if _int(raw.get("slippageBps"), "slippageBps") != slippage_bps:
        raise Refused("quote slippageBps does not echo the request")
    if raw.get("platformFee"):
        raise Refused("quote carries a platform fee; the executor sets none")
    impact_s = raw.get("priceImpactPct")
    if impact_s is None:
        raise Refused("quote has no priceImpactPct")
    try:
        impact = Decimal(str(impact_s)) * 10_000
    except InvalidOperation:
        raise Refused("quote priceImpactPct is not a number") from None
    if not impact.is_finite() or impact < 0:
        raise Refused("quote priceImpactPct is negative or non-finite")
    plan = raw.get("routePlan")
    if not isinstance(plan, list) or not plan:
        raise Refused("quote has no routePlan")
    legs = []
    for leg in plan:
        info = leg.get("swapInfo") if isinstance(leg, dict) else None
        if not isinstance(info, dict) or not info.get("ammKey"):
            raise Refused("quote routePlan entry is malformed")
        legs.append(
            RouteLeg(
                str(info.get("label") or "?"),
                str(info["ammKey"]),
                str(info.get("inputMint")),
                str(info.get("outputMint")),
                int(leg.get("percent") or 0),
            )
        )
    slot = raw.get("contextSlot")
    return Quote(
        input_mint,
        output_mint,
        in_raw,
        out_raw,
        min_out,
        slippage_bps,
        impact,
        tuple(legs),
        int(slot) if isinstance(slot, int) else None,
        raw,
    )


class Jupiter:
    # The keyless host rate limits hard (429 on a second call within about a second), so calls are spaced out
    # and a 429 is retried a bounded number of times. Every Jupiter call here is idempotent (quote, build, price).
    MIN_GAP_S = 1.1
    RETRIES_429 = 3

    def __init__(
        self, base_url: str, http: Http, api_key: str | None = None, min_gap_s: float | None = None, sleep=time.sleep
    ):
        self.base = base_url.rstrip("/")
        self.http = http
        self.min_gap_s = self.MIN_GAP_S if min_gap_s is None else min_gap_s
        self._sleep = sleep
        self._last = 0.0
        key = api_key if api_key is not None else os.environ.get("JUPITER_API_KEY")
        self.headers = {"x-api-key": key} if key else None

    def _paced(self, fn, *args):
        for attempt in range(self.RETRIES_429 + 1):
            wait = self.min_gap_s - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            self._last = time.monotonic()
            try:
                return fn(*args)
            except HttpError as exc:
                if exc.status != 429 or attempt == self.RETRIES_429:
                    raise
                self._sleep(2.0 * (attempt + 1))

    def quote(self, input_mint: str, output_mint: str, in_raw: int, slippage_bps: int) -> Quote:
        raw = self._paced(
            self.http.get_json,
            f"{self.base}/swap/v1/quote",
            {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(in_raw),
                "slippageBps": str(slippage_bps),
                "swapMode": "ExactIn",
                "restrictIntermediateTokens": "true",
            },
            self.headers,
        )
        return parse_quote(raw, input_mint, output_mint, in_raw, slippage_bps)

    def build_swap(self, quote: Quote, owner: str, max_priority_lamports: int) -> dict[str, Any]:
        """Ask for the serialized transaction. The response is untrusted until `txverify` has passed."""
        body = {
            "quoteResponse": quote.raw,
            "userPublicKey": owner,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "asLegacyTransaction": False,
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {"maxLamports": max_priority_lamports, "priorityLevel": "high"}
            },
        }
        resp = self._paced(self.http.post_json, f"{self.base}/swap/v1/swap", body, self.headers)
        if not isinstance(resp, dict) or not isinstance(resp.get("swapTransaction"), str):
            raise Refused("swap response has no swapTransaction")
        if resp.get("simulationError"):
            raise Refused(f"Jupiter's own simulation failed: {str(resp['simulationError'])[:200]}")
        lvbh = resp.get("lastValidBlockHeight")
        if not isinstance(lvbh, int) or lvbh <= 0:
            raise Refused("swap response has no lastValidBlockHeight")
        return resp

    def prices(self, mints: list[str]) -> dict[str, Decimal]:
        """USD price per mint from the Price API. A mint without a positive price is simply absent."""
        raw = self._paced(self.http.get_json, f"{self.base}/price/v3", {"ids": ",".join(mints)}, self.headers)
        out: dict[str, Decimal] = {}
        if isinstance(raw, dict):
            for mint in mints:
                entry = raw.get(mint)
                try:
                    price = Decimal(str(entry["usdPrice"])) if isinstance(entry, dict) else None
                except (InvalidOperation, KeyError):
                    price = None
                if price is not None and price.is_finite() and price > 0:
                    out[mint] = price
        return out
