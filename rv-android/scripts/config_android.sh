#!/bin/sh


# PRE-REQUISITE
# Manual step (/etc/profile or ~/.bashrc):
# - define ANDROID_HOME and ANDROID_SDK_ROOT
# - update PATH
# Example:
# export ANDROID_HOME=/home/pedro/desenvolvimento/android/sdk
# export ANDROID_SDK_ROOT=/home/pedro/desenvolvimento/android/sdk
# export PATH=$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/tools/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/build-tools/30.0.3:$PATH



if [ -z "$ANDROID_HOME" ]; then
    echo "[Error] No ANDROID_HOME environment variable found"
    exit 1
fi

#sdkmanager --list
ANDROID_EMULATOR_PACKAGE_x86="system-images;android-29;google_apis;x86"
ANDROID_PLATFORM_VERSION="platforms;android-29"
ANDROID_SDK_PACKAGES="${ANDROID_EMULATOR_PACKAGE_x86} ${ANDROID_PLATFORM_VERSION} platform-tools emulator build-tools;30.0.3"
EMULATOR_NAME_x86="RVSec"
#DEVICE_SERIAL_NUMBER="emulator-5554"


rm -Rf ${ANDROID_HOME}/cmdline-tools
mkdir ${ANDROID_HOME}/cmdline-tools


# command line tools
# https://developer.android.com/studio#command-tools
echo "[+] Downloading command line tools"
#ANDROID_SDK_VERSION=6514223
ANDROID_SDK_VERSION=8512546
wget -v https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip && \
	unzip *tools*linux*.zip -d ${ANDROID_HOME}/cmdline-tools && \
	mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/tools && \
	rm *tools*linux*.zip


# sdkmanager
echo "[+] Installing SDK packages"
sudo mkdir /root/.android/
sudo touch /root/.android/repositories.cfg
yes Y | sdkmanager --licenses 
yes Y | sdkmanager --verbose --no_https ${ANDROID_SDK_PACKAGES}


echo "[+] Creating virtual device (avd)"
echo "no" | avdmanager --verbose create avd --force --name "${EMULATOR_NAME_x86}" --device "pixel" --package "${ANDROID_EMULATOR_PACKAGE_x86}"


echo "[+] Accept the license agreements of the SDK components"
chmod +x license_accepter.sh && ./license_accepter.sh $ANDROID_SDK_ROOT


echo "[+] Android configured!"
