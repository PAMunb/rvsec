#!/bin/bash
set -e


VERSION=0.9.1
IMAGE=phtcosta/rvsec_base

docker build --no-cache -t $IMAGE:$VERSION -t $IMAGE:latest "$(dirname $0)"


echo "Image created successfully!!!"

# send to docker hub
#docker login -u phtcosta
#docker push phtcosta/rvsec_base:0.9.1
