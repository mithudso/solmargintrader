# `/dso` — deep strategy optimizer (in-repo mirror)

The live skill is installed at `~/.claude/skills/deep-strategy-optimizer/`, which is where
`/dso` resolves from. **`~/.claude/skills` is not version-controlled**, so this directory is a
committed mirror: the copy that survives a machine change or a deleted worktree.

```
SKILL.md               the skill (mirror of the installed copy)
references/passes.md   the 19 passes in detail
```

Reinstall from here with:

```bash
mkdir -p ~/.claude/skills/deep-strategy-optimizer/references
cp docs/dso-skill/SKILL.md ~/.claude/skills/deep-strategy-optimizer/
cp docs/dso-skill/references/passes.md ~/.claude/skills/deep-strategy-optimizer/references/
```

**These two copies can drift.** Whichever is edited, copy it to the other in the same commit.

The arithmetic half of the skill's statistical passes is executable and lives in the repo proper:

```bash
python3 research/dso_audit.py          # passes S2, S3, S4, S5 over the CPCV result CSVs
```

Design rationale and the measured evidence behind it:
`docs/strategy-optimization-concept-family.md`.
