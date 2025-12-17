#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PIDS=()

cleanup() {
  echo "[START] Stopping all agents..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

echo "----------------------------------------"
echo "Starting Sensors (S*.py)"
echo "----------------------------------------"
for s in S*.py; do
  [ -e "$s" ] || continue
  echo "Starting $s ..."
  python3 "$s" &
  PIDS+=($!)
  sleep 1
done

echo "----------------------------------------"
echo "Starting Averaging Agents (AA*.py)"
echo "----------------------------------------"
for a in AA*.py; do
  [ -e "$a" ] || continue
  echo "Starting $a ..."
  python3 "$a" &
  PIDS+=($!)
  sleep 1
done

echo
echo "All agents started. Press CTRL+C to stop."

while true; do
  sleep 5
done
