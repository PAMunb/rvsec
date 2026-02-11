FROM phtcosta/rvsec_android:0.8.0


WORKDIR /opt
RUN git clone https://github.com/honeynet/droidbot.git && \
    cd droidbot && \
    sed -i 's/androguard>=3.4.0a1/androguard==3.4.0a1/g' setup.py && \
    pip install -e .

ENV PYTHONPATH=/opt/droidbot:$PYTHONPATH


# RUN cd /opt/droidbot && pip install -e . && pip install telnetlib3

#apt-get install -y python2 && \
#curl  https://bootstrap.pypa.io/pip/2.7/get-pip.py | python2 && \
#pip2 install virtualenv
#python2 -m virtualenv venv2

# ENV SAPIENZ_HOME=/opt/sapienz/
# WORKDIR /opt
# RUN apt-get update && \
#     apt install -qq -y --no-install-recommends python2 libfreetype6-dev libxml2-dev libxslt1-dev python-dev python-tk libmotif-dev && \
#     curl  https://bootstrap.pypa.io/pip/2.7/get-pip.py | python2 && \
#     git clone https://github.com/droidxp/sapienz.git && \
#     cd sapienz && \
#     pip2 install -r requirements.txt && \
#     mkdir /opt/rvsec/rv-android/tools/sapienz
# COPY sapienz/copyreg.py /usr/local/lib/python2.7/dist-packages/deap/copyreg.py
# COPY sapienz/settings.py /opt/sapienz/settings.py
# COPY sapienz/__init__.py /opt/rvsec/rv-android/tools/sapienz
# COPY sapienz/tool.py /opt/rvsec/rv-android/tools/sapienz
# WORKDIR /opt/sapienz

#settings,py
#DEBUG = False
#ANDROID_HOME = '{0}/Android/Sdk/'.format(os.environ['HOME']) + os.sep
#WORKING_DIR = os.environ['SAPIENZ_HOME']
#AVD_SERIES = "api19_"
#EVAL_TIMEOUT = 120


#RUN cd /tmp && \
#    git clone https://github.com/yzygitzh/Humanoid.git && \
#    rm -Rf Humanoid/.git && \
#    cp -Rf Humanoid/* /opt/rvsec/rv-android/tools/humanoid && \
#    cd /opt/rvsec/rv-android && \
#    . venv/bin/activate && \
#    pip3 install pyflann
#COPY pyflann/pyflann /opt/rvsec/rv-android/venv/lib/python3.10/site-packages/pyflann


#ENV STOAT_HOME=/opt/Stoat/Stoat
#ENV PYTHONPATH=/opt/uiautomator:$PYTHONPATH
#ENV CLASSPATH=$STOAT_HOME/soot-github/lib/soot-develop.jar:$CLASSPATH
##ENV PATH=$STOAT_HOME/bin:$PATH
#COPY change_python.sh /opt
#WORKDIR /opt
#RUN apt-get update && \
#    apt install -qq -y --no-install-recommends ruby2.7 build-essential patch ruby-dev zlib1g-dev liblzma-dev && \
#	gem install nokogiri && \
#	git clone https://github.com/rbonifacio/Stoat.git && \
#    git clone https://github.com/xiaocong/uiautomator.git && \
#    chmod +x /opt/change_python.sh && \
#    /opt/change_python.sh $STOAT_HOME
#WORKDIR /opt/Stoat/Stoat

#RUN chmod a+x run_experiment.sh

#ENV VIRTUAL_ENV=/opt/rvsec/rv-android/venv
#ENV PYTHONPATH=/opt/rvsec/rv-android:$PYTHONPATH
#ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#RUN mkdir /opt/rvsec/rv-android/apks && \
#    cp /opt/rvsec/rv-android/apks_examples/cryptoapp.apk /opt/rvsec/rv-android/apks/

#ENTRYPOINT ["/bin/bash"]
#ENTRYPOINT ["python", "main.py"]
#CMD ["python", "main.py"]


# ENV RV_REPETITIONS=1
# ENV RV_TIMEOUTS=180
# ENV RV_TOOLS=sapienz
# ENV RV_HUMANOID_URL=humanoid:50405
# ENV RV_SKIP_MONITORS=false
# ENV RV_SKIP_INSTRUMENT=false
# ENV RV_SKIP_STATIC_ANALYSIS=false
# ENV RV_SKIP_EXPERIMENT=false
# ENV RV_NO_WINDOW=true
# ENV RV_JCA_SPEC=true

# #TODO receber o dir das specs tbm?

# VOLUME /opt/rvsec/rv-android/apks
# VOLUME /opt/rvsec/rv-android/out
# VOLUME /opt/rvsec/rv-android/results

# WORKDIR /opt/rvsec/rv-android

# CMD ["python", "main.py"]
