#!/usr/bin/env bash
# make_batches.sh — (re)gera os filtros de APKs deste experimento a partir do dataset.
#
# Lê o diretório do dataset instrumentado (219 .apk), ordena determinísticamente e
# escreve:
#   filters/experiment_apks.txt   — lista completa (219)
#   filters/batch_00.txt .. batch_15.txt — split contíguo balanceado em NBATCHES
#   filters/smoke_batch.txt       — 2 APKs para o smoke (NÃO sobrescreve se já existir)
#   filters/minismoke_batch.txt   — 1 APK (NÃO sobrescreve se já existir)
#
# O split é contíguo sobre a lista ordenada: os primeiros (N % NBATCHES) batches
# recebem um APK a mais. Mapeamento batch→VM (4 VMs × 4 containers):
#   m1: batch_00..03   m2: batch_04..07   m3: batch_08..11   m4: batch_12..15
#
# Regenerar só é necessário se o dataset ou a topologia de VMs mudar.
#
# Uso:
#   bash scripts/make_batches.sh
#   DATASET=/outro/path NBATCHES=16 bash scripts/make_batches.sh

set -euo pipefail
cd "$(dirname "$0")/.."

DATASET="${DATASET:-/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706}"
NBATCHES="${NBATCHES:-16}"

[[ -d "$DATASET" ]] || { echo "ERRO: DATASET inexistente: $DATASET"; exit 2; }

python3 - "$DATASET" "$NBATCHES" <<'PY'
import os, sys, math
dataset, nbatches = sys.argv[1], int(sys.argv[2])
apks = sorted(f for f in os.listdir(dataset) if f.endswith(".apk"))
n = len(apks)
if n == 0:
    print("ERRO: nenhum .apk encontrado no dataset", file=sys.stderr); sys.exit(2)

os.makedirs("filters", exist_ok=True)
with open("filters/experiment_apks.txt", "w") as fh:
    fh.write("\n".join(apks) + "\n")

# Split contíguo balanceado: os primeiros (n % nbatches) batches ganham +1.
base, rem = divmod(n, nbatches)
idx = 0
sizes = []
for b in range(nbatches):
    size = base + (1 if b < rem else 0)
    chunk = apks[idx:idx + size]
    idx += size
    sizes.append(len(chunk))
    with open(f"filters/batch_{b:02d}.txt", "w") as fh:
        fh.write("\n".join(chunk) + "\n")

# smoke: 2 primeiros APKs, só cria se ausente (não sobrescreve escolha manual).
if not os.path.exists("filters/smoke_batch.txt"):
    with open("filters/smoke_batch.txt", "w") as fh:
        fh.write("\n".join(apks[:2]) + "\n")
if not os.path.exists("filters/minismoke_batch.txt"):
    with open("filters/minismoke_batch.txt", "w") as fh:
        fh.write(apks[0] + "\n")

# Resumo + alvos por VM (apks × 11 tools × 3 reps × 3 timeouts).
TOOLS, REPS, TOUTS = 11, 3, 3
per_task = TOOLS * REPS * TOUTS
vm_map = {"m1": range(0, 4), "m2": range(4, 8), "m3": range(8, 12), "m4": range(12, 16)}
print(f"dataset={dataset}")
print(f"total APKs={n}  nbatches={nbatches}  (sizes: {sizes})")
print(f"tasks/apk = {TOOLS}×{REPS}×{TOUTS} = {per_task}  →  total tasks = {n*per_task}")
print("alvos por VM (COMPLETED distintos):")
gtot = 0
for vm, rng in vm_map.items():
    apk_count = sum(sizes[b] for b in rng)
    tasks = apk_count * per_task
    gtot += tasks
    print(f"  {vm}: batches {rng.start:02d}..{rng.stop-1:02d}  apks={apk_count:3d}  tasks={tasks}")
print(f"  Σ tasks = {gtot}")
PY

echo ""
echo "filters gerados em: $(pwd)/filters/"
