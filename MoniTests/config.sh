#!/bin/sh

if [[ -z "$ASPECTJ_HOME" ]]; then
    echo "[Error] No ASPECTJ_HOME environment variable found"
    exit 1
fi

CLASSPATH=${HOME}/.m2/repository/com/runtimeverification/rvmonitor/rv-monitor/1.4-SNAPSHOT/rv-monitor-1.4-SNAPSHOT.jar:${HOME}/.m2/repository/com/runtimeverification/rvmonitor/rv-monitor-rt/1.4-SNAPSHOT/rv-monitor-rt-1.4-SNAPSHOT.jar:${ASPECTJ_HOME}/lib/aspectjrt.jar:${ASPECTJ_HOME}/lib/aspectjweaver.jar:${ASPECTJ_HOME}/lib/aspectjtools.jar    

export CLASSPATH

echo "CLASSPATH environment variable set."

