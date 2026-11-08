---

id: tv_profile_fwb6gwpc

name: "Support & Resistance AI (K means/median) [ThinkLogicAI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Cluster historical price behavior into candidate support/resistance centers and characterize each cluster with density and dispersion."

registry_key: null

runner: null

evaluation: null

---

# Support & Resistance AI (K means/median) [ThinkLogicAI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Cluster historical price behavior into candidate support/resistance centers and characterize each cluster with density and dispersion.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The general iterative method is given, but source features, initialization and convergence/dispersion contracts are unresolved.

- Price versus price-change feature contract
- Center initialization and distance/convergence
- Empty-cluster/dispersion/density equations

## How it works

- Initialize centers,assign observations to the nearest center,recompute means or medians and iterate until centers settle. Draw cluster centers and optional one-standard-deviation bands,with a color-matched density table.

## Outputs and intended use

- Use centers for discretionary reversal/directional scenarios and dispersion bands as proposed stop references. The author illustrates a two-to-one reward/risk example but supplies no validated trading edge.

## Parameters and stated settings

- Choose three-to-five clusters,mean versus median and training lookback; SD-band display is optional. Suggested intraday count is three and daily four/five. A505-day lookback is an illustrative market example,not a universal default.

## Failure modes and caveats

- Initialization,outliers,unequal densities and sample choice affect clusters. The text alternates price-change data and price-level support/resistance without defining their transformation; density alone is not calibrated rejection probability.

## Missing information and implementation boundary

- Input feature/source,center seeds,distance metric,convergence tolerance,empty-cluster handling,SD definition and density denominator are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supports the disclosed technical inputs; missing scoring/algorithm contracts are separate specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
assign data to clusters based on minimum distance
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
calculate cluster center by taking the average or median
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
repeat steps 1-3 until cluster centers stop moving
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
select from 3 to five clusters
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
show the 1 standard deviation bands
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fwb6gwpc_support_resistance_ai_k_means_median_thinklogicai](../tv_fwb6gwpc_support_resistance_ai_k_means_median_thinklogicai.md)
- [tv_method_double_top_bottom](../tv_method_double_top_bottom.md)
- [tv_method_head_shoulders](../../../strategy_research/tv_method_head_shoulders.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_round_number_levels](../tv_method_round_number_levels.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/FwB6GWPC-Support-Resistance-AI-K-means-median-ThinkLogicAI/

Publication ID: FwB6GWPC. Source SHA-256: 43fb0f423fc2c57e72c937ada62715bf95e3c3ece6290e575e084d2cd18dc0a3. Raw-description SHA-256: 9a626d5fbe28dab96c54e5f579981e627654b397ce4edc232c81679ff91a5df2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
