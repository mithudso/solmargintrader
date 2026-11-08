---

id: tv_profile_y3pnzg2q

name: "Correlation Heatmap"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Correlation Heatmap compares aligned weekly or monthly arithmetic returns across a selected asset list. It aims to support diversification and relationship research while avoiding misleading comparisons caused by different session closing times. The distinctive alignment method reconstructs each other symbol’s price from sum/difference spread series sampled in chart context. All matrix pairs share one common history window, so adding a shorter-lived asset can change correlations even between existing names. Correlation remains descriptive and cannot establish causality or guarantee future diversification."

registry_key: null

runner: null

evaluation: null

---

# Correlation Heatmap

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Correlation Heatmap compares aligned weekly or monthly arithmetic returns across a selected asset list. It aims to support diversification and relationship research while avoiding misleading comparisons caused by different session closing times. The distinctive alignment method reconstructs each other symbol’s price from sum/difference spread series sampled in chart context. All matrix pairs share one common history window, so adding a shorter-lived asset can change correlations even between existing names. Correlation remains descriptive and cannot establish causality or guarantee future diversification.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines substantive parameterized calculations sufficient for reproduction.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Request confirmed sum and difference spreads between chart symbol and each selected ticker, then recover other-symbol price as half their difference.
- Calculate arithmetic returns and retain the common aligned period range.
- Compute Pearson covariance divided by product of standard deviations for each pair.

## Outputs and intended use

- Symmetric correlation table with gradients and sample count supports cross-asset risk inspection.

## Parameters and stated settings

- Monthly returns default; weekly alternative and Max periods cap.
- Published plan-dependent capacities are 20 or 32 symbols, based on two requests per asset; these are source-era limits.
- Chart interval must be at most monthly; requests include extended hours/dividend adjustments and inherited settlement settings.

## Failure modes and caveats

- Spread-derived aligned prices can fall before/after the symbol’s standard close.
- Correlation changes across regimes; zero-variance series need defined handling.

## Missing information and implementation boundary

- Exact unavailable/zero-variance policy and platform spread reconstruction parity remain unverified; core return/correlation equations and alignment contract are disclosed.

## Data requirements

Required inputs: aligned multi-asset prices with spread/session adjustments, selected symbol universe.

Repository input-class support: unavailable or unresolved. External aligned histories and dividend/session modifiers are required; actual feed coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
0.5 * (requestedSum - requestedDifference)
```

### E2: mechanism, readiness

```text
(currentPrice - previousPrice) / previousPrice
```

### E3: mechanism, readiness

```text
𝑟(𝑥, 𝑦) = cov(𝑥, 𝑦) / (𝜎𝑥 * 𝜎𝑦)
```

### E4: parameters

```text
up to 20 symbols
```

### E5: parameters

```text
up to 32 symbols
```

### E6: parameters

```text
default, its value is "1M"
```

### E7: parameters

```text
two
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_y3pnzg2q_correlation_heatmap](../../../strategy_research/tv_y3pnzg2q_correlation_heatmap.md)

## Source

https://www.tradingview.com/script/Y3PnzG2q-Correlation-Heatmap/

Publication ID: Y3PnzG2q. Source SHA-256: 902fadc2c87773e4cbcfd70ced6c5dbbd5a38d8b664be8087112315462468f17. Raw-description SHA-256: 3a490d9985af25743a1370c7709fa9ddd062a7c653cfe95caa49566e2475cd1f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
