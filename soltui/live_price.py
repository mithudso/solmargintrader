"""Display-only Jupiter prices. Token symbols never choose an ambiguous mint."""
from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from .jupiter_tokens import MINT

SOL_MINT = 'So11111111111111111111111111111111111111112'


def _get(path: str, params: dict[str, str]) -> Any:
    key = os.environ.get('JUPITER_API_KEY', '').strip()
    base = 'https://api.jup.ag' if key else 'https://lite-api.jup.ag'
    headers = {'Accept': 'application/json'}
    if key:
        headers['x-api-key'] = key
    req = urllib.request.Request(base + path + '?' + urllib.parse.urlencode(params), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.load(response)
    except Exception as exc:
        raise ValueError(f'Jupiter price request failed ({type(exc).__name__}); check Jupiter API access') from None


def jupiter(asset: str, *, get=None, clock=time.time) -> dict[str, Any]:
    get = get or _get
    if asset.upper() == 'SOL':
        mint = SOL_MINT
    elif MINT.fullmatch(asset):
        mint = asset
    else:
        tokens = get('/tokens/v2/search', {'query': asset})
        if not isinstance(tokens, list):
            raise ValueError('Jupiter token lookup returned invalid results')
        matches = {t['id'] for t in tokens if isinstance(t, dict) and
                   str(t.get('symbol', '')).upper() == asset.upper() and MINT.fullmatch(str(t.get('id', '')))}
        if len(matches) != 1:
            raise ValueError('Token symbol is unavailable or ambiguous on Jupiter; use its exact Solana mint')
        mint = matches.pop()
    result = get('/price/v3', {'ids': mint})
    item = result.get(mint) if isinstance(result, dict) else None
    price = item.get('usdPrice') if isinstance(item, dict) else None
    if isinstance(price, bool) or not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
        raise ValueError('Jupiter has no usable USD price for this mint')
    now = clock()
    return {'source': 'jupiter', 'asset': asset, 'mint': mint, 'price': price, 'fetched_at': now,
            'block_id': item.get('blockId'), 'source_timestamp': None,
            'message': 'Jupiter USD reference price; request time is shown. Executable swaps require a route quote.'}
