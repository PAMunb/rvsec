#!/bin/sh

echo "[+] Starting humanoid"

#nohup docker run -i -t --rm -p 50405:50405 phtcosta/humanoid:1.0 &
docker run -i -t --rm -p 50405:50405 phtcosta/humanoid:1.0
