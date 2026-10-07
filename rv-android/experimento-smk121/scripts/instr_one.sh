#!/usr/bin/env bash
# Instrument one APK with a given instr-cli.jar, using the descriptor, monitor
# sources and runtime jars of the stamp-off pre-processing run (tasks 9.0), with
# android-36/android.jar and d8 35.0.1 pinned. The monitor sources are copied into
# <out>/monitors unless <monitors-dir> is given (shared directory, task 9.1 part 2).
#
# usage: instr_one.sh <instr-cli.jar> <apk> <out> [monitors-dir] [-- extra instr-cli args]
# Environment passes through, so RVSEC_STAMP_HANDLERS reaches instr-cli (task 9.3).
set -euo pipefail
X="$(cd "$(dirname "$0")/.." && pwd)"
PRE="$X/results/pre"
: "${ANDROID_HOME:=/home/pedro/desenvolvimento/aplicativos/android/sdk}"
: "${JAVA_HOME:=$HOME/.sdkman/candidates/java/21.0.12-tem}"
KEYSTORE="$X/../modules/rv-instrumentation/assets/keystore.jks"

jar="$1"; apk="$2"; out="$3"; shift 3
monitors="$out/monitors"
if [[ $# -gt 0 && "$1" != "--" ]]; then monitors="$1"; shift; fi
[[ $# -gt 0 && "$1" == "--" ]] && shift

mkdir -p "$out"
if [[ "$monitors" == "$out/monitors" ]]; then
    rm -rf "$monitors"
    cp -r "$PRE/monitors" "$monitors"
fi
lib="$PRE/lib_tmp"
"$JAVA_HOME/bin/java" -Xmx8g -jar "$jar" instrument "$apk" \
    --descriptor "$monitors/MultiSpec_1MonitorAspect.json" \
    --output "$out/apk" --work-dir "$out/work" --monitor-src-dir "$monitors" \
    --keystore "$KEYSTORE" --keystore-pass password --key-alias server --key-pass password \
    --classpath "$lib/rv-monitor-rt.jar,$lib/rvsec-core.jar,$lib/rvsec-logger-logcat.jar" \
    --android-jar "$ANDROID_HOME/platforms/android-36/android.jar" \
    --d8 "$ANDROID_HOME/build-tools/35.0.1/d8" \
    "$@"
