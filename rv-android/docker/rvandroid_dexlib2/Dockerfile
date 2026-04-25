# gh52: rvandroid image variant for the dexlib2 instrumentation backend.
#
# Layered on top of the canonical rvandroid:0.8.0 image. The base already
# runs `mvn clean install -DskipTests` over the rvsec tree, which builds
# the rvsec-instrumentation-dexlib2 aggregator and auto-copies the fat
# CLI jar to rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar
# (design D9). All this layer adds is the variant env-var so rv-experiment
# selects the dexlib2 PreProcessor branch.
#
# Build:
#   docker build -f docker/rvandroid_dexlib2/Dockerfile \
#                -t phtcosta/rvandroid:0.8.0-dexlib2 .
#
# Run (paired with the ajc variant for Layer-4 validation):
#   docker compose -f docker/docker-compose.dexlib2-validation.template.yml up -d

FROM phtcosta/rvandroid:0.8.0

LABEL gh.issue="52"
LABEL gh.change="gh52-instr-dexlib2"
LABEL variant="dexlib2"
LABEL description="rvandroid + DEX-native dexlib2 instrumentation pipeline"

# rv-experiment dispatches on this env var (rv-experiment.config.ExperimentConfig
# .instrumentation_variant). The base image defaults to "ajc"; this layer flips it.
ENV RV_INSTRUMENTATION_VARIANT="dexlib2"

# Auto-copied jar from the base image's mvn install step. The compose
# template also bind-mounts the host workspace's jar over /opt/instr-cli.jar
# so dev iterations don't require a base-image rebuild — but pinning a
# default here means standalone `docker run` of this image still works.
ENV RVSEC_INSTR_DEXLIB2_JAR="/opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar"

# Sanity check at build time: fail the layer if the auto-copied jar is
# missing (would indicate the base image was built before D9 landed).
RUN test -f "$RVSEC_INSTR_DEXLIB2_JAR" \
    || (echo "ERROR: $RVSEC_INSTR_DEXLIB2_JAR missing; rebuild base image with gh52 merged" >&2 && exit 1)

# Inherits ENTRYPOINT, CMD, VOLUMEs, WORKDIR from the base.
