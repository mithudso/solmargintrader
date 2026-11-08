---

id: tv_profile_15kb0kgb

name: "RSI buy sell force ver 1 "

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This RSI-derived display separates buying and selling force into colored components so the user can read the prevailing directional balance. The short source offers two alternative interpretations: compare the blue and red components, or examine their position relative to zero. It describes a visual study rather than a completed automatic signaling strategy."

registry_key: null

runner: null

evaluation: null

---

# RSI buy sell force ver 1

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This RSI-derived display separates buying and selling force into colored components so the user can read the prevailing directional balance. The short source offers two alternative interpretations: compare the blue and red components, or examine their position relative to zero. It describes a visual study rather than a completed automatic signaling strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The transformation splitting RSI into buying and selling force is undisclosed.

- The transformation splitting RSI into buying and selling force is undisclosed.

## How it works

- Display RSI buying and selling force as blue and red components; the author interprets blue above red as bullish and the reverse as bearish.
- An alternative suggested interpretation uses above-zero or below-zero readings; the source says no security-based multi-timeframe calculation is used.

## Outputs and intended use

- Use relative component position to label bullish or bearish periods; zero-based signals are only proposed for experimentation.

## Parameters and stated settings

- No calculation length, smoothing setting or default values are given.

## Failure modes and caveats

- Analytical: the two suggested interpretations need not agree; neither includes risk management or a validated forecasting claim.

## Missing information and implementation boundary

- The formula separating RSI forces, crossing confirmation, alert behavior and exits are absent; the author offers to add signals later.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. RSI-derived deterministic chart calculations can use historical prices, although the force decomposition is unspecified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Very simple script with no security MTF that show RSI buy and sell force
```

### E2: mechanism, outputs_and_use, readiness

```text
blue above red =bullish period
red above blue =bearish period
```

### E3: outputs_and_use, readiness

```text
or you can try above 0 or bellow 0 as signal
```

### E4: missing_information, readiness

```text
if you want i will add signal after to this one
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_15kb0kgb_rsi_buy_sell_force_ver_1](../tv_15kb0kgb_rsi_buy_sell_force_ver_1.md)

## Source

https://www.tradingview.com/script/15KB0KGb-RSI-buy-sell-force-ver-1/

Publication ID: 15KB0KGb. Source SHA-256: 9e8c73032e38c4300083da629134e4c0fc12061cf5178848f901f2451fbc1ce4. Raw-description SHA-256: d4c39386b0b61a4133db440c5e8cd0d3309daea3db88765526b668154ddb2793.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
