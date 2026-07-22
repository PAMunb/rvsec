#!/bin/bash
# Snapshot progress of the JCA-400 aperv:sata_mop experiment.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/monitor_jca400.sh
#   watch -n 60 bash scripts/monitor_jca400.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="jca400_00 jca400_01 jca400_02 jca400_03 jca400_04 jca400_05"
EXPECTED=400

echo "=== JCA-400 aperv:sata_mop progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-11s %-10s %-9s %-6s %-6s %-8s %s\n" \
    "Container" "Status" "Completed" "Failed" "Total" "Phase" "Last activity"
printf "%-11s %-10s %-9s %-6s %-6s %-8s %s\n" \
    "----------" "------" "---------" "------" "-----" "-----" "-------------"

total_completed=0
total_failed=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c/$c"
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "not-found")

    completed=0
    failed=0
    ntasks=0
    phase="setup"
    last="-"

    tasks_file="$dir/tasks.json"
    if [ -f "$tasks_file" ]; then
        read completed failed ntasks < <(python3 -c "
import json
try:
    with open('$tasks_file') as f:
        data = json.load(f)
    tasks = data.get('tasks', [])
    c = sum(1 for t in tasks if t.get('result',{}).get('state') == 'COMPLETED')
    f = sum(1 for t in tasks if t.get('result',{}).get('state') in ('FAILED','ERROR'))
    print(c, f, len(tasks))
except Exception:
    print(0, 0, 0)
" 2>/dev/null)
    fi

    if [ -d "$dir" ]; then
        if [ "$completed" -gt 0 ] || [ "$failed" -gt 0 ]; then
            phase="exec"
        elif [ -d "$dir/instrumented_apks" ]; then
            phase="sa+run"
        elif [ -d "$dir/monitors" ]; then
            phase="instrument"
        else
            phase="monitors"
        fi

        last=$(find "$dir" -type f -printf '%T+ %f\n' 2>/dev/null \
            | sort -r | head -1 | awk '{print $2}')
        [ -z "$last" ] && last="-"
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))

    printf "%-11s %-10s %-9s %-6s %-6s %-8s %s\n" \
        "$c" "$status" "$completed" "$failed" "$ntasks" "$phase" "$last"
done

echo ""
done_total=$((total_completed + total_failed))
pct=0
if [ $EXPECTED -gt 0 ]; then
    pct=$((100 * done_total / EXPECTED))
fi
remaining=$((EXPECTED - done_total))
echo "Overall: $total_completed completed, $total_failed failed, $remaining pending of $EXPECTED [$pct%]"
