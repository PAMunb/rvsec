#!/bin/sh

set -e

if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: ./instrument.sh [apk] [mop_dir] [mop_out_dir]"
    exit
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "[Error] No ANDROID_HOME environment variable found"
    exit 1
fi

APK=$1                # apk to be instrumented
MOP_DIR=$2            # specs dir (may contain aspects or java classes to be included in final apk)
MOP_OUT_DIR=$3        # monitor related artifacts (previously generated)
OUT_DIR="out"         # out dir (for instrumented apk)
LIB_TMP="lib_tmp"     # libs dir (maven dependencies)
APK_NAME="$(basename $APK)"

JAVAMOP_HOME=../javamop
RV_MONITOR_HOME=../rv-monitor
#ASPECTJ_HOME=/home/pedro/desenvolvimento/aplicativos/aspectj-1.9.6

ANDROID_PLATFORM=android-33
ANDROID_BUILD_TOOLS=33.0.0
ANDROID_SDK_HOME=$ANDROID_HOME
ANDROID_PLATFORM_LIB=$ANDROID_SDK_HOME/platforms/$ANDROID_PLATFORM
ANDROID_BUILD_LIB=$ANDROID_SDK_HOME/build-tools/$ANDROID_BUILD_TOOLS
SDK_BUILD_VERSION=$($ANDROID_BUILD_LIB/aapt dump badging ./apks/$APK_NAME | grep -oP "(targetSdkVersion|platformBuildVersionCode)[=:][\"']?\d+[\"']?" | sed -n "1s/[^0-9]//gp")

echo "APK=$APK_NAME on SDK=$SDK_BUILD_VERSION"

# Set up output directories, removing old files
rm -rf tmp rvm_tmp jadx_tmp $LIB_TMP
mkdir tmp rvm_tmp jadx_tmp $LIB_TMP

# Copy dependency JARs to 'lib_tmp' folder
mvn clean compile

CLASSPATH="$ANDROID_PLATFORM_LIB/android.jar:$(printf %s: $LIB_TMP/*.jar):."
echo "CLASSPATH=$CLASSPATH"

# Convert APK to Jar (with Java bytecode), verify output Jar
echo "[+] Extracting Java classes to JAR in tmp/"
#REMOVE sh lib/dex2jar/d2j-dex2jar.sh -f -o tmp/no_monitor_$APK_NAME.jar $APK
#REMOVE sh lib/dex2jar/d2j-asm-verify.sh tmp/no_monitor_$APK_NAME.jar

sh lib/jadx/bin/jadx --no-debug-info -dr jadx_tmp -ds tmp $APK

# Extract application classes, remove temporary application Jar
#REMOVE unzip -q tmp/no_monitor_$APK_NAME.jar -d tmp
#REMOVE rm tmp/no_monitor_$APK_NAME.jar

# cp $MOP_OUT_DIR/*.java rvm_tmp/.
# cp $MOP_OUT_DIR/*.aj rvm_tmp/.

# Merge monitor and application sources
# cp -rf rvm_tmp/ tmp/
# rm -rf rvm_tmp/*

Merge monitor and application sources
cp -rf $MOP_DIR/* tmp/
cp $MOP_OUT_DIR/*.java tmp/.
cp $MOP_OUT_DIR/*.aj tmp/.
rm tmp/*.mop

# Instrument application with monitor classes
echo "[+] Instrumenting"

ajc -Xmx10240m -cp $CLASSPATH:mop:tmp:. -Xlint:ignore -inpath tmp -d tmp -source 1.8 -sourceroots mop
if [ "$?" = 1 ] ; then
    echo "AspectJ has encountered a fatal error and needs to close. Dying!"
    exit
fi

exit

echo "[+] Creating APK"
# Extract RV-Monitor support classes
cp lib_tmp/rv-monitor-rt.jar rvm_tmp/.
cp lib_tmp/rvsec-core.jar rvm_tmp/.
cp lib_tmp/rvsec-logger-logcat.jar rvm_tmp/.
cd rvm_tmp
jar xf rv-monitor-rt.jar
jar xf rvsec-core.jar
jar xf rvsec-logger-logcat.jar

# Remove rv-monitor-rt's manifest and the temporarily copied Jar + property files
rm -rf META-INF *.jar
cd ..

# Merge RV-Monitor support classes
cp -rf rvm_tmp/* tmp/

# Compress resulting transformed classes to Jar
cd tmp
jar cf monitored_$APK_NAME.jar *
cd ..

# Compile classes in Jar to Dex format
#sh lib/dex2jar/d2j-jar2dex.sh -f -o tmp/classes.dex tmp/monitored_$APK.jar
#d8 tmp/monitored_$APK_NAME.jar --release --lib $ANDROID_PLATFORM_LIB/android.jar --min-api 21

$ANDROID_BUILD_LIB/d8 --no-desugaring tmp/monitored_$APK_NAME.jar --release --lib $ANDROID_PLATFORM_LIB/android.jar --min-api $SDK_BUILD_VERSION

# If using D8, change classes.dex folder
echo "Coping classes.dex to ./tmp and delete from this directory"
cp classes.dex tmp/
rm classes.dex

############# confuso
cp $APK tmp/$APK_NAME
cd tmp

# Replace old classes.dex in APK with new classes.dex
zip -r $APK_NAME classes.dex

# Copy final classes.dex
cp $APK_NAME ../$OUT_DIR/unsigned_$APK_NAME
cd ..

# Verify and sign the Jar with debug key, repairing any inconsistent manifests
sh lib/dex2jar/d2j-asm-verify.sh out/unsigned_$APK_NAME

cd $OUT_DIR

echo "[+] Signing APK"
# Sign debug Jar with final key
sh ../lib/dex2jar/d2j-apk-sign.sh -f -o $APK_NAME unsigned_$APK_NAME
zip -d $APK_NAME "META-INF*"

jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore ../keystore.jks $APK_NAME server -storepass password
#jarsigner -verify -verbose -certs ../$OUT_DIR/$APK_NAME

rm unsigned_$APK_NAME

# Clean up
cd ..
rm -rf tmp rvm_tmp jadx_tmp $LIB_TMP
rm -rf mop_aux/*.aj
rm -rf mop_aux/*.rvm
rm -rf mop_aux/*.java

rm -rf mop/*.aj
rm -rf mop/*.rvm
rm -rf mop/*.java

echo "[+] Done! Final apk generated in $OUT_DIR/$APK_NAME"