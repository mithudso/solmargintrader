---

id: tv_profile_rtofqf13

name: "Trading Activity Index (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trading Activity Index measures whether smoothed price-times-volume is unusual relative to its own recent history. It highlights participation regimes using a log transform, percentile guides and color normalization. The author connects activity with breakout conviction, but the computation measures reported bar activity rather than liquidity depth, trade size distribution or institutional identities."

registry_key: null

runner: null

evaluation: null

---

# Trading Activity Index (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trading Activity Index measures whether smoothed price-times-volume is unusual relative to its own recent history. It highlights participation regimes using a log transform, percentile guides and color normalization. The author connects activity with breakout conviction, but the computation measures reported bar activity rather than liquidity depth, trade size distribution or institutional identities.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Log dollar-volume and percentile references is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Multiply close by volume, smooth with a configurable SMA and log-transform the result.
- Calculate rolling interpolated percentiles and a normalized rank for gradient coloring.
- D=close*volume;A=SMA(D,len_form);vscale=log(A) for A>0. Over caller len_hist compute linearly interpolated20th,40th,60th,80th percentiles. Color rank normalization,feed-volume units and nonpositive-domain behavior remain limitations.

## Outputs and intended use

- Read blue as quieter activity and orange/red as stronger activity; compare activity percentile with price setups instead of treating it as directional prediction.
- Usable scope: Log dollar-volume and percentile references. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Guides use 20/40/60/80 percentiles and color rank spans 0–1. Formation/history windows are configurable without defaults.

## Failure modes and caveats

- Analytical: multiplying volume already reported in quote currency can double-convert units, and log transformation needs positive values. High volume does not prove liquidity or follow-through.

## Missing information and implementation boundary

- Exact 0–1 rank-normalization equation, zero-volume handling, volume units and default windows are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
dlrVol  = close * volume
```

### E2: parameters, readiness

```text
percentile bands (20/40/60/80%)
```

### E3: parameters, readiness

```text
normalized rank (0–1)
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[pine]float dlrVol  = close * volume
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
float dlrVolAvg = ta.sma(dlrVol, len_form)[/pine]
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[pine]float p20 = ta.percentile_linear_interpolation(vscale, len_hist, 20)
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
float p40 = ta.percentile_linear_interpolation(vscale, len_hist, 40)
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
float p60 = ta.percentile_linear_interpolation(vscale, len_hist, 60)
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
float p80 = ta.percentile_linear_interpolation(vscale, len_hist, 80)[/pine]
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[*]The result is log-transformed, compressing large outliers for a more stable signal.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_rtofqf13_trading_activity_index_zeiierman](../tv_rtofqf13_trading_activity_index_zeiierman.md)

## Source

https://www.tradingview.com/script/rtOfqf13-Trading-Activity-Index-Zeiierman/

Publication ID: rtOfqf13. Source SHA-256: 3bc922bc320c46b33af7d0600d426aae2008f2f43eeb1e4a089fafbc60f88204. Raw-description SHA-256: 043cea5758e8464fdbb3a77a2482ae52445827a5e198732889e4d053928249f2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
