#!/bin/bash
# Monitor calibration progress: orchestrator + live containers.
# Usage: bash scripts/monitor_calibration.sh [results_dir]
#        bash scripts/monitor_calibration.sh results/precal_macro

RESULTS_DIR="${1:-results/precal_macro}"
LOG="$RESULTS_DIR/orchestrator.log"

echo "========================================================================"
echo "  Calibration Monitor — $(basename "$RESULTS_DIR")"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================================================"

# --- Orchestrator summary ---
echo ""
echo "--- Orchestrator ---"

completed=0
total_trials=0
containers=1

if [[ -f "$LOG" ]]; then
    phase=$(grep -oP 'Phase: \K\w+' "$LOG" 2>/dev/null | head -1)
    phase=${phase:-"?"}
    total_trials=$(grep -oP 'Trials: \K\d+' "$LOG" 2>/dev/null | head -1)
    total_trials=${total_trials:-0}
    containers=$(grep -oP 'Containers/round: \K\d+' "$LOG" 2>/dev/null | head -1)
    containers=${containers:-1}
    baseline_err=$(grep -oP 'Baseline max errors.*: \K[\d.]+' "$LOG" 2>/dev/null | head -1)
    baseline_err=${baseline_err:-"?"}
    round_timeout=$(grep -oP 'Round timeout: \K\d+' "$LOG" 2>/dev/null | head -1)
    round_timeout=${round_timeout:-"?"}

    echo "  Phase: $phase | Trials: $total_trials | Containers/round: $containers"
    echo "  Baseline max errors: $baseline_err | Round timeout: ${round_timeout}s"

    # grep -c always prints count (even 0) but returns exit 1 on no match.
    # Capture output separately to avoid "0\n0" from || echo "0".
    completed=$(grep -cP 'Trial \d+ -> score' "$LOG" 2>/dev/null) || true
    completed=${completed:-0}
    failed=$(grep -cP 'Trial \d+ FAILED' "$LOG" 2>/dev/null) || true
    failed=${failed:-0}
    current_round=$(grep -oP 'Round \K\d+' "$LOG" 2>/dev/null | tail -1)
    current_round=${current_round:-1}
    total_rounds=$(( (total_trials + containers - 1) / containers ))

    echo "  Completed: $completed/$total_trials | Failed: $failed | Round: $current_round/$total_rounds"

    # Best score
    if [[ "$completed" -gt 0 ]]; then
        best=$(grep -P 'Trial \d+ -> score' "$LOG" 2>/dev/null | \
            awk '{print $NF, $0}' | sort -rn | head -1 | sed 's/^[^ ]* //')
        if [[ -n "$best" ]]; then
            best_score=$(echo "$best" | grep -oP 'score \K[\d.]+')
            best_trial=$(echo "$best" | grep -oP 'Trial \K\d+')
            echo "  Best: trial_$best_trial = $best_score"
        fi

        # Last round score range
        scores=$(grep -oP 'score \K[\d.]+' "$LOG" 2>/dev/null | tail -"$containers")
        if [[ -n "$scores" ]]; then
            min_s=$(echo "$scores" | sort -n | head -1)
            max_s=$(echo "$scores" | sort -rn | head -1)
            echo "  Last round scores: $min_s — $max_s"
        fi
    fi
else
    echo "  (no orchestrator.log yet)"
fi

# --- Live containers ---
echo ""
echo "--- Live Containers ---"

running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep "$(basename "$RESULTS_DIR")-trial_" | sort) || true

if [[ -z "$running" ]]; then
    echo "  (no containers running)"
else
    printf "  %-12s  %-6s  %-6s  %-8s  %s\n" "Container" "Task" "Iter" "Elapsed" "APK"
    printf "  %-12s  %-6s  %-6s  %-8s  %s\n" "----------" "------" "------" "--------" "---"

    for name in $running; do
        trial_id=$(echo "$name" | grep -oP 'trial_\d+') || true
        trial_id=${trial_id:-"$name"}

        # Task/APK: grep full logs (not tail) for "Executing task" lines
        task_line=$(docker logs "$name" 2>&1 | grep -aP 'Executing task \d+/\d+' | tail -1) || true
        task_num=$(echo "$task_line" | grep -oP 'Executing task \K\d+/\d+') || true
        task_num=${task_num:-"?/?"}

        apk=$(echo "$task_line" | grep -oP 'apk=\K[^,)]+') || true
        apk=${apk:-"?"}
        apk=$(echo "$apk" | sed 's/_[0-9]*\.apk$//')
        [[ ${#apk} -gt 30 ]] && apk="${apk:0:27}..."

        # Iteration/elapsed: only need recent lines
        iter_line=$(docker logs --tail 200 "$name" 2>&1 | grep -aP 'Iteration \d+' | tail -1) || true
        iter=$(echo "$iter_line" | grep -oP 'Iteration \K\d+') || true
        iter=${iter:-"?"}

        elapsed_s=$(echo "$iter_line" | grep -oP 'elapsed: \K[\d.]+') || true
        if [[ -n "$elapsed_s" ]]; then
            elapsed_m=$(awk "BEGIN{printf \"%.0f\", $elapsed_s/60}")
            elapsed_str="${elapsed_m}m"
        else
            elapsed_str="?"
        fi

        printf "  %-12s  %-6s  %-6s  %-8s  %s\n" "$trial_id" "$task_num" "$iter" "$elapsed_str" "$apk"
    done
fi

# --- Resources ---
echo ""
echo "--- Resources ---"
n_running=0
if [[ -n "$running" ]]; then
    n_running=$(echo "$running" | wc -l)
fi
cpu_count=$(nproc)
mem_info=$(free -g 2>/dev/null | awk '/Mem/{printf "%dG/%dG", $3, $2}') || true
mem_info=${mem_info:-"?"}
disk_info=$(df -h / | awk 'NR==2{printf "%s free (%s used)", $4, $5}') || true
disk_info=${disk_info:-"?"}
echo "  Containers: $n_running | CPUs: $cpu_count | RAM: $mem_info | Disk: $disk_info"

# --- ETA ---
if [[ -f "$LOG" && "$completed" -gt 0 && "$completed" -lt "$total_trials" ]]; then
    echo ""
    echo "--- ETA ---"
    remaining_trials=$((total_trials - completed))
    remaining_rounds=$(( (remaining_trials + containers - 1) / containers ))

    round_times=$(grep -oP 'Round \d+ finished in \K\d+' "$LOG" 2>/dev/null) || true
    if [[ -n "$round_times" ]]; then
        avg_round=$(echo "$round_times" | awk '{s+=$1; n++} END{printf "%.0f", s/n}')
        eta_secs=$((remaining_rounds * avg_round))
        eta_hours=$(awk "BEGIN{printf \"%.1f\", $eta_secs/3600}")
        eta_finish=$(date -d "+${eta_secs} seconds" '+%Y-%m-%d %H:%M')
        echo "  Remaining: $remaining_trials trials ($remaining_rounds rounds)"
        echo "  Avg round: ${avg_round}s ($(awk "BEGIN{printf \"%.1f\", $avg_round/3600}")h)"
        echo "  ETA: ${eta_hours}h -> $eta_finish"
    else
        echo "  (waiting for first round to finish for ETA)"
    fi
elif [[ "$completed" -eq 0 && -f "$LOG" ]]; then
    echo ""
    echo "--- ETA ---"
    echo "  (waiting for first round to finish for ETA)"
fi

echo ""
