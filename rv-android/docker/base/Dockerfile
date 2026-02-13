FROM python:3.12.12-slim-trixie

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
    pip install --no-cache-dir --upgrade pip wheel 'setuptools<81.0.0'

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

# Install AspectJ compiler — version must match aspectj.version in rvsec/pom.xml (1.9.24)
RUN mkdir $ASPECTJ_HOME && \
    wget 'https://github.com/eclipse-aspectj/aspectj/releases/download/V1_9_24/aspectj-1.9.24.jar' -O aspectj-1.9.24.jar && \
    java -jar aspectj-1.9.24.jar -to $ASPECTJ_HOME && \
    sed -i 's/-Xmx64M/-Xmx4096M/g' $ASPECTJ_HOME/bin/ajc && \
    chmod a+x $ASPECTJ_HOME/bin/ajc && \
    rm aspectj-1.9.24.jar

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