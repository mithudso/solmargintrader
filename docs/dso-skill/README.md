# `/dso` — deep strategy optimizer (the canonical copy)

**This directory *is* the skill.** `~/.claude/skills/deep-strategy-optimizer` is a symlink to it:

```
~/.claude/skills/deep-strategy-optimizer -> <repo>/docs/dso-skill
```

`~/.claude/skills` is not version-controlled, so the content lives here instead and the loader
follows the link. There is exactly one copy, which is the point — the earlier arrangement kept two
and had to warn that they could drift. They can't now.

```
SKILL.md               the skill itself
references/passes.md   the 19 passes in detail
```

Edit these files directly. `/dso` picks the change up with no copy step, and `git` sees it.

## Recreating the link

After a fresh machine, a clone to a new path, or if the link is deleted:

```bash
ln -s /Users/mitch.hudson/dev/solmargintrader/docs/dso-skill \
      ~/.claude/skills/deep-strategy-optimizer
```

**Spell the main checkout out, and never point the link at a worktree.** `.claude/worktrees/` is
deleted when a session ends, and a link into one breaks silently — the same trap the soltui bundle
already paid for.

Do **not** derive the path with `git rev-parse --show-toplevel`: run inside a worktree that returns
the *worktree* root, so the convenient one-liner is precisely how you create the broken link. If you
want it derived rather than typed, `git rev-parse --git-common-dir` resolves to the main checkout's
`.git` from anywhere in the repo.

Two failure modes worth knowing:

- **Never leave a real directory beside the link inside `~/.claude/skills/`.** The loader reads every
  subdirectory, so a `deep-strategy-optimizer.bak` next to it registers as a *second* skill carrying
  the same description. Observed once while creating this link. Retired copies belong in
  `~/.claude/skill-consolidation/backups/`.
- If the link points somewhere unreadable the skill simply stops appearing, with no error. Check it
  with `ls -ld ~/.claude/skills/deep-strategy-optimizer`.

## The executable half

The arithmetic passes are code in the repo proper, not prose in the skill:

```bash
python3 research/dso_audit.py             # S2 deflated Sharpe, S3 evidence floor, S4 degeneracy, S5 attribution
python3 research/dso_audit.py --floor 50  # stricter evidence floor
```

It reports and never gates — gating would create an incentive to delete inconvenient strategies,
which is survivorship bias introduced by the optimizer itself.

Supporting maths, with tests pinned to the source paper's own worked figure:
`backtester/core/deflated_sharpe.py`.

Design rationale and the measured evidence behind the two-track split:
`docs/strategy-optimization-concept-family.md`.
