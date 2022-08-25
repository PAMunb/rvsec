#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: instrument_apk.sh [apk] [mop]"
    exit
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "[Error] No ANDROID_HOME environment variable found"
    exit 1
fi

#ASPECTJ_HOME=/home/pedro/desenvolvimento/aplicativos/aspectj-1.9.6

JAVAMOP_HOME=../javamop
RV_MONITOR_HOME=../rv-monitor

ANDROID_PLATFORM=android-17
ANDROID_SDK_HOME=/home/pedro/Android/Sdk
ANDROID_PLATFORM_LIB=$ANDROID_SDK_HOME/platforms/$ANDROID_PLATFORM


# Set up output directories, removing old files
find $2 -name "*.java" -exec rm -Rf {} \;
find $2 -name "*.rvm" -exec rm -Rf {} \;
find $2 -name "*.aj" -exec rm -Rf {} \;
rm -rf out tmp rvm_tmp lib_tmp
mkdir out
mkdir tmp
mkdir rvm_tmp
mkdir lib_tmp


# Copy dependency JARs to 'lib_tmp' folder 
mvn clean compile
CLASSPATH=$ANDROID_PLATFORM_LIB/android.jar:$(for i in lib_tmp/*.jar ; do echo -n $i: ; done):.
#CLASSPATH=/home/pedro/Android/Sdk/platforms/android-17/android.jar:lib_tmp/aspectjrt.jar:lib_tmp/aspectjtools.jar:lib_tmp/aspectjweaver.jar:lib_tmp/rv-monitor-rt.jar:lib_tmp/rv-monitor.jar:lib_tmp/rvsec.jar:.
echo "CLASSPATH=$CLASSPATH"
#/home/pedro/desenvolvimento/aplicativos/aspectj-1.8.1/lib/aspectjrt.jar:



# Convert APK to Jar (with Java bytecode), verify output Jar
echo "[+] Extracting Java classes to JAR in tmp/"
sh lib/dex2jar/d2j-dex2jar.sh -f -o tmp/no_monitor_$1.jar $1
sh lib/dex2jar/d2j-asm-verify.sh tmp/no_monitor_$1.jar

# Extract application classes, remove temporary application Jar
unzip -q tmp/no_monitor_$1.jar -d tmp
rm tmp/no_monitor_$1.jar

# Use JavaMOP
echo "[+] Executing JavaMOP"
$JAVAMOP_HOME/bin/javamop -s -merge $2/*.mop

# Use RV-Monitor
echo "[+] Executing RV-Monitor"
$RV_MONITOR_HOME/bin/rv-monitor -s -merge -d $2 $2/*.rvm


# Move all Java monitor classes into their final package namespace directory
python lib/fix_java_packages.py
if [ "$?" = 1 ] ; then
    # Unable to resolve Java package
    exit
fi


cp $2/*.java rvm_tmp/.
cp $2/*.aj rvm_tmp/.



# Merge monitor and application sources
cp -rf rvm_tmp/ tmp/
rm -rf rvm_tmp/*

# Instrument application with monitor classes
#ajc -cp $CLASSPATH -inpath tmp -d tmp -source 1.8 -sourceroots $2
#ajc -cp $CLASSPATH -inpath tmp -d tmp -source 1.8 -sourceroots $2
#if [ "$?" = 1 ] ; then
#    echo "AspectJ has encountered a fatal error and needs to close. Dying!"
#    exit
#fi

#ajc -cp /home/pedro/Android/Sdk/platforms/android-17/android.jar:lib_tmp/aspectjrt.jar:lib_tmp/aspectjtools.jar:lib_tmp/aspectjweaver.jar:lib_tmp/cfg.jar:lib_tmp/ere.jar:lib_tmp/fsm.jar:lib_tmp/guava.jar:lib_tmp/logicrepository.jar:lib_tmp/ltl.jar:lib_tmp/pda.jar:lib_tmp/po.jar:lib_tmp/ptcaret.jar:lib_tmp/ptltl.jar:lib_tmp/rv-monitor-rt.jar:lib_tmp/rv-monitor.jar:lib_tmp/rvsec.jar:lib_tmp/scala-library.jar:lib_tmp/scala-parser-combinators_2.11.jar:lib_tmp/srs.jar:lib_tmp/tfsm.jar:mop:tmp:. -inpath tmp -d tmp -source 1.8 -sourceroots mop
ajc -cp /home/pedro/Android/Sdk/platforms/android-17/android.jar:lib_tmp/aspectjrt.jar:lib_tmp/aspectjtools.jar:lib_tmp/aspectjweaver.jar:lib_tmp/cfg.jar:lib_tmp/ere.jar:lib_tmp/fsm.jar:lib_tmp/guava.jar:lib_tmp/logicrepository.jar:lib_tmp/ltl.jar:lib_tmp/pda.jar:lib_tmp/po.jar:lib_tmp/ptcaret.jar:lib_tmp/ptltl.jar:lib_tmp/rv-monitor-rt.jar:lib_tmp/rv-monitor.jar:lib_tmp/rvsec.jar:lib_tmp/scala-library.jar:lib_tmp/scala-parser-combinators_2.11.jar:lib_tmp/srs.jar:lib_tmp/tfsm.jar:mop:tmp:. -Xlint:ignore -showWeaveInfo -inpath tmp -d tmp -source 1.8 -sourceroots mop





# Extract RV-Monitor support classes
cp lib_tmp/rv-monitor-rt.jar rvm_tmp/.
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

jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore ../keystore.jks $1 server -storepass password 
#jarsigner -verify ../out/$1

# Clean up
cd ..
rm -rf tmp rvm_tmp

echo "[+] Done! Final apk generated in out/$1"
