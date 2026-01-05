#!/bin/bash
"""
Script para executar validação com Poetry e capturar toda a saída em arquivo.
"""

# Create timestamp for unique filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create logs directory
mkdir -p logs

# Define log file paths
STDOUT_LOG="logs/validation_stdout_${TIMESTAMP}.log"
STDERR_LOG="logs/validation_stderr_${TIMESTAMP}.log"
COMBINED_LOG="logs/validation_combined_${TIMESTAMP}.log"

echo "🚀 Starting Gemma3-tools Coordinate Validation"
echo "📝 Logs will be saved to:"
echo "  - stdout: $STDOUT_LOG"
echo "  - stderr: $STDERR_LOG"
echo "  - combined: $COMBINED_LOG"
echo ""
echo "⏳ Running validation... (this may take several minutes)"
echo ""

# Go to project root
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# Run with Poetry, capturing all output
poetry run python modules/rv-agent/validation/quick_test.py \
    > "modules/rv-agent/validation/$STDOUT_LOG" \
    2> "modules/rv-agent/validation/$STDERR_LOG"

# Capture exit code
EXIT_CODE=$?

# Create combined log
cd modules/rv-agent/validation
cat "$STDOUT_LOG" "$STDERR_LOG" > "$COMBINED_LOG"

echo "✅ Validation completed with exit code: $EXIT_CODE"
echo ""
echo "📊 Log files created:"
echo "  - $(wc -l < $STDOUT_LOG) lines in stdout"
echo "  - $(wc -l < $STDERR_LOG) lines in stderr"
echo "  - $(wc -l < $COMBINED_LOG) lines total"
echo ""
echo "📖 To view results:"
echo "  tail -f $COMBINED_LOG"
echo "  grep 'HIT\\|MISS\\|Hit Rate' $COMBINED_LOG"
echo "  grep 'REASONING\\|Explanation' $COMBINED_LOG"

exit $EXIT_CODE