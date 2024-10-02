#!/bin/sh
     
ANDROID_PLATFORMS_DIR="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
MOP_SPECS_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources"
RT_JAR="/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar"
OUT="/home/pedro/tmp/rvsec-reach.json"
GESDA_FILE="/home/pedro/tmp/rvsec-gesda.json"      
APK="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"
WRITER="json"
#WRITER="csv"

echo "[+] Executing ..."
java -jar target/rvsec-reach-jar-with-dependencies.jar --android-dir $ANDROID_PLATFORMS_DIR --mop-dir $MOP_SPECS_DIR --rt-jar $RT_JAR --output $OUT --gesda $GESDA_FILE --writer $WRITER --apk $APK
