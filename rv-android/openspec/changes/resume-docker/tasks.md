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

## 15. Docker Smoke Tests

Verify that the built Docker images work correctly. These are manual tests run after all images are built (task 14).

- [ ] 15.1 **Entry Point**: Verify entrypoint + CLI works: `docker run --rm phtcosta/rvandroid:0.8.0 bash -c "poetry run rv-experiment --help"`
- [ ] 15.2 **Tool Registry**: Verify all tools are registered: `docker run --rm phtcosta/rvandroid:0.8.0 bash -c "poetry run rv-experiment list-tools"`
- [ ] 15.3 **Basic Execution**: Run monkey with short timeout: `docker run --rm --device /dev/kvm -v $(pwd)/apks_examples:/opt/rvsec/rv-android/apks phtcosta/rvandroid:0.8.0 run` (defaults: monkey, 300s, 1 rep)
- [ ] 15.4 **Docker CLI in Container**: Verify docker.sock works: `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock phtcosta/rvandroid:0.8.0 bash -c "docker ps"`
- [ ] 15.5 **Resume in Docker**: Run with 2 reps and RV_EXPERIMENT_NAME, kill after rep 1, restart, verify resume detects completed task and skips it.

**Acceptance criteria:**
- All 5 smoke tests pass
- Entry point correctly translates env vars to CLI args
- Tool registry shows all registered tools (monkey, ape, droidbot, fastbot, humanoid, ares, qtesting, droidmate, rvagent)
- Resume works across container restarts (Form 2: Crash Recovery)

## 16. Update Change Documents

Update design.md and tasks.md to reflect the expanded scope (ARES/QTesting Docker sibling containers). Update delta specs to document the Docker network behavior for ARES/QTesting tool execution.

- [x] 16.1 In `design.md`: move "ARES and QTesting Docker sibling containers" from Non-Goals to Goals.
- [x] 16.2 In `design.md`: add D10 decision — "Docker Network for Sibling Containers" — documenting the `--network container:$(hostname)` approach with `/.dockerenv` detection, including the parallel execution architecture (7 containers, each with its own sibling).
- [x] 16.3 In `design.md`: add architecture diagram for the sibling container pattern.
- [x] 16.4 In `tasks.md`: add tasks 11-16 with subtasks and acceptance criteria.
- [x] 16.5 In `openspec/changes/resume-docker/specs/tools/spec.md`: create delta spec for the tools domain documenting Docker network behavior for ARES and QTesting tool execution (new invariant INV-TOOL-15 for Docker-aware command building).
- [x] 16.6 In `openspec/changes/resume-docker/specs/experiment/spec.md`: add Docker Execution Mode requirement (FR16-ext, NFR08) documenting docker-entrypoint.sh, env var translation, docker-compose files, parallel execution, docker.sock mount, and startup delay.
