# aero-lp

Automated range manager for **Aero** (aero.xyz) **Slipstream** concentrated-liquidity deposits on **Base**.

It watches your deposit, decides when re-centring the price range pays for itself, and rebalances:
unstake from the gauge, withdraw, swap to the right token ratio, mint the new range, and re-stake. It
also chooses between earning **AERO rewards** (staked) and **trading fees** (unstaked) by expected net yield.

Dry run is the default. In dry run, every rebalance is simulated end to end with `eth_simulateV1`
against live Base state. Nothing is signed or broadcast until you pass `--live`.

> Not financial advice. Concentrated liquidity can lose money: impermanent loss, loss-versus-rebalancing (LVR),
> smart-contract risk, and bugs in this program. Start with a small position in a dedicated wallet.

## How it decides ("maximum profit", not just "always in range")

Keeping a deposit in range is easy: rebalance whenever price leaves. That is not the same as making money.

| Term | What it is | Model used |
|---|---|---|
| Income | Trading fees (unstaked) or AERO emissions (staked), per $ while in range | On-chain pool fee, 24h volume (GeckoTerminal), gauge emissions from `LeafVoter.projectedCumulativeRewardShare`, your share of active or staked liquidity |
| LVR | The cost of trading against better-informed flow; grows as the range narrows | `sigma^2 / (8 * (1 - e^(-w/2)))` of position value per day for a +/-w range |
| Rebalance cost | Gas, swap fee and price impact on the swapped share, plus the gauge early-exit forfeit | Measured gas (~1.9-2.6M gas, about $0.09 on Base), pool fee, `effectivePenaltyConfig(gauge)` |

Volatility (`sigma`) comes from 72 hourly GeckoTerminal closes. If that fails, it falls back to the pool's
on-chain oracle (10-minute windows, corrected for the smoothing of window averages). With neither, widths fall
back to `fixed_half_width_pct`.

`width_mode = "optimal"` scores 40 range widths and picks the one with the highest
`income - LVR - expected rebalances * cost`. A rebalance happens only when the price is out of range,
or has stayed in the outer edge buffer for `confirm_checks` checks, the cooldown has passed, and the
expected gain over the horizon beats `benefit_cost_ratio` x the cost.

Because income and LVR both scale with concentration, the sign of the edge barely depends on the width.
If income is below LVR at every width, the bot says so (`expected edge is negative at every width`).
It also will not pay to re-enter the range when re-entering is expected to lose.
Set `lvr_weight = 0` if you want "always back in range" regardless.

At the time of writing (2026-11-05), WETH/USDC on Aero showed **negative expected edge at every width**:
about 3.6% daily volatility against a 0.7-3.8% income APR for a wide range. The 15-day backtest agreed,
because every tight range lost to holding. Run `aero-lp backtest` on your pool before committing capital.

## Quick start

```bash
cd aero-liquidity   # the directory this README is in
uv sync --extra dev -p 3.13

.venv/bin/aero-lp verify                     # contract addresses + RPC freshness
.venv/bin/aero-lp pools                      # top Aero Slipstream pools on Base
.venv/bin/aero-lp positions --owner 0xYOU --pool 0xPOOL   # staked positions need the pool address
.venv/bin/aero-lp backtest --pool 0xPOOL --widths 1,2,4,8,15,30 --mode aero

cp config.example.toml config.toml           # set owner + token_ids
.venv/bin/aero-lp status -c config.toml      # state, economics, decision (read-only)
.venv/bin/aero-lp simulate -c config.toml --force   # full rebalance via eth_simulateV1
.venv/bin/aero-lp run -c config.toml --once  # one dry-run cycle
.venv/bin/aero-lp withdraw -c config.toml --token-id N   # simulate exiting a position to the wallet (--live to do it)
```

### Going live

1. Create a dedicated wallet. Move only the position you want managed into it.
2. Store its key in the macOS Keychain, or set `key_file` in the config to a file you own with mode 600 (the bot refuses a key file another user can read).
   Keychain: `security` prompts for the value, so the key stays out of shell history:
   ```bash
   security add-generic-password -s aero-lp -a 0xyour-owner-address-lowercase -w
   ```
3. Set `safety.max_position_usd` and `safety.max_gas_usd` deliberately.
4. Start the bot:
   ```bash
   .venv/bin/aero-lp run -c config.toml --live
   ```

Live mode first re-verifies the contract addresses and RPC freshness. It loads the key and checks that
the key controls `owner`. For each rebalance it simulates the whole sequence, checks the simulated gas against
`max_gas_usd`, re-reads the position, owner, RPC freshness and TWAP deviation, and only then sends the
transactions. Each transaction is sent only after `eth_estimateGas` succeeds.

## Safety

- **Dry run is the default.** Live mode needs `--live` plus a key whose address equals `owner`.
- **The bot spends only the position's own funds.** Every amount is a wallet-balance delta measured from the start of the rebalance. Other tokens in the wallet are never used.
- **Slippage protection.** Every remove, swap and mint sets min-amounts (`max_slippage_bps`). The mint is sized on the post-swap pool price.
- **MEV fee.** Slipstream charges an extra fee on trades whose priority fee exceeds a threshold, so the priority fee is capped (`max_priority_fee_gwei`, default 0.001).
- **Manipulation guard.** A round is skipped when spot is more than `max_twap_deviation_bps` from the 10-minute TWAP. In live mode a round is also skipped when the TWAP cannot be read (short oracle history or an RPC error), and the check repeats on fresh state just before sending.
- **Mid-sequence drift guard.** If spot moves more than `max_stage_drift_bps` (default 100, about 1%) between the pre-send check and the end of the remove stage, the bot stops before swapping and leaves the tokens in the wallet. This stops a price pushed between the TWAP check and the swap from setting the swap's min-out.
- **Crash-safe tracking.** The new token id is written to the state file as soon as the mint lands, before the stake step runs. Ctrl-C during a live rebalance is held until the sequence finishes. A second Ctrl-C forces quit.
- **Stale RPC guard.** Refuses an RPC whose head block is more than 90 s old. One public endpoint tested was hours behind.
- **Gauge early-exit forfeit.** The live config is `minStakeBlocks = 70`, `penaltyRate = 100%`, so exiting within about 140 s of staking forfeits all unclaimed AERO. The bot waits the window out when waiting is cheaper than the penalty.
- **Size and gas caps.** `max_position_usd` and `max_gas_usd` block live rebalances above your limits. The gas cap is checked against both the config estimate and the simulated gas. If a USD price (either pool token or ETH) is unavailable, live mode blocks the rebalance, because neither cap can be enforced without prices.
- **Failure handling.** If a step fails mid-sequence, the bot stops that rebalance and prints the completed stages, the new token id (if one was minted) and every transaction hash. In live mode it writes the same record to the state file. Funds stay in your wallet. What happens next depends on how far it got:
  - Before the old NFT was burned (including after the unstake step): the next cycle re-reads the position and decides again.
  - After the mint, if only the stake step failed: the bot tracks the new, unstaked NFT from then on.
  - After the burn but before the mint: the old token id no longer exists, so that slot errors with "position does not exist" on every cycle. The tokens sit in your wallet. The bot does not re-mint them on its own. Mint a new position by hand and put its token id in `token_ids`.
- **Read-after-write.** After each transaction, balances and price are read at that transaction's block. A lagging RPC node causes a retry and then an error. Nonces are tracked locally and gas estimates are retried, so a node one block behind does not break a multi-transaction stage. Before sending, live mode also requires an ETH reserve of 3x the simulated gas, a position read no older than 90 s, and a price still inside the proposed range.

## Verified facts this relies on

- Contract addresses come from two sources that agree: the Aero docs Security page and the `deployment-addresses/cl-base.json` file in `github.com/dromos-labs/metadex-slipstream-public` (v1.1.0). See `src/aero_lp/addresses.py`.
- `NonfungiblePositionManager.mint` takes `tickSpacing` and `sqrtPriceX96`, not a fee tier. The gauge uses `deposit`/`withdraw(tokenId)` and `claimEmissions(account, recipient, tokenIds[])`.
- The live `CLFactory.tickSpacings()` returns `[1, 10, 50, 100, 150, 200, 250]`. The docs table also lists CL2000, but the factory does not.
- Staked deposits earn AERO, and their swap fees go to Token Operators. Unstaked deposits keep fees minus `unstakedFee` (currently 5%).

## Layout

| Path | Role |
|---|---|
| `src/aero_lp/clmath.py` | Exact tick/sqrt-price/liquidity math, fee growth, ratio swap |
| `src/aero_lp/strategy.py` | Range sizing, LVR model, width optimizer, rebalance decision (pure) |
| `src/aero_lp/chain.py` | Multicall3 reads: pools, positions, gauges, emissions |
| `src/aero_lp/market.py` | GeckoTerminal prices, volume, OHLCV; earnings model |
| `src/aero_lp/executor.py` | Transaction sequence; `SimRunner` (eth_simulateV1) and `LiveRunner` (sign + send) |
| `src/aero_lp/engine.py` | Glue: evaluate -> decide -> simulate -> execute; state tracking |
| `src/aero_lp/backtest.py` | Hourly width backtest with exact CL value path |
| `src/aero_lp/cli.py` | `aero-lp` command |
| `src/aero_lp/config.py` | TOML loading and validation (`strategy`, `execution`, `safety` tables) |
| `src/aero_lp/state.py` | JSON state file: current NFT per slot, hysteresis counters, rebalance history |
| `src/aero_lp/wallet.py` | Signing-key loading (Keychain or `AERO_LP_PRIVATE_KEY`); never prints or logs the key |
| `src/aero_lp/abi.py`, `addresses.py` | Minimal contract ABIs and the verified Base addresses |

## Tests

```bash
.venv/bin/pytest            # offline unit tests
.venv/bin/pytest -m network # live Base reads + full rebalance simulation on a real staked position
```
