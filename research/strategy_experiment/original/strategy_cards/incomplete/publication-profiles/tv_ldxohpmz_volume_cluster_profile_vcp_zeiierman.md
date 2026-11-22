---

id: tv_profile_ldxohpmz

name: "Volume Cluster Profile [VCP] (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Build a cluster-smoothed volume-by-price map for the current lookback and prior pivot-to-pivot segments. The result emphasizes major concentrations and thin areas, providing discretionary reference zones rather than a literal record of all transactions at each price."

registry_key: null

runner: null

evaluation: null

---

# Volume Cluster Profile [VCP] (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build a cluster-smoothed volume-by-price map for the current lookback and prior pivot-to-pivot segments. The result emphasizes major concentrations and thin areas, providing discretionary reference zones rather than a literal record of all transactions at each price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Nondegenerate current-window enhanced profile/POC is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Scan window extremes, split the range into bins, and assign each bar’s entire volume to its close-price bin. Select local histogram peaks at least as high as immediate neighbors and above average bin volume, retaining the strongest up to a cap.
- For each price bin, sum Gaussian contributions from cluster centers, then divide by the number of retained centers. The largest enhanced bin defines POC at its midpoint.
- Historical swing profiles are stored between pivots; the latest segment’s highest and lowest enhanced-volume bins can extend forward as VA/LV zones. These are extrema, not a conventional percentage value-area calculation.
- For window min/max and B bins,step=(max-min)/B;allocate entire bar volume to clamp(floor((close-min)/step),0,B-1). Retain local peaks>=immediate neighbors and>average bin volume,sorted strongest up to caller cap. Enhanced[b]=sum(centerV*exp(-(b-center)^2/(2*sigma^2)))/center_count. POC is midpoint of maximum enhanced bin. Require nonflat range,positive sigma,at least one center;ties/empty centers and historical pivot segments remain limitations.

## Outputs and intended use

- Current/historical profiles, POC and projected zones support cluster-to-cluster rotation targets and acceptance/rejection observation.
- Single-cluster context is interpreted as bullish above, bearish below and balanced inside; these are author heuristics without a quantified trade test.
- Usable scope: Nondegenerate current-window enhanced profile/POC. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Lookback, bin count, Gaussian sigma, maximum cluster centers, pivot length, retained profiles and display width. Default maximum clusters is two.

## Failure modes and caveats

- Close-only allocation and smoothing can move apparent volume concentrations away from executed-price distribution.
- Flat ranges, no qualifying peaks and tied bins require implementation choices; historical swing confirmation also introduces delay.

## Missing information and implementation boundary

- Pivot confirmation, empty-cluster fallback, endpoint/tie behavior and historical segment inclusion rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Standard historical OHLCV supports close-binned volume analysis.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
volBins[b] += volume[i]
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
if isPeak and v > avgVol
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
enhanced += centerV * math.exp(-(dist*dist) / (2.0 * clusterSigma * clusterSigma))
volBinsAI[b] := enhanced / szClFinal
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
By default, the Volume Cluster Profile (VCP) is configured to detect up to 2 dominant volume clusters
```

### E5: purpose, mechanism, parameters, outputs_and_use, readiness

```text
VA extension = the segment’s highest enhanced-volume bin
```

### E6: purpose, mechanism, parameters, outputs_and_use, readiness

```text
LV extension = the segment’s lowest enhanced-volume bin
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[pine]float step = (maxPrice - minPrice) / binsCount
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
    int b = f_clamp(int(math.floor((close[i] - minPrice) / step)), 0, binsCount - 1)
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
if isPeak and v > avgVol
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[pine]enhanced += centerV * math.exp(-(dist*dist) / (2.0 * clusterSigma * clusterSigma))
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
volBinsAI[b] := enhanced / szClFinal[/pine]
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
[*]POC is plotted at the midpoint price of that bin
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ldxohpmz_volume_cluster_profile_vcp_zeiierman](../tv_ldxohpmz_volume_cluster_profile_vcp_zeiierman.md)

## Source

https://www.tradingview.com/script/lDxohpMZ-Volume-Cluster-Profile-VCP-Zeiierman/

Publication ID: lDxohpMZ. Source SHA-256: 27423f9e5ad57b991d606b7a8b870468af075711196bf21958e0e903f3958708. Raw-description SHA-256: 0cf79a662fa53766e81c570ce2c93d77e75735e531b36df24fb9fd67a92dd223.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
