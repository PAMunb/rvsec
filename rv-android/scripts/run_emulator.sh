#!/bin/sh

EMULATOR_NAME_x86="RVSec"

echo "[+] Starting emulator"

#nohup emulator @${EMULATOR_NAME_x86} -writable-system -wipe-data -no-boot-anim -no-audio -netdelay none &
emulator @${EMULATOR_NAME_x86} -writable-system -wipe-data -no-boot-anim -no-audio -netdelay none 

#adb wait-for-device

#adb install ../media.apk
