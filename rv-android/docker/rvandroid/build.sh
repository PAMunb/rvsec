#!/bin/bash
set -e

# Camada 4 (produção). O Dockerfile CLONA `PAMunb/rvsec` do GitHub — ele não copia a árvore
# local — então todo commit que a imagem precisa carregar tem de estar PUSHED antes do build.
# É a origem de erro mais cara desta cadeia: um build verde sobre um push que não aconteceu
# produz uma imagem silenciosamente velha, e a campanha inteira mede o código anterior.
#
# Parametrizado por ambiente, com os valores de sempre como default:
#   VERSION       tag da imagem            (default 0.9.3)
#   RVSEC_BRANCH  branch clonado           (default modules — o canônico)
#   TAG_LATEST    também taguear :latest   (default 1 apenas quando VERSION=0.9.3)
#
# Uma tag de campanha NÃO deve mover o :latest — quem roda `phtcosta/rvandroid:latest` no dia
# seguinte estaria rodando a imagem de um experimento, não a de produção. Por isso o default
# de TAG_LATEST depende de VERSION.
#
# Exemplos:
#   ./build.sh                                     # produção: 0.9.3 + latest
#   VERSION=0.9.3-gh111 ./build.sh                 # imagem de campanha, sem mover o latest
#   VERSION=0.9.3-gh111 RVSEC_BRANCH=modules ./build.sh

VERSION="${VERSION:-0.9.3}"
RVSEC_BRANCH="${RVSEC_BRANCH:-modules}"
IMAGE=phtcosta/rvandroid

if [ -z "${TAG_LATEST+x}" ]; then
    if [ "$VERSION" = "0.9.3" ]; then TAG_LATEST=1; else TAG_LATEST=0; fi
fi

TAGS=(-t "$IMAGE:$VERSION")
[ "$TAG_LATEST" = "1" ] && TAGS+=(-t "$IMAGE:latest")

echo "=== build $IMAGE:$VERSION (branch $RVSEC_BRANCH, latest=$TAG_LATEST) ==="
docker build --no-cache \
    --build-arg "RVSEC_BRANCH=$RVSEC_BRANCH" \
    "${TAGS[@]}" \
    "$(dirname "$0")"

echo "Image created successfully!!!"
docker inspect "$IMAGE:$VERSION" --format 'criada em {{.Created}} | rvsec.branch={{index .Config.Labels "rvsec.branch"}}'

# send to docker hub
#docker login -u phtcosta
#docker push phtcosta/rvandroid:$VERSION
