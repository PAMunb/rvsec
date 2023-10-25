#!/bin/sh

#--no_window --skip_monitors --skip_instrument
#python main.py -tools monkey droidbot droidbot_dfs_greedy -r 1 -t 90 120 150
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot -r 1 -t 120 150
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy -r 1 -t 90
python main.py --skip_monitors --skip_instrument -tools monkey droidbot -r 1 -t 90

echo "[+] Done!"
