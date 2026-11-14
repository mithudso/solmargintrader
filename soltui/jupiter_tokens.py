"""Jupiter token discovery. Symbols are never treated as unique mint identities."""
from __future__ import annotations

import json
import logging
import math
import os
import re
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.jup.ag"
MINT = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}\Z")
MAX_API_BYTES = 8 * 1024 * 1024
_LOGGER = logging.getLogger(__name__)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ValueError("Jupiter authenticated redirects are refused")


def _authenticated_json(request: urllib.request.Request, timeout: float = 12.) -> Any:
    """Keep API keys on the intended host and bound provider response memory."""
    target = urllib.parse.urlsplit(request.full_url)
    if (target.scheme != "https" or target.hostname not in ("api.jup.ag", "lite-api.jup.ag")
            or target.username or target.password or target.port not in (None, 443)):
        raise ValueError("Unsupported Jupiter API origin")
    _LOGGER.debug("Jupiter API read", extra={"operation": "jupiter.api", "phase": "request"})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_API_BYTES + 1)
        if len(raw) > MAX_API_BYTES:
            raise ValueError("Jupiter API response exceeds the size limit")
        payload = json.loads(raw)
    except Exception as exc:
        _LOGGER.warning("Jupiter API read failed", extra={"operation": "jupiter.api", "phase": "failure",
                                                        "error_kind": type(exc).__name__})
        raise ValueError(f"Jupiter request failed ({type(exc).__name__})") from None
    _LOGGER.debug("Jupiter API read", extra={"operation": "jupiter.api", "phase": "success"})
    return payload


def get(path: str, params: dict[str, str]) -> Any:
    key = os.environ.get("JUPITER_API_KEY", "").strip()
    if not key:
        raise ValueError("JUPITER_API_KEY is required for Jupiter token discovery")
    req = urllib.request.Request(API + path + "?" + urllib.parse.urlencode(params),
                                 headers={"x-api-key": key, "Accept": "application/json"})
    return _authenticated_json(req)


def search(query: str) -> list[dict[str, Any]]:
    query = query.strip()
    if not query or len(query) > 80:
        raise ValueError("Enter a token symbol or mint")
    payload = get("/tokens/v2/search", {"query": query})
    if not isinstance(payload, list):
        raise ValueError("Jupiter returned invalid token search results")
    results = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        mint, decimals = item.get("id"), item.get("decimals")
        if not isinstance(mint, str) or not MINT.fullmatch(mint):
            continue
        if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 18:
            continue
        symbol, name = item.get("symbol"), item.get("name")
        if not isinstance(symbol, str) or not isinstance(name, str):
            continue
        token = {"mint": mint, "symbol": symbol[:40], "name": name[:100], "decimals": decimals,
                 "verified": item.get("isVerified") is True}
        price = item.get("usdPrice")
        if (not isinstance(price, bool) and isinstance(price, (int, float))
                and math.isfinite(price) and price > 0):
            token["usdPrice"] = price
        results.append(token)
    return results[:50]


def resolve(query: str) -> dict[str, Any]:
    matches = search(query)
    exact = [x for x in matches if x["mint"] == query or x["symbol"].casefold() == query.casefold()]
    if len(exact) != 1:
        raise ValueError("Token is unknown or ambiguous; choose an exact mint address")
    if not exact[0]["verified"]:
        raise ValueError("Token is not verified by Jupiter")
    return exact[0]
