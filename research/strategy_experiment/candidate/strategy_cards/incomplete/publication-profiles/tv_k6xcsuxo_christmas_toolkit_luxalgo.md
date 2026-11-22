---

id: tv_profile_k6xcsuxo

name: "Christmas Toolkit [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Christmas Toolkit uses holiday artwork to present an explicit technical-consensus score. It remains financial in scope because ornaments encode RSI/Stochastic extremes and moving-average direction, while the star aggregates those points into bullish/bearish states. The oscillators use contrarian extreme scoring whereas averages use trend-following scoring, so the composite mixes distinct hypotheses. Snow, moving needles and reindeer are decoration, not market measurements. The last nonneutral switch and fallen stars preserve state-change context without defining an execution strategy."

registry_key: null

runner: null

evaluation: null

---

# Christmas Toolkit [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Christmas Toolkit uses holiday artwork to present an explicit technical-consensus score. It remains financial in scope because ornaments encode RSI/Stochastic extremes and moving-average direction, while the star aggregates those points into bullish/bearish states. The oscillators use contrarian extreme scoring whereas averages use trend-following scoring, so the composite mixes distinct hypotheses. Snow, moving needles and reindeer are decoration, not market measurements. The last nonneutral switch and fallen stars preserve state-change context without defining an execution strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines a reproducible parameterized computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Score RSI14 and Stochastic14: below20/30 gives +2/+1, above80/70 gives -2/-1, otherwise zero.
- Add +1/-1 for close above EMA20 and rising/not-rising EMA20/50/100/200.
- Sum points; classify beyond±6 as very directional, exactly±6 directional and remaining totals neutral.

## Outputs and intended use

- Colored ornaments/star, condition tooltips, fallen switch stars and last-switch state provide a decorative technical dashboard.

## Parameters and stated settings

- Seven ornaments; oscillator lengths14 and EMA20/50/100/200.
- Tree width/offset, garland styling, static animation and reindeer speed are controls.

## Failure modes and caveats

- Correlated average votes dominate some states; oscillator extremes may persist.
- Decorative animation does not imply signal strength or probability.

## Missing information and implementation boundary

- Stochastic smoothing/source details and exact historical switch persistence are absent; standard parameterized scoring is otherwise explicit.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Named oscillator and EMA inputs use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
RSI (length 14)
```

### E2: parameters

```text
Stoch (length 14)
```

### E3: mechanism, parameters, readiness

```text
rsi < 20 - lime (+2 points)
```

### E4: parameters

```text
rsi < 30 - green (+1 point)
```

### E5: parameters

```text
rsi > 80 - darkRed (-2 points)
```

### E6: parameters

```text
rsi > 70 - red (-1 point)
```

### E7: parameters

```text
close vs. ema (length 20)
```

### E8: parameters

```text
ema (length 50)
```

### E9: parameters

```text
ema (length 100)
```

### E10: parameters

```text
ema (length 200)
```

### E11: parameters

```text
> 6 points
```

### E12: parameters

```text
6 points
```

### E13: parameters

```text
-6 points
```

## Source

https://www.tradingview.com/script/k6XcSuxO-Christmas-Toolkit-LuxAlgo/

Publication ID: k6XcSuxO. Source SHA-256: 6e75585734eeb7b0abcb8f60457ea70b5c8e161e612376b3a0071f1ff7aead2f. Raw-description SHA-256: 7d12ad1c848f4997fa7b6062409d8e70d03270bf24cd69a4e1cc3e28ed6ea8fb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
