---

id: tv_profile_fgvtpifr

name: "TF Segmented Linear Regression"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Separate price history into calendar-time intervals and fit a regression channel within each interval to compare local trends and residual variation."

registry_key: null

runner: null

evaluation: null

---

# TF Segmented Linear Regression

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Separate price history into calendar-time intervals and fit a regression channel within each interval to compare local trends and residual variation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the segmented linear-regression centerline on supplied Src and interval partitions; exact WMA/SMA implementation and optional RMSE-channel parity are outside this narrow scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Partition the caller-selected Src observations into successive intervals of the selected higher timeframe, daily by default, and fit a linear-regression centerline separately within each interval. The described endpoint implementation uses a linear combination of WMA and SMA, whose exact coefficients are not printed.
- Optional outer lines sit an RMSE multiple from that fitted centerline. The centerline is a separately usable linear-fit calculation; exact band denominator and endpoint implementation parity remain unresolved.

## Outputs and intended use

- Read slope as local directional structure and width as distance from a linear fit. A wide flat channel can indicate opposing swings that a line describes poorly; a narrow sloped one indicates a cleaner fitted trend.

## Parameters and stated settings

- Interval defaults daily and should exceed the chart timeframe. Source, RMSE multiplier and extremity visibility are selectable; extremities default on. The stated 54-line limit retains 18 three-line channels.

## Failure modes and caveats

- A developing interval is refitted as data arrives. Very large intervals may error, and historical fitted lines do not imply those full-period slopes were known at interval start.

## Missing information and implementation boundary

- Exact WMA/SMA endpoint coefficients, RMSE convention/multiplier default, active-segment update timing and gap handling are not supplied. These limit complete channel parity; no trade execution process is specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed feature uses ordinary price/volume history; this is input-class support rather than verified implementation or data-cache parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Timeframe : Determine the period of the interval
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
by default "Daily"
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Mult : Multiplication factor for the RMSE
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Since the maximum number of lines that can be plotted is 54, using the extremities will only return 18 channels.
```

### E5: mechanism, parameters, readiness

```text
Fit a line at successive intervals, where the interval period is determined by a user-selected time frame
```

### E6: mechanism, parameters, readiness

```text
Src : Input data for the indicator
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fgvtpifr_tf_segmented_linear_regression](../../tv_fgvtpifr_tf_segmented_linear_regression.md)

## Source

https://www.tradingview.com/script/FGvtpiFR-TF-Segmented-Linear-Regression/

Publication ID: FGvtpiFR. Source SHA-256: 389e77b96eceb8ac021dfce0960e0fa4b5b5bb43b7f08b0a80fea3d68a73847f. Raw-description SHA-256: b3df92afbc548721ac6e8bdb38266efbebaeffc9d2b2080b3f8f14d90bc56f39.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
