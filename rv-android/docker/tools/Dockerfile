FROM phtcosta/rvsec_android:0.8.0

WORKDIR /opt
RUN git clone https://github.com/honeynet/droidbot.git && \
    cd droidbot && \
    sed -i 's/androguard>=3.4.0a1/androguard==3.4.0a1/g' setup.py && \
    pip install -e .

ENV PYTHONPATH=/opt/droidbot:${PYTHONPATH:-}
