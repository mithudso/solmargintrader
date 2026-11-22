---

id: tv_profile_qnx9nxw0

name: "Multi Timeframe Volume Profiles [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Multi Timeframe Volume Profiles stacks activity distributions from several horizons on one chart. Its purpose is to show whether short-term participation aligns with broader accepted price areas, avoiding repeated chart switching. The standard display emphasizes total volume, while a delta variant describes buying-versus-selling pressure. Those labels are analytical interpretations: the description does not identify an aggressor-classification method or demonstrate that profile alignment predicts continuation."

registry_key: null

runner: null

evaluation: null

---

# Multi Timeframe Volume Profiles [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multi Timeframe Volume Profiles stacks activity distributions from several horizons on one chart. Its purpose is to show whether short-term participation aligns with broader accepted price areas, avoiding repeated chart switching. The standard display emphasizes total volume, while a delta variant describes buying-versus-selling pressure. Those labels are analytical interpretations: the description does not identify an aggressor-classification method or demonstrate that profile alignment predicts continuation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core rules remain unresolved.

- Volume/delta allocation and value-area computation are unspecified.
- The lower-timeframe source and coverage contract is incomplete.

## How it works

- Build profiles from selected lower-timeframe volume data for each selected horizon.
- Render total volume or a buy/sell difference by price level with point of control and value-area boundaries.

## Outputs and intended use

- Compare overlapping value areas, separated high-participation zones and lower/higher-timeframe disagreement.
- Use the display as context for confirming or fading an existing trading idea rather than as a prescribed trade signal.

## Parameters and stated settings

- Up to five profiles are supported. Timeframes, lower-timeframe source, row resolution, volume/delta model, labels and styling are configurable.

## Failure modes and caveats

- Historical coverage and extreme resolution combinations can materially change the distributions.
- Estimated delta is not automatically actual aggressor volume.

## Missing information and implementation boundary

- Price allocation, directional-volume inference, profile anchor windows, value-area percentage and POC tie handling are absent.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. Detailed lower-timeframe feeds beyond chart OHLCV are required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
multiple timeframe selection (up to 5 profiles)
```

### E2: mechanism, required_data

```text
This script uses lower timeframe data to construct profiles.
```

### E3: mechanism

```text
Delta mode shows the difference between buying and selling pressure at each price level.
```

### E4: risks

```text
accuracy depends on available historical data
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_qnx9nxw0_multi_timeframe_volume_profiles_tradingiq](../tv_qnx9nxw0_multi_timeframe_volume_profiles_tradingiq.md)

## Source

https://www.tradingview.com/script/qnX9nxw0-Multi-Timeframe-Volume-Profiles-TradingIQ/

Publication ID: qnX9nxw0. Source SHA-256: cc82e903a8501dd2ba8d3a23a7593ece5d2f0a77b2484f71a0410adbec902c13. Raw-description SHA-256: 811cf6695c33eddca372436eb11b54c067da942d63b56b04db67c48d2d81ab19.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
