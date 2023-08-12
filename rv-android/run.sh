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

# ERRO: nessa ordem a instrumentacao do droidfax funciona mas a do rvsec crash o app
#./instrument_rvsec.sh $APK mop_out instr_rvsec
#./instrument_droidfax.sh instr_rvsec/$APK_NAME out


# com essa ordem da erro na instrumentacao do rvsec, gera o apk e o droidfax funciona ... mas nao leva a instrumentacao do rvsec
#./instrument_droidfax.sh $APK instr_droidfax
#./instrument_rvsec.sh instr_droidfax/$APK_NAME mop_out out


./instrument_rvsec.sh $APK mop_out out

echo "[+] Done! Final apk generated in out/$APK_NAME"
