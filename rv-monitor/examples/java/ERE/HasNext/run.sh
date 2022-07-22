#!/bin/bash
###########################################################################
# Script to run the example
# colocar dentro de example/java/ERE/HasNext


if [[ -z "$ASPECTJ_HOME" ]]; then
    echo "[Error] No ASPECTJ_HOME environment variable found"
    exit 1
fi

RV_VERSION=statistics-1.4
RV_M2_REPO=${HOME}/.m2/repository/com/runtimeverification/rvmonitor

CLASSPATH=${RV_M2_REPO}/rv-monitor/${RV_VERSION}/rv-monitor-${RV_VERSION}.jar:${RV_M2_REPO}/rv-monitor-rt/${RV_VERSION}/rv-monitor-rt-${RV_VERSION}.jar:${ASPECTJ_HOME}/lib/aspectjrt.jar:${ASPECTJ_HOME}/lib/aspectjweaver.jar:${ASPECTJ_HOME}/lib/aspectjtools.jar    

export CLASSPATH

echo "CLASSPATH environment variable set."

../../../../bin/rv-monitor rvm/HasNext.rvm

javac -cp $CLASSPATH:. rvm/HasNextRuntimeMonitor.java HasNext_1/HasNext_1.java

java  -cp $CLASSPATH:. HasNext_1.HasNext_1