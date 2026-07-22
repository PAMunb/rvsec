#!/bin/bash
# Roda o smoke test em duas passagens (timeout=60 depois timeout=120).
# Mesmo RV_EXPERIMENT_NAME=smoke nos dois — auto-resume acumula via tasks.json.
#
# Uso: cd /home/pedro/experimento-20260706 && bash scripts/run_smoke.sh

set -e
cd "$(dirname "$0")/.."

mkdir -p results/smoke

for TIMEOUT in 60 120; do
  echo ""
  echo "=========================================================="
  echo "=== smoke pass: TIMEOUT=${TIMEOUT}s  ($(date '+%H:%M:%S')) ==="
  echo "=========================================================="
  SMOKE_TIMEOUT=$TIMEOUT docker compose -f docker-compose.smoke.yml up -d
  docker wait val_smoke
  EXIT=$(docker inspect -f '{{.State.ExitCode}}' val_smoke)
  echo "=== val_smoke exited with code $EXIT ==="
  docker compose -f docker-compose.smoke.yml down
  if [ "$EXIT" -ne 0 ]; then
    echo "ABORT: smoke pass falhou em TIMEOUT=$TIMEOUT"
    exit "$EXIT"
  fi
done

echo ""
echo "=== smoke completo $(date '+%H:%M:%S') ==="
echo "Results em: results/smoke/smoke/"
ls -la results/smoke/smoke/ 2>/dev/null | head -10
