FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

WORKDIR /opt/rvsec
RUN git clone --branch modules https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && \
    poetry install --no-root --sync --without dev

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
