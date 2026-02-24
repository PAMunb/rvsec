# Plan: Docker-Based Calibration Infrastructure

> **Note (2026-02-24)**: This plan covers the COMPLETED infrastructure phase (Tasks 1–6).
> Parameter counts (24) and test counts (35) below reflect the original infrastructure scope.
> Current values: 37 parameters (11 MACRO + 26 MICRO), 86 unit tests.
> See `tasks.md` for the full execution campaign (Tasks 13–27).

**GitHub Issue**: #9
**Workflow**: Quick Path (Analyze -> Fix -> Verify)
**Branch**: `modules` (current)
**Reference**: `docs/20260213_plano_calibracao.md` (Phase 0 ideation artifact — full technical design)
**Agent spec**: `openspec/specs/agent/spec.md` (line 127: "37 tunable parameters", line 221: "rv-agent-validation for calibration")

## Context

The calibration framework in rv-agent-validation tunes 24 parameters of the RVAgent exploration strategy across five phases (A through E), totaling ~306 hours of experiment execution. The current implementation uses Python-level parallelism: Optuna's `n_jobs=6` spawns six worker threads, each acquiring an emulator port from a thread-safe `EmulatorPool` (`calibration/emulator_pool.py`) and calling `CalibrationRunner.run_trial()` (`calibration/runner.py:80-142`) as a blocking subprocess. Each trial processes all 75 calibration APKs sequentially on a single emulator, taking approximately 8.75 hours.

This approach breaks when an Android emulator crashes — which happens frequently during long runs. The blocking `subprocess.run()` in the worker thread (runner.py:113) either hangs indefinitely or propagates the crash to the entire Python process, killing all six workers at once. There is no way to resume a partially-completed trial, so the 50 APKs processed before the crash are lost.

The rvsec-02 project (557 APKs, 10 tools, 25 days) proved that Docker container-level parallelism handles this reliably. Each container runs its own emulator in complete isolation. When a container crashes, only that container's current APK is lost (~7 minutes of work). The orchestration was intentionally simple — manual CSV updates and docker-compose commands — and that simplicity was an advantage.

This change adopts the rvsec-02 pattern for calibration Phases B through E. Two host-side Python scripts replace the existing in-process parallelism classes. The design decisions (trial-level vs APK-level parallelism, Optuna ask/tell API, container configuration, three-level resume strategy) are fully documented in the reference plan. From here, execution is mechanical.

---

## Validated Assumptions

Before writing this plan, every integration point was verified against the actual codebase. These validations ensure the plan can be implemented without surprises.

### A1: Optuna ask/tell API is compatible with `suggest_params()`

`suggest_params()` (parameter_space.py:275-295) takes an untyped `trial` parameter and calls `trial.suggest_float()` and `trial.suggest_int()`. Optuna's `study.ask()` returns a `Trial` object that supports these same methods — it is the same `Trial` class passed to `study.optimize()`'s objective function. No code changes needed in `parameter_space.py`.

```python
# This works — verified against Optuna ask/tell documentation
study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
trial = study.ask()                              # Returns Trial (not FrozenTrial)
params = suggest_params(trial, CalibrationPhase.MACRO)  # Calls trial.suggest_float/int — works
study.tell(trial.number, score)                  # Reports result back
```

### A2: `params_to_tool_spec()` produces the correct DSL format

`params_to_tool_spec()` (parameter_space.py:298-314) produces `"name=value,name=value,..."` with 4 decimal places for floats. The full tool spec becomes `rvagent:pure_algorithm@param1=val1,param2=val2`. The Docker entrypoint (`docker/rvandroid/docker-entrypoint.sh:22-24`) passes `RV_TOOLS` directly as `--tools $RV_TOOLS` to `rv-experiment run`. The end-to-end chain is validated:

```
params_to_tool_spec({"mop_direct_score": 350.0}) -> "mop_direct_score=350.0000"
f"rvagent:pure_algorithm@{spec}" -> "rvagent:pure_algorithm@mop_direct_score=350.0000"
entrypoint.sh: CMD="uv run rv-experiment run --tools rvagent:pure_algorithm@mop_direct_score=350.0000"
```

### A3: Parameter counts match

- MACRO_PARAMETERS (parameter_space.py:33-106): 8 parameters — `mop_direct_score`, `wtg_guided_score`, `unsaturated_bonus`, `max_re_enables`, `ui_coverage_threshold`, `stochastic_probability`, `strength_weight`, `visitation_penalty_factor`. All float/int. Verified by counting list items.
- MICRO_PARAMETERS (parameter_space.py:109-253): 16 parameters — all numeric (float/int). Verified by counting list items.
- Total: 24 parameters. Matches agent spec line 127 ("24 tunable parameters total").

### A4: `ObjectiveFunction.compute()` path resolution

`compute()` (objective.py:57-108) calls `_find_summary_csv()` which first checks `results_path / "summary.csv"` (line 174), then searches recursively. For the orchestrator, the call will be:

```python
results_dir = output_dir / f"trial_{trial_num}" / f"trial_{trial_num}"
score = objective_fn.compute(str(results_dir))
# _find_summary_csv checks results_dir/summary.csv — direct hit
```

The double nesting `trial_N/trial_N/` occurs because the host mounts `{output_dir}/trial_N/` as the container's `/opt/rvsec/rv-android/results`, and rv-experiment creates a subdirectory named after `RV_EXPERIMENT_NAME` (also `trial_N`) inside it.

### A5: `compute_baseline_max_errors()` reads `summary.csv`

`compute_baseline_max_errors()` (objective.py:220-252) reads `{baseline_dir}/summary.csv` (line 233). The baseline script must place the aggregated file at this exact path — naming it `summary.csv`, not `aggregated_summary.csv`, to avoid modifying `objective.py`. The per-batch files at `batch_0/batch_0/summary.csv` do not conflict with the root-level `summary.csv`. The method also requires a `tool` column (line 241: `summary.groupby('tool')['errors'].mean()`), which rv-platform's `ResultProcessorComponent` includes in all summary.csv files.

### A6: Docker compose structure follows existing pattern

`docker/docker-compose.parallel.yml` defines the production pattern: YAML anchors (`x-rvandroid`), per-service env var overrides via `<<: *rvandroid-env`, `/dev/kvm` device passthrough, per-container results volumes, `RV_DELAY` for staggered start, `RV_EXPERIMENT_NAME` for resume. The generated compose files must follow this exact structure.

Key difference from host-based parallel execution: inside Docker containers, each container has its own network namespace, so all containers use `RV_DEVICE_PORT=5554` (not staggered ports like the parallel.yml uses for host execution).

### A7: Entrypoint env var mapping

Verified against `docker/rvandroid/docker-entrypoint.sh`:

| Env Var | CLI Flag | Entrypoint Line | Used By |
|---------|----------|-----------------|---------|
| `RV_TOOLS` | `--tools` | 22-24 | Both scripts |
| `RV_EXPERIMENT_NAME` | `--name` | 82-84 | Both scripts |
| `RV_APKS_FILTER` | `--apks-filter` | 77-79 | Both scripts |
| `RV_TIMEOUTS` | `--timeout` | 27-29 | Both scripts |
| `RV_REPETITIONS` | `--repetitions` | 31-33 | Baseline only |
| `RV_NO_WINDOW` | `--no-window` | 41-45 | Both scripts |
| `RV_SKIP_MONITORS` | `--skip-monitors` | 59-61 | Both scripts |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` | 63-65 | Both scripts |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` | 67-69 | Both scripts |
| `RV_DELAY` | (sleep before exec) | 13-16 | Both scripts |
| `RV_DEVICE_PORT` | `--device-port` | 72-74 | Not needed (containers use 5554) |
| `RV_APKS_DIR` | `--apks-dir` | 36-38 | Not used (volume mount instead) |

---

## Known Limitations

### L1: No `prompt_version` categorical parameter

The reference plan (Section 6, Phase D) mentions "17 micro parameters (16 numeric + 1 categorical `prompt_version`)". However, `parameter_space.py` defines exactly 16 MICRO parameters, all numeric. There is no `suggest_categorical()` call in `suggest_params()`, and `params_to_tool_spec()` only handles `float` and `int` types (line 310-313).

If `prompt_version` calibration is needed in Phase D, it would require:
1. Adding a `ParameterDef` with `param_type="categorical"` to `MICRO_PARAMETERS`
2. Adding `suggest_categorical()` handling in `suggest_params()`
3. Adding string handling in `params_to_tool_spec()`

This is **out of scope** for this change. The orchestrator will work with the existing 16 numeric micro parameters. If `prompt_version` is needed, it should be a separate change that modifies `parameter_space.py`.

### L2: Aggregated file naming

The reference plan (Section 5.2) names the aggregated file `aggregated_summary.csv`. However, `ObjectiveFunction.compute_baseline_max_errors()` reads `{baseline_dir}/summary.csv` (A5 above). To avoid modifying `objective.py`, the baseline script names the aggregated file `summary.csv` at the output root, with a symlink `aggregated_summary.csv -> summary.csv` for human readability.

---

## Downstream Dependencies

This change creates the **infrastructure** to run calibration. The actual calibration execution (Phases B-E, ~12.8 days) and subsequent parameter updates are separate future work:

1. **Run calibration** — Execute Phases B through E using the scripts created here (requires desktop with GPU)
2. **Update parameter defaults** — After Phase D completes, update `parameter_space.py` default values with the optimal parameters found by Optuna
3. **Update agent spec** — Update `openspec/specs/agent/spec.md` (line 172-175: `RVAgentConfig` fields with default values) to reflect the calibrated values. This would be an **FF SDD change** since it modifies documented spec behavior.

These downstream changes are tracked separately and are not part of Issue #9.

---

## Tasks

All file paths are relative to `modules/rv-agent-validation/src/rv_agent_validation/` unless prefixed with `scripts/`, `modules/`, or `backup/`.

### Task 1: `scripts/calibration_orchestrator.py` + unit tests

*Ref: docs/20260213_plano_calibracao.md, Sections 3.1 (Pattern 2), 4.1, 8.1-8.4*

Write the calibration orchestrator as a standalone script at `scripts/calibration_orchestrator.py`. The script runs on the host (not inside Docker) and manages the Optuna study. All testable logic must be in pure functions that can be unit-tested without Docker.

**1.1 Script structure** — Organize into testable functions:

```python
# Pure functions (unit-testable)
def generate_calibration_compose(batch, data_dir, filter_file, output_dir, image, cpus, memory) -> dict
def recover_orphaned_trials(study, output_dir, objective_fn) -> int
def preflight_checks(data_dir, filter_file, agent_mode) -> None  # raises SystemExit on failure
def compute_score_for_trial(trial_num, output_dir, objective_fn) -> float

# Main orchestration (requires Docker)
def main() -> None
```

**1.2 Compose generation** — `generate_calibration_compose()` produces a dict (YAML-serializable) following the pattern from `docker/docker-compose.parallel.yml`. Each trial becomes a service:

```python
# Service definition for trial_N
{
    "image": image,                    # "phtcosta/rvandroid:0.8.0"
    "environment": {
        "RV_TOOLS": tool_spec,         # "rvagent:pure_algorithm@mop_direct_score=350.0000,..."
        "RV_EXPERIMENT_NAME": f"trial_{trial_num}",
        "RV_TIMEOUTS": str(timeout),
        "RV_NO_WINDOW": "true",
        "RV_SKIP_MONITORS": "true",
        "RV_SKIP_INSTRUMENT": "true",
        "RV_SKIP_STATIC_ANALYSIS": "true",
        "RV_APKS_FILTER": "/opt/rvsec/rv-android/filters/filter.txt",
        "RV_DELAY": str(index * 10),   # Staggered by 10s
    },
    "volumes": [
        f"{data_dir}:/opt/rvsec/rv-android/apks:ro",
        f"{filter_file}:/opt/rvsec/rv-android/filters/filter.txt:ro",
        f"{output_dir}/trial_{trial_num}:/opt/rvsec/rv-android/results",
    ],
    "devices": ["/dev/kvm:/dev/kvm"],
    "deploy": {"resources": {"limits": {"cpus": str(cpus), "memory": memory}}},
}
```

No `depends_on: humanoid` — per reference plan Section 8.5, none of the calibration tools (APE, FastBot, RVAgent) require the Humanoid DNN server.

**1.3 Optuna ask/tell loop** — Main orchestration logic:

```python
study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=seed),
                            storage=f"sqlite:///{output_dir}/optuna_study.db",
                            study_name=f"rvagent_{phase}", load_if_exists=resume)

while completed_trials < n_trials:
    batch = [(study.ask(), suggest_params(trial, phase)) for _ in range(batch_size)]
    compose = generate_calibration_compose(batch, ...)
    write_yaml(compose_path, compose)
    try:
        subprocess.run(["docker", "compose", "-f", str(compose_path), "up"], check=False, timeout=...)
    finally:
        subprocess.run(["docker", "compose", "-f", str(compose_path), "down"], check=False)
    for trial, params in batch:
        score = compute_score_for_trial(trial.number, output_dir, objective_fn)
        study.tell(trial.number, score if score > 0 else 0.0)
```

**1.4 Orphan recovery** — When `--resume` is used, iterate over RUNNING trials:

```python
def recover_orphaned_trials(study, output_dir, objective_fn) -> int:
    recovered = 0
    for trial in study.trials:
        if trial.state == optuna.trial.TrialState.RUNNING:
            results_dir = Path(output_dir) / f"trial_{trial.number}" / f"trial_{trial.number}"
            summary = results_dir / "summary.csv"
            if summary.exists():
                score = objective_fn.compute(str(results_dir))
                study.tell(trial.number, score)
            else:
                study.tell(trial.number, state=optuna.trial.TrialState.FAIL)
            recovered += 1
    return recovered
```

**1.5 Final output** — After all trials complete, save three files (same format as `CalibrationOptimizer.save_results()` in optimizer.py:289-331):
- `optimal_params.json`: `{"phase", "seed", "best_score", "best_params", "n_trials"}`
- `param_string.txt`: DSL string from `params_to_tool_spec()`
- `trial_history.json`: `[{"number", "params", "value", "state"}, ...]`

**1.6 Unit tests** — See Task 3 for test specifications.

### Task 2: `scripts/baseline_docker.py` + unit tests

*Ref: docs/20260213_plano_calibracao.md, Sections 3.1 (Pattern 1), 4.2, 5.2*

Write the baseline/validation script at `scripts/baseline_docker.py`. Simpler than the orchestrator — no Optuna, no parameter suggestions. Uses the batch pattern from `scripts/parallel_run.py` (existing reference, lines 36-42 for round-robin splitting).

**2.1 Batch splitting** — Round-robin distribution, following `parallel_run.py:split_apks()`:

```python
def split_apks_round_robin(apk_names: list[str], n_batches: int) -> list[list[str]]:
    batches: list[list[str]] = [[] for _ in range(n_batches)]
    for i, apk in enumerate(apk_names):
        batches[i % n_batches].append(apk)
    return batches
# 105 APKs / 6 containers = 4 batches of 18, 2 batches of 17
```

**2.2 Compose generation** — Similar to Task 1.2, but all containers get the same `RV_TOOLS` and each gets its own batch filter file:

```python
{
    "environment": {
        "RV_TOOLS": tools,              # "ape,fastbot,rvagent:pure_algorithm" (same for all)
        "RV_EXPERIMENT_NAME": f"batch_{i}",
        "RV_REPETITIONS": str(repetitions),
        "RV_APKS_FILTER": f"/opt/rvsec/rv-android/filters/batch_{i}_apks.txt",
        # ... same skip flags, RV_NO_WINDOW, RV_DELAY as calibration
    },
    "volumes": [
        f"{data_dir}:/opt/rvsec/rv-android/apks:ro",
        f"{output_dir}/batch_{i}_apks.txt:/opt/rvsec/rv-android/filters/batch_{i}_apks.txt:ro",
        f"{output_dir}/batch_{i}:/opt/rvsec/rv-android/results",
    ],
}
```

**2.3 Result aggregation** — After all containers complete, concatenate per-batch `summary.csv` files into `{output_dir}/summary.csv` (naming per L2 above):

```python
def aggregate_summaries(output_dir: Path, n_batches: int) -> Path:
    dfs = []
    for i in range(n_batches):
        csv_path = output_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv"
        if csv_path.exists():
            dfs.append(pd.read_csv(csv_path))
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        out_path = output_dir / "summary.csv"
        combined.to_csv(out_path, index=False)
        return out_path
    return None
```

**2.4 `--generate-only` mode** — Print compose file path and exit before `docker compose up`. Allows the operator to inspect the generated YAML before launching containers.

**2.5 Unit tests** — See Task 3 for test specifications.

### Task 3: Unit tests (TDD)

*Ref: docs/20260213_plano_calibracao.md, Section 11.1*

Tests are written alongside the scripts in Tasks 1-2 (TDD). All test files go in `modules/rv-agent-validation/tests/calibration/` with an `__init__.py`. Tests use `tmp_path` fixtures for filesystem, Optuna in-memory storage, and no Docker dependency.

**3.1 `test_compose_generation.py`** — 8 tests

| # | Test | Setup | Assertion |
|---|------|-------|-----------|
| T1 | `test_calibration_compose_structure` | `generate_calibration_compose(batch=[(0, "spec0"), (1, "spec1")], image="phtcosta/rvandroid:0.8.0", cpus=10, memory="20g")` | Result has 2 services (`trial_0`, `trial_1`), each with `image`, `deploy.resources.limits.cpus="10"`, `deploy.resources.limits.memory="20g"`, `devices=["/dev/kvm:/dev/kvm"]` |
| T2 | `test_calibration_compose_env_vars` | Same as T1 | Service `trial_0` has `RV_TOOLS="spec0"`, `RV_EXPERIMENT_NAME="trial_0"`, `RV_SKIP_MONITORS="true"`, `RV_SKIP_INSTRUMENT="true"`, `RV_SKIP_STATIC_ANALYSIS="true"`, `RV_NO_WINDOW="true"` |
| T3 | `test_calibration_compose_volumes` | `generate_calibration_compose(data_dir="/data", filter_file="/filters/cal.txt", output_dir="/out")` | Service `trial_0` volumes contain `"/data:/opt/rvsec/rv-android/apks:ro"`, `"/filters/cal.txt:/opt/rvsec/rv-android/filters/filter.txt:ro"`, `"/out/trial_0:/opt/rvsec/rv-android/results"` |
| T4 | `test_calibration_compose_staggered_delay` | Batch of 4 trials | `RV_DELAY` values are `"0"`, `"10"`, `"20"`, `"30"` |
| T5 | `test_calibration_compose_no_humanoid` | Any batch | No service with "humanoid" in its name. No `depends_on` key in any service. |
| T6 | `test_baseline_compose_structure` | `generate_baseline_compose(n_batches=3, tools="ape,fastbot")` | 3 services (`batch_0`, `batch_1`, `batch_2`), all with `RV_TOOLS="ape,fastbot"` |
| T7 | `test_baseline_compose_batch_filters` | `generate_baseline_compose(output_dir="/out", n_batches=2)` | Service `batch_0` mounts `"/out/batch_0_apks.txt:/opt/rvsec/rv-android/filters/batch_0_apks.txt:ro"` |
| T8 | `test_baseline_compose_repetitions` | `generate_baseline_compose(repetitions=3)` | All services have `RV_REPETITIONS="3"` |

**3.2 `test_batch_splitting.py`** — 6 tests

| # | Test | Input | Assertion |
|---|------|-------|-----------|
| T9 | `test_even_split` | 12 APKs, 6 batches | Each batch has exactly 2 APKs |
| T10 | `test_uneven_split` | 105 APKs, 6 batches | 4 batches have 18, 2 batches have 17 (sum = 105) |
| T11 | `test_single_container` | 10 APKs, 1 batch | Single batch with all 10 APKs |
| T12 | `test_more_containers_than_apks` | 3 APKs, 6 batches | 3 batches with 1 APK each, 3 empty batches |
| T13 | `test_all_apks_present` | 105 APKs, 6 batches | `set(flatten(batches)) == set(original_apks)` — no duplicates, no omissions |
| T14 | `test_round_robin_order` | `["a", "b", "c", "d"]`, 2 batches | Batch 0 = `["a", "c"]`, Batch 1 = `["b", "d"]` |

**3.3 `test_result_aggregation.py`** — 4 tests

| # | Test | Setup (tmp_path) | Assertion |
|---|------|-------------------|-----------|
| T15 | `test_aggregate_multiple_batches` | Create 3 CSV files with 5 rows each (same columns: `apk,tool,cov_method,errors`) | Aggregated CSV has 15 rows, 1 header |
| T16 | `test_aggregate_deduplicates_headers` | Same as T15 | `pd.read_csv(agg_path)` has no row where `apk == "apk"` (header not duplicated as data) |
| T17 | `test_aggregate_empty_batch` | 2 normal CSVs + 1 empty file | Aggregated CSV has 10 rows (empty batch skipped, no error) |
| T18 | `test_aggregate_missing_batch` | 2 of 3 expected batch dirs exist | Aggregated CSV has 10 rows, warning logged for missing batch |

**3.4 `test_orphan_recovery.py`** — 5 tests

| # | Test | Setup | Assertion |
|---|------|-------|-----------|
| T19 | `test_recover_completed_orphan` | Create in-memory study, `study.ask()` → trial 0, create `tmp_path/trial_0/trial_0/summary.csv` with mock data | After `recover_orphaned_trials()`: trial 0 state is COMPLETE, return value is 1 |
| T20 | `test_recover_failed_orphan` | Same, but no results dir for trial 0 | Trial 0 state is FAIL, return value is 1 |
| T21 | `test_recover_partial_orphan` | Results dir exists but no `summary.csv` inside | Trial 0 state is FAIL |
| T22 | `test_no_orphans` | Study with 0 trials (or all COMPLETE) | Return value is 0 |
| T23 | `test_resume_continues_from_completed` | Study with 6 COMPLETE trials (via `study.ask()` + `study.tell()`), `n_trials=10` | `remaining = n_trials - completed = 4` |

**3.5 `test_preflight_checks.py`** — 4 tests

| # | Test | Setup | Assertion |
|---|------|-------|-----------|
| T24 | `test_missing_data_dir` | `preflight_checks(data_dir="/nonexistent", ...)` | Raises `SystemExit` with message containing "data" and "not found" |
| T25 | `test_missing_filter_file` | `preflight_checks(filter_file="/nonexistent", ...)` | Raises `SystemExit` with message containing "filter" |
| T26 | `test_disk_space_check` | Mock `shutil.disk_usage` returning `(0, 0, 1_000_000)` (1MB free) | Raises `SystemExit` with message containing "disk" |
| T27 | `test_all_checks_pass` | Valid `tmp_path` dirs, sufficient disk | Returns without error |

**3.6 `test_parameter_integration.py`** — 8 tests

| # | Test | Setup | Assertion |
|---|------|-------|-----------|
| T28 | `test_suggest_params_with_ask_trial` | `study = optuna.create_study()`, `trial = study.ask()` | `suggest_params(trial, CalibrationPhase.MACRO)` returns dict with 8 keys, all within defined ranges |
| T29 | `test_params_to_tool_spec_format` | `params = {"mop_direct_score": 350.0, "max_re_enables": 8}` | Returns `"mop_direct_score=350.0000,max_re_enables=8"` |
| T30 | `test_tool_spec_dsl_string` | Same as T29 | `f"rvagent:pure_algorithm@{spec}"` == `"rvagent:pure_algorithm@mop_direct_score=350.0000,max_re_enables=8"` |
| T31 | `test_objective_compute_with_mock_results` | Create `tmp_path/summary.csv` with `cov_method=50.0,errors=5.0` (1 row) | `ObjectiveFunction(0.4, 0.4, 0.2).compute(str(tmp_path))` returns expected score |
| T32 | `test_objective_missing_summary` | Empty `tmp_path` | `ObjectiveFunction().compute(str(tmp_path))` returns `0.0` |
| T33 | `test_baseline_max_errors_computation` | Create `tmp_path/summary.csv` with columns `tool,errors`, 3 tools with avg errors 5.0, 8.0, 3.0 | `compute_baseline_max_errors(str(tmp_path))` returns `8.0` |
| T34 | `test_macro_phase_suggests_8_params` | `study.ask()` trial | `len(suggest_params(trial, CalibrationPhase.MACRO))` == 8 |
| T35 | `test_micro_phase_suggests_16_params` | `study.ask()` trial | `len(suggest_params(trial, CalibrationPhase.MICRO))` == 16 |

### Task 4: Remove dead code (P3)

*Ref: docs/20260213_plano_calibracao.md, Section 2 (Dead code removal table)*

All paths relative to `modules/rv-agent-validation/`.

**4.1 Backup and delete files**

```bash
mkdir -p backup/calibration_legacy/
cp src/rv_agent_validation/calibration/optimizer.py backup/calibration_legacy/
cp src/rv_agent_validation/calibration/runner.py backup/calibration_legacy/
cp src/rv_agent_validation/calibration/emulator_pool.py backup/calibration_legacy/
```

Then delete the three files from `src/rv_agent_validation/calibration/`.

**4.2 Update `calibration/__init__.py`** (currently 48 lines)

Remove three import lines and their `__all__` entries:

| Line | Current | Action |
|------|---------|--------|
| 19 | `from .emulator_pool import EmulatorPool` | DELETE |
| 21 | `from .optimizer import CalibrationOptimizer` | DELETE |
| 22 | `from .runner import CalibrationRunner, create_runner_from_config` | DELETE |
| 39 | `"EmulatorPool",` | DELETE |
| 41 | `"CalibrationOptimizer",` | DELETE |
| 43 | `"CalibrationRunner",` | DELETE |
| 44 | `"create_runner_from_config",` | DELETE |

Also remove the `# Emulator pool`, `# Optimizer`, `# Runner` comment headers (lines 37, 40, 42).

**4.3 Update `calibration/cli.py`** (currently 285 lines)

- DELETE lines 17-18: `from .optimizer import CalibrationOptimizer` and `from .runner import CalibrationRunner`
- DELETE lines 28-225: entire `calibrate()` command function with all its Click decorators
- KEEP lines 228-263: `show_params()` command
- KEEP lines 266-285: `show_defaults()` command
- KEEP lines 14-15: imports from `parameter_space` and `objective` (used by show_params indirectly via parameter_space import at line 261)

After edit, `cli.py` should have ~60 lines: the `@click.group()`, `show_params`, and `show_defaults`.

**4.4 Update `__main__.py`** (currently 160 lines)

- DELETE line 31: `cli.add_command(calibration.get_command(None, 'calibrate'), 'calibrate')`
- KEEP line 32: `cli.add_command(calibration.get_command(None, 'show-params'), 'show-params')`
- KEEP line 33: `cli.add_command(calibration.get_command(None, 'show-defaults'), 'show-defaults')`
- KEEP line 30: `from rv_agent_validation.calibration.cli import calibration` (still needed for show-params/show-defaults)

**4.5 Verify no dangling references**

```bash
grep -r "CalibrationOptimizer\|CalibrationRunner\|create_runner_from_config\|EmulatorPool" \
    modules/rv-agent-validation/src/ --include="*.py"
# Expected: zero matches

grep -r "CalibrationOptimizer\|CalibrationRunner\|EmulatorPool" \
    modules/ --include="*.py" | grep -v backup/ | grep -v __pycache__
# Expected: zero matches (scripts/ imports from parameter_space and objective, not from dead classes)
```

### Task 5: Update documentation

*Ref: docs/20260213_plano_calibracao.md, Section 2 (Downstream references table)*

**5.1 Update `modules/rv-agent-validation/CLAUDE.md`**

- Remove `optimizer.py` and `runner.py` and `emulator_pool.py` from the architecture tree under `calibration/`
- Add `scripts/calibration_orchestrator.py` and `scripts/baseline_docker.py` to project structure
- Remove `CalibrationOptimizer`, `CalibrationRunner`, `EmulatorPool` from "Key Classes" section
- Update "Calibration API" code example to show the new script-based workflow
- Update "CLI Commands > Parameter Calibration" to remove `calibrate` command, explain Docker scripts

**5.2 Update `modules/rv-agent-validation/README.md`** (if it references dead classes)

- Remove API examples referencing `CalibrationOptimizer` and `CalibrationRunner`
- Add brief mention of Docker-based calibration scripts

### Task 6: Verify

*Ref: docs/20260213_plano_calibracao.md, Sections 11.1 and 11.2*

**6.1 Unit tests** (no Docker required)

```bash
uv run pytest modules/rv-agent-validation/tests/calibration/ -v
uv run pytest modules/rv-agent-validation/tests/ -v
```

**6.2 Dangling reference check**

```bash
grep -r "CalibrationOptimizer\|CalibrationRunner\|EmulatorPool" modules/ \
    --include="*.py" | grep -v backup/ | grep -v __pycache__
# Expected: zero matches
```

**6.3 Smoke tests** (Docker + KVM available, `pure_algorithm` only — no SGLang/LLM)

The Docker image `phtcosta/rvandroid:0.8.0` and KVM are available on this machine. Smoke tests validate the end-to-end flow: compose generation -> container launch -> result collection -> score computation. LLM-dependent tests (multimode/Phase D) remain deferred until SGLang is available.

```bash
# Minimal filter (3 APKs)
head -3 modules/rv-agent-validation/data/calibration_set_v2.txt > /tmp/smoke_filter.txt

# Smoke: calibration orchestrator (2 trials, 2 containers, 60s timeout)
uv run python scripts/calibration_orchestrator.py \
    --phase macro --n-trials 2 --n-containers 2 \
    --data-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
    --filter-file /tmp/smoke_filter.txt \
    --output-dir /tmp/smoke_calibration \
    --timeout 60 --agent-mode pure_algorithm --seed 42

# Verify calibration outputs
ls /tmp/smoke_calibration/optuna_study.db
ls /tmp/smoke_calibration/trial_0/trial_0/summary.csv
cat /tmp/smoke_calibration/optimal_params.json

# Smoke: baseline docker (2 containers, 1 rep)
uv run python scripts/baseline_docker.py \
    --tools rvagent:pure_algorithm \
    --data-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
    --filter-file /tmp/smoke_filter.txt \
    --output-dir /tmp/smoke_baseline \
    --n-containers 2 --timeout 60 --repetitions 1

# Verify baseline outputs
ls /tmp/smoke_baseline/batch_0/batch_0/summary.csv
ls /tmp/smoke_baseline/summary.csv

# Smoke: --generate-only (no containers launched)
uv run python scripts/baseline_docker.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --data-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
    --filter-file /tmp/smoke_filter.txt \
    --output-dir /tmp/smoke_generate \
    --n-containers 6 --timeout 300 --repetitions 3 \
    --generate-only
cat /tmp/smoke_generate/docker-compose.yml
```

Note: Smoke tests run with `pure_algorithm` mode only. The `multimode` tests (which require SGLang at `192.168.0.36:30000`) are deferred until the LLM server is available.

---

## Acceptance Criteria

- [ ] `scripts/calibration_orchestrator.py` exists with testable pure functions for compose generation, orphan recovery, and preflight checks
- [ ] `scripts/baseline_docker.py` exists with round-robin splitting, compose generation, and CSV aggregation (output named `summary.csv` per L2)
- [ ] 35 unit tests pass in `modules/rv-agent-validation/tests/calibration/` (T1-T35)
- [ ] Smoke tests pass with Docker + KVM (`pure_algorithm` mode, 2 containers, 3 APKs, 60s timeout)
- [ ] `optimizer.py`, `runner.py`, `emulator_pool.py` backed up to `backup/calibration_legacy/` and deleted
- [ ] Zero references to `CalibrationOptimizer`, `CalibrationRunner`, `EmulatorPool` in `modules/**/src/**/*.py`
- [ ] `calibration/__init__.py` exports only: parameter_space symbols + `ObjectiveFunction` + `CalibrationMetricsCollector` + `RunMetrics`
- [ ] `calibration/cli.py` has only `show_params` and `show_defaults` commands
- [ ] `__main__.py` registers only `show-params` and `show-defaults` (not `calibrate`)
- [ ] `CLAUDE.md` and `README.md` updated — no dead class references
- [ ] Commit with `closes #9`
