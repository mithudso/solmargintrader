---

id: tv_profile_gbesfgsq

name: "Nasdaq Day and night breakdown"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Separate Nasdaq futures movement before and after the market open to compare overnight and daytime contributions to daily price change."

registry_key: null

runner: null

evaluation: null

---

# Nasdaq Day and night breakdown

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Separate Nasdaq futures movement before and after the market open to compare overnight and daytime contributions to daily price change.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact segment endpoints, wick construction and treatment of incomplete sessions are not supplied.

- Exact segment endpoints, wick construction and treatment of incomplete sessions are not supplied.

## How it works

- Compute close-minus-open change for the two disclosed NQ segments. A wick depicts the day's price range.

## Outputs and intended use

- Orange represents the pre-open segment and blue the post-open segment; white wicks show range. Read the display as a session decomposition rather than a forecasting signal.

## Parameters and stated settings

- The description gives colors but no exchange timezone, open time or configurable session boundaries.

## Failure modes and caveats

- Session definitions, daylight-saving transitions and futures session rollover can materially change the decomposition.

## Missing information and implementation boundary

- Exact segment endpoints, wick construction and treatment of incomplete sessions are not supplied.

## Data requirements

Required inputs: NQ intraday OHLCV, market-open session definition.

Repository input-class support: unavailable or unresolved. NQ intraday prices are required and the session boundary is unspecified; the current chart cannot be assumed to supply this dataset.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Orange: the (close - open) of NQ before market open
Blue: the (close - open) if NQ after market open
White wicks: the vibrating range of that day
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gbesfgsq_nasdaq_day_and_night_breakdown](../tv_gbesfgsq_nasdaq_day_and_night_breakdown.md)

## Source

https://www.tradingview.com/script/GBESfgsQ-Nasdaq-Day-and-night-breakdown/

Publication ID: GBESfgsQ. Source SHA-256: e90f5753c94c3f62ae468e59faf23ad197f52d7a00cc5c966a2335a76dbef2ba. Raw-description SHA-256: 584e6a354c0627460483f489488bee712503001f3aedf46dd03fecf5058bf72a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
