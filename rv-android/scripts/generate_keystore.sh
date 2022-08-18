#!/bin/sh

echo "Generating keystore"

keytool -genkey -v -alias server -keyalg RSA -keypass password -storepass password -validity 3650 -dname "CN=RVSec, OU=cic, O=unb, L=bsb, ST=df, C=br" -keystore ../keystore.jks 

#keytool -export -alias server -storepass password -file ../server.cer -keystore ../keystore.jks
