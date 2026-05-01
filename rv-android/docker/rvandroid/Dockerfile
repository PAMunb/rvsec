FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

# Branch checked out by the rvsec clone below. Defaults to the canonical
# `modules` branch which now ships both instrumentation variants (ajc + dexlib2)
# as separate workspace modules. Variant selection happens at runtime via
# RV_INSTRUMENTATION_VARIANT (or --instrumentation-variant). Override
# RVSEC_BRANCH only when building from a non-canonical branch for debugging.
ARG RVSEC_BRANCH=modules

WORKDIR /opt/rvsec
RUN git clone --branch ${RVSEC_BRANCH} https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && \
    uv sync --no-dev

# Build-time gate: the dexlib2 fat CLI jar must be present for variant
# selection to work at runtime. Maven's copy-resources step (design D9 in
# rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/pom.xml) auto-copies
# it to the workspace module's lib/ directory; if absent, fail the build
# loudly so we never ship an image where RV_INSTRUMENTATION_VARIANT=dexlib2
# crashes at runtime.
RUN test -f /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
    || (echo "ERROR: instr-cli.jar missing — Maven D9 auto-copy did not run; check rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/pom.xml" && exit 1)

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
