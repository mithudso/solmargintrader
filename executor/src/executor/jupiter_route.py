"""Strict Borsh layout decoder for the two supported Jupiter V6 ExactIn routes.

Layout source (pinned, not fetched at runtime):
https://github.com/jup-ag/jupiter-amm-implementation/blob/cc068c9d1df0060c62f9a8a4fc37ea13ea7b9b39/idls/jupiter_aggregator_v6.json
IDL blob f554d1c7635b3497c022109fca231a15cb3642bd.

The program's get_minimum_out_amount uses ceil(quoted * (10000-bps)/10000),
per its Swap V6 Offside April 2024 audit:
https://github.com/jup-ag/docs/blob/main/static/files/audits/swap-v6-offside-april-2024.pdf
We deliberately return FLOOR as a conservative lower bound. Requiring that
lower bound to meet the approved minimum cannot admit a weaker program bound.
Nonzero platform fees are unsupported. Unknown enum variants and trailing
bytes are refused, even if a familiar-looking economic tail follows them.
"""

from __future__ import annotations

from dataclasses import dataclass

BPS_DENOMINATOR = 10_000
MAX_PAYLOAD_BYTES = 1232  # Entire supported Solana packet is at most this size.

# Borsh enum ordinal is its position. Each field is consumed by its exact type.
# Keep names to make changes to this pinned protocol schema reviewable.
SWAP_LAYOUTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Saber", ()),
    ("SaberAddDecimalsDeposit", ()),
    ("SaberAddDecimalsWithdraw", ()),
    ("TokenSwap", ()),
    ("Sencha", ()),
    ("Step", ()),
    ("Cropper", ()),
    ("Raydium", ()),
    ("Crema", ("bool",)),
    ("Lifinity", ()),
    ("Mercurial", ()),
    ("Cykura", ()),
    ("Serum", ("side",)),
    ("MarinadeDeposit", ()),
    ("MarinadeUnstake", ()),
    ("Aldrin", ("side",)),
    ("AldrinV2", ("side",)),
    ("Whirlpool", ("bool",)),
    ("Invariant", ("bool",)),
    ("Meteora", ()),
    ("GooseFX", ()),
    ("DeltaFi", ("bool",)),
    ("Balansol", ()),
    ("MarcoPolo", ("bool",)),
    ("Dradex", ("side",)),
    ("LifinityV2", ()),
    ("RaydiumClmm", ()),
    ("Openbook", ("side",)),
    ("Phoenix", ("side",)),
    ("Symmetry", ("u64", "u64")),
    ("TokenSwapV2", ()),
    ("HeliumTreasuryManagementRedeemV0", ()),
    ("StakeDexStakeWrappedSol", ()),
    ("StakeDexSwapViaStake", ("u32",)),
    ("GooseFXV2", ()),
    ("Perps", ()),
    ("PerpsAddLiquidity", ()),
    ("PerpsRemoveLiquidity", ()),
    ("MeteoraDlmm", ()),
    ("OpenBookV2", ("side",)),
    ("RaydiumClmmV2", ()),
    ("StakeDexPrefundWithdrawStakeAndDepositStake", ("u32",)),
    ("Clone", ("u8", "bool", "bool")),
    ("SanctumS", ("u8", "u8", "u32", "u32")),
    ("SanctumSAddLiquidity", ("u8", "u32")),
    ("SanctumSRemoveLiquidity", ("u8", "u32")),
    ("RaydiumCP", ()),
    ("WhirlpoolSwapV2", ("bool", "option_remaining")),
    ("OneIntro", ()),
    ("PumpWrappedBuy", ()),
    ("PumpWrappedSell", ()),
    ("PerpsV2", ()),
    ("PerpsV2AddLiquidity", ()),
    ("PerpsV2RemoveLiquidity", ()),
    ("MoonshotWrappedBuy", ()),
    ("MoonshotWrappedSell", ()),
    ("StabbleStableSwap", ()),
    ("StabbleWeightedSwap", ()),
    ("Obric", ("bool",)),
    ("FoxBuyFromEstimatedCost", ()),
    ("FoxClaimPartial", ("bool",)),
    ("SolFi", ("bool",)),
    ("SolayerDelegateNoInit", ()),
    ("SolayerUndelegateNoInit", ()),
    ("TokenMill", ("side",)),
    ("DaosFunBuy", ()),
    ("DaosFunSell", ()),
    ("ZeroFi", ()),
    ("StakeDexWithdrawWrappedSol", ()),
    ("VirtualsBuy", ()),
    ("VirtualsSell", ()),
    ("Perena", ("u8", "u8")),
    ("PumpSwapBuy", ()),
    ("PumpSwapSell", ()),
    ("Gamma", ()),
    ("MeteoraDlmmSwapV2", ("remaining",)),
    ("Woofi", ()),
    ("MeteoraDammV2", ()),
    ("MeteoraDynamicBondingCurveSwap", ()),
    ("StabbleStableSwapV2", ()),
    ("StabbleWeightedSwapV2", ()),
    ("RaydiumLaunchlabBuy", ("u64",)),
    ("RaydiumLaunchlabSell", ("u64",)),
    ("BoopdotfunWrappedBuy", ()),
    ("BoopdotfunWrappedSell", ()),
    ("Plasma", ("side",)),
    ("GoonFi", ("bool", "u8")),
    ("HumidiFi", ("u64", "bool")),
    ("MeteoraDynamicBondingCurveSwapWithRemainingAccounts", ()),
    ("TesseraV", ("side",)),
)


@dataclass(frozen=True)
class RouteBound:
    kind: str
    steps: int
    amount_in: int
    quoted_out: int
    slippage_bps: int
    minimum_out: int


class _Cursor:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 8

    @property
    def remaining(self) -> int:
        return len(self.data) - self.offset

    def uint(self, width: int) -> int:
        if self.remaining < width:
            raise ValueError("truncated Jupiter route data")
        value = int.from_bytes(self.data[self.offset : self.offset + width], "little")
        self.offset += width
        return value

    def enum(self, choices: int, name: str) -> int:
        value = self.uint(1)
        if value >= choices:
            raise ValueError(f"unsupported Jupiter {name} variant")
        return value

    def remaining_accounts(self) -> None:
        count = self.uint(4)
        if count > self.remaining // 2:
            raise ValueError("invalid Jupiter remaining-account vector length")
        for _ in range(count):
            self.enum(9, "accounts type")
            self.uint(1)

    def field(self, kind: str) -> None:
        if kind == "bool":
            self.enum(2, "boolean")
        elif kind == "side":
            self.enum(2, "side")
        elif kind in ("u8", "u32", "u64"):
            self.uint({"u8": 1, "u32": 4, "u64": 8}[kind])
        elif kind == "remaining":
            self.remaining_accounts()
        elif kind == "option_remaining":
            if self.enum(2, "option"):
                self.remaining_accounts()
        else:  # A schema edit must not silently add an undecoded field.
            raise ValueError("unsupported Jupiter route field")


def decode_route(data: bytes, kind: str) -> RouteBound:
    """Consume a pinned ExactIn layout and return its conservative output bound.

    The caller validates the discriminator before selecting ``kind``. This
    decoder validates every variant on the path to the economic fields. It is
    pure and never loads a network schema or guesses an offset from a tail.
    """
    if kind not in ("route", "shared_accounts_route") or not 8 <= len(data) <= MAX_PAYLOAD_BYTES:
        raise ValueError("unsupported Jupiter route layout")
    cursor = _Cursor(data)
    if kind == "shared_accounts_route":
        cursor.uint(1)  # Shared-account PDA id.
    steps = cursor.uint(4)
    # Four bytes is the smallest RoutePlanStep; reserve the economic fields.
    if not 1 <= steps <= (cursor.remaining - 19) // 4:
        raise ValueError("invalid Jupiter route-plan length")
    for _ in range(steps):
        swap = cursor.enum(len(SWAP_LAYOUTS), "swap")
        for field_type in SWAP_LAYOUTS[swap][1]:
            cursor.field(field_type)
        percent, input_index, output_index = (cursor.uint(1) for _ in range(3))
        if not 1 <= percent <= 100 or input_index == output_index:
            raise ValueError("invalid Jupiter route-plan step")
    amount, quoted, slippage, fee = cursor.uint(8), cursor.uint(8), cursor.uint(2), cursor.uint(1)
    if cursor.remaining:
        raise ValueError("trailing Jupiter route data")
    if fee:
        raise ValueError("Jupiter platform fees are unsupported")
    if amount <= 0 or quoted <= 0 or slippage >= BPS_DENOMINATOR:
        raise ValueError("invalid Jupiter route economic fields")
    minimum = quoted * (BPS_DENOMINATOR - slippage) // BPS_DENOMINATOR
    if minimum <= 0:
        raise ValueError("Jupiter route has no positive minimum output")
    return RouteBound(kind, steps, amount, quoted, slippage, minimum)
