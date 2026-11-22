---

id: tv_profile_a8peqinu

name: "Smart NR2-NR20 and Inside Bar (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Find unusually compressed price ranges and mark their first breakout, optionally constrained by trend and accompanied by exit annotations."

registry_key: null

runner: null

evaluation: null

---

# Smart NR2-NR20 and Inside Bar (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Find unusually compressed price ranges and mark their first breakout, optionally constrained by trend and accompanied by exit annotations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Tightness rank formula, setup replacement, breach confirmation, target multiple, timeout and exit ordering are missing.

- Tightness rank formula, setup replacement, breach confirmation, target multiple, timeout and exit ordering are missing.

## How it works

- For lengths two through twenty, compare each N-bar high-low span against its prior spans and retain the tightest candidate. Add optional inside-bar setups, adapt comparison length inversely with ADX strength and gate breakout direction relative to an EMA/RMA trend line.

## Outputs and intended use

- Project range boundaries, mark first breaks and optional target/stop/time exits. The suggested long plan enters above range, stops below it and targets a range multiple or trailing momentum; short logic reverses it.

## Parameters and stated settings

- Choose static/ADX-adaptive lookback, bounds/ADX thresholds, inside bars, trend filter, static/adaptive MA length and multiplier. Numerical defaults for these and exit parameters are not supplied.

## Failure modes and caveats

- The claim that larger lookbacks give higher-quality setups is unvalidated. Selecting the tightest among many windows creates a scanning effect, and gap/intrabar execution can differ from drawn levels.

## Missing information and implementation boundary

- Tightness rank formula, setup replacement, breach confirmation, target multiple, timeout and exit ordering are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The feature uses ordinary chart history as its financial input class; source-code behavior and market coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
searches for the tightest Narrow Range (NR) condition across NR2…NR20
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It calculates the N-bar range (highest high − lowest low).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Higher ADX (strong trend) —[/b] shorter Look Back
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Enter on a breakout above the range high
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Stop below the opposite side of the range
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_a8peqinu_smart_nr2_nr20_and_inside_bar_zeiierman](../tv_a8peqinu_smart_nr2_nr20_and_inside_bar_zeiierman.md)
- [tv_method_inside_bar](../../../strategy_research/tv_method_inside_bar.md)

## Source

https://www.tradingview.com/script/a8pEQinU-Smart-NR2-NR20-and-Inside-Bar-Zeiierman/

Publication ID: a8pEQinU. Source SHA-256: e75231607e9cd1e1da6a4f69d6298afab66dbd9f1b31bacd5ea4cc6dd33d7657. Raw-description SHA-256: 21490002dddc8ac2fd23935a888e70e423faf094de9514e437ee7fc339d53483.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
