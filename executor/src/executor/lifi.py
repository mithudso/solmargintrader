"""Cross-chain quote, QUOTE ONLY. Nothing here builds, signs or sends a cross-chain transaction.

LI.FI's `/v1/quote` answers without an API key (checked 2026-11-07; unauthenticated use is rate limited). It also
returns a `transactionRequest`; this module drops it on purpose so that no caller can execute from it. Cross-chain
execution is an explicit gap (executor/CLAUDE.md): it needs its own verifier for another chain's transactions.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .config import Config
from .errors import BadParams, Refused
from .http import Http
from .tokens import Token, raw_to_ui

CHAINS = {"base": "BAS", "ethereum": "ETH", "arbitrum": "ARB", "optimism": "OPT", "polygon": "POL"}
SOLANA_CHAIN = "SOL"

# Destination tokens by chain: symbol -> (address, decimals). Native tokens use the zero address.
DEST_TOKENS: dict[str, dict[str, tuple[str, int]]] = {
    "base": {
        "ETH": ("0x0000000000000000000000000000000000000000", 18),
        "USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
    },
    "ethereum": {
        "ETH": ("0x0000000000000000000000000000000000000000", 18),
        "USDC": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
    },
}


def _dec(v: Any, name: str) -> Decimal:
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        raise Refused(f"cross-chain quote field {name} is missing or not a number") from None
    if not d.is_finite() or d < 0:
        raise Refused(f"cross-chain quote field {name} is invalid")
    return d


def quote_cross_chain(
    cfg: Config, http: Http, owner: str, token_in: Token, in_raw: int, to_chain: str, to_ref: str
) -> dict[str, Any]:
    chain = to_chain.lower()
    if chain not in CHAINS:
        raise BadParams(f"unsupported destination chain {to_chain!r} (supported: {', '.join(sorted(CHAINS))})")
    dest = DEST_TOKENS.get(chain, {}).get(to_ref.upper())
    if dest is None:
        raise BadParams(
            f"unsupported destination token {to_ref!r} on {chain} (supported: {', '.join(DEST_TOKENS.get(chain, {}))})"
        )
    address, decimals = dest
    raw = http.get_json(
        f"{cfg.lifi_base_url.rstrip('/')}/v1/quote",
        {
            "fromChain": SOLANA_CHAIN,
            "toChain": CHAINS[chain],
            "fromToken": token_in.mint,
            "toToken": address,
            "fromAmount": str(in_raw),
            "fromAddress": owner,
            "toAddress": cfg.bridge.evm_address,
            "order": "CHEAPEST",
        },
    )
    est = raw.get("estimate") if isinstance(raw, dict) else None
    if not isinstance(est, dict):
        raise Refused("cross-chain quote has no estimate")
    from_usd, to_usd = _dec(est.get("fromAmountUSD"), "fromAmountUSD"), _dec(est.get("toAmountUSD"), "toAmountUSD")
    if from_usd <= 0:
        raise Refused("cross-chain quote has no USD value for the input")
    to_raw, to_min_raw = int(_dec(est.get("toAmount"), "toAmount")), int(_dec(est.get("toAmountMin"), "toAmountMin"))
    if to_raw <= 0 or to_min_raw <= 0 or to_min_raw > to_raw:
        raise Refused("cross-chain quote output amounts are not positive and ordered")
    cost_bps = (from_usd - to_usd) / from_usd * 10_000
    problems = []
    if cost_bps > cfg.bridge.max_cost_bps:
        problems.append(
            f"cross-chain cost {float(cost_bps):.1f} bps exceeds bridge.max_cost_bps {cfg.bridge.max_cost_bps}"
        )
    fees = [
        {"name": str(f.get("name")), "usd": str(f.get("amountUSD"))}
        for f in est.get("feeCosts") or []
        if isinstance(f, dict)
    ]
    return {
        "mode": "quote-only",
        "executable": False,
        "gap": "cross-chain execution is not implemented; this quote only shows the price",
        "from_chain": "solana",
        "to_chain": chain,
        "from": token_in.symbol,
        "to": to_ref.upper(),
        "in_amount": str(raw_to_ui(in_raw, token_in.decimals)),
        "out_amount": str(raw_to_ui(to_raw, decimals)),
        "min_out_amount": str(raw_to_ui(to_min_raw, decimals)),
        "in_usd": str(from_usd),
        "out_usd": str(to_usd),
        "cost_bps": float(round(cost_bps, 2)),
        "tool": str(raw.get("tool")),
        "execution_seconds": est.get("executionDuration"),
        "fees": fees,
        "acceptable": not problems,
        "problems": problems,
    }
