#!/usr/bin/env bash
# Scan for committed credentials with a pinned, checksum-verified gitleaks.
#
#   scripts/secret_scan.sh            # working tree (tracked + untracked files)  [default]
#   scripts/secret_scan.sh history    # every commit reachable from any ref
#   scripts/secret_scan.sh staged     # only what `git commit` would record
#   scripts/secret_scan.sh all        # tree then history (what CI runs)
#
# Findings print redacted; exit 1 means a finding, 2 means the scanner could not
# run. The binary is cached under ${XDG_CACHE_HOME:-~/.cache}/solmargintrader.
# Set GITLEAKS=/path/to/gitleaks to use an existing install instead.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

VERSION=8.21.2
mode="${1:-tree}"

resolve_binary() {
  if [ -n "${GITLEAKS:-}" ]; then echo "$GITLEAKS"; return; fi
  local os arch sum
  case "$(uname -s)" in Linux) os=linux ;; Darwin) os=darwin ;; *) echo "secret_scan: unsupported OS" >&2; exit 2 ;; esac
  case "$(uname -m)" in x86_64|amd64) arch=x64 ;; arm64|aarch64) arch=arm64 ;; *) echo "secret_scan: unsupported CPU" >&2; exit 2 ;; esac
  # Published in gitleaks_${VERSION}_checksums.txt; pinned here so a swapped
  # release asset fails closed instead of running.
  case "$os-$arch" in
    linux-x64)    sum=5bc41815076e6ed6ef8fbecc9d9b75bcae31f39029ceb55da08086315316e3ba ;;
    linux-arm64)  sum=654c935542c89f565aabe7bf7c6c500830f116c114f0aeb509d2460c1ac2e6da ;;
    darwin-x64)   sum=5b42c6e4b1fd693eaeb2b5b7faa5f17a1434299d4deb2de63d4b2efd7c753128 ;;
    darwin-arm64) sum=cad3de5dc9a4d5447d967a70a4d49499c557f04db028274cc324f9ff983f6502 ;;
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
common=(--config .gitleaks.toml --redact --no-banner --exit-code 1)

case "$mode" in
  tree)    "$bin" dir . "${common[@]}" ;;
  history) "$bin" git . "${common[@]}" --log-opts="--all" ;;
  staged)  "$bin" git . "${common[@]}" --staged ;;
  all)     "$bin" dir . "${common[@]}" && "$bin" git . "${common[@]}" --log-opts="--all" ;;
  *) echo "usage: scripts/secret_scan.sh [tree|history|staged|all]" >&2; exit 2 ;;
esac
