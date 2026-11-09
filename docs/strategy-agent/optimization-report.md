# Prompt optimization checkpoint

The original request is retained in `prompts.md`. The candidate is in
`docs/strategy-agent/optimized-prompt.md`. This is a structural rewrite, not an
empirically validated prompt: no labeled prompt-evaluation dataset was supplied.

The initial audit covered all 16 prompt-deep-optimizer domains in three isolated
review bundles. Findings included missing transaction direction and size,
unsupported assumptions about the manager and Oracle, unspecified reporting,
unbounded experimentation, and contamination of a blind forward test. The
candidate adds explicit provenance, chronological splits, bounded experiments,
manager reporting, prospective gate definitions, and existing executor safety.

A later fresh-context audit identified additional issues in manager reporting,
voice, universe coverage and improvement approaches; the candidate was revised.
Another fresh-context review found gaps in precommitted test criteria, budgets,
benchmark definitions, output checking and examples; the candidate was revised
again. Those latest revisions have not received a fresh independent blind audit.
A helper validated the example-plan declaration, but it ran after the first
rewrite; the required pre-rewrite timing was missed. The original and candidate
were also compared by two isolated reviewers on normal, missing-data and
adversarial-Oracle scenarios. These were hypothetical checks, not executable
trading or agent acceptance tests. No CLEAN or optimizer convergence is claimed.

The owner's live authorization in `CLAUDE.md` is already established. The
independent review's suggestion to require a new authorization for each swap
does not override that authorization. Order direction, feasible amount and all
existing technical gates still need to be established.

A final fresh-context review after the checkpoint found an unresolved conflict: the candidate requires a manager record before the first agent action, although read-only discovery must happen first. It also found that the primary example does not demonstrate the full authoring and delivery sequence and that material capability and outcome claims need traceable source or receipt references. These findings remain unresolved in the candidate. Optimizer status is incomplete; no CLEAN, blind-gate pass, or convergence is claimed.
