# Runbook: Calibration Execution Campaign

This is an **execution runbook**, not a code design. Each section corresponds to one calibration phase and is self-contained — future sessions load ONLY the relevant section. The full technical analysis (architecture, design decisions, validated assumptions) is in `docs/20260213_plano_calibracao.md`.

**Infrastructure reference**: The three host-side scripts (`preprocess_docker.py`, `baseline_docker.py`, `calibration_orchestrator.py`) are documented in `docs/20260213_plano_calibracao.md`. The original infrastructure design decisions (D1-D7) are preserved in Sections 3 and 8 of that document.

---

## 0. Prerequisites (All Phases)

### Environment

| Requirement | Value | Verification |
|-------------|-------|-------------|
| Machine | Desktop: 64 CPUs, 128GB RAM | `nproc && free -h` |
| Docker | Image `phtcosta/rvandroid:0.8.0` | `docker images \| grep rvandroid` |
| KVM | `/dev/kvm` accessible | `ls -la /dev/kvm` |
| rv-android | uv sync, all modules | `uv run python -c "from rv_agent_validation.calibration import ObjectiveFunction; print('OK')"` |
| SGLang (Phases D, E) | Server at `localhost:30000` | `curl -s http://localhost:30000/v1/models` |

RVSEC_HOME and Java 8 are **not required on the host**. The Docker image `phtcosta/rvandroid:0.8.0` contains all prerequisites (RVSEC_HOME, Java 8, rv-android, Android SDK). All preprocessing and execution happens inside containers.

### APK Source (Phase A only)

The 188 APKs from experiment 1 (`exp01_jca=True` in `apks_complete.csv`) are the starting point. On the desktop, they should all be in a single flat directory — no subdirectories. The CSV file for metadata:

```
# Laptop path (for reference)
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/apks_complete.csv

# Copy CSV to rv-android before transfer:
cp /path/to/apks_complete.csv modules/rv-agent-validation/data/apks_complete.csv
```

### Data paths (relative to rv-android root, used by Phases B-E)

```
DATA_DIR=modules/rv-agent-validation/data/calibration_dataset_v2
FILTER_ALL=modules/rv-agent-validation/data/all_valid_apks.txt
FILTER_CAL=modules/rv-agent-validation/data/calibration_set_v2.txt
FILTER_HOLDOUT=modules/rv-agent-validation/data/holdout_set_v2.txt
```

These files are created by Phase A. They do not exist until that phase completes.

### Container configuration

Each container runs with: 10 CPUs, 20GB RAM, `/dev/kvm` passthrough, staggered start (10s apart), `--no-window`. No Humanoid service needed.

For Phases D and E (multimode), containers also need `extra_hosts: ["host.docker.internal:host-gateway"]` to reach the SGLang server on the host.

---

## 1. Phase A — Docker Preprocessing (~2 hours)

### Purpose

Run all preprocessing (monitor generation, APK instrumentation, static analysis) inside Docker containers using `--skip-execution`. This merges the previous Phase 0 (APK filtering by SA tool success) into Phase A — filtering happens AFTER container preprocessing, based on which APKs produced all 3 SA files.

The Docker image `phtcosta/rvandroid:0.8.0` contains RVSEC_HOME, Java 8, and all tools for preprocessing. Instead of installing these on the host, we run rv-experiment inside containers with `--skip-execution` to perform only the preprocessing phases (monitors + instrumentation + SA), without launching emulators or executing testing tools.

### How it works

1. Extract 188 APK names from `apks_complete.csv` (`exp01_jca=True`)
2. `preprocess_docker.py` splits APKs across N containers (round-robin)
3. Each container runs rv-experiment with **entrypoint override** (the Docker entrypoint does not map `RV_SKIP_EXECUTION`):
   - `--tools monkey` (required by ExperimentConfig validation, but the tool never executes)
   - `--skip-execution` (skips the execution phase entirely — no emulator, no tool)
   - `--specification-set jca` (generates JCA monitors for instrumentation)
   - No skip flags for preprocessing — monitors, instrumentation, and SA all run
4. Each container's `out/` directory is mounted as a volume on the host
5. After all containers finish, `preprocess_docker.py` collects artifacts from all containers
6. Filtering: APKs that produced all 3 SA files (.gesda, .wtg, .reach) pass → `passed_apks.txt` (filenames only, e.g. `com.example.app.apk`, not full paths — must match `apks_complete.csv` `apk` column for `select_dataset.py` join)
7. `select_dataset.py` creates 75 calibration + 30 holdout split (stratified by category)
8. The assembled flat `calibration_dataset_v2/` directory is ready for Phases B-E

### Docker compose structure

The compose overrides the entrypoint because the frozen Docker image's `docker-entrypoint.sh` does not support `RV_SKIP_EXECUTION`:

```yaml
services:
  preprocess_0:
    image: phtcosta/rvandroid:0.8.0
    entrypoint: ["bash", "-c"]
    command:
      - >
        sleep ${RV_DELAY:-0} &&
        uv run rv-experiment run
        --tools monkey
        --skip-execution
        --specification-set jca
        --apks-dir /opt/rvsec/rv-android/apks
        --apks-filter /opt/rvsec/rv-android/filters/filter.txt
        --no-window
    volumes:
      - /path/to/original_apks:/opt/rvsec/rv-android/apks:ro
      - /path/to/output/preprocess_0_filter.txt:/opt/rvsec/rv-android/filters/filter.txt:ro
      - /path/to/output/preprocess_0:/opt/rvsec/rv-android/out
    devices: ["/dev/kvm:/dev/kvm"]
    deploy:
      resources:
        limits: { cpus: "10", memory: "20g" }
```

### Execution

```bash
# Step 1: Extract APK names from CSV
python3 -c "
import csv
with open('modules/rv-agent-validation/data/apks_complete.csv') as f:
    reader = csv.DictReader(f)
    apks = [r['filename'] for r in reader if r.get('exp01_jca') == 'True']
print(f'{len(apks)} APKs with exp01_jca=True')
with open('/tmp/exp01_jca_apks.txt', 'w') as f:
    for a in sorted(apks):
        f.write(a + '\n')
"

# Step 2: Run Docker preprocessing
uv run python scripts/preprocess_docker.py \
    --apks-dir /path/to/desktop/original_apks \
    --filter-file /tmp/exp01_jca_apks.txt \
    --output-dir ./results/preprocessing_v2 \
    --n-containers 6

# Step 3: Dataset selection (75 cal + 30 holdout)
uv run python scripts/select_dataset.py \
    --passed-apks ./results/preprocessing_v2/passed_apks.txt \
    --csv modules/rv-agent-validation/data/apks_complete.csv \
    --output-dir modules/rv-agent-validation/data \
    --cal-size 75 \
    --seed 42

# Step 4: Copy assembled dataset to data directory
cp -r ./results/preprocessing_v2/dataset/* \
    modules/rv-agent-validation/data/calibration_dataset_v2/
```

**Expected duration**: ~2 hours (instrumentation + SA on 188 APKs across 6 containers, no tool execution overhead).

### Expected outputs

```
results/preprocessing_v2/
├── docker-compose.yml                  # Generated compose file
├── preprocess_{0..5}_filter.txt        # Per-container APK filter files
├── preprocess_0/                       # Container 0 out/ volume
│   ├── monitors/                       # Generated JCA monitors (redundant across containers)
│   ├── instrumented_apks/              # Instrumented APKs
│   └── ...                             # SA output files
├── preprocess_1/ ... preprocess_5/     # Containers 1-5
├── passed_apks.txt                     # APKs with all 3 SA files (~105-107)
├── failed_apks.txt                     # APKs that failed (with reasons)
└── dataset/                            # Assembled flat directory
    ├── app1.apk                        # Instrumented APK
    ├── app1.apk.gesda                  # GESDA output
    ├── app1.apk.wtg                    # GATOR WTG output
    ├── app1.apk.reach                  # REACH output
    └── ...                             # ~105 APKs x 4 files = ~420 files

modules/rv-agent-validation/data/
├── calibration_dataset_v2/             # Copied from results/preprocessing_v2/dataset/
├── all_valid_apks.txt                  # All passing APKs (~105)
├── calibration_set_v2.txt              # 75 APKs for calibration (Phases C/D)
├── holdout_set_v2.txt                  # 30 APKs for validation (Phase E)
└── dataset_split.csv                   # Metadata + set assignment
```

### Verification

```bash
# 1. Check pass count (expect ~105-107)
wc -l results/preprocessing_v2/passed_apks.txt

# 2. Verify dataset split
wc -l modules/rv-agent-validation/data/calibration_set_v2.txt    # → 75
wc -l modules/rv-agent-validation/data/holdout_set_v2.txt        # → 30
wc -l modules/rv-agent-validation/data/all_valid_apks.txt        # → ~105

# 3. Verify each APK in dataset has its 3 SA files
for apk in modules/rv-agent-validation/data/calibration_dataset_v2/*.apk; do
    base=$(basename "$apk")
    for ext in gesda wtg reach; do
        if [ ! -s "${apk}.${ext}" ]; then
            echo "MISSING: ${base}.${ext}"
        fi
    done
done
```

**Gate**: `passed_apks.txt` has ≥100 APKs. `calibration_set_v2.txt` has 75 entries, `holdout_set_v2.txt` has 30 entries, `all_valid_apks.txt` has ≥100 entries. Every APK in `calibration_dataset_v2/` has matching `.gesda`, `.wtg`, `.reach` files.

---

## 2. Phase B — Baseline (~18.4 hours)

### Purpose

Establish performance baselines for 3 tools (APE, FastBot, RVAgent:pure_algorithm) on all 105 APKs with 3 repetitions. The key output is `BASELINE_MAX_ERRORS` — the maximum average error count across tools — which normalizes the error component of the objective function in Phases C and D.

### Execution

```bash
./scripts/run_phase_b.sh
# Or manually:
uv run python scripts/baseline_docker.py \
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
│   ├── tasks.json                        # Completed tasks
│   └── summary.csv                       # Per-batch results
├── batch_1/batch_1/ ...
└── batch_5/batch_5/ ...
```

### Verification

```bash
uv run python scripts/verify_phase.py b --results-dir ./results/baseline_v2
```

Manual checks:
```bash
# 1. Compute BASELINE_MAX_ERRORS
python3 -c "
import pandas as pd
df = pd.read_csv('results/baseline_v2/summary.csv')
max_errors = df.groupby('tool')['errors'].mean().max()
print(f'BASELINE_MAX_ERRORS = {max_errors:.2f}')
"
```

**Gate**: All 6 batch summaries exist, aggregated CSV has 945 data rows, 3 tools present, BASELINE_MAX_ERRORS is a finite positive number. Record the value — it is needed for Phases C and D.

### Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Container exits with code 137 | OOM kill (20GB exceeded) | Check which APK caused it; consider excluding or reducing timeout |
| `summary.csv` has fewer rows than expected | Some APKs failed | Check `tasks.json` for failed entries; restart container to retry |
| `aggregated_summary.csv` missing | Script interrupted before aggregation | Run: `uv run python -c "from baseline_docker import aggregate_summaries; ..."` |
| Emulator boot timeout | KVM contention at startup | Increase `RV_DELAY` between containers |

### Resume (if interrupted)

Each container uses `RV_EXPERIMENT_NAME=batch_{N}`, enabling rv-experiment's task-level resume. Re-run the same command — completed tasks will be skipped automatically. No `--resume` flag is needed; `baseline_docker.py` does not accept one.

---

## 3. Phase C — Macro Calibration (~122 hours / 5.1 days)

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
./scripts/run_phase_c.sh
# Or manually:
uv run python scripts/calibration_orchestrator.py \
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
├── ...                                   # Up to round-14
├── trial_0/trial_0/summary.csv           # Per-trial results
├── ...                                   # Up to trial_79
├── optimal_params.json                   # Best parameters + score
├── param_string.txt                      # DSL string for --tools
└── trial_history.json                    # All trial results
```

### Verification

```bash
uv run python scripts/verify_phase.py c --results-dir ./results/calibration_macro_v2
```

**Gate**: 80 trials completed, best_score > 0.0, convergence visible (last 20 trials score higher than first 20 on average), `optimal_params.json` and `param_string.txt` exist.

### Resume (if interrupted)

```bash
# Same command, add --resume
uv run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 80 --n-containers 6 \
    ... (same args) ... \
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

## 4. Phase D — Micro Calibration (~160 hours / 6.7 days)

### Purpose

Fine-tune 16 additional parameters while keeping the 8 macro parameters fixed at their optimal values from Phase C. Uses `multimode` agent mode, which requires the SGLang server (Qwen3-VL-4B).

### Prerequisites (in addition to Section 0)

- Phase C completed with `optimal_params.json`
- SGLang server running at `localhost:30000` with Qwen3-VL-4B loaded
- Verify: `curl -s http://localhost:30000/v1/models | python3 -m json.tool`

### SGLang server lifecycle

Start the SGLang server before Phase D using the existing docker-compose:

```bash
cd /path/to/rvsec-vision-llm
docker compose up -d
# Wait for health check to pass (~30s)
docker compose ps  # Status should be "healthy"
curl -s http://localhost:30000/v1/models
```

Keep running for Phase E (also uses multimode). Stop after Phase E completes:
```bash
docker compose down
```

### Execution

```bash
./scripts/run_phase_d.sh
# Or manually:
uv run python scripts/calibration_orchestrator.py \
    --phase micro --n-trials 100 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_CAL \
    --output-dir ./results/calibration_micro_v2 \
    --timeout 300 --agent-mode multimode --seed 42 \
    --best-macro ./results/calibration_macro_v2/optimal_params.json \
    --baseline-dir ./results/baseline_v2 \
    --sglang-url http://host.docker.internal:30000/v1
```

`--sglang-url` injects `llm_base_url` into the tool spec so containers can reach the SGLang server via `host.docker.internal`. The compose file includes `extra_hosts: ["host.docker.internal:host-gateway"]` to resolve this hostname on Linux.

**Trials**: 100 total, in batches of 6. Each trial processes 75 APKs with multimode (70% LLM / 30% algorithm by default, but `llm_probability` is one of the tuned parameters).

**Expected duration**: 17 rounds x 9.4h = ~160 hours.

### Verification

```bash
uv run python scripts/verify_phase.py d \
    --results-dir ./results/calibration_micro_v2 \
    --macro-dir ./results/calibration_macro_v2
```

**Gate**: 100 trials completed, best_score > 0.0, `optimal_params.json` contains all 24 parameters (8 macro fixed + 16 micro tuned).

### Resume and Troubleshooting

Same as Phase C — add `--resume` flag. Additional concern: SGLang server may need monitoring for memory leaks during 6.7 days of continuous use. If the server degrades, restart it between rounds.

---

## 5. Phase E — Validation (~5.6 hours)

### Purpose

Validate the calibrated parameters on the 30-APK holdout set (never seen during calibration). Run the same 3 tools x 3 repetitions as the baseline for direct statistical comparison.

### Prerequisites (in addition to Section 0)

- Phase D completed with `param_string.txt`
- SGLang server running at `localhost:30000` (the calibrated RVAgent uses multimode)

### Execution

```bash
./scripts/run_phase_e.sh
# Or manually:
PARAMS=$(cat ./results/calibration_micro_v2/param_string.txt)

uv run python scripts/baseline_docker.py \
    --tools "ape,fastbot,rvagent:multimode@${PARAMS}" \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_HOLDOUT \
    --output-dir ./results/validation_v2 \
    --n-containers 6 --timeout 300 --repetitions 3 \
    --sglang-url http://host.docker.internal:30000/v1
```

`--sglang-url` is required because the calibrated RVAgent uses multimode, which needs `llm_base_url` to reach the SGLang server. The script injects it into the tool spec and adds `extra_hosts` to the compose.

**Tasks**: 3 tools x 30 APKs x 3 reps = 270 tasks.

**Expected duration**: ~5.6 hours.

### Verification

```bash
uv run python scripts/verify_phase.py e \
    --results-dir ./results/validation_v2 \
    --baseline-dir ./results/baseline_v2
```

Manual statistical comparison:
```bash
python3 -c "
import pandas as pd
from scipy import stats

baseline = pd.read_csv('results/baseline_v2/summary.csv')
validation = pd.read_csv('results/validation_v2/summary.csv')

# Filter to holdout APKs and rvagent tool
holdout_apks = set(validation['apk'].unique())
base_rv = baseline[(baseline['apk'].isin(holdout_apks)) & (baseline['tool'].str.startswith('rvagent'))]
val_rv = validation[validation['tool'].str.startswith('rvagent')]

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

## 6. Parameter Application (Post-Execution)

After Phase E validates the calibrated parameters, apply them to the codebase:

1. **Update `parameter_space.py`**: Change default values in `MACRO_PARAMETERS` and `MICRO_PARAMETERS` to match `optimal_params.json`
2. **Update agent spec**: Delta spec for `openspec/specs/agent/spec.md` with new default values for `RVAgentConfig` fields
3. **Update unit tests**: Any tests that assert default parameter values need updating
4. **Commit**: `closes #9` — the full calibration lifecycle is complete

This step is tracked as Tasks 25-27 and will be executed as an FF SDD change for the agent spec update.
