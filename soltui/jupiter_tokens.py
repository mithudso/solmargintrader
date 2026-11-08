"""Jupiter token discovery. Symbols are never treated as unique mint identities."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.jup.ag"
MINT = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}\Z")


def get(path: str, params: dict[str, str]) -> Any:
    key = os.environ.get("JUPITER_API_KEY", "").strip()
    if not key:
        raise ValueError("JUPITER_API_KEY is required for Jupiter token discovery")
    req = urllib.request.Request(API + path + "?" + urllib.parse.urlencode(params),
                                 headers={"x-api-key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.load(response)
    except Exception as exc:
        raise ValueError(f"Jupiter request failed ({type(exc).__name__})") from None


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
        results.append({"mint": mint, "symbol": symbol[:40], "name": name[:100], "decimals": decimals,
                        "verified": item.get("isVerified") is True})
    return results[:50]


def resolve(query: str) -> dict[str, Any]:
    matches = search(query)
    exact = [x for x in matches if x["mint"] == query or x["symbol"].casefold() == query.casefold()]
    if len(exact) != 1:
        raise ValueError("Token is unknown or ambiguous; choose an exact mint address")
    if not exact[0]["verified"]:
        raise ValueError("Token is not verified by Jupiter")
    return exact[0]
