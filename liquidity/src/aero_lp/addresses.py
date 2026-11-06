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

# Other venues on Base, read-only (the provider comparison in providers.py never sends to them). Each address has two
# sources: the DEX's own docs or deployment repo, and an on-chain check in `providers.verify_registry`
# (the contract has code, and the position manager's factory() is the factory).
UNISWAP_V3_FACTORY = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"  # docs.uniswap.org .../base-deployments
UNISWAP_V3_NPM = "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1"  # docs.uniswap.org .../base-deployments
PANCAKE_V3_FACTORY = (
    "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"  # developer.pancakeswap.finance/contracts/v3/addresses
)
PANCAKE_V3_NPM = "0x46A15B0b27311cedF172AB29E4f4766fbE7F4364"  # developer.pancakeswap.finance/contracts/v3/addresses
SUSHI_V3_FACTORY = "0xc35DADB65012eC5796536bD9864eD8773aBc74C4"  # sushiswap/v3-periphery deployments/base
SUSHI_V3_NPM = "0x80C7DD17B01855a6D2347444a0FCC36136a314de"  # sushiswap/v3-periphery deployments/base
ALIEN_V3_FACTORY = "0x0Fd83557b2be93617c9C1C1B6fd549401C74558C"  # docs.alienbase.xyz/contracts
ALIEN_V3_NPM = "0xB7996D1ECD07fB227e8DcA8CD5214bDfb04534E5"  # docs.alienbase.xyz/contracts
UNISWAP_V4_POOL_MANAGER = "0x498581fF718922c3f8e6A244956aF099B2652b2b"  # docs.uniswap.org/contracts/v4/deployments
UNISWAP_V4_STATE_VIEW = "0xA3c0c9b65baD0b08107Aa264b0f3dB444b867A71"  # docs.uniswap.org/contracts/v4/deployments
UNISWAP_V4_POSITION_MANAGER = "0x7C5f5A4bBd8fD63184577525326123B519429bDc"  # docs.uniswap.org/contracts/v4/deployments

ALL_CONTRACTS = {
    "CLFactory": CL_FACTORY,
    "NonfungiblePositionManager": NONFUNGIBLE_POSITION_MANAGER,
    "SwapRouter": SWAP_ROUTER,
    "CLGaugeFactory": CL_GAUGE_FACTORY,
    "LeafVoter": LEAF_VOTER,
    "AERO": AERO_TOKEN,
}
