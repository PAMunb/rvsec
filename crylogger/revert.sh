#!/bin/bash

RT_JAR_DIR=$HOME/.sdkman/candidates/java/8.0.302-open/jre/lib
RT_JAR_ORIGINAL=$RT_JAR_DIR/rt-backup.jar

cp -vf $RT_JAR_ORIGINAL $RT_JAR_DIR/rt.jar
