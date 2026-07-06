#!/usr/bin/env bash
# build_and_push_091.sh — (re)constrói e publica as imagens 0.9.1 no Docker Hub.
#
# O experimento-20260706 puxa das VMs exatamente estas tags do Docker Hub:
#   phtcosta/rvandroid:0.9.1   (compose gcp/smoke)         ← RECONSTRUÍDA aqui
#   phtcosta/humanoid:1.0      (compose gcp/smoke)         ← já no hub, inalterada
#   phtcosta/ares:latest       (tool.py, sibling container) ← retag 0.9.0
#   phtcosta/qtesting:latest   (tool.py, sibling container) ← retag 0.9.0
#
# Por que reconstruir só a rvandroid:
#   - A rvandroid clona o rvsec do GitHub (branch `modules`) no build E copia o
#     docker-entrypoint.sh LOCAL (que já tem o fix --frozen --no-dev, commit 14013b60).
#     Reconstruir garante o entrypoint corrigido baked-in → compose SEM bind-mount.
#   - ares/qtesting são containers de ferramenta independentes (sem código rvsec),
#     idênticos ao 0.9.0 validado no 20260604 → apenas retag 0.9.0 → 0.9.1 + latest.
#     (Para forçar rebuild de ares/qtesting, use REBUILD_TOOLS=1.)
#
# PRÉ-REQUISITO: o build clona rvsec de origin/modules — os commits precisam estar
# pushados. O script verifica e ABORTA se o HEAD local estiver à frente do remoto.
#
# Uso (LOCAL, antes de subir pras VMs):
#   bash experimento-20260706/scripts/build_and_push_091.sh          # build + push
#   DRY_RUN=1 bash .../build_and_push_091.sh                          # só mostra o que faria
#   REBUILD_TOOLS=1 bash .../build_and_push_091.sh                    # rebuild ares/qtesting também
#
# NÃO invocar sem autorização expressa do usuário.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"   # rv-android/
DOCKER_DIR="${REPO_ROOT}/docker"
DRY_RUN="${DRY_RUN:-0}"
REBUILD_TOOLS="${REBUILD_TOOLS:-0}"
VERSION=0.9.1

run() { echo "+ $*"; [[ "$DRY_RUN" == "1" ]] || "$@"; }

echo "════════════════════════════════════════════════════════════════"
echo " Build + push imagens ${VERSION} — experimento-20260706"
echo "   REPO_ROOT = ${REPO_ROOT}"
echo "   DRY_RUN=${DRY_RUN}  REBUILD_TOOLS=${REBUILD_TOOLS}"
echo "════════════════════════════════════════════════════════════════"

# ── Gate: HEAD local pushado? (o build clona rvsec de origin/modules) ──
cd "${REPO_ROOT}"
LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/modules 2>/dev/null || echo none)"
echo "  git HEAD local  = ${LOCAL_HEAD}"
echo "  git origin/modules = ${REMOTE_HEAD}"
if ! git branch -r --contains "${LOCAL_HEAD}" 2>/dev/null | grep -q "origin/modules"; then
    echo "ERRO: HEAD local NÃO está em origin/modules. Faça 'git push' antes —"
    echo "      a imagem clona o rvsec do GitHub e sairia desatualizada."
    exit 3
fi
echo "  OK: HEAD está em origin/modules (build reproduzível)."

# ── Fase 1: rebuild da cadeia rvandroid (base→android→tools→rvandroid) ──
# Cada build.sh já fixa VERSION=0.9.1 e tageia :0.9.1 + :latest.
echo; echo "── Fase 1: rebuild cadeia rvandroid (${VERSION}) ──"
run "${DOCKER_DIR}/base/build.sh"
run "${DOCKER_DIR}/android/build.sh"
run "${DOCKER_DIR}/tools/build.sh"
run "${DOCKER_DIR}/rvandroid/build.sh"

# ── Fase 2: ares/qtesting — retag 0.9.0 → 0.9.1 + latest (ou rebuild) ──
echo; echo "── Fase 2: ares/qtesting (${VERSION}) ──"
if [[ "$REBUILD_TOOLS" == "1" ]]; then
    run docker build --no-cache -t "phtcosta/ares:${VERSION}" -t "phtcosta/ares:latest" \
        "${REPO_ROOT}/modules/rv-tools/src/rv_tools/builtin/ares"
    run docker build --no-cache -t "phtcosta/qtesting:${VERSION}" -t "phtcosta/qtesting:latest" \
        "${REPO_ROOT}/modules/rv-tools/src/rv_tools/builtin/qtesting"
else
    run docker tag "phtcosta/ares:0.9.0"     "phtcosta/ares:${VERSION}"
    run docker tag "phtcosta/ares:0.9.0"     "phtcosta/ares:latest"
    run docker tag "phtcosta/qtesting:0.9.0" "phtcosta/qtesting:${VERSION}"
    run docker tag "phtcosta/qtesting:0.9.0" "phtcosta/qtesting:latest"
fi

# ── Fase 3: push (login manual antes: `docker login -u phtcosta`) ──
echo; echo "── Fase 3: push Docker Hub ──"
run docker push "phtcosta/rvandroid:${VERSION}"
run docker push "phtcosta/rvandroid:latest"
run docker push "phtcosta/ares:${VERSION}"
run docker push "phtcosta/ares:latest"
run docker push "phtcosta/qtesting:${VERSION}"
run docker push "phtcosta/qtesting:latest"
echo "  (humanoid:1.0 já está no hub — inalterada, não republicada)"

echo; echo "════════════════════════════════════════════════════════════════"
echo " Concluído. Tags publicadas:"
echo "   phtcosta/rvandroid:${VERSION} (+latest)"
echo "   phtcosta/ares:${VERSION} (+latest)   phtcosta/qtesting:${VERSION} (+latest)"
echo "════════════════════════════════════════════════════════════════"
