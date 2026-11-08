---

id: tv_profile_ijpiemfw

name: "Rolling largest Impulse Murreys Lines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This experimental study chooses a dominant impulse inside a rolling window and builds Murrey-style reference lines from that selected move. The distinguishing idea is algorithmic impulse selection rather than manual selection of a chart range. The description names the maximum-subarray method but leaves the financial encoding of its input and the subsequent line construction unexplained."

registry_key: null

runner: null

evaluation: null

---

# Rolling largest Impulse Murreys Lines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This experimental study chooses a dominant impulse inside a rolling window and builds Murrey-style reference lines from that selected move. The distinguishing idea is algorithmic impulse selection rather than manual selection of a chart range. The description names the maximum-subarray method but leaves the financial encoding of its input and the subsequent line construction unexplained.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Kadane input encoding and Murrey level construction are undisclosed.

- Kadane input encoding and Murrey level construction are undisclosed.

## How it works

- Apply Kadane’s maximum-subarray-sum algorithm within a window to select the largest impulse.
- Draw Murrey’s math lines based on the chosen impulse.

## Outputs and intended use

- Use the resulting lines as chart references associated with a locally dominant move; the source supplies no breakout or reversal instruction.

## Parameters and stated settings

- A rolling window is mentioned without a disclosed length, default or line-spacing setting.

## Failure modes and caveats

- Analytical: the selected impulse can change abruptly as the window moves; a maximum-sum segment need not be a stable market structure.

## Missing information and implementation boundary

- Input encoding, signed versus absolute impulse handling, Murrey line equations and trade rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, readiness

```text
Uses Kadane's max subarray sum algorithm to find the largest impulse within a window and draws Murrey's math lines based on that impulse.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ijpiemfw_rolling_largest_impulse_murreys_lines](../tv_ijpiemfw_rolling_largest_impulse_murreys_lines.md)

## Source

https://www.tradingview.com/script/iJpIEMfW-Rolling-largest-Impulse-Murreys-Lines/

Publication ID: iJpIEMfW. Source SHA-256: a9d4eb868088540c8680ac62a808fdd2392e17c1b44065d7a5eee9785d95d3f0. Raw-description SHA-256: 780b88e94157f4acd28e5e12126b96586041db1c64c7eab92b0b8979b2ee4871.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
