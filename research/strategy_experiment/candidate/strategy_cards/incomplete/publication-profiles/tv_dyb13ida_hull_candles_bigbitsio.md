---

id: tv_profile_dyb13ida

name: "Hull Candles [BigBitsIO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Smooth candle geometry to reduce visual noise and emphasize trends while retaining a separate line for current market price."

registry_key: null

runner: null

evaluation: null

---

# Hull Candles [BigBitsIO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Smooth candle geometry to reduce visual noise and emphasize trends while retaining a separate line for current market price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source explicitly applies standard HMA to each OHLC series, defines the comparison driving colors and specifies the close SMA, including defaults.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Apply HMA separately to open, high, low and close. Determine candle color from whether HMA-smoothed OHLC4 exceeds its previous value, and plot an independently smoothed close line.

## Outputs and intended use

- Green indicates rising smoothed OHLC4; otherwise candles are red. The separate price line helps distinguish synthetic candles from current price.

## Parameters and stated settings

- HMA period defaults to 10; the close-price SMA defaults to one period and is blue. Both smoothing periods can be changed.

## Failure modes and caveats

- Smoothed candles are synthetic prices and cannot substitute for executable market OHLC. Noise reduction also delays changes and may conceal intrabar extremes.

## Missing information and implementation boundary

- Initialization, OHLC consistency constraints, handling of equal smoothed values beyond the stated red case, and trade/alert rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Open, High, Low and Close (o, h, l, and c) are all calculated using an HMA calculation based on a user input length/period, defaulted at 10.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Green candles have an ohlc4 greater than the previous candle, all other candles are red.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The current price is plotted with the default blue line with an SMA calculation with 1 period
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dyb13ida_hull_candles_bigbitsio](../../../strategy_research/tv_dyb13ida_hull_candles_bigbitsio.md)
- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)

## Source

https://www.tradingview.com/script/dyb13iDa-Hull-Candles-BigBitsIO/

Publication ID: dyb13iDa. Source SHA-256: 99e19ffeb10354d46fa1829497bcfe433d35e15db572419cbd1b4d104579589f. Raw-description SHA-256: 3b41f177e89d28e8b63e8ff29c20abe6c7504c88e0e9409743268ce81327d492.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
