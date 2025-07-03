#!/bin/bash

# start emulator
# install cryptoapp apk

# run ape
adb push -a -p ape.jar "/data/local/tmp/ape.jar"

adb -s emulator-5554 shell CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process /data/local/tmp/ com.android.commands.monkey.Monkey -p br.unb.cic.cryptoapp --running-minutes 1 --ape sata
adb -s emulator-5554 shell CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process /data/local/tmp/ com.android.commands.monkey.Monkey -p br.unb.cic.cryptoapp --running-minutes 0 --ape sata


echo "[+] Done!"
