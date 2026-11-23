---

id: tv_profile_faku8ild

name: "Example: Graph style - 4th Dimension RSI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Fourth Dimension RSI is an experimental visualization of RSI and price change through a short time sequence. Its financial purpose is to inspect how momentum and price movement evolve together, using a scatter-like graph instead of a conventional oscillator pane. The phrase fourth dimension is descriptive artwork terminology here, not a claim of additional predictive information. The description establishes that axes are inverted to make both properties graphable, but does not define the coordinates precisely. A reader should therefore treat it as a visual experiment rather than infer a standard RSI divergence or threshold-crossing strategy."

registry_key: null

runner: null

evaluation: null

---

# Example: Graph style - 4th Dimension RSI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fourth Dimension RSI is an experimental visualization of RSI and price change through a short time sequence. Its financial purpose is to inspect how momentum and price movement evolve together, using a scatter-like graph instead of a conventional oscillator pane. The phrase fourth dimension is descriptive artwork terminology here, not a claim of additional predictive information. The description establishes that axes are inverted to make both properties graphable, but does not define the coordinates precisely. A reader should therefore treat it as a visual experiment rather than infer a standard RSI divergence or threshold-crossing strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** RSI/price-change mapping and scatter-axis construction are undefined.

- RSI/price-change mapping and scatter-axis construction are undefined.

## How it works

- Collect RSI fluctuations and price change over a period and place them in a scatter-like representation.
- Invert axes to permit graphing both properties; exact mapping is not given.

## Outputs and intended use

- A short-history joint momentum/price graph supports exploratory observation.

## Parameters and stated settings

- The stated example period is 10; RSI length and other controls are not disclosed.

## Failure modes and caveats

- Unspecified scaling and inverted axes can change perceived relationships.
- No forecasting or signal-quality evidence accompanies the experimental display.

## Missing information and implementation boundary

- RSI formula settings, price-change definition, axis mapping, point timing and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. RSI and price change derive from chart prices, an OHLCV data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
fluctuations of the RSI and price change over a period of time(10)
```

### E2: mechanism

```text
inversion of axis
```

### E3: risks

```text
EXPERIMENTAL:
```

## Source

https://www.tradingview.com/script/Faku8iLD-Example-Graph-style-4th-Dimension-RSI/

Publication ID: Faku8iLD. Source SHA-256: f869fe849844a4972337548f16d025ba75ed6f1af1cd428287cab3c5fc686bfe. Raw-description SHA-256: a98e1e4f76241926057213bdafde61d8008568b22092485d5c95ddae534c65d0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
