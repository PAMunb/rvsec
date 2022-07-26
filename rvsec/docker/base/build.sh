#!/bin/bash

VERSION=0.0.1
IMAGE=pamunb/mop-base

#docker build -t $IMAGE:$VERSION $(dirname $0)
docker build -t $IMAGE:$VERSION $(dirname $0)

ID=$(docker images | grep "$IMAGE" | head -n 1 | awk '{print $3}')

docker tag "$ID" $IMAGE:latest
docker tag "$ID" $IMAGE:$VERSION
