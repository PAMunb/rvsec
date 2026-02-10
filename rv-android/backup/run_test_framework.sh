#!/bin/bash
# RV-Android Test Framework execution script
# This script simplifies the execution of the test framework with common parameters
# 
# Usage:
#   ./run_test_framework.sh run --apks-dir ./out [--config ./tf_configs/my_config.json]
#   ./run_test_framework.sh create-config [--output my_config.json]
#   ./run_test_framework.sh analyze --results-dir ./test_results/run_yyyymmdd_hhmmss
# python custom_analyzer.py test_results/run_20250407_132108 analise_002

# If no arguments are provided, use default configuration
if [ $# -eq 0 ]; then
    echo "Using default configuration..."
    python run_test_framework.py run --config tf_configs/basic_config.json --apks-dir ./out
else
    # Otherwise, pass all arguments to the Python script
    python run_test_framework.py "$@"
fi

echo "[+] Done!"
