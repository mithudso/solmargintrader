#!/usr/bin/env bash
# The full local verification gate, as one command.
#
#   tools/gate.sh              # everything that does not need the network
#   tools/gate.sh --net        # also check live Jupiter reachability
#   tools/gate.sh --quick      # backtester + index only, for a pre-commit hook
#
# This exists because master was once left with a failing test: a branch was
# fast-forwarded in after its last green run but before a later commit went stale.
# See "Landing work on master" in CLAUDE.md.
#
# Exit 0 iff every selected check passes. Prints one line per check.

set -uo pipefail
cd "$(dirname "$0")/.."

QUICK=0
NET=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --net)   NET=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg (see --help)" >&2; exit 2 ;;
  esac
done

FAILED=0

run() {
  local label="$1"; shift
  local out
  if out=$("$@" 2>&1); then
    printf '  PASS  %s\n' "$label"
  else
    printf '  FAIL  %s\n' "$label"
    printf '%s\n' "$out" | tail -15 | sed 's/^/          /'
    FAILED=1
  fi
}

echo "gate: $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"

# The index goes stale on almost any file addition, and the staleness check is a
# test, so rebuild BEFORE running the suite rather than reporting a failure the
# author then has to interpret. build.py is idempotent.
if [ -f index/build.py ]; then
  if python3 index/build.py all >/dev/null 2>&1; then
    if ! git diff --quiet -- index/ 2>/dev/null; then
      printf '  NOTE  index rebuilt and is now dirty — stage index/ before committing\n'
    fi
  else
    printf '  FAIL  index rebuild\n'; FAILED=1
  fi
fi

run "backtester suite"   python3 -m unittest discover -s backtester/tests -t .
run "figure verification" python3 research/verify_numbers.py

if [ "$QUICK" -eq 0 ]; then
  run "soltui suite" python3 -m unittest discover -s soltui/tests -t .
  if [ -d extension/node_modules ] || [ -f extension/package.json ]; then
    run "extension suite" npm --prefix extension test
    # A round trip must still close positive; this is the integration gate that
    # loading the extension unpacked cannot be automated to replace.
    run "extension dry run" node extension/tools/dryrun.js --ticks 8 --osc 6 --offline 100
  fi
fi

if [ "$NET" -eq 1 ]; then
  run "jupiter reachability" node extension/tools/verify-endpoints.js
fi

if [ "$FAILED" -eq 0 ]; then
  echo "gate: PASS"
else
  echo "gate: FAIL" >&2
fi
exit "$FAILED"
