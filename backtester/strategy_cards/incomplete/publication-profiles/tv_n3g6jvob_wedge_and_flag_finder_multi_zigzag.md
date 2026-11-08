---

id: tv_profile_n3g6jvob

name: "Wedge and Flag Finder (Multi - zigzag)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Wedge and Flag Finder attempts to locate chart wedges and flags automatically using a multi-zigzag approach. The author changes the number of pivots considered relative to the described standard wedge detector in order to reduce common incidental formations. A flag is presented as a wedge accompanied by a tail. The short description communicates that design intent, but its settings are only referenced through an image link and its geometric rules are not described."

registry_key: null

runner: null

evaluation: null

---

# Wedge and Flag Finder (Multi - zigzag)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Wedge and Flag Finder attempts to locate chart wedges and flags automatically using a multi-zigzag approach. The author changes the number of pivots considered relative to the described standard wedge detector in order to reduce common incidental formations. A flag is presented as a wedge accompanied by a tail. The short description communicates that design intent, but its settings are only referenced through an image link and its geometric rules are not described.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation remains underspecified.

- The pivot detector and wedge/flag geometry are unspecified.

## How it works

- Evaluate five pivots instead of the four attributed to the standard wedge detector.
- Mark a detected wedge with a tail as a flag; the tail measurement is unspecified.

## Outputs and intended use

- Use the detected chart formations as candidates for manual pattern analysis.
- No breakout direction, order placement, stop or target follows from the supplied prose.

## Parameters and stated settings

- Five pivots are used; the source contrasts this with four pivots. Other settings are not transcribed.

## Failure modes and caveats

- More pivot requirements may reduce detections without proving greater predictive accuracy.
- A zigzag endpoint may evolve depending on an undisclosed confirmation rule.

## Missing information and implementation boundary

- Zigzag lengths, pivot confirmation, wedge convergence/tolerance, tail definition and invalidation rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The calculation uses chart OHLCV rather than an external data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters

```text
I have considered 5 pivots instead
```

### E2: parameters

```text
Tradingview standard wedge checks for only 4 pivots.
```

### E3: mechanism

```text
If wedge comes with a tail, then it is marked as flag
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_n3g6jvob_wedge_and_flag_finder_multi_zigzag](../tv_n3g6jvob_wedge_and_flag_finder_multi_zigzag.md)

## Source

https://www.tradingview.com/script/n3g6JvoB-Wedge-and-Flag-Finder-Multi-zigzag/

Publication ID: n3g6JvoB. Source SHA-256: 562be2aa1246118d99e69e2daa4e2e77d3e34959c5aa76c0c5bdc35075c7c684. Raw-description SHA-256: 86ec65f16e816bab0e36ffeb1b5f91b4af37d17def64b4b13e4351f172a4027c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
