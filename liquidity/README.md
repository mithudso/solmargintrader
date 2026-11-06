# liquidity — Aero Slipstream LP manager

The **liquidity** component of solmargintrader. It manages concentrated-liquidity positions on **Aero**
(aero.xyz) **Slipstream** on **Base**, in one daemon:

- **Measures** each pool's likely profit or loss (below).
- **Scouts** for the pools most likely to be profitable at your deposit size.
- **Rebalances** a position when that pays for itself.
- **Compounds** fees and AERO back into the position.
- **Deploys** idle wallet coins when a pool clears the bar. When candidates are close, it splits the coins into a **side-by-side experiment** and tracks each arm's P&L.

soltui's **Liquidity** tab shows all of it. The tab reads the daemon's state files and nothing else (see
`STATE_FILES.md`).

> Not financial advice. Concentrated liquidity can lose money through impermanent loss,
> loss-versus-rebalancing (LVR), smart-contract risk, and bugs in this program. Code defaults are dry-run.
> Live mode needs `--live` and a signing key.

## How a pool is judged

| Measure | Source | Why it matters |
|---|---|---|
| Fee income per unit liquidity | 24 h change in `feeGrowthGlobal` (CLPool credits it per unit of *unstaked* in-range liquidity, net of the unstaked fee) | Includes dynamic fees, router discounts and MEV capture. Volume × quoted fee overstated it about 5× on WETH/cbBTC. |
| AERO income per unit staked liquidity | 24 h change in `LeafVoter.projectedCumulativeRewardShare(gauge)` | What the gauge actually emitted, not a quoted APR. |
| σ of the pair's price ratio | GeckoTerminal hourly closes, using **overlapping 24 h returns** | Hourly scaling counts bid-ask bounce 24 times and overstates σ on pegged pairs. |
| LVR | σ²/(8·(1−e^(−w/2))) of value per day for a ±w range | The cost of trading against informed flow. It grows as the range narrows. |
| Rebalance cost | Measured gas (Base L2 + L1 data fee), swap fee and impact on about half the value, times σ²/w² rebalances per day | It decides how narrow a small position can go. |
| **Edge ratio** | income / LVR | Barely depends on width. Below 1, no passive range is profitable. |
| **Model net APR** | best width's income − LVR − rebalance cost, for your deposit size | The forward-looking estimate. |
| **Backtest net APR** | the pool's actual hourly path replayed at 12 widths, against holding the pair | Sees mean reversion that the LVR formula charges as loss. |
| Break-even deposit | smallest size whose income covers gas at that width | Small positions die by gas. |
| Context flags | TVL, turnover, staked share, gauge status, token allow-list, history length | These set confidence. |

The allocator deploys only into a pool where **both** the model and the backtest clear `min_net_apr`
(default 5%). The pool must also have edge ≥ 1.2, at least medium confidence, TVL ≥ $100k and allow-listed
tokens. When candidates score within 30% of the best, it runs a side-by-side experiment of up to 3 arms.
After 7 days it closes any arm that trails the winner by at least 5% APR.

**Finding as of 2026-11-06:** no Aero pool cleared that bar for a deposit of about $50.
- Volatile pairs lose to LVR: WETH/cbBTC is −3% to −4% on both measures.
- Pegged pairs (LST/ETH, USDC/USDT) sit at about 0%, because 1-tick professional liquidity takes nearly all the income.

The daemon therefore holds your coins and rescans every 6 h. That is the intended behaviour.

## Quick start

```bash
cd /Users/mitch/dev/solmargintrader/liquidity
uv sync --extra dev -p 3.13

.venv/bin/aero-lp verify                                  # contract addresses + RPC freshness
.venv/bin/aero-lp scout --deposit-usd 50                  # rank pools; writes ~/.aero-lp/scout.json
.venv/bin/aero-lp positions --owner 0xYOU --pool 0xPOOL   # find a position's token id
mkdir -p ~/.aero-lp && cp config.example.toml ~/.aero-lp/config.toml   # set owner, key_file, caps
.venv/bin/aero-lp daemon -c ~/.aero-lp/config.toml --once # one dry-run tick
.venv/bin/aero-lp pnl                                     # per-position P&L from the ledger
```

Run it as a service (launchd, restarts on crash, logs to `~/.aero-lp/daemon.log`):

```bash
scripts/aero-lp-service install            # live; `install --dry-run` for plans only
scripts/aero-lp-service status | logs
scripts/aero-lp-service kill | resume      # pause / resume every on-chain action
scripts/aero-lp-service uninstall
```

The research agent `.claude/agents/aero-pool-scout.md` (repo root) gives a skeptical second opinion. It reruns
the scout, checks the top candidates' tokens and numbers against independent sources, and writes
`~/.aero-lp/scout-review.md`. It never signs.

## What each loop does (`aero-lp daemon`)

1. **Kill switch.** While `~/.aero-lp/KILL` exists, the loop takes no on-chain action. It still reads state and writes status.
2. **Wallet snapshot.** It records balances in the ledger. A coin counts as *idle* only if it stayed in the wallet for `idle_window_hours` (24 h), so coins you are trading by hand are left alone.
3. **Positions.** It evaluates each position and rebalances when the strategy says so:
   - the price is out of range, or has stayed in the edge buffer for the confirm count;
   - the cooldown has passed;
   - the benefit is more than 1.5× the cost;
   - and LVR is accounted for.
4. **Compounding** (hourly):
   - A staked position claims AERO, swaps it into the pool's tokens via the deepest direct pool, then unstakes, increases liquidity and restakes.
   - An unstaked position collects its fees and adds them back.
   - Either happens only when the reward is at least `max($1, 10 × gas)` and the gauge penalty window has passed.
5. **Scout** (every 6 h). It scores the top pools by volume, plus every pool of the curated pegged pairs, and writes `scout.json`.
6. **Allocate** (hourly):
   - It unwraps a little WETH when native ETH drops below the gas reserve.
   - It deploys idle coins into the qualifying pool or experiment.
   - It graduates finished experiments.
7. **Status.** It writes `status.json` for soltui.

## Safety

Everything from the original bot applies:
- every rebalance is simulated first with `eth_simulateV1`;
- it spends only the funds that came out of the position, or the funds designated for that operation;
- slippage minimums apply on every swap, remove and mint;
- the priority fee is capped under Slipstream's MEV-fee threshold;
- the TWAP and stale-RPC guards fail closed;
- live mode enforces the size and gas caps and an ETH reserve;
- Ctrl-C is held until an in-flight sequence finishes;
- the new token id is persisted as soon as the mint lands.

The daemon adds these:
- the idle window, so it never grabs coins you just moved;
- the allow-list of tokens;
- `max_position_usd` and `max_total_deployed_usd`;
- the kill switch;
- dry-run code defaults. A fresh install never signs.

## Layout

| Path | Role |
|---|---|
| `src/aero_lp/metrics.py` | Every profitability measure for one pool |
| `src/aero_lp/scout.py` | Candidate discovery + ranking → `scout.json` |
| `src/aero_lp/allocator.py` | Pure deploy / experiment / graduation decisions |
| `src/aero_lp/ledger.py` | SQLite P&L ledger: slots, flows, events, snapshots, wallet history |
| `src/aero_lp/daemon.py` | The loop: manage, compound, scout, allocate, status |
| `src/aero_lp/executor.py` | Transaction sequences: rebalance, withdraw, deploy, topup, claim, collect, swap, unwrap |
| `src/aero_lp/engine.py` | Per-position evaluation, decision and safety gates |
| `src/aero_lp/strategy.py` | Width optimizer, LVR model, rebalance decision (pure) |
| `src/aero_lp/chain.py`, `market.py` | Multicall3 chain reads, GeckoTerminal data, earnings model |
| `src/aero_lp/clmath.py`, `abi.py`, `addresses.py` | Tick math, ABIs, contract addresses (two agreeing sources) |
| `STATE_FILES.md` | Contract with soltui's Liquidity tab |
| `scripts/aero-lp-service` | launchd install / status / kill |

## Tests

```bash
.venv/bin/pytest -q            # offline
.venv/bin/pytest -q -m network # live Base reads + a full rebalance simulated on a real staked position
```

This component uses pytest in its own virtualenv. It is separate from the repo's unittest suites, the same way
`extension/` has its own node tests.
