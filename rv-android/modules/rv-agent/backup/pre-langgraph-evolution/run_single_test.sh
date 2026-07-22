#!/bin/bash
"""
Script simples para testar um único screenshot com Poetry.
Melhor para debug inicial.
"""

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="validation/logs/single_test_${TIMESTAMP}.log"

# Create logs directory in validation folder
mkdir -p validation/logs

echo "🧪 Quick Single Test - Gemma3-tools Validation (RV-Agent Module)"
echo "📝 Output will be saved to: $LOG_FILE"
echo ""
echo "Testing with:"
echo "  - Model: PetrosStav/gemma3-tools:4b"
echo "  - App: cryptoapp.apk"
echo "  - Screenshots: 1 (first available)"
echo "  - Strategy: baseline"
echo "  - Module: rv-agent (local poetry)"
echo ""
echo "⏳ Running test..."

# We're already in rv-agent module directory

# Run single test with full output capture
{
    echo "========================================"
    echo "SINGLE TEST START: $(date)"
    echo "========================================"
    echo ""
    echo "Environment:"
    echo "  PWD: $(pwd)"
    echo "  Python: $(poetry run python --version)"
    echo ""

    # Test if we can import modules first
    echo "Testing imports..."
    poetry run python -c "
import sys
sys.path.append('validation')
try:
    from mock_device_adapter import MockDeviceAdapter
    from simple_tools_with_explanation import create_validation_tools
    from coordinate_validator import CoordinateValidator
    print('✅ All imports successful')
except Exception as e:
    print(f'❌ Import error: {e}')
"
    echo ""

    # Run the actual test
    echo "Running validation test..."
    poetry run python validation/quick_test.py

    echo ""
    echo "========================================"
    echo "SINGLE TEST END: $(date)"
    echo "========================================"

} > "$LOG_FILE" 2>&1

EXIT_CODE=$?

cd validation

echo ""
echo "✅ Single test completed with exit code: $EXIT_CODE"
echo ""

# Quick analysis
if [ $EXIT_CODE -eq 0 ]; then
    echo "📊 Quick Results:"

    # Check for success indicators
    if grep -q "Test successful" "$LOG_FILE"; then
        echo "  ✅ Test executed successfully"

        # Extract key metrics
        HIT_RATE=$(grep "Hit Rate:" "$LOG_FILE" | tail -1 | sed 's/.*Hit Rate: //' | sed 's/%.*//')
        if [ ! -z "$HIT_RATE" ]; then
            echo "  🎯 Hit Rate: ${HIT_RATE}%"
        fi

        CLICKS=$(grep "Clicks:" "$LOG_FILE" | tail -1 | sed 's/.*Clicks: //')
        if [ ! -z "$CLICKS" ]; then
            echo "  🖱️ Total Clicks: $CLICKS"
        fi

        echo ""
        echo "📖 View full results:"
        echo "  cat logs/$(basename $LOG_FILE)"

    else
        echo "  ❌ Test may have failed - check log for errors"
    fi

else
    echo "  ❌ Test failed with exit code $EXIT_CODE"
    echo ""
    echo "🔍 Check for errors:"
    echo "  grep -i 'error\\|exception\\|failed' logs/$(basename $LOG_FILE)"
fi

echo ""
echo "📋 Log file: logs/$(basename $LOG_FILE)"

exit $EXIT_CODE