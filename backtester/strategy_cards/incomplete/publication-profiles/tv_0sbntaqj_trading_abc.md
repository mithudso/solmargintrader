---

id: tv_profile_0sbntaqj

name: "Trading ABC"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Recognize an ABC pullback that agrees with a moving-average trend, then mark a subsequent price bounce rather than treating every zigzag correction as a trade."

registry_key: null

runner: null

evaluation: null

---

# Trading ABC

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Recognize an ABC pullback that agrees with a moving-average trend, then mark a subsequent price bounce rather than treating every zigzag correction as a trade.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The precise bounce test, trend aggregation, pivot confirmation delay and numerical Fibonacci/error defaults are absent. Stops, exits and position sizing are unspecified.

- The precise bounce test, trend aggregation, pivot confirmation delay and numerical Fibonacci/error defaults are absent. Stops, exits and position sizing are unspecified.

## How it works

- A cloud made from simple and exponential averages establishes trend context. The last pair of zigzag waves is compared with user-defined Fibonacci bounds and an error allowance.
- Only after the candidate passes those checks and price bounces does the script draw a triangle. Repeated bounces can create repeated markers for the same broader pattern.

## Outputs and intended use

- Use the cloud to assess directional context and the ABC lines to inspect the proposed correction. Triangles are bounce annotations; the description supplies no complete order-management plan.
- Old pattern drawings, zigzag legs and minimum/maximum retracement levels can be retained or hidden to manage chart clutter.

## Parameters and stated settings

- Moving-average lengths default to 50, 100, 150, 200, 20 and 40. Zigzag period, Fibonacci bounds and error rate are adjustable.
- Cloud visibility, old labels/lines and drawing colors are configurable.

## Failure modes and caveats

- A developing zigzag can revise recent structure; repeated triangles should not automatically be counted as independent opportunities.

## Missing information and implementation boundary

- The precise bounce test, trend aggregation, pivot confirmation delay and numerical Fibonacci/error defaults are absent. Stops, exits and position sizing are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described calculation uses chart price/volume history. This establishes input class only, not a verified implementation or cached market coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
- It creates Trend Cloud using Simple and Exponential moving averages with the lenghts 50, 100, 150, 200, 20, 40 by default and checks the trend. you can change the lengths as you wish
```

### E2: purpose, mechanism, outputs_and_use, parameters

```text
- Using last 2 zigzag waves it checks if there is suitable ABC pattern according the Trend, the Min/Max Fibonacci levels and Error Rate
```

### E3: purpose, mechanism, outputs_and_use, parameters

```text
- If there are multiple bouncing then you can see multiple triangles
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0sbntaqj_trading_abc](../tv_0sbntaqj_trading_abc.md)

## Source

https://www.tradingview.com/script/0SBnTaqJ-Trading-ABC/

Publication ID: 0SBnTaqJ. Source SHA-256: c7f61acb7aeb5e57d26331f81ee05e0d8144cab8c20151b729dd88ca8c5d99bd. Raw-description SHA-256: ee0aa6dfbc89b63e3dcbbc712f024c584b412cd3fa0c1706782112d91b4fe10d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
