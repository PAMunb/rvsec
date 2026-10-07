#!/usr/bin/env bash
# Build probe.jar (StampProbe dexed for app_process) next to this script.
# Compiles against android-30/android.jar alone and dexes with d8 35.0.1.
set -euo pipefail

: "${ANDROID_HOME:?ANDROID_HOME must point to the Android SDK}"
JAVA_HOME="${JAVA_HOME:-$HOME/.sdkman/candidates/java/21.0.12-tem}"
ANDROID_JAR="$ANDROID_HOME/platforms/android-30/android.jar"
D8="$ANDROID_HOME/build-tools/35.0.1/d8"
HERE="$(cd "$(dirname "$0")" && pwd)"

rm -f "$HERE"/*.class "$HERE/probe.jar"
"$JAVA_HOME/bin/javac" -source 1.8 -target 1.8 -Xlint:-options \
    -cp "$ANDROID_JAR" -d "$HERE" "$HERE/StampProbe.java"
JAVA_HOME="$JAVA_HOME" "$D8" --release --min-api 21 --lib "$ANDROID_JAR" \
    --output "$HERE/probe.jar" "$HERE"/*.class
echo "built $HERE/probe.jar ($(stat -c %s "$HERE/probe.jar") bytes)"
