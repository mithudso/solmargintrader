---

id: tv_profile_shy8kacw

name: "Market Structure Volume Profiles [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Market Structure Volume Profiles divides activity into structural price legs rather than arbitrary sessions. Each completed break-of-structure or change-of-character event triggers a profile for that leg, and cumulative delta adds a participation view. The intended use is to compare continuation, reversal and balanced legs by their internal volume distribution. These displays describe estimated activity and structure; the description does not establish actual buyer identities or a predictive advantage."

registry_key: null

runner: null

evaluation: null

---

# Market Structure Volume Profiles [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Structure Volume Profiles divides activity into structural price legs rather than arbitrary sessions. Each completed break-of-structure or change-of-character event triggers a profile for that leg, and cumulative delta adds a participation view. The intended use is to compare continuation, reversal and balanced legs by their internal volume distribution. These displays describe estimated activity and structure; the description does not establish actual buyer identities or a predictive advantage.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation needs the listed definitions.

- Structural confirmation and volume/value-area calculations are unspecified.
- Lower-timeframe source and coverage are unspecified.

## How it works

- Detect BoS and CHoCH, then allocate lower-timeframe volume from the completed structural leg into price levels.
- Compute buy/sell distributions, point of control, value area and optional statistics; track cumulative volume delta with selectable resets.
- Choose detailed, split or compact mini-profile rendering, with mini profiles used when a leg lacks sufficient bars.

## Outputs and intended use

- Compare POC levels, value areas, volume balance and leg return/range summaries.
- Extend POCs and track untouched references; candle coloring can identify structural regimes.

## Parameters and stated settings

- Detailed profiles support up to 500 rows. CVD resets can follow CHoCH, BoS plus CHoCH, day or week.

## Failure modes and caveats

- Profile fidelity depends on lower-timeframe history and structural confirmation.
- The source reports a response-too-large limitation above its row cap.

## Missing information and implementation boundary

- Pivot/structure rules, directional volume allocation, value-area percentage, row boundaries and naked-POC invalidation are absent.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. The described external or detailed input contract is not available from ordinary chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
new volume profile for each completed BoS or CHoCH
```

### E2: parameters

```text
Detailed profiles can use up to 500 rows.
```

### E3: parameters

```text
CHoCH
[*]BoS + CHoCH
[*]Day
[*]Week
```

### E4: required_data

```text
Each profile is built from lower timeframe data
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_shy8kacw_market_structure_volume_profiles_kioseff_trading](../tv_shy8kacw_market_structure_volume_profiles_kioseff_trading.md)

## Source

https://www.tradingview.com/script/shy8kACw-Market-Structure-Volume-Profiles-Kioseff-Trading/

Publication ID: shy8kACw. Source SHA-256: a11cfe1f283101326ac3bc06fc040012c6ac66b4a3ffd31508e201e36a425bab. Raw-description SHA-256: 2cb893c3b54390e339c0ed1b84eda95731b91b2fd42c48985d861b69b69dd762.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
