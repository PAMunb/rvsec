FROM phtcosta/rvsec_android:0.9.2

WORKDIR /opt
RUN git clone https://github.com/honeynet/droidbot.git && \
    cd droidbot && \
    sed -i 's|from androguard.core.bytecodes.apk import APK|from androguard.core.apk import APK|' droidbot/app.py && \
    pip install -e . && \
    pip install --upgrade 'androguard>=4.1.3'

ENV PYTHONPATH=/opt/droidbot:${PYTHONPATH:-}
