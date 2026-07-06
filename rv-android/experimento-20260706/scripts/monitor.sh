#!/bin/bash
# Wrapper fino do rv_status.py com os parâmetros deste experimento (20260706):
#   219 APKs × 11 tools × 3 reps × 3 passes (timeouts 60/180/300) = 21681 tasks.
#
# Uso (na VM, dentro de experimento-20260706):
#   bash scripts/monitor.sh            # snapshot único
#   bash scripts/monitor.sh --watch 30 # atualiza a cada 30s
#   bash scripts/monitor.sh --json     # snapshot estruturado p/ coleta
#
# Qualquer argumento extra é repassado ao rv_status.py.

cd "$(dirname "$0")/.."
exec python3 scripts/rv_status.py \
    --results results \
    --prefix exp_ \
    --apks 219 --tools 11 --reps 3 \
    --timeouts 60,180,300 \
    "$@"
