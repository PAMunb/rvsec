#!/bin/env bash

APPNAME=$1
EMUNAME=$2
TIMEOUT=$3
ARES_DIR=$4

echo $APPNAME
echo $EMUNAME
echo $TIMEOUT
echo $ARES_DIR

cp -f $APPNAME $ARES_DIR/apks/app.apk
docker  run -v $ARES_DIR/apks:/ares/apks --net=host -it --rm ares \
        venv/bin/python3 rl_interaction/parallel_exec.py \
            --list_devices . \
            --appium_ports 4270 \
            --android_ports 0 \
            --timer $TIMEOUT \
            --rotation \
            --algo SAC \
            --iterations 1 \
            --path "apks" \
            --timesteps 9999 \
            --trials_per_app 1 \
            --real_device \
            --udid "$EMUNAME" \
            --pool_strings=rl_interaction/strings.txt