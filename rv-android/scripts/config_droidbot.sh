#!/bin/sh


# PRE-REQUISITE
# Manual step (/etc/profile or ~/.bashrc):
# - update PATH
# Example:
# export PATH=/home/pedro/.local/bin:$PATH

BASE_DIR=/home/pedro/tmp

cd $BASE_DIR
git clone https://github.com/honeynet/droidbot.git
cd droidbot/
pip install -e .

droidbot -h

echo "[+] Droidbot configured!"

