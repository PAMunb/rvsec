#!/bin/sh

if [[ -z "$ASPECTJ_HOME" ]]; then
    echo "[Error] No ASPECTJ_HOME environment variable found"
    exit 1
fi

if [[ -z "$M2_REPO" ]]; then
    M2_REPO=${HOME}/.m2/repository
fi

RV_MONITOR_REPO=${M2_REPO}/br/unb/cic/rvmonitor
RV_MONITOR_VERSION=0.1.0-SNAPSHOT

CLASSPATH=${RV_MONITOR_REPO}/rv-monitor/${RV_MONITOR_VERSION}/rv-monitor-${RV_MONITOR_VERSION}.jar:${RV_MONITOR_REPO}/rv-monitor-rt/${RV_MONITOR_VERSION}/rv-monitor-rt-${RV_MONITOR_VERSION}.jar:${ASPECTJ_HOME}/lib/aspectjrt.jar:${ASPECTJ_HOME}/lib/aspectjweaver.jar:${ASPECTJ_HOME}/lib/aspectjtools.jar    

export CLASSPATH

echo "CLASSPATH environment variable set."

