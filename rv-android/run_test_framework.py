#!/usr/bin/env python3
"""
Runner script for the RV-Android test framework.

This script provides a convenient way to use the test framework from the command line.
It supports specifying directories containing APK files and their related static analysis files,
executing tests with various tool configurations, and analyzing results.

Examples:
    # Run tests with APKs from a specific directory
    python run_test_framework.py run --apks-dir ./out

    # Run tests with a specific configuration file
    python run_test_framework.py run --apks-dir ./out --config ./tf_configs/basic_config.json

    # Run tests and analyze batch strategies
    python run_test_framework.py run --apks-dir ./out --config ./tf_configs/basic_config.json --analyze-batch

    # Create a test configuration
    python run_test_framework.py create-config --output my_config.json

    # Analyze previous test results
    python run_test_framework.py analyze --results-dir ./test_results/run_20250407_114438
    
    # Analyze batch strategies in previous results
    python run_test_framework.py analyze --results-dir ./test_results/run_20250407_114438 --batch-analysis
"""

import sys
from rvandroid.test_framework.cli import main

if __name__ == "__main__":
    main()
