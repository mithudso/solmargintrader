---

id: tv_profile_ddvp5qaz

name: "Match Finder [theUltimator5]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Match Finder searches a chosen comparison list for the asset whose recent price shape most closely tracks the active chart. It is explicitly about current compatibility, not forecasting continued correlation. After selecting the strongest positive Pearson relationship, it rescales the matched segment for visual comparison, optionally displaying every candidate’s coefficient."

registry_key: null

runner: null

evaluation: null

---

# Match Finder [theUltimator5]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Match Finder searches a chosen comparison list for the asset whose recent price shape most closely tracks the active chart. It is explicitly about current compatibility, not forecasting continued correlation. After selecting the strongest positive Pearson relationship, it rescales the matched segment for visual comparison, optionally displaying every candidate’s coefficient.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Pearson table/strongest-positive match is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate rolling Pearson correlation between chart and comparison ticker segments, excluding self matches, then choose the highest positive correlation.
- Overlay the selected segment with min-max scaling or endpoint-matching rotation and optionally list correlations in a table.
- Over caller N compute r=sum((x-mean(x))*(y-mean(y)))/sqrt(sum((x-mean(x))^2)*sum((y-mean(y))^2)). Exclude self;select largest finite positive r. All-negative,constant/missing series and optional rotation excluded.

## Outputs and intended use

- Inspect which asset/sector has recently tracked the chart; treat the rotated display as adjusted geometry rather than an untouched price series.
- Usable scope: Pearson table/strongest-positive match. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Forty ticker slots default broadly to ETFs. Correlation length defaults to 30 with range 10–500; table is initially off and best-fit line yellow.

## Failure modes and caveats

- The source warns of memory/load/timeouts; analytical: selecting the maximum among many correlated assets inflates apparent fit, and rotation forces additional visual agreement.

## Missing information and implementation boundary

- Handling of all-negative/missing correlations, exact rotation equation, feed alignment and default full ETF set are absent.

## Data requirements

Required inputs: chart and caller-selected comparison closing-price histories.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
list of 40 tickers
```

### E2: parameters, readiness

```text
Default: 30
Range: 10–500
```

### E3: risks, readiness

```text
This effectively rotates the pattern to force it to track the chart to an extent.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[*]Calculates the Pearson correlation between the current symbol and each comparison ticker.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
[*]Identifies the single best-matching ticker (highest positive correlation, excluding the current symbol itself).
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
Default: 30
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ddvp5qaz_match_finder_theultimator5](../../tv_ddvp5qaz_match_finder_theultimator5.md)

## Source

https://www.tradingview.com/script/ddvP5qAZ-Match-Finder-theUltimator5/

Publication ID: ddvP5qAZ. Source SHA-256: 3acaf64ca40a2c0b1ecbbaa5084da0b9b3de755124b58b418836066dbae2fb55. Raw-description SHA-256: b983f6d4eb0475ed48f2c4d30750ffc497fe83420b4ab03ed2b9a992d6b70ed4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
