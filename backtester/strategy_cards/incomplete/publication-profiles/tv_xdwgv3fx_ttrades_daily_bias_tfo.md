---

id: tv_profile_xdwgv3fx

name: "TTrades Daily Bias [TFO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "TTrades Daily Bias assigns a next-period target toward a previous high or low from the latest completed period’s relationship to its own prior range. It then measures how often those target levels are reached and closed through. Daily and weekly modes share the same scenario logic, making the tool a directional-target heuristic plus historical reporting rather than a complete entry/stop strategy."

registry_key: null

runner: null

evaluation: null

---

# TTrades Daily Bias [TFO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

TTrades Daily Bias assigns a next-period target toward a previous high or low from the latest completed period’s relationship to its own prior range. It then measures how often those target levels are reached and closed through. Daily and weekly modes share the same scenario logic, making the tool a directional-target heuristic plus historical reporting rather than a complete entry/stop strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source supplies explicit prior-period high/low scenario rules and target-hit accounting; residual edge cases are nonblocking.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- A close above/below prior high/low favors continuation toward the corresponding next period’s prior extreme; a one-sided sweep closing back inside favors the opposite extreme.
- An inside period uses prior-candle bullish/bearish polarity; an outside period sweeping both sides and closing inside receives no bias.
- Draw reference levels, mark touches and count target-hit and subsequent close-through outcomes by scenario.

## Outputs and intended use

- Inspect current daily/weekly bias, reasoning labels, target status and sample-size statistics; configure new-bias or high/low-hit alerts.

## Parameters and stated settings

- Daily and weekly choices are available. Default reference levels begin blue and turn red after traded through; directional display defaults green/red. No numeric lookback/default sample is supplied.

## Failure modes and caveats

- Analytical: historical target-hit frequency omits entry, stop and costs; session definitions and sample selection affect results.

## Missing information and implementation boundary

- Equality/doji tie handling, exact period session boundary, statistics reset and same-bar touch/close accounting are not detailed, but the primary scenario mapping is explicit.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
if price closes above its previous day high (PDH), the following day's bias will target PDH
```

### E2: mechanism, readiness

```text
outside bar that takes both PDH and PDL, but closes inside that range, no bias is assigned.
```

### E3: parameters, readiness

```text
weekly timeframe is also an included option
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_inside_bar](../../tv_method_inside_bar.md)
- [tv_xdwgv3fx_ttrades_daily_bias_tfo](../tv_xdwgv3fx_ttrades_daily_bias_tfo.md)

## Source

https://www.tradingview.com/script/xdwgV3Fx-TTrades-Daily-Bias-TFO/

Publication ID: xdwgV3Fx. Source SHA-256: 5fdab7cc3b72e6643d4c6eebd1dfea314ceb8646ed0a38b253bc284288285f9d. Raw-description SHA-256: 0ee5158d4bae3c2f2f3a5339efa330ded711e557c76c7a1e3a75bc965d844416.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
