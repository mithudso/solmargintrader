"""Token table and exact amount conversion.

Only tokens listed here can ever be traded: decimals come from this table, never from a guess. A mint that is
not here is refused even when it is in the config allowlist, because an unknown decimal count turns a $1 order
into a $1,000,000 one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .errors import BadParams, Refused

WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


@dataclass(frozen=True)
class Token:
    symbol: str
    mint: str
    decimals: int
    stable: bool = False


TOKENS: dict[str, Token] = {
    t.symbol: t
    for t in (
        Token("SOL", WSOL_MINT, 9),
        Token("USDC", USDC_MINT, 6, stable=True),
        Token("USDT", USDT_MINT, 6, stable=True),
    )
}
BY_MINT: dict[str, Token] = {t.mint: t for t in TOKENS.values()}

# The quote asset of every strategy trade: a buy spends it, a sell receives it.
QUOTE_MINT = USDC_MINT


def resolve(ref: str) -> Token:
    """Symbol (case-insensitive) or mint address -> Token. Unknown refs are refused, never guessed."""
    if not isinstance(ref, str) or not ref.strip():
        raise BadParams("a token symbol or mint is required")
    ref = ref.strip()
    tok = TOKENS.get(ref.upper()) or BY_MINT.get(ref)
    if tok is None:
        raise Refused(f"token {ref!r} is not in the executor token table (known: {', '.join(sorted(TOKENS))})")
    return tok


def ui_to_raw(amount: str, decimals: int) -> int:
    """Exact decimal string -> integer base units. Rejects floats, negatives, zero and excess precision."""
    if not isinstance(amount, str):
        raise BadParams("amount must be a decimal string such as '1.25' (a JSON number loses precision)")
    try:
        d = Decimal(amount.strip())
    except InvalidOperation:
        raise BadParams(f"amount {amount!r} is not a decimal number") from None
    if not d.is_finite() or d <= 0:
        raise BadParams("amount must be a positive finite number")
    if type(decimals) is not int or not 0 <= decimals <= 255:
        raise BadParams("token decimals must be an integer in 0..255")
    _, digits, exponent = d.as_tuple()
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    shift = exponent + decimals
    if shift < 0:
        raise BadParams(f"amount {amount!r} has more than {decimals} decimal places")
    # SPL token quantities are uint64. Check the exponent before constructing a
    # power of ten, so an untrusted scientific-notation amount cannot allocate
    # an arbitrarily large integer. No decimal-context rounding is permitted.
    if len(digits) + shift > 20:
        raise BadParams("amount exceeds the token quantity range")
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    raw = coefficient * 10**shift
    if raw >= 2**64:
        raise BadParams("amount exceeds the token quantity range")
    return raw


def raw_to_ui(raw: int, decimals: int) -> Decimal:
    # Tuple construction is exact even when a caller uses a small local context.
    return Decimal((int(raw < 0), tuple(map(int, str(abs(raw)))), -decimals))
