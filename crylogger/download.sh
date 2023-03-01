#!/bin/bash
###########################################################################
# Script para realizar o download do projeto

git clone https://github.com/lucapiccolboni/crylogger.git
cd crylogger
git checkout v1.0
rm -Rf .git
