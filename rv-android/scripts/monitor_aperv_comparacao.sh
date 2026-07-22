#!/bin/bash
# Monitor progress of APE-RV comparison experiment containers.
# Reads tasks.json from each container's results directory to count completed/failed tasks.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/monitor_aperv_comparacao.sh
#   watch -n 60 bash scripts/monitor_aperv_comparacao.sh
#
# See: docs/20260313_aperv_comparacao.md

RESULTS_DIR="${1:-data/results}"
CONTAINERS="aperv_00 aperv_01 aperv_02 aperv_03 aperv_04 aperv_05 aperv_06 aperv_07 aperv_08 aperv_09"
EXPECTED=1014  # 169 APKs × 3 tools × 2 reps

echo "=== APE-RV Comparison Progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
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

    # rv-experiment nests results: $dir/$c/tasks.json
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

    # Last modified file in results dir
    last=$(find "$dir" -type f -newer "$dir" -printf '%T+ %f\n' 2>/dev/null \
        | sort -r | head -1 | cut -d' ' -f2)
    [ -z "$last" ] && last="-"

    printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
        "$c" "$status" "$completed" "$failed" "$((completed+failed))" "$ntasks" "$last"
done

echo ""

# Per-tool breakdown (aggregated across containers)
echo "--- Per-Tool Breakdown ---"
python3 -c "
import json
from pathlib import Path
from collections import defaultdict

results_dir = Path('$RESULTS_DIR')
tool_stats = defaultdict(lambda: {'completed': 0, 'failed': 0, 'total': 0})

for i in range(10):
    name = f'aperv_{i:02d}'
    tasks_file = results_dir / name / name / 'tasks.json'
    if not tasks_file.exists():
        continue
    with open(tasks_file) as f:
        data = json.load(f)
    for t in data.get('tasks', []):
        tool = t['config']['tool']
        state = t.get('result', {}).get('state', 'UNKNOWN')
        tool_stats[tool]['total'] += 1
        if state == 'COMPLETED':
            tool_stats[tool]['completed'] += 1
        elif state in ('FAILED', 'ERROR'):
            tool_stats[tool]['failed'] += 1

for tool in sorted(tool_stats):
    s = tool_stats[tool]
    print(f'  {tool:20s}: {s[\"completed\"]:4d} completed, {s[\"failed\"]:4d} failed (of {s[\"total\"]})')
" 2>/dev/null

echo ""
remaining=$((EXPECTED - total_completed - total_failed))
pct=0
if [ $EXPECTED -gt 0 ]; then
    pct=$((100 * (total_completed + total_failed) / EXPECTED))
fi
echo "Overall: $total_completed completed, $total_failed failed, $remaining remaining (of $EXPECTED expected) [$pct%]"
