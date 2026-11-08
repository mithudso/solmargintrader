---

id: tv_profile_pohudx82

name: "Multi Time Frame Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Multi Time Frame Candles lets a trader inspect candles from another timeframe while continuing to work on the current chart. It is a financial visualization tool even though it does not generate entries or calculate an oscillator. Its purpose is to preserve cross-timeframe context in a compact candle overlay and allow that context to update during the current period."

registry_key: null

runner: null

evaluation: null

---

# Multi Time Frame Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multi Time Frame Candles lets a trader inspect candles from another timeframe while continuing to work on the current chart. It is a financial visualization tool even though it does not generate entries or calculate an oscillator. Its purpose is to preserve cross-timeframe context in a compact candle overlay and allow that context to update during the current period.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Selected-timeframe OHLC candles and caller-selected count define the principal display; positioning and style are presentation choices.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Display a user-selected number of candles from another timeframe on the current chart without changing its timeframe.

## Outputs and intended use

- Use the overlaid candles to inspect larger or alternative interval structure alongside the working chart.

## Parameters and stated settings

- The description supports up to 3 candles, selectable timeframe and candle count, plus body and wick colors. It illustrates 2 candles and weekly candles on a 1-hour chart.

## Failure modes and caveats

- Analytical: a developing higher-timeframe candle can change before its interval closes; the realtime wording does not prove historical/live parity.

## Missing information and implementation boundary

- Candle positioning, interval request rules, default timeframe and confirmed-versus-developing handling are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
This script can show (upto) 3 candles of another time frames without changing chart time frame
```

### E2: parameters, readiness

```text
in this example number of candles is 2:
```

### E3: parameters, readiness

```text
weekly candles are shown on 1h chart:
```

## Source

https://www.tradingview.com/script/pOHudX82-Multi-Time-Frame-Candles/

Publication ID: pOHudX82. Source SHA-256: 02799c0b8c1eea525ea460b8603ce8a3624bcc667755ac2177100fb273948a44. Raw-description SHA-256: 118de868f007fa32fa982f784663b1fea53c86306367b9f99ead2d19cdae7358.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
