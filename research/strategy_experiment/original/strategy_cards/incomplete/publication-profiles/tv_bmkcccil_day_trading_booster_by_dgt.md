---

id: tv_profile_bmkcccil

name: "Day Trading Booster by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Day Trading Booster combines session timing, opening ranges and familiar price references to help the user focus on active trading periods. It provides forex-specific session context and broader day/week/month reference levels, plus custom VWAP and pivot displays. The source motivates these features with general participation patterns, but does not define a complete channel-breakout strategy in prose or prove a best trading time for every asset."

registry_key: null

runner: null

evaluation: null

---

# Day Trading Booster by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Day Trading Booster combines session timing, opening ranges and familiar price references to help the user focus on active trading periods. It provides forex-specific session context and broader day/week/month reference levels, plus custom VWAP and pivot displays. The source motivates these features with general participation patterns, but does not define a complete channel-breakout strategy in prose or prove a best trading time for every asset.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Session opens/opening ranges is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Map session opens/ranges and opening channels, draw day reference levels from ATR or prior-session high-low span, and add week/month opens.
- Offer an opening/closing timetable with countdown and typical volume activity; optionally show anchored VWAP, pivots and a selected moving average.
- At caller day/week/month boundaries capture first open. Over selected5,15 or60-minute opening window compute highest high/lowest low and carry completed references. Caller supplies timezone/session; custom VWAP,pivots/activity excluded.

## Outputs and intended use

- Use session/range context to investigate timing and inspect broader references while monitoring lower-timeframe charts.
- Usable scope: Session opens/opening ranges. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Opening-range choices include 5 minutes, 15 minutes or 1 hour. MA choices include SMA, EMA, WMA and HMA; VWAP anchoring can be Auto, Interactive or Manual.

## Failure modes and caveats

- Analytical: usual participation patterns can fail around holidays/news, and historical statements about crypto session behavior do not establish current conditions.

## Missing information and implementation boundary

- Session timezone/DST logic, typical-volume dataset, custom VWAP/pivot formulas, ATR reference multipliers and complete breakout rules are missing.

## Data requirements

Required inputs: ohlcv, session/calendar configuration, user anchors in interactive/manual VWAP modes.

Repository input-class support: unavailable or unresolved. Core price references are OHLCV-derived, but exact session contracts, optional anchors and typical-activity inputs are not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
5m, 15m or 1h Opening Range
```

### E2: parameters, readiness

```text
Auto, Interactive and Manual anchoring options.
```

### E3: parameters, readiness

```text
SMA, EMA, WMA and HMA
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
   - Day (Session) Open, 5m, 15m or 1h Opening Range
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Forex market is traded 24 hours a day, 5 days a week across by banks, institutions and individual traders worldwide, but that doesn’t mean it’s always active the entire day.  It may be very difficult time trying to make money when the market doesn’t move at all. The busiest times with highest trading volume occurs during the overlap of the London and New York trading sessions, because U.S. dollar (USD) and the Euro (EUR) are the two most popular currencies traded. Typically most of the trading activity for a specific currency pair will occur when the trading sessions of the individual currencies overlap. For example, Australian Dollar (AUD) and Japanese Yen (JPY) will experience a higher trading volume when both Sydney and Tokyo sessions are open
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
   - Week and Month Open
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bmkcccil_day_trading_booster_by_dgt](../tv_bmkcccil_day_trading_booster_by_dgt.md)
- [tv_method_opening_range](../tv_method_opening_range.md)

## Source

https://www.tradingview.com/script/bmkCcCIL-Day-Trading-Booster-by-DGT/

Publication ID: bmkCcCIL. Source SHA-256: 8d69cec4183d49d69a8a18d952c1ece390b782f5409654a5719a445611f10f2e. Raw-description SHA-256: 23ff1ecdd57a7bd50ef838505215343fb9e769cc175be326d0e40a40e4cfec3f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
