#!/usr/bin/env bash
# copy_dataset_to_vms.sh — envia o dataset + a pasta do experimento para as VMs.
#
# Cada VM precisa de:
#   /home/pedro/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/   (219 .apk + 219 .apk.json)
#   /home/pedro/experimento-20260706/                                  (compose, filters, scripts)
#
# As imagens NÃO são copiadas — as VMs puxam do Docker Hub (build_and_push_091.sh
# já publicou rvandroid:0.9.1, ares/qtesting:latest, humanoid:1.0).
#
# Uso (informe os alvos SSH das 4 VMs, na ordem m1 m2 m3 m4):
#   bash scripts/copy_dataset_to_vms.sh user@vm1 user@vm2 user@vm3 user@vm4
#
# Alternativa gcloud (se preferir instâncias por nome):
#   USE_GCLOUD=1 GCLOUD_ZONE=us-central1-a \
#     bash scripts/copy_dataset_to_vms.sh inst-m1 inst-m2 inst-m3 inst-m4
#
# DRY_RUN=1 mostra os comandos sem executar.

set -euo pipefail
cd "$(dirname "$0")/.."
EXP_DIR="$(pwd)"

DATASET="${DATASET:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706}"
DATASET_DEST="/home/pedro/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706"
EXP_DEST="/home/pedro/experimento-20260706"
DRY_RUN="${DRY_RUN:-0}"
USE_GCLOUD="${USE_GCLOUD:-0}"
GCLOUD_ZONE="${GCLOUD_ZONE:-}"

if [[ $# -ne 4 ]]; then
    echo "Uso: bash scripts/copy_dataset_to_vms.sh <m1> <m2> <m3> <m4>"
    echo "  (alvos SSH user@host, ou nomes de instância com USE_GCLOUD=1)"
    exit 64
fi
[[ -d "$DATASET" ]] || { echo "ERRO: DATASET inexistente: $DATASET"; exit 2; }

run() { echo "+ $*"; [[ "$DRY_RUN" == "1" ]] || "$@"; }

copy_to() {
    local target="$1"
    echo "──────────────────────────────────────────────────────────"
    echo " → $target"
    echo "──────────────────────────────────────────────────────────"
    if [[ "$USE_GCLOUD" == "1" ]]; then
        local zflag=(); [[ -n "$GCLOUD_ZONE" ]] && zflag=(--zone "$GCLOUD_ZONE")
        run gcloud compute scp --recurse "${zflag[@]}" "$DATASET" "${target}:${DATASET_DEST%/*}/"
        run gcloud compute scp --recurse "${zflag[@]}" "$EXP_DIR" "${target}:${EXP_DEST%/*}/"
    else
        run rsync -az --info=progress2 "$DATASET/"  "${target}:${DATASET_DEST}/"
        run rsync -az --info=progress2 "$EXP_DIR/"   "${target}:${EXP_DEST}/"
    fi
}

VMS=("$1" "$2" "$3" "$4")
for t in "${VMS[@]}"; do copy_to "$t"; done

echo ""
echo "Concluído. Em cada VM: cd ${EXP_DEST} && bash scripts/run_smoke.sh"
