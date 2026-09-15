#!/bin/bash
# Gera o compose, os filtros e o meta do smoke e da campanha com o gen_compare da skill
# rv-experiment-compare, a partir de scripts/campanha.env. Roda DEPOIS do exportar_corpus.py
# --apply: o gen_compare lista os APKs da pasta montada, e a pasta só existe depois dele.
#
#   experimento-estudo02-20260916/scripts/gerar_campanha.sh
#
# O gen_compare escreve em lugares fixos do rv-android (docker/, docs/, data/). O compose e o
# plano gerado vêm para este diretório; filtros e meta ficam em data/, onde o
# monitor_compare.sh, o consolidate_compare.py e o admissibility.py os procuram. O compose
# usa volumes relativos (`../data/...`), que resolvem igual daqui, na mesma profundidade.
set -euo pipefail
EXP="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EXP/.."
source "${CAMPANHA_ENV:-$EXP/scripts/campanha.env}"
GEN=.claude/skills/rv-experiment-compare/scripts/gen_compare.py

mkdir -p "$EXP/docs"
[ -d "$DATASET" ] || { echo "!! dataset inexistente: $DATASET — rode antes exportar_corpus.py --apply"; exit 1; }

gerar() {  # gerar <name> <containers> <timeout> <reps> [args extras...]
  local name=$1 n=$2 timeout=$3 reps=$4; shift 4
  local dest="$EXP/docker-compose.$name.yml"
  [ -e "$dest" ] && { echo "!! já existe: $dest — remova à mão para regerar"; exit 1; }
  python3 "$GEN" --name "$name" --dataset "$DATASET" --tools "$TOOLS" \
    --timeout "$timeout" --reps "$reps" --containers "$n" --spec-set "$SPEC_SET" \
    --image "$IMAGE" --humanoid-image "$HUMANOID_IMAGE" --cpus "$CPUS" --memory "$MEMORY" \
    --restart "$RESTART" --logcat-diagnostics "$@"
  local date; date=$(date +%Y%m%d)
  mv "docker/docker-compose.$name.yml" "$dest"
  mv "docs/${date}_${name}.md" "$EXP/docs/${date}_${name}_gerado.md"
  sed -i -e "s|^# Plano: docs/${date}_${name}.md|# Plano: experimento-estudo02-20260916/docs/20260916_plano.md|" \
         -e "s|docker/docker-compose.$name.yml|experimento-estudo02-20260916/docker-compose.$name.yml|" "$dest"
  docker compose -f "$dest" config -q
  echo "  -> $dest"
}

gerar "$SMOKE_NAME" "$SMOKE_CONTAINERS" "$SMOKE_TIMEOUT" "$SMOKE_REPS" --only "$SMOKE_APKS"
gerar "$NAME" "$CONTAINERS" "$TIMEOUTS" "$REPS"

sha=$(sha256sum "data/${NAME}_filters/corpus.txt" | cut -c1-16)
echo
echo "corpus.txt da campanha: $(grep -c . "data/${NAME}_filters/corpus.txt") APKs, sha256 $sha"
echo "registre o sha256 no README (seção Estado) antes do preflight"
