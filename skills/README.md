# skills/

Version-controlled copies of the Claude Code skills this project's research depends on.

## Why a copy lives here

The live skills are installed at `~/.claude/skills/`, which is outside this repository and not
version-controlled. Several of this project's research documents cite them as the source of a
method or a convention — `research/RANKED_LISTS.md` on CPCV and PBO, the strategy cards on
signal definitions, `backtester/core/fetch_minutes.py` on the venue/universe reasoning. A citation
to a file that only exists on one machine is not a citation, so the copy is here to make those
references resolvable and to record which version of the guidance a result was produced under.

## This is a COPY, not the source of truth

`~/.claude/skills/trading-and-investing/` is what Claude Code actually loads. Editing the copy here
changes nothing at runtime. Re-sync after changing the live skill:

    rsync -a --delete ~/.claude/skills/trading-and-investing/ skills/trading-and-investing/

If the two diverge, the live one wins — this directory is documentation of a dependency, not the
dependency itself.

## What is here

`trading-and-investing/` — the foundation-and-hub skill for markets and active trading, plus its
`references/` spokes. Educational material only, **not financial advice**; every reference carries
its own disclaimer and its own cited primary sources (SEC, FINRA, CFTC, OCC, Cboe, CME, IRS, BIS).
