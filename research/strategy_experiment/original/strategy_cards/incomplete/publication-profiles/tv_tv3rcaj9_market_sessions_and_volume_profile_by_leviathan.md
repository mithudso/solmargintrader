---

id: tv_profile_tv3rcaj9

name: "Market sessions and Volume profile - By Leviathan"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Combine session boundaries and volume profiles to compare participation and value regions across intraday and calendar periods."

registry_key: null

runner: null

evaluation: null

---

# Market sessions and Volume profile - By Leviathan

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine session boundaries and volume profiles to compare participation and value regions across intraday and calendar periods.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Bin allocation, up/down volume classification, value-area percentage/expansion and smoothing formula are missing.

- Bin allocation, up/down volume classification, value-area percentage/expansion and smoothing formula are missing.

## How it works

- Accumulate a histogram, point of control and value-area boundaries for a selected Tokyo, London, New York, daily, weekly or monthly session. Optional smoothing modifies volume inputs.

## Outputs and intended use

- Display ongoing-session zones and selectively show histogram, POC, VAH or VAL. These are contextual market references rather than guaranteed support/resistance or trade orders.

## Parameters and stated settings

- The text lists UTC/GMT windows Tokyo 1:00-9:00, London 7:00-16:00 and New York 13:00-22:00. Profile resolution, smoothing, colors, line thickness and visibility are adjustable.

## Failure modes and caveats

- The author recommends lower chart intervals for shorter sessions and intervals above fifteen minutes for monthly sessions. Fixed UTC windows may not track all daylight-saving shifts. Higher resolution reduces retained profile count.

## Missing information and implementation boundary

- Bin allocation, up/down volume classification, value-area percentage/expansion and smoothing formula are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
- Tokyo session (1:00 - 9:00 UTC/ GMT )
- London session (7:00 - 16:00 UTC/ GMT )
- New York session (13:00 - 22:00 UTC/ GMT )
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Use timeframe higher than 15min when viewing Monthly sessions
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Resolution (The higher the value, the more refined of a profile, but less profiles are shown on the chart)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_tv3rcaj9_market_sessions_and_volume_profile_by_leviathan](../tv_tv3rcaj9_market_sessions_and_volume_profile_by_leviathan.md)

## Source

https://www.tradingview.com/script/tV3rCaJ9-Market-sessions-and-Volume-profile-By-Leviathan/

Publication ID: tV3rCaJ9. Source SHA-256: 8218945cc8a9ccd3423503561efb8c5bf2aa67f7dd3fe0aa46cc0c6e00e039df. Raw-description SHA-256: ec940fc3cd576523c51e669fec2f7a28dfb6440a34175b8a438c2a91d8ee4ed7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
