RV-Android 
-------------------

### Pre-requisites

- Android environment (see an example in scripts/config_android.sh)
- Java 11
- droidbot (https://github.com/honeynet/droidbot)


### Basic usage

Edit the APK in run.sh and execute the script


### Experiment

experiment_01.py

TODO: setar o ambiente


### Tools

#### Droidbot

    git clone https://github.com/honeynet/droidbot.git
    cd droidbot/
    git checkout ac183c03b62e965f3a5e8dc615d2e0d736f12113
    pip install -e .

#### Droidmate

>> NAO ESTA COMPILANDO ... pegando o do droidxp por enquanto

    git clone https://github.com/uds-se/droidmate.git
    cd droidmate
    git checkout 2.1.2
    ./gradlew shadowJar
    cp repo/build/libs/droidmate*-all.jar $RV_ANDROID_HOME/lib/droidmate




