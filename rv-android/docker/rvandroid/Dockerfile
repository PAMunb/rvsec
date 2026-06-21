FROM phtcosta/rvandroid_tools:0.9.1

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

# Build APE-RV from source so the shipped ape-rv.jar always matches current
# ape (and the current static-analysis JSON schema, gh60 `reachesTarget`). The
# committed binary was a drift source: a stale jar read the legacy `reachesMop`
# key, so MOP boost fired in 0/147,153 evaluations (gh71). The base image
# already provides d8, Maven, Git, and a JDK, so a single stage suffices. The
# ape ref is the repository default branch (always current); no ARG/SHA pin by
# design (gh71 D3). The copy target exists because the rvsec clone above brings
# rv-android/modules/aperv-tool/... into the image.
RUN git clone https://github.com/phtcosta/ape.git /tmp/ape && \
    mvn -f /tmp/ape/pom.xml package -DskipTests && \
    cp /tmp/ape/target/ape-rv.jar \
       /opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar && \
    test -s /opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar && \
    rm -rf /tmp/ape

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

# Default environment variables (gh55: RV_JCA_SPEC removed; use RV_SPEC_SET).
ENV RV_TOOLS=monkey
ENV RV_TIMEOUTS=300
ENV RV_REPETITIONS=1
ENV RV_NO_WINDOW=true
ENV RV_SPEC_SET=jca

# Volumes for APKs, artifacts, and results
VOLUME /opt/rvsec/rv-android/apks
VOLUME /opt/rvsec/rv-android/out
VOLUME /opt/rvsec/rv-android/results

# Entry point performs allow-list validation against the canonical ENV_*
# registry, then execs `rv-experiment run` (gh55: env→flag translation
# removed). The entrypoint sources scripts/validate_env_vars.sh, so both
# files must be staged at /opt/ with the same relative layout.
COPY docker-entrypoint.sh /opt/docker-entrypoint.sh
COPY scripts/validate_env_vars.sh /opt/scripts/validate_env_vars.sh
RUN chmod +x /opt/docker-entrypoint.sh /opt/scripts/validate_env_vars.sh

WORKDIR /opt/rvsec/rv-android

ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["run"]
