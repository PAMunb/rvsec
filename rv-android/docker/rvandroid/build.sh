#!/bin/bash
set -e

# Camada 4 (produção). O Dockerfile CLONA `PAMunb/rvsec` do GitHub — ele não copia a árvore
# local — então todo commit que a imagem precisa carregar tem de estar PUSHED antes do build.
# É a origem de erro mais cara desta cadeia: um build verde sobre um push que não aconteceu
# produz uma imagem silenciosamente velha, e a campanha inteira mede o código anterior.
#
# Parametrizado por ambiente, com os valores de sempre como default:
#   VERSION       tag da imagem            (default 0.9.5)
#   RVSEC_BRANCH  branch clonado           (default modules — o canônico)
#   TAG_LATEST    também taguear :latest   (default 1 apenas quando VERSION=0.9.5)
#
# Uma tag de campanha NÃO deve mover o :latest — quem roda `phtcosta/rvandroid:latest` no dia
# seguinte estaria rodando a imagem de um experimento, não a de produção. Por isso o default
# de TAG_LATEST depende de VERSION.
#
# Exemplos:
#   ./build.sh                                     # produção: 0.9.5 + latest
#   VERSION=0.9.5-gh111 ./build.sh                 # imagem de campanha, sem mover o latest
#   VERSION=0.9.5-gh111 RVSEC_BRANCH=modules ./build.sh

VERSION="${VERSION:-0.9.5}"
RVSEC_BRANCH="${RVSEC_BRANCH:-modules}"
IMAGE=phtcosta/rvandroid

if [ -z "${TAG_LATEST+x}" ]; then
    if [ "$VERSION" = "0.9.5" ]; then TAG_LATEST=1; else TAG_LATEST=0; fi
fi

TAGS=(-t "$IMAGE:$VERSION")
[ "$TAG_LATEST" = "1" ] && TAGS+=(-t "$IMAGE:latest")

echo "=== build $IMAGE:$VERSION (branch $RVSEC_BRANCH, latest=$TAG_LATEST) ==="
docker build --no-cache \
    --build-arg "RVSEC_BRANCH=$RVSEC_BRANCH" \
    "${TAGS[@]}" \
    "$(dirname "$0")"

# Gate: uma partida sem rede tem de rodar a .venv da imagem sem sincronizar. Se o uv reconstruir
# algum membro do workspace ("Building", "Installed"), a partida dependeria do PyPI. O --network none
# sozinho não basta: enquanto o cache do uv der por válido o índice do hatchling gravado no build, a
# reconstrução passa sem rede — por isso o gate também procura essas linhas na saída.
echo "=== gate: partida sem rede ==="
GATE_OUT=$(docker run --rm --network none --entrypoint bash "$IMAGE:$VERSION" \
    -c 'cd /opt/rvsec/rv-android && uv run --frozen --no-dev rv-experiment --help' 2>&1) || {
    echo "$GATE_OUT"; echo "ERRO: rv-experiment não parte sem rede"; exit 1; }
if echo "$GATE_OUT" | grep -qE '^ *(Building|Built|Installed|Uninstalled) '; then
    echo "$GATE_OUT"; echo "ERRO: uv sincronizou o workspace na partida (falta UV_NO_SYNC?)"; exit 1
fi
echo "gate ok"

echo "Image created successfully!!!"
docker inspect "$IMAGE:$VERSION" --format 'criada em {{.Created}} | rvsec.branch={{index .Config.Labels "rvsec.branch"}}'

# send to docker hub
#docker login -u phtcosta
#docker push phtcosta/rvandroid:$VERSION
