FROM python:3.12.12-slim-trixie

# Environment configurations as per your provided Dockerfile
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
SHELL ["/bin/bash", "-c"]

# Environment variables for installation paths as per your provided Dockerfile
ENV JAVA_HOME=/opt/openjdk-25.0.2
ENV MAVEN_HOME=/opt/apache-maven-3.9.16
ENV ASPECTJ_HOME=/opt/aspectj
ENV PATH=$ASPECTJ_HOME/bin:$JAVA_HOME/bin:$MAVEN_HOME/bin:$PATH

# Install basic packages and dependencies
RUN apt update && \
    apt upgrade -y && \
    apt install -qq -y --no-install-recommends curl wget zip unzip git nano gpg lsb-release && \
    pip install --no-cache-dir --upgrade pip wheel 'setuptools<81.0.0'

WORKDIR /opt

# Install Java 25 exactly as in your provided Dockerfile
RUN wget https://download.java.net/java/GA/jdk25.0.2/b1e0dfa218384cb9959bdcb897162d4e/10/GPL/openjdk-25.0.2_linux-x64_bin.tar.gz && \
    tar -xzf openjdk-25.0.2_linux-x64_bin.tar.gz && \
    mv jdk-25.0.2 openjdk-25.0.2 && \
    rm openjdk-25.0.2_linux-x64_bin.tar.gz

# Install Maven 3.9.16. Source URL is dlcdn.apache.org because archive.apache.org
# is unreachable from Docker containers in this environment (host can reach it,
# but the Docker network namespace consistently times out on the route — observed
# during the gh55 build_all run). dlcdn.apache.org carries only the current
# 3.9.x; bump 3.9.x as upstream evolves (3.9.15 was purged 2026-06, → 3.9.16).
RUN wget https://dlcdn.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.zip && \
    unzip apache-maven-3.9.16-bin.zip && \
    rm apache-maven-3.9.16-bin.zip

# Install AspectJ compiler — version must match aspectj.version in rvsec/pom.xml (1.9.25.1)
# JVM tuning bakes -Xmx8192M (default is 64M, far too small for whole-APK weaving)
# and -Xss8m (default 512K overflows on Kotlin deep generic parameterizations;
# 7 JCA-557 APKs failed with StackOverflowError during UnresolvedType recursion
# on Flow/Channel/Continuation hierarchies). See gh50 tasks.md §20.
RUN mkdir $ASPECTJ_HOME && \
    wget 'https://github.com/eclipse-aspectj/aspectj/releases/download/V1_9_25_1/aspectj-1.9.25.1.jar' -O aspectj-1.9.25.1.jar && \
    java -jar aspectj-1.9.25.1.jar -to $ASPECTJ_HOME && \
    sed -i 's/-Xmx64M/-Xmx8192M -Xss8m/g' $ASPECTJ_HOME/bin/ajc && \
    chmod a+x $ASPECTJ_HOME/bin/ajc && \
    rm aspectj-1.9.25.1.jar

# Install uv as a core build tool
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

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