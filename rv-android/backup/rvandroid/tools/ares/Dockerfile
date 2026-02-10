FROM jtpastro/docker-adb
#FROM phtcosta/ares:0.0.2

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/ares

ENV TIMEOUT_IN_MINUTES=1
ENV EMUNAME="emulator-5554"

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

COPY run_inside.sh /ares/run_inside.sh

VOLUME /ares/apks

#ENTRYPOINT ["venv/bin/python3", "rl_interaction/parallel_exec.py", "--list_devices", ".", "--appium_ports", "4270", "--android_ports", "0", "--timer", "$TIMEOUT_IN_MINUTES", "--rotation", "--algo", "SAC", "--iterations", "1", "--path", "apks", "--timesteps", "999999", "--trials_per_app", "1", "--real_device", "--udid", "${EMUNAME}", "--pool_strings=rl_interaction/strings.txt"]
#ENTRYPOINT ["venv/bin/python3", "rl_interaction/parallel_exec.py", "--list_devices . --appium_ports 4270 --android_ports 0 --timer ${TIMEOUT_IN_MINUTES} --rotation --algo SAC --iterations 1 --path \"/ares/apks\" --timesteps 999999 --trials_per_app 1 --real_device --udid \"${EMUNAME}\" --pool_strings=rl_interaction/strings.txt"]

CMD [ "/ares/run_inside.sh" ]
#CMD ["echo", "$EMUNAME:$TIMEOUT_IN_MINUTES"]