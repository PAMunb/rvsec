# Runbook: Calibration Execution Campaign

This is an **execution runbook**, not a code design. Each section corresponds to one calibration phase and is self-contained — future sessions load ONLY the relevant section. The full technical analysis (architecture, design decisions, validated assumptions) is in `docs/20260213_plano_calibracao.md`.

**Infrastructure reference**: The two host-side scripts are documented in `docs/20260213_plano_calibracao.md` Sections 4.1 and 4.2. The original infrastructure design decisions (D1-D7) are preserved in `docs/20260213_plano_calibracao.md` Sections 3 and 8.

---

## 0. Prerequisites (All Phases)

### Environment

| Requirement | Value | Verification |
|-------------|-------|-------------|
| Machine | Desktop: 64 CPUs, 128GB RAM | `nproc && free -h` |
| Docker | Image `phtcosta/rvandroid:0.8.0` | `docker images \| grep rvandroid` |
| KVM | `/dev/kvm` accessible | `ls -la /dev/kvm` |
| Dataset | `calibration_dataset_v2/` (105 APKs + SA) | `ls data/calibration_dataset_v2/*.apk \| wc -l` → 105 |
| Filter files | `all_valid_apks.txt` (105), `calibration_set_v2.txt` (75), `holdout_set_v2.txt` (30) | `wc -l data/*.txt` |
| SGLang (Phase D only) | Server at `192.168.0.36:30000` | `curl -s http://192.168.0.36:30000/v1/models` |
| rv-android | Poetry install, all modules | `poetry run python -c "from rv_agent_validation.calibration import ObjectiveFunction; print('OK')"` |

### Data paths (relative to rv-android root)

```
DATA_DIR=modules/rv-agent-validation/data/calibration_dataset_v2
FILTER_ALL=modules/rv-agent-validation/data/all_valid_apks.txt
FILTER_CAL=modules/rv-agent-validation/data/calibration_set_v2.txt
FILTER_HOLDOUT=modules/rv-agent-validation/data/holdout_set_v2.txt
```

### Container configuration

Each container runs with: 10 CPUs, 20GB RAM, `/dev/kvm` passthrough, staggered start (10s apart), `RV_DEVICE_PORT=5554` (internal), all skip flags enabled (APKs are pre-instrumented). No Humanoid service needed.

---

## 1. Phase B — Baseline (~18.4 hours)

### Purpose

Establish performance baselines for 3 tools (APE, FastBot, RVAgent:pure_algorithm) on all 105 APKs with 3 repetitions. The key output is `BASELINE_MAX_ERRORS` — the maximum average error count across tools — which normalizes the error component of the objective function in Phases C and D.

### Execution

```bash
poetry run python scripts/baseline_docker.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_ALL \
    --output-dir ./results/baseline_v2 \
    --n-containers 6 --timeout 300 --repetitions 3
```

**Tasks**: 3 tools x 105 APKs x 3 reps = 945 tasks, split across 6 containers (~158 tasks each).

**Expected duration**: ~18.4 hours (945 tasks x 7 min / 6 containers).

### Expected outputs

```
results/baseline_v2/
├── docker-compose.yml                    # Generated compose file
├── batch_{0..5}_apks.txt                 # Per-batch filter files (6 files)
├── summary.csv                           # Aggregated: all batches combined
├── aggregated_summary.csv -> summary.csv # Symlink for readability
├── batch_0/batch_0/
│   ├── tasks.json                        # 158 completed tasks
│   └── summary.csv                       # Per-batch results
├── batch_1/batch_1/ ...
└── batch_5/batch_5/ ...
```

### Verification

```bash
# 1. All batch results exist
for i in $(seq 0 5); do
    echo "batch_$i: $(wc -l < results/baseline_v2/batch_$i/batch_$i/summary.csv) rows"
done

# 2. Aggregated summary has correct row count
# Expected: 945 data rows + 1 header = 946 lines
wc -l results/baseline_v2/summary.csv
# → 946

# 3. All 3 tools present
cut -d',' -f2 results/baseline_v2/summary.csv | sort -u
# → ape, fastbot, rvagent (+ header "tool")

# 4. Compute BASELINE_MAX_ERRORS
python3 -c "
import pandas as pd
df = pd.read_csv('results/baseline_v2/summary.csv')
max_errors = df.groupby('tool')['errors'].mean().max()
print(f'BASELINE_MAX_ERRORS = {max_errors:.2f}')
"

# 5. Symlink intact
ls -la results/baseline_v2/aggregated_summary.csv
# → aggregated_summary.csv -> summary.csv
```

**Gate**: All 6 batch summaries exist, aggregated CSV has 945 data rows, 3 tools present, BASELINE_MAX_ERRORS is a finite positive number. Record the value — it is needed for Phases C and D.

### Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Container exits with code 137 | OOM kill (20GB exceeded) | Check which APK caused it; consider excluding or reducing timeout |
| `summary.csv` has fewer rows than expected | Some APKs failed | Check `tasks.json` for failed entries; restart container to retry |
| `aggregated_summary.csv` missing | Script interrupted before aggregation | Run: `poetry run python -c "from baseline_docker import aggregate_summaries; ..."` |
| Emulator boot timeout | KVM contention at startup | Increase `RV_DELAY` between containers |

### Resume (if interrupted)

```bash
# Same command — rv-experiment auto-resumes via tasks.json
poetry run python scripts/baseline_docker.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_ALL \
    --output-dir ./results/baseline_v2 \
    --n-containers 6 --timeout 300 --repetitions 3
```

---

## 2. Phase C — Macro Calibration (~122 hours / 5.1 days)

### Purpose

Tune 8 high-impact parameters (scorer weights and exploration settings) using Optuna's TPESampler with batch parallelism. Each trial evaluates one parameter set by running RVAgent on all 75 calibration APKs.

### Parameters tuned

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `mop_direct_score` | 300.0 | 200-500 | MOP method prioritization |
| `wtg_guided_score` | 250.0 | 100-400 | WTG navigation guidance |
| `unsaturated_bonus` | 80.0 | 40-120 | State diversity bonus |
| `max_re_enables` | 6 | 3-15 | Successor exploration depth |
| `ui_coverage_threshold` | 0.9 | 0.7-1.0 | Re-enable trigger threshold |
| `stochastic_probability` | 0.3 | 0.1-0.7 | Exploration randomness |
| `strength_weight` | 50.0 | 25-100 | Historical action success |
| `visitation_penalty_factor` | -10.0 | -20 to -5 | Over-visited penalty |

### Execution

```bash
poetry run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 80 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_CAL \
    --output-dir ./results/calibration_macro_v2 \
    --timeout 300 --agent-mode pure_algorithm --seed 42 \
    --baseline-dir ./results/baseline_v2
```

**Trials**: 80 total, in batches of 6. Each trial processes 75 APKs.

**Expected duration**: 14 rounds x 8.75h = ~122 hours.

**Objective function**: 40% method coverage + 40% normalized MOP errors + 20% UI coverage.

### Expected outputs

```
results/calibration_macro_v2/
├── optuna_study.db                       # Persistent Optuna SQLite
├── orchestrator.log                      # Script execution log
├── docker-compose.round-01.yml           # Round 1 compose (trials 0-5)
├── docker-compose.round-02.yml           # Round 2 compose (trials 6-11)
├── ...                                   # Up to round-14
├── trial_0/trial_0/summary.csv           # Per-trial results
├── trial_1/trial_1/summary.csv
├── ...                                   # Up to trial_79
├── optimal_params.json                   # Best parameters + score
├── param_string.txt                      # DSL string for --tools
└── trial_history.json                    # All trial results
```

### Verification

```bash
# 1. All 80 trials completed
python3 -c "
import json
with open('results/calibration_macro_v2/trial_history.json') as f:
    trials = json.load(f)
print(f'{len(trials)} trials completed')
assert len(trials) == 80, f'Expected 80, got {len(trials)}'
"

# 2. Best score is meaningful (> 0.1 expected)
python3 -c "
import json
with open('results/calibration_macro_v2/optimal_params.json') as f:
    data = json.load(f)
print(f'Best score: {data[\"best_score\"]:.4f}')
print(f'Best params: {json.dumps(data[\"best_params\"], indent=2)}')
assert data['best_score'] > 0.0, 'Best score is 0 — all trials failed?'
"

# 3. Convergence analysis (score over time)
python3 -c "
import json
with open('results/calibration_macro_v2/trial_history.json') as f:
    trials = json.load(f)
scores = [t['value'] for t in trials if t['value'] is not None]
print(f'Score range: {min(scores):.4f} - {max(scores):.4f}')
print(f'Mean (first 20): {sum(scores[:20])/20:.4f}')
print(f'Mean (last 20): {sum(scores[-20:])/20:.4f}')
# Last 20 should generally score higher than first 20 (convergence)
"

# 4. param_string.txt is valid DSL
cat results/calibration_macro_v2/param_string.txt
# Should look like: mop_direct_score=350.0000,wtg_guided_score=280.0000,...
```

**Gate**: 80 trials completed, best_score > 0.0, convergence visible (last 20 trials score higher than first 20 on average), `optimal_params.json` and `param_string.txt` exist.

### Resume (if interrupted)

```bash
# Same command + --resume flag
poetry run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 80 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_CAL \
    --output-dir ./results/calibration_macro_v2 \
    --timeout 300 --agent-mode pure_algorithm --seed 42 \
    --baseline-dir ./results/baseline_v2 \
    --resume
```

The script recovers orphaned RUNNING trials from SQLite, scores any that have results, marks others as FAIL, and continues with new trial suggestions.

### Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Many trials score 0.0 | Containers failing before producing results | Check `trial_N/trial_N/tasks.json` for errors; may need to increase timeout |
| No convergence | Parameter ranges too wide or objective function issues | Check `objective.py` error computation; verify BASELINE_MAX_ERRORS is correct |
| Script hangs after `docker compose up` | All containers stuck | Ctrl+C (cleanup guaranteed by try/finally); check emulator status inside containers |
| `optuna_study.db` locked | Previous script instance still running | Kill previous process; SQLite lock is PID-based |

---

## 3. Phase D — Micro Calibration (~160 hours / 6.7 days)

### Purpose

Fine-tune 16 additional parameters while keeping the 8 macro parameters fixed at their optimal values from Phase C. Uses `multimode` agent mode, which requires the SGLang server (Qwen3-VL-4B).

### Prerequisites (in addition to Section 0)

- Phase C completed with `optimal_params.json`
- SGLang server running at `192.168.0.36:30000` with Qwen3-VL-4B loaded
- Verify: `curl -s http://192.168.0.36:30000/v1/models | python3 -m json.tool`

### Execution

```bash
poetry run python scripts/calibration_orchestrator.py \
    --phase micro --n-trials 100 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_CAL \
    --output-dir ./results/calibration_micro_v2 \
    --timeout 300 --agent-mode multimode --seed 42 \
    --best-macro ./results/calibration_macro_v2/optimal_params.json \
    --baseline-dir ./results/baseline_v2
```

**Trials**: 100 total, in batches of 6. Each trial processes 75 APKs with multimode (70% LLM / 30% algorithm by default, but `llm_probability` is one of the tuned parameters).

**Expected duration**: 17 rounds x 9.4h = ~160 hours.

### Verification

```bash
# 1. All 100 trials completed
python3 -c "
import json
with open('results/calibration_micro_v2/trial_history.json') as f:
    trials = json.load(f)
print(f'{len(trials)} trials completed')
assert len(trials) == 100
"

# 2. Best score (should improve over macro-only)
python3 -c "
import json
with open('results/calibration_micro_v2/optimal_params.json') as f:
    micro = json.load(f)
with open('results/calibration_macro_v2/optimal_params.json') as f:
    macro = json.load(f)
print(f'Macro best: {macro[\"best_score\"]:.4f}')
print(f'Micro best: {micro[\"best_score\"]:.4f}')
improvement = (micro['best_score'] - macro['best_score']) / macro['best_score'] * 100
print(f'Improvement: {improvement:+.1f}%')
"

# 3. Verify all 24 parameters present in optimal params
python3 -c "
import json
with open('results/calibration_micro_v2/optimal_params.json') as f:
    data = json.load(f)
print(f'Parameter count: {len(data[\"best_params\"])}')
for k, v in sorted(data['best_params'].items()):
    print(f'  {k} = {v}')
"
```

**Gate**: 100 trials completed, best_score > 0.0, `optimal_params.json` contains all 24 parameters (8 macro fixed + 16 micro tuned).

### Resume and Troubleshooting

Same as Phase C — add `--resume` flag. Additional concern: SGLang server may need monitoring for memory leaks during 6.7 days of continuous use. If the server degrades, restart it between rounds.

---

## 4. Phase E — Validation (~5.6 hours)

### Purpose

Validate the calibrated parameters on the 30-APK holdout set (never seen during calibration). Run the same 3 tools x 3 repetitions as the baseline for direct statistical comparison.

### Execution

```bash
PARAMS=$(cat ./results/calibration_micro_v2/param_string.txt)

poetry run python scripts/baseline_docker.py \
    --tools "ape,fastbot,rvagent:multimode@${PARAMS}" \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_HOLDOUT \
    --output-dir ./results/validation_v2 \
    --n-containers 6 --timeout 300 --repetitions 3
```

**Tasks**: 3 tools x 30 APKs x 3 reps = 270 tasks.

**Expected duration**: ~5.6 hours.

### Verification

```bash
# 1. Row count
wc -l results/validation_v2/summary.csv
# → 271 (270 data rows + 1 header)

# 2. Statistical comparison: calibrated RVAgent vs baseline RVAgent
python3 -c "
import pandas as pd
from scipy import stats

baseline = pd.read_csv('results/baseline_v2/summary.csv')
validation = pd.read_csv('results/validation_v2/summary.csv')

# Filter to holdout APKs and rvagent tool
holdout_apks = set(validation['apk'].unique())
base_rv = baseline[(baseline['apk'].isin(holdout_apks)) & (baseline['tool'] == 'rvagent')]
val_rv = validation[validation['tool'] == 'rvagent']

print('=== Method Coverage ===')
print(f'Baseline mean: {base_rv[\"cov_method\"].mean():.2f}%')
print(f'Calibrated mean: {val_rv[\"cov_method\"].mean():.2f}%')

# Wilcoxon signed-rank test (paired by APK)
base_means = base_rv.groupby('apk')['cov_method'].mean()
val_means = val_rv.groupby('apk')['cov_method'].mean()
common = base_means.index.intersection(val_means.index)
stat, p = stats.wilcoxon(base_means[common], val_means[common])
print(f'Wilcoxon p-value: {p:.4f} ({\"significant\" if p < 0.05 else \"not significant\"})')

print()
print('=== MOP Errors ===')
print(f'Baseline mean: {base_rv[\"errors\"].mean():.2f}')
print(f'Calibrated mean: {val_rv[\"errors\"].mean():.2f}')
"
```

**Gate**: 270 data rows, 3 tools present. The calibrated RVAgent should show improvement over baseline on at least one metric (coverage or error reduction). Statistical significance (p < 0.05) is desired but not required for the gate — the holdout set has only 30 APKs, which may limit statistical power.

---

## 5. Parameter Application (Post-Execution)

After Phase E validates the calibrated parameters, apply them to the codebase:

1. **Update `parameter_space.py`**: Change default values in `MACRO_PARAMETERS` and `MICRO_PARAMETERS` to match `optimal_params.json`
2. **Update agent spec**: Delta spec for `openspec/specs/agent/spec.md` with new default values for `RVAgentConfig` fields (line 172-175)
3. **Update unit tests**: Any tests that assert default parameter values need updating
4. **Commit**: `closes #9` — the full calibration lifecycle is complete

This step is tracked as Tasks 23-24 and will be executed as an FF SDD change for the agent spec update.
