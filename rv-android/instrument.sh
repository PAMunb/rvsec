#!/bin/sh

if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: ./mop.sh [apk] [mop_dir] [mop_out_dir]"
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

APK=$1                # apk to be instrumented
MOP_DIR=$2            # specs dir (may contain aspects or java classes to be included in final apk)
MOP_OUT_DIR=$3        # monitor related artifacts (previously generated)
OUT_DIR="out"         # out dir (for instrumented apk)
LIB_TMP="lib_tmp"     # libs dir (maven dependencies)

# Set up output directories, removing old files
rm -rf tmp $LIB_TMP
mkdir tmp rvm_tmp $LIB_TMP

# Copy dependency JARs to 'lib_tmp' folder 
mvn clean compile

CLASSPATH="$ANDROID_PLATFORM_LIB/android.jar:$(printf %s: $LIB_TMP/*.jar):."
echo "CLASSPATH=$CLASSPATH"

APK_NAME="$(basename $APK)"
echo "APK=$APK_NAME"

# Convert APK to Jar (with Java bytecode), verify output Jar
echo "[+] Extracting Java classes to JAR in tmp/"
sh lib/dex2jar/d2j-dex2jar.sh -f -o tmp/no_monitor_$APK_NAME.jar $1
sh lib/dex2jar/d2j-asm-verify.sh tmp/no_monitor_$APK_NAME.jar

# Extract application classes, remove temporary application Jar
unzip -q tmp/no_monitor_$APK_NAME.jar -d tmp
rm tmp/no_monitor_$APK_NAME.jar


# Merge monitor and application sources
cp -rf $MOP_DIR/* tmp/
cp $MOP_OUT_DIR/*.java tmp/.
cp $MOP_OUT_DIR/*.aj tmp/.
rm tmp/*.mop


# Instrument application with monitor classes
echo "[+] Instrumenting"
#ajc -Xmx10240m -cp $CLASSPATH:mop:tmp:. -Xlint:ignore -showWeaveInfo -inpath tmp -d tmp -source 1.8 -sourceroots mop
ajc -cp $CLASSPATH:$MOP_DIR:tmp:. -Xlint:ignore -inpath tmp -d tmp -source 1.8 -sourceroots tmp
if [ "$?" = 1 ] ; then
    echo "AspectJ has encountered a fatal error and needs to close. Dying!"
    exit
fi

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
#sh lib/dex2jar/d2j-jar2dex.sh -f -o tmp/classes.dex tmp/monitored_$1.jar
#d8 tmp/monitored_$APK_NAME.jar --release --lib $ANDROID_PLATFORM_LIB/android.jar --min-api 21
d8 tmp/monitored_$APK_NAME.jar --lib $ANDROID_PLATFORM_LIB/android.jar --min-api 21


# If using D8, change classes.dex folder
echo "Coping classes.dex to ./tmp and delete from this directory"
cp classes.dex tmp/
rm classes.dex

############# confuso
cp $1 tmp/$APK_NAME
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
rm -rf tmp rvm_tmp $LIB_TMP

echo "[+] Done! Final apk generated in $OUT_DIR/$APK_NAME"
