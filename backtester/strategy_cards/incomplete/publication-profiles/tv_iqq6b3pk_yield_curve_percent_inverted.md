---

id: tv_profile_iqq6b3pk

name: "Yield Curve Percent Inverted"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Yield Curve Percent Inverted summarizes how widespread Treasury yield-curve inversion is across maturity pairs. It avoids focusing on a single spread by counting the proportion of shorter-versus-longer comparisons whose long maturity yields less. The intended use is macroeconomic risk context: broad inversion can accompany concern about the near-term economy. The source cites historical pre-recession episodes, but those retrospective statements are not independently checked here and do not establish a reliable timing rule for trading assets."

registry_key: null

runner: null

evaluation: null

---

# Yield Curve Percent Inverted

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Yield Curve Percent Inverted summarizes how widespread Treasury yield-curve inversion is across maturity pairs. It avoids focusing on a single spread by counting the proportion of shorter-versus-longer comparisons whose long maturity yields less. The intended use is macroeconomic risk context: broad inversion can accompany concern about the near-term economy. The source cites historical pre-recession episodes, but those retrospective statements are not independently checked here and do not establish a reliable timing rule for trading assets.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The exact included Treasury-maturity set defining the fixed spread denominator is not enumerated.

- The exact included Treasury-maturity set defining the fixed spread denominator is not enumerated.

## How it works

- Compare every included Treasury maturity pair and classify a spread as inverted when longer-duration yield is lower.
- Divide inverted-pair count by total pair count and plot the percentage.

## Outputs and intended use

- A percentage series measures breadth of inversion for macro/regime observation.

## Parameters and stated settings

- Source specifies 55 spreads from one-month through thirty-year maturities.
- It cites 60–70% as historical pre-recession territory and says its available history begins in 1987; these are dated author claims, not verified current coverage.

## Failure modes and caveats

- Correlated spreads are not independent recession signals.
- Inversion can persist, and a retrospective threshold does not establish an actionable lead time.

## Missing information and implementation boundary

- Full maturity list, feed symbols, missing-yield handling, equality convention, update alignment and trading rules are absent.

## Data requirements

Required inputs: Treasury yield histories across multiple maturities.

Repository input-class support: unavailable or unresolved. Requires synchronized external yield series rather than ordinary traded-asset OHLCV; coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
all fifty-five Treasury Bond Yield spreads
```

### E2: parameters

```text
1-month up to 30-year
```

### E3: parameters, risks

```text
60%-70% range
```

### E4: parameters, risks

```text
prior to 1987
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_iqq6b3pk_yield_curve_percent_inverted](../tv_iqq6b3pk_yield_curve_percent_inverted.md)

## Source

https://www.tradingview.com/script/IQq6B3Pk-Yield-Curve-Percent-Inverted/

Publication ID: IQq6B3Pk. Source SHA-256: 4150f384fc6f817cb3fc6533d5f82500db208c9fb7d3fa35db8ef3141e2d096a. Raw-description SHA-256: 7d0ddb207c4e92f76108c4a9dbbfc30ad5bf07bc833bd5634f587b365048a18e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
