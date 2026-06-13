#!/bin/bash
set -e


VERSION=0.9.1
IMAGE=phtcosta/rvsec_android

docker build --no-cache -t $IMAGE:$VERSION -t $IMAGE:latest "$(dirname $0)"


echo "Imagem criada com sucesso!!!"

# mandar imagem pro docker hub
#docker login
#docker push phtcosta/rvsec_android:0.9.1