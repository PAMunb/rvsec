#!/bin/sh

EMULATOR_NAME="RVSec"

echo "[+] Starting emulator"

# Launches the canonical RVSec AVD (API 30 x86_64 google_apis, gh55 default).
# Image and AVD are provisioned by docker/android/Dockerfile; this script
# starts the emulator with the flags expected by rv-platform's boot code:
# -writable-system    GATOR pushes its hooks; without this, post-boot writes fail
# -wipe-data          fresh state per run, reproducible coverage measurements
# -no-boot-anim       cuts ~5s of boot animation for parallel-container starts
# -noaudio            no PulseAudio dependency on headless hosts
# -no-snapshot-save   discard the cold-boot snapshot to keep image immutable
# -delay-adb          wait for adb to bind before exposing the device
emulator @${EMULATOR_NAME} -writable-system -wipe-data -no-boot-anim -noaudio -no-snapshot-save -delay-adb
