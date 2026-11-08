# Four nonlinear lead-lag children: research and testing implications

Version: 2
Delta: v1 to v2; link the completed canonical run and separate remote delivery qualification.
Reviewed: 2026-11-08. Research only; no new market backtest or live trade.
Status: evidence, installed reference and canonical completion accepted. Remote delivery is tracked separately in `nonlinear-lead-lag-children/run-report.md`.

## Findings by concept

The numbered findings below reproduce canonical assertions without changing their wording. Their claim identifiers and source URLs are recorded in `nonlinear-lead-lag-children/claim-index.json`. They concern inference methods and graph representations; this run supplies no measured five-minute SOL trading result.

### Conditional nonlinear information transfer

1. Bivariate TE can reflect indirect influences or shared drivers. Conditioning on relevant observed processes can separate those effects from the source-target dependency; the interpretation is relative to the variables and histories actually included. [1]

2. Interpret TE as a measured directed statistical dependency. A predictive dependency alone does not establish a physical causal mechanism: the estimator study explicitly avoids equating Wiener-style dependency with causal effect, and the high-order TE study distinguishes measured behavior from mechanism. [2]

### Finite-sample dependency uncertainty

3. Finite-sample uncertainty in mutual-information estimates includes systematic bias as well as sampling variability; error bars alone do not establish that an estimate is unbiased. [3]

4. For KSG, ordinary resampling with replacement can create duplicate points that appear to be fine-scale information-bearing structure. Holmes and Nemenman show severe upward bias in such bootstrap estimates; Piras and colleagues reproduce this failure. [4]

5. A surrogate null must match the dependence structure required by the hypothesis. Shorten and colleagues show excessive false positives from naive source time shifts in a common-driver spike-process example; Diks and Fang separately warn that destroying unconditional dependence need not reproduce a conditional-independence null. Their findings concern the tested schemes and processes. [5]

### Lag-selection multiplicity

6. Searching candidate lags and then testing the selected lag as though it were fixed creates a multiplicity problem. Include lag selection in the inferential procedure rather than reporting an unadjusted selected-lag test. [6]

7. A maximum-statistic test mirrors candidate selection: calculate the maximum across candidate surrogate statistics in each surrogate realization, then compare the observed selected maximum against that distribution. The IDTxl paper describes this procedure and its pinned implementation constructs a surrogate table and tests against its maxima. [7]

### Directed graph preservation

8. Symmetrizing a directed adjacency matrix loses edge orientation. For a lead-lag graph, retaining that symmetrized matrix alone therefore cannot preserve which variable leads which; this application is a methodological inference from the graph representations. [8]

9. Bennett, Cucuringu and Reinert describe significance thresholding when constructing a lead-lag network: an edge is retained only when the associated lead-lag metric is sufficiently large. A direction-preserving encoding therefore addresses a different stage from deciding which inferred edges to retain. [9]

10. Bennett, Cucuringu and Reinert report low overall persistence and year-to-year instability in their empirical US-equity lead-lag structure. This is a scope warning for carrying an inferred graph across time; it does not measure five-minute SOL graph stability. [10]

## Proposed experiment

The following is a proposed evaluation design, not a validated trading rule.

1. Freeze the decision-time data, conditioning histories, candidate lags, estimator family and parameter search before evaluation. Keep an untouched chronological test period. Compare the proposed nonlinear feature against own-history and linear baselines.
2. Audit bias, uncertainty and the conditional null separately. Include candidate selection in the significance procedure, and record the complete comparison family. Retain original directed, weighted, lag-labelled graphs alongside transformed representations; evaluate threshold and temporal sensitivity separately from representation fidelity.
3. Accept a trading feature only after testing achievable entry timing, favorable-versus-adverse first passage, abstention and net execution costs. The earlier `FIVE-MINUTE-PERPS.md` describes that broader proposed outcome design. This research does not supply an entry threshold, minimum sufficient sample size, profitable leverage level or guaranteed liquidation buffer.

## Evidence and limits

The final research-gate/v4 packet accepted all 73 assertions: 56 SUPPORTED factual assertions and 17 nonassertions. It includes 49 structured claims and 24 auxiliary assertions. The bounded repair reused 60 validated judgments and reviewed 13 changed assertion/evidence pairs. Independent checks cover three original research groups per child, negative searches, 81 structured spans and 32 bound source snapshots. The structured claim counts are 13 conditional, 13 finite-sample, 7 lag-selection and 16 directed-graph records; overlap among their subject matter is not a count of independent discoveries.

Four exact source-id/hash pairs reuse TASK-808 snapshots. The other 28 are not exact TASK-808 reuse; that does not establish 28 fresh fetches. Acquisition events include within-cohort cache reuse. The public receipt omits private source bodies and judgment transcripts.

Evidence details: `nonlinear-lead-lag-children/accepted-gate-receipt.json`. Standard-depth completion is separate from empirical trading validation and conceptual saturation.

## Sources

[1] Canonical assertion `clm:500221fa4626e00260a077453dff912fdd409f7742b2a2353e8dc29c8bb3f50c`.

https://arxiv.org/abs/nlin/0001042
https://pmc.ncbi.nlm.nih.gov/articles/PMC7517310/
https://pmc.ncbi.nlm.nih.gov/articles/PMC7597255/

[2] Canonical assertion `clm:91e2a00f773fe86214298099300377ea845613b4652c93088846d590b837490b`.

https://arxiv.org/html/2402.03229v4
https://pmc.ncbi.nlm.nih.gov/articles/PMC7597255/

[3] Canonical assertion `clm:073a9ecd78fc0baccc256965a083ef47da3ead5189c01cb1eff591ec7cfdcfa6`.

https://arxiv.org/html/1903.09280
https://arxiv.org/html/2211.00024v2

[4] Canonical assertion `clm:11887efb0eef14fb799f7a2f9181985039e81a457ccd1ad9b428abb17b47f510`.

https://arxiv.org/html/1903.09280
https://arxiv.org/html/2211.00024v2

[5] Canonical assertion `clm:df72010d81b96bfa4d3015a074b17ea5671b7999bca26e854c94a77f6976e7ba`.

https://pmc.ncbi.nlm.nih.gov/articles/PMC8084348/
https://www.mdpi.com/1099-4300/19/7/372

[6] Canonical assertion `clm:bbeb6fccec412364d9d2ea3c7a614000f1f42ae93daf3b875ea9bd967cfab6e6`.

https://pmc.ncbi.nlm.nih.gov/articles/PMC11398661/
https://pmc.ncbi.nlm.nih.gov/articles/PMC6663300/

[7] Canonical assertion `clm:7b2079e146f799a08eaac92b3bf126a4ffc2e5d2ca6094c48079ed0de3ddaca0`.

https://github.com/pwollstadt/IDTxl/blob/master/idtxl/stats.py
https://pmc.ncbi.nlm.nih.gov/articles/PMC6663300/

[8] Canonical assertion `clm:33ea9733b2cb8b368f1f750a9552b53ba4dc76c971e5acbddb313f85d34b80c5`.

https://arxiv.org/html/2411.15527v2
https://pmc.ncbi.nlm.nih.gov/articles/PMC9425115/

[9] Canonical assertion `clm:b2f7779a391f4c7d39b2892f9f628a5ce83f1cc4f45f44f5c617c77fda581a92`.

https://link.springer.com/article/10.1007/s10994-022-06250-4

[10] Canonical assertion `clm:ba73e2324552ae6210b763ef08d227829d9c27af155ad5012c7fff1d4858109e`.

https://link.springer.com/article/10.1007/s10994-022-06250-4
