---

id: tv_profile_5qso13ib

name: "Flare"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Flare is an educational methods/objects demonstration with a genuine price-location indicator embedded in it. It builds a fan-like shape from an earlier closing price and classifies the present close by where it falls within that shape. The author labels the resulting zones from neutral through bullish/bearish to overbought/oversold, so it offers a visual description of displacement from a past anchor. That financial behavior keeps it in scope despite the substantial Pine syntax tutorial. The examples demonstrate visual states, not validated trade outcomes or a prescription to fade an extreme."

registry_key: null

runner: null

evaluation: null

---

# Flare

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Flare is an educational methods/objects demonstration with a genuine price-location indicator embedded in it. It builds a fan-like shape from an earlier closing price and classifies the present close by where it falls within that shape. The author labels the resulting zones from neutral through bullish/bearish to overbought/oversold, so it offers a visual description of displacement from a past anchor. That financial behavior keeps it in scope despite the substantial Pine syntax tutorial. The examples demonstrate visual states, not validated trade outcomes or a prescription to fade an extreme.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Flare slopes, boundaries and state thresholds are undisclosed.

- Flare slopes, boundaries and state thresholds are undisclosed.

## How it works

- Choose a close a user-defined number of bars back and construct a flare from it toward the current bar or farther.
- Compare current close with flare boundaries, maintain a directional/color state, and update the object each bar.
- A user-defined Flare type groups linefill arrays, direction and color.

## Outputs and intended use

- Shapes below bars indicate the upper flare region; shapes above bars indicate the lower region; both sides indicate the middle.
- Adjustable colors distinguish bullish/bearish intensity and neutral location; optional background coloring improves visibility.

## Parameters and stated settings

- x close back selects the anchor; Width of Flare controls its extent.
- Colors and Bgcolor are configurable; geometric/default numeric values are not supplied.

## Failure modes and caveats

- Financial zone labels depend on the undisclosed flare geometry rather than an established probabilistic definition of overbought/oversold.
- Moving the anchor or width can materially change classifications.

## Missing information and implementation boundary

- Exact slope/boundary construction, zone thresholds, default lookback and trade-management rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The indicator compares historical/current closes and bar coordinates, all compatible with OHLCV data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, purpose, readiness

```text
Calculate where current close is located versus the Flare lines.
```

### E2: outputs_and_use

```text
Below bar if current close is located in the upper part of the Flare
```

### E3: outputs_and_use

```text
Above bar if current close is located in the lower part of the Flare
```

### E4: parameters

```text
settings:[/b] 'x close back'
```

### E5: parameters

```text
dependable of "Width of Flare"
```

## Source

https://www.tradingview.com/script/5QSO13Ib-Flare/

Publication ID: 5QSO13Ib. Source SHA-256: bc059448a01a23699208e4335241c0fb39f9347328cd1e4851c62e2e1487ed25. Raw-description SHA-256: 6764b9f4f63df914e4bc5ba09e54c257deccc2386de42d10b507a05981fb6744.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
