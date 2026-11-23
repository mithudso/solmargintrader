---

id: tv_profile_rcfo5hhf

name: "Reverse Stochastic Momentum Index On Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Reverse Stochastic Momentum Index On Chart translates oscillator conditions into prospective closing-price levels. Instead of asking only where SMI currently sits, the display asks what close would place it at an alert threshold, equal its signal line or leave it unchanged. This makes oscillator-based planning visible on the price chart. The levels are conditional mathematical references, not guaranteed future prices, and the provided prose does not reproduce the reverse calculations."

registry_key: null

runner: null

evaluation: null

---

# Reverse Stochastic Momentum Index On Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Reverse Stochastic Momentum Index On Chart translates oscillator conditions into prospective closing-price levels. Instead of asking only where SMI currently sits, the display asks what close would place it at an alert threshold, equal its signal line or leave it unchanged. This makes oscillator-based planning visible on the price chart. The levels are conditional mathematical references, not guaranteed future prices, and the provided prose does not reproduce the reverse calculations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation needs the listed definitions.

- SMI smoothing and inverse price-solving equations are missing.

## How it works

- Invert SMI to obtain prices corresponding to chosen upper, middle and lower oscillator values.
- Separately solve for equality with the signal line and equality with the previous SMI value.
- Clamp negative returned prices to zero for chart scaling.

## Outputs and intended use

- Plot crossover and equal-value price lines plus an optional infobox.
- The author describes threshold recrosses, signal crossings and directional agreement as traditional discretionary signals.

## Parameters and stated settings

- Normal SMI range is -100 to +100; upper/middle/lower defaults are 40, 0 and -40. Signal-line default is 13.

## Failure modes and caveats

- Current high/low changes may alter conditional closing-price solutions.
- Clamping can hide an economically or mathematically meaningful negative solution.

## Missing information and implementation boundary

- SMI lookback/smoothing definitions and both inverse formulas are absent, including treatment of changing range extremes.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The default analysis is based on chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Upper alert level ( default 40
```

### E2: parameters

```text
Mid-Line ( default value 0
```

### E3: parameters

```text
Lower alert level ( default -40
```

### E4: parameters

```text
Signal line ( default 13
```

### E5: parameters

```text
normal range of values between +100 and -100.
```

### E6: mechanism, risks

```text
replace any values below zero with zero
```

### E7: mechanism

```text
closing price which would make the SMI equal to its previous value
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_rcfo5hhf_reverse_stochastic_momentum_index_on_chart](../tv_rcfo5hhf_reverse_stochastic_momentum_index_on_chart.md)

## Source

https://www.tradingview.com/script/rCfo5HHf-Reverse-Stochastic-Momentum-Index-On-Chart/

Publication ID: rCfo5HHf. Source SHA-256: 36ebbec5a1734bad0e980b6d44c45b93468619071b193a6a92f927e0b0cf6208. Raw-description SHA-256: 70d8995660c566985f053f1284736a65c09df5525a23a0e507addb1591dd2116.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
