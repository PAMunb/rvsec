#!/bin/bash
# Snapshot progress of the E3 decisive run (gh90).
#
# Usage:
#   cd .../rv-android/experimento-e3-decisiva
#   bash scripts/monitor.sh
#   watch -n 120 bash scripts/monitor.sh
#
# Expected total is 120 = 40 APKs x 3 arms x 1 repetition. Each container owns
# 5 APKs and runs all three arms over them, so a healthy container converges on
# 15 tasks. A container short of 15 with the others done is where the resume
# pass has work to do.

RESULTS_DIR="${1:-results}"
CONTAINERS="e3_decisiva_00 e3_decisiva_01 e3_decisiva_02 e3_decisiva_03 e3_decisiva_04 e3_decisiva_05 e3_decisiva_06 e3_decisiva_07"
EXPECTED=120

echo "=== E3 decisive run progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-16s %-10s %-9s %-6s %-6s %-10s %s\n" \
    "Container" "Status" "Completed" "Failed" "Total" "Phase" "Last activity"
printf "%-16s %-10s %-9s %-6s %-6s %-10s %s\n" \
    "---------------" "------" "---------" "------" "-----" "-----" "-------------"

total_completed=0
total_failed=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c/$c"
    # docker inspect emits an empty stdout line before failing on a missing
    # container, so a bare `|| echo` would produce a two-line status and break
    # the column layout. Take the first non-empty line instead.
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | head -1)
    [ -z "$status" ] && status="not-found"

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
    tasks = data if isinstance(data, list) else data.get('tasks', [])
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
        else
            phase="boot"
        fi

        last=$(find "$dir" -type f -printf '%T+ %f\n' 2>/dev/null \
            | sort -r | head -1 | awk '{print $2}')
        [ -z "$last" ] && last="-"
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))

    printf "%-16s %-10s %-9s %-6s %-6s %-10s %s\n" \
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
echo ""
sglang_status=$(docker inspect --format='{{.State.Status}} ({{.State.Health.Status}})' sglang-server 2>/dev/null | head -1)
[ -z "$sglang_status" ] && sglang_status="not-found"
echo "SGLang: $sglang_status"
