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
# TODO Edit setup.py: 'androguard>=3.4.0a1' to 'androguard==3.4.0a1'
pip install -e .

droidbot -h

echo "[+] Droidbot configured!"

