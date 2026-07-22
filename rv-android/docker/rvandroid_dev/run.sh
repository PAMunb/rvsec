#!/bin/env bash

EXPERIMENT02_BASE_DIR=/home/pedro/desenvolvimento/RV_ANDROID/EXPERIMENTO_02/BASE
APKS_DIR=$EXPERIMENT02_BASE_DIR/apks/tmp
INSTRUMENTED_DIR=$EXPERIMENT02_BASE_DIR/instrumented
RESULTS_DIR=$EXPERIMENT02_BASE_DIR/results

echo "APKS_DIR=${APKS_DIR}"

#docker run -it --rm --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvandroid:0.0.1
#docker run -it --rm --entrypoint "/bin/bash" --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvandroid:0.0.1
#docker run -it --rm --entrypoint "/bin/bash" --device /dev/kvm -v $APKS_DIR:/opt/rvsec/rv-android/apks -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvandroid:0.0.1


#docker run -it --rm --device /dev/kvm --name rvsec-01 \
#-v $APKS_DIR:/opt/rvsec/rv-android/apks \
#-v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
#-v $RESULTS_DIR:/opt/rvsec/rv-android/results \
#-e MEMORY=6144 -e CORES=2 \
#phtcosta/rvandroid:0.0.1

#docker run -it --rm --name rv01 --device /dev/kvm \
#  -e RV_REPETITIONS=1 \
#  -e RV_TIMEOUTS=300 \
#  -e RV_TOOLS="monkey ares qtesting droidbot" \
#  -e ENV_NO_WINDOW=true \
#  -e MEMORY=6144 -e CORES=2 \
#  -v $APKS_DIR:/opt/rvsec/rv-android/apks \
#  -v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
#  -v $RESULTS_DIR:/opt/rvsec/rv-android/results \
#  phtcosta/rvandroid:0.0.1




docker run -it --rm --device /dev/kvm --entrypoint "/bin/bash" --name rvsec-01 \
-v $APKS_DIR:/opt/rvsec/rv-android/apks \
-v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
-v $RESULTS_DIR:/opt/rvsec/rv-android/results \
-e MEMORY=6144 -e CORES=2 \
phtcosta/rvandroid:0.7.0

#docker run -d --device /dev/kvm -p 5555:5555 -v androiddata:/data -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name docker-android-emulator cndaqiang/docker-android-emulator:api-33
