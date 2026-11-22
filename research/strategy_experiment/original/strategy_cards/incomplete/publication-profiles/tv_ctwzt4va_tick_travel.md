---

id: tv_profile_ctwzt4va

name: "Tick travel ⍗"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Show how price changes during a live candle by marking individual platform-update observations and their direction."

registry_key: null

runner: null

evaluation: null

---

# Tick travel ⍗

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show how price changes during a live candle by marking individual platform-update observations and their direction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for sequential per-bar update numbering and higher/lower/equal color mapping on supplied live updates; feed availability, exact label positioning and retention defects remain separate limitations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For supplied ordered live platform updates, reset the update index at each new candle and number successive observations 1, 2, and so on. Place a dot at that index in tick-up/down mode; progression mode places the observations on the candle using successively spaced text.
- Compare each observed price with the preceding tick price: higher is green, lower red and unchanged dimmed blue. A separate start symbol identifies the first update of each candle. Platform updates can reflect either price or volume changes and are not guaranteed to be individual trades.

## Outputs and intended use

- Green/red/blue means higher/lower/unchanged tick price. Separate start symbols and optional hidden candles help identify where each bar's update sequence begins. This is live microstructure visualization, not a historical reconstruction.

## Parameters and stated settings

- Maximum displayed dots are five hundred. Dot/custom symbol and candle display are configurable. The author considers intervals above five minutes generally impractical, particularly for active symbols.

## Failure modes and caveats

- The author reports possible undrawn ticks, imperfect label price placement and overlap into following candles. Label limits delete earlier history; platform updates are not necessarily individual exchange executions.

## Missing information and implementation boundary

- Persistence/deduplication, exact positioning and retention rules need code. A live update feed is essential and cannot be recovered from ordinary bars.

## Data requirements

Required inputs: live price/volume updates.

Repository input-class support: unavailable or unresolved. The source requires live-bar updates; saved OHLCV lacks their ordered sequence.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
max 500 dots.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if price is higher than previous tick price -> green
- if price is lower than previous tick price -> red
- otherwise -> blue (dimmed)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
A timeframe higher than 5 minutes mostly won't be feasible
```

### E4: mechanism, parameters, readiness

```text
If for example there is 1 tick (first of new bar), a dot will be placed on 1,
if it is the 8th tick off that bar, there will be a dot placed on 8.
```

### E5: mechanism, parameters, readiness

```text
This is the very first tick on each candle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ctwzt4va_tick_travel](../tv_ctwzt4va_tick_travel.md)

## Source

https://www.tradingview.com/script/CtWzT4VA-Tick-travel/

Publication ID: CtWzT4VA. Source SHA-256: ed41cdfc4b08483d3d6225f347843c98cb97baaf7284262bb431e2fb18017da2. Raw-description SHA-256: 9f0300f46ead65925ea325ffe53a83ecdbf69ba502746005e384195b9d6601e2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
