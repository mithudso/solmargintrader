---

id: tv_profile_uyms0uuj

name: "FiniteStateMachine"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Make trading logic explicit as prioritized state transitions and concurrent-condition rules. Although the library also demonstrates traffic lights, its source explicitly combines technical conditions, position management and re-entry in a trading-strategy example, making it relevant execution infrastructure."

registry_key: null

runner: null

evaluation: null

---

# FiniteStateMachine

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Make trading logic explicit as prioritized state transitions and concurrent-condition rules. Although the library also demonstrates traffic lights, its source explicitly combines technical conditions, position management and re-entry in a trading-strategy example, making it relevant execution infrastructure.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Matrix and concurrent-map matching, wildcard precedence, ordering, return contracts and text rule formats define reproducible state transitions.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- A matrix row maps current state plus one event to next state. Concurrent rules map state to ordered condition/output pairs; their winning event can feed the sequential matrix engine.
- Blank strings and ANY serve as wildcards. Specific state/event matches outrank event wildcards, then state wildcards, then full wildcards; first encountered rules break ties within priority.
- Text loaders trim and append rules. Adding to an existing map state combines its rules instead of overwriting them. Validators check declared states, duplicate/conflicting transitions, malformed fields and unreachable/no-entry-or-exit states.

## Outputs and intended use

- Returns a next-state or event string, or na when no match exists. Rule/validation tables help inspect and debug control flow.
- The demo routes EMA/gap/fractal/RSI conditions through idle, setup, entry, position, exit and re-entry states; their actual financial thresholds are not part of this specification.

## Parameters and stated settings

- Caller state array, current state, event or active-condition names, ordered matrix/map rules, strict-input/transition flags and table options.
- Matrix text uses current state | event | next state; concurrent text maps state | condition > output pairs.

## Failure modes and caveats

- Order-dependent rules can hide unintended priorities. Validation of rule structure cannot guarantee safe trading logic or correct venue state.
- The narrative says first row wins while detailed contracts establish specificity tiers; implementations must apply first-match ordering within those tiers.

## Missing information and implementation boundary

- Strict-mode edge semantics and the full trading demo’s indicator/order rules are not explained; these are outside the basic transition computation.

## Data requirements

Required inputs: caller state/event rules and active condition names.

Repository input-class support: unavailable or unresolved. The caller must supply aligned model outputs/observations or state/event contracts; these are not provided by OHLCV alone.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Trading Strategy Demo (Concurrent FSM)
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Priority: exact match > event wildcard > state wildcard > full wildcard.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Priority: exact match > condition wildcard > state wildcard > full wildcard.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Returns: The next state or `na`.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Format: "state | condName > output | condName > output | ..."
```

## Source

https://www.tradingview.com/script/uYMS0UUJ-FiniteStateMachine/

Publication ID: uYMS0UUJ. Source SHA-256: 44911d6e4ef0ec1689bd7e4af6a744182d2764a3d6d382a84d439c21197410ee. Raw-description SHA-256: 75b18cac0996e6b1cbddc935c8ff54a4ebe02c58910f4ce507cceb236bf34597.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
