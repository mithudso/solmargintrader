---

id: tv_profile_fvpgxfb3

name: "Wolfe Scanner (Multi - zigzag) [HeWhoMustNotBeNamed]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Wolfe Scanner seeks wedge-based Wolfe formations from multiple zigzag structures and draws a projected target reference. The author explains that pure Fibonacci-ratio matching did not consistently agree with visual inspection, motivating a wedge-first approach. Its financial intent is pattern identification and visual target/stop context, but the prose does not specify the actual wedge detector or a complete entry rule."

registry_key: null

runner: null

evaluation: null

---

# Wolfe Scanner (Multi - zigzag) [HeWhoMustNotBeNamed]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Wolfe Scanner seeks wedge-based Wolfe formations from multiple zigzag structures and draws a projected target reference. The author explains that pure Fibonacci-ratio matching did not consistently agree with visual inspection, motivating a wedge-first approach. Its financial intent is pattern identification and visual target/stop context, but the prose does not specify the actual wedge detector or a complete entry rule.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Zigzag lengths, wedge convergence/tolerance, pivot ordering, entry trigger and stop/target execution timing are absent.

- Zigzag lengths, wedge convergence/tolerance, pivot ordering, entry trigger and stop/target execution timing are absent.

## How it works

- Find wedges using the inherited zigzag/wedge approach, then connect the identified first and fourth pivots for the Wolfe target line.
- Use the converging trendline as the author’s stop-loss reference.

## Outputs and intended use

- Inspect wedge geometry and the pivot-connection target as a trade-planning aid.

## Parameters and stated settings

- Pivots one and four define the target line. Settings are described only in a linked chart image; no lengths/ratios/defaults are transcribed.

## Failure modes and caveats

- Analytical: zigzag confirmation can lag and subjective wedge acceptance materially changes formations; a projected line is not a guaranteed destination.

## Missing information and implementation boundary

- Zigzag lengths, wedge convergence/tolerance, pivot ordering, entry trigger and stop/target execution timing are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
draw a line joining pivot 1 and 4
```

### E2: outputs_and_use, readiness

```text
Converging trendline forms the stop loss
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fvpgxfb3_wolfe_scanner_multi_zigzag_hewhomustnotbenamed](../tv_fvpgxfb3_wolfe_scanner_multi_zigzag_hewhomustnotbenamed.md)
- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)

## Source

https://www.tradingview.com/script/fVPGXfB3-Wolfe-Scanner-Multi-zigzag-HeWhoMustNotBeNamed/

Publication ID: fVPGXfB3. Source SHA-256: 1bb2ef7b50e66e11cecacb644f1faa7cd0b1b4c3b4ee2738f210d0fd5071cbaf. Raw-description SHA-256: 129afb12c549ec9fa28422696d9b9022ece36e615f5bafe2359d6317ce1e5726.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
