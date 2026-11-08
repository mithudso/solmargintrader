---

id: tv_profile_kvrhsptp

name: "Elliott Wave [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Elliott Wave detects impulse and corrective structures from zigzag pivots, tracks their development, and draws Fibonacci retracements from recognized impulses. It aims to automate a sequential wave count while retaining invalidation information. The source demonstrates that an initially confirmed pattern can later enlarge or become invalid, so confirmed does not mean permanently fixed. Users receive alerts for discoveries, invalidations and possible new impulses. The result is pattern-analysis context rather than a complete Elliott-based trade plan with defined entries, stops or position sizes."

registry_key: null

runner: null

evaluation: null

---

# Elliott Wave [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Elliott Wave detects impulse and corrective structures from zigzag pivots, tracks their development, and draws Fibonacci retracements from recognized impulses. It aims to automate a sequential wave count while retaining invalidation information. The source demonstrates that an initially confirmed pattern can later enlarge or become invalid, so confirmed does not mean permanently fixed. Users receive alerts for discoveries, invalidations and possible new impulses. The result is pattern-analysis context rather than a complete Elliott-based trade plan with defined entries, stops or position sizes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The full zigzag-wave recognition and invalidation inequalities are missing.

- The full zigzag-wave recognition and invalidation inequalities are missing.

## How it works

- Detect pivots from selected high/low sources and length, then connect them into zigzags.
- Recognize five-wave motive and three-wave corrective patterns, enforcing at least wave-two origin and wave-four non-overlap constraints.
- Update counts/extrema, retracements and invalidation styling as subsequent prices arrive.

## Outputs and intended use

- Wave labels, Fibonacci references, circles/crosses and dotted/dashed invalidation styling show evolving structures.
- Dynamic alerts distinguish motive/corrective discoveries, invalidations and possible starts.

## Parameters and stated settings

- High/low inputs can use actual extremes, close or body extremes.
- The example uses length 10 and confirms an impulse one bar after its endpoint; these are described examples.

## Failure modes and caveats

- Pattern labels can update or invalidate after initial detection.
- The example invalidates a pattern when wave five exceeds wave three, but the complete rule set is not documented.

## Missing information and implementation boundary

- All pattern inequalities, ratios, pivot defaults, overlap handling and trade-management rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Pivots, wave lengths and retracements derive from OHLCV prices.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
divided in 5 waves
```

### E2: parameters, mechanism

```text
divided in 3 waves
```

### E3: parameters

```text
length = 10
```

### E4: parameters

```text
1 bar after point (5)
```

### E5: mechanism

```text
Wave 4[/b] does not overlap
```

### E6: mechanism

```text
Wave 2[/b] can’t retrace
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_kvrhsptp_elliott_wave_luxalgo](../tv_kvrhsptp_elliott_wave_luxalgo.md)
- [tv_method_elliott_wave](../tv_method_elliott_wave.md)

## Source

https://www.tradingview.com/script/KvrhsPTp-Elliott-Wave-LuxAlgo/

Publication ID: KvrhsPTp. Source SHA-256: be8885b42826c6f8903ee14a320dc0df9949c872cc3dd4cfad88556252dd5114. Raw-description SHA-256: a17052ff4f9f83b87a40459a33b46d1074199c3b5fdb076f7d11e532847934c3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
