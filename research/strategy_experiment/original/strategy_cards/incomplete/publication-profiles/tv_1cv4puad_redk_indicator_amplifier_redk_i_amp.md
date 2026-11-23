---

id: tv_profile_1cv4puad

name: "RedK Indicator Amplifier (RedK i-Amp)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "RedK i-Amp wraps another indicator’s output to provide richer visualization and alerts. It does not add independent market analysis; it maps the connected series into an equalizer-like display with gradient intensity, peak hold and configurable levels. Bounded versus unbounded scaling determines whether fixed extreme-level alerts make sense, an important distinction when interpreting the same display across different source indicators."

registry_key: null

runner: null

evaluation: null

---

# RedK Indicator Amplifier (RedK i-Amp)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

RedK i-Amp wraps another indicator’s output to provide richer visualization and alerts. It does not add independent market analysis; it maps the connected series into an equalizer-like display with gradient intensity, peak hold and configurable levels. Bounded versus unbounded scaling determines whether fixed extreme-level alerts make sense, an important distinction when interpreting the same display across different source indicators.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Supplied-series baseline/high/low crossing events is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Read a source plot or built-in preset, select bounded/unbounded and centered/one-direction scaling, and draw blocks from a baseline.
- For unbounded sources, scale against recent extremes or use a fixed block size; detect baseline and fixed extreme-level crossings for markers/alerts.
- For supplied series x and caller baseline,MaxHi,MaxLow levels,each level L produces up when x[t-1]<=L and x[t]>L,and down when x[t-1]>=L and x[t]<L. These six crossing events are independently reproducible;manual levels exclude unknown adaptive scaling,peak-hold decay and external-source parity.

## Outputs and intended use

- Monitor connected indicator changes with peak hold, price-chart flips and an info panel, without treating visual amplitude as a new trading signal.
- Usable scope: Supplied-series baseline/high/low crossing events. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- RSI 14 is default; presets include RSI/Stochastic/CCI/MACD. Six alert types exist and last five hundred flip markers remain visible.
- Unbounded Lookback above one uses adaptive scale and disables Max Hi/Low; Lookback one uses fixed Block Size for real-value levels.

## Failure modes and caveats

- Analytical: adaptive color/block scale can change without equivalent source movement, and source repainting or stale external values propagate through the wrapper.

## Missing information and implementation boundary

- Full scaling equations, peak-hold decay, default preset parameters and bar-confirmation behavior are unspecified.

## Data requirements

Required inputs: caller-selected indicator output, scaling/threshold configuration.

Repository input-class support: unavailable or unresolved. Requires an external indicator series and its intended scale; built-in mode defaults are only partly documented.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
RSI (14) is loaded by default.
```

### E2: parameters, readiness

```text
provides 6 alerts
```

### E3: parameters, readiness

```text
last 500 Flip markers
```

### E4: parameters, readiness

```text
Set Lookback = 1: real values.
```

### E5: parameters, readiness

```text
Max Hi / Max Low are turned off for Unbounded modes with Lookback above 1
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[*]6 alerts: when the indicator's plot crosses the baseline up or down, or crosses the Max Hi / Max Low levels (if supported)
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[*]Flip markers on the price chart when the indicator's plot value crosses its baseline
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_1cv4puad_redk_indicator_amplifier_redk_i_amp](../tv_1cv4puad_redk_indicator_amplifier_redk_i_amp.md)

## Source

https://www.tradingview.com/script/1cv4PUad-RedK-Indicator-Amplifier-RedK-i-Amp/

Publication ID: 1cv4PUad. Source SHA-256: 2b6f7b2172c52252114b452dda1ecd90642b3d1dcddca4ab214bcd1dffd48afc. Raw-description SHA-256: b45dd47128a70b12b00d2f646106a28fc28a892ec96d49af4d48e7e8ed6060d4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
