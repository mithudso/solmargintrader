---

id: tv_profile_r8g2yhdg

name: "Order Block Finder (Experimental)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Order Block Finder marks the final opposite-direction candle before a qualifying consecutive move. It aims to locate price regions that might later be revisited and used for discretionary limit-order planning. The author describes these as institutional order blocks, but candle sequences do not directly establish institutional participation. Detection necessarily occurs after the following candles close, so the original marked candle must not be treated as a contemporaneously known signal. The source explicitly calls this repainting by definition."

registry_key: null

runner: null

evaluation: null

---

# Order Block Finder (Experimental)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Order Block Finder marks the final opposite-direction candle before a qualifying consecutive move. It aims to locate price regions that might later be revisited and used for discretionary limit-order planning. The author describes these as institutional order blocks, but candle sequences do not directly establish institutional participation. Detection necessarily occurs after the following candles close, so the original marked candle must not be treated as a contemporaneously known signal. The source explicitly calls this repainting by definition.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The percentage-move gate lacks defined endpoints and doji/sequence handling, preventing exact event reproduction.

## How it works

- Identify a last down candle followed by a configured run of up candles for bullish blocks, or the reverse for bearish blocks.
- Require the sequence to achieve a minimum percentage move.
- Mark bullish open-to-low or bearish open-to-high range and its midpoint; optionally project latest-block channels.

## Outputs and intended use

- Block boundaries, equilibrium midpoint, optional channels and documentation tooltip support revisitation scenarios.

## Parameters and stated settings

- Sequential-candle count and minimum percentage move are adjustable; numeric defaults are absent.

## Failure modes and caveats

- Backplaced blocks become known only after the required subsequent closes.
- No measured revisit probability or institutional-order evidence is supplied.

## Missing information and implementation boundary

- Percentage-change endpoints, doji policy, sequence overlap, defaults and limit-order risk rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Candle directions, open/high/low and percentage changes use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
last down candle before a sequence of up candles.
```

### E2: mechanism

```text
last up candle before a sequence of down candles.
```

### E3: parameters, readiness

```text
minimum %-change
```

### E4: risks

```text
only possible after the required number of subsequent candles has closed
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_order_blocks](../tv_method_order_blocks.md)
- [tv_r8g2yhdg_order_block_finder_experimental](../../tv_r8g2yhdg_order_block_finder_experimental.md)

## Source

https://www.tradingview.com/script/R8g2YHdg-Order-Block-Finder-Experimental/

Publication ID: R8g2YHdg. Source SHA-256: 2142510ae17dd62959999098efb297bc55007162bd1d15fb70076f992106ecc0. Raw-description SHA-256: ce72f74c5967bf0d24cd034ff897d506647556f2024beba04c0c8f5561e2910f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
