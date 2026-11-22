---

id: tv_profile_r7o3zulh

name: "Estimated Time At Price [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Estimated Time At Price estimates how long price occupies individual price blocks or levels. It substitutes a time-at-price perspective for the related author volume-delta study, using lower-timeframe observations to build the estimates. The resulting highlighted level and extended reference line identify the greatest estimated duration, not necessarily the largest volume. The author repeatedly calls these estimates, which is important because bar observations do not supply an exact continuous history of every traded price."

registry_key: null

runner: null

evaluation: null

---

# Estimated Time At Price [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimated Time At Price estimates how long price occupies individual price blocks or levels. It substitutes a time-at-price perspective for the related author volume-delta study, using lower-timeframe observations to build the estimates. The resulting highlighted level and extended reference line identify the greatest estimated duration, not necessarily the largest volume. The author repeatedly calls these estimates, which is important because bar observations do not supply an exact continuous history of every traded price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation needs the listed definitions.

- Time-at-price allocation and lower-timeframe resolution are undefined.

## How it works

- Derive lower-timeframe values using a formula referenced to another publication but not repeated here.
- Aggregate estimated duration by block in classic mode or by more precise price levels in non-classic mode.
- Highlight the greatest-duration level and optionally extend its POC-labelled line until price violates it.

## Outputs and intended use

- Read duration labels in minute.second format and inspect the distribution beside the latest bar.
- Customize line removal after violation, colors, neon appearance, recalculation interval and inclusion of the current bar.

## Parameters and stated settings

- No numerical defaults or bin widths are supplied; duration is formatted as minute.second.

## Failure modes and caveats

- Duration allocation from lower-timeframe bars is approximate; changing resolution can change the dominant level.

## Missing information and implementation boundary

- Duration allocation, block sizing, referenced lower-timeframe formula and violation/reset criteria are missing.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. The described external or detailed input contract is not available from ordinary chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: outputs_and_use

```text
all time estimates are in minute.second format.
```

### E2: purpose

```text
estimate the approximate time spent at price blocks
```

### E3: mechanism

```text
estimated time spent at those levels is summed
```

### E4: outputs_and_use

```text
POC line is extended right until violated.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_r7o3zulh_estimated_time_at_price_kioseff_trading](../tv_r7o3zulh_estimated_time_at_price_kioseff_trading.md)

## Source

https://www.tradingview.com/script/r7O3zuLh-Estimated-Time-At-Price-Kioseff-Trading/

Publication ID: r7O3zuLh. Source SHA-256: 38adbdf645f3e1b057d2752ee986c7d5c5740354f19c664f3bc84aca8cb19e65. Raw-description SHA-256: 39ade8a84a3cb0b73da2686573f360cff0c54528649f8dfd007cb42752729fcd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
