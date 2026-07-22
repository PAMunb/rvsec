#!/bin/bash
# Status + auto-resume de uma comparacao gerada por gen_compare.py.
#
# Uso: monitor_compare.sh <name> [--no-resume]
#   <name>      prefixo do experimento (containers <name>_NN)
#   --no-resume so reporta, nao reinicia containers
#
# CONTAGEM CORRETA: identidades distintas (apk,tool,variant,rep,timeout) via result.state.
#   NUNCA contar com `grep '"state": "COMPLETED"'` — isso conta EM DOBRO, pois o
#   estado COMPLETED tambem aparece em result.state_transitions[]. (licao da corrida 2026-06-19.)
#
# AUTO-RESUME: container nao-running antes de terminar OU 'Up' sem progresso desde a
#   ultima checada -> docker restart (resume por RV_EXPERIMENT_NAME: pula COMPLETED, re-roda FAILED).
set -euo pipefail
NAME="${1:?uso: monitor_compare.sh <name> [--no-resume]}"
RESUME=1; [ "${2:-}" = "--no-resume" ] && RESUME=0

# resolve a raiz do repo (rv-android) a partir da localizacao do script
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
META="data/results/${NAME}_compare_meta.json"
[ -f "$META" ] || { echo "meta nao encontrado: $META (rode gen_compare.py primeiro)"; exit 1; }
STATE="/tmp/${NAME}_prev_counts.txt"

echo "===== ${NAME}: $(date '+%Y-%m-%d %H:%M:%S') ====="
docker ps -a --filter "name=${NAME}_" --format '{{.Names}} {{.Status}}' | sort
docker ps --filter "name=sglang-server" --format '{{.Names}} {{.Status}}' 2>/dev/null || true
echo

# contagem distinta por container -> /tmp/<name>_done_now.txt (NN done total)
python3 - "$NAME" "$META" <<'PY' > "/tmp/${NAME}_done_now.txt"
import json, sys, os
name, meta = sys.argv[1], json.load(open(sys.argv[2]))
n_tools, reps, containers = meta["n_tools"], meta["reps"], meta["containers"]
fdir = meta["filters_dir"]
for i in range(containers):
    nn = f"{i:02d}"
    tj = f"data/results/{name}_{nn}/{name}_{nn}/tasks.json"
    done = 0
    if os.path.exists(tj):
        seen = set()
        for t in json.load(open(tj))["tasks"]:
            if (t.get("result") or {}).get("state") != "COMPLETED":
                continue
            c = t["config"]; tc = c["tool_config"]
            seen.add((c["apk_name"], tc["name"], tc.get("variant"), c["repetition"], c["timeout"]))
        done = len(seen)
    bf = os.path.join(fdir, f"batch_{nn}.txt")
    apks = sum(1 for ln in open(bf) if ln.strip()) if os.path.exists(bf) else 0
    print(nn, done, apks * n_tools * reps)
PY

declare -A PREV
[ -f "$STATE" ] && while read -r k v; do PREV[$k]=$v; done < "$STATE"
NEW=$(mktemp); gtot=0; gdone=0; actions=""
while read -r nn done total; do
  rstate=$(docker inspect -f '{{.State.Running}}' "${NAME}_${nn}" 2>/dev/null || echo "missing")
  prev=${PREV[$nn]:- -1}; flag=""
  if [ "$total" -gt 0 ] && [ "$done" -ge "$total" ]; then
    flag="DONE"
  elif [ "$RESUME" -eq 1 ] && [ "$rstate" != "true" ]; then
    flag="NAO-RUNNING -> resume"
    docker restart "${NAME}_${nn}" >/dev/null 2>&1 && actions="$actions\n  ${NAME}_${nn}: restart (nao-running, done=$done<$total)"
  elif [ "$RESUME" -eq 1 ] && [ "$prev" -ge 0 ] 2>/dev/null && [ "$done" -eq "$prev" ]; then
    flag="TRAVADO -> resume"
    docker restart "${NAME}_${nn}" >/dev/null 2>&1 && actions="$actions\n  ${NAME}_${nn}: restart (Up sem progresso, done=$done)"
  fi
  pct=0; [ "$total" -gt 0 ] && pct=$((done * 100 / total))
  printf "%s_%s: %5d / %5d tasks distintas (%d%%)  %s\n" "$NAME" "$nn" "$done" "$total" "$pct" "$flag"
  echo "$nn $done" >> "$NEW"; gtot=$((gtot + total)); gdone=$((gdone + done))
done < "/tmp/${NAME}_done_now.txt"
mv "$NEW" "$STATE"

gpct=0; [ "$gtot" -gt 0 ] && gpct=$((gdone * 100 / gtot))
echo "-------------------------------------------"
printf "TOTAL: %5d / %5d tasks distintas COMPLETED (%d%%)\n" "$gdone" "$gtot" "$gpct"
if [ -n "$actions" ]; then echo; echo ">>> ACOES DE RESUME:"; echo -e "$actions"
else echo; echo ">>> Nenhuma acao necessaria."; fi
