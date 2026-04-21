#!/bin/sh

EMULATOR_NAME="RVSec"

echo "[+] Starting emulator"

# -------------------------------------------------------------------------
# OLD — API 29 x86 (`RVSec` AVD before gh50 Section 17 / INV-INS-24). Kept
# commented for reference; the emulator flags are identical to the new
# launch because the difference is only the AVD behind the name `RVSec`
# (re-created from system-images;android-30;google_apis;x86_64).
# -------------------------------------------------------------------------
#emulator @${EMULATOR_NAME} -writable-system -wipe-data -no-boot-anim -noaudio -no-snapshot-save -delay-adb

# -------------------------------------------------------------------------
# NEW — API 30 x86_64 google_apis (Android 11).
# Matches `docker/android/Dockerfile`: API_LEVEL=30, ARCHITECTURE=x86_64.
# AVD `RVSec` was recreated with:
#   avdmanager --verbose create avd --force \
#     --name RVSec \
#     --abi google_apis/x86_64 \
#     --package "system-images;android-30;google_apis;x86_64" \
#     --device pixel
# -------------------------------------------------------------------------
emulator @${EMULATOR_NAME} -writable-system -wipe-data -no-boot-anim -noaudio -no-snapshot-save -delay-adb

#adb wait-for-device

#adb install ../media.apk

# adb logcat -v threadtime -s RVSEC RVSEC-COV
