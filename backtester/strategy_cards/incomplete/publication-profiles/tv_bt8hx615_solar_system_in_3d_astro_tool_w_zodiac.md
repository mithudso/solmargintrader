---

id: tv_profile_bt8hx615

name: "Solar System in 3D [Astro Tool w/ Zodiac]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Solar System in 3D is primarily a graphical rendering demonstration, but the author explicitly proposes it for financial astrology and visual comparison with price action. It therefore belongs in financial research tooling under the requested broad scope. It depicts timestamp-dependent geocentric planetary relationships; it does not supply evidence that those relationships predict returns or a defined trading signal."

registry_key: null

runner: null

evaluation: null

---

# Solar System in 3D [Astro Tool w/ Zodiac]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Solar System in 3D is primarily a graphical rendering demonstration, but the author explicitly proposes it for financial astrology and visual comparison with price action. It therefore belongs in financial research tooling under the requested broad scope. It depicts timestamp-dependent geocentric planetary relationships; it does not supply evidence that those relationships predict returns or a defined trading signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Major-angle aspect classification is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Use AstroLib coordinates to render celestial bodies, orbits, rotation/inclination and geocentric perspective.
- Calculate angular aspects, retrograde state and optional tropical/sidereal zodiac locations; show contextual labels and replay animation.
- Given planetary longitudes use smallest circular separation in[0,180]degrees. Match0,60,90,120,180 within caller tolerance(default1degree) to conjunction,sextile,square,trine,opposition. Rendering,coordinate production,retrograde,zodiac and trading validity remain excluded.

## Outputs and intended use

- Inspect planetary configurations alongside price in bar replay or an overlay for exploratory financial-astrology analysis.
- Usable scope: Major-angle aspect classification. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Aspect tolerance defaults to 1 degree. Major aspect angles are 0, 60, 90, 120 and 180 degrees; zodiac divides the ecliptic into twelve 30-degree sectors.
- Planets, colors, labels, resolution and view are configurable without a full default set.

## Failure modes and caveats

- Analytical: accurate astronomy does not establish a causal or predictive financial relationship; visual pattern selection can encourage confirmation bias.

## Missing information and implementation boundary

- AstroLib ephemeris/version, coordinate/time conventions, retrograde algorithm, sidereal offset and any testable trading hypothesis are not fully specified.

## Data requirements

Required inputs: timestamped astronomical ephemerides, chart timestamps.

Repository input-class support: unavailable or unresolved. Requires external AstroLib planetary coordinates and time conventions; financial OHLCV alone cannot generate them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
practical tool for Financial Astrologists.
```

### E2: parameters, readiness

```text
accuracy defined by the user (1° by default).
```

### E3: parameters, readiness

```text
Conjunction: 0° Alignment.
```

### E4: parameters, readiness

```text
Sextile: 60° Alignment.
```

### E5: parameters, readiness

```text
Square: 90° Alignment.
```

### E6: parameters, readiness

```text
Trine: 120° Alignment.
```

### E7: parameters, readiness

```text
Opposition: 180° Alignment.
```

### E8: parameters, readiness

```text
30° separation (making 12 in total)
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
This indicator supports all the Major Planetary Aspects, with an accuracy defined by the user (1° by default).
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[*] Conjunction: 0° Alignment. This draws a RED line starting from the center, and going through both planets.
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
[*] Sextile: 60° Alignment. This draws three YELLOW lines, connecting the planets to each other and to the center.
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
[*] Square: 90° Alignment. This draws three BLUE lines, connecting the planets to each other and to the center.
```

### E13: mechanism, parameters, outputs_and_use, readiness

```text
[*] Trine: 120° Alignment. This draws three PURPLE lines, connecting the planets to each other and to the center.
```

### E14: mechanism, parameters, outputs_and_use, readiness

```text
[*] Opposition: 180° Alignment. This draws a GREEN line starting from one planet, passing through the center and ending on the second planet.
```

## Source

https://www.tradingview.com/script/bT8hx615-Solar-System-in-3D-Astro-Tool-w-Zodiac/

Publication ID: bT8hx615. Source SHA-256: 6e1ff43142b781ccf0e977e984d357ced8a84adb06399c530ad2ff514739c44c. Raw-description SHA-256: a0b3fb1285cd70572a194ba946c74adbf7e1ad0853f555f7b0a5cbdb2e9a6941.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
