---

id: tv_profile_okuj0d2n

name: "Earnings Price Move Cheat Sheet [KT]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Earnings Price Move Cheat Sheet summarizes historical price behavior around earnings, separating surprises, misses and all releases. It aims to help users inspect repeatability and event risk, with average returns, post-release range and historical-tail metrics. These are retrospective event statistics; the source explicitly warns that sparse earnings categories can make apparent relationships misleading."

registry_key: null

runner: null

evaluation: null

---

# Earnings Price Move Cheat Sheet [KT]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Earnings Price Move Cheat Sheet summarizes historical price behavior around earnings, separating surprises, misses and all releases. It aims to help users inspect repeatability and event risk, with average returns, post-release range and historical-tail metrics. These are retrospective event statistics; the source explicitly warns that sparse earnings categories can make apparent relationships misleading.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Post-event high-low range is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Collect returns over chosen pre/post-earnings session horizons and average them by earnings outcome category.
- Calculate historical-method VaR/CVaR, lower return percentiles and post-event highest-high minus lowest-low range.
- Given supplied earnings-session mapping and caller horizon h=1..20 sessions,range=max(high across post-event window)-min(low across window). Wait until horizon matures. Surprise,event mapping,return/VaR outputs excluded.

## Outputs and intended use

- Inspect typical and adverse earnings-related movement before planning event exposure, without interpreting averages as guaranteed returns.
- Usable scope: Post-event high-low range. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Horizons run from one to twenty sessions; lower earnings-loss percentiles cover first through fifth. No confidence/default sample window or event-category threshold is supplied.

## Failure modes and caveats

- Insufficient misses or short listing history can invalidate apparent correlations; analytical: overlapping events, after-hours timing and revisions affect estimates.

## Missing information and implementation boundary

- Surprise definition, point-in-time earnings feed, price-window alignment, VaR/CVaR conventions and sample inclusion rules are missing.

## Data requirements

Required inputs: earnings dates and surprise/miss history, aligned asset price history.

Repository input-class support: unavailable or unresolved. Requires external point-in-time earnings events/classifications; chart OHLCV alone cannot identify them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
average 1-session to 20-session performance
```

### E2: parameters, readiness

```text
1st - 5th percentile for earnings losses.
```

### E3: risks, readiness

```text
there is an insufficient sample size; no correlations are ascertainable.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
This script looks to distinguish replicable sequences and correlations between earnings releases and price.  The indicator calculates the average 1-session to 20-session performance of an asset prior to an earnings release, and the 1-session to 20-session performance of an asset subsequent an earnings release.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
The script also calculates the highest high and lowest low following an earnings release, up to 20 sessions, and calculates the difference between the two.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
The script also calculates the highest high and lowest low following an earnings release, up to 20 sessions, and calculates the difference between the two.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_okuj0d2n_earnings_price_move_cheat_sheet_kt](../../../strategy_research/tv_okuj0d2n_earnings_price_move_cheat_sheet_kt.md)

## Source

https://www.tradingview.com/script/oKUj0d2n-Earnings-Price-Move-Cheat-Sheet-KT/

Publication ID: oKUj0d2n. Source SHA-256: e35dfefd5276278cc4f46e4982c7af68029e8478fb17e0ae291557efeee24ee1. Raw-description SHA-256: 7056d1f6df10ce9e07dcbce7697887e32ca49b9c8784ebe79ddb6a21f611d81c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
