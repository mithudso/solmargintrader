---

id: tv_profile_guxndiot

name: "Interactive ATR Stop-Loss [TANHEF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Draw a manually anchored ATR trailing exit and optional fixed profit target to monitor a trade from a chosen starting point."

registry_key: null

runner: null

evaluation: null

---

# Interactive ATR Stop-Loss [TANHEF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Draw a manually anchored ATR trailing exit and optional fixed profit target to monitor a trade from a chosen starting point.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: The trailing ratchet equation, trigger comparison, reset behavior, target units and intrabar event ordering are absent.

- The trailing ratchet equation, trigger comparison, reset behavior, target units and intrabar event ordering are absent.

## How it works

- The first interactive click sets start time/price and direction: below price for a long stop, above for a short stop. The plotted stop uses the prior candle's ATR-derived trailing value and continues until hit.

## Outputs and intended use

- Stop-hit and target-hit alerts can be created. The target stops plotting after either target or stop is hit, while the trailing stop continues after target success until its own hit. This is a monitoring indicator, not verified broker execution.

## Parameters and stated settings

- Start anchor can be dragged or edited. ATR settings, optional target and alert conditions are configurable; exact ATR period/multiplier defaults are not disclosed.

## Failure modes and caveats

- A plotted stop does not ensure a fill during gaps or slippage. Historical OHLC may not resolve which threshold was hit first in one bar.

## Missing information and implementation boundary

- The trailing ratchet equation, trigger comparison, reset behavior, target units and intrabar event ordering are absent.

## Data requirements

Required inputs: ohlcv, user-selected trade start time/price and target.

Repository input-class support: available. OHLCV supports the volatility calculation, with manual trade anchors required. This does not imply order-routing or fill data availability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
For a long stop-loss, select below price.
For a short stop-loss, select above price.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the trailing value that is considered as the stop loss value is the value of the ATR from the prior candle.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
trailing stop-loss will continue to be plotted until it has been hit regardless of the profit target being hit or not.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_guxndiot_interactive_atr_stop_loss_tanhef](../tv_guxndiot_interactive_atr_stop_loss_tanhef.md)
- [tv_method_atr_trailing](../../tv_method_atr_trailing.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/gUXnDioT-Interactive-ATR-Stop-Loss-TANHEF/

Publication ID: gUXnDioT. Source SHA-256: 368dbc59b68948289c2b37e66f962a8eddd6af65904670e60321dd7f31e94d9e. Raw-description SHA-256: ff3860555f211d2ac8095e10fc17bc9b832812047884ac34f358d0faff943b0b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
