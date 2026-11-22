---

id: tv_profile_mdfcdbek

name: "HTFCandlesLib"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "HTFCandlesLib represents a higher-timeframe candle together with the lower-timeframe candles that established its open, high, low and close. It supports financial structural inspection and drawing, not a directional signal. A caller can retain timestamps, bar indices and a link to the prior candle, exposing more provenance than a bare OHLC tuple."

registry_key: null

runner: null

evaluation: null

---

# HTFCandlesLib

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

HTFCandlesLib represents a higher-timeframe candle together with the lower-timeframe candles that established its open, high, low and close. It supports financial structural inspection and drawing, not a directional signal. A caller can retain timestamps, bar indices and a link to the prior candle, exposing more provenance than a bare OHLC tuple.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Supplied-Candle rendering is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Build a Candle object with OHLC/time/index fields and embedded lower-timeframe key-candle references; use getCurrentCandle within a higher-timeframe request.
- Provide string formatting and box/line rendering for bodies and wicks with bullish/bearish colors.
- For supplied timestamped OHLC,body endpoints=open/close,wick endpoints=low/high;color by close relative to open with caller doji policy and positioning. Key-subcandle selection,ties,requests and aggregation remain excluded.

## Outputs and intended use

- Use detailed candle objects in another analysis script or draw them with optional descriptions.
- Usable scope: Supplied-Candle rendering. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Caller supplies lower-timeframe candle array, formatting delimiter, colors and description toggle; no timeframe/default settings are given.

## Failure modes and caveats

- Analytical: a current HTF candle can evolve, and the referenced high/low subcandle may change until confirmation.

## Missing information and implementation boundary

- Aggregation boundaries, equal-extreme ties, realtime confirmation, missing-candle handling and request lookahead settings are not specified.

## Data requirements

Required inputs: supplied candle OHLC and timestamps at caller resolution.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
Library to get detailed higher timeframe candle information
```

### E2: mechanism, readiness

```text
Candle object with embedded lower timeframe key candles
```

### E3: mechanism, readiness

```text
Lower timeframe candle that records the high price
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[b]method draw(this, bullishColor, bearishColor, printDescription)[/b]
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Library  [b]"HTFCandlesLib"[/b]
```

## Source

https://www.tradingview.com/script/mdFcDbEK-HTFCandlesLib/

Publication ID: mdFcDbEK. Source SHA-256: 3d846c95f8a0b6c4ce31121bb15094348fa745d7ebde4c8e2c8bbedd5721c35c. Raw-description SHA-256: be8615a280133fe6c1efc59796d74f4daa1123b81494c7878df8f08b4aafd843.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
