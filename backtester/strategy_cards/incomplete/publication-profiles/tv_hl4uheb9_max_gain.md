---

id: tv_profile_hl4uheb9

name: "Max Gain"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare recent rally and selloff magnitudes to develop discretionary price-target hypotheses from historical excursion sizes."

registry_key: null

runner: null

evaluation: null

---

# Max Gain

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare recent rally and selloff magnitudes to develop discretionary price-target hypotheses from historical excursion sizes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines the current-high/prior-low gain and inverse recovery interpretation for the current-low/prior-high loss, including the lookback and a numerical recovery example.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Measure gain from a prior-window low to the current high and loss from a prior-window high to the current low. Transform the loss side into an equivalent recovery-gain scale for visual comparison, while retaining an optional actual-loss plot.

## Outputs and intended use

- Green and red curves compare opposing movement magnitudes. Historical repeated percentage regions are used as target references, but they do not imply attainable trade returns.

## Parameters and stated settings

- The default window is thirty periods and can be changed or applied to other chart intervals. Actual loss is hidden by default; the author suggests swapping plot choices for bear-market analysis.

## Failure modes and caveats

- The adjusted red curve is intentionally not actual percentage loss. The author acknowledges incorrect absolute-loss interpretation during unusual directional moves. Rolling extrema do not necessarily correspond to tradable timed entries/exits.

## Missing information and implementation boundary

- Exact adjustment equation, window inclusion, target timing and a reproducible entry/exit process are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The green plot shows percentage gain from current high to the low of the previous 30 days.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The red plot shows adjusted percentage loss from current low to the high of the previous 30 days.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
a loss of 25% can only be recovered with a percentage gain of 33%.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The actual max loss percent is calculated and plottable but is not plotted by default
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hl4uheb9_max_gain](../tv_hl4uheb9_max_gain.md)

## Source

https://www.tradingview.com/script/Hl4UHEB9-Max-Gain/

Publication ID: Hl4UHEB9. Source SHA-256: 9ac38e2ea91b2465a19d6dd076276c7bad8cae3ada12ad34934e8d12635a9de9. Raw-description SHA-256: 429c4299d06ce215523a123a4f01529084412469f0a1397c54da76857525a826.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
