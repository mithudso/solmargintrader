---

id: tv_profile_bbeeqrdm

name: "Time of day / day of week Sigma Spike"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Time of Day/Day of Week Sigma Spike breaks an existing sigma-spike study into calendar buckets. It aims to reveal whether unusually large standardized moves concentrate at particular hours or hour-and-weekday combinations. The complete source only explains the additional grouping and required chart resolution; it does not reproduce the linked parent spike definition. Consequently the card describes the seasonal analysis layer without importing another publication’s formula or treating a spike as a trading signal."

registry_key: null

runner: null

evaluation: null

---

# Time of day / day of week Sigma Spike

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Time of Day/Day of Week Sigma Spike breaks an existing sigma-spike study into calendar buckets. It aims to reveal whether unusually large standardized moves concentrate at particular hours or hour-and-weekday combinations. The complete source only explains the additional grouping and required chart resolution; it does not reproduce the linked parent spike definition. Consequently the card describes the seasonal analysis layer without importing another publication’s formula or treating a spike as a trading signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The underlying Sigma Spike calculation and bucket statistics are absent.

## How it works

- Group unspecified Sigma Spike events by hour or hour combined with weekday.
- Require hourly chart observations for the grouping convention.

## Outputs and intended use

- Calendar breakdown supports timing/seasonality research; exact tables or plots are not described.

## Parameters and stated settings

- Must use H1 chart. No spike threshold or sample defaults supplied.

## Failure modes and caveats

- Calendar bucket counts can be sparse and regime-dependent.
- A spike concentration does not determine direction or profitable execution.

## Missing information and implementation boundary

- Base spike formula, normalization window, threshold, timezone, sample selection and output metrics are absent.

## Data requirements

Required inputs: hourly ohlcv, sigma-spike event definition.

Repository input-class support: unavailable or unresolved. Hourly candles may be available as a data class, but required event construction and timezone are not specified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, purpose

```text
by hour of the day or hour of the day & day of the week.
```

### E2: parameters, readiness

```text
MUST be used on H1 chart.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bbeeqrdm_time_of_day_day_of_week_sigma_spike](../tv_bbeeqrdm_time_of_day_day_of_week_sigma_spike.md)
- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/bbEeQrdm-Time-of-day-day-of-week-Sigma-Spike/

Publication ID: bbEeQrdm. Source SHA-256: 2f78bcf8e580bdca15da082090f49faf576aa0c1adcc13246e790c3a728add74. Raw-description SHA-256: a7ec6a4a611fa2c6b4e1999c7a7c9abc353c5dd1c40c4ac4663070663ad76ef5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
