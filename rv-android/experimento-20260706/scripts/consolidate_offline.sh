#!/usr/bin/env bash
# Consolidação OFFLINE dos resultados do experimento-20260706, a partir dos
# .logcat preservados (NÃO dos CSVs do container — o resume zera T=60/T=180 no CSV,
# gotcha do result_processor). Reusa o pipeline genérico scripts/regenerate_results/,
# fixando os caminhos deste experimento (dataset SA de 219 + RESULTADOS das 4 VMs).
#
# Três fases:
#   1. VALIDAÇÃO  — dedup COMPLETED por identidade + gate VerifyError (read-only).
#   2. REGEN      — reparsea cada .logcat com static_data → summary/coverage/errors
#                   _regen.csv por container, concatena por-VM e consolidado.
#   3. AUDITORIA  — verify.py --full (C1-C4) contra os .logcat brutos.
#
# Promoção (_regen.csv → _all.csv) é passo MANUAL, separado, gated pelo verify.
#
# Pré-requisitos:
#   - RESULTS_ROOT no layout m<i>/results/exp_<j>/exp_<j>/<apk>/*.logcat (sem smoke).
#   - STATIC_DIR com 219 JSONs (um por APK), schema gh60 (reachesTarget). O próprio
#     dataset instrumentado já traz os .apk.json ao lado dos .apk.
#
# Uso:
#   bash experimento-20260706/scripts/consolidate_offline.sh
#   RESULTS_ROOT=/outro/path bash .../consolidate_offline.sh   # override

set -euo pipefail

RESULTS_ROOT="${RESULTS_ROOT:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTADOS_experimento-20260706}"
STATIC_DIR="${STATIC_DIR:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706}"
WORKERS_PER_CONTAINER="${WORKERS_PER_CONTAINER:-4}"
VMS=(m1 m2 m3 m4)

# Alvos por VM (219 APK × 11 tools × 3 reps × 3 timeouts, fatiado por batches).
# m1: batch_00..03 (56 apk), m2: 04..07 (56), m3: 08..11 (55), m4: 12..15 (52).
declare -A ALVO=([m1]=5544 [m2]=5544 [m3]=5445 [m4]=5148)
TARGET_TOTAL=21681

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REGEN_DIR="${PROJECT_ROOT}/scripts/regenerate_results"

echo "════════════════════════════════════════════════════════════════"
echo " Consolidação offline — experimento-20260706"
echo "   RESULTS_ROOT = ${RESULTS_ROOT}"
echo "   STATIC_DIR   = ${STATIC_DIR}"
echo "   workers/cont = ${WORKERS_PER_CONTAINER}  (16 containers paralelos)"
echo "════════════════════════════════════════════════════════════════"

# Sanidade de caminhos.
[[ -d "${RESULTS_ROOT}" ]] || { echo "ERRO: RESULTS_ROOT inexistente"; exit 2; }
[[ -d "${STATIC_DIR}"   ]] || { echo "ERRO: STATIC_DIR inexistente"; exit 2; }
n_json=$(find "${STATIC_DIR}" -maxdepth 1 -name '*.json' | wc -l)
echo "   SA JSONs     = ${n_json}  (esperado 219)"
if find "${RESULTS_ROOT}"/m*/results -maxdepth 1 -type d -name smoke 2>/dev/null | grep -q smoke; then
    echo "ERRO: ainda há pasta(s) smoke sob RESULTS_ROOT — remova antes (contamina o consolidado)."; exit 2
fi

# ─────────────────────────────────────────────────────────────────
echo; echo "── FASE 1: VALIDAÇÃO (dedup COMPLETED + gate VerifyError) ──"
python3 - "${RESULTS_ROOT}" "${TARGET_TOTAL}" <<'PY'
import json, glob, sys
root, target = sys.argv[1], int(sys.argv[2])
alvos = {'m1': 5544, 'm2': 5544, 'm3': 5445, 'm4': 5148}
gtot = set()
print(f"  {'VM':4} {'COMPLETED':>10} {'alvo':>6} {'faltam':>7}")
for vm in ('m1', 'm2', 'm3', 'm4'):
    comp = set()
    for tf in glob.glob(f"{root}/{vm}/results/exp_*/exp_*/tasks.json"):
        try:
            d = json.load(open(tf))
        except Exception:
            continue
        for t in d.get('tasks', []):
            c = t.get('config', {}); r = t.get('result', {}); tc = c.get('tool_config', {}) or {}
            if r.get('state') == 'COMPLETED':
                comp.add((c.get('apk_name'), tc.get('name'), tc.get('variant'),
                          c.get('repetition'), c.get('timeout')))
    a = alvos[vm]
    print(f"  {vm:4} {len(comp):>10} {a:>6} {a - len(comp):>7}")
    gtot |= comp
print(f"  {'Σ':4} {len(gtot):>10} {target:>6} {target - len(gtot):>7}   ({100*len(gtot)/target:.2f}%)")
PY

# grep paralelo (xargs -P) restrito aos .logcat: um VerifyError de runtime é logado
# no logcat, não nos .trace (ação da tool). Evita ler ~2,5 G de traces por VM e usa
# os núcleos disponíveis — o grep -rl recursivo single-thread levava ~1 h POR VM num HDD.
echo "  -- gate VerifyError (por VM; grep paralelo só em .logcat) --"
ve_total=0
for vm in "${VMS[@]}"; do
    n=$(find "${RESULTS_ROOT}/${vm}/results/exp_"*/ -name '*.logcat' -size +0c 2>/dev/null \
        | xargs -r -P16 -d '\n' grep -l VerifyError 2>/dev/null | wc -l || true)
    echo "     ${vm} VE_files=${n}"
    ve_total=$((ve_total + n))
done
echo "  -- VerifyError total = ${ve_total} (esperado 0) --"

# ─────────────────────────────────────────────────────────────────
echo; echo "── FASE 2: REGEN (reparse de logcats → CSVs) — pode levar 30-60 min ──"
RESULTS_ROOT="${RESULTS_ROOT}" STATIC_DIR="${STATIC_DIR}" \
    WORKERS_PER_CONTAINER="${WORKERS_PER_CONTAINER}" \
    bash "${REGEN_DIR}/run_all.sh"

# ─────────────────────────────────────────────────────────────────
echo; echo "── FASE 3: AUDITORIA (verify.py --full, C1-C4) ──"
set +e
uv run python "${REGEN_DIR}/verify.py" --full \
    --results-root "${RESULTS_ROOT}" --workers 8
verify_rc=$?
set -e

echo; echo "════════════════════════════════════════════════════════════════"
echo " Consolidados gerados em:"
echo "   ${RESULTS_ROOT}/{summary,coverage,errors}_regen.csv"
echo " Relatório de auditoria:"
echo "   ${RESULTS_ROOT}/verification_report.md"
if [[ ${verify_rc} -eq 0 ]]; then
    echo " AUDITORIA: PASS (C1-C4). Pronto para promoção (_regen.csv → _all.csv)."
else
    echo " AUDITORIA: FALHOU — inspecione verification_report.md antes de promover."
fi
echo "════════════════════════════════════════════════════════════════"
exit ${verify_rc}
