#!/bin/bash

VERSION=0.8.0
IMAGE=phtcosta/rvsec_android

docker build --no-cache -t $IMAGE:$VERSION $(dirname $0)

ID=$(docker images | grep "$IMAGE" | head -n 1 | awk '{print $3}')

docker tag "$ID" $IMAGE:latest
docker tag "$ID" $IMAGE:$VERSION

echo "Imagem criada com sucesso!!!"

# mandar imagem pro docker hub
#docker login
#docker push phtcosta/rvsec_android:0.8.0