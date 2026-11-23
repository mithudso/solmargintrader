---

id: tv_profile_00jfil5w

name: "`security()` revisited [PineCoders]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "This PineCoders educational example compares ways of requesting higher-timeframe market values and explains why historical plots can conceal realtime repainting. Its leading correction explicitly withdraws endorsement of the bar-state technique originally presented as a universal non-repainting solution."

registry_key: null

runner: null

evaluation: null

---

# `security()` revisited [PineCoders]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

This PineCoders educational example compares ways of requesting higher-timeframe market values and explains why historical plots can conceal realtime repainting. Its leading correction explicitly withdraws endorsement of the bar-state technique originally presented as a universal non-repainting solution.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The historical wrapper equation and its example arguments are explicitly printed, making its offset computation reproducible despite the prominent author deprecation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- The supplied f_security wrapper accepts symbol, requested timeframe, source expression and a repaint flag. Repainting mode leaves both history offsets at zero. The proposed alternative uses a source offset on realtime bars and an output offset on historical bars, intending to deliver the preceding confirmed higher-timeframe observation.
- Chart bands distinguish historical, elapsed realtime and active realtime bars. Multiple comparison plots expose different alignment behavior, including deliberately misleading early historical updates. Tuple results require offsets inside the tuple-producing function and after assignment rather than passing the tuple through the wrapper.

## Outputs and intended use

- Use the plots and Data Window offset/bar-state values to study higher-timeframe market-data timing. The wrapper is a documented historical implementation example, with the explicit deprecation retained as a material limitation; it is not a validated current recommendation.

## Parameters and stated settings

- Repaint defaults off. Inputs select the source, requested timeframe and whether to show a reminder. The supplied example requests daily close for the current symbol with repaint false; the chart demonstration compares a five-second chart with one-minute requested values.

## Failure modes and caveats

- The author has identified inconsistencies undermining universal reliability. Different historical/realtime or intraday/daily feeds can revise values. A source is not available early merely because its historical plot is shifted; using such plots can invalidate backtests.

## Missing information and implementation boundary

- The full comparison-script and tuple helper implementations are absent. Current replacement practice is linked externally but is outside this cached description.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The financial example requests chart-symbol higher-timeframe OHLC values; sufficiently granular OHLCV provides the data class, without guaranteeing platform feed parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, risks, readiness

```text
The non-repainting technique in this publication that relies on bar states is now deprecated
```

### E2: mechanism, parameters, risks, readiness

```text
f_security(_sym, _res, _src, _rep) => security(_sym, _res, _src[not _rep and barstate.isrealtime ? 1 : 0])[_rep or barstate.isrealtime ? 0 : 1]
```

### E3: mechanism, parameters, risks, readiness

```text
previousDayClose = f_security(syminfo.tickerid, "D", close, false)
```

### E4: mechanism, parameters, risks, readiness

```text
"Repaint" = "On" (the default is "Off")
```

### E5: mechanism, parameters, risks, readiness

```text
letting our 5sec chart run for a few minutes
```

## Source

https://www.tradingview.com/script/00jFIl5w-security-revisited-PineCoders/

Publication ID: 00jFIl5w. Source SHA-256: eb280b16308bac9d2e157b61d602e9ce2d28ce4f6cdf1e4c13c5a03fc01e6163. Raw-description SHA-256: 489c120a3ce34b375fa4382ecae81c61e5696aaf00ded352cc5c388d95bb89d5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
