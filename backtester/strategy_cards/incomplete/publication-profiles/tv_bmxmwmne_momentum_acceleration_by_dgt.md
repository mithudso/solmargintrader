---

id: tv_profile_bmxmwmne

name: "Momentum Acceleration by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Momentum Acceleration treats price change as speed and changes in that speed as acceleration. The purpose is to distinguish whether directional movement is strengthening or weakening, then show possible setup changes with arrows. It is a transparent finite-difference analogy rather than a physical model of markets, and the author explicitly says the display should fit inside an existing strategy rather than be traded alone."

registry_key: null

runner: null

evaluation: null

---

# Momentum Acceleration by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Momentum Acceleration treats price change as speed and changes in that speed as acceleration. The purpose is to distinguish whether directional movement is strengthening or weakening, then show possible setup changes with arrows. It is a transparent finite-difference analogy rather than a physical model of markets, and the author explicitly says the display should fit inside an existing strategy rather than be traded alone.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Explicit source/length finite-difference equations define speed and acceleration; undisclosed arrow formatting does not block the principal numeric signal.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate speed as the difference between current source and source one selected length ago, divided by that length.
- Calculate acceleration by differencing current speed against speed one length ago and dividing by length again. Use acceleration as the signal component.

## Outputs and intended use

- Read bullish/bearish arrows and consider direction changes as possible setups requiring the broader strategy’s confirmation.

## Parameters and stated settings

- Source and length enter both differences; the description gives no defaults or arrow threshold settings.

## Failure modes and caveats

- Analytical: second differences amplify noise and can reverse quickly; changing length alters both lag and scaling.

## Missing information and implementation boundary

- Source-price default, arrow transition/threshold details, confirmation timing and position management are not provided.

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
speed can be calculated as (source – source[length])/length and acceleration becomes  (speed – speed[length])/length
```

### E2: outputs_and_use, readiness

```text
acceleration is used as signal line and result plotted as arrows demonstrating bull or bear direction
```

### E3: risks, readiness

```text
not to be traded upon solely
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bmxmwmne_momentum_acceleration_by_dgt](../tv_bmxmwmne_momentum_acceleration_by_dgt.md)

## Source

https://www.tradingview.com/script/BmXmwmnE-Momentum-Acceleration-by-DGT/

Publication ID: BmXmwmnE. Source SHA-256: c8e479ddc39e072ec0f0dd4b5725a109a094f7260fc71e4c4b70cc77aa07d8a8. Raw-description SHA-256: 817295c0435f764b8e1eeb6d0d3ec5635c64bdb812b33009d08c76ceba68a2c8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
