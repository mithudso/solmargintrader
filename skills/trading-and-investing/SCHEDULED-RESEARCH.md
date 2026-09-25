# Scheduled research pass — Jupiter unsourced citation markers

**Raised:** 2026-08-05 · **Status:** OPEN · **Owner:** unassigned
**Blocking?** No. Both files are honest as-is — every marker below is explicitly labelled `UNSOURCED`
in-file, and each file's header note states that an `UNSOURCED` marker is *not* a citation.

---

## What needs doing

21 footnote markers across two references cite claims that **have no source**. They are not broken
links — the definitions were never written by the original `/dr` research artifact, which cited five
footnote prefixes and defined only one.

| File | Markers still `UNSOURCED` |
|---|---:|
| `references/jupiter-jlp-pool.md` | **20** |
| `references/jupiter-perps-trading.md` | **1** |

A 2026-08-04 research pass resolved **32 of 52** dangling markers against 22 fetched primary sources.
These 21 are the residue.

## Why they could not be sourced — and why this needs research, not editing

The claims are overwhelmingly **IDL / on-chain account-field assertions**: `swapBps`, `taxBps`,
`tokenWeightageBufferBps`, `aumUsd`, `cumulativeInterestRate`, the `permissions` pause flag, and
`PositionRequest` slippage semantics.

Their former public home — **`dev.jup.ag/docs/old/perpetual-exchange/*` — now returns 404**, and
`docs.jup.ag/llms.txt` lists no replacement. So the sourcing gap is not laziness in the prior pass; the
documentation was withdrawn.

**Two viable routes, in order of strength:**

1. **Read the program state directly.** These are on-chain values. A Solana RPC read of the mainnet
   Pool account `5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq` and its six Custody accounts is a
   *stronger* source than the docs ever were, and is how the §1 weights table in `jupiter-jlp-pool.md`
   was already built. Prefer this.
2. **The published IDL / program repo**, if one is reachable. Cite the exact commit or program address.

If neither yields a source, **the correct outcome is to weaken or delete the claim**, not to keep the
marker. A claim that cannot be sourced after a genuine attempt should not stay in a reference file
indefinitely on the strength of a disclaimer.

## Hard rule for whoever picks this up

**Never invent a URL, page title, or source you have not fetched and read.** A fabricated citation is
worse than an unsourced claim because it manufactures false authority. Reporting "still unsourceable"
is a perfectly good result.

## Ready-to-run prompt

```
Resolve the remaining UNSOURCED footnote markers in:
  ~/.claude/skills/trading-and-investing/references/jupiter-jlp-pool.md          (20 markers)
  ~/.claude/skills/trading-and-investing/references/jupiter-perps-trading.md     (1 marker)

Read SCHEDULED-RESEARCH.md in that skill directory first — it explains why these are unsourced and
which routes are viable.

For each marker: read the claim it supports, then try (1) a direct Solana RPC read of the mainnet Pool
account 5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq and its Custody accounts, then (2) the published
IDL or program repo. Match the existing definition format used by the jup-liq-* footnotes.

NEVER invent a URL or source you have not actually fetched. If a marker still cannot be sourced,
propose weakening or deleting the underlying claim rather than leaving the marker in place — and say
which you recommend per claim.

Both files are currently under the ~10k-token ceiling (jlp ~5.7k, perps ~7.4k). If your additions push
either over, report it rather than trimming content.
```

## Related context

- The same 2026-08-04 pass found **nine contradictions** between the live docs and the published prose,
  all since corrected inline. Re-reading those corrections is a good warm-up — they show how fast this
  venue's documentation drifts.
- Venue mechanics change frequently here. Anything sourced by this pass should carry a
  `verified-as-of` stamp.
