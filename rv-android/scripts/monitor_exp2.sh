#!/bin/bash
# Monitor progress of experiment 2: aperv:sata_mop + rvsmart:mvp.
#
# Usage:
#   bash scripts/monitor_exp2.sh
#   watch -n 60 bash scripts/monitor_exp2.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="exp2_00 exp2_01 exp2_02 exp2_03 exp2_04 exp2_05 exp2_06 exp2_07 exp2_08 exp2_09"
EXPECTED=1014  # 169 APKs × 2 tools × 3 reps

echo "=== Experiment 2: aperv:sata_mop + rvsmart:mvp ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-10s %-12s %5s %5s %5s %5s  %s\n" \
    "Container" "Status" "Done" "Fail" "Total" "%" "Last tool"
printf "%-10s %-12s %5s %5s %5s %5s  %s\n" \
    "----------" "------" "----" "----" "-----" "---" "---------"

total_completed=0
total_failed=0
total_tasks=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c"
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "gone")

    tasks_file="$dir/$c/tasks.json"
    completed=0
    failed=0
    ntasks=0
    last_tool="-"
    if [ -f "$tasks_file" ]; then
        read completed failed ntasks last_tool < <(python3 -c "
import json
with open('$tasks_file') as f:
    data = json.load(f)
tasks = data.get('tasks', [])
c = sum(1 for t in tasks if t.get('result',{}).get('state') == 'COMPLETED')
f = sum(1 for t in tasks if t.get('result',{}).get('state') in ('FAILED', 'ERROR'))
last = '-'
for t in reversed(tasks):
    if t.get('result',{}).get('state') in ('COMPLETED','FAILED','ERROR'):
        last = t.get('tool','?')
        break
print(c, f, len(tasks), last)
" 2>/dev/null || echo "0 0 0 -")
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))
    total_tasks=$((total_tasks + ntasks))

    done_count=$((completed + failed))
    if [ "$ntasks" -gt 0 ]; then
        pct=$((100 * done_count / ntasks))
    else
        pct=0
    fi

    printf "%-10s %-12s %5d %5d %5d %4d%%  %s\n" \
        "$c" "$status" "$completed" "$failed" "$ntasks" "$pct" "$last_tool"
done

echo ""
remaining=$((EXPECTED - total_completed - total_failed))
if [ $remaining -lt 0 ]; then remaining=0; fi
pct_total=0
if [ $EXPECTED -gt 0 ]; then
    pct_total=$((100 * (total_completed + total_failed) / EXPECTED))
fi

echo "Overall: $total_completed completed, $total_failed failed, $remaining remaining [$pct_total%]"

# ETA calculation
if [ $total_completed -gt 0 ]; then
    # Find earliest task start time
    start_ts=$(python3 -c "
import json, os
from pathlib import Path
earliest = None
for i in range(10):
    tf = Path('$RESULTS_DIR') / f'exp2_{i:02d}' / f'exp2_{i:02d}' / 'tasks.json'
    if tf.exists():
        ts = os.path.getmtime(tf)
        if earliest is None or ts < earliest:
            earliest = ts
if earliest:
    print(f'{earliest:.0f}')
else:
    print('0')
" 2>/dev/null)
    if [ "$start_ts" != "0" ] && [ -n "$start_ts" ]; then
        now=$(date +%s)
        elapsed=$((now - ${start_ts%.*}))
        done_count=$((total_completed + total_failed))
        if [ $done_count -gt 0 ] && [ $remaining -gt 0 ]; then
            secs_per_task=$((elapsed / done_count))
            eta_secs=$((secs_per_task * remaining / 10))  # 10 containers in parallel
            eta_hours=$(echo "scale=1; $eta_secs / 3600" | bc 2>/dev/null || echo "?")
            eta_time=$(date -d "+${eta_secs} seconds" '+%H:%M' 2>/dev/null || echo "?")
            echo "Pace: ${secs_per_task}s/task | ETA: ~${eta_hours}h (finish ~${eta_time})"
        fi
        elapsed_h=$(echo "scale=1; $elapsed / 3600" | bc 2>/dev/null || echo "?")
        echo "Elapsed: ${elapsed_h}h"
    fi
fi
