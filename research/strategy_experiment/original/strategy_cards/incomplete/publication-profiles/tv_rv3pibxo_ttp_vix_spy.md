---

id: tv_profile_rv3pibxo

name: "TTP VIX Spy"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "TTP VIX Spy uses VIX momentum as an external risk-context signal for entries in another asset. It assumes falling volatility from an extreme is constructive for risk assets and rising volatility is adverse. Two signal families distinguish new VIX trend confirmation from pullback out of an extreme. A collection of optional price/volatility filters attempts to remove undesirable signals. The author reports informal mixed-timeframe experience on crypto, which does not establish measured net performance or universal inverse correlation."

registry_key: null

runner: null

evaluation: null

---

# TTP VIX Spy

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

TTP VIX Spy uses VIX momentum as an external risk-context signal for entries in another asset. It assumes falling volatility from an extreme is constructive for risk assets and rising volatility is adverse. Two signal families distinguish new VIX trend confirmation from pullback out of an extreme. A collection of optional price/volatility filters attempts to remove undesirable signals. The author reports informal mixed-timeframe experience on crypto, which does not establish measured net performance or universal inverse correlation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Exact signal-one/two MACD/extreme predicates and filter thresholds are not specified.

## How it works

- Observe TVC:VIX momentum through MACD.
- Generate trend-start and extreme-pullback signal families for long/short use.
- Filter with price/RSI slopes, supertrend countertrend alignment, wide Bollinger bandwidth, VIX RSI and weekday conditions.

## Outputs and intended use

- Colored VIX-momentum states, two alert streams and a backtestable output support entry-context research.

## Parameters and stated settings

- Internal supertrend and slope lookbacks are configurable; VIX RSI filter defaults off.
- Examples tried 4H,1H,15min on BTCUSDT.P/ETHUSDT.P, with author preference for 1H; no measured results are supplied.

## Failure modes and caveats

- VIX and crypto trade on different calendars; stale VIX can distort weekend/intraday signals.
- Multiple filters create tuning risk, and VIX relationships can change.

## Missing information and implementation boundary

- MACD settings, extreme/trend predicates, BBW threshold, slope formulas, defaults and exit rules are absent.

## Data requirements

Required inputs: VIX history, target asset ohlcv.

Repository input-class support: unavailable or unresolved. Requires aligned external VIX and target-asset series; their session alignment and coverage are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
observes the momentum of VIX using MACD.
```

### E2: parameters

```text
By default is OFF
```

### E3: parameters

```text
4H, 1H and 15min
```

### E4: parameters

```text
incline for the results in the 1H.
```

### E5: readiness

```text
begging of a new trend
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_vix_timing](../tv_method_vix_timing.md)
- [tv_rv3pibxo_ttp_vix_spy](../tv_rv3pibxo_ttp_vix_spy.md)

## Source

https://www.tradingview.com/script/Rv3pibXO-TTP-VIX-Spy/

Publication ID: Rv3pibXO. Source SHA-256: c2fddca91defb314128c0cc801b00d108bc0f7efb58fc15ac13775500679f7c7. Raw-description SHA-256: 14792bdf13fcb035746e53eb5a4bed7cf61e3f1af8b13143894007b999f42128.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
