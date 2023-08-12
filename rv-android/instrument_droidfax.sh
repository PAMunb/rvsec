#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: ./instrument_droidfax.sh [apk] [out_dir]"
    exit
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "[Error] No ANDROID_HOME environment variable found"
    exit 1
fi

ANDROID_PLATFORM=android-29
ANDROID_SDK_HOME=$ANDROID_HOME
ANDROID_PLATFORM_LIB=$ANDROID_SDK_HOME/platforms/$ANDROID_PLATFORM
ANDROID_JAR_PATH=$ANDROID_PLATFORM_LIB/android.jar

APK=$1             # apk to be instrumented
OUT_DIR=$2         # out dir (for instrumented apk)
DROIDFAX_LIBS="lib/droidfax"
TMP_DIR="tmp"

echo "[+] Processing APK=$APK"

APK_NAME="$(basename $APK)"
SIGNED_APK="signed_$APK_NAME"

# Set up output directories, removing old files
rm -rf $TMP_DIR
mkdir $TMP_DIR

MAIN_CP="$(printf %s: $DROIDFAX_LIBS/*.jar)"
echo "MAIN_CP=$MAIN_CP"

DROIDFAX_JAR=$DROIDFAX_LIBS/droidfax.jar
SOOT_CP="$DROIDFAX_JAR:$ANDROID_JAR_PATH"
echo "SOOT_CP=$SOOT_CP"


echo "[+] Instrumenting ..."
cmd="java -Xmx100g -Xss1g -ea -cp ${MAIN_CP} dynCG.sceneInstr \
	-w -cp $SOOT_CP -p cg verbose:false,implicit-entry:true \
	-p cg.spark verbose:false,on-fly-cg:true,rta:false \
	-d $OUT_DIR \
	-instr3rdparty \
	-process-dir $APK"

$cmd

echo "[+] Signing ..."
UNSIGNED_APK_NAME="unsigned_$APK_NAME"
mv $OUT_DIR/$APK_NAME $OUT_DIR/$UNSIGNED_APK_NAME

# Sign debug Jar with final key
sh lib/dex2jar/d2j-apk-sign.sh -f -o $OUT_DIR/$APK_NAME $OUT_DIR/$UNSIGNED_APK_NAME
zip -q -d $OUT_DIR/$APK_NAME "META-INF*"

jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore keystore.jks $OUT_DIR/$APK_NAME server -storepass password

jarsigner -verify -certs $OUT_DIR/$APK_NAME

#mv $OUT_DIR/$APK_NAME $OUT_DIR/$SIGNED_APK
#zipalign -f -v 4 $OUT_DIR/$SIGNED_APK $OUT_DIR/$APK_NAME
#rm $OUT_DIR/$SIGNED_APK

echo "[+] Done! Instrumented (droidfax) apk generated in $OUT_DIR/$APK_NAME"
