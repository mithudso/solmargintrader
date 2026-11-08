"""Quote evaluation: the best route Jupiter finds, checked against an independent price reference.

A quote is only usable when (a) every number is present, (b) its price impact is within `max_price_impact_bps`,
(c) its implied rate is within `max_price_deviation_bps` of the Jupiter Price API (a separate service and data path
from the quote engine), and (d) its slippage cap is within `max_slippage_bps`. A missing price is a refusal.
Deviation is two-sided: a quote far *better* than the reference is as suspect as one far worse.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .config import Config
from .errors import Refused
from .jupiter import Jupiter, Quote
from .tokens import WSOL_MINT, Token, raw_to_ui


@dataclass(frozen=True)
class QuoteReport:
    quote: Quote
    token_in: Token
    token_out: Token
    in_ui: Decimal
    out_ui: Decimal
    min_out_ui: Decimal
    in_usd: Decimal
    out_usd: Decimal
    price_in_usd: Decimal
    price_out_usd: Decimal
    reference_rate: Decimal  # out per in, from the Price API
    quote_rate: Decimal
    deviation_bps: Decimal  # signed: positive = the quote is worse than the reference
    problems: tuple[str, ...]
    fetched_at: float
    sol_price_usd: Decimal | None = None

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict[str, Any]:
        q = self.quote
        return {
            "from": self.token_in.symbol,
            "to": self.token_out.symbol,
            "in_amount": str(self.in_ui),
            "out_amount": str(self.out_ui),
            "min_out_amount": str(self.min_out_ui),
            "in_raw": q.in_raw,
            "out_raw": q.out_raw,
            "min_out_raw": q.min_out_raw,
            "slippage_bps": q.slippage_bps,
            "price_impact_bps": float(round(q.price_impact_bps, 4)),
            "route": [
                {
                    "label": leg.label,
                    "amm": leg.amm,
                    "percent": leg.percent,
                    "from": leg.input_mint,
                    "to": leg.output_mint,
                }
                for leg in q.route
            ],
            "reference": {
                "source": "jupiter-price-api",
                "price_in_usd": str(self.price_in_usd),
                "price_out_usd": str(self.price_out_usd),
                "rate": str(self.reference_rate),
            },
            "quote_rate": str(self.quote_rate),
            "deviation_bps": float(round(self.deviation_bps, 4)),
            "in_usd": str(round(self.in_usd, 6)),
            "out_usd": str(round(self.out_usd, 6)),
            "context_slot": q.context_slot,
            "acceptable": self.ok,
            "problems": list(self.problems),
        }


def evaluate(
    cfg: Config, quote: Quote, token_in: Token, token_out: Token, prices: dict[str, Decimal], now: float | None = None
) -> QuoteReport:
    p_in, p_out = prices.get(token_in.mint), prices.get(token_out.mint)
    if p_in is None or p_out is None:
        missing = [t.symbol for t, p in ((token_in, p_in), (token_out, p_out)) if p is None]
        raise Refused(f"no independent price reference for {', '.join(missing)}; refusing rather than guessing")
    in_ui = raw_to_ui(quote.in_raw, token_in.decimals)
    out_ui = raw_to_ui(quote.out_raw, token_out.decimals)
    ref_rate = p_in / p_out
    quote_rate = out_ui / in_ui
    deviation = (ref_rate - quote_rate) / ref_rate * 10_000
    r = cfg.rails
    problems = []
    if quote.slippage_bps > r.max_slippage_bps:
        problems.append(f"slippage {quote.slippage_bps} bps exceeds max_slippage_bps {r.max_slippage_bps}")
    if quote.price_impact_bps > r.max_price_impact_bps:
        problems.append(
            f"price impact {float(quote.price_impact_bps):.2f} bps exceeds max_price_impact_bps {r.max_price_impact_bps}"
        )
    if abs(deviation) > r.max_price_deviation_bps:
        problems.append(
            f"quote rate deviates {float(deviation):.1f} bps from the price reference "
            f"(limit {r.max_price_deviation_bps} bps)"
        )
    return QuoteReport(
        quote=quote,
        token_in=token_in,
        token_out=token_out,
        in_ui=in_ui,
        out_ui=out_ui,
        min_out_ui=raw_to_ui(quote.min_out_raw, token_out.decimals),
        in_usd=in_ui * p_in,
        out_usd=out_ui * p_out,
        price_in_usd=p_in,
        price_out_usd=p_out,
        reference_rate=ref_rate,
        quote_rate=quote_rate,
        deviation_bps=deviation,
        problems=tuple(problems),
        fetched_at=time.time() if now is None else now,
        sol_price_usd=prices.get(WSOL_MINT),
    )


def fetch_report(
    cfg: Config,
    jup: Jupiter,
    token_in: Token,
    token_out: Token,
    in_raw: int,
    slippage_bps: int,
    now: float | None = None,
) -> QuoteReport:
    if token_in.mint == token_out.mint:
        raise Refused("from and to are the same token")
    allowed = cfg.mint_allowlist()
    bad = [t.symbol for t in (token_in, token_out) if t.mint not in allowed]
    if bad:
        raise Refused(f"{', '.join(bad)} not in rails.allowed_mints")
    quote = jup.quote(token_in.mint, token_out.mint, in_raw, slippage_bps)
    prices = jup.prices(sorted({token_in.mint, token_out.mint, WSOL_MINT}))
    return evaluate(cfg, quote, token_in, token_out, prices, now)
