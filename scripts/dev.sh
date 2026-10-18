#!/usr/bin/env bash
# Run the whole stack locally: simulator container, API, frontend.
#
#   scripts/dev.sh
#
# Frontend  http://localhost:5173
# API       http://localhost:8080  (docs at /docs)
#
# Ctrl-C stops both; colima is left running since starting it is slow.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# The simulator runs inside a container because OpenModelica has no macOS build.
if ! colima status >/dev/null 2>&1; then
  echo "starting colima (a minute or so)..."
  colima start --cpu 4 --memory 6 --disk 40
fi

if [ ! -x build/RideThroughCore ]; then
  echo "compiling the model (one time)..."
  python3 -c "from sim import runner; runner.build()"
fi

cleanup() { kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload &
API_PID=$!

# Wait for the API rather than racing it, so the first slider run does not fall back.
for _ in $(seq 1 40); do
  curl -sf http://localhost:8080/health >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf http://localhost:8080/health >/dev/null 2>&1 \
  && echo "API   ready  http://localhost:8080" \
  || echo "API   did not come up; the page will fall back to the precomputed grid"

(cd frontend && npm run dev) &
WEB_PID=$!

echo "web   starting http://localhost:5173"
wait
