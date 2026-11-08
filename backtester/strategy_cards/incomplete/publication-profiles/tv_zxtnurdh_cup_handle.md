---

id: tv_profile_zxtnurdh

name: "Cup & Handle"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Cup & Handle searches for paired pivot highs whose intervening closes remain below a temporary connecting line, then fits a cup-shaped envelope and a handle region. It aims to automate a particular geometric interpretation of this pattern rather than simply identify a rounded low by eye. The detector tolerates a configurable fraction of bars breaking its upper/lower cup boundaries. Only the latest full drawing remains, while optional labels preserve historical locations for replay. The author does not supply a breakout-entry or measured pattern-success rule."

registry_key: null

runner: null

evaluation: null

---

# Cup & Handle

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Cup & Handle searches for paired pivot highs whose intervening closes remain below a temporary connecting line, then fits a cup-shaped envelope and a handle region. It aims to automate a particular geometric interpretation of this pattern rather than simply identify a rounded low by eye. The detector tolerates a configurable fraction of bars breaking its upper/lower cup boundaries. Only the latest full drawing remains, while optional labels preserve historical locations for replay. The author does not supply a breakout-entry or measured pattern-success rule.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Cup-circle construction and handle detection/timing are unspecified.

## How it works

- Store confirmed pivot highs and compare a new high with prior candidates using a temporary rim line.
- Reject candidates with disallowed closes/boundary breaks, then draw circular top/bottom cup lines and a retracement handle box.

## Outputs and intended use

- Latest cup/handle drawing and optional historical labels support discretionary pattern research.

## Parameters and stated settings

- Handle maximum retracement described as 33–50% of cup height.
- Pivot Left/Right, PP back and % max breaks are configurable; numeric defaults absent.

## Failure modes and caveats

- Pivots and pattern fitting arrive after historical anchors.
- Circular geometry/tolerated breaks can create flexible hindsight matching.

## Missing information and implementation boundary

- Circle equations, rim-line tolerance, handle timing/selection, defaults and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Pivots and candle-boundary tests use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
maximum 33-50% retracement
```

### E2: mechanism, readiness

```text
2 circle shaped lines
```

### E3: mechanism

```text
close (between these 2 points) doesn't break above this test line.
```

### E4: outputs_and_use

```text
Only the latest pattern is shown
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_cup_handle](../tv_method_cup_handle.md)
- [tv_zxtnurdh_cup_handle](../tv_zxtnurdh_cup_handle.md)

## Source

https://www.tradingview.com/script/ZxTnUrDh-Cup-Handle/

Publication ID: ZxTnUrDh. Source SHA-256: 839f63586ef73533f30a85c6fb6ae055a313d6c626fe719eadcb62ad87ab90a9. Raw-description SHA-256: 31fae4f95a463abc3ae088156b59ca55db804bada60c9d119af576f135c2bcab.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
