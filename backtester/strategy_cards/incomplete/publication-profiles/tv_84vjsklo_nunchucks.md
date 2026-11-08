---

id: tv_profile_84vjsklo

name: "Nunchucks"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Nunchucks is an alternative financial-chart display that compares its current representation with the preceding representation’s range. It is intended to be read together with the current-price line, giving a compact view of whether price is higher or lower than the previous nunchuck range. The author says the color does not flip during the current candle, suggesting a visually stable intrabar state. That statement does not disclose how the state is fixed or establish broader historical non-repainting behavior. The very short description gives a display concept rather than enough information to recreate the transformation or define a trading system."

registry_key: null

runner: null

evaluation: null

---

# Nunchucks

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Nunchucks is an alternative financial-chart display that compares its current representation with the preceding representation’s range. It is intended to be read together with the current-price line, giving a compact view of whether price is higher or lower than the previous nunchuck range. The author says the color does not flip during the current candle, suggesting a visually stable intrabar state. That statement does not disclose how the state is fixed or establish broader historical non-repainting behavior. The very short description gives a display concept rather than enough information to recreate the transformation or define a trading system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The market-data-to-nunchuck construction and color-state update are undefined.

- The market-data-to-nunchuck construction and color-state update are undefined.

## How it works

- Represent market data as nunchucks and compare higher/lower position against the previous nunchuck’s range.
- Maintain current-candle color without flipping according to the author’s stated design.

## Outputs and intended use

- A range-relative market display is read beside the current-price line.

## Parameters and stated settings

- No configurable parameters or numeric defaults are disclosed.

## Failure modes and caveats

- A fixed intrabar color may lag changing price conditions.
- The unspecified range transformation prevents interpreting this as standard candle or breakout logic.

## Missing information and implementation boundary

- Nunchuck construction, range endpoints, color-fixing timing, inputs, confirmation and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Market ranges and current price are compatible with OHLCV data; the transformation is an algorithm gap rather than evidence of an external-data need.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, outputs_and_use, readiness

```text
Displays Higher and Lower than the previous nunchuck's range
```

### E2: mechanism, risks

```text
Does not flip color during current candle
```

### E3: outputs_and_use

```text
Use it with current price line
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_84vjsklo_nunchucks](../tv_84vjsklo_nunchucks.md)

## Source

https://www.tradingview.com/script/84VJskLO-Nunchucks/

Publication ID: 84VJskLO. Source SHA-256: d8888b04c3531393cef058dbc8092941573aef4759ce0293f33b9a4af7f44aeb. Raw-description SHA-256: 2521c17eef35612657ab60940abcb39bd4383094be7b30a62df68818d5194811.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
