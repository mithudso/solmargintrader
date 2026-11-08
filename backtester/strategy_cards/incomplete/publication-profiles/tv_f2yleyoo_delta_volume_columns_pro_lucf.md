---

id: tv_profile_f2yleyoo

name: "Delta Volume Columns Pro [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Inspect estimated directional volume through five balance models, with configurable columns, signal lines, divergence context and alerts. Crucially, the publication uses different historical and realtime methods and explicitly warns that refreshed elapsed realtime bars change."

registry_key: null

runner: null

evaluation: null

---

# Delta Volume Columns Pro [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Inspect estimated directional volume through five balance models, with configurable columns, signal lines, divergence context and alerts. Crucially, the publication uses different historical and realtime methods and explicitly warns that refreshed elapsed realtime bars change.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Historical directional-volume raw/EMA balances is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Historically, classify lower-timeframe bars into buy/sell bins by direction, carrying the last polarity when unchanged. Realtime mode instead accumulates price/volume feed updates; initial existing bar volume is assigned by current polarity.
- On-bar balance is buy minus sell; average balance subtracts their EMAs. Momentum balance contrasts each EMA with a double-length SMA and applies centered RSI to the directional difference. Relative balance takes positive excesses above separate EMAs, subtracts them and ALMA-smooths; percent balance smooths delta divided by total volume.
- Combined balances sum directional states. Marker bias accumulates signed events; divergence levels retain and expand signal levels on disagreement with bar polarity, leaving subsequent movement to establish direction.
- For supplied historical LTF bars sign volume by candle direction,carrying last polarity when unchanged. U,D are summed directional volumes;OnBar=U-D;Average=EMA(U,n)-EMA(D,n) with caller n/LTF. This historical branch is reproducible independently of live update/reset behavior,ALMA/marker settings and initial-polarity policy;retain data_available=false for full realtime parity and all repaint warnings.

## Outputs and intended use

- Stacked buy/sell columns or a selected balance/bias line, independent coloring/fills, divergence channels and chart-bar colors support discretionary context.
- Markers cover balance agreement, consecutive directional bumps, divergence confirmation and state/bias shifts. The author stresses uncertainty rather than predicting reversals from divergences alone.
- Usable scope: Historical directional-volume raw/EMA balances. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Separate smoothing periods, historical intrabar auto/fixed choices, signal/display/marker selection and volume-discrepancy threshold. Default historical targeting uses at least50 intrabars per chart bar.
- Combined state range is -5 to+5; momentum RSI is centered on -50/+50.

## Failure modes and caveats

- Refresh/re-execution repaints elapsed realtime bars and confirmed alerts because they recalculate through the coarser historical model. Live update history cannot be reconstructed from generic candles.
- Volume feeds differ across resolutions and instruments. Legacy platform restrictions in the description are historical claims, not current API guarantees.

## Missing information and implementation boundary

- Exact period defaults, ALMA settings, historical intrabar extraction implementation and realtime update-volume/reset behavior are not fully specified.

## Data requirements

Required inputs: lower-timeframe OHLCV for historical mode, live incremental price volume feed updates for realtime parity.

Repository input-class support: unavailable or unresolved. Historical OHLCV supports the historical proxy, but live update histories needed to reproduce realtime calculations are not established as available.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
When you refresh your chart or re-execute the script on the chart, the indicator will repaint
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
minimum of 50 intrabars
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
it ranges from −5 to +5.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
an RSI of that value is calculated and brought over the −50/+50 scale.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The final "Relative Balance" value is an ALMA of that subtraction.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
Historical bars on TradingView charts contain OHLCV data only, which is insufficient to calculate volume​ delta on them with any level of precision. To mine more detailed information from those bars we look at [I]intrabars[/i], i.e., bars from a smaller timeframe (we call it the [i]intrabar timeframe[/i]) that are contained in one chart bar. If your chart Is running at 1D on a 24x7 market for example, most 1D chart bars will contain 24 underlying 1H bars in their dilation. On historical bars, this indicator looks at those intrabars to amass volume​ delta information. If the intrabar is up, its volume​ goes in the Buy bin, and inversely for the Sell bin. When price does not move on an intrabar, the polarity of the last known movement is used to determine in which bin its volume​ goes.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
1 — [I]On Bar Balance[/i]: This is the only balance using instant values; it is simply the subtraction of the Sell volume​ from the Buy volume​ on the bar.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
2 — [I]Average Balance[/i]: Calculates a distinct EMA for both the Buy and Sell volumes, and subtracts the Sell EMA from the Buy EMA.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_f2yleyoo_delta_volume_columns_pro_lucf](../tv_f2yleyoo_delta_volume_columns_pro_lucf.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/F2ylEYOO-Delta-Volume-Columns-Pro-LucF/

Publication ID: F2ylEYOO. Source SHA-256: 46d44e080dd071a300dc92e0c1ddbd4757f3b5c00a1140cbbe380d4dcf913204. Raw-description SHA-256: 85b17bc20061e444844a3af5bd33fbe91c2e44a235d5484ea5328a29ad9ae169.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
