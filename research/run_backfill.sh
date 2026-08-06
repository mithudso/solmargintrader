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

mkdir -p "$LOG_DIR"

running() {
    [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

case "${1:-start}" in
  --status)
        if running; then
            echo "running (pid $(cat "$PIDFILE"), nice $(ps -o nice= -p "$(cat "$PIDFILE")" | tr -d ' '))"
        else
            echo "not running"
        fi
        echo "--- checkpoints:"
        for f in "$HOME_DIR"/data/checkpoints/*.json; do
            [[ -e "$f" ]] || { echo "  none yet"; break; }
            python3 -c "
import json,sys
s=json.load(open('$f'))
print(f\"  {'$f'.split('/')[-1]}: {s['trades']} trades, {s['pages']} pages, done={s['done']}\")
"
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
            kill -TERM "$(cat "$PIDFILE")"
            echo "stop requested; it will checkpoint and exit within a page"
        else
            echo "not running"
        fi
        exit 0
        ;;
esac

if running; then
    echo "already running (pid $(cat "$PIDFILE")). Use --status, --tail or --stop." >&2
    exit 1
fi

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
nohup "${LAUNCH[@]}" python3 -u research/tick_backfill.py \
    --assets "$ASSETS" --start "$START" --end "$END" --pause "$PAUSE" \
    --data-dir "$HOME_DIR/data" \
    --out-dir "$HOME_DIR/data/authoritative" \
    --checkpoint-dir "$HOME_DIR/data/checkpoints" \
    --report "$REPORT" \
    >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"

echo "pid $(cat "$PIDFILE") — safe to close this terminal."
echo "progress: ./research/run_backfill.sh --status"
