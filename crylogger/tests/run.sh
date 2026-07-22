#!/bin/bash

rm -v /tmp/application.cryptolog
mvn
mv -v /tmp/application.cryptolog /tmp/application.cryptolog2
mvn
