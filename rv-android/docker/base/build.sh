#!/bin/bash

VERSION=0.8.0
IMAGE=phtcosta/rvsec_base

docker build --no-cache -t $IMAGE:$VERSION $(dirname $0)

ID=$(docker images | grep "$IMAGE" | head -n 1 | awk '{print $3}')

docker tag "$ID" $IMAGE:latest
docker tag "$ID" $IMAGE:$VERSION

echo "Image created successfully!!!"

# send to docker hub
#docker login -u phtcosta
#docker push phtcosta/rvsec_base:0.8.0
