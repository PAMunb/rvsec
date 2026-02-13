# Tasks: Resume + Docker

## Execution Order

Tasks are numbered by topic but executed in dependency order. This section tracks the actual execution sequence.

### Completed (in execution order)

1. Tasks 1-5: Resume CLI, Platform wiring, Dead code removal, Docker entry point, Docker files
2. Task 6: Unit tests for resume (TDD RED phase)
3. Task 7: Result consolidation bug fix (TDD GREEN phase)
4. Task 8: Smoke tests (rv-platform + rv-experiment, Forms 1 and 2)
5. Task 10: MOP violation reconstruction from logcat (TDD RED → GREEN)
6. Task 9: Documentation update
7. Tasks 11-13: Docker compose docker.sock, ARES/QTesting network fix, build_all.sh
8. Task 14: Build all Docker images (base → android → tools → rvandroid → ares → qtesting)
9. Task 16: Update change documents (D10, delta specs)
10. Task 17: Fix monkey command builder (D11)
11. Task 18.1-18.2: Build and verify dev Docker image
12. Task 15.1-15.4: Docker smoke tests (entry point, tool registry, Docker CLI)
13. Task 15.3.a: Docker tool test — monkey:fast (PASSED)
14. Task 19: Fix DroidBot device_serial bug (D12) — verified locally
15. Task 20.1-20.2: Dev Docker image layer optimization (D13)
16. Task 20.4: Handle droidbot path dependency in Dockerfile (DONE — Layer 1b in Dockerfile)
17. Task 20.5: Exclude discontinued modules from Docker image (D14)
18. Task 18.3: Rebuild dev Docker image (includes D12, D14 fixes)
19. Task 21: Fix Humanoid tool — rewrite as DroidBot + `-humanoid` flag (D15)
20. Task 18.4: Rebuild dev Docker image (includes D15 humanoid fix)
21. Task 15.3.i: Docker tool test — humanoid (PASSED, 6-check verified)
22. Task 22: Fix ARES tool — rewrite with `docker create` + `docker cp` + `docker start` pattern (D16)
23. Task 18.5: Rebuild dev Docker image (includes D16 ARES fix)
24. Task 15.3.j: Docker tool test — ares (PASSED, 6-check verified)

25. Task 15.3.a: Docker tool test — monkey:fast (PASSED, 6-check verified)
26. Task 15.3.b: Docker tool test — ape (PASSED, 6-check verified)
27. Task 15.3.c: Docker tool test — droidbot:dfs_greedy (PASSED, 6-check verified)
28. Task 15.3.d: Docker tool test — droidbot:bfs_greedy (PASSED, 6-check verified)
29. Task 15.3.e: Docker tool test — droidbot:dfs_naive (PASSED, 6-check verified)
30. Task 15.3.f: Docker tool test — droidbot:bfs_naive (PASSED, 6-check verified)
31. Task 15.3.g: Docker tool test — fastbot (PASSED, 6-check verified)
32. Task 15.3.h: Docker tool test — rvagent:pure_algorithm (PASSED, 6-check verified)

25. Task 23: Fix QTesting tool — rewrite with `docker create` + `docker cp` + `docker start` pattern + remove struct.py (D17)
26. Task 18.6: Rebuild QTesting Docker image (without struct.py) + rebuild dev Docker image (includes D17 QTesting fix)
27. Task 15.3.k: Docker tool test — qtesting (PASSED, 6-check verified)

28. Task 24: Fix DroidMate tool — rewrite with correct DroidMate-2 CLI flags (D18)
29. Task 18.7: Rebuild dev Docker image (includes D18 DroidMate fix)
30. Task 15.3.l: Docker tool test — droidmate (PASSED, 6-check verified)

31. Task 15.5: Resume in Docker (PASSED, 6-check verified)

32. Task 20.3: Verify layer cache optimization (PASSED — 0.7s rebuild after code-only change)

33. Task 15.6: Full pipeline integration test in Docker (PASSED — all 8 checks, see below)

### Pending (planned order)

(none — all implementation tasks complete)

---

## 1. Resume CLI (rv-experiment)

- [x] 1.1 Add `--resume-dir` Click option to the `run` command in `modules/rv-experiment/src/rv_experiment/__main__.py`. Type: `click.Path(exists=True)`, default `None`. Pass through to `_create_experiment_config_from_cli()`.
- [x] 1.2 Make `--name` resume-aware in `_create_experiment_config_from_cli()`. When `--name` is provided and `results/<name>/tasks.json` exists, auto-set `skip_monitors=True`, `skip_instrument=True`, `skip_static=True`, and log "Resuming experiment '<name>' — auto-skipping pre-processing".
- [x] 1.3 Implement `--resume-dir` handling in `_create_experiment_config_from_cli()`. When provided: use as `experiment_dir`, auto-set all skip flags, log "Resuming experiment from <path>". `--resume-dir` overrides `--name` if both are provided. The `--apks-dir` argument is NOT auto-detected — the user must provide it explicitly (or the default applies).

## 2. Platform Resume Wiring (rv-platform)

- [x] 2.1 In `Platform.run()` (`modules/rv-platform/src/rv_platform/platform.py`), after `_generate_tasks()`: create `ExperimentMetadata` with `experiment_id=self.config.results_dir`, compute `config_checksum` from `PlatformConfig`, set `start_time` to current ISO timestamp, and call `self.task_storage.set_experiment_metadata(metadata)`.
- [x] 2.2 In `_skip_completed_tasks()`, after confirming completed tasks exist: call `self.task_storage.check_continuation_compatibility(config_dict)`. If it returns `False`, log warning "Config changed since last run — resuming anyway". Keep existing skip logic unchanged.

## 3. Dead Code Removal (rv-experiment)

- [x] 3.0 Backup `modules/rv-experiment/src/rv_experiment/config.py` to `backup/config.py.bak` before any modifications. This preserves the original for thesis records and enables recovery.
- [x] 3.1 Delete `get_artifact_validation_config()` method entirely from `config.py` (references undefined `self.artifact_reuse_enabled` and `self.phase_control`; crashes at runtime). No adapter, no deprecation wrapper — complete removal.
- [x] 3.2 Delete `load_from_status()` method entirely from `config.py` (dead code, never called from any entry point). No compatibility shim — the new resume architecture uses a fundamentally different approach (CLI detection + platform task skipping).
- [x] 3.3 Grep the entire codebase to confirm zero references to `get_artifact_validation_config` and `load_from_status` (expected: none). Document grep results in the commit message.

## 4. Docker Entry Point

- [x] 4.1 Create `docker/rvandroid/docker-entrypoint.sh` translating CLI env vars to `rv-experiment run` arguments: RV_TOOLS (→ --tools), RV_TIMEOUTS (→ --timeout), RV_REPETITIONS (→ --repetitions), RV_APKS_DIR (→ --apks-dir), RV_NO_WINDOW (→ --no-window/--window), RV_SPEC_SET (→ --specification-set), RV_JCA_SPEC (→ --specification-set jca/generic, legacy compat), RV_SKIP_MONITORS (→ --skip-monitors), RV_SKIP_INSTRUMENT (→ --skip-instrument), RV_SKIP_STATIC_ANALYSIS (→ --skip-static), RV_DEVICE_PORT (→ --device-port), RV_APKS_FILTER (→ --apks-filter), RV_EXPERIMENT_NAME (→ --name), RV_RESUME_DIR (→ --resume-dir), RV_DEBUG (→ --log-level DEBUG). Include RV_DELAY (sleep before exec). Pass-through vars (RVSEC_HOME, ANDROID_HOME, TOOLS_DIR, RV_HUMANOID_URL, RVAGENT_*, RV_PYDANTIC) are NOT translated — they are read directly by Python modules. Support `bash`/`shell` mode for interactive access. Echo generated command.

## 5. Docker Files

- [x] 5.1 Update `docker/rvandroid/Dockerfile`: add ENTRYPOINT (`/opt/docker-entrypoint.sh`), CMD (`["run"]`), ENV defaults (RV_TOOLS, RV_TIMEOUTS, RV_REPETITIONS, RV_NO_WINDOW, RV_JCA_SPEC), VOLUME declarations (apks, out, results), and COPY + chmod for the entrypoint script.
- [x] 5.2 Create `docker/rvandroid_dev/Dockerfile`: based on `phtcosta/rvandroid_tools:0.8.0`, COPY local Poetry files and module sources, run `poetry install`, COPY entrypoint script. Build context is the repo root.
- [x] 5.3 Create `docker/docker-compose.parallel.yml` with YAML anchors (`x-rvandroid` base), Humanoid service with healthcheck, and rv01/rv02 service definitions with per-container volumes and experiment names. Support env var overrides (BASE_DIR, RV_TOOLS, RV_TIMEOUTS, CPUS, MEMORY).
- [x] 5.4 Update `docker/docker-compose.yml`: add rvandroid service with env vars, volumes (apks, out, results), device `/dev/kvm`, resource limits, and Humanoid dependency.
- [x] 5.5 Clean `docker/tools/Dockerfile`: remove all commented-out legacy code (~80 lines of Sapienz, Stoat, Humanoid, pyflann, legacy env vars). Keep only DroidBot installation.
- [x] 5.6 Update `docker/build_all.sh`: ensure all 4 image layers are built in order (base, android, tools, rvandroid) with error handling.

## 6. Unit Tests for Resume and Result Consolidation

Write unit tests BEFORE implementing the bug fixes (tests U7-U10 will initially fail — this is the expected TDD RED phase). Tests U1-U6 and U11-U14 verify already-implemented behavior and should pass.

### 6.1 rv-platform Resume Unit Tests

- [x] 6.1.1 Create `modules/rv-platform/tests/execution/test_resume.py` with tests U1-U10 from design.md Testing Strategy:
  - U1: `test_skip_completed_tasks_filters_by_identity` — Mock TaskStorage with 2 completed tasks, generate 5 tasks, verify 3 remain after filtering
  - U2: `test_skip_completed_tasks_stores_skipped_count` — Mock TaskStorage with 3 completed tasks, verify `_skipped_count == 3`
  - U3: `test_skip_completed_tasks_does_not_skip_error_tasks` — Mock TaskStorage with ERROR tasks, verify they remain in task list
  - U4: `test_skip_completed_tasks_checksum_mismatch_warns` — Mock TaskStorage with different checksum, verify warning logged
  - U5: `test_skip_completed_tasks_checksum_match_no_warning` — Mock TaskStorage with same checksum, verify no warning
  - U6: `test_metadata_created_after_task_generation` — Mock dependencies, verify `set_experiment_metadata()` called
  - U7: `test_process_results_uses_all_completed_tasks` — Mock TaskStorage with 3 completed tasks, verify ResultProcessorComponent receives all 3 (**EXPECTED TO FAIL before fix**)
  - U8: `test_generate_summary_includes_skipped_count` — Verify summary dict has `skipped_tasks` field (**EXPECTED TO FAIL before fix**)
  - U9: `test_generate_summary_total_includes_skipped` — Verify `total_tasks` reflects only executed tasks and `skipped_tasks` is reported separately (**EXPECTED TO FAIL before fix**)
  - U10: `test_no_resume_skipped_count_zero` — Run without any completed tasks, verify `skipped_tasks: 0`

- [x] 6.1.2 Run rv-platform tests: verify U1-U6 and U10 pass, U7-U9 fail (RED phase for result consolidation fix). Result: 6 PASS, 4 FAIL (U2, U7, U8, U9 — all expected pre-fix failures)

### 6.2 rv-experiment Resume Unit Tests

- [x] 6.2.1 Create tests U11-U14 in `modules/rv-experiment/tests/` (use existing test file structure or create `tests/test_resume_cli.py`):
  - U11: `test_cli_resume_dir_sets_skip_flags` — Mock CLI invocation with `--resume-dir`, assert all 3 skip flags are True
  - U12: `test_cli_name_detects_existing_results` — Create temp dir with `tasks.json`, verify `resume_mode=True`
  - U13: `test_cli_name_first_run_no_resume` — Mock CLI with `--name` pointing to non-existent dir, verify `resume_mode=False`
  - U14: `test_cli_resume_dir_overrides_name` — Mock CLI with both flags, verify results dir from `--resume-dir`

- [x] 6.2.2 Run rv-experiment tests: verify U11-U14 all pass (these test already-implemented logic). Result: 4 PASS

## 7. Result Consolidation Bug Fix (rv-platform)

These changes fix the result consolidation bug discovered during smoke testing (see design.md "Bug: Result Consolidation on Resume" section). Changes are made AFTER unit tests exist (task 6), following TDD RED-GREEN flow: tests U7-U9 fail before these changes and pass after.

- [x] 7.1 In `Platform.__init__()`: add `self._skipped_count = 0` to track the number of skipped tasks across the resume flow.

- [x] 7.2 In `_skip_completed_tasks()`: after computing `skipped = original_count - len(self.tasks)`, store the value in `self._skipped_count = skipped`. This preserves the count for use in `_generate_summary()`.

- [x] 7.3 In `_process_results()`: replace `ResultProcessorComponent(self.tasks, ...)` with `ResultProcessorComponent(list(self.task_storage.get_completed_tasks()), ...)`. This ensures that all completed tasks from all sessions (loaded from `tasks.json` + executed in this session) are included in the output files.

- [x] 7.4 In `_generate_summary()`: add `skipped_count: int = 0` parameter. Include `skipped_tasks` in the returned dict. Update log message to: "Execution summary: {successful_tasks}/{total_tasks} tasks successful ({skipped_count} skipped from previous runs)".

- [x] 7.5 In `run()`: pass `self._skipped_count` to `_generate_summary(results, self._skipped_count)`.

- [x] 7.6 In `__main__.py` `cmd_run()`: after printing "Total tasks:", add conditional display: if `results.get('skipped_tasks', 0) > 0`, print "Skipped (from previous runs): {skipped_tasks}".

- [x] 7.7 Run rv-platform tests again: verify U7-U9 now pass (GREEN phase). All 10 resume tests (U1-U10) pass. Result: 10 PASS, 0 FAIL

- [x] 7.8 Fix ExperimentController double-nesting bug (discovered during smoke test 8.2.1): `ExperimentController.__init__()` appended `config.name` to `config.results_dir`, creating `results/<name>/<name>/`. Changed to use `config.results_dir` directly. Removed dead `experiment_dir` field from `ExperimentConfig` and the `get_experiment_dir` import from `config.py`. All 14 existing tests pass after fix.

## 8. Smoke Tests (Manual, with Emulator)

Run AFTER unit tests pass (task 6) and bug fixes are implemented (task 7). These validate end-to-end behavior with a real emulator. See design.md "Smoke Tests" section for detailed steps.

### 8.1 rv-platform Smoke Tests

rv-platform runs independently without pre-processing (no monitors, no instrumentation, no static analysis). These tests validate the core resume mechanism in isolation.

- [x] 8.1.1 **rv-platform Form 1 (Expand Experiment)** — Run with monkey: 1 rep then 2 reps. Result: PASSED. tasks.json=2 COMPLETED, summary.csv=2 rows, "Skipped (from previous runs): 1", logcats for both reps.

- [x] 8.1.2 **rv-platform Form 2 (Crash Recovery)** — Run with ape: 3 reps bg, kill after rep 1 completes, cleanup emulator locks/qcow2, re-run. Result: PASSED. Rep 1 skipped, reps 2+3 executed and completed. tasks.json=3 COMPLETED, summary.csv=3 rows, logcats for all 3 reps. Note: monkey fails with non-zero exit codes after emulator kill/restart — ape handles this correctly.

### 8.2 rv-experiment Smoke Tests

rv-experiment wraps rv-platform with pre-processing (monitor generation, APK instrumentation, static analysis). These tests validate resume through the full pipeline, including auto-skip of pre-processing on resume (INV-EXP-13).

- [x] 8.2.1 **rv-experiment Form 1 (Expand Experiment)** — Run rv-experiment with `--name smoke_exp --repetitions 1`, then run again with `--name smoke_exp --repetitions 2`. Result: **PASSED** (re-tested after task 10 logcat re-reading fix). Resume mechanism works correctly: pre-processing auto-skipped on second run ("Resuming experiment 'smoke_exp' — auto-skipping pre-processing"), rep 1 skipped, rep 2 executed, results consolidated, flat directory structure. `summary.csv` has 2 rows (rep 1: 75%/14.41%/32%/3 errors, rep 2: 50%/9.32%/22%/3 errors). `errors.csv` has 6 rows — 3 for rep 1 (reconstructed from logcat via `_reconstruct_repository_from_logcat`) + 3 for rep 2 (from runtime repository). `results.json` has complete `monitored_operations_errors` with details for both reps. `tasks.json` has 2 COMPLETED tasks.

- [x] 8.2.2 **rv-experiment Form 2 (Crash Recovery)** — Run rv-experiment with `--name smoke_exp --repetitions 3` in background, waited ~11 min (pre-processing + rep 1), killed process + emulator, cleaned locks/qcow2, re-ran same command. Result: **PASSED**. Resume auto-detected: "Resuming experiment 'smoke_exp' — auto-skipping pre-processing". Rep 1 skipped, reps 2+3 executed (both COMPLETED). `summary.csv` has 3 rows. `errors.csv` has 3 rows (rep 2 had 3 MOP violations, reps 1+3 had 0). `tasks.json` has 3 COMPLETED tasks. Log confirms "Execution summary: 2/2 tasks successful (1 skipped from previous runs)". Logcat reconstruction for rep 1 correctly returned 0 violations (matching `total_errors: 0` in coverage_metrics).

## 10. MOP Violation Reconstruction from Logcat (rv-platform)

This task fixes the empty `errors.csv` bug discovered during smoke test 8.2.1. `ResultProcessorComponent` generates MOP violation data (monitored operations violations detected by runtime verification monitors) from `task.repository`, which is `None` for tasks loaded from `tasks.json` on resume. The fix re-reads the persisted logcat file to reconstruct violation data. See design.md D9 decision and platform delta spec "Logcat Re-Reading for MOP Violation Reconstruction" scenario.

### 10.1 Unit Tests (TDD RED phase)

- [x] 10.1.1 Create tests U15-U17 in `modules/rv-platform/tests/execution/test_resume.py`:
  - U15: `test_result_processor_reconstructs_violations_from_logcat` — Create mock task with `repository=None` and a logcat file containing `RVSEC` entries; verify `errors.csv` has MOP violation rows after `ResultProcessorComponent.execute()`
  - U16: `test_result_processor_handles_missing_logcat` — Create mock task with `repository=None` and `logcat_file` pointing to non-existent path; verify warning logged and `errors.csv` has no rows for that task
  - U17: `test_result_processor_json_includes_violation_details_from_logcat` — Create mock task with `repository=None` and logcat with `RVSEC` entries; verify `results.json` `monitored_operations_errors` has correct `total`, `messages`, and `details`

- [x] 10.1.2 Run tests: verify U15-U17 FAIL (RED phase — implementation not yet done). Existing U1-U10 should still pass. Result: 10 PASS (U1-U10), 3 FAIL (U15-U17) — as expected.

### 10.2 Implementation

- [x] 10.2.1 Add `_reconstruct_repository_from_logcat(self, task)` method to `ResultProcessorComponent` in `modules/rv-platform/src/rv_platform/components/result_processor.py`:
  - Check `task.result.logcat_file` exists and is a file on disk
  - Call `parse_logcat_file(logcat_file)` from `rv_coverage.parser.log.logcat_parser`
  - Return the `LogcatRepository` (or `None` if file doesn't exist)
  - Log warning if logcat file is missing

- [x] 10.2.2 Update `_write_task_error_data()`: When `task.repository` is `None`, try `_reconstruct_repository_from_logcat(task)`. If a repository is obtained, use `repository.get_errors()` to write MOP violation rows. Otherwise skip (no data source).

- [x] 10.2.3 Update `_extract_task_data()`: When `task.repository` is `None`, try `_reconstruct_repository_from_logcat(task)` for MOP violation details (total, messages, details). Summary data still comes from `task.result.coverage_metrics` (serialized).

- [x] 10.2.4 `_write_task_coverage_data()` — No change needed. The existing fallback (single summary row from `task.result.coverage_metrics`) is correct. The reconstructed repository from logcat cannot provide per-method coverage data because `register_method_call()` requires static analysis class data.

### 10.3 Verification

- [x] 10.3.1 Run tests: verify U15-U17 now PASS (GREEN phase). All existing tests (U1-U14) should still pass. Result: 13 PASS (U1-U10 + U15-U17 in rv-platform), 4 PASS (U11-U14 in rv-experiment) — all 17 tests pass.

- [x] 10.3.2 Re-run smoke test 8.2.1 (rv-experiment Form 1): verify `errors.csv` now has MOP violation rows for rep 1 (reconstructed from logcat), `results.json` has violation details, `summary.csv` unchanged. Result: PASSED. `errors.csv` has 6 rows (3 per rep), `results.json` has full violation details for both reps, log shows "Reconstructed 3 MOP violations from logcat for task a01b26d0".

- [x] 10.3.3 Run smoke test 8.2.2 (rv-experiment Form 2: Crash Recovery) — Validates interrupted rv-experiment resume with MOP violation reconstruction. Result: PASSED. See 8.2.2 for details.

## 9. Documentation Update

- [x] 9.1 Update documentation to reflect resume functionality. Updated 6 files: `modules/rv-platform/CLAUDE.md` (resume section, MOP violation reconstruction, key fields, test structure), `modules/rv-platform/README.md` (resume usage example), `modules/rv-platform/docs/architecture.md` (resume flow diagram, MOP reconstruction), `modules/rv-experiment/CLAUDE.md` (resume section with examples, test structure), `modules/rv-experiment/README.md` (resume CLI options, examples, behavior), `modules/rv-experiment/docs/architecture.md` (resume scenario, ExperimentConfig fields).

- [x] 9.2 Clean up manual test data: `rm -rf results/smoke_test/ results/smoke_exp/` and any other test directories created during smoke testing. Done.

## 11. Docker Compose — docker.sock Mount

The `docker.sock` volume mount allows the rvandroid container to spawn ARES/QTesting sibling containers via the host's Docker daemon. Without this mount, `docker run` inside the container fails because there is no Docker daemon available. See design.md D10 for architectural rationale.

- [x] 11.1 Add `/var/run/docker.sock:/var/run/docker.sock` volume to the `rvandroid` service in `docker/docker-compose.yml`.
- [x] 11.2 Add `/var/run/docker.sock:/var/run/docker.sock` volume to the `x-rvandroid` anchor in `docker/docker-compose.parallel.yml` and to rv01/rv02 volumes (since they override the anchor's volumes).

**Acceptance criteria:**
- Both compose files include the docker.sock mount
- `docker compose config` validates without errors for both files

## 12. ARES/QTesting Docker Network Fix (Tool Code)

When running inside a Docker container, ARES and QTesting sibling containers need `--network container:$(hostname)` to share the parent container's network namespace and reach the emulator at `localhost:5554`. Without this flag, the sibling container gets its own isolated network and cannot connect to the emulator. The detection uses `os.path.exists('/.dockerenv')`, which is the standard mechanism for detecting Docker execution context. See design.md D10 for architectural rationale.

In parallel execution (7 rvandroid containers), each container spawns its own ARES/QTesting sibling with `--network container:<its-own-container-id>`. Each sibling reaches only its parent's emulator — no cross-container interference.

- [x] 12.1 In `modules/rv-tools/src/rv_tools/builtin/ares/tool.py`, method `_build_ares_command()`: after volume mapping and before Docker image, added `--network container:{socket.gethostname()}` when `os.path.exists('/.dockerenv')`. Added `import socket`.
- [x] 12.2 In `modules/rv-tools/src/rv_tools/builtin/qtesting/tool.py`, method `_build_qtesting_command()`: same change — after device serial and before Docker image, added network flag with `/.dockerenv` detection. Added `import socket`.

**Acceptance criteria:**
- When running inside Docker (`/.dockerenv` exists), the spawned ARES/QTesting container command includes `--network container:<hostname>`
- When running outside Docker, no `--network` flag is added (standalone behavior unchanged)
- No changes to ARES/QTesting Dockerfiles or internal logic

## 13. Update build_all.sh

Add ARES and QTesting image builds as steps 5/6 and 6/6 to `docker/build_all.sh`. These images must be pre-built on the host because rvandroid containers spawn them at runtime via `docker run` — they are not pulled from a registry.

Note: QTesting's `build.sh` references a `DockerfileSdkman` that does not exist. The main `Dockerfile` is self-contained (`FROM python:3.10-slim`) and does not need a separate base image. The fix is to call `docker build` directly, skipping the Sdkman step.

- [x] 13.1 Add ARES image build step (5/6) to `docker/build_all.sh`. Uses `docker build --no-cache -t phtcosta/ares:latest` directly from `modules/rv-tools/src/rv_tools/builtin/ares/`.
- [x] 13.2 Add QTesting image build step (6/6) to `docker/build_all.sh`. Builds directly from `modules/rv-tools/src/rv_tools/builtin/qtesting/Dockerfile`, bypassing the broken `build.sh` that references the missing `DockerfileSdkman`. The main Dockerfile is self-contained (`FROM python:3.10-slim`).
- [x] 13.3 Updated script header, step labels (1/6 through 6/6), and final message to reflect 6 images. Added `REPO_ROOT` variable for clean path resolution.

**Acceptance criteria:**
- `docker/build_all.sh` builds all 6 images in correct dependency order: base → android → tools → rvandroid → ares → qtesting
- Script uses `set -e` to fail fast on build errors
- ARES and QTesting builds do not depend on missing files (no DockerfileSdkman reference)

## 14. Build Docker Images

Build all 6 images in dependency order. Fix any Dockerfile issues discovered during builds. This is the first time these images are being built — expect potential issues with base images, package versions, or missing files.

Build order:
1. `phtcosta/rvsec_base:0.8.0` — `docker/base/build.sh`
2. `phtcosta/rvsec_android:0.8.0` — `docker/android/build.sh`
3. `phtcosta/rvandroid_tools:0.8.0` — `docker/tools/build.sh`
4. `phtcosta/rvandroid:0.8.0` — `docker/rvandroid/build.sh`
5. `phtcosta/ares:latest` — from `modules/rv-tools/.../ares/Dockerfile`
6. `phtcosta/qtesting:latest` — from `modules/rv-tools/.../qtesting/Dockerfile`

- [x] 14.1 Build base image (`phtcosta/rvsec_base:0.8.0`) — 1.29GB, built successfully
- [x] 14.2 Build android image (`phtcosta/rvsec_android:0.8.0`) — 8.18GB, built successfully
- [x] 14.3 Build tools image (`phtcosta/rvandroid_tools:0.8.0`) — 8.59GB, built successfully
- [x] 14.4 Build rvandroid image (`phtcosta/rvandroid:0.8.0`) — 27.9GB, built successfully
- [x] 14.5 Build ares image (`phtcosta/ares:latest`) — 4.6GB, built successfully from `jtpastro/docker-adb` base
- [x] 14.6 Build qtesting image (`phtcosta/qtesting:latest`) — 3.69GB, built successfully. **Fix applied**: changed `openjdk-17-jre` to `default-jre-headless` in `modules/rv-tools/src/rv_tools/builtin/qtesting/Dockerfile` because `openjdk-17-jre` is not available in Debian Trixie (the base OS of `python:3.10-slim`)

**Acceptance criteria:**
- All 6 images build without errors
- `docker images | grep phtcosta` shows all 6 images with correct tags
- No dangling intermediate images left behind

**Known risks:**
- ARES Dockerfile uses `jtpastro/docker-adb` as base — may be unavailable or outdated
- QTesting Dockerfile downloads Android SDK tools — download URL may be stale
- Base image build takes ~15-20 min (JDK, Maven, Android SDK)

## 17. Fix Monkey Command Builder (rv-tools)

The `_build_monkey_command()` method had hardcoded values instead of reading from `self.config`. This meant variants (`fast`, `stress`) and `configure()` parameters had no effect on the actual command. See design.md D11 for root cause analysis.

- [x] 17.1 Update `_build_monkey_command()` in `modules/rv-tools/src/rv_tools/builtin/monkey/tool.py` to use `self.config` for: `event_count`, `throttle`, `ignore_crashes`, `ignore_timeouts`, `verbosity`, `seed`. Default behavior unchanged (same values as before when using default config). Validated by Docker tool test 15.3.a.

**Acceptance criteria:**
- `_build_monkey_command()` reads all relevant fields from `self.config`
- Default variant produces the same command as before (backward compatible)
- `fast` variant now actually adds `--ignore-crashes` and `--ignore-timeouts` flags
- `throttle > 0` adds `--throttle N` flag

## 18. Build Dev Docker Image

Build the dev image (`phtcosta/rvandroid_dev:0.8.0`) using local source code. This avoids the commit+push+rebuild cycle needed for the production image and enables rapid iteration on tool fixes.

- [x] 18.1 Build dev image: `docker/rvandroid_dev/build.sh`. Build context is the repo root — includes local monkey fix and all other local changes. Built in ~4.5min, 174 packages installed.
- [x] 18.2 Verify dev image starts correctly: `docker run --rm --device /dev/kvm phtcosta/rvandroid_dev:0.8.0 bash -c "poetry run rv-experiment --help"` — PASSED. CLI shows full help.
- [x] 18.3 Rebuild dev image after tasks 17, 19, 20. Build succeeded: 117 packages installed (vs 174 before — 57 fewer without discontinued modules). 13 active modules installed. CLI works. Tool registry shows 9 tools (8 ICST + rvagent). Discontinued tools log warnings only.

**Acceptance criteria:**
- `phtcosta/rvandroid_dev:0.8.0` image built successfully
- Entry point and CLI work identically to production image
- Local code changes (monkey fix, droidbot fix, resume, etc.) are reflected in the image

## 15. Docker Smoke Tests

Verify that Docker images work correctly. Tests 15.1-15.4 were validated with the production image (task 14). Tests 15.3.x (per-tool validation) and 15.5 use the dev image (task 18) to enable rapid iteration on fixes.

- [x] 15.1 **Entry Point**: PASSED (prod image). Entry point intercepts `bash` correctly, CLI shows full help with commands (run, config, list-tools, validate). Working directory is `/opt/rvsec/rv-android`.
- [x] 15.2 **Tool Registry**: PASSED (prod image). All 10 tools registered: ape, monkey, ares, droidbot, droidmate, fastbot, humanoid, qtesting, rvdroid, rvagent.
- [x] 15.4 **Docker CLI in Container**: PASSED (prod image). `docker` binary available at `/usr/bin/docker`. With docker.sock mount, container can list running containers on the host via `docker ps`.

### 15.3 Docker Tool Validation (dev image)

Validates all 8 ICST official tools (11 configurations) + rvagent:pure_algorithm (12 total) inside Docker. Each tool tested with 60s timeout against `cryptoapp.apk` with KVM. See design.md "Docker Tool Validation Tests" for ICST tool mapping, tiered approach, methodology, and the **Verification Protocol** (6-check protocol with Docker run template and post-test commands).

**Verification Protocol**: Defined in design.md section "Docker Tool Validation Tests → Verification Protocol". Each tool test must pass ALL 6 checks before being marked PASSED:
1. Exit code = 0
2. tasks.json: `result.state = COMPLETED`
3. summary.csv: 1 row, tool:variant matches
4. Tool execution evidence (log grep — tool-specific pattern, see design.md table)
5. Trace file analysis (`.trace` exists, non-trivial size, tool-specific execution records — see design.md table)
6. No crash artifacts (all tracebacks in log must be identified as handled; no unhandled exceptions)

**Result artifacts location**: `/tmp/docker_test_<tool>/` (host volume mount) and `/tmp/docker_test_<tool>.log` (tee'd output).

**Each test result below must document all 6 checks explicitly**.

**Tier 1 — Standalone (`docker run --device /dev/kvm`)**:

- [x] 15.3.a **monkey:fast**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_monkey/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=monkey, variant=fast, apk=cryptoapp.apk
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,monkey:fast,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `adb -s emulator-5554 shell monkey -v --ignore-crashes --ignore-timeouts --ignore-security-exceptions -s 12345 -p br.unb.cic.cryptoapp 1000000000` — ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__monkey:fast.trace` (103KB) — 236 `:Sending Touch/Trackball` lines, last event counter `// Sending event #1200`. Logcat file has only headers (no MOP violations — APKs not instrumented, skip flags active).
  - Check 6 (no crashes): 3 tracebacks in log are the expected timeout chain (`subprocess.TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handled by error handler with `"Tool timeout (expected)"`
- [x] 15.3.b **ape**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_ape/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=ape:default, apk=cryptoapp.apk
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,ape,0.0,0.0,0.0,0`
  - Check 4 (log evidence): APE JAR pushed to `/data/local/tmp/ape.jar`, executed via `app_process` with `--ape sata` strategy, ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__ape.trace` (290KB, 2558 lines) — 35 SATA steps, state creation/exploration, activity transitions (MainActivity, CryptographyActivity). Also `ape_output/` directory created.
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
- [x] 15.3.c **droidbot:dfs_greedy**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_droidbot_dfs_greedy/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=droidbot:dfs_greedy
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,droidbot:dfs_greedy,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `poetry run droidbot -d emulator-5554 -a .../cryptoapp.apk -policy dfs_greedy -count 10000000000 -timeout 60 -ignore_ad -is_emulator` — DroidBot configured with Policy: dfs_greedy, ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__droidbot:dfs_greedy.trace` (89KB, 1682 lines) — 8 Actions (TouchEvent, IntentEvent, KeyEvent, KillAppEvent), 14 UtgGreedySearchPolicy entries, state transitions, DroidBotAppConn restarts (normal accessibility adapter reconnections)
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
- [x] 15.3.d **droidbot:bfs_greedy**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_droidbot_bfs_greedy/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=droidbot:bfs_greedy
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,droidbot:bfs_greedy,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `poetry run droidbot -d emulator-5554 -a .../cryptoapp.apk -policy bfs_greedy -count 10000000000 -timeout 60 -ignore_ad -is_emulator` — DroidBot configured with Policy: bfs_greedy, ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__droidbot:bfs_greedy.trace` (39KB, 723 lines) — 10 Actions (TouchEvent on Button-MESSAGE DI/ImageView, IntentEvent, KeyEvent, KillAppEvent), UtgGreedySearchPolicy exploration, state transitions
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
- [x] 15.3.e **droidbot:dfs_naive**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_droidbot_dfs_naive/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=droidbot:dfs_naive
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,droidbot:dfs_naive,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `poetry run droidbot -d emulator-5554 -a .../cryptoapp.apk -policy dfs_naive -count 10000000000 -timeout 60 -ignore_ad -is_emulator` — DroidBot configured with Policy: dfs_naive, ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__droidbot:dfs_naive.trace` (14KB, 248 lines) — 11 Actions (TouchEvent on TextView-Crypto App/ImageView/Button-MESSAGE DI, IntentEvent, KeyEvent, KillAppEvent), UtgNaiveSearchPolicy selecting un-clicked views, activity transitions (MainActivity, MessageDigestActivity)
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
- [x] 15.3.f **droidbot:bfs_naive**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_droidbot_bfs_naive/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=droidbot:bfs_naive
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,droidbot:bfs_naive,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `poetry run droidbot -d emulator-5554 -a .../cryptoapp.apk -policy bfs_naive -count 10000000000 -timeout 60 -ignore_ad -is_emulator` — DroidBot configured with Policy: bfs_naive, ran full 60s timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__droidbot:bfs_naive.trace` (54KB, 1019 lines) — 7 Actions (TouchEvent on TextView-Crypto App/ImageView/Button-MESSAGE DI, IntentEvent, KeyEvent, KillAppEvent), UtgNaiveSearchPolicy selecting un-clicked views, state transitions
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
- [x] 15.3.g **fastbot**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_fastbot/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=fastbot:default
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,fastbot,0.0,0.0,0.0,0`
  - Check 4 (log evidence): 3 FastBot JARs pushed (fastbot-thirdpart.jar, framework.jar, monkeyq.jar), `Starting FastBot execution for br.unb.cic.cryptoapp`, completed within timeout
  - Check 5 (trace file): `cryptoapp.apk__1__60__fastbot.trace` (54KB, 699 lines) — events up to #300+, touch actions with coordinates (ACTION_DOWN/MOVE/UP), model-based exploration, activity filtering (NOT USING 14+ system activities)
  - Check 6 (no crashes): 0 tracebacks — clean execution, FastBot finished within timeout (no timeout chain)
- [x] 15.3.h **rvagent:pure_algorithm**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_rvagent/`.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=rvagent:pure_algorithm
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,rvagent:pure_algorithm,0.0,0.0,0.0,0`
  - Check 4 (log evidence): AgentFactory created RVAgent, DeviceInterface connected to emulator-5554, RVAgentStrategy initialized with pure_algorithm mode, algorithm_node executing CLICK/SET_TEXT/KEY_EVENT actions
  - Check 5 (metrics file): `br.unb.cic.cryptoapp__1__60__rvagent:pure_algorithm.rvagent_metrics.json` (4KB) — 4 iterations, 3 unique states, 4 total actions (100% algorithm), 26 unique UI elements, 3 screens visited, 11.5% element coverage. Note: rvagent produces `.rvagent_metrics.json` instead of `.trace`
  - Check 6 (no crashes): 0 tracebacks — clean execution

**Tier 2 — External Service (`docker-compose` with humanoid service)**:

- [x] 15.3.i **humanoid**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_humanoid/`. Prerequisite: D15 humanoid tool rewrite (Task 21).
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=humanoid:default
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,humanoid,0.0,0.0,0.0,0`
  - Check 4 (log evidence): `Configured Humanoid tool - Policy: dfs_greedy, Humanoid URL: rv-humanoid:50405`, command: `poetry run droidbot -d emulator-5554 -a .../cryptoapp.apk -humanoid rv-humanoid:50405 -policy dfs_greedy -count 10000000000 -timeout 60 -ignore_ad -is_emulator`
  - Check 5 (trace file): `cryptoapp.apk__1__60__humanoid.trace` (22KB, 403 lines) — DroidBot exploration with UtgGreedySearchPolicy, TouchEvent actions on CipherActivity views (TextView-Crypto App, EditText-Input text, Button-ENCRYPT), state transitions between CipherActivity states
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`
  - **Test infrastructure**: Docker network `rv-test`, humanoid server (`phtcosta/humanoid:1.0`) as named container `rv-humanoid`, rvandroid container with `--network rv-test` and `RV_HUMANOID_URL=rv-humanoid:50405`

**Tier 3 — Sibling Container (docker.sock mount)**:

- [x] 15.3.j **ares**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_ares/`. Prerequisite: D16 ARES tool rewrite (Task 22).
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=ares:default, execution_time=115s
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,ares,0.0,0.0,0.0,0`
  - Check 4 (log evidence): Container `ares_ac7de587` created with `phtcosta/ares:latest`, env vars `EMUNAME=emulator-5554 TIMEOUT_IN_MINUTES=1`, APK copied via `docker cp .../cryptoapp.apk ares_ac7de587:/ares/apks/app.apk`, started with `docker start -a`, network `--network container:$(hostname)` (inside Docker)
  - Check 5 (trace file): `cryptoapp.apk__1__60__ares.trace` (1843 bytes, 20 lines) — ARES RL exploration: `EPISODE RESET`, SAC actions on `buttonMessageDigest`, `spinnerMessageDigest`, `editTextMessageDigest`, activity transitions between `MainActivity` and `MessageDigestActivity`, text input (`put string: string2`), orientation changes
  - Check 6 (no crashes): 3 tracebacks are expected timeout chain (`subprocess.TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"` and `"Completed tool: ares (timeout)"`
  - **Test infrastructure**: docker.sock mount (`-v /var/run/docker.sock:/var/run/docker.sock`), pre-built `phtcosta/ares:latest` image, network sharing via `--network container:$(hostname)` inside Docker
- [x] 15.3.k **qtesting**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_qtesting/`. Prerequisite: D17 QTesting tool rewrite (Task 23) + struct.py removal.
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=qtesting:default, execution_time=112s
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,qtesting,0.0,0.0,0.0,0`
  - Check 4 (log evidence): Container `qtesting_fa9fff96` created with `phtcosta/qtesting:latest`, APK copied via `docker cp`, conf.txt copied via `docker cp`, started with `docker start -a`, network `--network container:$(hostname)` (inside Docker), full container lifecycle (create → cp → start → timeout → cleanup)
  - Check 5 (trace file): `cryptoapp.apk__1__60__qtesting.trace` (3195 bytes, 37 lines) — TensorFlow/CUDA initialization, `adb root`, package extraction (`br.unb.cic.cryptoapp`), activity launch (`MainActivity`), Siamese LSTM model loaded (126K params, Sequential + ManDist layers), Q-learning started (`==============start testing=============`)
  - Check 6 (no crashes): 1 traceback is the expected timeout chain (`RVToolTimeoutError: qtesting execution timed out after 60.0 seconds caused by RVCommandTimeoutError`), handler logs `"Tool timeout (expected)"`. Boot polling warnings (`getprop init.svc.bootanim` exit code 1) are normal emulator startup.
  - **Test infrastructure**: docker.sock mount (`-v /var/run/docker.sock:/var/run/docker.sock`), pre-built `phtcosta/qtesting:latest` image (rebuilt without struct.py), network sharing via `--network container:$(hostname)` inside Docker

**Tier 4 — External Artifact (TOOLS_DIR volume)**:

- [x] 15.3.l **droidmate**: PASSED (all 6 checks). Artifacts: `/tmp/docker_test_droidmate/`. Prerequisite: D18 DroidMate CLI flags fix (Task 24).
  - Check 1 (exit code): 0 — log ends with "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, tool=droidmate:default, execution_time=112s
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,droidmate,0.0,0.0,0.0,0`
  - Check 4 (log evidence): Correct DroidMate-2 command: `java -jar .../droidmate-2-X.X.X-all.jar --Exploration-apkNames=cryptoapp.apk --Exploration-apksDir=/opt/rvsec/rv-android/apks --Output-outputDir=.../droidmate_output --Selectors-timeLimit=60000 --Selectors-actionLimit=100000000 --Core-logLevel=debug`. JAR resolved via JarResolver at module directory.
  - Check 5 (trace file): `cryptoapp.apk__1__60__droidmate.trace` (15110 bytes) — DroidMate-2 copyright, configuration dump (apksDirPath, outputDir, deviceSerialNumber=null), 9 exploration strategies registered (RandomWidget, actionBasedTerminate, timeBasedTerminate, etc.), APK processing (br.unb.cic.cryptoapp), device setup (emulator-5554), UiAutomator2 daemon installed, exploration loop with LaunchApp + ClickEvent actions, screenshots pulled, "remaining exploration time" decreasing. Also `droidmate_output/` directory created with model, images, report subdirectories.
  - Check 6 (no crashes): 1 traceback is the expected timeout chain (`RVToolTimeoutError: droidmate execution timed out after 60.0 seconds`), handler logs `"Tool timeout (expected)"`. Boot polling warnings are normal emulator startup.
  - **Note**: DroidMate JAR (`droidmate-2-X.X.X-all.jar`, 46MB) is bundled in the module directory — no external volume mount needed. No TOOLS_DIR env var required.

**Acceptance criteria:**
- Minimum (Tier 1): monkey, ape, droidbot (4 ICST variants), fastbot, rvagent:pure_algorithm — 8 configurations execute successfully (all 6 verification checks pass)
- Extended (Tier 2-3): + humanoid, ares, qtesting — 11 configurations
- Full ICST (all tiers): + droidmate — all 11 ICST configurations + rvagent:pure_algorithm = 12 total

### 15.5 Resume in Docker (dev image)

- [x] 15.5 **Resume in Docker**: PASSED (all 6 checks). Test used `monkey:fast` (not default `monkey` — default variant lacks `--ignore-crashes` and exits with code 29 on app crash, causing task ERROR state).
  - **Run 1**: Started container with `RV_TOOLS=monkey:fast`, `RV_REPETITIONS=2`, `RV_EXPERIMENT_NAME=docker_resume_test`. Rep 1 completed successfully (COMPLETED state in tasks.json). Killed container during rep 2 execution with `docker kill`.
  - **Run 2**: Re-ran same command. Resume mechanism activated:
    - "Resuming experiment 'docker_resume_test' — auto-skipping pre-processing"
    - "Loading tasks from results/docker_resume_test/tasks.json"
    - "Resume: skipped 1 already-completed tasks (1 remaining)"
    - Rep 2 executed and completed
    - "Execution summary: 1/1 tasks successful (1 skipped from previous runs)"
  - Check 1 (exit code): 0 — "Experiment completed successfully"
  - Check 2 (tasks.json): 2 tasks, both COMPLETED, 100% completion, 0 failed. Rep 1 preserved from run 1 (task ID `be652535`), rep 2 completed in run 2 (new task ID `3793af6c`).
  - Check 3 (result files): 4 files — `cryptoapp.apk__1__60__monkey:fast.trace` (29KB, from run 1), `cryptoapp.apk__2__60__monkey:fast.trace` (102KB, from run 2), 2 logcat files.
  - Check 4 (resume evidence): All 4 resume log messages present (see above). Pre-processing auto-skipped. Rep 1 skipped.
  - Check 5 (tool execution): Monkey:fast ran only for rep 2 (60s timeout, expected timeout chain). No execution of rep 1 tool (skipped).
  - Check 6 (no crashes): Only expected timeout chain (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`), handler logs `"Tool timeout (expected)"`.
  - **Note**: First attempt with `monkey` default variant failed — monkey exited with code 29 (app crash, no `--ignore-crashes` flag), causing `RVToolExecutionError` and task ERROR state. The resume mechanism correctly does NOT skip ERROR tasks (only COMPLETED), which is the intended behavior. Used `monkey:fast` for successful test.

## 16. Update Change Documents

Update design.md and tasks.md to reflect the expanded scope (ARES/QTesting Docker sibling containers). Update delta specs to document the Docker network behavior for ARES/QTesting tool execution.

- [x] 16.1 In `design.md`: move "ARES and QTesting Docker sibling containers" from Non-Goals to Goals.
- [x] 16.2 In `design.md`: add D10 decision — "Docker Network for Sibling Containers" — documenting the `--network container:$(hostname)` approach with `/.dockerenv` detection, including the parallel execution architecture (7 containers, each with its own sibling).
- [x] 16.3 In `design.md`: add architecture diagram for the sibling container pattern.
- [x] 16.4 In `tasks.md`: add tasks 11-16 with subtasks and acceptance criteria.
- [x] 16.5 In `openspec/changes/resume-docker/specs/tools/spec.md`: create delta spec for the tools domain documenting Docker network behavior for ARES and QTesting tool execution (new invariant INV-TOOL-15 for Docker-aware command building).
- [x] 16.6 In `openspec/changes/resume-docker/specs/experiment/spec.md`: add Docker Execution Mode requirement (FR16-ext, NFR08) documenting docker-entrypoint.sh, env var translation, docker-compose files, parallel execution, docker.sock mount, and startup delay.

## 19. Fix DroidBot `device_serial` Bug (D12)

Regression introduced during module refactoring. The original DroidBot code used a hardcoded `device_id: "emulator-5554"` default. The refactored `configure()` changed this to `config.get("device_serial", None)`, which stores `None` when no `device_serial` is provided. Combined with the `Command` class gaining Pydantic validation (`@field_validator('args')` rejecting non-string elements), this causes ALL DroidBot variants to fail with `args.3=None` validation error. See design.md D12 for full root cause analysis and comparison with all other tools.

- [x] 19.1 In `modules/rv-tools/src/rv_tools/builtin/droidbot/tool.py`, `configure()` line 172: change `config.get("device_serial", None)` to `config.get("device_serial", "emulator-5554")`. This is the root fix — matching the original code behavior and how APE handles it.
- [x] 19.2 In `modules/rv-tools/src/rv_tools/builtin/droidbot/tool.py`, `_build_droidbot_command()` line 258: change `self.config.get("device_serial", "emulator-5554")` to `self.config.get("device_serial") or "emulator-5554"`. Defense-in-depth — same pattern as FastBot. This change was already in the working tree.
- [x] 19.3 Verify DroidBot works locally via `rv-experiment run --tools droidbot:dfs_greedy --apks-dir ./apks_examples --timeout 60 --no-window --skip-monitors --skip-instrument --skip-static`. Result: PASSED. Task completed successfully (110s execution time), emulator managed by platform, DroidBot ran with `dfs_greedy` policy against `cryptoapp.apk`. Note: tested via rv-experiment because rv-platform CLI does not parse `tool:variant` DSL syntax.

**Acceptance criteria:**
- `configure()` defaults `device_serial` to `"emulator-5554"` (not `None`)
- `_build_droidbot_command()` uses `or` fallback as defense-in-depth
- DroidBot executes successfully for all variants (dfs_greedy, bfs_greedy, random, etc.)
- No regression in other tools (monkey, ape, fastbot)

## 20. Optimize Dev Docker Image Layers (D13)

The dev image (`phtcosta/rvandroid_dev:0.8.0`) re-downloads ~174 Python packages on every rebuild (~4.5 min), even when only source code changed. This is caused by two factors: `build.sh` uses `--no-cache` (invalidates all layers), and the Dockerfile copies source code before running `poetry install` (any code change invalidates the install layer). See design.md D13 for full analysis.

- [x] 20.1 Restructure `docker/rvandroid_dev/Dockerfile`: separate dependency installation from source code copying. Copy each module's `pyproject.toml` individually before `poetry install`, then copy full `modules/` directory after. Also create stub `__init__.py` files so Poetry can resolve editable installs before real source code is copied. 5 layers: root pyproject.toml → module pyproject.toml → stubs → poetry install → source code.
- [x] 20.2 Remove `--no-cache` from `docker/rvandroid_dev/build.sh`. The `--no-cache` flag forces Docker to re-execute every layer from scratch, which is appropriate for CI/release builds but counterproductive for development.
- [x] 20.3 Verify: build image twice — first build installs all packages (~4.5 min), second build after a code-only change should complete in ~10-20 seconds (layer cache hit for `poetry install`). Result: PASSED. Warm cache build: 3.1s. After `touch` on source file: 0.7s. Layer 21 (`poetry lock && poetry install`) stays CACHED on code-only changes. Docker uses content-based hashing, so `touch` (mtime-only) doesn't invalidate the `COPY modules/` layer either.
- [x] 20.4 Handle droidbot path dependency: COPY `droidbot/setup.py` and create stub `droidbot/droidbot/__init__.py` in Dockerfile so Poetry resolves the path dependency without error. DroidBot is already installed in the base tools image via pip — the local path is for development only.
- [x] 20.5 Exclude discontinued modules from Docker image (D14): (a) Removed `rv-llm`, `rvsmart-tool`, `rvdroid-tool` COPY lines from Layer 2 and stubs from Layer 3. (b) Added Layer 2b: `sed` to remove these modules from root `pyproject.toml` and `rv-experiment/pyproject.toml`. (c) Added `poetry lock` before `poetry install` in Layer 4 to regenerate lock file after sed. (d) Removed dead imports from `rv-experiment/config.py`: `LLMConfig` (only used in type annotation where branch returns `{}`), `PromptConfig` (never used). (e) `experiment_tools.py` rvdroid registration already uses `try/except ImportError` — no change needed.

**Acceptance criteria:**
- Code-only changes rebuild in under 30 seconds (layer cache hit)
- Dependency changes (`pyproject.toml`) still trigger full reinstall (correct behavior)
- Image produces identical runtime behavior as before optimization

## 21. Fix Humanoid Tool — DroidBot + `-humanoid` Flag (D15)

The Humanoid tool was completely rewritten incorrectly during modularization. The original tool ran DroidBot with the `-humanoid <url>` flag to connect to an external inference HTTP server. The rewritten tool tried to execute a nonexistent `run_humanoid.sh` script with fabricated CLI flags (--mode hybrid, --visual-threshold, --nlp-model, etc.). See design.md D15 for full root cause analysis.

- [x] 21.1 Rewrite `modules/rv-tools/src/rv_tools/builtin/humanoid/tool.py`: DroidBot command with `-humanoid <url>` flag. Follows DroidBot tool pattern. URL resolved from config > `RV_HUMANOID_URL` env > default `127.0.0.1:50405`. Single `default` variant (dfs_greedy policy).
- [x] 21.2 Delete `modules/rv-tools/src/rv_tools/builtin/humanoid/run_humanoid.sh` (was a 2-line Docker run helper, not the fictional bash tool).
- [x] 21.3 Update `modules/rv-tools/src/rv_tools/builtin/humanoid/__init__.py` (simplified docstring).
- [x] 21.4 Verify tool loads and configures correctly via `ToolRegistry`.

**Acceptance criteria:**
- `_build_humanoid_command()` produces: `poetry run droidbot -d <serial> -a <apk> -humanoid <url> -policy dfs_greedy -count 10000000000 -timeout <t> -ignore_ad -is_emulator`
- `RV_HUMANOID_URL` env var is read with fallback to `127.0.0.1:50405`
- `ToolRegistry` registers humanoid with 1 variant (`default`)
- `run_humanoid.sh` deleted, no references to CV/NLP/vision/learning config

## 22. Fix ARES Tool — Docker Sibling Container Pattern (D16)

The ARES tool was completely rewritten incorrectly during modularization — the same class of error as the Humanoid tool (D15). The original tool ran a local shell script that copied the APK to the ARES directory and executed the ARES Python process. The rewritten tool tried to `docker run` with fabricated CLI flags (`--apk`, `--output`, `--emulator`, `--timeout`), wrong image name (`ares:latest` vs `phtcosta/ares:latest`), and wrong volume mounts (`/app/target.apk` vs `/ares/apks/`). See design.md D16 for full root cause analysis.

- [x] 22.1 Rewrite `modules/rv-tools/src/rv_tools/builtin/ares/tool.py`: Three-step Docker pattern (`docker create` + `docker cp` + `docker start -a`) with cleanup in `finally` block. Env vars `EMUNAME` and `TIMEOUT_IN_MINUTES`. Network: `--network container:$(hostname)` inside Docker, `--network host` outside. Timeout conversion: `max(1, int(seconds / 60))`. Single `default` variant.
- [x] 22.2 Update `modules/rv-tools/src/rv_tools/builtin/ares/__init__.py` (simplified docstring).
- [x] 22.3 Verify tool loads and configures correctly via `ToolRegistry`.
- [x] 22.4 Rebuild dev Docker image (`docker/rvandroid_dev/build.sh`).

**Acceptance criteria:**
- `execute_tool_specific_logic()` uses `docker create` + `docker cp` + `docker start -a` pattern (not `docker run`)
- `docker cp` copies APK to `/ares/apks/app.apk` inside the ARES container
- Network uses `--network container:$(hostname)` when `/.dockerenv` exists
- Container is cleaned up (`docker rm -f`) in `finally` block
- `ToolRegistry` registers ares with 1 variant (`default`)

## 15.6 Full Pipeline Integration Test (Docker)

Validate the complete rv-experiment pipeline inside Docker WITHOUT skip flags: monitor generation → APK instrumentation → static analysis → tool execution. This test validates that the Docker image includes all build tools (JDK, Maven, Android SDK platforms) needed for the pre-processing phases. See design.md "Full Pipeline Integration Test" for extended 8-check verification protocol.

- [x] 15.6.1 Run full pipeline with `monkey:fast` tool, `jca` specification set, `cryptoapp.apk`, 60s timeout. RVSEC_HOME mounted as volume. Production image (`phtcosta/rvandroid:0.8.0`). Experiment ID: `cli_experiment_20260213_104143_f5b30ff0`.
- [x] 15.6.2 Verify 8-check protocol — **ALL 8 PASSED**:
  - Check 1 (exit code): 0 — background task confirmed exit code 0, "Experiment completed successfully"
  - Check 2 (tasks.json): `result.state = "COMPLETED"`, 100% completion, 0 failed, execution_time=128s
  - Check 3 (summary.csv): 1 row — `cryptoapp.apk,1,60,monkey:fast,50.0,10.17,20.0,0`
  - Check 4 (log evidence): `monkey -v --ignore-crashes --ignore-timeouts --ignore-security-exceptions -s 12345 -p br.unb.cic.cryptoapp 1000000000` — full 60s timeout execution
  - Check 5 (trace file): `cryptoapp.apk__1__60__monkey:fast.trace` (23KB, 425 lines) — monkey touch/trackball events
  - Check 6 (no crashes): Expected timeout chain only (`TimeoutExpired` → `RVCommandTimeoutError` → `RVToolTimeoutError`)
  - Check 7 (monitor generation): `Coverage.aj` (5KB) + `MultiSpec_1MonitorAspect.aj` (42KB) + `MultiSpec_1RuntimeMonitor.java` (498KB) — 23 JCA specs processed
  - Check 8 (instrumented APK + coverage): Instrumented `cryptoapp.apk` (3.4MB), 12 `RVSEC-COV` logcat entries, coverage: methods=10.17%, activities=50%, MOP methods=20%
- [x] 15.6.3 Validate coverage: `methods_jca_reachable_coverage = 20.0%` in summary.csv — **PASSED** (mandatory threshold: > 0%). 12 method calls detected by monitors: `onCreate`, `onCreateOptionsMenu`, `showScreenMessageDigest`, `showScreen`, `generateHash`, `validateAlgorithm`, `validateInput`, `clearErrors`, `hash(String)`, `hash(byte[])`, `showErrorDialog`.
- [x] 15.6.4 Check MOP errors: `total_errors = 0` in summary.csv, `errors.csv` has header only (no violations). Acceptable — monkey's random path in 60s did not trigger JCA misuse patterns in cryptoapp. The full error detection pipeline is validated by the RVSEC-COV logcat entries (monitors are active and logging).

**Docker fixes required during testing:**
- **AspectJ version mismatch**: `docker/base/Dockerfile` installed ajc 1.9.6 but `rvsec/pom.xml` declares 1.9.24. Fixed: updated base Dockerfile to download AspectJ 1.9.24 from GitHub releases.
- **GATOR ANDROID_SDK_HOME**: `docker/android/Dockerfile` lacked `ANDROID_SDK_HOME` env var required by GATOR static analysis. Fixed: added `ENV ANDROID_SDK_HOME=/opt/android`.
- Full image chain rebuilt after fixes: base → android → tools → production + dev.

**Acceptance criteria:**
- All 8 verification checks pass
- Monitor generation produces `.aj` files from JCA specifications
- APK instrumentation produces instrumented `cryptoapp.apk`
- `methods_jca_reachable_coverage > 0%` in `summary.csv` (mandatory — monitors logging `RVSEC-COV`)
- Logcat file contains `RVSEC-COV` entries
- MOP errors (`total_errors`, `errors.csv`) documented but not required to be > 0
- No skip flags used — full pipeline runs end-to-end

## 23. Fix QTesting Tool — Docker Sibling Container Pattern + struct.py Fix (D17)

The QTesting tool was completely rewritten incorrectly during modularization — the same class of error as the Humanoid tool (D15) and ARES tool (D16). The original tool ran QTesting natively, generating a dynamic `conf.txt` INI config file. The rewritten tool tried to `docker run` with fabricated CLI flags (`--apk`, `--algorithm qlearning`, `--max-episodes`, `--learning-rate`, etc.), wrong image name, and invented RL algorithm variants (`dqn`, `ddqn`, `sarsa`, `actor_critic`) that do not exist. Additionally, the QTesting Docker image had a `struct.py` file that shadowed Python's stdlib struct module, breaking numpy import. See design.md D17 for full root cause analysis.

- [x] 23.1 Rewrite `modules/rv-tools/src/rv_tools/builtin/qtesting/tool.py`: Three-step Docker pattern (`docker create` + `docker cp` x2 + `docker start -a`) with cleanup in `finally` block. Dynamic `conf.txt` INI generation with `[Path]` and `[Setting]` sections. Network: `--network container:$(hostname)` inside Docker, `--network host` outside. Single `default` variant.
- [x] 23.2 Update `modules/rv-tools/src/rv_tools/builtin/qtesting/__init__.py` (simplified docstring).
- [x] 23.3 Remove `modules/rv-tools/src/rv_tools/builtin/qtesting/src/struct.py` (moved to `backup/qtesting_struct.py.bak`). Truncated decompiled Python 2.7 artifact that shadowed stdlib struct module, breaking numpy import in the QTesting Docker image.
- [x] 23.4 Rebuild QTesting Docker image (`phtcosta/qtesting:latest`) without `struct.py`.
- [x] 23.5 Rebuild dev Docker image (`docker/rvandroid_dev/build.sh`) with D17 QTesting tool fix.
- [x] 23.6 Verify tool loads and configures correctly via `ToolRegistry` (1 variant: default).

**Acceptance criteria:**
- `execute_tool_specific_logic()` uses `docker create` + `docker cp` + `docker start -a` pattern (not `docker run`)
- `docker cp` copies APK to `/qtesting/apks/app.apk` and `conf.txt` to `/qtesting/apks/conf.txt`
- `conf.txt` generated dynamically with INI format (`[Path]`, `[Setting]` sections)
- Network uses `--network container:$(hostname)` when `/.dockerenv` exists
- Container is cleaned up (`docker rm -f`) in `finally` block
- `ToolRegistry` registers qtesting with 1 variant (`default`)
- QTesting Docker image runs without numpy ImportError (struct.py removed)

## 24. Fix DroidMate Tool — Correct DroidMate-2 CLI Flags (D18)

The DroidMate tool was completely rewritten incorrectly during modularization — the same class of error as Humanoid (D15), ARES (D16), and QTesting (D17). The original tool used correct DroidMate-2 `--Category-settingName=value` flags. The rewritten tool used fabricated flags (`-apk`, `-explorationTimeoutMs`, `-explorationStrategy`, `-deviceSerialNumber`, etc.) and invented 4 variants (`systematic`, `quick`, `research`) that do not correspond to real DroidMate-2 options. Unlike the Docker-based tools, DroidMate runs locally as `java -jar` — only the CLI flags were wrong. See design.md D18 for full root cause analysis.

- [x] 24.1 Rewrite `modules/rv-tools/src/rv_tools/builtin/droidmate/tool.py`: Fix `_build_droidmate_command()` with correct DroidMate-2 flags (`--Exploration-apkNames`, `--Exploration-apksDir`, `--Output-outputDir`, `--Selectors-timeLimit`, `--Selectors-actionLimit`, `--Core-logLevel`). Split `app.path` into `basename` + `dirname` for the two Exploration flags. Single `default` variant with `action_limit=100000000`.
- [x] 24.2 Update `modules/rv-tools/src/rv_tools/builtin/droidmate/__init__.py` (simplified docstring).
- [x] 24.3 Verify tool loads and configures correctly via `ToolRegistry` (1 variant: default).
- [x] 24.4 Rebuild dev Docker image (`docker/rvandroid_dev/build.sh`).

**Acceptance criteria:**
- `_build_droidmate_command()` produces: `java -jar droidmate-2-X.X.X-all.jar --Exploration-apkNames=<filename> --Exploration-apksDir=<dir> --Output-outputDir=<dir> --Selectors-timeLimit=<ms> --Selectors-actionLimit=100000000 --Core-logLevel=debug`
- JarResolver finds JAR at `modules/rv-tools/src/rv_tools/builtin/droidmate/droidmate-2-X.X.X-all.jar`
- `ToolRegistry` registers droidmate with 1 variant (`default`)
- No fabricated flags, no invented variants, no `register_droidmate_variants()` function
