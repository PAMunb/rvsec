#!/bin/bash
# Snapshot progress of leg B of the rearch A/B gate (gh97).
#
# Usage:
#   cd .../rv-android/experimento-rearch-aperv
#   bash scripts/monitor.sh
#   watch -n 120 bash scripts/monitor.sh
#
# Expected total is 360 = 40 APKs x 3 arms x 3 repetitions, the same grid as leg
# A by requirement. Amendment 01 spreads that grid over ten containers, so each
# container owns 4 APKs and runs all three arms over them, and a healthy
# container converges on 36 tasks. A container short of 36 with the others done
# is where the resume pass has work to do.
#
# The count below is identity-distinct by construction — it reads each task's
# state, never `grep COMPLETED tasks.json`, which double-counts through
# state_transitions.

RESULTS_DIR="${1:-results}"
CONTAINERS="rearch_aperv_00 rearch_aperv_01 rearch_aperv_02 rearch_aperv_03 rearch_aperv_04 rearch_aperv_05 rearch_aperv_06 rearch_aperv_07 rearch_aperv_08 rearch_aperv_09"
EXPECTED=360

echo "=== rearch A/B gate — leg B progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
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
# Counted per IDENTITY (apk, tool, variant, repetition, timeout), not per task
# record: a resume appends a fresh task_id for an identity it re-attempts, so
# counting records reports more completed work than exists and a container looks
# finished while a pair is still missing. An identity that ever completed counts
# as completed even if a later record for it failed.
try:
    with open('$tasks_file') as f:
        data = json.load(f)
    tasks = data if isinstance(data, list) else data.get('tasks', [])
    states = {}
    for t in tasks:
        cfg = t.get('config') or {}
        tc = cfg.get('tool_config') or {}
        ident = (cfg.get('apk_name'), tc.get('name'), tc.get('variant'),
                 cfg.get('repetition'), cfg.get('timeout'))
        state = (t.get('result') or {}).get('state')
        if states.get(ident) != 'COMPLETED':
            states[ident] = state
    c = sum(1 for s in states.values() if s == 'COMPLETED')
    f = sum(1 for s in states.values() if s in ('FAILED', 'ERROR'))
    print(c, f, len(states))
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
