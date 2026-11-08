---

id: tv_profile_swwmsmqw

name: "Indicator Panel"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Compare selected technical-indicator values across several symbols in a dynamic table and highlight whether each value has risen or fallen."

registry_key: null

runner: null

evaluation: null

---

# Indicator Panel

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare selected technical-indicator values across several symbols in a dynamic table and highlight whether each value has risen or fallen.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Given the selected indicator readings, the per-symbol table and current-versus-prior green/red/gray rule define a reproducible principal reporting output. This usable scope does not certify numerical parity of unprinted underlying indicator implementations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate selected momentum, directional, money-flow and moving-average readings per symbol. Compare each current reading to its prior value to color its cell green, red or gray.
- The source explicitly lists MACD line, signal and histogram, and DMI components +DI, -DI and ADX. The reporting rule compares each selected reading with its preceding value.

## Outputs and intended use

- Use the panel for compact cross-symbol monitoring. Green means the indicator increased, not necessarily that its absolute level is bullish or a trade should be opened.

## Parameters and stated settings

- Choose five symbols, six indicator categories and two SMA/EMA averages. Listed average lengths are 50 and 200 and can be changed; indicator lengths are also adjustable.

## Failure modes and caveats

- An indicator rising from an extreme or increasing volatility can have different implications from increasing price. Unsynchronized sessions can make cross-symbol comparisons misleading.

## Missing information and implementation boundary

- Default symbols/timeframes, numerical smoothing and source defaults of the underlying indicator calculations, update timing and alert rules are not disclosed. The MACD and DMI component sets are explicitly listed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The panel uses the supported OHLCV input class for a user-selected fixed set of symbols. Aligned histories and source/timeframe choices must be supplied; this does not establish cache coverage for every selected market.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if current value is greater than last value then backgroung color is green, if lower than last value then red, if they are equals then gray.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
You can choose 5 different Symbols, 6 Indicators and 2 Simple or Exponential Moving averages
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- MA with Length 50
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- MA with Length 200
```

### E5: mechanism, parameters, missing_information, readiness

```text
- MACD ([i]MACD and Signal and Histogram[/i])
- DMI ([i]+DI and -DI + and ADX[/i])
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_swwmsmqw_indicator_panel](../../tv_swwmsmqw_indicator_panel.md)

## Source

https://www.tradingview.com/script/SWWMsMQw-Indicator-Panel/

Publication ID: SWWMsMQw. Source SHA-256: d43e67e4552b25a91ef54ccfe645a07efe37700f025c781ad6d880da10e2dbd4. Raw-description SHA-256: 57e371d5e3252a7d6a247719238c87ea7a3f9bb1e0d75bbb2e049c9867634498.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
