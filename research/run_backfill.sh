#!/usr/bin/env bash
# Explicit control only; paths never become executable Python source.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$REPO/research/backfill_control.py" "$@"
