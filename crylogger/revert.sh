#!/bin/bash

JRE_LIB_DIR=$HOME/.sdkman/candidates/java/8.0.302-open/jre/lib
RT_JAR_ORIGINAL=$JRE_LIB_DIR/rt-backup.jar
JCE_JAR_ORIGINAL=$JRE_LIB_DIR/jce-backup.jar

cp -vf $RT_JAR_ORIGINAL $JRE_LIB_DIR/rt.jar
cp -vf $JCE_JAR_ORIGINAL $JRE_LIB_DIR/jce.jar
