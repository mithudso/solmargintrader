---

id: tv_profile_xmke97vn

name: "Developing Market Profile / TPO [Honestcowboy]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Developing Market Profile rebuilds a rolling time-at-price distribution on each bar rather than resetting by session. It aims to expose changing market environments and retain a historical visual record of profile development. Each price zone’s importance is measured against the largest zone count, not a conventional value area. The method is TPO-like because bars visiting a zone increment its count; it is not a traded-volume profile. Computational controls limit history and visual artifacts rather than change the market hypothesis."

registry_key: null

runner: null

evaluation: null

---

# Developing Market Profile / TPO [Honestcowboy]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Developing Market Profile rebuilds a rolling time-at-price distribution on each bar rather than resetting by session. It aims to expose changing market environments and retain a historical visual record of profile development. Each price zone’s importance is measured against the largest zone count, not a conventional value area. The method is TPO-like because bars visiting a zone increment its count; it is not a traded-volume profile. Computational controls limit history and visual artifacts rather than change the market hypothesis.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines substantive parameterized calculations sufficient for reproduction.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Find rolling high/low, divide into equal zones and count one visit per bar for each zone traversed.
- Draw zone widths from occurrence counts and colors/transparency from percentage of the largest count.
- Repeat per historical bar for profile-history characters.

## Outputs and intended use

- Current horizontal profile and colored historical marks support regime/pattern study without session segmentation.

## Parameters and stated settings

- Example lookback 200; zone resolution maximum 32 due to stated plotting limits.
- Default size tiers are 20/40/60/80%; five colors, offset, borders, square history character and visibility are configurable.
- Calculate from here limits computation; Min Size mitigates zero-reaching visual bugs.

## Failure modes and caveats

- Bar visitation does not measure actual time spent continuously or executed volume at each price.
- Changing rolling extrema shifts bins, making profiles across bars not perfectly comparable.

## Missing information and implementation boundary

- Exact zone-overlap boundary/tie convention and Min Size behavior are absent; core rolling occurrence-profile calculation is disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Rolling ranges and candle-zone overlap use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
add +1 to the zones price was in
```

### E2: parameters

```text
lookback 200 bars
```

### E3: parameters

```text
maximum of 32
```

### E4: parameters

```text
top 20% will be red, top 40% purple, top 60% blue, top 80% green
```

### E5: outputs_and_use

```text
Does not have a value area
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_xmke97vn_developing_market_profile_tpo_honestcowboy](../tv_xmke97vn_developing_market_profile_tpo_honestcowboy.md)

## Source

https://www.tradingview.com/script/XMKe97Vn-Developing-Market-Profile-TPO-Honestcowboy/

Publication ID: XMKe97Vn. Source SHA-256: fae70797ed28d5930d5f1a25034e618e85e3d815669e8765eb07230cc64519c2. Raw-description SHA-256: 00159be75a3938f15997f4c2867ac8dc5e4d90d37e5c5b079d83542bd0c686be.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
