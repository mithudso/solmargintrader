#!/usr/bin/env bash
# Land a branch on master, gated. Use this instead of `git merge` by hand.
#
#   tools/land.sh <branch>          # gate, then fast-forward master onto <branch>
#   tools/land.sh <branch> --net    # also require live Jupiter reachability
#
# WHY THIS EXISTS, and it is not a style preference:
#
# **Git runs no hook for a fast-forward merge.** `pre-merge-commit` fires only when
# a merge COMMIT is created, so `git merge --ff-only` bypasses every hook there is.
# That is exactly how master was once left with a failing test — the branch was
# green when last run, went stale one commit later, and the fast-forward sailed
# through because there was nothing to stop it.
#
# So the gate has to live in the thing you run, not in a hook. This is that thing.
#
# It refuses rather than fixes: no stashing, no auto-commit, no --force anywhere,
# and it never touches a remote (this repository deliberately has none).

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && git rev-parse --path-format=absolute --git-common-dir)"
REPO_ROOT="$(dirname "$REPO_ROOT")"
cd "$REPO_ROOT"

BRANCH="${1:-}"
shift || true
if [ -z "$BRANCH" ] || [ "$BRANCH" = "-h" ] || [ "$BRANCH" = "--help" ]; then
  sed -n '2,20p' "$0"
  exit 0
fi

die() { printf 'land: %s\n' "$1" >&2; exit 1; }

git rev-parse --verify "$BRANCH" >/dev/null 2>&1 || die "no such branch: $BRANCH"

CURRENT="$(git rev-parse --abbrev-ref HEAD)"
[ "$CURRENT" = "master" ] || die "the main checkout is on '$CURRENT', not master"

# Uncommitted work in the main checkout blocks a fast-forward anyway, and another
# session may own it. Refuse; never stash someone else's work.
if [ -n "$(git status --porcelain)" ]; then
  git status --short | sed 's/^/  /' >&2
  die "main checkout is dirty — commit or set aside the above first (never stashed for you)"
fi

# Must actually be a fast-forward. If it is not, the branch owes master a merge,
# and doing that merge here would hide a conflict resolution inside a "land" step.
if ! git merge-base --is-ancestor master "$BRANCH"; then
  BEHIND="$(git rev-list --count "$BRANCH".."master")"
  die "not a fast-forward: $BRANCH is $BEHIND commit(s) behind master. Merge master into it first."
fi

if [ "$(git rev-parse master)" = "$(git rev-parse "$BRANCH")" ]; then
  echo "land: master already at $BRANCH, nothing to do"
  exit 0
fi

# Gate the BRANCH's tree, which is what is about to become master. Checking out
# the branch would disturb the working copy, so run the gate from a throwaway
# worktree of that exact commit.
TMP="$(mktemp -d)"
cleanup() { git worktree remove --force "$TMP/w" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT

echo "land: gating $BRANCH ($(git rev-parse --short "$BRANCH")) before touching master"
git worktree add --detach "$TMP/w" "$BRANCH" >/dev/null 2>&1 \
  || die "could not create a temporary worktree to gate in"

# data/ is a gitignored fetch cache that lives only in the main checkout; link it
# so the gate's data-dependent checks behave as they would on master.
[ -d data ] && ln -s "$REPO_ROOT/data" "$TMP/w/data" 2>/dev/null || true
[ -d extension/node_modules ] && ln -s "$REPO_ROOT/extension/node_modules" \
  "$TMP/w/extension/node_modules" 2>/dev/null || true

if ! (cd "$TMP/w" && ./tools/gate.sh "$@"); then
  die "gate failed on $BRANCH — master untouched"
fi

echo "land: gate passed, fast-forwarding master"
git merge "$BRANCH" --ff-only || die "fast-forward failed"
echo "land: master now at $(git rev-parse --short HEAD)"

# The tree that just landed was gated in isolation; confirm it in place too, since
# the index staleness check compares against the working tree.
echo "land: confirming in the main checkout"
./tools/gate.sh --quick || die "master is failing AFTER the merge — investigate immediately"
echo "land: PASS"
