#!/bin/bash
"""
Script para executar teste incremental com Poetry e capturar saída.
"""

# Create timestamp for unique filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create logs directory
mkdir -p logs

# Define log file paths
LOG_FILE="logs/incremental_validation_${TIMESTAMP}.log"

echo "🚀 Starting Incremental Gemma3-tools Validation"
echo "📝 All output will be saved to: $LOG_FILE"
echo ""
echo "⏳ Running incremental validation..."
echo "   Level 0: 1 app, 1 screenshot, 1 strategy"
echo "   Level 1: 1 app, 2 screenshots, 2 strategies"
echo "   Level 2: 1 app, 3 screenshots, all strategies"
echo "   Level 3: 2 apps, 3 screenshots, key strategies"
echo "   Level 4: 4 apps, 5 screenshots, all strategies"
echo ""
echo "📊 This may take 15-45 minutes depending on model speed..."
echo ""

# Go to project root and run with Poetry
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

{
    echo "==================================================================="
    echo "INCREMENTAL VALIDATION START: $(date)"
    echo "==================================================================="
    echo ""

    # Run incremental test
    poetry run python modules/rv-agent/validation/incremental_test.py

    echo ""
    echo "==================================================================="
    echo "INCREMENTAL VALIDATION END: $(date)"
    echo "==================================================================="

} > "modules/rv-agent/validation/$LOG_FILE" 2>&1

# Capture exit code
EXIT_CODE=$?

cd modules/rv-agent/validation

echo "✅ Incremental validation completed with exit code: $EXIT_CODE"
echo ""
echo "📊 Log analysis:"
echo "  - Total lines: $(wc -l < $LOG_FILE)"
echo "  - Hit rate results: $(grep -c 'Hit Rate:' $LOG_FILE)"
echo "  - Strategy tests: $(grep -c 'Testing strategy:' $LOG_FILE)"
echo "  - Tool calls: $(grep -c 'ANDROID_CLICK\\|ANDROID_INPUT' $LOG_FILE)"
echo ""
echo "📖 Quick analysis commands:"
echo "  # View final summary"
echo "  tail -30 $LOG_FILE"
echo ""
echo "  # See all hit rates"
echo "  grep 'Hit Rate:' $LOG_FILE"
echo ""
echo "  # See LLM reasoning"
echo "  grep -A2 -B2 'Explanation:' $LOG_FILE"
echo ""
echo "  # See coordinate choices"
echo "  grep 'Coordinates:' $LOG_FILE"
echo ""
echo "  # See hit/miss results"
echo "  grep 'HIT\\|MISS' $LOG_FILE | head -20"

exit $EXIT_CODE