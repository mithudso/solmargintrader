---

id: tv_profile_2tennpoc

name: "RSI Past Can Turn RSI Into a Directional Tool"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "RSI Past repurposes RSI extremes as evidence about direction rather than automatically treating them as reversal opportunities. It compares how recently the series reached an overbought state versus an oversold state. The difference between those elapsed-bar counts becomes a persistent directional reading, so repeated overbought events can support a bullish interpretation instead of a conventional sell interpretation."

registry_key: null

runner: null

evaluation: null

---

# RSI Past Can Turn RSI Into a Directional Tool

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

RSI Past repurposes RSI extremes as evidence about direction rather than automatically treating them as reversal opportunities. It compares how recently the series reached an overbought state versus an oversold state. The difference between those elapsed-bar counts becomes a persistent directional reading, so repeated overbought events can support a bullish interpretation instead of a conventional sell interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** RSI extreme elapsed counts and bullish-positive/bearish-negative sign define the difference; RSI length/thresholds can be caller parameters and initialization an explicit boundary.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Count bars since the latest overbought and oversold RSI readings and plot a difference between the counts.
- Repeated overbought readings refresh the bullish side of the comparison; repeated oversold readings refresh the bearish side.

## Outputs and intended use

- Positive readings indicate the author’s bullish state and negative readings the bearish state; examples illustrate individual historical stocks without establishing measured performance.

## Parameters and stated settings

- RSI lookback, overbought/oversold thresholds and default settings are not disclosed.

## Failure modes and caveats

- Analytical: elapsed-event counts can remain directional for a long period without measuring the size or profitability of a trend; threshold choice changes reset timing.

## Missing information and implementation boundary

- The precise subtraction order is inferred only from the stated sign interpretation; initialization before either extreme and executable entry/exit rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; code parity is unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
comparing how many bars have passed since RSI's most recent overbought and oversold readings.
```

### E2: outputs_and_use, readiness

```text
Stocks with “bullish” signals will have positive readings
```

### E3: outputs_and_use, readiness

```text
“Bearish” readings are just the opposite, growing more negative as oversold conditions occur.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2tennpoc_rsi_past_can_turn_rsi_into_a_directional_tool](../tv_2tennpoc_rsi_past_can_turn_rsi_into_a_directional_tool.md)

## Source

https://www.tradingview.com/script/2tennpoc-RSI-Past-Can-Turn-RSI-Into-a-Directional-Tool/

Publication ID: 2tennpoc. Source SHA-256: 78697f6c24b42d05b0e04693375435b2565ed8904fc509ffb419cbb6783d8b91. Raw-description SHA-256: 8469254b52c19dc0885d0d87e7f5b9526c9ce698709b181bb8f14aac2fad3767.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
