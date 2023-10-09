#!/bin/sh

#python main.py -tools monkey -r 1 -t 60 90
python main_novo.py --skip_monitors --skip_instrument -tools monkey droidbot -r 3 -t 60 90 120

echo "[+] Done!"
