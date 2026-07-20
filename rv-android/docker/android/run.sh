#!/bin/env bash

docker run -it --rm --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvsec_android:0.9.3 bash


#docker run -d --device /dev/kvm -p 5555:5555 -v androiddata:/data -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name docker-android-emulator cndaqiang/docker-android-emulator:api-33
