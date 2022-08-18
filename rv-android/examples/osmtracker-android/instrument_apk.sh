#!/bin/sh

# Copyright 2014 Runtime Verification Inc., All Rights Reserved

#if [ "$#" -ne 6 ]; then
#    echo "Illegal number of parameters!"
#    echo "Usage: instrument_apk.sh [apk] [keystore] [keystore password] [signing key alias] [monitors_directory] [aspects_directory]"
#    exit
#fi

ANDROID_PLATFORM=android-17
ANDROID_SDK_HOME=/home/pedro/Android/Sdk
ANDROID_PLATFORM_LIB=$ANDROID_SDK_HOME/platforms/$ANDROID_PLATFORM
ASPECTJ_HOME=/home/pedro/desenvolvimento/aplicativos/aspectj-1.9.6
RV_MONITOR_HOME=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/target/release/rv-monitor
CLASSPATH=$ANDROID_PLATFORM_LIB/android.jar:$ASPECTJ_HOME/lib/aspectjrt.jar:$RV_MONITOR_HOME/lib/rv-monitor-rt.jar

echo "CLASSPATH=$CLASSPATH"

# Set up output directories, removing old files
rm -rf out tmp rvm_tmp
mkdir out
mkdir tmp
mkdir rvm_tmp

# Convert APK to Jar (with Java bytecode), verify output Jar
echo "[+] Extracting Java classes to JAR in tmp/"
sh lib/dex2jar/d2j-dex2jar.sh -f -o tmp/no_monitor_$1.jar $1
sh lib/dex2jar/d2j-asm-verify.sh tmp/no_monitor_$1.jar

# Extract application classes, remove temporary application Jar
cd tmp
jar xf no_monitor_$1.jar
cd ..

# Use RV-Monitor to compile all monitors to bytecode
cd $5
for i in *.rvm; do
    out=$(${RV_MONITOR_HOME}/bin/rv-monitor $i)
    if echo $out | grep -q "generated" ; then
        echo "RV-Monitor successfully processed $i."
    else
        echo "RV-Monitor failed to process $i with an error! Failing!"
        exit
    fi
done

# Remove sources and dependencies
mv *.java ../rvm_tmp/.
cd ..

# Move all Java monitor classes into their final package namespace directory
python lib/fix_java_packages.py
if [ "$?" = 1 ] ; then
    # Unable to resolve Java package
    exit
fi
rm tmp/no_monitor_$1.jar

# Merge monitor and application sources
cp -rf rvm_tmp/ tmp/
rm -rf rvm_tmp/*

# Instrument application with monitor classes
ajc -cp $CLASSPATH -inpath tmp -showWeaveInfo -d tmp -sourceroots $6
if [ "$?" = 1 ] ; then
    echo "AspectJ has encountered a fatal error and needs to close. Dying!"
    exit
fi

# Extract RV-Monitor support classes
cp $RV_MONITOR_HOME/lib/rv-monitor-rt.jar rvm_tmp/.
cd rvm_tmp
jar xf rv-monitor-rt.jar

# Remove rvmonitorrt's manifest and the temporarily copied Jar + property files
rm -rf META-INF rv-monitor-rt.jar
cd ..

# Merge RV-Monitor support classes
cp -rT rvm_tmp/ tmp/
rm -rf rvm_tmp/*

# Compress resulting transformed classes to Jar
cd tmp
jar cf monitored_$1.jar *
cd ..

# Compile classes in Jar to Dex format
sh lib/dex2jar/d2j-jar2dex.sh -f -o tmp/classes.dex tmp/monitored_$1.jar
cp $1 tmp/$1
cd tmp

# Replace old classes.dex in APK with new classes.dex
zip -r $1 classes.dex

# Copy final classes.dex
cp $1 ../out/unsigned_$1
cd ..

# Verify and sign the Jar with debug key, repairing any inconsistent manifests
sh lib/dex2jar/d2j-asm-verify.sh out/unsigned_$1
cd out

# Sign debug Jar with final key
sh ../lib/dex2jar/d2j-apk-sign.sh -f -o $1 unsigned_$1
zip -d $1 "META-INF*"
#echo $3 | jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore $2 $1 $4

jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore $2 $1 $4 -storepass password 
#jarsigner -verify ../out/$1

# Clean up
cd ..
rm -rf tmp rvm_tmp

echo "[+] Done! Final apk generated in out/$1"
