# Runbook: Calibration Execution Campaign

This is an **execution runbook**, not a code design. Each section corresponds to one calibration phase and is self-contained — future sessions load ONLY the relevant section. The full technical analysis (architecture, design decisions, validated assumptions) is in `docs/20260213_plano_calibracao.md`.

**Infrastructure reference**: The three host-side scripts (`preprocess_docker.py`, `baseline_docker.py`, `calibration_orchestrator.py`) are documented in `docs/20260213_plano_calibracao.md`. The original infrastructure design decisions (D1-D7) are preserved in Sections 3 and 8 of that document.

---

## 0. Prerequisites (All Phases)

### Timeout

`TIMEOUT_SECS` is a placeholder — the optimal value will be determined from the speed test (`docker-compose.speed-test.yml`), which compares 5 APKs at 1800s vs baseline at 300s. Analysis of per-APK coverage curves will identify the plateau ("knee point"). Expected range: 600-900s (10-15 min). Replace all `TIMEOUT_SECS` references in this document once determined.

### Phase Structure

```
A  → Preprocessing (188 APKs, ~2h)
B  → Baseline (ALL valid APKs, 3 tools × 3 reps) — establishes reference + BASELINE_MAX_ERRORS
C0 → Pre-macro (20 APKs, 30 trials, 11 MACRO params) — validates calibration approach
D0 → Pre-micro (20 APKs, 40 trials, 26 MICRO params, SGLang) — validates multimode calibration
     [evaluate: did pre-cal improve over baseline defaults?]
     [if yes: update defaults, proceed to full calibration]
C  → Full macro (cal APKs, 80 trials, 11 MACRO params)
D  → Full micro (cal APKs, 100 trials, 26 MICRO params, SGLang)
E  → Validation (holdout APKs, 37 params, SGLang)
```

**Rationale**: Baseline runs first because (1) it establishes the real `BASELINE_MAX_ERRORS` for the objective function (not an estimate from a 20-APK subset), (2) it provides empirical evidence of current performance before investing in calibration, and (3) it eliminates the B0 phase entirely. The pre-calibration (C0/D0) then validates whether Optuna can find params better than defaults — if not, the methodology needs revision before committing to the full campaign.

**Dataset sizing**: The number of APKs for each phase depends on Phase A results. All APKs that produce both an instrumented `.apk` and an analysis `.json` are valid. The cal/holdout split is decided after Phase B, based on the actual dataset size.

### Parameter forwarding chain

Calibration parameters flow: orchestrator → docker-compose env vars → docker-entrypoint → rv-experiment CLI `--tools` → ToolFactory → `build_agent_config_dict()` → RVAgentConfig → scorers/strategy code.

The bottleneck is `build_agent_config_dict()` in `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py` which uses explicit whitelists (`llm_params`, `strategy_params`, `scorer_params`) to forward parameters. Any new parameter added to `RVAgentConfig` MUST also be added to the appropriate whitelist, otherwise it will be silently dropped (the tool_config dict has the value, but it never reaches RVAgentConfig).

**All 37 calibration parameters** (11 MACRO + 26 MICRO from `parameter_space.py`) must appear in the whitelists. See Task 20a for the C0-era fix that added 15 missing params.

### Environment

| Requirement | Value | Verification |
|-------------|-------|-------------|
| Machine | Desktop: 64 CPUs, 128GB RAM | `nproc && free -h` |
| Docker | Image `phtcosta/rvandroid:0.8.0` (rebuilt from `modules` branch) | `docker images \| grep "rvandroid.*0.8.0"` |
| KVM | `/dev/kvm` accessible | `ls -la /dev/kvm` |
| rv-android | uv sync, all modules | `uv run python -c "from rv_agent_validation.calibration import ObjectiveFunction; print('OK')"` |
| SGLang (Phases D, E) | Server at `localhost:30000` | `curl -s http://localhost:30000/v1/models` |

RVSEC_HOME and Java are **not required on the host**. The Docker image contains all prerequisites (RVSEC_HOME, Java 25, rv-android, Android SDK). All preprocessing and execution happens inside containers.

**Known issue**: Docker image 0.8.0 uses Java 25 (was Java 11 in 0.0.1). This causes dex2jar v2.4 to fail on 1 APK (`com.danielme.muspyforandroid_3`). Java 8 `rt.jar` (needed by GATOR/Soot for JDK class resolution) is bundled separately in the image and not affected by the JDK version change.

**IMPORTANT**: The Docker image `phtcosta/rvandroid:0.8.0` MUST be rebuilt from the current `modules` branch before calibration. The existing `0.8.0` image predates gh26 (exploration strategy), gh18 (error detection), and gh27 (unified static analysis — single `.json` output instead of `.gesda/.wtg/.reach`). Rebuilding overwrites the tag with current code. See Task 13a for the rebuild procedure.

### Data paths (relative to rv-android root)

**Reference data** (committed, always available):
```
APKS_CSV=modules/rv-agent-validation/data/apks_complete.csv       # Master catalog (253 APKs, all metadata)
FILTER_JCA=modules/rv-agent-validation/data/exp01_jca_apks.txt    # 188 JCA APKs (Phase A input)
```

**APK source** (Phase A only — desktop path, flat directory, no subdirectories):
```
APKS_DIR=/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS
```

**Created by Phase A** (do not exist until Phase A completes):
```
DATA_DIR=modules/rv-agent-validation/data/calibration_dataset_v2
FILTER_ALL=modules/rv-agent-validation/data/all_valid_apks.txt
FILTER_CAL=modules/rv-agent-validation/data/calibration_set_v2.txt
FILTER_HOLDOUT=modules/rv-agent-validation/data/holdout_set_v2.txt
```

### Container configuration

Each container runs with: 10 CPUs, 20GB RAM, `/dev/kvm` passthrough, staggered start (10s apart), `--no-window`. No Humanoid service needed.

For Phases D and E (multimode), containers also need `extra_hosts: ["host.docker.internal:host-gateway"]` to reach the SGLang server on the host.

---

## 1. Phase A — Docker Preprocessing (~2 hours)

### Purpose

Run all preprocessing (monitor generation, APK instrumentation, static analysis) inside Docker containers using `--skip-execution`. This merges the previous Phase 0 (APK filtering by SA tool success) into Phase A — filtering happens AFTER container preprocessing, based on which APKs produced the unified analysis JSON file.

The Docker image (rebuilt from `modules` branch as `phtcosta/rvandroid:0.8.0`) contains RVSEC_HOME, Java 25, and all tools for preprocessing. Instead of installing these on the host, we run rv-experiment inside containers with `--skip-execution` to perform only the preprocessing phases (monitors + instrumentation + SA), without launching emulators or executing testing tools.

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
6. Filtering: APKs that produced the analysis JSON file (`.json`) pass → `passed_apks.txt` (filenames only, e.g. `com.example.app.apk`, not full paths — must match `apks_complete.csv` `apk` column)
7. Failed APKs are retried with extended timeout (task 15g) to recover timeout-only failures
8. The assembled flat dataset directory (instrumented APKs + SA JSONs) is copied to `calibration_dataset_v2/` (task 16)
9. Cal/holdout split is created later (task 25), after baseline validates the dataset

### Docker compose structure

The compose overrides the entrypoint because the Docker image's `docker-entrypoint.sh` does not support `RV_SKIP_EXECUTION`:

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
        --output-dir /opt/rvsec/rv-android/out
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

**IMPORTANT**: `--output-dir /opt/rvsec/rv-android/out` is required. Without it, rv-experiment writes to `results/cli_experiment_...` inside the container (a path not visible on the host via the volume mount).

### Execution

```bash
# Run Docker preprocessing (filter file is committed in the repo)
uv run python scripts/preprocess_docker.py \
    --apks-dir /pedro/desenvolvimento/RV_ANDROID/NOVO/APKS \
    --filter-file modules/rv-agent-validation/data/exp01_jca_apks.txt \
    --output-dir ./results/preprocessing_v2 \
    --n-containers 6
```

Dataset selection and copy are separate tasks (16 and 25) — see tasks.md.

**Expected duration**: ~2 hours (instrumentation + SA on 188 APKs across 6 containers, no tool execution overhead).

### Known SA failure categories

Phase A first run (125/188 passed) revealed three categories of SA failure:

1. **Missing Android platforms** (~20-25 APKs): APKs targeting API levels 10-18 fail because the Docker image only has platforms 19-35. The GATOR wrapper tries to install via `sdkmanager` at `$ANDROID_HOME/tools/bin/sdkmanager` (hardcoded path that doesn't exist in the image). **Fix**: add platforms 10-18 to `docker/android/Dockerfile` + create sdkmanager symlink.

2. **StackOverflowError in RvsecAnalysisClient** (~15-20 APKs): `collectEventHandlers()` and `collectWidgets()` recursively traverse GATOR's GUI node tree without cycle detection. Some APKs produce cyclic node graphs causing infinite recursion. Java crashes with `StackOverflowError`, exit code is 0, no JSON produced. **Fix**: add `Set<NNode> visited` parameter to prevent revisiting nodes.

3. **Soot crash / Timeout** (~15-20 APKs): Soot `InternalTypingException` on certain bytecode patterns, or APK too complex for the 600s GATOR timeout. **No fix** — inherent limitation.

After applying fixes 1 and 2, expect ~145-150 passing APKs (up from 125).

### Expected outputs

```
results/preprocessing_v2/
├── docker-compose.yml                  # Generated compose file
├── preprocess_{0..5}_filter.txt        # Per-container APK filter files
├── preprocess_0/                       # Container 0 out/ volume
│   ├── monitors/                       # Generated JCA monitors (redundant across containers)
│   ├── instrumented_apks/              # Instrumented APKs + SA JSON files
│   └── experiment_completion.json      # Completion marker
├── preprocess_1/ ... preprocess_5/     # Containers 1-5
├── passed_apks.txt                     # APKs with analysis JSON (~145-150)
├── failed_apks.txt                     # APKs that failed (with reasons)
└── dataset/                            # Assembled flat directory
    ├── app1.apk                        # Instrumented APK
    ├── app1.apk.json                   # Unified analysis (reachability, windows, transitions)
    └── ...                             # ~145 APKs x 2 files = ~290 files

```

### Verification

```bash
# 1. Check pass count (expect ~145-150 after fixes, was 125 before)
wc -l results/preprocessing_v2/passed_apks.txt

# 2. Verify each APK in dataset has its analysis JSON
for apk in results/preprocessing_v2/dataset/*.apk; do
    base=$(basename "$apk")
    if [ ! -s "${apk}.json" ]; then
        echo "MISSING: ${base}.json"
    fi
done
```

**Gate**: `passed_apks.txt` has ≥140 APKs (improvement from 125 in first run). Every APK in `dataset/` has a matching `.json` analysis file. Cal/holdout split is deferred to task 25.

---

## 1b. Pre-Calibration Phases (C0 → D0)

### Purpose

Run a reduced-scale calibration on 20 APKs before the full campaign. This validates that Optuna can find parameters better than current defaults (using the real `BASELINE_MAX_ERRORS` from Phase B), determines if the trial counts and objective function work, and produces better starting defaults for the full campaign.

**Prerequisite**: Phase B (baseline) must be complete — provides `BASELINE_MAX_ERRORS` for the objective function. B0 is not needed because the full baseline already exists.

**APK selection**: 20 APKs drawn from the valid dataset, stratified by category. Saved as `precal_set.txt`.

**No new scripts** — pre-calibration reuses `calibration_orchestrator.py` with `--filter-file precal_set.txt` and fewer trials.

### Phase C0 — Pre-macro (30 trials, 11 MACRO params)

```bash
uv run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 30 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file modules/rv-agent-validation/data/precal_set.txt \
    --output-dir ./results/precal_macro \
    --timeout TIMEOUT_SECS --agent-mode pure_algorithm --seed 42 \
    --baseline-dir ./results/baseline_v2
```

**Trials**: 30 total. Each trial processes 20 APKs. **Duration**: ~5.5h (600s) to ~8.3h (900s).

### Phase D0 — Pre-micro (40 trials, 26 MICRO params, SGLang)

```bash
uv run python scripts/calibration_orchestrator.py \
    --phase micro --n-trials 40 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file modules/rv-agent-validation/data/precal_set.txt \
    --output-dir ./results/precal_micro \
    --timeout TIMEOUT_SECS --agent-mode multimode --seed 42 \
    --best-macro ./results/precal_macro/optimal_params.json \
    --baseline-dir ./results/baseline_v2 \
    --sglang-url http://host.docker.internal:30000/v1
```

**Trials**: 40 total. Each trial processes 20 APKs with multimode. **Duration**: ~7.4h (600s) to ~11.1h (900s).

### Decision gate after pre-cal

Compare pre-cal best score against the baseline defaults score on the same 20 APKs. If pre-cal shows meaningful improvement → proceed to full calibration with pre-cal values as starting defaults. If not → investigate objective function, parameter ranges, or methodology before committing to the full campaign.

### How pre-cal feeds into the full campaign

1. C0 optimal values become starting defaults for Phase C. Ranges optionally narrowed to +/-30% around C0 best values (clamped to original bounds).
2. D0 optimal values become starting defaults for Phase D. Same narrowing applies.
3. Update `parameter_space.py` defaults from pre-cal results before full calibration.

### Verification

```bash
# C0: verify convergence (last 10 trials avg > first 10 avg)
python3 -c "
import json
with open('results/precal_macro/trial_history.json') as f:
    trials = json.load(f)
scores = [t['score'] for t in trials]
print(f'First 10 avg: {sum(scores[:10])/10:.4f}')
print(f'Last 10 avg: {sum(scores[-10:])/10:.4f}')
"

# D0: verify optimal_params.json has 37 params (11 macro + 26 micro)
python3 -c "
import json
with open('results/precal_micro/optimal_params.json') as f:
    data = json.load(f)
print(f'Parameters: {len(data[\"best_params\"])} (expected 37)')
"
```

**Gate**: C0 shows convergence trend. D0 produces `optimal_params.json` with 37 parameters.

---

## 2. Phase B — Baseline

### Purpose

Establish performance baselines for 3 tools (APE, FastBot, RVAgent:pure_algorithm) on ALL valid APKs from Phase A, with 3 repetitions. This is the **first execution phase** after preprocessing — it runs with current defaults (no calibration yet). The key output is `BASELINE_MAX_ERRORS` — the maximum average error count across tools — which normalizes the error component of the objective function in Phases C0, C, and D.

### Execution

```bash
./scripts/run_phase_b.sh
# Or manually:
uv run python scripts/baseline_docker.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_ALL \
    --output-dir ./results/baseline_v2 \
    --n-containers 6 --timeout TIMEOUT_SECS --repetitions 3
```

**Tasks**: 3 tools × N APKs × 3 reps (N = number of valid APKs from Phase A, expected ~145-150). Split across 6 containers.

**Expected duration**: Depends on TIMEOUT_SECS and N. At N=150 and 600s: ~37h. At 900s: ~56h.

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

**Gate**: All 6 batch summaries exist, aggregated CSV has 3×N×3 data rows, 3 tools present, BASELINE_MAX_ERRORS is a finite positive number. Record the value — it is needed for Phases C0, C, D0, and D.

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

## 3. Phase C — Macro Calibration

### Purpose

Tune 11 high-impact parameters (scorer weights, exploration settings, and flow-altering thresholds) using Optuna's TPESampler with batch parallelism. Each trial evaluates one parameter set by running RVAgent on the calibration APK subset. Starting defaults come from Phase C0 pre-calibration (if it showed improvement) or from current code defaults.

### Parameters tuned

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `mop_direct_score` | 500.0 | 300-700 | MOP method prioritization |
| `wtg_guided_score` | 150.0 | 50-300 | WTG navigation guidance |
| `unsaturated_bonus` | 100.0 | 50-150 | State diversity bonus |
| `max_re_enables` | 6 | 3-15 | Successor exploration depth |
| `ui_coverage_threshold` | 0.9 | 0.7-1.0 | Re-enable trigger threshold |
| `stochastic_probability` | 0.15 | 0.05-0.4 | Exploration randomness |
| `strength_weight` | 50.0 | 25-100 | Historical action success |
| `visitation_penalty_factor` | -15.0 | -25 to -5 | Over-visited penalty |
| `backtrack_saturation_threshold` | 0.8 | 0.5-1.0 | Backtrack trigger threshold (gh26) |
| `coverage_density_weight` | 200.0 | 50-400 | Coverage density scoring (gh26) |
| `error_detection_confidence` | 0.7 | 0.3-0.95 | Error detection threshold (gh18) |

### Execution

```bash
./scripts/run_phase_c.sh
# Or manually:
uv run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 80 --n-containers 6 \
    --data-dir $DATA_DIR \
    --filter-file $FILTER_CAL \
    --output-dir ./results/calibration_macro_v2 \
    --timeout TIMEOUT_SECS --agent-mode pure_algorithm --seed 42 \
    --baseline-dir ./results/baseline_v2
```

**Trials**: 80 total, in batches of 6. Each trial processes the calibration APK subset. Starting defaults from C0 pre-calibration (or current defaults if C0 was skipped).

**Expected duration**: Depends on TIMEOUT_SECS. At 600s: ~167h. At 900s: ~250h.

**Objective function**: 30% method coverage + 20% normalized MOP errors + 50% UI coverage. Weights are configurable via `--coverage-weight`, `--errors-weight`, `--ui-coverage-weight` CLI params (default 0.30/0.20/0.50).

**Error normalization**: Log-scaled with max-APK reference. `compute_baseline_max_errors()` computes `groupby('apk')['errors'].mean().max()` — the maximum per-APK average error count across all tools. The normalization formula is `min(log(1 + avg_errors) / log(1 + baseline_max_errors) * 100, 100)`. This provides continuous gradient across the error range without saturation in practice (saturation only at avg_errors >= max-APK errors, which is impossible as a dataset mean).

**Rationale**: The original linear normalization (`avg_errors / mean_per_tool * 100`) saturated at avg_errors >= 1.58 (the max tool mean across 167 APKs), providing zero gradient to Optuna on 40% of the score. Log normalization with a higher reference (max-APK ≈ 22.33) eliminates this problem. C0 analysis (Task 21a) showed MOP errors and method coverage are insensitive to MACRO params (14/20 APKs std=0 for errors, most std<3% for coverage), while UI element coverage varies 20-83% per APK. Weights rebalanced from 40/40/20 to 30/20/50 to give Optuna a stronger optimization signal on the responsive metric.

### Scoring architecture and parameter ranges

All 9 scorers in `ActionRanker` are composed via **pure additive sum**: `total = sum(scorer.score() for scorer in scorers)`. The action with the highest total is selected (deterministic) or used as Gumbel-max base (stochastic, 15% probability).

**Typical score contributions per scorer** (at default parameter values):

| Scorer | Max contribution | Condition for max |
|--------|-----------------|-------------------|
| MopScorer | +500 | Action directly reaches MOP method |
| GradualDecayScorer | +200 | First visit to element (decays with visits) |
| CoverageDensityScorer | +200 | Destination state fully untested |
| WtgScorer | +150 | WTG suggests this action for navigation |
| SaturationScorer | +100 | Current state fully unsaturated (state-level) |
| ComponentPriorityScorer | +50 | Button, input, or navigation element |
| StrengthScorer | +65 | Perfect historical success + max reward |
| VisitationPenaltyScorer | -60 | State visited 50+ times (state-level, log-based) |
| SystemElementFilter | -5000 | systemui package (effectively blocks) |

**Realistic composite range**: [-60, +1225]. MopScorer dominates at 41% of the max.

**Range widening rationale**: C0 analysis showed near-zero variation in scores because some secondary scorers are capped too low relative to MOP magnitude — Optuna cannot explore configurations where coverage exploration or historical success meaningfully compete with MOP targeting. Since the objective function gives coverage and errors equal weight (40% each), the parameter ranges should allow coverage-favoring strategies. See Task 20b for the 11 widened ranges and rationale.

**Dead code note**: 3 MICRO params (`mop_nav_weight`, `max_short_term_iterations`, `llm_max_retries`) are defined in `RVAgentConfig` but never consumed at runtime. They must be excluded from D0 calibration or wired into the code first. See Task 20b.

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

## 4. Phase D — Micro Calibration

### Purpose

Fine-tune 26 additional parameters while keeping the 11 macro parameters fixed at their optimal values from Phase C. Uses `multimode` agent mode, which requires the SGLang server (Qwen3-VL-4B). Starting defaults come from Phase D0 pre-calibration (if it showed improvement) or from current code defaults.

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
    --timeout TIMEOUT_SECS --agent-mode multimode --seed 42 \
    --best-macro ./results/calibration_macro_v2/optimal_params.json \
    --baseline-dir ./results/baseline_v2 \
    --sglang-url http://host.docker.internal:30000/v1
```

`--sglang-url` injects `llm_base_url` into the tool spec so containers can reach the SGLang server via `host.docker.internal`. The compose file includes `extra_hosts: ["host.docker.internal:host-gateway"]` to resolve this hostname on Linux.

**Trials**: 100 total, in batches of 6. Each trial processes the calibration APK subset with multimode (70% LLM / 30% algorithm by default, but `llm_probability` is one of the tuned parameters). Starting defaults from D0 pre-calibration (or current defaults if D0 was skipped).

**Expected duration**: Depends on TIMEOUT_SECS. At 600s: ~208h. At 900s: ~313h.

### Verification

```bash
uv run python scripts/verify_phase.py d \
    --results-dir ./results/calibration_micro_v2 \
    --macro-dir ./results/calibration_macro_v2
```

**Gate**: 100 trials completed, best_score > 0.0, `optimal_params.json` contains all 37 parameters (11 macro fixed + 26 micro tuned).

### Resume and Troubleshooting

Same as Phase C — add `--resume` flag. Additional concern: SGLang server may need monitoring for memory leaks during continuous use. If the server degrades, restart it between rounds.

---

## 5. Phase E — Validation

### Purpose

Validate the 37 calibrated parameters on the holdout set (never seen during calibration). Run the same 3 tools × 3 repetitions as the baseline for direct statistical comparison.

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
    --n-containers 6 --timeout TIMEOUT_SECS --repetitions 3 \
    --sglang-url http://host.docker.internal:30000/v1
```

`--sglang-url` is required because the calibrated RVAgent uses multimode, which needs `llm_base_url` to reach the SGLang server. The script injects it into the tool spec and adds `extra_hosts` to the compose.

**Tasks**: 3 tools × H holdout APKs × 3 reps (H determined by task 25 split).

**Expected duration**: Depends on TIMEOUT_SECS and H.

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

**Gate**: 3×H×3 data rows, 3 tools present. The calibrated RVAgent should show improvement over baseline on at least one metric (coverage or error reduction). Statistical significance (p < 0.05) is desired but not required for the gate — a small holdout set may limit statistical power.

---

## 6. Parameter Application (Post-Execution)

After Phase E validates the 37 calibrated parameters, apply them to the codebase:

1. **Update `parameter_space.py`**: Change default values in `MACRO_PARAMETERS` (11) and `MICRO_PARAMETERS` (26) to match `optimal_params.json`
2. **Update agent spec**: Delta spec for `openspec/specs/agent/spec.md` with new default values for `RVAgentConfig` fields
3. **Update unit tests**: Any tests that assert default parameter values need updating
4. **Commit**: `closes #9` — the full calibration lifecycle is complete

This step is tracked as Tasks 32-34 and will be executed as an FF SDD change for the agent spec update.

---

## 7. Parameter Importance Classification

Each parameter has an importance rating (1-5) to enable fast calibration strategies. The full campaign tunes all 37 parameters; a fast calibration can focus on importance >= 4 (12 params) or importance >= 3 (24 params).

| Importance | Count | Description | Fast calibration strategy |
|------------|-------|-------------|--------------------------|
| 5 (Critical) | 5 | Controls exploration direction, primary scoring | Always calibrate |
| 4 (High) | 7 | Significantly affects exploration efficiency | Calibrate in fast mode |
| 3 (Medium) | 12 | Noticeable impact on specific subsystems | Fix at defaults in fast mode |
| 2 (Low) | 11 | Fine-tuning within a subsystem | Fix at defaults |
| 1 (Minimal) | 2 | Very narrow range, negligible effect | Fix at defaults |

### Importance 5 — Critical (5 params)

| Parameter | Phase | Rationale |
|-----------|-------|-----------|
| `mop_direct_score` | MACRO | Primary signal driving agent toward monitored operations |
| `max_re_enables` | MACRO | Directly controls DFS depth vs breadth |
| `stochastic_probability` | MACRO | Exploration/exploitation balance — small changes dramatically alter behavior |
| `visitation_penalty_factor` | MACRO | Anti-loop mechanism — wrong value = stuck in loops or premature abandonment |
| `llm_probability` | MICRO | THE key multimode parameter — LLM vs algorithm ratio |

### Importance 4 — High (7 params)

| Parameter | Phase | Rationale |
|-----------|-------|-----------|
| `wtg_guided_score` | MACRO | Important for exploration breadth via WTG graph |
| `unsaturated_bonus` | MACRO | Drives state diversity in exploration |
| `ui_coverage_threshold` | MACRO | Controls when successors get re-enabled |
| `strength_weight` | MACRO | Controls exploitation of historically successful actions |
| `backtrack_saturation_threshold` | MACRO | Controls when exploration pivots via backtracking |
| `mop_transitive_score` | MICRO | Secondary MOP signal — still significant for coverage |
| `llm_temperature` | MICRO | Validated as critical for tool calling accuracy |

### Fast Calibration Option (importance >= 4)

12 parameters: 9 MACRO + 3 MICRO. Estimate: ~60% faster than full calibration (12 vs 37 params reduces Optuna's search space dimension by 68%). Remaining 25 parameters stay at their defaults.

Use `get_parameters_by_importance(min_importance=4)` in `parameter_space.py` to get this subset programmatically.
