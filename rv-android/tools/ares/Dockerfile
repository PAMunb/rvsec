FROM jtpastro/docker-adb

ENV DEBIAN_FRONTEND noninteractive
ENV TZ=America/Sao_Paulo
ENV PYTHONPATH /ares

WORKDIR /ares
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-distutils python3-pip python3.10-venv npm git psmisc && \
    apt-get clean
RUN npm install -g appium@1.22.3
RUN git clone https://github.com/H2SO4T/ARES .
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install -v --timeout=5000 -r rl_interaction/requirements.txt
RUN apt-get remove -y  python3-pip python3.10-venv git && \
    apt-get -y autoremove --purge