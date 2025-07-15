#!/bin/env bash

echo "Emulator name: $EMUNAME"
echo "Timeout: $TIMEOUT_IN_MINUTES minutes"

cd /ares

venv/bin/python3 rl_interaction/parallel_exec.py \
    --list_devices . \
    --appium_ports 4270 \
    --android_ports 0 \
    --timer $TIMEOUT_IN_MINUTES \
    --rotation \
    --algo SAC \
    --iterations 1 \
    --path "apks" \
    --timesteps 1000000 \
    --trials_per_app 1 \
    --real_device \
    --udid "$EMUNAME" \
    --pool_strings=rl_interaction/strings.txt