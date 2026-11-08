---

id: tv_profile_kiy0znxs

name: "Volume Profile / Fixed Range"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This fixed-range volume profile displays how trading volume is distributed through the prices covered by a selected number of bars. It uses box drawings to present that distribution and exposes profile granularity and value-area controls. The description specifically warns that buy and sell volumes are approximate, so these should be read as inferred components rather than direct aggressor-side measurements."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile / Fixed Range

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This fixed-range volume profile displays how trading volume is distributed through the prices covered by a selected number of bars. It uses box drawings to present that distribution and exposes profile granularity and value-area controls. The description specifically warns that buy and sell volumes are approximate, so these should be read as inferred components rather than direct aggressor-side measurements.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Price-bin volume allocation, side attribution and value-area construction are undefined.

- Price-bin volume allocation, side attribution and value-area construction are undefined.

## How it works

- Calculate and draw a volume profile over a fixed bar range using boxes; the price-bin allocation method is not described.
- Separate approximate buy/sell volumes and provide a POC line and value-area display.

## Outputs and intended use

- Inspect volume concentration, the point of control and the chosen value area as contextual price references.

## Parameters and stated settings

- Number of Bars selects the range, Row Size selects row count, and Value Area Volume % selects the value-area proportion; colors and POC line style are configurable. No defaults are disclosed.

## Failure modes and caveats

- Sell/buy volume is expressly approximate; analytical: row count and bar resolution can materially alter apparent concentration.

## Missing information and implementation boundary

- Volume allocation, buy/sell estimation, POC ties and value-area construction rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: risks, readiness

```text
Sell/Buy volumes are calculated approximately!.
```

### E2: parameters, readiness

```text
"Number of Bars"
```

### E3: parameters, readiness

```text
"Row Size"
```

### E4: parameters, readiness

```text
the percent for Value Area
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_builtin_volume_profile_fixed_range](../tv_builtin_volume_profile_fixed_range.md)

## Source

https://www.tradingview.com/script/kIY0znXs-Volume-Profile-Fixed-Range/

Publication ID: kIY0znXs. Source SHA-256: 7557189ace9dca90594cdf24bbb67e5ae4165862477955faaba0929981a00fcd. Raw-description SHA-256: f7d2fc9101d83afbd9b3a6dd0029c7c4210ae8296b59df8762bfb7b1ece975e5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
