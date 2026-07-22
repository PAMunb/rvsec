#!/bin/bash

# Examples:
# ./execution_status.sh results/20241106124331/execution_memory.json
# ./execution_status.sh

memory_file_path="$1"

if [ -z "$memory_file_path" ]; then
  last_dir_name=$(ls -lt results | grep "^d" | head -n 1 | awk '{print $9}')
  exec_dir="$(pwd)/results/${last_dir_name}"
  memory_file_path="${exec_dir}/execution_memory.json"
  echo "No file path provided. Using the last execution found: ${memory_file_path}"
fi

if [[ -z "$memory_file_path" || ! -f "$memory_file_path" ]]; then
  echo "Please provide the path to the execution memory file."
  exit 1
fi

python execution_status.py "$memory_file_path"
