# liquidity state files (contract with soltui)

The liquidity daemon (`aero-lp daemon`) writes these files. `soltui`'s Liquidity tab only **reads**
them; the one exception is the kill-switch file, which soltui may create or delete. soltui never
imports `aero_lp`, web3 or any key material.

The directory is `$AERO_LP_HOME`, and defaults to `~/.aero-lp/`.

Every JSON file is written atomically (temp file + rename), so a reader never sees a half-written
file. Readers must tolerate a missing file, an unknown `schema`, and missing optional keys by showing
"no data" rather than raising.

## `status.json` — schema `aero-lp-status/1`

```json
{
  "schema": "aero-lp-status/1",
  "generated_at": 1762400000.0,
  "mode": "live",
  "killed": false,
  "owner": "0x901a…5314",
  "last_scout_at": 1762390000.0,
  "wallet": {
    "eth": 0.0000926,
    "idle_usd": 45.6,
    "deployed_usd": 0.0,
    "tokens": [{"symbol": "WETH", "address": "0x4200…0006", "amount": 0.0193796, "usd": 43.1, "idle": true}]
  },
  "positions": [
    {
      "slot": "1609324",
      "token_id": 1609324,
      "pool": "0xeC3c…74C2",
      "pair": "WETH/cbBTC",
      "tick_spacing": 1,
      "staked": true,
      "in_range": false,
      "range": [0.0296403, 0.0296847],
      "price": 0.0294201,
      "value_usd": 43.10,
      "deposited_usd": 45.00,
      "withdrawn_usd": 0.0,
      "hodl_usd": 44.00,
      "rewards_usd": 0.0,
      "gas_usd": 0.02,
      "pnl_usd": -1.92,
      "pnl_vs_hodl_usd": -0.92,
      "apr_realized": -12.3,
      "opened_at": 1762300000.0,
      "experiment": null,
      "decision": "skip_unprofitable",
      "reason": "re-entering is expected to lose …"
    }
  ],
  "experiments": [
    {
      "id": "exp-20261106-1",
      "started_at": 1762400000.0,
      "status": "running",
      "winner": null,
      "arms": [{"slot": "1700001", "pair": "WETH/wstETH", "pool": "0x…", "deposited_usd": 20.0, "pnl_usd": 0.05, "pnl_pct": 0.25, "apr_realized": 4.6}]
    }
  ],
  "actions": [{"ts": 1762400000.0, "kind": "rebalance", "slot": "1609324", "detail": "…", "tx": ["0x…"]}]
}
```

- `mode` is either `"live"` or `"dry-run"`.
- `killed` is true while `$AERO_LP_HOME/KILL` exists. The daemon then takes no on-chain action.
- In a position, `range` and `price` are human prices (token1 per token0).
- In a position, `decision` is one of the strategy actions: `hold`, `rebalance`, `wait_confirm`, `wait_cooldown`, `wait_penalty` or `skip_unprofitable`.
- An experiment's `status` is either `"running"` or `"graduated"`.
- `actions` holds the newest 50 entries, newest last. An action's `kind` is one of `rebalance`, `compound`, `deploy`, `withdraw`, `topup`, `unwrap`, `scout`, `skip`, `graduate`, `error`, `claim`, `collect`, `swap`, `register` or `closed`. Readers must show an unknown `kind` as plain text.

## `scout.json` — schema `aero-lp-scout/1`

```json
{
  "schema": "aero-lp-scout/1",
  "generated_at": 1762390000.0,
  "deposit_usd": 50.0,
  "pools": [
    {
      "pool": "0x…",
      "pair": "WETH/wstETH",
      "tick_spacing": 1,
      "tvl_usd": 1200000.0,
      "volume_24h_usd": 3400000.0,
      "turnover": 2.8,
      "fee_pct": 0.01,
      "sigma_daily_pct": 0.05,
      "fee_apr_ref": 3.1,
      "aero_apr_ref": 6.4,
      "lvr_apr_ref": 0.2,
      "edge_ratio": 31.0,
      "best_mode": "aero",
      "best_half_width_pct": 0.4,
      "expected_net_apr": 18.2,
      "rebalances_per_week": 0.6,
      "cost_per_rebalance_usd": 0.03,
      "break_even_deposit_usd": 4.1,
      "staked_share": 0.97,
      "gauge_active": true,
      "confidence": "high",
      "flags": []
    }
  ]
}
```

- The `*_apr_ref` fields are APR % at a reference half-width of +/-10%.
- `edge_ratio` is (fee or AERO income) / LVR. It barely depends on the range width. Above 1 is necessary for profit.
- `expected_net_apr` is the APR % at the optimized width, after LVR and rebalance cost, for `deposit_usd`.
- `confidence` is `high`, `medium` or `low`.
- Pools are sorted by `expected_net_apr`, highest first.

## `providers.json` and `providers-report.md`, written by `aero-lp providers`

Written on demand (not by the daemon), read-only analysis, schema `aero-lp-providers/1`. soltui does not read it yet.
`providers-report.md` is the human version: provider summary, top pools by expected net APR, and how to read them.

Top-level keys: `schema`, `generated_at`, `chain`, `deposit_usd`, `min_net_apr`, `params`, `sources`, `registry`
(factory, position manager and the two sources of each address), `providers` (one summary per provider), `pools`
(ranked rows), `excluded`, `unscored`, `errors`.

Each row in `pools` has:
- `venue`, `project`, `amm_type`, `pool`, `pair`, `fee_pct`, `tvl_usd`, `volume_24h_usd`;
- `tier`: `measured` (read on chain; income is the 24h `feeGrowthGlobal` change) or `quoted` (DefiLlama `apyBase`);
- `income_apr`, `lvr_apr`, `rebalance_cost_apr`, `edge_ratio`, `expected_net_apr` (income - LVR - rebalance cost),
  `replay_net_apr` (measured rows only), `best_half_width_pct`, `break_even_deposit_usd`, `sigma_daily_pct`;
- `quoted_apy_base`: DefiLlama's figure, kept beside the measurement. It is a quote.
- `incentive_apr` and `net_apr_with_incentives`: DefiLlama `apyReward`, separate from income. Absent on an Aero row
  that already counts measured AERO emissions;
- `confidence` (`high`, `medium`, `low`), `clears_bar` (the allocator's rule: measured, model and replay at or above
  `min_net_apr`, edge >= 1.2, confidence at least medium), `flags`;
- `venue_info` and `actionable`: chain id, factory, position manager, pool (or v4 poolId, hooks, StateView) so a later
  change can act on the row. Nothing acts on it today.

Rows are sorted low-confidence last, then by `expected_net_apr`. Any number may be `null`.

## `KILL`

When the file exists, the daemon takes no on-chain action. It keeps writing `status.json` with `killed: true`. Deleting the file resumes normal operation. The file's contents are ignored.
