#!/bin/bash

#--no_window --skip_monitors --skip_instrument --skip_static_analysis --skip_experiment --debug
#python main.py -tools monkey droidbot droidbot_dfs_greedy -r 1 -t 90 120 150
#python main.py --skip_monitors --skip_instrument -tools monkey droidbot -r 1 -t 120 150
#python main.py -h

#python main.py --no_window -tools monkey droidbot droidbot_dfs_greedy droidbot_bfs_naive droidbot_bfs_greedy humanoid droidmate ape -r 3 -t 60 90 120 180 300

# 60 (1min) * 60 = (1hr) * 3 = 10800
#python main.py --no_window -tools ape ares droidbot droidbot_bfs_greedy droidbot_bfs_naive droidbot_dfs_greedy droidmate fastbot humanoid monkey qtesting  -r 1 -t 10800
#python main.py --no_window --debug -tools ares qtesting droidmate -r 1 -t 600
#python main.py --debug --no_window -tools droidmate ape -r 2 -t 180 300 600

#python main.py --skip_monitors --skip_instrument --skip_static_analysis --no_window -tools ape ares droidbot droidbot_bfs_greedy droidbot_bfs_naive droidbot_dfs_greedy droidmate fastbot monkey -r 1 -t 120
#python main.py --skip_monitors --skip_instrument --skip_static_analysis --no_window -tools qtesting -r 1 -t 60

python main.py --no_window -tools ape monkey -r 1 -t 180

#execution_dir_timestamp="20241118124358"
#execution_memory="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/${execution_dir_timestamp}/execution_memory.json"
#python main.py --no_window -c $execution_memory

echo "[+] Done!"
