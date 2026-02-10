FROM python:3.10-slim

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

ENV ANDROID_HOME=/android
ENV ANDROID_SDK_ROOT=/android
ENV ANDROID_SDK_PACKAGES="platform-tools build-tools;34.0.0"
ENV ANDROID_SDK_VERSION=8512546
ENV PATH=$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/tools/bin:$ANDROID_HOME/build-tools/34.0.0:$PATH

RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends openjdk-17-jre curl unzip wget zip && \
    mkdir -p ${ANDROID_HOME}/cmdline-tools


# command line tools
# https://developer.android.com/studio#command-tools
RUN wget -v https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip && \
	unzip *tools*linux*.zip -d ${ANDROID_HOME}/cmdline-tools && \
	mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/tools && \
	rm *tools*linux*.zip && \
    mkdir ${HOME}/.android/ && touch ${HOME}/.android/repositories.cfg && \
    yes Y | sdkmanager --licenses && \
    yes Y | sdkmanager --verbose --no_https ${ANDROID_SDK_PACKAGES}

WORKDIR /qtesting

COPY src /qtesting/src
COPY src/conf.txt /qtesting/conf/conf.txt

RUN mkdir /qtesting/apks && \
    pip install --upgrade pip && \
    pip install -r /qtesting/src/requirements.txt && \
    apt-get -y autoremove --purge

VOLUME /qtesting/apks

ENTRYPOINT ["python", "src/main.py", "-r", "apks/conf.txt"]
