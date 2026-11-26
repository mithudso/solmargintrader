#!/usr/bin/env bash
# Scan for committed credentials with a pinned, checksum-verified gitleaks.
#
#   scripts/secret_scan.sh            # tracked files at HEAD  [default]
#   scripts/secret_scan.sh history    # every commit reachable from any ref
#   scripts/secret_scan.sh staged     # only what `git commit` would record
#   scripts/secret_scan.sh all        # tree then history (what CI runs)
#
# Findings print redacted; exit 1 means a finding, 2 means the scanner could not
# run. The binary is cached under ${XDG_CACHE_HOME:-~/.cache}/solmargintrader.
# Set GITLEAKS=/path/to/gitleaks to use an existing install instead.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

VERSION=8.28.0
mode="${1:-tree}"

resolve_binary() {
  if [ -n "${GITLEAKS:-}" ]; then echo "$GITLEAKS"; return; fi
  local os arch sum
  case "$(uname -s)" in Linux) os=linux ;; Darwin) os=darwin ;; *) echo "secret_scan: unsupported OS" >&2; exit 2 ;; esac
  case "$(uname -m)" in x86_64|amd64) arch=x64 ;; arm64|aarch64) arch=arm64 ;; *) echo "secret_scan: unsupported CPU" >&2; exit 2 ;; esac
  # Published in gitleaks_${VERSION}_checksums.txt; pinned here so a swapped
  # release asset fails closed instead of running.
  case "$os-$arch" in
    linux-x64)    sum=a65b5253807a68ac0cafa4414031fd740aeb55f54fb7e55f386acb52e6a840eb ;;
    linux-arm64)  sum=eff65261156100e5d94a6b3dec313d532fddfe19ae1590bf7a2b4f2699128356 ;;
    darwin-x64)   sum=edf5a507008b0d2ef4959575772772770586409c1f6f74dabf19cbe7ec341ced ;;
    darwin-arm64) sum=d942f3ad147250c9edbaab3fed9e482f98d3b59ba10ae97b8d75647e3ade492c ;;
  esac
  local dir="${XDG_CACHE_HOME:-$HOME/.cache}/solmargintrader/gitleaks-$VERSION"
  local bin="$dir/gitleaks"
  if [ ! -x "$bin" ]; then
    command -v gitleaks >/dev/null 2>&1 && gitleaks version 2>/dev/null | grep -q "$VERSION" && { command -v gitleaks; return; }
    mkdir -p "$dir"
    local tgz="$dir/gitleaks.tar.gz"
    curl -fsSL -o "$tgz" "https://github.com/gitleaks/gitleaks/releases/download/v$VERSION/gitleaks_${VERSION}_${os}_${arch}.tar.gz" \
      || { echo "secret_scan: download failed" >&2; exit 2; }
    if ! echo "$sum  $tgz" | sha256sum -c --status 2>/dev/null && ! echo "$sum  $tgz" | shasum -a 256 -c --status 2>/dev/null; then
      rm -f "$tgz"; echo "secret_scan: checksum mismatch for $os-$arch; refusing to run" >&2; exit 2
    fi
    tar -xzf "$tgz" -C "$dir" gitleaks && rm -f "$tgz"
  fi
  echo "$bin"
}

bin="$(resolve_binary)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
policy="$PWD/.gitleaks.toml"
common=(--config "$policy" --redact --no-banner --exit-code 1 --report-format json \
  --max-target-megabytes 2)  # zipped research artefacts and data dumps hold no config

# Print rule, file and line for each finding (secrets already redacted), so a
# red CI log says what to fix without anyone re-running the scan.
summarise() {
  python3 - "$1" <<'PY'
import json, sys, collections
try:
    rows = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(0)
for r in rows[:300]:
    where = r.get("File", "")
    if r.get("Commit"):
        where = r["Commit"][:8] + ":" + where
    print(f"  {r.get('RuleID')}\t{where}:{r.get('StartLine')}")
if len(rows) > 300:
    print(f"  ... {len(rows) - 300} more")
by = collections.Counter(r.get("RuleID") for r in rows)
print("  by rule: " + ", ".join(f"{k}={v}" for k, v in by.most_common()))
PY
}

run() {  # run <label> <gitleaks args...>
  local label="$1"; shift
  local report="$work/$label.json"
  if "$bin" "$@" "${common[@]}" --report-path "$report"; then
    echo "secret_scan: $label clean"
  else
    local rc=$?
    echo "secret_scan: $label findings:" >&2
    summarise "$report" >&2
    return "$rc"
  fi
}

# The tree scan reads exactly the tracked files at HEAD (git archive), so a
# local virtualenv, node_modules or .git object store never produces noise.
scan_tree() {
  mkdir -p "$work/tree"
  git archive --format=tar HEAD | tar -x -C "$work/tree"
  (cd "$work/tree" && run tree dir .)
}

case "$mode" in
  tree)    scan_tree ;;
  history) run history git . --log-opts="--all" ;;
  staged)  run staged git . --staged ;;
  all)     rc=0; scan_tree || rc=$?; run history git . --log-opts="--all" || rc=$?; exit "$rc" ;;
  *) echo "usage: scripts/secret_scan.sh [tree|history|staged|all]" >&2; exit 2 ;;
esac
