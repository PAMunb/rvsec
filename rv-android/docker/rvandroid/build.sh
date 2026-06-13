#!/bin/bash
set -e


VERSION=0.9.1
IMAGE=phtcosta/rvandroid

docker build --no-cache -t $IMAGE:$VERSION -t $IMAGE:latest "$(dirname $0)"


echo "Image created successfully!!!"

# send to docker hub
#docker login -u phtcosta
#docker push phtcosta/rvandroid:0.9.1
