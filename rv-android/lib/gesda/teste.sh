#!/bin/sh

ANDROID_PLATFORMS_DIR="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
RT_JAR="/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar"
OUT="/home/pedro/tmp/rvsec-gesda.json"
APK="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"

echo "[+] Executing ..."
java -jar rvsec-gesda.jar --android-dir $ANDROID_PLATFORMS_DIR --rt-jar $RT_JAR --output $OUT --apk $APK
