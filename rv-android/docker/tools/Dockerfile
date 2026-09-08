FROM phtcosta/rvsec_android:0.9.3

WORKDIR /opt
# O droidbot serve CINCO dos onze bracos da comparacao: as quatro politicas `droidbot:*` e o
# `humanoid` (que e' droidbot com `-humanoid`). O clone era do branch default, sem SHA: a
# camada `tools` ficou em cache desde 13/08 carregando `52aeea4` (2023-11-16), e o primeiro
# rebuild sem cache — 08/09 — pulou para `cc4cc93` (2026-08-29) sem que nada no repositorio
# mudasse. Um build verde teria trocado a versao de cinco bracos no meio de uma campanha cuja
# premissa e' que um unico fator muda (o conjunto de specs), e nenhum portao pegaria isso.
#
# `52aeea4` e' o commit que todas as imagens anteriores carregam, inclusive a
# `0.9.3-jca-android` que teceu o corpus. Mover este pin e' mudar o objeto medido.
ARG DROIDBOT_COMMIT=52aeea4
RUN git clone https://github.com/honeynet/droidbot.git && \
    cd droidbot && \
    git checkout "$DROIDBOT_COMMIT" && \
    sed -i 's|from androguard.core.bytecodes.apk import APK|from androguard.core.apk import APK|' droidbot/app.py && \
    pip install -e . && \
    pip install --upgrade 'androguard>=4.1.3'

ENV PYTHONPATH=/opt/droidbot:${PYTHONPATH:-}
