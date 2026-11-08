---

id: tv_profile_qt7fqntr

name: "Breakout Probability (Expo)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Estimate historical next-candle level-hit frequencies conditional on whether the preceding candle closed up or down."

registry_key: null

runner: null

evaluation: null

---

# Breakout Probability (Expo)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate historical next-candle level-hit frequencies conditional on whether the preceding candle closed up or down.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Counting denominator, sample window, doji classification, compounding of step spacing and close-confirmation logic are absent.

- Counting denominator, sample window, doji classification, compounding of step spacing and close-confirmation logic are absent.

## How it works

- Count how often subsequent candles reach a new high/low and additional percentage-spaced levels for each prior-candle color class. Display observed hit counts as percentages and a basic first-level outcome table.

## Outputs and intended use

- Use the lines as historical bias/context or candidate stop-distance information. An alert at candle open can include ticker, bias, percentage and first upper/lower prices.

## Parameters and stated settings

- Percentage Step sets level spacing, Number of Lines controls count and the statistics panel is optional. Zero-percent levels are hidden by default. A one-percent step is an example.

## Failure modes and caveats

- Level hits on both sides can occur on one candle, so displayed upper/lower percentages are not mutually exclusive directional probabilities. Rare-event samples and regime shifts weaken forecast interpretation.

## Missing information and implementation boundary

- Counting denominator, sample window, doji classification, compounding of step spacing and close-confirmation logic are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed feature class; this does not establish implementation parity or complete data coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
depending on whether the previous candle was red or green
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
1% means that each level is located 1% above/under the previous one.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
If a level got a 0% likelihood of being hit, the level is not displayed as default.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
An alert is sent on candle open
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qt7fqntr_breakout_probability_expo](../tv_qt7fqntr_breakout_probability_expo.md)

## Source

https://www.tradingview.com/script/Qt7fqntR-Breakout-Probability-Expo/

Publication ID: Qt7fqntR. Source SHA-256: 743722bc17de66bf0676e9e7552a7eb628ecdca19c16f9f5d38e16687023d181. Raw-description SHA-256: 12f49f38c9c19f5bc8f17aa397afa1b7bcd66f46aedac0eba23426b33b78c37b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
