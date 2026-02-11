FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

WORKDIR /opt/rvsec
RUN git clone --branch modules https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && \
    poetry install --no-root --sync --without dev