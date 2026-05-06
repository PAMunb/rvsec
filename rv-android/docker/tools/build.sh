#!/bin/bash
set -e


VERSION=0.8.0
IMAGE=phtcosta/rvandroid_tools

docker build --no-cache -t $IMAGE:$VERSION -t $IMAGE:latest "$(dirname $0)"


echo "Imagem criada com sucesso!!!"

# mandar imagem pro docker hub
#docker login
#docker push phtcosta/rvandroid_tools:0.8.0