---

id: tv_profile_vozihfu9

name: "OBV Traffic Lights"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Make volume-driven directional trends easier to read by combining a Heikin-Ashi-based OBV variation with several visual moving averages."

registry_key: null

runner: null

evaluation: null

---

# OBV Traffic Lights

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Make volume-driven directional trends easier to read by combining a Heikin-Ashi-based OBV variation with several visual moving averages.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact volume signing, average configuration, state transitions and handling of equal Heikin Ashi closes are missing.

- Exact volume signing, average configuration, state transitions and handling of equal Heikin Ashi closes are missing.

## How it works

- Base the OBV direction decision on the current and previous Heikin Ashi closes rather than the conventional underlying close comparison. Add traffic-light moving averages to show trend and changes in volume direction.

## Outputs and intended use

- Read the OBV and its averages as participation context and possible directional shifts. The source does not turn those shifts into a defined entry or exit.

## Parameters and stated settings

- Moving averages and their inherited defaults are mentioned, but the actual types, lengths and color-state rules are not listed.

## Failure modes and caveats

- Heikin Ashi transforms price and can smooth or delay direction changes. This OBV variation is not a direct measure of executed buy/sell aggression.

## Missing information and implementation boundary

- Exact volume signing, average configuration, state transitions and handling of equal Heikin Ashi closes are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This version spices the OBV up a bit by basing it off of the current and previous close of the Heikin Ashi of the current bar, as well as adding "traffic light"
moving averages to the mix
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_vozihfu9_obv_traffic_lights](../tv_vozihfu9_obv_traffic_lights.md)

## Source

https://www.tradingview.com/script/VoziHfu9-OBV-Traffic-Lights/

Publication ID: VoziHfu9. Source SHA-256: 9e1b9616a1180c5f25de3a9478a30204c9f3dbf27ddbfe3db66d811badf82bcd. Raw-description SHA-256: 6c8940b729a4b83271a58406e3ba18e5eb69d21fa33e94a3af4a5630b58f6788.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
