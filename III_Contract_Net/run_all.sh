#!/usr/bin/env bash
set -euo pipefail

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# venv (same idea as .bat: repo root/.venv)
VENV_ACT="$PROJ_ROOT/.venv/bin/activate"
if [[ ! -f "$VENV_ACT" ]]; then
  echo "Virtual environment not found at:"
  echo "  $PROJ_ROOT/.venv"
  echo "----------------------------------------------"
  echo "HOW TO SET IT UP (Linux):"
  echo "  cd \"$PROJ_ROOT\""
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install --upgrade pip"
  echo "  pip install paho-mqtt"
  echo "----------------------------------------------"
  exit 1
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_ACT"

BROKER="${BROKER:-localhost}"
PORT="${PORT:-1883}"
DEADLINE="${DEADLINE:-0.8}"
WAIT_DONE="${WAIT_DONE:---wait-done}"

# Choose supervisor (default: supervisor.py). To use opt:
#   SUPERVISOR=supervisor_opt ./run_all.sh
SUPERVISOR="${SUPERVISOR:-supervisor}"

# Jobs list (comma-separated as in the .bat)
JOBS="${JOBS:-cut,drill,paint,cut,drill,paint,cut,drill,paint,cut,drill,paint,cut,drill,paint}"

declare -a PIDS=()

cleanup() {
  echo
  echo "[RUN_ALL] Stopping machines..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

# Machine definitions: ID + capabilities "job:seconds,job:seconds,..."
declare -A CAPS
CAPS["M01"]="cut:1.8,drill:4.5,paint:1.2"
CAPS["M02"]="cut:2.4,drill:2.1,paint:2.0"
CAPS["M03"]="cut:3.0,drill:1.9,paint:2.6"
CAPS["M04"]="cut:2.2,drill:3.8,paint:1.4"
CAPS["M05"]="cut:1.9,drill:4.2,paint:1.8"
CAPS["M06"]="cut:2.8,drill:2.5,paint:1.6"
CAPS["M07"]="cut:3.6,drill:1.7,paint:2.2"
CAPS["M08"]="cut:2.1,drill:3.1,paint:1.3"
CAPS["M09"]="cut:2.7,drill:2.3,paint:1.9"
CAPS["M10"]="cut:3.2,drill:2.0,paint:2.1"
CAPS["M11"]="cut:2.5,drill:2.7,paint:1.5"
CAPS["M12"]="cut:1.7,drill:3.9,paint:1.7"

echo "[RUN_ALL] Launching 12 machines..."
for mid in M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11 M12; do
  python3 -u "$SCRIPT_DIR/machine.py" \
    --id "$mid" \
    --caps "${CAPS[$mid]}" \
    --broker "$BROKER" \
    --port "$PORT" \
    > "$SCRIPT_DIR/log_${mid}.txt" 2>&1 &
  PIDS+=($!)
  echo "  - $mid (pid=${PIDS[-1]}) log=log_${mid}.txt"
  sleep 0.2
done

echo
echo "[RUN_ALL] Starting supervisor ($SUPERVISOR.py) in foreground..."
echo "Press CTRL+C to stop everything."

python3 -u "$SCRIPT_DIR/${SUPERVISOR}.py" \
  --jobs "$JOBS" \
  --deadline "$DEADLINE" \
  $WAIT_DONE \
  --broker "$BROKER" \
  --port "$PORT"
