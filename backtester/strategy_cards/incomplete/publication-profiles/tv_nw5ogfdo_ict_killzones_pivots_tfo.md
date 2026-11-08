---

id: tv_profile_nw5ogfdo

name: "ICT Killzones + Pivots [TFO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "ICT Killzones + Pivots preserves the price extremes established during configurable session windows. It is designed to keep potentially relevant session highs and lows visible after the session has ended, rather than requiring the user to redraw them. Optional opening-price references and timestamps add temporal context. This is a chart organization tool: the description does not claim that a session extreme predicts a reversal or prescribe a trade when price reaches it."

registry_key: null

runner: null

evaluation: null

---

# ICT Killzones + Pivots [TFO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

ICT Killzones + Pivots preserves the price extremes established during configurable session windows. It is designed to keep potentially relevant session highs and lows visible after the session has ended, rather than requiring the user to redraw them. Optional opening-price references and timestamps add temporal context. This is a chart organization tool: the description does not claim that a session extreme predicts a reversal or prescribe a trade when price reaches it.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for high/low tracking of chosen sessions under an explicit caller time contract. Optional opening lines and level-extension/invalidation parity remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For each caller-configured session and explicit timezone/bar-inclusion contract, reset High/Low on entry, update High=max(included highs) and Low=min(included lows), and retain those extrema after the window closes. This independent session-extrema output does not depend on optional open lines, cutoff behavior or exact traded-through equality.
- Track each enabled session high and low as bars arrive during its configured window.
- Extend the resulting pivot levels until price trades through them or a configured drawing cutoff is reached.

## Outputs and intended use

- Use session boxes and extended extremes as references for later price interaction.
- Add optional opening-price lines and vertical time markers with individual styles.

## Parameters and stated settings

- Five session windows, four optional open-price lines and four timestamp markers are provided.
- Session times/labels and a cutoff time are customizable; cutoff behavior is enabled by default.
- Caller provides session start/end and timezone with known inclusion of bars at boundaries; five session slots are available. Default ICT timing and DST behavior are not supplied.

## Failure modes and caveats

- Session timezone and daylight-saving interpretation can change the bars included.
- A traded-through level is an invalidated drawing, not proof of an executable fill.

## Missing information and implementation boundary

- Default windows, timezone, exact through-price equality behavior and open-price sampling are not stated.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the default input class; this does not establish source-code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
There are 5 Killzones / sessions
```

### E2: parameters

```text
4 optional Open Price lines and 4 vertical Timestamps
```

### E3: purpose, mechanism

```text
storing their highs and lows for future reference, until traded through.
```

### E4: mechanism

```text
Cutoff Time where all drawings will stop extending
```

### E5: mechanism, parameters, readiness

```text
sessions are fully customizable.
```

### E6: mechanism, parameters, readiness

```text
keep track of the highs and lows made during their respective times
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_nw5ogfdo_ict_killzones_pivots_tfo](../../tv_nw5ogfdo_ict_killzones_pivots_tfo.md)

## Source

https://www.tradingview.com/script/nW5oGfdO-ICT-Killzones-Pivots-TFO/

Publication ID: nW5oGfdO. Source SHA-256: 882b773336e6d0cc743b791cd758f6c17c4e423609d2acb8fbf71fff951ce07f. Raw-description SHA-256: 5d8f3d85c959d1883db76888552cc3434079e3e5ce4554935d2f88ee573fe2bd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
