FROM phtcosta/rvsec_base:0.9.1


# Build-time AVD configuration. Default = API 30 x86_64 google_apis (gh55 D8/D10
# decision; previous default was API 29 x86). Host-side investigation
# (results/avd_compat_investigation/20260506_133454/, n=80) shows API 30 x86_64
# boots in 30s with the existing default config (no -writable-system) and gains
# 7/20 modern APKs with 0 regressions. Docker-container boot smoke (gh55 task
# 6.4a, ≥3 BOOT_COMPLETED runs) is the pre-merge gate that closes the host-vs-
# container gap. Override at build time with `--build-arg API_LEVEL=29 --build-arg
# ARCHITECTURE=x86` to fall back to the legacy AVD if a tool incompatibility
# emerges on API 30 (case-by-case per task 6.5/6.8).
ARG API_LEVEL=30
ARG IMG_TYPE=google_apis
ARG ARCHITECTURE=x86_64
ARG CMD_LINE_VERSION=8512546_latest
ARG DEVICE_ID=pixel
ARG GPU_ACCELERATED=false


ENV PACKAGE_PATH="system-images;android-${API_LEVEL};${IMG_TYPE};${ARCHITECTURE}"
ENV ANDROID_PLATFORM_VERSION="platforms;android-$API_LEVEL"
# sdkmanager --list
ENV ANDROID_SDK_PACKAGES="${PACKAGE_PATH} ${ANDROID_PLATFORM_VERSION} platform-tools build-tools;35.0.1 platforms;android-10 platforms;android-11 platforms;android-12 platforms;android-13 platforms;android-14 platforms;android-15 platforms;android-16 platforms;android-17 platforms;android-18 platforms;android-19 platforms;android-20 platforms;android-21 platforms;android-22 platforms;android-23 platforms;android-24 platforms;android-25 platforms;android-26 platforms;android-27 platforms;android-28 platforms;android-29 platforms;android-30 platforms;android-31 platforms;android-32 platforms;android-33 platforms;android-34 platforms;android-35 platforms;android-36"

ENV EMU_PARTITION=8192
ENV EMU_MEMORY=4096
ENV EMU_CORES=2
ENV EMU_GPU_MODE="swiftshader_indirect"

ENV EMULATOR_NAME="RVSec"
ENV ANDROID_HOME=/opt/android
ENV ANDROID_SDK_ROOT=/opt/android
ENV ANDROID_SDK_HOME=/opt/android
ENV PATH=$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/tools/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/build-tools/35.0.1:$PATH
ENV LD_LIBRARY_PATH="$ANDROID_SDK_ROOT/emulator/lib64:$ANDROID_SDK_ROOT/emulator/lib64/qt/lib"

ENV API_LEVEL=$API_LEVEL \
	DEVICE_ID=$DEVICE_ID \
	ARCHITECTURE=$ARCHITECTURE \
	ABI=${IMG_TYPE}/${ARCHITECTURE} \
	GPU_ACCELERATED=$GPU_ACCELERATED \
	QTWEBENGINE_DISABLE_SANDBOX=1 \
	ANDROID_EMULATOR_WAIT_TIME_BEFORE_KILL=10 \
	ANDROID_AVD_HOME=/data

WORKDIR /opt

# Create fake keymap file
RUN mkdir -v -p $ANDROID_SDK_ROOT/tools/keymaps && \
	touch $ANDROID_SDK_ROOT/tools/keymaps/en-us

# Symlink sdkmanager to legacy path expected by GATOR wrapper
# (GATOR uses $ANDROID_HOME/tools/bin/sdkmanager, image has cmdline-tools/tools/bin/)
RUN mkdir -p $ANDROID_HOME/tools/bin && \
	ln -s $ANDROID_HOME/cmdline-tools/tools/bin/sdkmanager $ANDROID_HOME/tools/bin/sdkmanager


# Initializing the required directories.
RUN mkdir $HOME/.android/ &&  \
	touch $HOME/.android/repositories.cfg && \
	mkdir /data


# https://developer.android.com/studio#command-tools
RUN apt update && apt -qq -y --no-install-recommends install bzip2 libdrm-dev \
	libxkbcommon-dev libgbm-dev libasound-dev libnss3 \
	libxcursor1 libpulse-dev libxshmfence-dev \
	xauth xvfb x11vnc fluxbox wmctrl libdbus-glib-1-2 socat \
	virt-manager && \
	wget -v https://dl.google.com/android/repository/commandlinetools-linux-${CMD_LINE_VERSION}.zip && \
	mkdir $ANDROID_SDK_ROOT/cmdline-tools/ && \
	unzip *tools*linux*.zip -d $ANDROID_HOME/cmdline-tools && \
	mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/tools && \
	rm *tools*linux*.zip && \
	yes Y | sdkmanager --licenses && \
	sdkmanager --install ${ANDROID_SDK_PACKAGES} && \
	echo "no" | avdmanager --verbose create avd --force --name "$EMULATOR_NAME" --abi "$ABI" --package "$PACKAGE_PATH" --device "$DEVICE_ID"


#COPY license_accepter.sh /opt/android/license_accepter.sh
# Exporting ADB keys.
#COPY keys/* /root/.android/
#
# The following layers will download the Android command-line tools
# to install the Android SDK, emulator and system images.
# It will then install the Android SDK and emulator.
#COPY scripts/install-sdk.sh /opt/
#RUN chmod +x /opt/install-sdk.sh
#
## Copy the container scripts in the image.
#COPY scripts/start-emulator.sh /opt/
#COPY scripts/emulator-monitoring.sh /opt/
#RUN chmod +x /opt/*.sh