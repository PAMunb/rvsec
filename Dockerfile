# Stage 1: build_environment - Setup fundamental build and runtime environment
# Base image as per your provided Dockerfile
FROM python:3.14.3-slim-trixie AS build_environment

# Environment configurations as per your provided Dockerfile
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
SHELL ["/bin/bash", "-c"]

# Environment variables for installation paths as per your provided Dockerfile
ENV JAVA_HOME=/opt/openjdk-25.0.2
ENV RV_RT_JAR=/opt/java-se-8u44-ri/jre/lib/rt.jar
ENV MAVEN_HOME=/opt/apache-maven-3.9.12
ENV ASPECTJ_HOME=/opt/aspectj
ENV PATH=$ASPECTJ_HOME/bin:$JAVA_HOME/bin:$MAVEN_HOME/bin:$PATH

# Install basic packages and dependencies
RUN apt update && \
    apt upgrade -y && \
    apt install -qq -y --no-install-recommends curl wget zip unzip git nano gpg lsb-release && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /opt

# Install Java 25 exactly as in your provided Dockerfile
RUN wget https://download.java.net/java/GA/jdk25.0.2/b1e0dfa218384cb9959bdcb897162d4e/10/GPL/openjdk-25.0.2_linux-x64_bin.tar.gz && \
    tar -xzf openjdk-25.0.2_linux-x64_bin.tar.gz && \
    mv jdk-25.0.2 openjdk-25.0.2 && \
    rm openjdk-25.0.2_linux-x64_bin.tar.gz

# Download and install Java (jre) 8 exactly as in your provided Dockerfile
RUN wget https://download.java.net/openjdk/jdk8u44/ri/openjdk-8u44-linux-x64.tar.gz && \
    tar -xzf openjdk-8u44-linux-x64.tar.gz && \
    rm -Rf java-se-8u44-ri/sample java-se-8u44-ri/src.zip java-se-8u44-ri/demo && \
    rm openjdk-8u44-linux-x64.tar.gz

# Install Maven exactly as in your provided Dockerfile
RUN wget https://dlcdn.apache.org/maven/maven-3/3.9.12/binaries/apache-maven-3.9.12-bin.zip && \
    unzip apache-maven-3.9.12-bin.zip && \
    rm apache-maven-3.9.12-bin.zip

# Install AspectJ and configure memory exactly as in your provided Dockerfile
RUN mkdir $ASPECTJ_HOME && \
    wget 'https://www.eclipse.org/downloads/download.php?file=/tools/aspectj/aspectj-1.9.6.jar&r=1' -O aspectj-1.9.6.jar && \
    java -jar aspectj-1.9.6.jar -to $ASPECTJ_HOME && \
    sed -i 's/-Xmx64M/-Xmx4096M/g' $ASPECTJ_HOME/bin/ajc && \
    chmod a+x $ASPECTJ_HOME/bin/ajc && \
    rm aspectj-1.9.6.jar

# Install Poetry as a core build tool
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="${POETRY_HOME}/bin:${PATH}"
RUN curl -sSL https://install.python-poetry.org | python - 

# Install Docker CLI - required for running ARES and QTesting as sibling containers
# Adapting for Debian Trixie which might not be 'stable' yet. Using 'bookworm' in case 'trixie' (lsb_release -cs) fails.
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs 2>/dev/null || echo "trixie") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt update && apt install -y docker-ce-cli

# Final cleanup as per your provided Dockerfile
RUN apt autoremove -y && \
    apt clean all && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/*


# Stage 2: java_builder - Compile all Java modules and prepare rv-android JARs
FROM build_environment AS java_builder

WORKDIR /app

# Copy the entire project source code (which is the rvsec directory in this context)
COPY . /app

# Compile all Maven modules and collect rv-android dependencies
# Paths are now relative to the /app (rvsec root)
RUN mvn -B clean install -DskipTests -DskipMopAgent \
    && mvn -B -f rv-android/pom.xml process-resources


# Stage 3: python_deps - Install Python dependencies for rv-android
FROM build_environment AS python_deps

WORKDIR /app

# Copy only pyproject.toml and poetry.lock files for caching optimization
# Paths are now relative to the /app (rvsec root)
COPY rv-android/pyproject.toml rv-android/poetry.lock ./rv-android/

# Install Python dependencies using poetry.lock (only for rv-android)
# Paths are now relative to the /app (rvsec root)
RUN cd rv-android && poetry install --no-root --no-dev --sync


# Stage 4: android_sdk_setup - Configure Android SDK and AVD
# Uses 'build_environment' as base to inherit Java, Maven, Poetry, etc.
FROM build_environment AS android_sdk_setup

# Arguments that can be overridden at build-time, as per your docker/android/Dockerfile
ARG API_LEVEL=29
ARG IMG_TYPE=google_apis
ARG ARCHITECTURE=x86
ARG CMD_LINE_VERSION=8512546_latest
ARG DEVICE_ID=pixel
ARG GPU_ACCELERATED=false

# Environment variables for Android SDK as per your docker/android/Dockerfile
ENV PACKAGE_PATH="system-images;android-${API_LEVEL};${IMG_TYPE};${ARCHITECTURE}"
ENV ANDROID_PLATFORM_VERSION="platforms;android-$API_LEVEL"
ENV ANDROID_SDK_PACKAGES="${PACKAGE_PATH} ${ANDROID_PLATFORM_VERSION} platform-tools build-tools;35.0.1 platforms;android-19 platforms;android-20 platforms;android-21 platforms;android-22 platforms;android-23 platforms;android-24 platforms;android-25 platforms;android-26 platforms;android-27 platforms;android-28 platforms;android-30 platforms;android-31 platforms;android-32 platforms;android-33 platforms;android-34 platforms;android-35"

ENV EMU_PARTITION=8192
ENV EMU_MEMORY=4096
ENV EMU_CORES=2
ENV EMU_GPU_MODE="swiftshader_indirect"

ENV EMULATOR_NAME="RVSec"
ENV ANDROID_HOME=/opt/android
ENV ANDROID_SDK_ROOT=/opt/android
ENV PATH=$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/tools/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/build-tools/35.0.1:$PATH
ENV LD_LIBRARY_PATH="$ANDROID_SDK_ROOT/emulator/lib64:$ANDROID_SDK_ROOT/emulator/lib64/qt/lib"

# Additional ENV variables for API_LEVEL, DEVICE_ID, etc.
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

# Initializing the required directories.
RUN mkdir $HOME/.android/ &&  \
    touch $HOME/.android/repositories.cfg && \
    mkdir /data

# Install Android SDK components and create AVD, as per your docker/android/Dockerfile
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
    sdkmanager --install "${ANDROID_SDK_PACKAGES}" && \
    echo "no" | avdmanager --verbose create avd --force --name "$EMULATOR_NAME" --abi "$ABI" --package "$PACKAGE_PATH" --device "$DEVICE_ID"


# Stage 5: tools - Install DroidBot
FROM android_sdk_setup AS tools

WORKDIR /opt

RUN git clone https://github.com/honeynet/droidbot.git && \
    cd droidbot && \
    sed -i 's/androguard>=3.4.0a1/androguard==3.4.0a1/g' setup.py && \
    pip install -e .


# Stage 6: final - Assemble the final image
FROM tools AS final

WORKDIR /app

# Set RVSEC_HOME to /app (which is the rvsec root in this container)
ENV RVSEC_HOME="/app"
ENV ANDROID_HOME="/opt/android"

# Copy compiled Java artifacts from java_builder
COPY --from=java_builder /app /app

# Copy Python virtual environment from python_deps
COPY --from=python_deps /app/rv-android/.venv /app/rv-android/.venv

# Ensure Python venv binaries are on PATH
ENV PATH="/app/rv-android/.venv/bin:${PATH}"

# Set default command for the container
# ENTRYPOINT will be 'poetry run rv-experiment', which is the main orchestrator
# CMD provides generic help to allow user to specify tools
ENTRYPOINT ["poetry", "run", "rv-experiment"]
CMD ["--help"]

# Expose ports for ADB and emulator (if running GUI or external connection)
EXPOSE 5554
EXPOSE 5555 

# These ENV variables appear to be intended for runtime configuration,
# not build-time. They are typically set by the user when running the container
# or via a docker-compose file. Keeping them here as per your provided Dockerfile.
ENV RV_REPETITIONS=1
ENV RV_TIMEOUTS=60
ENV RV_TOOLS=monkey
ENV RV_HUMANOID_URL=humanoid:50405
ENV RV_SKIP_MONITORS=false
ENV RV_SKIP_INSTRUMENT=false
ENV RV_SKIP_STATIC_ANALYSIS=false
ENV RV_SKIP_EXPERIMENT=false
ENV RV_NO_WINDOW=true
ENV RV_JCA_SPEC=true
ENV RV_RT_JAR=/opt/java-se-8u44-ri/jre/lib/rt.jar

VOLUME /opt/rv-android/apks
VOLUME /opt/rv-android/out
VOLUME /opt/rv-android/results