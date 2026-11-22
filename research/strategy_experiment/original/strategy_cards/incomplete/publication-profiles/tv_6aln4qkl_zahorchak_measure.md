---

id: tv_profile_6aln4qkl

name: "Zahorchak Measure"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Zahorchak Measure supplies a broad-market trend bias to inform stock or ETF decisions. It combines relationships among moving averages of a market index and the NYSE advance-decline line, so its scope is market regime rather than the charted security’s own momentum alone. Positive values broadly indicate an uptrend and negative values a downtrend. This adaptation smooths a discrete composite into an oscillator, aiming to reduce whipsaws while accepting additional lag. It also allows timeframe and moving-average customization, meaning its interpretation can differ from the historical method it reproduces."

registry_key: null

runner: null

evaluation: null

---

# Zahorchak Measure

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Zahorchak Measure supplies a broad-market trend bias to inform stock or ETF decisions. It combines relationships among moving averages of a market index and the NYSE advance-decline line, so its scope is market regime rather than the charted security’s own momentum alone. Positive values broadly indicate an uptrend and negative values a downtrend. This adaptation smooths a discrete composite into an oscillator, aiming to reduce whipsaws while accepting additional lag. It also allows timeframe and moving-average customization, meaning its interpretation can differ from the historical method it reproduces.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** NYSE/breadth relationship scoring and retained moving-average periods are unspecified.

- NYSE/breadth relationship scoring and retained moving-average periods are unspecified.

## How it works

- Compare multiple NYSE Composite moving averages with an average of the NYSE advance-decline line to build the composite measure.
- Smooth the discrete measure with an EMA; reducing EMA length to one restores the unsmoothed form described by the author.
- Convert the historical weekly lookbacks to daily values in the adaptation and allow multi-timeframe use.

## Outputs and intended use

- An oscillator ranging from -10 to +10 indicates broad bullish/bearish bias around zero.
- Use market bias to constrain a separate stock/ETF approach; intermediate-level interpretation is left open.

## Parameters and stated settings

- Historical averages used 5, 15 and 40 weeks; the author converts by a factor of five for daily use.
- The short index average is removed in the Morris variant used here; moving-average lengths, timeframe and EMA length are adjustable.

## Failure modes and caveats

- NYSE breadth and composite trends may diverge from a particular stock or ETF.
- Smoothing delays regime changes; the author’s qualitative superiority claim is not a measured result here.

## Missing information and implementation boundary

- Exact relationship scoring, retained average lengths/defaults, breadth series identifiers and complete trading rules are not supplied.

## Data requirements

Required inputs: NYSE Composite index history, NYSE advance-decline line history.

Repository input-class support: unavailable or unresolved. The method requires external broad-market and breadth series; their availability and historical alignment are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, required_data, readiness

```text
multiple moving averages of the NYSE Composite, a moving average of the NYSE advance decline line
```

### E2: parameters

```text
EMA Length to 1
```

### E3: parameters

```text
moving averages of 5, 15, and 40 weeks.
```

### E4: parameters

```text
dividing by 5.
```

### E5: parameters, outputs_and_use

```text
ZM oscillates between -10 and +10.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6aln4qkl_zahorchak_measure](../tv_6aln4qkl_zahorchak_measure.md)

## Source

https://www.tradingview.com/script/6aLn4Qkl-Zahorchak-Measure/

Publication ID: 6aLn4Qkl. Source SHA-256: 550b87cbb7e0ef21875df5f9b12fe94c64328ba4ad4455df7847e1d0d40830a8. Raw-description SHA-256: a11437fbd5688bc4a97b22713ac8f5a451c261bda04164f39c334896fe9e4917.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
