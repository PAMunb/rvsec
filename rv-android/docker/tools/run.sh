#!/bin/env bash

#docker run -it --rm --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-tool phtcosta/rvandroid_tools:0.0.1


#docker run -d --device /dev/kvm -p 5555:5555 -v androiddata:/data -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name docker-android-emulator cndaqiang/docker-android-emulator:api-33

#!/bin/env bash

EXPERIMENT02_BASE_DIR=/home/pedro/desenvolvimento/RV_ANDROID/EXPERIMENTO_02/BASE
APKS_DIR=$EXPERIMENT02_BASE_DIR/apks/tmp
INSTRUMENTED_DIR=$EXPERIMENT02_BASE_DIR/instrumented
RESULTS_DIR=$EXPERIMENT02_BASE_DIR/results

echo "APKS_DIR=${APKS_DIR}"

docker run -it --rm --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvandroid_tools:0.9.0 bash
#docker run -it --rm --entrypoint "/bin/bash" --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec-01 phtcosta/rvandroid:0.0.1

#docker run -it --rm --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec_teste-01 phtcosta/rvandroid_tools:0.0.1
#docker run -it --rm --entrypoint "/bin/bash" --device /dev/kvm -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name rvsec_teste-01 phtcosta/rvandroid_tools:0.0.1

#venv/bin/python main.py
#docker run -it --rm --device /dev/kvm --name rvsec_teste-01 \
#-v $APKS_DIR:/opt/rvsec/rv-android/apks \
#-v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
#-v $RESULTS_DIR:/opt/rvsec/rv-android/results \
#-e MEMORY=6144 -e CORES=2 \
#phtcosta/rvandroid_tools:0.0.1

# --entrypoint "/opt/rvsec/rv-android/venv/bin/python /opt/rvsec/rv-android/main.py"
# --entrypoint "/bin/bash"
#docker run -it --rm --device /dev/kvm --entrypoint "python main.py" \
#--name rvsec_teste-01 \
#-v $APKS_DIR:/opt/rvsec/rv-android/apks \
#-v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
#-v $RESULTS_DIR:/opt/rvsec/rv-android/results \
#-e MEMORY=6144 -e CORES=2 \
#phtcosta/rvandroid_tools:0.0.1


# docker run -it --rm --device /dev/kvm --entrypoint "/bin/bash" --name rvsec_teste-03 \
# -v $APKS_DIR:/opt/rvsec/rv-android/apks \
# -v $INSTRUMENTED_DIR:/opt/rvsec/rv-android/out \
# -v $RESULTS_DIR:/opt/rvsec/rv-android/results \
# -e MEMORY=6144 -e CORES=2 \
# phtcosta/rvandroid_tools:0.9.0

#docker run --rm phtcosta/rvandroid_tools:0.0.1 python --version

#docker run -d --device /dev/kvm -p 5555:5555 -v androiddata:/data -e PARTITION=24576 -e MEMORY=6144 -e CORES=2 --name docker-android-emulator cndaqiang/docker-android-emulator:api-33

#cd /opt/rvsec/rv-android && source venv/bin/activate &&
