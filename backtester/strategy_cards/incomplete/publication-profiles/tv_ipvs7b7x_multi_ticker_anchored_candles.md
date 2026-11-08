---

id: tv_profile_ipvs7b7x

name: "Multi-Ticker Anchored Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Overlay several assets in a common session-relative price coordinate system so different nominal price scales can be compared visually."

registry_key: null

runner: null

evaluation: null

---

# Multi-Ticker Anchored Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Overlay several assets in a common session-relative price coordinate system so different nominal price scales can be compared visually.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for session-open percentage scaling and main-open anchoring when aligned OHLC/open series are supplied; actual comparison feeds and session alignment remain unavailable inputs.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For each supplied session-aligned comparison ticker, express each OHLC value X as percentage change 100*(X/O-1) from that ticker’s session open O. Map the relative change onto the main chart’s session-opening price M, so zero change coincides with M and a comparison move of p percent is represented relative to M. Reset at the next selected anchor period.
- This scaling-and-anchoring procedure preserves relative movement rather than executable prices. Up to three comparisons use their own OHLC and opens; the selected anchor defaults to one day.

## Outputs and intended use

- Draw up to three comparison tickers as colored candles with configurable labels, opening line and session-break markers. A comparison candle crossing the shared opening level means it crosses its own open, not the main asset's actual price.

## Parameters and stated settings

- Anchor period defaults one day but can be any selected timeframe. Tickers, labels and session markers are configurable; no fixed comparison universe is defined.

## Failure modes and caveats

- Scaled prices are synthetic and not executable quotes. Assets with different trading sessions, missing opens or currency exposures can have misleading comparisons despite percentage normalization.

## Missing information and implementation boundary

- The source describes the principal scale/anchor transformation, but timestamp alignment, gaps and session-boundary data contracts remain unresolved for arbitrary symbols.

## Data requirements

Required inputs: aligned OHLCV for chart and comparison tickers, session opens.

Repository input-class support: unavailable or unresolved. No selected multi-ticker history or aligned session-open contract is supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
overlaying up to 3 tickers
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
by default this is set to 1 day.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
percentage performance of each ticker's OHLC values relative to its daily open
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
adding the scaled ticker data to the main chart's daily open
```

### E5: mechanism, parameters, readiness

```text
The scale is simply "% change from open".
```

### E6: mechanism, parameters, readiness

```text
By adding the scaled ticker data to the main chart's daily open, each of our resulting series will be properly scaled to the main chart's data based on percentages.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ipvs7b7x_multi_ticker_anchored_candles](../../../strategy_research/tv_ipvs7b7x_multi_ticker_anchored_candles.md)

## Source

https://www.tradingview.com/script/ipvS7b7x-Multi-Ticker-Anchored-Candles/

Publication ID: ipvS7b7x. Source SHA-256: 3bc9f9657253d563a523dd5453b3c4f707c17a3518c19c919d892422cd3596ff. Raw-description SHA-256: 0907bc0a736484f6e4ed3bba6dfc72865b381c9c03d801bba0b41e2658bf800a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
