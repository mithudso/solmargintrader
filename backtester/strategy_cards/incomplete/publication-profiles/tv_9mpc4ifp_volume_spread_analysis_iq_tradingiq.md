---

id: tv_profile_9mpc4ifp

name: "Volume Spread Analysis IQ [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume Spread Analysis IQ organizes candle volume, range and recent contextual evidence into a discretionary effort-versus-result reading. It aims to distinguish strong participation that produces movement from large effort that produces little progress, and to label familiar VSA scenarios. The author explicitly acknowledges that VSA literature is subjective and that coding the event definitions requires engineering interpretation. Consequently, an Upthrust or Shakeout label represents this implementation’s interpretation rather than an objective universal pattern. The tool is meant to complement structure or price-action analysis rather than turn each event into a mechanical trade."

registry_key: null

runner: null

evaluation: null

---

# Volume Spread Analysis IQ [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Spread Analysis IQ organizes candle volume, range and recent contextual evidence into a discretionary effort-versus-result reading. It aims to distinguish strong participation that produces movement from large effort that produces little progress, and to label familiar VSA scenarios. The author explicitly acknowledges that VSA literature is subjective and that coding the event definitions requires engineering interpretation. Consequently, an Upthrust or Shakeout label represents this implementation’s interpretation rather than an objective universal pattern. The tool is meant to complement structure or price-action analysis rather than turn each event into a mechanical trade.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Effort/result rankings, context weights and VSA event inequalities are missing.

- Effort/result rankings, context weights and VSA event inequalities are missing.

## How it works

- Rank volume as effort and candle spread as result, then compare their relationship.
- Accumulate recent bullish/bearish VSA evidence into a strong/weak/neutral background.
- Apply contextual conditions to No Demand, No Supply, Upthrust, Shakeout and Stopping Volume events.

## Outputs and intended use

- Lower-panel ranks, optional E/R candle labels, tinted background, live interpretation table and event markers support chart reading.

## Parameters and stated settings

- Effort/result rankings run from 1 to 10.
- Body size, wick length, close location, spread/volume strictness, background proof, traditional/broad demand-supply logic, trend alignment and raw overrides are configurable.

## Failure modes and caveats

- Volume/range mismatch does not directly reveal hidden institutional intent.
- Subjective event definitions may differ materially from a reader’s VSA convention.

## Missing information and implementation boundary

- Ranking windows/formulas, background evidence weights, exact event predicates, threshold defaults and complete trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Candle range, body/wicks, close location and volume are OHLCV-derived; hidden-intent interpretations are not additional observable data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
rankings from 1 to 10.
```

### E2: outputs_and_use

```text
No Demand
[*]No Supply
[*]Upthrust
[*]Shakeout
[*]Stopping Volume
```

### E3: risks, missing_information

```text
there aren’t exact rules to follow.
```

### E4: mechanism

```text
recent flow of bullish and bearish evidence.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9mpc4ifp_volume_spread_analysis_iq_tradingiq](../tv_9mpc4ifp_volume_spread_analysis_iq_tradingiq.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_volume_spread_analysis](../tv_method_volume_spread_analysis.md)

## Source

https://www.tradingview.com/script/9MpC4ifP-Volume-Spread-Analysis-IQ-TradingIQ/

Publication ID: 9MpC4ifP. Source SHA-256: 06225ff5bea212bcbdf3758bef3e3b3e2f31a95e45f4ad4943fe81fa7e52af7e. Raw-description SHA-256: 8d970b2b92f7ccb7920c5173e4db19d178a949a2bc351c237707c850156e77d5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
