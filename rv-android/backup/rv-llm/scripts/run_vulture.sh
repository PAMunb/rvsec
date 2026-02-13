#!/bin/bash

# This script executes Vulture with default parameters.
# It uses 'poetry run' to ensure Vulture is executed from Poetry's virtual environment.

poetry run vulture . \
    --exclude "*.pyc,.git,__pycache__,*/tests/*" \
    --min-confidence 60 \
    --ignore-names "setup" \
    # Add more options here if needed

# Optional: Check Vulture's exit code
if [ $? -ne 0 ]; then
    echo "Vulture found dead code. Please review the warnings."
    exit 1
else
    echo "Vulture found no dead code. Good job!"
fi