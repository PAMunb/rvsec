#!/usr/bin/env bash
# Progresso da run gov.br por container (COMPLETED distintos, dedup por identidade).
# Reusa o rv_status.py genérico do experimento-20260706.
set -euo pipefail
cd "$(dirname "$0")/.."

RV_STATUS=../experimento-20260706/scripts/rv_status.py
if [ ! -f "$RV_STATUS" ]; then
  echo "rv_status.py não encontrado em $RV_STATUS" >&2; exit 1
fi

# 34 APKs · 1 tool (ape) · 1 rep · 1 timeout (3600) = 34 identidades-alvo.
python3 "$RV_STATUS" --results results --prefix exp_ \
    --apks 34 --tools 1 --reps 1 --timeouts 3600 "$@"

echo
echo "=== docker ps (containers da run) ==="
docker ps --filter name=exp_ --format 'table {{.Names}}\t{{.Status}}' || true
