#!/bin/bash
# Monitor progress of comparison experiment containers.
#
# Usage: bash scripts/monitor_comparacao.sh
#        watch -n 60 bash scripts/monitor_comparacao.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="cmp01 cmp02 cmp03 cmp04 cmp05 cmp06 cmp07 cmp08"

echo "=== Comparison Experiment Progress ($(date '+%H:%M:%S')) ==="
echo ""

printf "%-8s %-12s %-10s %-10s %-6s %-6s %s\n" "Container" "Status" "Completed" "Failed" "Done" "Total" "Last activity"
printf "%-8s %-12s %-10s %-10s %-6s %-6s %s\n" "--------" "------" "---------" "------" "----" "-----" "-------------"

total_completed=0
total_failed=0
total_tasks=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c"

    # Container status
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "not found")

    if [ ! -d "$dir" ]; then
        printf "%-8s %-12s %-10s %-10s %-6s %-6s %s\n" "$c" "$status" "0" "0" "0" "?" "no results dir"
        continue
    fi

    # rv-experiment nests results: $dir/$c/tasks.json
    tasks_file="$dir/$c/tasks.json"
    completed=0
    failed=0
    ntasks=0
    if [ -f "$tasks_file" ]; then
        # Use python to count correctly from JSON structure (avoid double-counting)
        read completed failed ntasks < <(python3 -c "
import json, sys
with open('$tasks_file') as f:
    data = json.load(f)
tasks = data.get('tasks', [])
c = sum(1 for t in tasks if t.get('result',{}).get('state') == 'COMPLETED')
f = sum(1 for t in tasks if t.get('result',{}).get('state') in ('FAILED', 'ERROR'))
print(c, f, len(tasks))
" 2>/dev/null || echo "0 0 0")
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))
    total_tasks=$((total_tasks + ntasks))

    # Last modified file
    last=$(find "$dir" -type f -newer "$dir" -printf '%T+ %f\n' 2>/dev/null | sort -r | head -1 | cut -d' ' -f2)
    [ -z "$last" ] && last="-"

    printf "%-8s %-12s %-10s %-10s %-6s %-6s %s\n" "$c" "$status" "$completed" "$failed" "$((completed+failed))" "$ntasks" "$last"
done

echo ""

expected=600  # 100 APKs x 2 tools (rvsmart:mvp + arrival_first_v17) x 3 reps
echo "Overall: $total_completed completed, $total_failed failed, $((expected - total_completed - total_failed)) remaining (of $expected expected)"
