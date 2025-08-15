#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOGDIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGDIR"

echo "Logs: $LOGDIR"
source .venv/bin/activate
# Start the backend using `uv run main.py` if available, otherwise fall back to python3
if command -v uv >/dev/null 2>&1; then
  echo "Starting backend: uv run main.py"
  uv run main.py 2>&1 | tee "$LOGDIR/main.log" &
else
  echo "Warning: 'uv' not found in PATH. Falling back to 'python3 main.py'"
  python3 main.py 2>&1 | tee "$LOGDIR/main.log" &
fi
APP_PID=$!

# Start the Streamlit frontend
if command -v streamlit >/dev/null 2>&1; then
  echo "Starting frontend: streamlit run frontend.py"
  streamlit run frontend.py --server.port 8431 2>&1 | tee "$LOGDIR/frontend.log" &
else
  echo "Error: 'streamlit' not found in PATH. Stopping backend and exiting."
  kill "$APP_PID" 2>/dev/null || true
  exit 1
fi
FRONTEND_PID=$!

echo "Backend PID: $APP_PID, Frontend PID: $FRONTEND_PID"

cleanup() {
  echo "Shutting down processes..."
  kill -TERM "$APP_PID" 2>/dev/null || true
  kill -TERM "$FRONTEND_PID" 2>/dev/null || true
  sleep 1
  kill -KILL "$APP_PID" 2>/dev/null || true
  kill -KILL "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

if wait -n "$APP_PID" "$FRONTEND_PID" 2>/dev/null; then
  EXIT_CODE=0
else
  EXIT_CODE=$?
fi

echo "A child process exited (code: $EXIT_CODE). Cleaning up..."
cleanup
exit "$EXIT_CODE"
