#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Building RV-Android Docker images (6 total) ==="

echo "--- Step 1/6: Base image ---"
"$SCRIPT_DIR/base/build.sh"

echo "--- Step 2/6: Android image ---"
"$SCRIPT_DIR/android/build.sh"

echo "--- Step 3/6: Tools image ---"
"$SCRIPT_DIR/tools/build.sh"

echo "--- Step 4/6: RV-Android image ---"
"$SCRIPT_DIR/rvandroid/build.sh"

echo "--- Step 5/6: ARES image ---"
ARES_DIR="$REPO_ROOT/modules/rv-tools/src/rv_tools/builtin/ares"
docker build --no-cache -t phtcosta/ares:latest "$ARES_DIR"
echo "ARES image built: phtcosta/ares:latest"

echo "--- Step 6/6: QTesting image ---"
QTESTING_DIR="$REPO_ROOT/modules/rv-tools/src/rv_tools/builtin/qtesting"
docker build --no-cache -t phtcosta/qtesting:latest "$QTESTING_DIR"
echo "QTesting image built: phtcosta/qtesting:latest"

echo "=== All 6 images built successfully ==="
