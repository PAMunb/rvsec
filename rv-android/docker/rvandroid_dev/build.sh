#!/bin/bash

VERSION=0.9.2
IMAGE=phtcosta/rvandroid_dev

docker build -t $IMAGE:$VERSION -f $(dirname $0)/Dockerfile $(dirname $0)/../..

ID=$(docker images | grep "$IMAGE" | head -n 1 | awk '{print $3}')

docker tag "$ID" $IMAGE:latest
docker tag "$ID" $IMAGE:$VERSION

echo "Image created successfully!!!"
