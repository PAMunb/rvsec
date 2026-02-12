FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

# Copy local Poetry workspace files
WORKDIR /opt/rvsec/rv-android
COPY pyproject.toml poetry.lock ./

# Copy module sources
COPY modules/ ./modules/

# Install all modules in editable mode
RUN poetry install --no-root --sync --without dev

# Copy entry point script
COPY docker/rvandroid/docker-entrypoint.sh /opt/docker-entrypoint.sh
RUN chmod +x /opt/docker-entrypoint.sh

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

ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["run"]
