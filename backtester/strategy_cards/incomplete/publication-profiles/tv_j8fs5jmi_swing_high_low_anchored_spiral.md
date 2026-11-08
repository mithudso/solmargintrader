---

id: tv_profile_j8fs5jmi

name: "Swing High/Low Anchored Spiral"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Fit a swing-anchored Archimedean spiral to price as an exploratory chart geometry drawing."

registry_key: null

runner: null

evaluation: null

---

# Swing High/Low Anchored Spiral

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fit a swing-anchored Archimedean spiral to price as an exploratory chart geometry drawing.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The fitting objective, spiral scale, pivot confirmation and any market interpretation are not documented.

- The fitting objective, spiral scale, pivot confirmation and any market interpretation are not documented.

## How it works

- Choose a historical swing high or low as the spiral center and estimate a spiral over the chart. The number of turns controls its shape.

## Outputs and intended use

- Use the generated geometry for visual exploration. The author jokes about apophenia and does not claim that intersections predict market reactions.

## Parameters and stated settings

- Users choose the swing occurrence and number of turns. Length/occurrence settings can be reduced if drawing problems occur; no defaults are provided.

## Failure modes and caveats

- Flexible geometry can invite pattern-finding without statistical support. Swing selection and chart aspect ratio can materially alter apparent alignment.

## Missing information and implementation boundary

- The fitting objective, spiral scale, pivot confirmation and any market interpretation are not documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Fit the estimate of an Archimedean spiral to the price, with a central point determined by swing high/lows.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Users can determine which historical swing high/low to use as the spiral central point and can choose the number of turns it should make.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_j8fs5jmi_swing_high_low_anchored_spiral](../tv_j8fs5jmi_swing_high_low_anchored_spiral.md)

## Source

https://www.tradingview.com/script/J8fs5jMi-Swing-High-Low-Anchored-Spiral/

Publication ID: J8fs5jMi. Source SHA-256: 76991a241c358925a358734e05d3512769678452e729f220cc669049f804f45f. Raw-description SHA-256: 197e66e4308b58c71db629c3186604f41dee6bf25d7e2455e1796169b438bfe2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
