#!/bin/bash
     
ANDROID_PLATFORMS_DIR="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
#ANDROID_PLATFORMS_DIR="/home/pedro/desenvolvimento/aplicativos/android/platforms"
MOP_SPECS_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca"
RT_JAR="/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar"
# WRITER="json"
WRITER="csv"
TIMEOUT=300

APKS_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_exp02"
#APKS_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini"
OUT_DIR="/home/pedro/tmp"
OUT_TIMES="$OUT_DIR/reach_tempos.txt"

if [[ -f "$OUT_TIMES" ]]; then
    rm -v -f $OUT_TIMES
    echo "apk_name == runtime (in secs)" >> "$OUT_TIMES"
fi

if [[ -d "$APKS_DIR" ]]; then
    for APK in "$APKS_DIR"/*.apk; do
        if [[ -f "$APK" ]]; then
            apk_name=$(basename "$APK" .apk)
            output="$OUT_DIR/reach_$apk_name.reach"
                 
            echo "[+] Executing: $APK"
            start=$(date +%s.%N)
			java -jar target/rvsec-reach.jar \
                    --android-dir $ANDROID_PLATFORMS_DIR \
                    --mop-dir $MOP_SPECS_DIR \
                    --rt-jar $RT_JAR \
                    --output $output \
                    --writer $WRITER \
                    --timeout $TIMEOUT \
                    --apk $APK \
                    2>&1 > /dev/null
            end=$(date +%s.%N)    
            runtime=$(python -c "print(${end} - ${start})")

            echo "$apk_name == $runtime" >> "$OUT_TIMES"
        fi
    done
    echo "[+] File saved: $OUT_TIMES"
else
    echo "The folder '$APKS_DIR' does not exist."
    exit 1
fi
