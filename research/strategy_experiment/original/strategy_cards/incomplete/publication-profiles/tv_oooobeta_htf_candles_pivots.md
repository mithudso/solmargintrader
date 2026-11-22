---

id: tv_profile_oooobeta

name: "HTF Candles & Pivots"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "HTF Candles & Pivots overlays higher-timeframe candle ranges and pivot references on the working chart. It helps retain broader interval context while controlling how much historical information remains visible. A separate shift option can position the previous candle at the current interval, making it a comparison aid rather than a statement that those prior values are current prices."

registry_key: null

runner: null

evaluation: null

---

# HTF Candles & Pivots

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

HTF Candles & Pivots overlays higher-timeframe candle ranges and pivot references on the working chart. It helps retain broader interval context while controlling how much historical information remains visible. A separate shift option can position the previous candle at the current interval, making it a comparison aid rather than a statement that those prior values are current prices.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The independent higher-timeframe OHLC box display is reproducible from selected intervals and body/range modes; unspecified pivot/CPR extras remain outside this usable candle-display scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Draw higher-timeframe candles as boxes showing open-close, high-low or both.
- Add standard pivot points and optionally the central pivot range; allow prior-candle shifting.

## Outputs and intended use

- Inspect broader candle structure with pivot context; show all history, today only or previous day only.

## Parameters and stated settings

- Display choices include body/range selection, historical visibility, previous-to-current shift and CPR toggle. No timeframe or numeric defaults are given.

## Failure modes and caveats

- Analytical: shifted prior candles can be misread as current observations unless their provenance is clear.

## Missing information and implementation boundary

- Exact pivot/CPR equations, interval selection, live-candle updating and repaint behavior are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
The candles are displayed in a box and you can select Open-Close, High-Low or both.
```

### E2: mechanism, readiness

```text
You can also shift one previous candle to the current one.
```

### E3: parameters, readiness

```text
There is an option to display CPR (Central pivot range).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_oooobeta_htf_candles_pivots](../tv_oooobeta_htf_candles_pivots.md)

## Source

https://www.tradingview.com/script/ooOobeTa-HTF-Candles-Pivots/

Publication ID: ooOobeTa. Source SHA-256: 11ea4345a46aca0e02d92be1e22545e49cd8126ffc3ab36b377d21ceea205118. Raw-description SHA-256: 9fd4b7f82d72c046d141e9152377115449e7cafe59ebe2e8504c6a70ae73c790.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
