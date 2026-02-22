# Tasks: Docker-Based Calibration — Full Lifecycle

## Execution Order

Tasks 1-12 cover infrastructure development (COMPLETED — 86 tests passing). Tasks 12a-12d cover parameter space expansion (gh18/gh26 sync). Tasks 13-14 handle commit and desktop transfer. Tasks 15-16 cover Docker preprocessing (Phase A). Tasks 16a-16h cover pre-calibration (Phases B0/C0/D0). Tasks 17-24 cover the full calibration execution campaign (Phases B-E). Tasks 25-27 cover post-execution parameter application.

When bugs are discovered during execution, correction tasks are inserted as sub-tasks (e.g., Task 17a) to preserve numbering.

### Infrastructure (COMPLETED)

1. Task 1: `scripts/calibration_orchestrator.py` — host-side Optuna ask/tell orchestrator
2. Task 2: `scripts/baseline_docker.py` — batch baseline/validation runner
3. Task 3: Unit tests (39 tests across 6 files in `tests/calibration/`)
4. Task 4: Dead code removal (optimizer.py, runner.py, emulator_pool.py -> `backup/calibration_legacy/`)
5. Task 5: Documentation updates (CLAUDE.md, README.md for rv-agent-validation)
6. Task 6: Optuna upgrade (3.5 -> 4.7.0 in pyproject.toml + uv.lock)
7. Task 7: Fix G1 — add `aggregated_summary.csv` symlink in `baseline_docker.py`
8. Task 8: Fix G2 — fix compose file naming in `calibration_orchestrator.py`
9. Task 9: Update unit tests for G1/G2 fixes
10. Task 10: Run unit tests — 39/39 passed (2.01s)
11. Task 11: Update GitHub Issue #9 (label + body for Full SDD)

### Bug Fixes and Preprocessing Script (COMPLETED)

12. Task 12: Fix infrastructure bugs + create `preprocess_docker.py`

### Parameter Space Expansion (COMPLETED)

12a. Task 12a: Update `parameter_space.py` — sync 6 defaults (gh26), add 12 new params (3 MACRO + 9 MICRO)
12b. Task 12b: Update unit tests — 11 MACRO, 26 MICRO, 37 total
12c. Task 12c: Update `design.md` — pre-cal phases, expanded params, TIMEOUT_SECS placeholder
12d. Task 12d: Update `tasks.md` — add pre-cal tasks, update param counts

### Commit and Transfer (PENDING)

13. Task 13: Commit all code + rewritten artifacts (refs #9)
14. Task 14: Transfer and verify on desktop (smoke tests)

### Docker Preprocessing (PENDING)

15. Task 15: Phase A — Execute Docker preprocessing
16. Task 16: Phase A — Verify results + assemble dataset

### Pre-Calibration (PENDING)

16a. Task 16a: Select 20 pre-calibration APKs (stratified from calibration set)
16b. Task 16b: Phase B0 — Execute pre-baseline (20 APKs, 2 tools, 1 rep)
16c. Task 16c: Phase B0 — Verify results + compute BASELINE_MAX_ERRORS_PRE
16d. Task 16d: Phase C0 — Execute pre-macro (30 trials, 11 MACRO params)
16e. Task 16e: Phase C0 — Verify convergence
16f. Task 16f: Phase D0 — Execute pre-micro (40 trials, 26 MICRO params, SGLang)
16g. Task 16g: Phase D0 — Verify convergence
16h. Task 16h: Update `parameter_space.py` defaults from pre-cal optimal params

### Execution Campaign (PENDING)

17. Task 17: Phase B — Execute baseline
18. Task 18: Phase B — Verify results + compute BASELINE_MAX_ERRORS
19. Task 19: Phase C — Execute macro calibration (80 trials, 11 MACRO params)
20. Task 20: Phase C — Verify results + analyze convergence
21. Task 21: Phase D — Execute micro calibration (100 trials, 26 MICRO params, SGLang)
22. Task 22: Phase D — Verify results + compare modes
23. Task 23: Phase E — Execute validation (37 params, SGLang)
24. Task 24: Phase E — Verify results + statistical comparison

### Post-Execution (PENDING)

25. Task 25: Apply 37 optimal parameters to code
26. Task 26: Update agent spec (FF SDD delta spec)
27. Task 27: Archive change and close issue (closes #9)

---

## Infrastructure Tasks (COMPLETED — Details Preserved for Reference)

### 1. Calibration Orchestrator Script

- [x] 1.1 Create `scripts/calibration_orchestrator.py` with pure functions: `generate_calibration_compose()`, `recover_orphaned_trials()`, `preflight_checks()`, `compute_score_for_trial()`, `_save_results()`.
- [x] 1.2 Implement Optuna ask/tell loop in `main()`.
- [x] 1.3 Implement orphan recovery for `--resume`.
- [x] 1.4 Implement three output files: `optimal_params.json`, `param_string.txt`, `trial_history.json`.
- [x] 1.5 Support `--phase macro|micro` with fixed macro params loading for micro phase.
- [x] 1.6 Use `@` separator for tool spec DSL.
- [x] 1.7 Implement preflight checks: data dir, filter file, disk space.
- [x] 1.8 Implement compose file archival per round.

### 2. Baseline Docker Script

- [x] 2.1 Create `scripts/baseline_docker.py` with pure functions.
- [x] 2.2 Implement round-robin APK distribution.
- [x] 2.3 Implement compose generation.
- [x] 2.4 Implement result aggregation with `summary.csv` + symlink.
- [x] 2.5 Implement `--generate-only` mode.
- [x] 2.6 Implement `try/finally` cleanup.

### 3. Unit Tests

- [x] 3.1 `test_compose_generation.py` — 8 tests
- [x] 3.2 `test_batch_splitting.py` — 6 tests
- [x] 3.3 `test_result_aggregation.py` — 4 tests
- [x] 3.4 `test_orphan_recovery.py` — 5 tests
- [x] 3.5 `test_preflight_checks.py` — 8 tests (parametrized)
- [x] 3.6 `test_parameter_integration.py` — 8 tests

### 4-11. Supporting Tasks

- [x] 4: Dead code removal (P3)
- [x] 5: Documentation updates
- [x] 6: Optuna upgrade
- [x] 7: Fix G1 (aggregated summary symlink)
- [x] 8: Fix G2 (compose file naming)
- [x] 9: Update unit tests for G1/G2
- [x] 10: Run unit tests (39/39 passed)
- [x] 11: Update GitHub Issue #9

---

## Bug Fixes and Preprocessing Script

### 12. Fix Infrastructure Bugs + Create `preprocess_docker.py`

Code fixes for risks identified during deep analysis, plus the new preprocessing script that replaces host-side Phase 0/A scripts with Docker-based preprocessing.

#### Completed

- [x] 12.1 **R3: SGLang networking** — Add `extra_hosts: ["host.docker.internal:host-gateway"]` to `generate_calibration_compose()` in `calibration_orchestrator.py`. Conditional: only when `--sglang-url` is provided.
- [x] 12.2 **R3: SGLang networking** — Add `extra_hosts` to `generate_baseline_compose()` in `baseline_docker.py`. Conditional: only when `--sglang-url` is provided.
- [x] 12.3 **R4: llm_base_url injection** — Add `--sglang-url` CLI parameter to `calibration_orchestrator.py`. When provided, append `llm_base_url=<url>` to the tool spec in the Optuna loop.
- [x] 12.4 **R4: llm_base_url injection** — Add `--sglang-url` CLI parameter to `baseline_docker.py`. When provided and tools contain `multimode`, inject `llm_base_url` into the tool spec.
- [x] 12.5 **R1: Naming mismatch** — Fix `filter_apks_static_analysis.py` to output `passed_apks.txt` instead of `valid_apks.txt`.
- [x] 12.5a **Wrapper script fixes** — Fix `run_phase_d.sh`: use `host.docker.internal:30000/v1` (not hardcoded desktop IP), separate host-side preflight from container URL, add `--sglang-url` to orchestrator command. Fix `run_phase_e.sh`: add `--sglang-url`, SGLang preflight check. Remove broken `--resume` flag from `run_phase_b.sh` and `run_phase_e.sh` (baseline_docker.py does not accept it).

- [x] 12.6 **Create `scripts/preprocess_docker.py`** — Dedicated compose generator for Phase A (Docker preprocessing). Pure functions: `generate_preprocess_compose()` (entrypoint override with `--skip-execution`), `collect_preprocessed_artifacts()` (merge per-container `out/` into single dataset), `filter_by_sa_completeness()` (check for .gesda, .wtg, .reach). See design.md Section 1 for compose structure.
- [x] 12.7 **Unit tests for `preprocess_docker.py`** — 8 compose tests (T15-T22) in `test_compose_generation.py`, 8 collection/filter tests (T23-T30) in `test_preprocess.py`.
- [x] 12.8 **Unit tests for `extra_hosts` and `--sglang-url`** — 6 tests (T9-T14) in `test_compose_generation.py`.
- [x] 12.9 Run all tests: 84/84 passed (3.11s).

---

## Parameter Space Expansion

### 12a. Update `parameter_space.py` — Expand from 24 to 37 Params

Sync 6 existing defaults changed by gh26, add 3 new MACRO params (gh26 + gh18), add 10 new MICRO params (gh26 + gh18).

#### Completed

- [x] 12a.1 Sync `mop_direct_score` default 300→500, range 200-500→300-700.
- [x] 12a.2 Sync `mop_transitive_score` default 150→300, range 75-250→150-450.
- [x] 12a.3 Sync `wtg_guided_score` default 250→150, range 100-400→50-300.
- [x] 12a.4 Sync `unsaturated_bonus` default 80→100, range 40-120→50-150.
- [x] 12a.5 Sync `visitation_penalty_factor` default -10→-15, range -20/-5→-25/-5.
- [x] 12a.6 Sync `stochastic_probability` default 0.3→0.15, range 0.1-0.7→0.05-0.4.
- [x] 12a.7 Add MACRO: `backtrack_saturation_threshold` (float, 0.8, 0.5-1.0, gh26).
- [x] 12a.8 Add MACRO: `coverage_density_weight` (float, 200.0, 50-400, gh26).
- [x] 12a.9 Add MACRO: `error_detection_confidence` (float, 0.7, 0.3-0.95, gh18).
- [x] 12a.10 Add MICRO: `mop_nav_weight`, `mop_max_input_variations`, `reward_gamma`, `reward_score_weight`, `multi_value_saturation_threshold` (gh26).
- [x] 12a.11 Add MICRO: `error_max_indicator_size`, `error_max_indicator_count`, `spatial_edittext_boost`, `spatial_spinner_boost`, `spatial_min_match_threshold` (gh18).
- [x] 12a.12 Update `CalibrationPhase` docstring: 11 MACRO, 26 MICRO, 37 total.

### 12b. Update Unit Tests

- [x] 12b.1 `test_parameter_integration.py`: T28 assert 11 macro, update ranges.
- [x] 12b.2 `test_parameter_integration.py`: T34 assert 11 macro, T35 assert 26 micro.
- [x] 12b.3 Add T36 (FULL phase suggests 37) and T37 (new MICRO params exist).
- [x] 12b.4 `test_verify_phase.py`: Update 24→37 in all TestVerifyPhaseD tests.
- [x] 12b.5 `scripts/verify_phase.py`: Update parameter_count check 24→37.
- [x] 12b.6 Run all tests: 86/86 passed (5.84s).

### 12c. Update `design.md`

- [x] 12c.1 Add TIMEOUT_SECS placeholder section with speed test reference.
- [x] 12c.2 Add phase structure diagram (A → B0 → C0 → D0 → B → C → D → E).
- [x] 12c.3 Add Section 1b: Pre-Calibration Phases (B0, C0, D0).
- [x] 12c.4 Update Phase C: 8→11 MACRO params, C0 starting defaults.
- [x] 12c.5 Update Phase D: 16→26 MICRO, 24→37 total, D0 starting defaults.
- [x] 12c.6 Update Phase E: 37 params validated.
- [x] 12c.7 Update all `--timeout 300` → `--timeout TIMEOUT_SECS`.
- [x] 12c.8 Update post-execution section: 37 params.

### 12d. Update `tasks.md`

- [x] 12d.1 Add Tasks 12a-12d (parameter space expansion).
- [x] 12d.2 Add Tasks 16a-16h (pre-calibration).
- [x] 12d.3 Update Tasks 14.6-14.8 (smoke tests with 37 params).
- [x] 12d.4 Update Tasks 17-22 (new param counts, timeout references).
- [x] 12d.5 Update Task 25 (apply 37 optimal parameters).

---

## Commit and Transfer

### 13. Commit All Code + Rewritten Artifacts

Commit all infrastructure code, bug fixes, preprocessing script, and the rewritten SDD artifacts. Update GH#9 title/body. Use `refs #9` (not `closes` — the issue stays open for execution).

- [ ] 13.1 Run unit tests: all must pass.
- [ ] 13.2 Update GH#9 title to: "Docker-based calibration: infrastructure + full execution campaign (Phases A-E)"
- [ ] 13.3 Update GH#9 body with full lifecycle acceptance criteria.
- [ ] 13.4 Stage all files: scripts, tests, dead code removals, docs, OpenSpec artifacts, uv.lock.
- [ ] 13.5 Commit with `refs #9`.

### 14. Transfer and Verify on Desktop

Transfer code to the desktop machine and run smoke tests to validate end-to-end before the campaign.

- [ ] 14.1 `git pull` on desktop.
- [ ] 14.2 `uv sync` on desktop.
- [ ] 14.3 Verify environment: Docker image, KVM, disk space. (RVSEC_HOME and Java 8 NOT needed on host.)
- [ ] 14.4 Copy `apks_complete.csv` to `modules/rv-agent-validation/data/`.
- [ ] 14.5 Verify APK source directory: flat structure, 188+ APKs.
- [ ] 14.6 **S1: Preprocessing smoke** — `preprocess_docker.py` with 3 APKs, 2 containers.
  - Verify: compose has entrypoint override with `--skip-execution`, `out/` volume mounted, instrumented APKs and SA files collected.
- [ ] 14.7 **S2: Calibration orchestrator smoke** — `--phase macro --n-trials 2 --n-containers 2 --timeout 60 --seed 42` with 3 APKs.
  - Verify: `optuna_study.db` exists, `trial_0/trial_0/summary.csv` exists, `optimal_params.json` saved, 11 macro params suggested.
- [ ] 14.8 **S3: Baseline docker smoke** — `--tools rvagent:pure_algorithm --n-containers 2 --timeout 60 --repetitions 1` with 3 APKs.
  - Verify: `batch_0/batch_0/summary.csv` exists, `summary.csv` aggregated, `aggregated_summary.csv` symlink.
- [ ] 14.9 **S4: Generate-only smoke** — `--tools ape,fastbot,rvagent:pure_algorithm --n-containers 6 --generate-only`.
  - Verify: `docker-compose.yml` has 6 services, no containers launched, batch filter files created.

---

## Docker Preprocessing Tasks

### 15. Phase A — Execute Docker Preprocessing

*Runbook reference: design.md Section 1*

- [ ] 15.1 Extract 188 APK names from `apks_complete.csv` (`exp01_jca=True`).
- [ ] 15.2 Run `preprocess_docker.py` with `--n-containers 6`.
- [ ] 15.3 Monitor progress (~2h expected). Each container runs monitors + instrumentation + SA independently.

### 16. Phase A — Verify Results + Assemble Dataset

*Runbook reference: design.md Section 1 "Verification"*

- [ ] 16.1 `passed_apks.txt` exists with ≥100 APKs.
- [ ] 16.2 All passing APKs have `.gesda`, `.wtg`, `.reach` files in assembled dataset.
- [ ] 16.3 Run `select_dataset.py` to create 75 cal + 30 holdout split.
- [ ] 16.4 Verify `calibration_set_v2.txt` (75), `holdout_set_v2.txt` (30), `all_valid_apks.txt` (~105).
- [ ] 16.5 Copy assembled dataset to `modules/rv-agent-validation/data/calibration_dataset_v2/`.

**Gate**: All 5 checks pass before proceeding to pre-calibration.

---

## Pre-Calibration Tasks

### 16a. Select 20 Pre-Calibration APKs

- [ ] 16a.1 Select 20 APKs from `calibration_set_v2.txt` (stratified by category from `dataset_split.csv`).
- [ ] 16a.2 Save as `modules/rv-agent-validation/data/precal_set.txt`.
- [ ] 16a.3 Verify: all 20 APKs exist in `calibration_dataset_v2/` with SA files.

### 16b. Phase B0 — Execute Pre-Baseline

*Runbook reference: design.md Section 1b*

- [ ] 16b.1 Run `baseline_docker.py --tools ape,rvagent:pure_algorithm --filter-file precal_set.txt --repetitions 1 --timeout TIMEOUT_SECS`.
- [ ] 16b.2 Monitor progress (40 tasks, ~1.5-2.5h expected).

### 16c. Phase B0 — Verify Results

- [ ] 16c.1 `summary.csv` has 40 data rows (2 tools x 20 APKs x 1 rep).
- [ ] 16c.2 Compute and record `BASELINE_MAX_ERRORS_PRE` value.

### 16d. Phase C0 — Execute Pre-Macro

- [ ] 16d.1 Run `calibration_orchestrator.py --phase macro --n-trials 30 --filter-file precal_set.txt --timeout TIMEOUT_SECS`.
- [ ] 16d.2 Monitor progress (30 trials, ~5.5-8.3h expected).

### 16e. Phase C0 — Verify Convergence

- [ ] 16e.1 30 trials completed.
- [ ] 16e.2 Convergence visible: last 10 trials avg > first 10 avg.
- [ ] 16e.3 `optimal_params.json` saved with 11 MACRO params.

### 16f. Phase D0 — Execute Pre-Micro

**Prerequisite**: SGLang server running at `localhost:30000`.

- [ ] 16f.1 Start SGLang server.
- [ ] 16f.2 Run `calibration_orchestrator.py --phase micro --n-trials 40 --filter-file precal_set.txt --best-macro precal_macro/optimal_params.json --sglang-url ... --timeout TIMEOUT_SECS`.
- [ ] 16f.3 Monitor progress (40 trials, ~7.4-11.1h expected).

### 16g. Phase D0 — Verify Convergence

- [ ] 16g.1 40 trials completed.
- [ ] 16g.2 `optimal_params.json` contains 37 parameters (11 macro + 26 micro).
- [ ] 16g.3 Pre-cal total duration < 25h.

### 16h. Update Defaults from Pre-Cal Results

- [ ] 16h.1 Update `parameter_space.py` defaults from C0 + D0 `optimal_params.json`.
- [ ] 16h.2 Optionally narrow ranges to +/-30% around best values (clamped to original bounds).
- [ ] 16h.3 Run tests: 86/86 must pass.
- [ ] 16h.4 Commit with `refs #9`.

---

## Execution Campaign Tasks

### 17. Phase B — Execute Baseline

*Runbook reference: design.md Section 2*

- [ ] 17.1 Run `./scripts/run_phase_b.sh` (or `baseline_docker.py` manually with `--timeout TIMEOUT_SECS`).
- [ ] 17.2 Monitor progress: check batch directories for `tasks.json` growth.
- [ ] 17.3 If interrupted: re-run same command (resume is automatic via `RV_EXPERIMENT_NAME`).

### 18. Phase B — Verify Results

*Runbook reference: design.md Section 2 "Verification"*

- [ ] 18.1 All 6 batch summaries exist.
- [ ] 18.2 Aggregated `summary.csv` has 945 data rows.
- [ ] 18.3 All 3 tools present in summary.
- [ ] 18.4 Compute and record `BASELINE_MAX_ERRORS` value.
- [ ] 18.5 Symlink `aggregated_summary.csv` intact.

**Gate**: All 5 checks pass before proceeding to Phase C.

### 19. Phase C — Execute Macro Calibration (11 MACRO params)

*Runbook reference: design.md Section 3*

Starting defaults from C0 pre-calibration.

- [ ] 19.1 Run `./scripts/run_phase_c.sh` (or `calibration_orchestrator.py` manually with `--timeout TIMEOUT_SECS`).
- [ ] 19.2 Monitor progress: check `trial_history.json` growth, `orchestrator.log` for errors.
- [ ] 19.3 If interrupted: re-run with `--resume`.

### 20. Phase C — Verify Results

*Runbook reference: design.md Section 3 "Verification"*

- [ ] 20.1 All 80 trials completed (check `trial_history.json`).
- [ ] 20.2 Best score > 0.0.
- [ ] 20.3 Convergence visible: last 20 trials score higher than first 20 on average.
- [ ] 20.4 `optimal_params.json` and `param_string.txt` exist and are valid.

**Gate**: All 4 checks pass before proceeding to Phase D.

### 21. Phase D — Execute Micro Calibration (26 MICRO params)

*Runbook reference: design.md Section 4*

Starting defaults from D0 pre-calibration. 11 macro params fixed from Phase C.

**Prerequisite**: SGLang server running at `localhost:30000`.

- [ ] 21.1 Start SGLang server: `cd rvsec-vision-llm && docker compose up -d`.
- [ ] 21.2 Verify SGLang server: `curl -s http://localhost:30000/v1/models`.
- [ ] 21.3 Run `./scripts/run_phase_d.sh` (or `calibration_orchestrator.py` manually with `--sglang-url --timeout TIMEOUT_SECS`).
- [ ] 21.4 Monitor progress: check `trial_history.json` growth, SGLang server health.
- [ ] 21.5 If interrupted: re-run with `--resume`.

### 22. Phase D — Verify Results

*Runbook reference: design.md Section 4 "Verification"*

- [ ] 22.1 All 100 trials completed.
- [ ] 22.2 Best score > 0.0.
- [ ] 22.3 `optimal_params.json` contains all 37 parameters (11 macro + 26 micro).
- [ ] 22.4 Compare micro best score vs macro best score (improvement expected).

**Gate**: All 4 checks pass before proceeding to Phase E.

### 23. Phase E — Execute Validation

*Runbook reference: design.md Section 5*

**Prerequisite**: SGLang server still running (calibrated RVAgent uses multimode).

- [ ] 23.1 Verify SGLang server: `curl -s http://localhost:30000/v1/models`.
- [ ] 23.2 Run `./scripts/run_phase_e.sh` (or `baseline_docker.py` manually with `--sglang-url`).
- [ ] 23.3 Monitor progress.

### 24. Phase E — Verify Results

*Runbook reference: design.md Section 5 "Verification"*

- [ ] 24.1 `summary.csv` has 270 data rows, 3 tools present.
- [ ] 24.2 Run statistical comparison (Wilcoxon) between calibrated and baseline RVAgent.
- [ ] 24.3 Document results: coverage improvement, error reduction, p-values.
- [ ] 24.4 Stop SGLang server: `cd rvsec-vision-llm && docker compose down`.

**Gate**: 270 rows present. Calibrated RVAgent shows improvement over baseline on at least one metric.

---

## Post-Execution Tasks

### 25. Apply 37 Optimal Parameters to Code

*Runbook reference: design.md Section 6*

- [ ] 25.1 Update default values in `parameter_space.py` — 11 MACRO + 26 MICRO from `optimal_params.json`.
- [ ] 25.2 Update any unit tests that assert default parameter values.
- [ ] 25.3 Run `uv run pytest modules/rv-agent-validation/tests/calibration/ -v` — all must pass.

### 26. Update Agent Spec

- [ ] 26.1 Create FF SDD delta spec for `openspec/specs/agent/spec.md` with calibrated default values.
- [ ] 26.2 Sync delta spec to main spec.

### 27. Archive and Close

- [ ] 27.1 Run `openspec archive "gh9-docker-calibration" --skip-specs` (archives to `openspec/changes/archive/YYYY-MM-DD-gh9-docker-calibration/`).
- [ ] 27.2 Commit with `closes #9`.
- [ ] 27.3 Verify issue closed on GitHub.
