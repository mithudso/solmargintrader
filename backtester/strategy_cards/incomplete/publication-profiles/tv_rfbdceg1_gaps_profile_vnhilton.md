---

id: tv_profile_rfbdceg1

name: "Gaps Profile [vnhilton]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Gaps Profile tracks price gaps that remain unclosed and arranges them into a compact chart profile. Its gap definition uses current open versus previous close, distinct from a full-bar high/low void. The author suggests these remaining intervals as possible reaction or supply/demand areas; the display does not establish that price must fill them."

registry_key: null

runner: null

evaluation: null

---

# Gaps Profile [vnhilton]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Gaps Profile tracks price gaps that remain unclosed and arranges them into a compact chart profile. Its gap definition uses current open versus previous close, distinct from a full-bar high/low void. The author suggests these remaining intervals as possible reaction or supply/demand areas; the display does not establish that price must fill them.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Partial-fill definition, touch/close criterion, gap aging, duplicate overlap handling and defaults are not supplied.

- Partial-fill definition, touch/close criterion, gap aging, duplicate overlap handling and defaults are not supplied.

## How it works

- Detect open-to-prior-close gaps above a percentage threshold, retain unclosed portions and draw overlapping gap boxes from a chosen side.
- Limit displayed gaps by discarding those farthest from price and optionally emphasize largest/newest gaps.

## Outputs and intended use

- Inspect remaining up/down gaps and their proximity for contextual price-reaction planning.

## Parameters and stated settings

- Displays 3–499 gaps; inputs include minimum gap percentage, four color themes, profile side/offset and borders.

## Failure modes and caveats

- The source warns of loop execution above 500ms and suggests fewer boxes/higher threshold; analytical: distant gaps may be removed without being filled.

## Missing information and implementation boundary

- Partial-fill definition, touch/close criterion, gap aging, duplicate overlap handling and defaults are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
3 to 499 remaining up/down gaps
```

### E2: parameters, readiness

```text
4 GP color themes
```

### E3: parameters, risks, readiness

```text
loop running longer than >500ms
```

### E4: mechanism, readiness

```text
distance between the current open and the previous close.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_rfbdceg1_gaps_profile_vnhilton](../tv_rfbdceg1_gaps_profile_vnhilton.md)

## Source

https://www.tradingview.com/script/rfBdCeg1-Gaps-Profile-vnhilton/

Publication ID: rfBdCeg1. Source SHA-256: 3efb1565a624b4987480b0ed0e346962f0f3ac4914bc56066c77f7e1d70f44c9. Raw-description SHA-256: 17e1abcab8a31a7d63b52755af50f2efaf83139797c6be26ba75d6d6ad461ddc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
