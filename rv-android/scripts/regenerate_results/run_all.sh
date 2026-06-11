#!/usr/bin/env bash
# Orchestrate the full 3-level regeneration locally.
#
# Level 1: regenerate_container.py runs once per container (16 total). All 16
# run concurrently as background jobs; each job uses its own internal worker
# pool (--workers). Total parallelism is approximately CONTAINER_JOBS *
# WORKERS_PER_CONTAINER.
#
# Level 2: concat_vm.py concatenates the 4 containers of each VM.
# Level 3: concat_all.py concatenates the 4 VMs into the final consolidated CSVs.
#
# Does NOT run verify.py and does NOT touch the original *_all.csv files. See
# docs/20260514_regenerar_planilhas.md.

set -euo pipefail

RESULTS_ROOT="${RESULTS_ROOT:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS}"
STATIC_DIR="${STATIC_DIR:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB}"
WORKERS_PER_CONTAINER="${WORKERS_PER_CONTAINER:-4}"
if [[ -z "${VMS+x}" ]]; then
    VMS=(m1 m2 m3 m4)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

echo "[run_all] results_root = ${RESULTS_ROOT}"
echo "[run_all] static_dir   = ${STATIC_DIR}"
echo "[run_all] vms          = ${VMS[*]}"
echo "[run_all] workers/cont = ${WORKERS_PER_CONTAINER}"

cd "${PROJECT_ROOT}"

# ---- Level 1: 16 containers in parallel ----
echo "[run_all] starting level 1 (per-container regeneration) ..."
pids=()
for vm in "${VMS[@]}"; do
    vm_results="${RESULTS_ROOT}/${vm}/results"
    if [[ ! -d "${vm_results}" ]]; then
        echo "[run_all] WARNING: ${vm_results} does not exist, skipping"
        continue
    fi
    for container in "${vm_results}"/*/; do
        # rv-android container layout: results/exp_XX/exp_XX/
        inner_name="$(basename "${container}")"
        inner="${container}${inner_name}"
        if [[ ! -d "${inner}" ]]; then
            echo "[run_all] WARNING: ${inner} is not a directory, skipping"
            continue
        fi
        log="${LOG_DIR}/${vm}_${inner_name}.log"
        echo "[run_all]   dispatch ${vm}/${inner_name} -> ${log}"
        uv run python scripts/regenerate_results/regenerate_container.py \
            "${inner}" \
            --static-dir "${STATIC_DIR}" \
            --workers "${WORKERS_PER_CONTAINER}" \
            >"${log}" 2>&1 &
        pids+=($!)
    done
done

# Wait for all containers, abort on any non-zero exit.
fail=0
for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then
        fail=1
    fi
done
if [[ ${fail} -ne 0 ]]; then
    echo "[run_all] FAIL: at least one container regeneration failed (see ${LOG_DIR}/*.log)"
    exit 1
fi
echo "[run_all] level 1 OK"

# ---- Level 2: per-VM concat ----
echo "[run_all] starting level 2 (per-VM concat) ..."
uv run python scripts/regenerate_results/concat_vm.py "${VMS[@]}" \
    --results-root "${RESULTS_ROOT}"

# ---- Level 3: consolidated concat ----
echo "[run_all] starting level 3 (consolidated concat) ..."
uv run python scripts/regenerate_results/concat_all.py \
    --vms "${VMS[@]}" \
    --results-root "${RESULTS_ROOT}"

echo "[run_all] DONE. Now run verify.py --full to audit results."
