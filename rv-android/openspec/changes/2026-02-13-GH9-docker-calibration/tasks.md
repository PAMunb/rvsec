# Tasks: Docker-Based Calibration — Infrastructure and Execution Campaign

## Execution Order

Tasks 1-11 cover infrastructure development (COMPLETED). Tasks 12-24 cover the execution campaign lifecycle. When bugs are discovered during execution, correction tasks are inserted as sub-tasks (e.g., Task 15a) to preserve numbering.

### Infrastructure (COMPLETED)

1. Task 1: `scripts/calibration_orchestrator.py` — host-side Optuna ask/tell orchestrator
2. Task 2: `scripts/baseline_docker.py` — batch baseline/validation runner
3. Task 3: Unit tests (39 tests across 6 files in `tests/calibration/`)
4. Task 4: Dead code removal (optimizer.py, runner.py, emulator_pool.py -> `backup/calibration_legacy/`)
5. Task 5: Documentation updates (CLAUDE.md, README.md for rv-agent-validation)
6. Task 6: Optuna upgrade (3.5 -> 4.7.0 in pyproject.toml + poetry.lock)
7. Task 7: Fix G1 — add `aggregated_summary.csv` symlink in `baseline_docker.py`
8. Task 8: Fix G2 — fix compose file naming in `calibration_orchestrator.py`
9. Task 9: Update unit tests for G1/G2 fixes
10. Task 10: Run unit tests — 39/39 passed (2.01s)
11. Task 11: Update GitHub Issue #9 (label + body for Full SDD)

### Execution Campaign (PENDING)

12. Task 12: Commit infrastructure + rewritten artifacts, run tests, update GH#9
13. Task 13: Transfer and verify infrastructure on desktop (smoke tests S1-S3)
14. Task 14: Phase B — Execute baseline (~18.4h)
15. Task 15: Phase B — Verify results + compute BASELINE_MAX_ERRORS
16. Task 16: Phase C — Execute macro calibration (~122h)
17. Task 17: Phase C — Verify results + analyze convergence
18. Task 18: Phase D — Execute micro calibration (~160h, requires SGLang)
19. Task 19: Phase D — Verify results + compare modes
20. Task 20: Phase E — Execute validation (~5.6h)
21. Task 21: Phase E — Verify results + statistical comparison
22. Task 22: Apply optimal parameters to code
23. Task 23: Update agent spec (FF SDD delta spec)
24. Task 24: Archive change and close issue (closes #9)

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

## Execution Campaign Tasks

### 12. Commit Infrastructure + Rewritten Artifacts

Commit all infrastructure code and the rewritten SDD artifacts (proposal.md expanded, design.md as runbook, tasks.md with execution campaign). Update GH#9 title/body. Use `refs #9` (not `closes` — the issue stays open for execution).

- [ ] 12.1 Run unit tests: `poetry run pytest modules/rv-agent-validation/tests/calibration/ -v` — all 39 must pass.
- [ ] 12.2 Update GH#9 title to reflect expanded scope (infrastructure + execution campaign).
- [ ] 12.3 Update GH#9 body with execution campaign acceptance criteria.
- [ ] 12.4 Stage all files: scripts, tests, dead code removals, docs, OpenSpec artifacts, poetry.lock.
- [ ] 12.5 Commit with `refs #9`.

### 13. Transfer and Verify on Desktop

Transfer code to the desktop machine and run smoke tests S1-S3 to validate the Docker infrastructure end-to-end before committing to the ~306-hour campaign.

- [ ] 13.1 `git pull` on desktop.
- [ ] 13.2 `poetry install` on desktop.
- [ ] 13.3 **S1: Calibration orchestrator smoke** — `--phase macro --n-trials 2 --n-containers 2 --timeout 60 --seed 42` with 3 APKs.
  - Verify: `optuna_study.db` exists, `trial_0/trial_0/summary.csv` exists, `optimal_params.json` saved.
- [ ] 13.4 **S2: Baseline docker smoke** — `--tools rvagent:pure_algorithm --n-containers 2 --timeout 60 --repetitions 1` with 3 APKs.
  - Verify: `batch_0/batch_0/summary.csv` exists, `summary.csv` aggregated, `aggregated_summary.csv` symlink.
- [ ] 13.5 **S3: Generate-only smoke** — `--tools ape,fastbot,rvagent:pure_algorithm --n-containers 6 --generate-only`.
  - Verify: `docker-compose.yml` has 6 services, no containers launched, batch filter files created.

### 14. Phase B — Execute Baseline

*Runbook reference: design.md Section 1*

- [ ] 14.1 Run baseline command from design.md Section 1 "Execution".
- [ ] 14.2 Monitor progress: check batch directories for `tasks.json` growth.
- [ ] 14.3 If interrupted: re-run same command (rv-experiment auto-resumes via tasks.json).

### 15. Phase B — Verify Results

*Runbook reference: design.md Section 1 "Verification"*

- [ ] 15.1 All 6 batch summaries exist.
- [ ] 15.2 Aggregated `summary.csv` has 945 data rows.
- [ ] 15.3 All 3 tools present in summary.
- [ ] 15.4 Compute and record `BASELINE_MAX_ERRORS` value.
- [ ] 15.5 Symlink `aggregated_summary.csv` intact.

**Gate**: All 5 checks pass before proceeding to Phase C.

### 16. Phase C — Execute Macro Calibration

*Runbook reference: design.md Section 2*

- [ ] 16.1 Run calibration orchestrator command from design.md Section 2 "Execution".
- [ ] 16.2 Monitor progress: check `trial_history.json` growth, `orchestrator.log` for errors.
- [ ] 16.3 If interrupted: re-run with `--resume` flag.

### 17. Phase C — Verify Results

*Runbook reference: design.md Section 2 "Verification"*

- [ ] 17.1 All 80 trials completed (check `trial_history.json`).
- [ ] 17.2 Best score > 0.0.
- [ ] 17.3 Convergence visible: last 20 trials score higher than first 20 on average.
- [ ] 17.4 `optimal_params.json` and `param_string.txt` exist and are valid.

**Gate**: All 4 checks pass before proceeding to Phase D.

### 18. Phase D — Execute Micro Calibration

*Runbook reference: design.md Section 3*

**Prerequisite**: SGLang server running at `192.168.0.36:30000`.

- [ ] 18.1 Verify SGLang server: `curl -s http://192.168.0.36:30000/v1/models`.
- [ ] 18.2 Run calibration orchestrator command from design.md Section 3 "Execution".
- [ ] 18.3 Monitor progress: check `trial_history.json` growth, SGLang server health.
- [ ] 18.4 If interrupted: re-run with `--resume` flag.

### 19. Phase D — Verify Results

*Runbook reference: design.md Section 3 "Verification"*

- [ ] 19.1 All 100 trials completed.
- [ ] 19.2 Best score > 0.0.
- [ ] 19.3 `optimal_params.json` contains all 24 parameters (8 macro + 16 micro).
- [ ] 19.4 Compare micro best score vs macro best score (improvement expected).

**Gate**: All 4 checks pass before proceeding to Phase E.

### 20. Phase E — Execute Validation

*Runbook reference: design.md Section 4*

- [ ] 20.1 Run baseline command from design.md Section 4 "Execution" (uses `param_string.txt` from Phase D).
- [ ] 20.2 Monitor progress.

### 21. Phase E — Verify Results

*Runbook reference: design.md Section 4 "Verification"*

- [ ] 21.1 `summary.csv` has 270 data rows, 3 tools present.
- [ ] 21.2 Run statistical comparison (Wilcoxon) between calibrated and baseline RVAgent.
- [ ] 21.3 Document results: coverage improvement, error reduction, p-values.

**Gate**: 270 rows present. Calibrated RVAgent shows improvement over baseline on at least one metric.

### 22. Apply Optimal Parameters to Code

*Runbook reference: design.md Section 5*

- [ ] 22.1 Update default values in `parameter_space.py` (`MACRO_PARAMETERS` and `MICRO_PARAMETERS`).
- [ ] 22.2 Update any unit tests that assert default parameter values.
- [ ] 22.3 Run `poetry run pytest modules/rv-agent-validation/tests/calibration/ -v` — all must pass.

### 23. Update Agent Spec

- [ ] 23.1 Create FF SDD delta spec for `openspec/specs/agent/spec.md` with calibrated default values.
- [ ] 23.2 Sync delta spec to main spec.

### 24. Archive and Close

- [ ] 24.1 Archive change directory to `openspec/changes/archive/2026-02-13-GH9-docker-calibration/`.
- [ ] 24.2 Commit with `closes #9`.
- [ ] 24.3 Verify issue closed on GitHub.
