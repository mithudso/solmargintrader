---

id: tv_profile_efbdipvs

name: "Bjorgum AutoTrail"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Bjorgum AutoTrail manages a single existing position with an interactively anchored trailing stop. The user places crosshairs to establish an initial reference, and the script infers a long trail when placed below price or a short trail when above. Its aim is to monitor positional risk when the trader cannot continually watch the chart. It supports several distance models and alert building blocks, but actual exchange automation requires separate provider-specific integration. The source’s one-shot alert behavior is particularly important: a triggered trail must be recreated rather than assumed to manage future trades automatically."

registry_key: null

runner: null

evaluation: null

---

# Bjorgum AutoTrail

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bjorgum AutoTrail manages a single existing position with an interactively anchored trailing stop. The user places crosshairs to establish an initial reference, and the script infers a long trail when placed below price or a short trail when above. Its aim is to monitor positional risk when the trader cannot continually watch the chart. It supports several distance models and alert building blocks, but actual exchange automation requires separate provider-specific integration. The source’s one-shot alert behavior is particularly important: a triggered trail must be recreated rather than assumed to manage future trades automatically.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Price-offset trail recurrence and triggered-stop transition predicates are incomplete.

- Price-offset trail recurrence and triggered-stop transition predicates are incomplete.

## How it works

- Anchor a price-based trail from the user-selected point, or hold a hard stop until a percentage-distance trigger activates a close-based percentage trail.
- Offer ATR and modified PSAR alternatives; PSAR preserves its value on the trigger candle instead of flipping.
- Create basic trail-hit alerts and optional customizable webhook strings with ticker, asset, quantity and exchange inputs.

## Outputs and intended use

- A single-position trail and one-time hit alert support manual or separately integrated risk management.

## Parameters and stated settings

- Interactive anchor, trail type, percentage/volatility controls, quantity and exchange fields are described; numeric defaults are not supplied.

## Failure modes and caveats

- Alerts and webhooks do not establish broker execution, fills or guaranteed stop prices.
- Interactive mode starts on adding the script, and each hit requires a fresh trail/alert.

## Missing information and implementation boundary

- Exact price-offset factor, ATR/SAR defaults, touch/close trigger policy, webhook schema and live reconciliation behavior are absent.

## Data requirements

Required inputs: ohlcv, user-selected trade anchor and direction.

Repository input-class support: unavailable or unresolved. OHLCV supplies trail prices, but the required live-position anchor/settings and any execution integration are user-provided and not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
one time trailing stop
```

### E2: mechanism, readiness

```text
If placed above price action the script will plot a short trail, if placed below it will trail for a long position.
```

### E3: outputs_and_use, risks

```text
alerts are designed to go off only once
```

### E4: risks

```text
Once an alert is triggered, a new trail is to be set up.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_efbdipvs_bjorgum_autotrail](../tv_efbdipvs_bjorgum_autotrail.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/EfbdipVs-Bjorgum-AutoTrail/

Publication ID: EfbdipVs. Source SHA-256: 19f2ca5e8ce8908341fcd26a780e079b7d9bff097d211b301440560b11539589. Raw-description SHA-256: b8dfd6ae909a02300cbd384e11178afeee4dce8d86fc0fc52d0be5c4050c4a47.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
