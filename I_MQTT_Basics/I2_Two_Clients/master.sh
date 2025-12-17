#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PIDS=()

cleanup() {
  echo "[MASTER] Stopping clients..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

echo "[MASTER] Starting ping client (Agent1.py)"
python3 Agent1.py &
PIDS+=($!)
sleep 1

echo "[MASTER] Starting pong client (Agent2.py)"
python3 Agent2.py &
PIDS+=($!)

echo "[MASTER] Both clients started."
echo "Press CTRL+C to stop."

# Keep script alive
while true; do
  sleep 5
done
