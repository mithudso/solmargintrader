---

id: tv_profile_utcrhzep

name: "Volume Profile, Pivot Anchored by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Profile Pivot Anchored selects its analysis window using detected pivot highs and lows. It displays trading activity horizontally by price, aiming to show where participation concentrated inside a swing-defined interval. The publication pairs the profile with pivot annotations and volume-weighted candle coloring. Other linked tools use sessions or fixed ranges, but those alternatives should not be imported as rules of this publication."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile, Pivot Anchored by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Profile Pivot Anchored selects its analysis window using detected pivot highs and lows. It displays trading activity horizontally by price, aiming to show where participation concentrated inside a swing-defined interval. The publication pairs the profile with pivot annotations and volume-weighted candle coloring. Other linked tools use sessions or fixed ranges, but those alternatives should not be imported as rules of this publication.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- Pivot-window selection, volume allocation and candle-color rules are unspecified.

## How it works

- Use a Pivot Points High Low study to determine the profile interval.
- Allocate volume across price levels over that interval and render a horizontal histogram.
- Add volume-weighted colored bars as an auxiliary chart view.

## Outputs and intended use

- Inspect high-activity prices together with the pivot structure that anchored them.
- Use profile information as contextual analysis rather than an independent prescribed trade system.

## Parameters and stated settings

- No pivot lengths, row counts, volume thresholds or numerical defaults are disclosed.

## Failure modes and caveats

- Confirmed pivots require a timing rule; retroactive anchoring can make historical displays look available earlier than they were.
- Bar-volume allocation can only approximate true volume-at-price without detailed observations.

## Missing information and implementation boundary

- Pivot confirmation, anchor pairing/reset, volume-bin allocation, profile statistics and candle-color equation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
Specified time period with [b]Pivots Anchored Volume Profile[/b] is determined by the Pivot Levels
```

### E2: outputs_and_use

```text
horizontal histogram
```

### E3: mechanism

```text
[i]Volume Weighted Colored Bars[/i] indicator is presneted with the study
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_utcrhzep_volume_profile_pivot_anchored_by_dgt](../tv_utcrhzep_volume_profile_pivot_anchored_by_dgt.md)

## Source

https://www.tradingview.com/script/utCRHZeP-Volume-Profile-Pivot-Anchored-by-DGT/

Publication ID: utCRHZeP. Source SHA-256: 5c6d7b3fec24e5064e146b86dbdf30b86b3c1b92599ac2418d11793f2c1e6455. Raw-description SHA-256: 00a59928fcf3346c36029305976560ccc576302319d4b6da4232dab77ab71156.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
