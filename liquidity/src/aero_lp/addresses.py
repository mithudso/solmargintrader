"""Aero contract addresses on Base (chain id 8453).

Every address here appears in two independent sources that agree:
  1. Aero docs "Security Overview" -> "Contract addresses" (https://aero.xyz/docs/security)
  2. github.com/dromos-labs/metadex-slipstream-public deployment-addresses/cl-base.json,
     leaf-base.json (Slipstream v1.1.0, commit cf1ae46, first distributed 2026-10-21)

`chain.verify_deployment()` re-checks at runtime that each address holds contract code and
that the position manager reports the expected factory before live mode signs anything.
"""

from __future__ import annotations

BASE_CHAIN_ID = 8453

# Aero Slipstream (concentrated liquidity)
CL_FACTORY = "0x9CB220581b91b0C83223012FE69688b92aD07a76"
NONFUNGIBLE_POSITION_MANAGER = "0x4857DB576eE0e45F10525eC59527BfD10beeC60b"
SWAP_ROUTER = "0x9Ee35Bf1bd69a03c6F0393582030fCe8Bb93D418"
METAQUOTER = "0x1dDfeC5058180C207F55BB77D95AcDd0d8227868"
CL_GAUGE_FACTORY = "0xf437f62053ACB121665b8fDBfeA8F214FB8E589d"

# Aero core (Base is the root network)
LEAF_VOTER = "0x382409fad8503FbCdbB27A4211551fa03e884078"
AERO_TOKEN = "0x3f5bF3EdAc59d650D8fDf9657a71F2f904A3a4Ee"

# Canonical OP-stack WETH on Base
WETH = "0x4200000000000000000000000000000000000006"

ALL_CONTRACTS = {
    "CLFactory": CL_FACTORY,
    "NonfungiblePositionManager": NONFUNGIBLE_POSITION_MANAGER,
    "SwapRouter": SWAP_ROUTER,
    "CLGaugeFactory": CL_GAUGE_FACTORY,
    "LeafVoter": LEAF_VOTER,
    "AERO": AERO_TOKEN,
}
