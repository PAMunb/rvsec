#!/bin/sh

#APK=osmtracker.apk
#APK=apks/media.apk
#APK=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/media.apk
APK=cryptoapp.apk
#APK=media.apk

APK_NAME="$(basename $APK)"

#MOP_DIR=mop
MOP_DIR=mop_mini

./generate_monitor.sh $MOP_DIR mop_out

./instrument.sh $APK mop_out out

echo "[+] Done! Final apk generated in out/$APK_NAME"
