#!/bin/sh

SOURCE_DIR="src/main/java/mop"
MOP_DIR="../rvsec-mop/src/main/resources"
 
echo "[+] Cleaning ..."

mvn clean
rm -Rf output
rm JavaMOPAgent.jar
rm $SOURCE_DIR/MultiSpec_*
rm $MOP_DIR/*.rvm
rm $MOP_DIR/MultiSpec_*
