#!/usr/bin/env bash
# Dispara a run gov.br: 8 containers, APE, timeout 3600s, 1 passada (reps=1).
# up -d -> docker wait (todos) -> down. Auto-resume: re-rodar recupera de tasks.json.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=docker-compose.gov.yml
TIMEOUT="${EXP_TIMEOUT:-3600}"
CONTAINERS=(exp_00 exp_01 exp_02 exp_03 exp_04 exp_05 exp_06 exp_07)

echo "[run_gov] dataset: /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS_INSTRUMENTADOS"
n=$(ls /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS_INSTRUMENTADOS/*.apk 2>/dev/null | wc -l)
echo "[run_gov] instrumented APKs presentes: $n (esperado 33; receita.rfb fora — 65536 ceiling)"
if [ "$n" -lt 33 ]; then
  echo "[run_gov] ABORT: dataset instrumentado incompleto (<33). Rode instrument_gov.py primeiro." >&2
  exit 1
fi

echo "[run_gov] up -d (EXP_TIMEOUT=$TIMEOUT) ..."
EXP_TIMEOUT="$TIMEOUT" docker compose -f "$COMPOSE" up -d

echo "[run_gov] aguardando containers terminarem (docker wait) ..."
docker wait "${CONTAINERS[@]}" || true

echo "[run_gov] down ..."
docker compose -f "$COMPOSE" down || true
echo "[run_gov] passada concluída. Verifique com scripts/monitor_gov.sh; re-rode este script para o resume final."
