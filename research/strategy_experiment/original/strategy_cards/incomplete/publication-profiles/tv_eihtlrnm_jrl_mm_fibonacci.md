---

id: tv_profile_eihtlrnm

name: "[JRL] MM Fibonacci"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "MM Fibonacci combines Murrey Math-derived anchor selection with Fibonacci retracement ratios. It aims to use one geometric method to decide where a long-term range begins and ends, then another to subdivide it into potential reaction levels. The author believes the combination is superior, but supplies no quantified comparison or formula. The card therefore preserves the hybrid intent without substituting a generic rolling high/low method for the undisclosed Murrey top/bottom calculation."

registry_key: null

runner: null

evaluation: null

---

# [JRL] MM Fibonacci

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

MM Fibonacci combines Murrey Math-derived anchor selection with Fibonacci retracement ratios. It aims to use one geometric method to decide where a long-term range begins and ends, then another to subdivide it into potential reaction levels. The author believes the combination is superior, but supplies no quantified comparison or formula. The card therefore preserves the hybrid intent without substituting a generic rolling high/low method for the undisclosed Murrey top/bottom calculation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core Murrey anchor-detection equations and retracement parameters are absent.

## How it works

- Use unspecified Murrey Math formulas to identify tops/bottoms.
- Draw long-term Fibonacci retracements between those anchors.

## Outputs and intended use

- Automatically anchored retracement lines support discretionary level analysis.

## Parameters and stated settings

- No periods, ratios or numeric defaults are disclosed.

## Failure modes and caveats

- Geometric levels do not establish predictive support/resistance.
- Unknown anchor timing can introduce hindsight effects.

## Missing information and implementation boundary

- Murrey range/anchor formulas, confirmation, complete Fibonacci ratios, reset rules and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price tops/bottoms and retracements use OHLCV; formula omissions are algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
uses Murrey Math formulas to find the tops and bottoms
```

### E2: outputs_and_use

```text
draw long-term fibonacci retracement levels.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eihtlrnm_jrl_mm_fibonacci](../tv_eihtlrnm_jrl_mm_fibonacci.md)

## Source

https://www.tradingview.com/script/eIHtlRnM-JRL-MM-Fibonacci/

Publication ID: eIHtlRnM. Source SHA-256: 7f01b61ed8a9e3258ffcb3016acf0a949dd8330678103724348933d27579d082. Raw-description SHA-256: be2ef4bf525e6ae1987d07231791cabe1ebc38f56ba7729437d96a125765760b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
