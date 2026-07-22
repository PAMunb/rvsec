#!/usr/bin/env bash
# hourly_monitor.sh — monitor horário (on the hour, via cron) da run gov.br.
#
# O que faz, a cada tick:
#   1. SNAPSHOT por container: COMPLETED distinto (dedup por identidade
#      (apk,tool,variant,rep,timeout) via rv_status.py — NUNCA grep de estado, que
#      duplica por state_transitions[]) vs alvo (linhas do batch_NN.txt) + estado docker.
#   2. RESUME de containers problemáticos: para cada container que NAO esta "running",
#      se done < alvo (OOM exit 137, crash, erro transiente de adb install) -> `docker
#      start exp_NN` (o entrypoint auto-resume do tasks.json: pula COMPLETED, re-roda
#      ERROR/FAILED). Container exited com done >= alvo NAO e reiniciado (terminou o lote).
#      Auto-restart de OOM e pre-autorizado (regra permanente).
#   3. Anexa snapshot com timestamp em results/MONITORAMENTO_gov.md.
#
# Metrica primaria = violacoes MOP (linhas `RVSEC   :`), NAO cobertura (0 por design,
# static pulado). RVSEC-COV = numerador de metodos executados (informativo).
#
# Instalado no cron:
#   0 * * * * cd <repo-root> && bash experimento-gov/scripts/hourly_monitor.sh \
#             >> experimento-gov/results/hourly_monitor.log 2>&1
set -uo pipefail

# --- Ancoragem de paths (funciona com o cd do cron OU rodado de qualquer lugar) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"           # experimento-gov/
RESULTS="$EXP_DIR/results"
FILTERS="$EXP_DIR/filters"
RV_STATUS="$EXP_DIR/../experimento-20260706/scripts/rv_status.py"
REGISTRO="$RESULTS/MONITORAMENTO_gov.md"
CONTAINERS=(exp_00 exp_01 exp_02 exp_03 exp_04 exp_05 exp_06 exp_07)

TS="$(date '+%Y-%m-%d %H:%M:%S %z')"

# --- 1. Contagem COMPLETED distinta por container (dedup por identidade) ---
# rv_status so lista containers com tasks.json; default 0 para os demais.
declare -A DONE
STATUS_JSON="$(python3 "$RV_STATUS" --results "$RESULTS" \
  --apks 33 --tools 1 --reps 1 --timeouts 3600 --json 2>/dev/null)"
if [ -n "$STATUS_JSON" ]; then
  while IFS=$'\t' read -r name completed; do
    [ -n "$name" ] && DONE["$name"]="$completed"
  done < <(printf '%s' "$STATUS_JSON" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for c in d.get("containers",[]):
    print("%s\t%s" % (c.get("container"), c.get("completed",0)))
')
fi

# --- 2/3. Varredura por container: estado, alvo, decisao de resume ---
resumed=()
lines=()
total_done=0
total_target=0
running_n=0
for c in "${CONTAINERS[@]}"; do
  idx="${c#exp_}"
  target="$(wc -l < "$FILTERS/batch_${idx}.txt" 2>/dev/null || echo 0)"
  done="${DONE[$c]:-0}"
  state="$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null || echo gone)"
  exitc="$(docker inspect --format '{{.State.ExitCode}}' "$c" 2>/dev/null || echo '-')"
  total_done=$((total_done + done))
  total_target=$((total_target + target))
  action="-"

  if [ "$state" = "running" ]; then
    running_n=$((running_n + 1))
  elif [ "$done" -lt "$target" ]; then
    # NAO running e incompleto -> resume (OOM/crash/transiente). Nunca mexe em emulador.
    if docker start "$c" >/dev/null 2>&1; then
      action="RESUMED (was $state exit=$exitc, done=$done<$target)"
      resumed+=("$c")
      state="restarting"
    else
      action="RESUME-FAIL ($state exit=$exitc)"
    fi
  else
    action="done ($done/$target)"   # exited/terminado — nao reiniciar
  fi

  lines+=("$(printf '| %-6s | %-10s | %5s | %s/%s | %s |' "$c" "$state" "$exitc" "$done" "$target" "$action")")
done

# --- Metrica primaria (unica que interessa): violacoes MOP (linhas `RVSEC   :`) ---
# Cobertura (RVSEC-COV) e IRRELEVANTE neste experimento (static pulado) -> nao computada.
mop_lines="$(find "$RESULTS" -name '*.logcat' -exec grep -hcE 'RVSEC +:' {} + 2>/dev/null | awk '{s+=$1} END{print s+0}')"
n_logcats="$(find "$RESULTS" -name '*.logcat' 2>/dev/null | wc -l)"

all_exited=1
[ "$running_n" -gt 0 ] && all_exited=0

# --- 3. Append markdown ---
{
  echo ""
  echo "### $TS"
  echo ""
  echo "- Progresso: **COMPLETED $total_done/$total_target** distintos · running=$running_n/8 · logcats=$n_logcats"
  echo "- MOP (deliverable — única métrica): **$mop_lines** linhas \`RVSEC   :\` (violações)"
  if [ "${#resumed[@]}" -gt 0 ]; then
    echo "- **RESUME disparado**: ${resumed[*]}"
  fi
  if [ "$all_exited" = "1" ] && [ "$total_done" -ge "$total_target" ]; then
    echo "- **>>> RUN COMPLETA** (todos exited, $total_done/$total_target) — rodar finish sequence (resume final + consolidação)."
  elif [ "$all_exited" = "1" ]; then
    echo "- Todos exited mas $total_done/$total_target — resume disparado onde faltava; próximo tick reavalia."
  fi
  echo ""
  echo "| container | estado | exit | done/alvo | ação |"
  echo "|---|---|---:|---:|---|"
  for l in "${lines[@]}"; do echo "$l"; done
} | tee -a "$REGISTRO"

echo "[hourly_monitor] $TS  done=$total_done/$total_target running=$running_n mop=$mop_lines resumed=${#resumed[@]}"
