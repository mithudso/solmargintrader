# Before and after DSO

Research output, not investment advice; simulation only.

**No measured forecasting improvement.** All 34 registered strategies have identical
before/after directional accuracy on each of the four matched datasets. The two
hourly sizing corrections produce worse net returns on the evaluated temporal
holdout. The experiment leaves the originals and the production registry unchanged.

| Hourly SOL strategy | Directional accuracy old → new | Net return old → new | Sharpe old → new | Maximum drawdown old → new |
|---|---:|---:|---:|---:|
| Volatility target | 46.02% → 46.02% | −11.50% → −12.24% | −2.172 → −2.436 | −24.22% → −24.01% |
| EWMA volatility target | 46.02% → 46.02% | −11.50% → −12.43% | −2.172 → −2.474 | −24.22% → −23.79% |

These are comparisons of corrected economics, not promotions. More realistic
sizing also creates additional resize events and fees. Daily strategy results
remain identical. The hourly tail has 4,410 contiguous real bars; its final 1,323
bars form the evaluation segment. No missing prices were synthesized. The initial
whole-cache refusal remains in `results/initial-gapped-run/`.

## Scope and evidence

- 34 registry defaults × 4 datasets × 2 variants × 2 temporal splits = 544 completed evaluations, zero failed cells in the final run.
- All original core modules, cards and research-only specifications are preserved in 1,822 checksum-bound files. The candidate has 1,823 files, including the cadence helper.
- Auxiliary ladder-grid and DCA simulations ran on all four datasets. Both paired-spread simulations ran and took zero trades. The completed-day triangle replay ran; its small executed-cycle sample is insufficient evidence of an edge. All unchanged mechanisms produced parity.
- The scorecard comparison records all 46 components: 38 can run with the supplied OHLCV data and 8 need missing inputs. Common executable accuracy is 149/318 = 46.86% for both variants, with 11.87% coverage and a 50% active-sample majority baseline.
- The scorecard's native reported accuracy changed from 48.68% to 49.50% because its outcome label was corrected. This is a measurement correction, not improved predictions. Its adaptive learner retains its documented close-to-close target; the report flags that mismatch.
- Research-only specifications and data-dependent components remain explicitly non-executable or insufficiently evidenced. No losing configuration was removed.

## Defects corrected in candidate copies

| Finding | Severity | Correction | Verification |
|---|---|---|---|
| Daily risk annualizer used on hourly bars | Critical | Infer periods per year from visible timestamps for the two volatility-target rules | Daily parity; hourly size ratio sqrt(24); prefix invariance; invalid cadence refusal |
| Cards call the faulty hourly degeneracy valid | High | Retire the faulty interpretation in the two candidate cards | Original cards preserved; archive/hash checks |
| Scorecard reports close-to-close accuracy and net returns as executable | Critical | Score diagnostics from next open to next close and state label basis | Gap example changes 100% false success to 0%; same executable horizon net figure |
| Triangle replay accepts future quote timestamps | Critical | Require finite quote time and nonnegative bounded quote age | Future, stale and nonfinite quotes refused; current quotes still accepted |

## DSO status and metric panel

The two audit bundles enumerate all 273 registry method rows across DI/OV/ST/RR/RB/CE/RA/IF/RP.
Their statuses distinguish executed or static checks, inapplicable methods, missing
inputs, and venue/live-data gaps. Auxiliary review is additional scoped coverage,
not a claim that every method ran for every auxiliary mechanism.

One defect-remediation iteration was followed by candidate regression checks,
matched empirical reruns, and an independent final review. The reports retain
unexecuted significance, perturbation, CPCV/PBO and live-fill requirements. This
run does not claim CLEAN convergence, statistically validated gains, or promotion.
The canonical convergence and promotion contracts are
`/Users/mitch/.claude/skill-consolidation/convergence-and-severity.md` and
`/Users/mitch/.claude/skill-consolidation/champion-challenger.md`.

Computed registry metrics include active accuracy/count/coverage/base rate, realized-event
win rate and count, return, CAGR, Sharpe, Sortino, Calmar, volatility, profit factor,
average win/loss, drawdown and duration, exposure, fees, borrow costs, liquidations,
and equity. Undefined values are JSON null. Full values and conventions are in
`results/results.json`; signed comparisons are in `results/comparison.csv`.
Other metric-only methods requiring resampling, additional labels or source data
remain insufficient evidence. Annualized short-window metrics are descriptive.

## Verification and reproducibility

The baseline backtester suite ran 941 tests with one generated-index failure after
workflow records changed. No strategy test failed. The final suite passed all 960 tests. The independent final reviewer found no
corroborated Medium+ source or provenance defects. Documentation/index gates and
archive-number verification are recorded in `memory.md`. The comparison manifests bind source packages,
runner, common engine, cached inputs, selected periods, costs and splits. Both
source packages remained unchanged during evaluation. Archives verify and expand
in a fresh directory and reject an altered expanded source tree.

No parameter search ran. Historical data and defaults were examined in earlier
research; this temporal split is exploratory rather than independent confirmation.
Accuracy does not establish profitability. These losing corrected results provide
no basis to replace production strategies.

## Rollback

The source archives and original source hash map permit exact recovery. Restore the
candidate distribution without touching production:

```sh
mv research/strategy_experiment/candidate /tmp/strategy-candidate-before-restore
python3 -c 'from research.strategy_snapshots import ensure_snapshots; ensure_snapshots()'
```
