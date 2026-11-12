#!/usr/bin/env bash
# Run research/tick_backfill.py as a polite, long-lived background job.
#
# "Polite" means three separate things, and only the first is obvious:
#
#   1. CPU. `nice -n 19` is the weakest scheduling priority, so the job yields
#      to anything interactive.
#   2. I/O and thermals. On macOS `taskpolicy -b` puts the process in the
#      background QoS tier (throttled disk I/O, parked on efficiency cores on
#      Apple silicon). nice alone does not do this, and a job that saturates
#      the SSD is felt even at nice 19.
#   3. The network. The job is rate-limited in Python (--pause), because the
#      thing most likely to disrupt other work here is exhausting a shared
#      public API quota, which no scheduler priority can mitigate.
#
# It detaches from the terminal, survives the shell closing, checkpoints as it
# goes, and can be stopped with `--stop` without losing progress.
#
#   ./research/run_backfill.sh                 # start (or resume) in background
#   ./research/run_backfill.sh --status        # progress
#   ./research/run_backfill.sh --tail          # follow the log
#   ./research/run_backfill.sh --stop          # checkpoint and stop

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() {
    echo "Usage: $0 [start|--status|--tail|--stop|--help]"
}
if [[ $# -gt 1 ]]; then
    usage >&2
    exit 2
fi
ACTION="${1:-start}"
case "$ACTION" in
  -h|--help) usage; exit 0 ;;
  start|--status|--tail|--stop) ;;
  *) usage >&2; exit 2 ;;
esac
# Output goes to BACKFILL_HOME, which defaults to the repo this script lives in
# but should be pointed at the main checkout when running from a git worktree:
# a worktree is deleted at the end of a session, and a job that runs for hours
# must not write its only copy of the results into it.
HOME_DIR="${BACKFILL_HOME:-$REPO}"
LOG_DIR="$HOME_DIR/data/logs"
LOG="$LOG_DIR/tick_backfill.log"
PIDFILE="$LOG_DIR/tick_backfill.pid"
ASSETS="${BACKFILL_ASSETS:-DOGE,ZEC,SOL,BTC,ETH}"
START="${BACKFILL_START:-2026-07-06}"
END="${BACKFILL_END:-2026-08-06}"
PAUSE="${BACKFILL_PAUSE:-0.15}"
REPORT="${BACKFILL_REPORT:-$HOME_DIR/research/TICK-BACKFILL-AUDIT.md}"
PYTHON="${BACKFILL_PYTHON:-$REPO/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
    printf 'Missing repository Python environment. Create it with: uv venv %q --python 3.13\n' "$REPO/.venv" >&2
    printf 'Then: uv pip install --python %q -e %q\n' "$REPO/.venv/bin/python" "$REPO/backtester" >&2
    exit 3
fi

running() {
    VERIFIED_PID=""
    [[ -f "$PIDFILE" ]] || return 1
    local collector_pid collector_command
    collector_pid="$(cat "$PIDFILE")"
    [[ "$collector_pid" =~ ^[1-9][0-9]*$ ]] || return 1
    collector_command="$(ps -p "$collector_pid" -o command= 2>/dev/null)" || return 1
    # A PID alone is not ownership. Refuse ambiguous/legacy command lines rather
    # than signalling or replacing an unrelated process's saved owner record.
    if "$PYTHON" - "$collector_command" "$REPO/research/tick_backfill.py" "$HOME_DIR" "$PYTHON" "$REPORT" <<'PY'
import os
import shlex
import sys
from pathlib import Path

try:
    arguments = shlex.split(sys.argv[1])
    script, home, interpreter, report = sys.argv[2:]
    valid = (len(arguments) >= 3 and os.path.isabs(arguments[0])
             and os.path.realpath(arguments[0]) == os.path.realpath(interpreter)
             and arguments[1:3] == ['-u', script])
    expected = {'--data-dir': str(Path(home) / 'data'),
                '--out-dir': str(Path(home) / 'data/authoritative'),
                '--checkpoint-dir': str(Path(home) / 'data/checkpoints'),
                '--report': report}
    for flag, value in expected.items():
        valid = valid and arguments.count(flag) == 1
        if valid:
            actual = arguments[arguments.index(flag) + 1]
            valid = os.path.isabs(actual) and os.path.normpath(actual) == os.path.normpath(value)
except (ValueError, IndexError):
    valid = False
raise SystemExit(0 if valid else 1)
PY
    then
        VERIFIED_PID="$collector_pid"
        return 0
    fi
    return 1
}

case "$ACTION" in
  --status)
        if running; then
            echo "running (pid $VERIFIED_PID)"
        else
            echo "not running or collector identity is unverified"
        fi
        echo "--- checkpoints:"
        for f in "$HOME_DIR"/data/checkpoints/*.json; do
            [[ -e "$f" ]] || { echo "  none yet"; break; }
            "$PYTHON" - "$f" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
with path.open() as stream:
    state = json.load(stream)
print(f"  {path.name}: {state['trades']} trades, {state['pages']} pages, done={state['done']}")
PY
        done
        echo "--- last log lines:"
        [[ -f "$LOG" ]] && tail -5 "$LOG" || echo "  no log yet"
        exit 0
        ;;
  --tail)
        exec tail -f "$LOG"
        ;;
  --stop)
        if running; then
            # SIGTERM, not SIGKILL: the script traps it, finishes the current
            # page and checkpoints. Killing it outright costs the current batch.
            kill -TERM "$VERIFIED_PID"
            echo "stop requested; it will checkpoint and exit within a page"
        else
            echo "not running or collector identity is unverified; no signal sent"
            [[ ! -f "$PIDFILE" ]] || exit 1
        fi
        exit 0
        ;;
esac

if [[ -f "$PIDFILE" ]]; then
    if running; then
        echo "already running (pid $(cat "$PIDFILE")). Use --status, --tail or --stop." >&2
    else
        echo "Refusing existing unverified collector PID record; no launch or replacement." >&2
    fi
    exit 1
fi
if ! "$PYTHON" -c 'import pandas' >/dev/null 2>&1; then
    printf 'Missing pandas. Install in the repository environment: uv pip install --python %q -e %q\n' "$PYTHON" "$REPO/backtester" >&2
    exit 3
fi
mkdir -p "$LOG_DIR"

# taskpolicy is macOS-only; fall back to plain nice elsewhere.
if command -v taskpolicy >/dev/null 2>&1; then
    LAUNCH=(taskpolicy -b nice -n 19)
else
    LAUNCH=(nice -n 19)
fi

echo "starting: assets=$ASSETS window=$START..$END pause=${PAUSE}s"
echo "output home: $HOME_DIR"
echo "log: $LOG"

cd "$REPO"
nohup "${LAUNCH[@]}" "$PYTHON" -u "$REPO/research/tick_backfill.py" \
    --assets "$ASSETS" --start "$START" --end "$END" --pause "$PAUSE" \
    --data-dir "$HOME_DIR/data" \
    --out-dir "$HOME_DIR/data/authoritative" \
    --checkpoint-dir "$HOME_DIR/data/checkpoints" \
    --report "$REPORT" \
    >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"

echo "pid $(cat "$PIDFILE") — safe to close this terminal."
echo "progress: ./research/run_backfill.sh --status"
