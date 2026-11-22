---

id: tv_profile_ypaxpury

name: "Interactive Motive Wave Checklist"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Interactive Motive Wave Checklist tests a manually selected price structure against disclosed Elliott-wave-style conditions. It is an educational validation aid: the user supplies the candidate rather than an automatic market scanner discovering it. The checklist distinguishes general motive requirements from impulse and expanding/contracting diagonal constraints. Its results express consistency with the stated geometry and do not establish a price forecast."

registry_key: null

runner: null

evaluation: null

---

# Interactive Motive Wave Checklist

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Interactive Motive Wave Checklist tests a manually selected price structure against disclosed Elliott-wave-style conditions. It is an educational validation aid: the user supplies the candidate rather than an automatic market scanner discovering it. The checklist distinguishes general motive requirements from impulse and expanding/contracting diagonal constraints. Its results express consistency with the stated geometry and do not establish a price forecast.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for individual generic-motive and expanding/contracting diagonal checks on six supplied ordered pivots. The impulse extension rule and equality/boundary parity are not claimed.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow generic-motive/diagonal checklist: take six chronologically increasing pivot points P0…P5 with alternating high/low direction, and wave lengths L_i=abs(P_i−P_(i−1)). With direction d=sign(P1−P0), require L2<L1, d×(P3−P1)>0 and (L3>L1 or L3>L5), following the source strict bigger-than wording. For diagonals additionally require L4<L3 and P4 strictly inside the P0-to-P1 price territory. Contracting requires L1>L3>L5 and L2>L4; expanding requires L1<L3<L5 and L2<L4.
- Require chronologically ordered alternating pivots, limit second-wave retracement and require the third wave to exceed the first endpoint without being the shortest action wave.
- For impulses prohibit overlap of the first and fourth waves and test extension constraints.
- For diagonals restrict fourth-wave retracement, require overlap with first-wave territory and compare sequential action/correction magnitudes for expansion or contraction.

## Outputs and intended use

- After selecting the points, inspect pass/fail checklist items on the chart.
- Use the result to learn how candidate impulse/diagonal structures differ.

## Parameters and stated settings

- Six pivots define the candidate. Retracement rules use 100% and extension is defined above 200%.
- User selects six timestamped price pivots; no automatic pivot detection is needed. Strict inequalities define the narrow checklist; complete impulse validity and extension>200% denominator remain outside scope.

## Failure modes and caveats

- Manual candidate selection introduces hindsight and interpretation bias.
- The phrase all not extended is ambiguous about whether every action wave is individually prohibited from extension.

## Missing information and implementation boundary

- Extension-ratio denominator and its exact aggregate impulse condition are unclear; equality cases are not fully specified.

## Data requirements

Required inputs: ohlcv, six user-selected timestamped price pivots.

Repository input-class support: unavailable or unresolved. Selected external series or user pivots are required beyond chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, required_data

```text
enter 6 pivots in an order
```

### E2: mechanism, parameters

```text
Wave 2 retracement is less than 100%
```

### E3: parameters

```text
retracement ratios of more than 200%
```

### E4: mechanism, parameters, readiness

```text
Wave1 > Wave3 > Wave5 and Wave2 > Wave4
```

### E5: mechanism, parameters, readiness

```text
Wave1 < Wave3 < Wave5 and Wave2 < Wave4
```

### E6: mechanism, parameters, readiness

```text
Wave 2 retracement is less than 100% of wave1
```

### E7: mechanism, parameters, readiness

```text
Wave 3 retracement is more than 100% of wave2
```

### E8: mechanism, parameters, readiness

```text
Checks if Wave 3 is bigger than either Wave 1 or wave 5 or both.
```

### E9: mechanism, parameters, readiness

```text
Wave 4 retracement is less than 100%
```

### E10: mechanism, parameters, readiness

```text
Wave 4 always ends within the price territory of Wave 1
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_elliott_wave](../tv_method_elliott_wave.md)
- [tv_ypaxpury_interactive_motive_wave_checklist](../tv_ypaxpury_interactive_motive_wave_checklist.md)

## Source

https://www.tradingview.com/script/ypAxpurY-Interactive-Motive-Wave-Checklist/

Publication ID: ypAxpurY. Source SHA-256: 676633573b7c6227a4c1630a5b047120814a184ee63bfaa52d88e146b7b4ac70. Raw-description SHA-256: f3aebebe69bff7dfd5c1bdf693668be4fe6f2e4cd0fd2a25e0812dc76245eeff.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
