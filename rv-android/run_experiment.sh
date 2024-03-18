#!/bin/sh

#--no_window --skip_monitors --skip_instrument --skip_experiment
#python main.py -tools monkey droidbot droidbot_dfs_greedy -r 1 -t 90 120 150
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot -r 1 -t 120 150
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy -r 1 -t 90
#python main.py --skip_monitors --skip_instrument --no_window -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy humanoid droidmate -r 1 -t 180
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy humanoid droidmate -r 1 -t 180

#python main.py --skip_experiment --skip_instrument -tools monkey -r 1 -t 10
#python3 main.py --no_window --debug -tools monkey -r 1 -t 60

python main.py --no_window -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy humanoid droidmate ape -r 3 -t 60 120 180 300

echo "[+] Done!"
