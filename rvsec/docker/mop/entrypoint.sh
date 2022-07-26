#!/bin/bash

echo "EXECUTANDO ......"

cd /projects/MoniTests

mvn -B clean install -DskipTests

echo "Copying output"
cp -v JavaMOPAgent.jar /projects/output

