---

id: tv_profile_mdgjq4j5

name: "Simplified Percentile Clustering"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Simplified Percentile Clustering creates deterministic regime centers from percentiles and a mean instead of iterative k-means. It can classify one indicator or fuse several normalized indicators by their distances to corresponding centers, then interpolate toward the next closest regime. This is a clustering heuristic for interpreting market state, explicitly not a buy/sell model or forecast."

registry_key: null

runner: null

evaluation: null

---

# Simplified Percentile Clustering

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Simplified Percentile Clustering creates deterministic regime centers from percentiles and a mean instead of iterative k-means. It can classify one indicator or fuse several normalized indicators by their distances to corresponding centers, then interpolate toward the next closest regime. This is a clustering heuristic for interpreting market state, explicitly not a buy/sell model or forecast.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Standalone percentile centers/distance interpolation is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Build low/high centers halfway between lower/upper percentiles and mean, adding the mean as a middle center when selected.
- Average distances across enabled RSI/CCI/Fisher/DMI/Z-score/price-to-MA features and choose the closest combined center.
- Interpolate nearest and second-nearest cluster values using their distance ratio to show proximity transitions.
- For supplied feature/window compute low_pct,high_pct and mean mid. K=2 centers=((low_pct+mid)/2,(high_pct+mid)/2);K=3 adds mid between them. Given distances d1,d2 to the closest and second-closest feature-space centers, and their assigned cluster label/index values c1,c2,rel_pos=d1/(d1+d2);real_clust=c1+(c2-c1)*rel_pos. The interpolated output is in cluster label/index units, not feature-space centroid magnitudes. Require nonzero distance sum;feature fusion and normalization remain excluded.

## Outputs and intended use

- Inspect colored regime histograms, bar colors and continuous transition line; use as an interpretable research feature or adaptive-filter context.
- Usable scope: Standalone percentile centers/distance interpolation. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Two or three clusters are supported; lookback, percentile cutoffs and feature toggles/standardization are configurable without full defaults.

## Failure modes and caveats

- Analytical: correlated features receive repeated influence, standardization choices alter distance and the prose’s 0/0.5/1 transition interpretation does not directly follow its nearest-distance ratio.

## Missing information and implementation boundary

- Feature variants/lengths, exact distance metric, normalization, tie behavior and zero-enabled-feature handling are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
K Clusters (2–3)
```

### E2: mechanism, readiness

```text
[k0, k1] = [avg(low_pct, mid), avg(high_pct, mid)]
```

### E3: mechanism, risks, readiness

```text
rel_pos = min_dist / (min_dist + second_min_dist)
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[k0, k1] = [avg(low_pct, mid), avg(high_pct, mid)]
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
[k0, k1, k2] = [avg(low_pct, mid), mid, avg(high_pct, mid)][/pine]
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[pine]rel_pos = min_dist / (min_dist + second_min_dist)
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
real_clust = cluster_val + (second_val - cluster_val) * rel_pos[/pine]
```

### E8: mechanism, outputs_and_use, readiness

```text
rel_pos = min_dist / (min_dist + second_min_dist)
real_clust = cluster_val + (second_val - cluster_val) * rel_pos
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mdgjq4j5_simplified_percentile_clustering](../tv_mdgjq4j5_simplified_percentile_clustering.md)

## Source

https://www.tradingview.com/script/mdGJq4j5-Simplified-Percentile-Clustering/

Publication ID: mdGJq4j5. Source SHA-256: af072d690a306ad26372a68a07d82e91d352e21db33c37d6771b264b6aa46ce3. Raw-description SHA-256: bdbb2cbca43c33b62292fb4638a7c11c5e1fcbf34fe806f68f067e33eed319d7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
