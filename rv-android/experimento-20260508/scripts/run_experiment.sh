#!/bin/bash
# Roda o experimento na VM atual: 3 passadas sequenciais (timeout=60, 180, 300).
# Mesmo RV_EXPERIMENT_NAME por container — tasks.json acumula combos
# (apk, tool, variant, rep, timeout) sem duplicar.
#
# Uso (na VM):
#   cd /home/pedro/experimento-20260508
#   ./scripts/run_experiment.sh m1   # ou m2, m3, m4 — define qual .env carregar
#
# IMPORTANTE: este script só dispara o experimento. NÃO deve ser invocado sem
# autorização expressa do usuário.

set -e
cd "$(dirname "$0")/.."

VM_NAME="$1"
if [ -z "$VM_NAME" ]; then
    echo "Erro: uso ./scripts/run_experiment.sh {m1|m2|m3|m4}"
    exit 64
fi

ENV_FILE=".env.$VM_NAME"
if [ ! -f "$ENV_FILE" ]; then
    echo "Erro: $ENV_FILE não existe"
    exit 65
fi

mkdir -p results/exp_00 results/exp_01 results/exp_02 results/exp_03

for TIMEOUT in 60 180 300; do
    echo ""
    echo "=========================================================="
    echo "=== passada TIMEOUT=${TIMEOUT}s  ($(date '+%Y-%m-%d %H:%M:%S')) ==="
    echo "=========================================================="
    EXP_TIMEOUT=$TIMEOUT docker compose --env-file "$ENV_FILE" -f docker-compose.gcp.yml up -d
    docker wait exp_00 exp_01 exp_02 exp_03
    docker compose --env-file "$ENV_FILE" -f docker-compose.gcp.yml down
done

echo ""
echo "=== experimento concluído $(date '+%Y-%m-%d %H:%M:%S') ==="
