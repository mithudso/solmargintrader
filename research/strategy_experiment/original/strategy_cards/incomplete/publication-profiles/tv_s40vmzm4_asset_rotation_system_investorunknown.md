---

id: tv_profile_s40vmzm4

name: "Asset Rotation System [InvestorUnknown]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Asset Rotation System compares a user-selected set of assets against USD and against each other, seeking to hold the strongest relative candidate. It presents a trend matrix, hypothetical rotation equity and individual buy-and-hold comparisons. Although published as an indicator, it describes a portfolio-selection concept rather than a single-chart oscillator. Its historical curves are analytical outputs, and the description does not establish realistic transaction timing, costs or an independently verified rotation result."

registry_key: null

runner: null

evaluation: null

---

# Asset Rotation System [InvestorUnknown]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Asset Rotation System compares a user-selected set of assets against USD and against each other, seeking to hold the strongest relative candidate. It presents a trend matrix, hypothetical rotation equity and individual buy-and-hold comparisons. Although published as an indicator, it describes a portfolio-selection concept rather than a single-chart oscillator. Its historical curves are analytical outputs, and the description does not establish realistic transaction timing, costs or an independently verified rotation result.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for selected-source/length RSI50 cross/state comparisons on supplied USD asset and pair-ratio series. All-mode voting, optimal selection, cash/ties and equity metrics remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow RSI matrix: take six caller-selected USD asset source series X_i and aligned ratio sources X_i/X_j. Calculate RSI at the selected source/length for each USD and ratio series. Mark crossing up through 50 when current RSI>50 and previous≤50, crossing down when current<50 and previous≥50; above/below50 gives the corresponding directional state. Exact equality state is unspecified. This matrix does not choose or rotate a portfolio.
- Classify each asset/USD and asset-ratio trend with RSI, CCI, SuperTrend, DMI or PSAR, individually or in an All mode.
- Identify an optimal asset and calculate a system equity curve assuming exclusive investment in that asset.
- Report return dispersion, Sharpe, Sortino, Omega and drawdown alongside individual asset equity.

## Outputs and intended use

- Use the matrix to compare relative trends and confirmed-optimal-asset alerts to notice a possible rotation.
- Calibrate settings cautiously; the author explicitly warns against maximizing historical performance.

## Parameters and stated settings

- Six USD-denominated tickers are selected. Default history is capped at 5000 bars or the youngest asset history, whichever is shorter.
- RSI uses a 50 crossover; indicator lengths/sources, SuperTrend factor and PSAR acceleration settings are configurable.
- Select RSI alone, six USD-denominated tickers, source and RSI length; no default length is disclosed. Inputs are a fixed selected set, not a mandated dynamic universe.

## Failure modes and caveats

- A chosen static asset set can introduce selection bias; synchronization and costs affect rotation results.

## Missing information and implementation boundary

- All-mode voting, optimal-score/tie selection, cash fallback, signal execution lag and performance-metric conventions are missing.

## Data requirements

Required inputs: synchronized OHLCV for six selected USD assets.

Repository input-class support: unavailable or unresolved. The described external or detailed input contract is not available from ordinary chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, required_data

```text
performance of six assets against both the US Dollar and each other.
```

### E2: mechanism, parameters

```text
RSI (50 crossover), CCI, SuperTrend, DMI, and Parabolic SAR.
```

### E3: parameters

```text
5000 bars ago
```

### E4: parameters

```text
inception of the youngest asset included, whichever is shorter.
```

### E5: mechanism, parameters, readiness

```text
RSI (50 crossover)
```

### E6: mechanism, parameters, readiness

```text
both individually against USD and in pairs (assetX/assetY)
```

### E7: mechanism, parameters, readiness

```text
RSI Source: Choose the price data source for RSI calculation.
```

### E8: mechanism, parameters, readiness

```text
RSI Length: Set the period for the RSI calculation.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_s40vmzm4_asset_rotation_system_investorunknown](../tv_s40vmzm4_asset_rotation_system_investorunknown.md)

## Source

https://www.tradingview.com/script/s40vmZM4-Asset-Rotation-System-InvestorUnknown/

Publication ID: s40vmZM4. Source SHA-256: 8d9b5c12c4e57021af63105c33dc7d7212288949d63f2ab2102854e8269e308a. Raw-description SHA-256: 91c06125d2b799f5e5af0a7a83bcb6b5ff763208da8f4cd4006fb8af6c8629c9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
