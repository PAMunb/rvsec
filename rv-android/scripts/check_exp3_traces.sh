#!/bin/bash
# Quick sanity check on first completed traces — verify LLM is working.
# Usage: bash scripts/check_exp3_traces.sh [results_dir]

RESULTS_DIR="${1:-data/results}"
echo "=== Exp3 Trace Sanity Check ($(date '+%H:%M:%S')) ==="

checked=0
for i in $(seq 0 7); do
    dir=$(printf "$RESULTS_DIR/exp3_%02d/exp3_%02d" $i $i)
    [ -d "$dir" ] || continue

    traces=$(find "$dir" -name "*.trace" -size +0c 2>/dev/null | head -3)
    for trace in $traces; do
        apk=$(basename $(dirname "$trace"))
        size=$(stat -c%s "$trace" 2>/dev/null || echo 0)
        llm_calls=$(grep -c "LlmRouter\|SglangClient\|LLM action" "$trace" 2>/dev/null || echo 0)
        timeouts=$(grep -c "LLM.*timeout\|llm.*timed out" "$trace" 2>/dev/null || echo 0)
        circuit=$(grep -c "CircuitBreaker.*OPEN" "$trace" 2>/dev/null || echo 0)
        errors=$(grep -c "LLM.*error\|LLM.*fail\|SglangClient.*error" "$trace" 2>/dev/null || echo 0)

        echo ""
        echo "  $apk ($(( size / 1024 ))KB)"
        echo "    LLM calls: $llm_calls | Timeouts: $timeouts | Circuit OPEN: $circuit | Errors: $errors"

        if [ "$llm_calls" -eq 0 ]; then
            echo "    WARNING: No LLM calls detected!"
        elif [ "$timeouts" -gt "$((llm_calls / 2))" ]; then
            echo "    WARNING: >50% of calls timed out — SGLang overloaded?"
        elif [ "$circuit" -gt 5 ]; then
            echo "    WARNING: Circuit breaker opened multiple times"
        else
            echo "    OK"
        fi
        checked=$((checked + 1))
    done
done

if [ "$checked" -eq 0 ]; then
    echo ""
    echo "  No traces found yet — experiment may not have started"
fi

echo ""
echo "=== Empty traces ==="
empty=$(find "$RESULTS_DIR"/exp3_*/exp3_*/ -name "*.trace" -size 0 2>/dev/null | wc -l)
total=$(find "$RESULTS_DIR"/exp3_*/exp3_*/ -name "*.trace" 2>/dev/null | wc -l)
echo "  $empty/$total empty traces"
if [ "$total" -gt 0 ] && [ "$empty" -gt "$((total / 3))" ]; then
    echo "  WARNING: Too many empty traces (>33%)"
fi
