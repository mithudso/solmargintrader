# Strategy comparison experiment — 2026-11-09

Research output, not investment advice; simulation only.

The baseline comes from source commit 898f09611dc65fd8e8457ced29ac05e0b87568db.
The experiment preserves all 34 registered default strategies, all core simulators,
all strategy cards, and research-only strategy specifications. It changes no live
strategy, service, wallet configuration, default parameter, or production registry.

`original.zip` and `candidate.zip` contain complete, separate source trees. They
expand to `original/` and `candidate/` beside this file on the first comparison or
test. The expanded trees remain on disk. Archives avoid indexing thousands of
identical copies in the repository's generated text index. `archives.json` binds
every member and archive by SHA-256. `snapshot.json` binds the baseline to its source
commit. Expansion verifies all members, refuses unsafe archive paths and refuses
to overwrite an altered source tree.

## Reproduce

From the repository root, with the backtester requirements installed:

```sh
python3 research/strategy_compare.py --contiguous-tail
python3 research/strategy_aux_compare.py
python3 -m unittest backtester.tests.test_strategy_candidate backtester.tests.test_candidate_auxiliary backtester.tests.test_strategy_compare -v
```

The current local Python environment is `/Users/mitch/.venvs/soltui/bin/python`.
Data remains in the main checkout's gitignored cache. Result manifests record its
hashes and exact selected periods. A later cache revision is a different experiment.
No command above fetches market data or places orders.

## Read the results

- `results/comparison.md`: all registry strategies, original versus candidate.
- `results/comparison.csv`: signed differences, including accuracy and risk metrics.
- `results/results.json`: complete metric values, accuracy counts and coverage.
- `results/manifest.json`: source hashes, data hashes, splits and execution costs.
- `results/auxiliary.md` and `results/auxiliary.json`: non-registry simulators and indicators.
- `results/initial-gapped-run/`: the retained initial attempt that refused hourly gaps.
- `audit_integrity.md` and `audit_realism.md`: all 273 DSO method statuses and findings.

The comparison uses the same execution engine and costs for both registry variants.
It scores working and temporal holdout periods with fresh capital, causal pre-roll,
and no position carried across the split. The hourly cache has gaps. The explicit
`--contiguous-tail` rule chooses the latest regular suffix by timestamps, before
examining returns, and never interpolates a price or compresses a missing interval.
The original full-cache failure remains visible.

Directional accuracy means signal at close t versus next-bar open-to-close direction.
Flat calls abstain. Active-call counts, coverage and the same-sample majority baseline
matter as much as the percentage. Default registry strategies are long/flat; a high
hit rate can simply reflect bullish bars. Realized-event win rate includes partial
resizes and is not a count of independent round trips. Costed returns, drawdown,
Sharpe and fees are separate measurements. The auxiliary scorecard's native old/new
accuracy changes partly because the defect fix corrects its label; its executable
common-label comparison distinguishes this from a forecasting improvement.

This is the DSO defect track. No parameter search or promotion ran. Historical data
and defaults were previously researched; temporal holdout results are exploratory,
not independent confirmation. Missing robustness, significance, live-fill and data
inputs are explicitly unresolved. The audit does not claim CLEAN convergence or a
validated profitable strategy. Research-only specifications cannot be executed.

## Restore candidate copies

This does not change production. To restore distributed candidates after local edits:

```sh
mv research/strategy_experiment/candidate /tmp/strategy-candidate-before-restore
python3 -c 'from research.strategy_snapshots import ensure_snapshots; ensure_snapshots()'
```
