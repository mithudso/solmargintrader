---

id: tv_profile_erbzovy8

name: "Fair Value Gap"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Fair Value Gap displays current-timeframe and optional higher-timeframe gaps as possible future price targets. It aims to make imbalance references and cross-timeframe confluence easy to monitor. The user can remove a gap at its midpoint instead of waiting for full fill, optionally deleting filled historical drawings. The description does not define the underlying gap predicate, so a familiar three-candle definition cannot be assumed merely from the title. Its claim that gaps are often filled is qualitative and does not establish timing or profitability."

registry_key: null

runner: null

evaluation: null

---

# Fair Value Gap

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fair Value Gap displays current-timeframe and optional higher-timeframe gaps as possible future price targets. It aims to make imbalance references and cross-timeframe confluence easy to monitor. The user can remove a gap at its midpoint instead of waiting for full fill, optionally deleting filled historical drawings. The description does not define the underlying gap predicate, so a familiar three-candle definition cannot be assumed merely from the title. Its claim that gaps are often filled is qualitative and does not establish timing or profitability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core FVG detection and confirmation predicate is not described.

## How it works

- Detect unspecified bullish/bearish FVGs on chart and selected higher timeframe.
- Track either full-gap or midpoint reach and optionally delete filled historical gaps.

## Outputs and intended use

- Gap regions, midpoint line and timeframe labels support discretionary target/context analysis.

## Parameters and stated settings

- MTF switch/timeframe, midpoint fill, delete-on-fill and timeframe labels are controls without stated defaults.

## Failure modes and caveats

- Developing HTF values and fill-touch timing may differ from confirmed events.
- A gap can remain unfilled or be crossed through with adverse execution.

## Missing information and implementation boundary

- Gap definition, size threshold, confirmation/lookahead, touch-versus-close fill and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed candle-gap concept is compatible with OHLCV; exact algorithm remains unknown.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
current timeframe and an additional higher timeframe.
```

### E2: mechanism, parameters

```text
Half way point
```

### E3: mechanism

```text
delete the gap when reached instead of a full fill.
```

### E4: readiness

```text
displays the Fair Value Gap
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_erbzovy8_fair_value_gap](../tv_erbzovy8_fair_value_gap.md)
- [tv_method_fair_value_gap](../../../strategy_research/tv_method_fair_value_gap.md)

## Source

https://www.tradingview.com/script/erbzoVY8-Fair-Value-Gap/

Publication ID: erbzoVY8. Source SHA-256: 43b75defcdee305219ce925264de2a25d06459cf596f327f100c586d044da73e. Raw-description SHA-256: ae04c743cb3ce1cb614dfeced5e31af03c61b62f8e877ec3ae8fc74b870c9f44.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
