---
name: coin-strategy-fit
description: Evaluate one coin or rank a group for spot grid, averaging-down DCA or scheduled accumulation using the 22-field screening template and shared SolTUI quick/audit backtests. Use for coin suitability, explanations or bulk comparison tables; does not place orders or optimize/adopt bot settings.
---

# Coin strategy fit

Apply the same rules as the runnable script and SolTUI Bots tab. Use this repository's backend; do not replace its verdict with an improvised score or confuse an averaging-down bot with scheduled contributions.

## Choose scope and inputs

- Identify the coin(s), bot and mode. Interpret an unspecified “DCA bot” as averaging-down; use `scheduled_dca` for periodic accumulation.
- Use explicit local cached hourly candles. `ALL` means every cached asset, not all coins in the market. Current cache membership does not reconstruct historical listings or delistings.
- Read the current bot configuration and modeled costs in the result. Apply the same funded capital, date window and settings to the group. Do not silently fetch data, alter settings or start services.
- If no data is available, preserve the insufficient-data result and explain which cache is required. An explicitly requested synthetic demo is a software example, never coin evidence.

## Run the shared tool

Resolve this skill's `scripts/coin_strategy_fit.py` relative to this file. It locates the containing SolTUI checkout. Use the existing SolTUI Python environment (NumPy/Pandas); do not assume system Python has dependencies.

```sh
python scripts/coin_strategy_fit.py --coin SOL --bot grid --mode quick
python scripts/coin_strategy_fit.py --coins SOL BTC ETH --bot dca --mode quick --format csv
python scripts/coin_strategy_fit.py --coin SOL --bot grid --mode audit --format json --output coin-audit.json
python scripts/coin_strategy_fit.py --demo --bot all --mode audit
```

Quick ranking scores only the older development slice, leaving the newest quarter (at most thirty days) out of the score. Audit runs three chronological development folds, the reserved newest holdout, a continuous account and doubled-cost scenarios. It uses fixed parameters, not an in-sample configuration search. Previous research may already have inspected the reserved dates; do not call them globally untouched or proof of an independent edge.

For an audit of a ranked row, retain the quick report's configuration, capital, common dates, fees, slippage, selection ID and row data hash. The Bots tab does this automatically. Report any cache change rather than silently changing the test.

## Interpret the result

- `PROVISIONAL_FIT`: the quick historical screen clears its stated heuristics; audit before treating the result as stronger evidence.
- `GOOD_FIT`: the audit's historical simulation criteria pass. This is not live execution approval or a forecast of future profit.
- `POOR_FIT`: at least one stated check fails; explain the measured failure rather than suggesting a forced allocation.
- `INSUFFICIENT_DATA`: the requested common window or essential evidence is unavailable. Keep the row in bulk output.
- Scheduled accumulation also needs an evidenced ownership thesis. A profitable historical path alone cannot establish it. Optional context format is documented in `references/method.md`.

Show the verdict and its scope first. Cite the actual date window, full-capital net return, drawdown, costs, cycles/deals, unresolved inventory, benchmark and failed checks. Read `references/method.md` when explaining thresholds, audit assumptions or missing template fields.

In bulk mode output a table with rank, coin, bot, verdict, score, net return, hold return, drawdown and reason. Keep failed/missing candidates visible. Compare rows within the same bot/mode/window only; do not blend one audited result into a quick leaderboard or infer diversification from ticker count.

All twenty-two template fields appear in each completed row. Distinguish measured, simulated, assumed, provided, unknown and not-applicable evidence. Report missing current depth, asset fundamentals, historical eligibility and shared-budget stress explicitly. Do not relabel unknown fields as passes. The score and thresholds are configurable research hypotheses, not validated optimal parameters.
