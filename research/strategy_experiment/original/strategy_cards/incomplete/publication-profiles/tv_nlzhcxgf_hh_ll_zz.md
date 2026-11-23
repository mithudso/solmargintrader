---

id: tv_profile_nlzhcxgf

name: "HH-LL ZZ"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Build zigzag structure by requiring repeated breaches of a trigger bar's high or low before recognizing a new directional trigger."

registry_key: null

runner: null

evaluation: null

---

# HH-LL ZZ

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build zigzag structure by requiring repeated breaches of a trigger bar's high or low before recognizing a new directional trigger.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Counter reset/consecutiveness, trigger selection within multiple breaches, fixed-point timing and execution rules are omitted.

- Counter reset/consecutiveness, trigger selection within multiple breaches, fixed-point timing and execution rules are omitted.

## How it works

- A trigger bar establishes upper/lower boundaries. After the configured count of breaches below its low or above its high, move the trigger to a new lower low or higher high. Search between recognized triggers for the opposing extreme and adjust temporary swing points as needed.

## Outputs and intended use

- Use structure for trend review, harmonic analysis or support/resistance. Yellow lines/labels are described as fixed; the newest pair of points remains changeable.

## Parameters and stated settings

- Breach source is close or high/low; count ranges one to ten, with the worked example using three. Styles, labels, support/resistance and repaint-warning visibility are configurable.

## Failure modes and caveats

- The source explicitly says the last two points can repaint. Hiding the warning changes presentation, not that behavior. Repeated breaches need not be consecutive unless code confirms it.

## Missing information and implementation boundary

- Counter reset/consecutiveness, trigger selection within multiple breaches, fixed-point timing and execution rules are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The last 2 points can change (repaint).
Yellow coloured lines/labels are set and won't change anymore.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
X breaches                     -> [i]1 -> 10
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
when 3 bars closes under that [i]low[/i], a new LL is found
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_nlzhcxgf_hh_ll_zz](../tv_nlzhcxgf_hh_ll_zz.md)

## Source

https://www.tradingview.com/script/nlZhcXgF-HH-LL-ZZ/

Publication ID: nlZhcXgF. Source SHA-256: f6e103d205c438e6a1fb4a8a83fd7769f68b8ab4b4f1a4d1710e36ece5048288. Raw-description SHA-256: d13bb35d93eac1e0be519789190ba2e84db1a49bf42c810670990d42476af831.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
