#!/bin/bash
# Monitor progress of exp6 (component triggering) containers.
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/monitor_exp6.sh
#   watch -n 60 bash scripts/monitor_exp6.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="exp6_00 exp6_01 exp6_02 exp6_03 exp6_04 exp6_05 exp6_06 exp6_07 exp6_08 exp6_09"
EXPECTED=507  # 169 APKs × 1 tool × 3 reps

echo "=== Exp6: Component Triggering Progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
    "Container" "Status" "Completed" "Failed" "Done" "Total" "Last activity"
printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
    "----------" "------" "---------" "------" "----" "-----" "-------------"

total_completed=0
total_failed=0
total_tasks=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c"
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "not found")

    if [ ! -d "$dir" ]; then
        printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
            "$c" "$status" "0" "0" "0" "?" "no results dir"
        continue
    fi

    tasks_file="$dir/$c/tasks.json"
    completed=0
    failed=0
    ntasks=0
    if [ -f "$tasks_file" ]; then
        read completed failed ntasks < <(python3 -c "
import json
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

    last=$(find "$dir" -type f -newer "$dir" -printf '%T+ %f\n' 2>/dev/null \
        | sort -r | head -1 | cut -d' ' -f2)
    [ -z "$last" ] && last="-"

    printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
        "$c" "$status" "$completed" "$failed" "$((completed+failed))" "$ntasks" "$last"
done

echo ""
remaining=$((EXPECTED - total_completed - total_failed))
pct=0
if [ $EXPECTED -gt 0 ]; then
    pct=$((100 * (total_completed + total_failed) / EXPECTED))
fi
echo "Overall: $total_completed completed, $total_failed failed, $remaining remaining (of $EXPECTED expected) [$pct%]"
