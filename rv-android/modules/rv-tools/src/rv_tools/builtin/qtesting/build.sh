#!/bin/bash

VERSION=0.0.1
IMAGE=phtcosta/qtesting

docker build --no-cache -t phtcosta/python310_sdkman:0.0.1 -f DockerfileSdkman $(dirname $0)
docker build --no-cache -t $IMAGE:$VERSION $(dirname $0)

ID=$(docker images | grep "$IMAGE" | head -n 1 | awk '{print $3}')

docker tag "$ID" $IMAGE:latest
docker tag "$ID" $IMAGE:$VERSION

echo "Imagem criada com sucesso!!!"

# mandar imagem pro docker hub
#docker login
#docker push phtcosta/qtesting:0.0.1