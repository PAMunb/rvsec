#!/bin/sh

ANDROID_PLATFORMS_DIR=/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms
APK=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk
APK_PACKAGE=br.unb.cic.cryptoapp
OUTPUT_FILE=/home/pedro/tmp/teste.csv

mvn clean package

java -jar target/methods-extractor.jar --apk $APK --apk-package $APK_PACKAGE --android-dir $ANDROID_PLATFORMS_DIR --output $OUTPUT_FILE

echo "[+] Done!"
