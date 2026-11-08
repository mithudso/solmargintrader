---

id: tv_profile_efxi515c

name: "Linear Regression Channel"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Linear Regression Channel adds break detection and direction/momentum labels to a configurable regression envelope. It helps the user distinguish channel orientation from whether its momentum is strengthening or weakening. The script also retains optional broken-channel drawings, providing historical context without defining a complete breakout strategy."

registry_key: null

runner: null

evaluation: null

---

# Linear Regression Channel

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Linear Regression Channel adds break detection and direction/momentum labels to a configurable regression envelope. It helps the user distinguish channel orientation from whether its momentum is strengthening or weakening. The script also retains optional broken-channel drawings, providing historical context without defining a complete breakout strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Regression/deviation estimator, momentum equation, break definition and initialization/confirmation are unspecified.

- Regression/deviation estimator, momentum equation, break definition and initialization/confirmation are unspecified.

## How it works

- Calculate a regression channel for selected source/window/deviation, check for price breaks and evaluate increasing/decreasing/equal channel momentum.
- Change line color and arrow-label shape according to direction and momentum state.

## Outputs and intended use

- Use arrows to distinguish stronger/weaker uptrends or downtrends and a no-trend state; inspect where channels broke.

## Parameters and stated settings

- Source, channel length, deviation, up/down colors, broken-channel visibility and line width are inputs without numeric defaults.

## Failure modes and caveats

- Analytical: regression channels adapt with the sample and break markers may not imply durable continuation or reversal.

## Missing information and implementation boundary

- Regression/deviation estimator, momentum equation, break definition and initialization/confirmation are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
checks the momentum of the channel and shows it's increasing/decreasing/equal
```

### E2: parameters, readiness

```text
Show/hide broken channels
```

### E3: outputs_and_use, readiness

```text
⇑ : Uptrend and moment incresing
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_efxi515c_linear_regression_channel](../tv_efxi515c_linear_regression_channel.md)
- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)

## Source

https://www.tradingview.com/script/efXI515C-Linear-Regression-Channel/

Publication ID: efXI515C. Source SHA-256: 9175fbbd867adf06f1308068f7dceb0ad0fb90bddb1b8de042f6c40a1ce38edf. Raw-description SHA-256: 5a48ce97f079ed639e6409c302634aba2c2175ed1030cd30b28ffcf81affdc78.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
