#!/bin/bash

# Script used to instrument an APK with the rvsec (previously generated) monitors.

if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: ./instrument2.sh [apk] [mop_out_dir] [out_dir]"
    exit
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "[Error] No ANDROID_HOME environment variable found"
    exit 1
fi

#ASPECTJ_HOME=/home/pedro/desenvolvimento/aplicativos/aspectj-1.9.6

JAVAMOP_HOME=../javamop
RV_MONITOR_HOME=../rv-monitor

ANDROID_PLATFORM=android-29
ANDROID_SDK_HOME=$ANDROID_HOME
ANDROID_PLATFORM_LIB=$ANDROID_SDK_HOME/platforms/$ANDROID_PLATFORM
#SDK_BUILD_VERSION=$($ANDROID_BUILD_LIB/aapt dump badging ./apks/$APK_NAME | grep -oP "(targetSdkVersion|platformBuildVersionCode)[=:][\"']?\d+[\"']?" | sed -n "1s/[^0-9]//gp")


APK=$1                # apk to be instrumented
MOP_OUT_DIR=$2        # monitor related artifacts (previously generated)
OUT_DIR=$3            # out dir (for instrumented apk)
LIB_TMP="lib_tmp"     # libs dir (maven dependencies)
TMP_DIR="tmp"
RVM_TMP_DIR="rvm_tmp"

echo "[+] Processing APK=$APK"

package=$(aapt dump badging $APK | awk '/package/{gsub("name=|'"'"'","");  print $2}')
replace="."
replacewith="/"
PACKAGE="${package//${replace}/${replacewith}}"


# Set up output directories, removing old files
rm -rf $TMP_DIR $RVM_TMP_DIR $LIB_TMP $OUT_DIR
mkdir $TMP_DIR $RVM_TMP_DIR $LIB_TMP $OUT_DIR

# Copy dependency JARs to 'lib_tmp' folder
mvn clean compile

CLASSPATH="$ANDROID_PLATFORM_LIB/android.jar:$(printf %s: $LIB_TMP/*.jar):."
echo "CLASSPATH=$CLASSPATH"

APK_NAME="$(basename $APK)"
echo "APK=$APK_NAME"
NO_MONITOR_JAR=no_monitor_$APK_NAME.jar
MONITORED_JAR=monitored_$APK_NAME.jar
UNSIGNED_APK_NAME=unsigned_$APK_NAME

# Convert APK to Jar (with Java bytecode), verify output Jar
echo "[+] Extracting Java classes to JAR in $TMP_DIR/"
sh lib/dex2jar/d2j-dex2jar.sh -f -o $TMP_DIR/$NO_MONITOR_JAR $APK
sh lib/dex2jar/d2j-asm-verify.sh $TMP_DIR/$NO_MONITOR_JAR


# Extract application classes, remove temporary application Jar
unzip -q $TMP_DIR/$NO_MONITOR_JAR -d $TMP_DIR
rm $TMP_DIR/$NO_MONITOR_JAR


# Merge monitor and application sources
#cp $MOP_OUT_DIR/* $TMP_DIR

rm -Rf tmp_ajc
mkdir tmp_ajc
cp $MOP_OUT_DIR/* tmp_ajc
cd $TMP_DIR
cp -r $PACKAGE/**/* --parents ../tmp_ajc
cd -

# Instrument application with monitor classes
echo "[+] Instrumenting"
#ajc -Xmx10240m -cp $CLASSPATH:mop:tmp:. -Xlint:ignore -showWeaveInfo -inpath tmp -d tmp -source 1.8 -sourceroots mop
#ajc -cp $CLASSPATH -Xlint:ignore -inpath tmp -d tmp -source 1.8
ajc -cp $CLASSPATH:$TMP_DIR -Xlint:ignore -showWeaveInfo -inpath tmp_ajc -d $TMP_DIR -source 1.8 -sourceroots tmp_ajc
if [ "$?" = 1 ] ; then
    echo "AspectJ has encountered a fatal error and needs to close. Dying!"
    exit
fi


echo "[+] Creating APK"
# Extract RV-Monitor support classes
cp $LIB_TMP/rv-monitor-rt.jar $RVM_TMP_DIR/.
cp $LIB_TMP/rvsec-core.jar $RVM_TMP_DIR/.
cp $LIB_TMP/rvsec-logger-logcat.jar $RVM_TMP_DIR/.
cp $LIB_TMP/aspectjrt.jar $RVM_TMP_DIR/.
cd $RVM_TMP_DIR
jar xf rv-monitor-rt.jar
jar xf rvsec-core.jar
jar xf rvsec-logger-logcat.jar
jar xf aspectjrt.jar

# Remove rv-monitor-rt's manifest and the temporarily copied Jars + property files
rm -rf META-INF *.jar
cd ..

# Merge RV-Monitor support classes
cp -rf $RVM_TMP_DIR/* $TMP_DIR/

# Compress resulting transformed classes to Jar
cd $TMP_DIR
jar cf $MONITORED_JAR *
cd ..

# Compile classes in Jar to Dex format
#sh lib/dex2jar/d2j-jar2dex.sh -f -o tmp/classes.dex tmp/monitored_$1.jar
#d8 tmp/monitored_$APK_NAME.jar --release --lib $ANDROID_PLATFORM_LIB/android.jar --min-api 21
d8 $TMP_DIR/$MONITORED_JAR --release --lib $ANDROID_PLATFORM_LIB/android.jar --min-api 26


# If using D8, change classes.dex folder
echo "Coping classes.dex to ./$TMP_DIR and delete from this directory"
#mv classes.dex $TMP_DIR/
cp classes.dex $TMP_DIR/
rm classes.dex

# Replace old classes.dex in APK with new classes.dex
cp -v $APK $TMP_DIR/$APK_NAME
cd $TMP_DIR
zip -r $APK_NAME classes.dex

# Copy new apk to out_dir
cp -v $APK_NAME ../$OUT_DIR/$UNSIGNED_APK_NAME
cd ..

cd $OUT_DIR

# Verify and sign the Jar with debug key, repairing any inconsistent manifests
sh ../lib/dex2jar/d2j-asm-verify.sh $UNSIGNED_APK_NAME

echo "[+] Signing APK"
# Sign debug Jar with final key
sh ../lib/dex2jar/d2j-apk-sign.sh -f -o $APK_NAME $UNSIGNED_APK_NAME
zip -q -d $APK_NAME "META-INF*"

jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore ../keystore.jks $APK_NAME server -storepass password

jarsigner -verify -certs $APK_NAME

rm $UNSIGNED_APK_NAME

# Clean up
cd ..
rm -rf $TMP_DIR $RVM_TMP_DIR $LIB_TMP

echo "[+] Done! Instrumented (rvsec) apk generated in $OUT_DIR/$APK_NAME"
