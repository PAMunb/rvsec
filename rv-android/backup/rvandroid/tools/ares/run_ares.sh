#!/bin/bash

APPNAME=$1
EMUNAME=$2
TIMEOUT=$3
ARES_DIR=$4

#APPNAME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/com.github.axet.hourlyreminder_476.apk"
#EMUNAME="emulator-5554"
#TIMEOUT=2
#ARES_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/ares"

echo $APPNAME
echo $EMUNAME
echo $TIMEOUT
echo $ARES_DIR

cp -f $APPNAME $ARES_DIR/apks/app.apk
#docker run -v $ARES_DIR/apks:/ares/apks -e TIMEOUT_IN_MINUTES=$TIMEOUT -e EMUNAME=$EMUNAME --net=host -i --rm phtcosta/ares:0.0.2 #\
cd $ARES_DIR
export PYTHONPATH=$ARES_DIR
venv/bin/python rl_interaction/parallel_exec.py \
    --list_devices . \
    --appium_ports 4270 \
    --android_ports 0 \
    --timer $TIMEOUT \
    --rotation \
    --algo SAC \
    --iterations 1 \
    --path "apks" \
    --timesteps 1000000 \
    --trials_per_app 1 \
    --real_device \
    --udid "$EMUNAME" \
    --pool_strings=rl_interaction/strings.txt