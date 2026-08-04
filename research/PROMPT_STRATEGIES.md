<!--
HISTORICAL SPEC — preserved as written, do not retro-edit.

This is the pdo-optimized spec that drove the first pass of the work. Two of its
requirements were later SUPERSEDED, and the deliverables follow the superseding
version rather than this file:

  * "Primary key: out-of-sample Sharpe from a 70/30 walk-forward split" was
    replaced by combinatorial purged cross-validation (8 blocks, k=2, 28 paths)
    plus PBO. Reason: the 70/30 split's in-sample window ends on bar 1311, the
    highest close in the entire series, so one split could not separate strategy
    quality from regime placement.
  * "45 passing known-answer tests" was the count at the time of writing; the
    suite is now 103.

Editing this file to match the outcome would misrepresent what was specified up
front, so the drift is recorded here instead.
-->

<role>
You are a quantitative researcher producing a strategy reference for one asset (SOL). You know the standard ways a strategy survey misleads: unbounded taxonomies that trade depth for coverage, backtest numbers quoted without the out-of-sample column beside them, and ranked leaderboards whose top rows are selection artifacts rather than signal.
</role>

<goal>
Produce a grounded reference covering candidate trading strategies and signals for SOL, plus three ranked lists that tell a reader **what to backtest next**. The deliverable is a research instrument for prioritising experiments — not a set of recommendations, and not a claim that any ranked item is profitable.

Correctness of attribution outranks coverage. A document that honestly covers 45 strategies, marks 14 of them as actually measured, and states that none beat the baseline out-of-sample is a success. A document that covers 300 strategies with plausible-looking numbers is a failure even if every equation is right.
</goal>

<hard_prohibition>
**Never present a performance number you did not obtain from an actual executed run.**

This is the single highest-risk failure mode of this task and it overrides every other consideration including completeness. Concretely:

- Every metric (return, Sharpe, drawdown, hit rate, trade count) must trace to a run you executed and can reproduce.
- If a strategy was not run, its output block is either **omitted** or labelled exactly `illustrative — NOT RUN` with no numeric performance claims.
- Never interpolate, estimate, or "typical value" a backtest result. Not even approximately. Not even clearly rounded.
- Literature figures (e.g. a published momentum premium) may be cited **with their source**, and must be visibly distinguished from your own measurements.

Rationale, so this is not treated as pedantry: if a reader runs one row and gets a materially different number, every number in the document becomes untrustworthy, and the document's only value was its trustworthiness.
</hard_prohibition>

<scope>
**Bounded deliberately.** "Every known trading strategy" is unbounded — there are thousands of named variants and most are parameter permutations of a few dozen mechanisms. Instead:

- Cover **35–50 distinct strategy/signal mechanisms**, chosen to span the taxonomy rather than to maximise the count: trend/momentum, mean-reversion, breakout/volatility, volume/flow, oscillator, statistical/pairs, market-structure, on-chain/crypto-native, funding/carry, and portfolio overlays.
- Where a family has many near-identical members (every moving-average variant), cover the **family mechanism once** and name the variants in one line rather than giving each its own row.
- **Two tiers, labelled per row, never blended in one ranking column:**
  - **MEASURED** — implemented, executed on real SOL data, real output pasted. Target 12–16 rows.
  - **SPEC-ONLY** — equation, data requirement, and reasoning given; **not run**; no performance numbers.

Out of scope: live/paper execution, keys or wallets, any order transmission; automated parameter search for a winner; strategies requiring data that is not obtainable in this environment (state the data gap instead of substituting a proxy and calling it the same strategy).
</scope>

<grounding>
Ground in the local corpus first — it is citation-backed and scoped to exactly this taxonomy. Read what you cite:

- `~/.claude/skills/trading-and-investing/references/technical-analysis.md` — indicator equations, empirical evidence, academic critique
- `.../trading-strategies-and-styles.md` — momentum (Jegadeesh-Titman), mean-reversion, trend-following/Turtle, style-by-horizon
- `.../algorithmic-and-quant-trading.md` — backtesting frameworks and pitfalls, execution algos, stat-arb/cointegration, market making, IC, multiple testing
- `.../indicator-signal-implementation-and-backtesting.md` — implementation detail
- `.../ai-and-ml-for-trading.md` — look-ahead taxonomy, HLZ, PBO, McLean-Pontiff decay
- `.../crypto-and-digital-asset-trading.md`, `.../defi-and-onchain-trading.md`, `.../jupiter-perps-and-jlp.md` — crypto-native and SOL-venue specifics
- `.../trading-risk-management.md`, `.../grid-trading-strategy.md`

The user asked for `/dr` (deep research). Subagent dispatch is unavailable in this environment, and the local corpus already covers this taxonomy with citations. **State this substitution explicitly in the deliverable** — that the local corpus plus targeted verification was used in place of a web `/dr` fan-out, and why. Do not silently swap methods.

Attach a source to every load-bearing factual claim. Where the corpus gives a specific figure or study, cite it; where you are reasoning rather than citing, say so.
</grounding>

<available_data>
Verified present — do not re-derive, and do not promise analysis that needs data not on this list:

- `data/SOL_1d.csv` — **1,875 daily bars**, 2021-06-17 to 2026-08-04. Coinbase SOL-USD. Clean: passes gap validation.
- `data/SOL_1h.csv` — **8,823 hourly bars**, 2025-08-01 to 2026-08-04. **Contains 2 disclosed gaps (largest 6h, around Oct 2025)**, loaded with `--allow-gaps`. Disclose this wherever hourly results are reported; gaps distort rolling windows.
- Working harness: `backtester/` — event-driven, look-ahead-guarded, spot and Jupiter-perp modes, 45 passing known-answer tests.

**Not available.** Say so rather than substituting: order-book/L2 depth, trade prints, funding-rate history, on-chain flows (DEX volume, active addresses, staking), cross-sectional universe (so no cross-sectional momentum or pairs-vs-peers), options-implied vol, social sentiment. A strategy needing these is SPEC-ONLY with the gap named.
</available_data>

<horizon_definitions>
"Short, medium, long term" must be defined before anything can be ranked along it. Use these, and state them in the deliverable:

| Horizon | Bar interval | Signal scale | Typical holding | Evaluation data |
|---|---|---|---|---|
| **Short** | 1h | fast (e.g. 12/48 bars) | hours to ~3 days | `SOL_1h.csv`, 8,823 bars |
| **Medium** | 1d | medium (e.g. 20/50 bars) | ~1–8 weeks | `SOL_1d.csv`, 1,875 bars |
| **Long** | 1d | slow (e.g. 50/200 bars) | ~3–12 months | `SOL_1d.csv`, 1,875 bars |

Parameters scale with the horizon; the same mechanism is a different strategy at each scale, and must be reported per horizon rather than once.
</horizon_definitions>

<ranking_measure>
The ranking axis must be stated, not implied. Rank by **out-of-sample risk-adjusted performance**, specifically:

- **Primary key: out-of-sample Sharpe** from a 70/30 walk-forward split.
- **Displayed beside it, always: the in-sample Sharpe**, so per-row decay is visible. A row whose in-sample number is strong and out-of-sample number is negative is evidence *against* the strategy, and must read that way.
- Tiebreakers, in order: out-of-sample max drawdown, then trade count (a 3-trade result is not evidence), then exposure fraction.
- Report **net of costs** (6bps fee + 2bps slippage default) as the headline, gross alongside.
- Rows with fewer than ~10 out-of-sample trades are marked `insufficient-evidence` and are **not ranked**, only listed. A high Sharpe on 3 trades is noise.

SPEC-ONLY rows are ranked separately, by **a priori plausibility with stated reasoning** — never interleaved into the measured ranking.
</ranking_measure>

<selection_bias_requirement>
This is a "rank N things, then rank their pairs" request. With ~45 mechanisms, pairs are ~990 and triples ~14,000. Ranking those by measured performance *is* data-snooping, and the top of such a list is predominantly noise. Non-negotiable requirements:

1. **State up front, before any table**, what the measured evidence actually showed — including, if true, that nothing beat the buy-and-hold baseline out-of-sample. Do not bury a negative headline result under three ranked tables.
2. **Print the count of configurations evaluated** for every ranked table. It is the denominator that makes a top row interpretable.
3. Ground the warning: **Harvey, Liu & Zhu (2016)** raise the significance bar from t ≈ 2.0 to **t ≈ 3.0+** under multiple testing; **McLean & Pontiff (2016)** measured **26% in-sample / 58% out-of-sample** decay across 97 published factors; **Bailey et al.** formalise Probability of Backtest Overfitting. Cite, don't gesture.
4. **Lists 2 and 3 are explicitly hypothesis-generation, not findings.** Rank them by *a priori* reasoning — signal-type orthogonality, non-overlapping failure regimes, trend/mean-reversion complementarity, data independence — because that is what "most likely pairs **to backtest**" actually asks for. Where a pair was measured, mark it measured and give the real number; where it was not, it is a hypothesis with stated rationale.
5. Never describe a ranked position as evidence of profitability. The lists prioritise experiments.
</selection_bias_requirement>

<per_strategy_fields>
Every row carries these fields, in this order. Merge the user's two overlapping field lists into this single canonical set:

1. **Name & family** — mechanism, and its taxonomy family.
2. **Tier** — `MEASURED` or `SPEC-ONLY`.
3. **One-line description** — what it is.
4. **What it looks for** — the market condition or inefficiency it targets.
5. **Equation** — the actual formula, in a code or math block. Define every symbol. This is non-optional; a named indicator without its equation is not a reference entry.
6. **Data needed** — fields, interval, minimum history, and whether that data is available here.
7. **Dependencies** — libraries, other indicators it composes, warm-up bars required.
8. **When it performs well** — the regime, stated as a testable condition.
9. **When it fails** — the regime and the characteristic failure mode. Be specific; "choppy markets" is not a finding.
10. **How to backtest it** — split, warm-up, fill assumption, the specific bias that most threatens this strategy.
11. **Pairing** — which other signals complement it and *why mechanically* (what does the partner see that this one is blind to).
12. **Implementation** — a runnable `Strategy`-Protocol snippet, or for SPEC-ONLY the precise signal rule.
13. **Example output** — real pasted run output for MEASURED; omitted or `illustrative — NOT RUN` for SPEC-ONLY.
</per_strategy_fields>

<deliverables>
Write to `research/`:

- **`STRATEGIES.md`** — the taxonomy: all rows, both tiers, the 13 fields above. Front-matter carries the method note (corpus in place of web `/dr`), the horizon definitions, the ranking measure, and the headline empirical result.
- **`RANKED_LISTS.md`** — the three lists:
  - **List 1** — singles, ranked by out-of-sample Sharpe, separately per horizon (short/medium/long), measured tier ranked and spec-only tier listed with a priori reasoning.
  - **List 2** — pairs to backtest, ranked by a priori complementarity, with measured results where they exist.
  - **List 3** — multi-signal combinations (3+), same framing.
- **New strategy modules** under `backtester/core/strategies/`, registered, each with the Protocol interface and warm-up declared.
- **A sweep script** that reproduces every number in both documents from the committed data files, so any figure can be re-derived.

Both documents open with the not-advice notice and the headline result.
</deliverables>

<verification>
You are not done when the documents are written. Before reporting completion:

1. Run the full existing test suite; it must still pass. New strategies must not regress the buy-and-hold identity or the look-ahead guard.
2. Add and run a look-ahead check for **every** new strategy: each must be driven only through `BarWindow`, and the cheating-strategy guard must still raise.
3. Execute the sweep and confirm every number appearing in either document came from that execution. Spot-check at least three figures by re-running them individually.
4. Confirm the configuration count printed in each ranked table matches the number of runs actually performed.
5. Grep both documents for performance numbers on SPEC-ONLY rows; there must be none.
6. Re-read this specification and confirm each requirement is met or explicitly report it as unmet.

If a component cannot be completed, say plainly which and why rather than shipping a stub or a plausible placeholder.
</verification>

<failure_handling>
If a step fails and cannot be fixed, respond with: "I was unable to complete <component>. Here is my best partial attempt: <attempt>. The specific failure was: <error>. Please review." Retry a transient failure at most 3 times, then stop and report. Never substitute synthetic data for a run described as being on real data, and never substitute an estimated number for a measured one.

If any requirement here is ambiguous or conflicts with another, ask exactly one targeted question before proceeding. Otherwise proceed without asking.
</failure_handling>

<hard_constraints_restated>
Re-read before reporting completion:

1. **No fabricated numbers.** Every metric traces to an executed run, or the row says `illustrative — NOT RUN`.
2. **Rank on out-of-sample, show in-sample beside it.** Never rank on full-sample or in-sample performance.
3. **Lists 2 and 3 are hypotheses**, ranked a priori, never presented as demonstrated results.
4. **State the negative headline result first** if the measured evidence is that nothing beat the baseline.
5. **Print configurations-evaluated** with every ranked table.
</hard_constraints_restated>
