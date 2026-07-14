#!/bin/bash
# MOP-UP de baixa concorrência: 2 containers por vez (16g cada) para recuperar
# o resíduo ERROR (majoritariamente monkey/OOM-transitório) sem oversubscrição.
# Reusa os results/exp_NN existentes: resume pula COMPLETED, re-roda só ERROR.
# 2 ondas (exp_00+exp_01, depois exp_02+exp_03) x 3 passadas (60,180,300).
set -e
cd "$(dirname "$0")/.."
VM_NAME="$1"
[ -z "$VM_NAME" ] && { echo "uso: run_mopup.sh {m1|m2|m3|m4}"; exit 64; }
ENV_FILE=".env.$VM_NAME"
[ -f "$ENV_FILE" ] || { echo "$ENV_FILE nao existe"; exit 65; }
COMPOSE="docker-compose.mopup.yml"
mkdir -p results/exp_00 results/exp_01 results/exp_02 results/exp_03

for WAVE in "exp_00 exp_01" "exp_02 exp_03"; do
  echo ""
  echo "########## MOPUP $VM_NAME onda [$WAVE] ($(date "+%F %T")) ##########"
  for TIMEOUT in 60 180 300; do
    echo "=== MOPUP passada TIMEOUT=${TIMEOUT}s onda[$WAVE] ($(date "+%F %T")) ==="
    EXP_TIMEOUT=$TIMEOUT docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d humanoid $WAVE
    docker wait $WAVE
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" stop $WAVE
  done
done
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" down
echo "=== MOPUP $VM_NAME concluido $(date "+%F %T") ==="
