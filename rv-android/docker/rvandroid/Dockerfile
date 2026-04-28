FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

# Branch checked out by the rvsec clone below. Defaults to the canonical
# `modules` branch (ajc pipeline). Override at build time to produce a
# variant image, e.g.:
#   docker build --build-arg RVSEC_BRANCH=gh52-instr-dexlib2 \
#                -t phtcosta/rvandroid:0.8.0-dexlib2-base .
ARG RVSEC_BRANCH=modules

WORKDIR /opt/rvsec
RUN git clone --branch ${RVSEC_BRANCH} https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && \
    uv sync --no-dev

# Persist the branch tag in the image for traceability (image history
# + `docker inspect` reveals what code shipped).
LABEL rvsec.branch="${RVSEC_BRANCH}"

# Default environment variables
ENV RV_TOOLS=monkey
ENV RV_TIMEOUTS=300
ENV RV_REPETITIONS=1
ENV RV_NO_WINDOW=true
ENV RV_JCA_SPEC=true

# Volumes for APKs, artifacts, and results
VOLUME /opt/rvsec/rv-android/apks
VOLUME /opt/rvsec/rv-android/out
VOLUME /opt/rvsec/rv-android/results

# Entry point script translates env vars to CLI arguments
COPY docker-entrypoint.sh /opt/docker-entrypoint.sh
RUN chmod +x /opt/docker-entrypoint.sh

WORKDIR /opt/rvsec/rv-android

ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["run"]
