#!/usr/bin/env bash
# Point this clone's git at .githooks/, once.
#
#   tools/install-hooks.sh
#
# `core.hooksPath` is per-clone local config, not something a commit can set, so a
# fresh clone has no hooks until this runs. It is set on the COMMON git dir, so
# every worktree of this repository picks the hooks up too.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

chmod +x .githooks/* tools/*.sh 2>/dev/null || true
git config core.hooksPath .githooks

echo "hooks installed: core.hooksPath = $(git config --get core.hooksPath)"
echo
echo "  pre-commit         rebuilds + stages index/, refuses a red backtester suite"
echo "  pre-merge-commit   runs tools/gate.sh --quick before a merge commit"
echo
echo "Git runs NO hook for a fast-forward merge, so use tools/land.sh <branch>"
echo "to put a branch on master. Bypass either hook with --no-verify."
