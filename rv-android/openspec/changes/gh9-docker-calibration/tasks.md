# Tasks: Docker-Based Calibration — Full Lifecycle

## Execution Order

Tasks 1-12d cover infrastructure development (COMPLETED — 86 tests passing). Tasks 13-13a cover commit + Docker image rebuild (COMPLETED). Tasks 14-15 cover Phase A first run (COMPLETED — 125/188 passed). Tasks 15a-15c cover Phase A corrections (DONE). Tasks 15d-15h cover verification, re-run, retry, and dataset assembly (DONE — 179/188 valid). Task 16 covers dataset copy to calibration_dataset_v2 (DONE). Tasks 17-18 cover Phase B baseline (runs FIRST with current defaults on ALL valid APKs). Tasks 19-24 cover pre-calibration (C0/D0 on 20 APKs — validates approach before full campaign). Tasks 25-31 cover the full calibration campaign (C/D/E — only if pre-cal validates). Tasks 32-34 cover post-execution parameter application.

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

### Commit, Docker Rebuild, and Transfer (COMPLETED)

13. Task 13: Commit all code + rewritten artifacts (refs #9)
13a. Task 13a: Rebuild Docker image `0.8.0` (overwrite with current `modules` branch code)

### Phase A — First Run (COMPLETED — 125/188 passed)

14. Task 14: Phase A — Execute Docker preprocessing (6 containers)
15. Task 15: Phase A — Verify results

Phase A completed with 125/188 APKs passing SA. Investigation revealed 3 categories of failure affecting 62 APKs:

| Category | Count | Root Cause | Fixable? |
|----------|-------|-----------|----------|
| Missing Android platforms in Docker | ~20-25 | Docker image lacks platforms 4-18; GATOR wrapper uses hardcoded `tools/bin/sdkmanager` path that doesn't exist in image | YES — add platforms + symlink |
| `StackOverflowError` in `RvsecAnalysisClient.collectEventHandlers` | ~15-20 | Recursive GUI node traversal without cycle detection — infinite recursion on cyclic node graphs | YES — add visited set |
| Soot crash / Timeout | ~15-20 | Soot `InternalTypingException` or APK too complex for 600s timeout | NO — inherent Soot/APK limitations |

### Phase A Corrections (15a-15d DONE, 15e-15h IN PROGRESS)

15a. Task 15a: Fix `StackOverflowError` in `RvsecAnalysisClient.java` — DONE
15b. Task 15b: Fix Docker image — add Android platforms 10-18 + sdkmanager symlink — DONE
15c. Task 15c: Rebuild JARs + Docker image — DONE
15d. Task 15d: Verify fixes in Docker (10 test APKs) — DONE
15e. Task 15e: Re-run Phase A preprocessing (6 containers) — IN PROGRESS
15f. Task 15f: Verify Phase A results
15g. Task 15g: Retry failed APKs with extended timeout
15h. Task 15h: Assemble final dataset + commit

### Dataset Assembly (PENDING)

16. Task 16: Copy dataset to `data/calibration_dataset_v2/` + create `all_valid_apks.txt`

### Phase B — Baseline (PENDING)

17. Task 17: Phase B — Execute baseline (ALL valid APKs, 3 tools × 3 reps, current defaults)
18. Task 18: Phase B — Verify results + compute BASELINE_MAX_ERRORS

### Pre-Calibration (PENDING)

19. Task 19: Select 20 pre-calibration APKs
20. Task 20: Phase C0 — Execute pre-macro (30 trials, 11 MACRO params)
21. Task 21: Phase C0 — Verify convergence
22. Task 22: Phase D0 — Execute pre-micro (40 trials, 26 MICRO params, SGLang)
23. Task 23: Phase D0 — Verify + decision gate
24. Task 24: Update defaults from pre-cal results

### Full Calibration Campaign (PENDING — only if pre-cal validates)

25. Task 25: Create cal/holdout split
26. Task 26: Phase C — Execute macro calibration (80 trials, 11 MACRO params)
27. Task 27: Phase C — Verify results
28. Task 28: Phase D — Execute micro calibration (100 trials, 26 MICRO params, SGLang)
29. Task 29: Phase D — Verify results
30. Task 30: Phase E — Execute validation (37 params, SGLang)
31. Task 31: Phase E — Verify results + statistical comparison

### Post-Execution (PENDING)

32. Task 32: Apply 37 optimal parameters to code
33. Task 33: Update agent spec (FF SDD delta spec)
34. Task 34: Archive change and close issue (closes #9)

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

- [x] 12.6 **Create `scripts/preprocess_docker.py`** — Dedicated compose generator for Phase A (Docker preprocessing). Pure functions: `generate_preprocess_compose()` (entrypoint override with `--skip-execution`), `collect_preprocessed_artifacts()` (merge per-container `out/` into single dataset), `filter_by_sa_completeness()` (check for unified `.json` analysis file). See design.md Section 1 for compose structure.
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

## Commit and Transfer (COMPLETED)

### 13. Commit All Code + Rewritten Artifacts

- [x] 13.1-13.5: Infrastructure commit completed (refs #9).

### 13a. Rebuild Docker Image

- [x] 13a.1-13a.6: Docker image `0.8.0` rebuilt from `modules` branch. E2E smoke passed (rvagent:pure_algorithm). Obsolete gh26 images removed.

---

## Phase A — First Run (COMPLETED — 125/188)

### 14. Phase A — Execute Docker Preprocessing

- [x] 14.1 Fixed `preprocess_docker.py`: added `--output-dir /opt/rvsec/rv-android/out` to align with Docker volume mount. Removed unused `RV_EXPERIMENT_NAME` env var.
- [x] 14.2 Validated with 1-APK smoke test (1 container, `biz.gyrus.yaab_30.apk`): APK + JSON collected.
- [x] 14.3 Executed Phase A: 6 containers, 188 APKs, `--specification-set jca`.
- [x] 14.4 All 6 containers completed (4 exit 0, 2 exit 1 — non-zero due to SA failures, not script failures).

### 15. Phase A — Verify Results

- [x] 15.1 `passed_apks.txt` has 125 APKs (exceeds design expectation of ~105).
- [x] 15.2 `failed_apks.txt` has 62 APKs (all `missing: .json`).
- [x] 15.3 1 APK failed instrumentation: `com.danielme.muspyforandroid_3.apk` (dex2jar failure).
- [x] 15.4 `dataset/` assembled: 187 APKs + 125 JSONs = 312 files.
- [x] 15.5 Investigated failure categories (10 APKs tested locally):

| Category | Tested | Result | Root Cause |
|----------|--------|--------|-----------|
| Missing platforms | 5 APKs (targets 16-18) | All SUCCESS locally | Docker image lacks platforms 10-18 |
| StackOverflowError | 3 APKs (targets 14-30) | All FAILED locally too | `collectEventHandlers()` recursion without visited set |
| Soot crash | 1 APK (target 28) | FAILED locally | Soot `InternalTypingException: Unexpected type null` |
| Timeout | 1 APK (target 29) | FAILED locally (exit 206) | APK too complex for 300s timeout |

---

## Phase A Corrections (15a-15d DONE, 15e-15h IN PROGRESS)

### 15a. Fix RvsecAnalysisClient — StackOverflow + Class Filtering

Two bugs in `RvsecAnalysisClient.java`:

1. **StackOverflowError**: `collectEventHandlers()` and `collectWidgets()` recursively traverse GUI nodes without cycle detection. Cyclic node graphs → infinite recursion → no JSON output.
2. **Library classes in reachability**: `extractClasses()` uses `Scene.v().getApplicationClasses()` which returns ALL DEX classes (app + libraries like retrofit2, kotlinx, etc.). This inflates the coverage denominator — the reachability section defines the 100% universe for coverage calculation.

**Fix for (2)**: Pass the detected `code_package` (from Python-side `PackageDetector`) to GATOR via `-clientParam "codePackage=..."`. In Java, filter `extractClasses()` by this prefix. Fallback to manifest package when `codePackage` param is absent.

**Source files**:
- Java: `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java`
- Python: `modules/rv-static-analysis/src/rv_static_analysis/config.py`, `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

#### StackOverflow fix (DONE)

- [x] 15a.1 Fix `collectEventHandlers()`: add `Set<NNode> visited` parameter, skip already-visited nodes.
- [x] 15a.2 Fix `collectWidgets()`: same pattern — add `Set<NNode> visited` parameter.
- [x] 15a.3 Update callers in `complementWithCallbacks()` and `extractWindows()` to pass `new HashSet<>()`.

#### Class filtering fix (DONE)

- [x] 15a.4 Java: add `getCodePackage()` method to read `codePackage=` from `-clientParam`.
- [x] 15a.5 Java: modify `extractClasses(String filterPackage)` — filter by `className.startsWith(filterPackage)`, exclude `R`, `R$*`, `BuildConfig`.
- [x] 15a.6 Java: update `run()` — resolve `filterPackage` (prefer `codePackage` param, fallback to manifest package), pass to `extractClasses()`.
- [x] 15a.7 Python `config.py`: add `code_package` kwarg to `get_tool_command()`, append `-clientParam "codePackage=..."` when provided.
- [x] 15a.8 Python `static_analysis.py`: pass `self.app.code_package` to `get_tool_command()` via kwarg.

#### Unit tests (DONE)

- [x] 15a.9 Java: extract `isAppClass(String className, String filterPackage)` as package-private static method for testability.
- [x] 15a.10 Java: create `ExtractClassesFilterTest.java` — 25 tests covering app classes, library classes, R/BuildConfig exclusion, inner classes, edge cases.
- [x] 15a.11 Python `test_config.py`: 2 tests — `get_tool_command()` includes `codePackage` clientParam when kwarg provided, omits when absent.
- [x] 15a.12 Python `test_static_analysis.py`: 1 test — `_run_analysis()` passes `code_package=self.app.code_package` to `get_tool_command()`.
- [x] 15a.13 Build updated JAR: 44 Java tests passing (25 filter + 12 BFS + 7 JSON).
- [x] 15a.14 Run Java unit tests: `mvn test -pl rvsec-gator/client -DskipTests=false` — 44/44 passed.
- [x] 15a.15 Run Python unit tests: `uv run pytest modules/rv-static-analysis/tests/` — 24/24 passed.

#### Local verification (DONE)

- [x] 15a.16 Test locally with `com.gh4a_73.apk` — verified:
  - 965 app classes (was 2933 unfiltered), all `com.gh4a.*`, zero library classes
  - R/BuildConfig correctly excluded
  - 1968 classes filtered (libraries + generated)
  - MOP reachability works: 120 signatures loaded, 119 resolved, 59.8% reachesMop
  - WTG: 90 windows (47 activities, 3 dialogs, 40 menus), all app-internal
  - Compared with 13 APKs from old `.reach` data: filtered counts match exactly (e.g., `ca.farrelltonsolar.classic_314`: OLD=49, NEW filtered=49; `org.emunix.insteadlauncher_80601`: OLD=131, NEW filtered=131)

### 15b. Fix Docker Image — Add Platforms + sdkmanager Symlink (DONE)

The Docker image (`docker/android/Dockerfile`) installs platforms 19-35 but many APKs target earlier levels (10-18). The GATOR wrapper also uses a hardcoded path `$ANDROID_HOME/tools/bin/sdkmanager` which doesn't exist — the image has `cmdline-tools/tools/bin/sdkmanager`.

- [x] 15b.1 Update `docker/android/Dockerfile`: add `platforms;android-10` through `platforms;android-18` to `ANDROID_SDK_PACKAGES`.
- [x] 15b.2 Add `RUN mkdir -p $ANDROID_HOME/tools/bin && ln -s $ANDROID_HOME/cmdline-tools/tools/bin/sdkmanager $ANDROID_HOME/tools/bin/sdkmanager` for GATOR wrapper compatibility.
- [ ] 15b.3 Rebuild `phtcosta/rvsec_android:0.8.0` base image (moved to 15c — full chain rebuild).

### 15c. Rebuild JARs + Docker Images

**IMPORTANT**: The `rvandroid:0.8.0` image has an ENTRYPOINT (`/opt/docker-entrypoint.sh`) that intercepts all commands and starts the experiment pipeline. Verification commands MUST use `--entrypoint ""` to bypass the entrypoint and run commands directly.

- [x] 15c.1 Rebuild full image chain: `rvsec_android:0.8.0` → `rvandroid_tools:0.8.0` → `rvandroid:0.8.0`. (User rebuilt 2026-02-25.)
- [x] 15c.2 Verify new JAR in image: 59MB, dated 2026-02-25 12:55. Present at correct path.
- [x] 15c.3 Verify platforms: android-10 through android-35 — all 26 levels present.
- [x] 15c.4 Verify sdkmanager symlink: `tools/bin/sdkmanager -> cmdline-tools/tools/bin/sdkmanager`. Correct.

### 15d. Verify Fixes in Docker (10 Test APKs) — DONE

Re-ran the same 10 APKs from Phase A investigation inside Docker (5 containers, 2 APKs each, `--entrypoint ""`, timeout 300s). Tests both StackOverflow fix (JAR) and platform fix (image) simultaneously.

- [x] 15d.1 StackOverflow APKs (3):
  - `com.gh4a_73`: timeout at 300s (verified locally at 600s in 15a.16 — needs longer timeout, not a fix issue)
  - `com.koushikdutta.superuser_1030`: SUCCESS — 450KB JSON, 102 classes
  - `com.cyanogenmod.filemanager.ics_1015`: SUCCESS — 1.4MB JSON, 485 classes
- [x] 15d.2 Missing-platform APKs (5): all produced JSON
  - `com.blippex.app_5`: 47KB, 26 classes
  - `com.gracecode.android.presentation_20131114`: 98KB, 38 classes
  - `org.nick.wwwjdic_2370`: 685KB, 239 classes
  - `com.andrew.apollo_2`: 939KB, 261 classes
  - `com.Bisha.TI89EmuDonation_1133`: 154KB, 0 classes (app package not matched — investigate)
- [x] 15d.3 Previously unfixable APKs (2):
  - `com.alienpants.leafpicrevived_24`: SURPRISE SUCCESS — 742KB, 380 classes (Soot crash was likely StackOverflow misattributed)
  - `com.amphoras.tpthelper_25`: timeout as expected (no JSON)

**Result**: 8/10 produced JSON (expected 7/10). Fix effectiveness confirmed. Full E2E validation in task 15e.

### 15e. Re-run Phase A Preprocessing

- [x] 15e.0 Add reference data files to `modules/rv-agent-validation/data/`:
  - `apks_complete.csv`: master APK catalog (253 rows, from ase-journal repo)
  - `exp01_jca_apks.txt`: 188 JCA APK names (generated from CSV where `exp01_jca=True`)
  - Updated CLAUDE.md (data dir tree), design.md (data paths, execution commands)
- [x] 15e.1 Clean previous preprocessing results (Docker alpine for root-owned dirs + rm user-owned files).
- [x] 15e.2 Run `preprocess_docker.py` with 6 containers on all 188 APKs.
- [x] 15e.3 Monitor progress. Results: 187/188 instrumented (1 dex2jar failure), 165 JSONs produced. 4 containers completed normally. Containers 2 and 3 stopped manually after 3h (due to sequential SA timeouts consuming 10 min each).

### 15f. Verify Phase A Results — DONE

- [x] 15f.1 `passed_apks.txt` has 165 APKs (exceeds gate of 125, up from first-run's 125).
- [x] 15f.2 All 165 passing APKs have `.json` analysis file in assembled `dataset/` (187 APKs + 165 JSONs = 352 files). Orphan JSON for `com.danielme.muspyforandroid_3` removed (dex2jar failure, no instrumented APK).
- [x] 15f.3 Categorized 22 failed APKs (no JSON):
  - **SA timeout (exit 206)**: 10 APKs — GATOR timed out at 600s, may recover with extended timeout
  - **Never started SA**: 12 APKs — container 2 stopped before reaching them in the queue (all instrumented, just need SA run)

**Gate**: PASSED — 165 > 125.

### 15f-bug. Fix SA Timeout Not Enforced by Command — DONE

**Bug discovered during 15e**: `StaticAnalyzer._run_analysis()` created `Command(cmd_args[0], cmd_args[1:])` without passing `timeout=self.config.analysis_timeout` (static_analysis.py:256). The `Command.invoke()` method called `proc.communicate(timeout=None)` — waited indefinitely. The `--timeout 600` CLI argument only controlled the GATOR Python wrapper's internal `call()`, not the Python `Command` process-level timeout.

In practice, the GATOR wrapper timeout WAS working for most APKs (exit code 206 after 600s). The missing Command timeout was a safety-net gap — if the GATOR wrapper hung, Command would wait forever. This fix ensures both timeout layers are active.

- [x] 15f-bug.1 Fix `static_analysis.py:256`: pass `timeout=self.config.analysis_timeout` to `Command()` constructor.
- [x] 15f-bug.2 Add test `test_run_analysis_passes_timeout_to_command`: verifies `Command` receives `timeout=600` from config. 15/15 tests passing.
- [x] 15f-bug.3 Commit `156ec8f7` + rebuild Docker image `rvandroid:0.8.0`.

### 15f-bug2. Parametrize GATOR JVM Memory

**Bug**: GATOR wrapper (`lib/gator/gator`) has `-Xmx12G` hardcoded. `RVStaticAnalysisConfig.jvm_memory` (default `8g`) exists but is never passed to the GATOR command. Large APKs (84K vertices, 863K edges) may need more heap.

- [x] 15f-bug2.1 `lib/gator/gator`: add `--jvm-memory` argument (default `12G`), replace hardcoded `-Xmx12G`.
- [x] 15f-bug2.2 `config.py` (`get_tool_command`): pass `--jvm-memory {self.jvm_memory.upper()}` to GATOR.
- [x] 15f-bug2.3 `config.py`: change default `jvm_memory` from `8g` to `12g` (match GATOR's current default).
- [x] 15f-bug2.4 `rv_experiment/config.py`: read `RV_JVM_MEMORY` env var, pass to `RVStaticAnalysisConfig`.
- [x] 15f-bug2.5 `preprocess_docker.py`: add `--jvm-memory` param, inject as `RV_JVM_MEMORY` env var.
- [x] 15f-bug2.6 Tests: update default `8g→12g` in 2 test files, add `test_tool_command_includes_jvm_memory`. 81/81 passing.
- [x] 15f-bug2.7 Commit `912269e4` + push + rebuild Docker image `rvandroid:0.8.0`. Dangling image removed.

### 15g. Retry Failed APKs with Extended Timeout

**Prerequisite**: 15f-bug2.7 (Docker image rebuild with JVM memory + SA timeout parametrization).

Give 22 failed APKs a second chance with a longer SA timeout (30 min) and more JVM heap (20g). 10 are confirmed timeouts, 12 never ran SA (container stopped before reaching them).

**SA timeout mechanism**: `RV_SA_TIMEOUT` env var → `ExperimentConfig.get_static_analysis_config()` reads it → passes `analysis_timeout` to `RVStaticAnalysisConfig` → `StaticAnalyzer` creates `Command(timeout=...)`.

- [x] 15g.1 Collected 22 failed APKs from 15f. Excluded `com.danielme.muspyforandroid_3` (dex2jar/Java 25 incompatibility — no instrumented APK).
- [x] 15g.2 Created `retry_filter.txt` with 22 APKs in `results/preprocessing_v2/`.
- [x] 15g.3 Added `--sa-timeout` parameter to `preprocess_docker.py`: injects `RV_SA_TIMEOUT` env var in compose services.
- [x] 15g.4 Updated `ExperimentConfig.get_static_analysis_config()`: reads `RV_SA_TIMEOUT` env var, passes as `analysis_timeout` to `RVStaticAnalysisConfig`.
- [x] 15g.5 Run retry: 5 containers, 14 CPUs, 28g RAM each, `--sa-timeout 1800`, `--jvm-memory 20g`. Distribution: 5+5+4+4+4 APKs. Result: 14/22 recovered, 8 definitively failed (WTG timeout/complexity).
- [x] 15g.6 Merged 14 recovered JSONs into `dataset/`. APKs already present from first run (only JSONs were missing).
- [x] 15g.7 Updated `passed_apks.txt` (179) and `failed_apks.txt` (8). Final: 187 APKs + 179 JSONs = 366 files in dataset.

### 15h. Assemble Final Dataset + Commit — DONE

- [x] 15h.1 Merged 15e + 15g results. Removed 8 orphan APKs (no JSON). Final: 179 APKs + 179 JSONs = 358 files.
- [x] 15h.2 Integrity check passed: every APK has matching non-empty `.json`.
- [x] 15h.3 Final counts: 179 valid (from 188 JCA), 8 failed (WTG timeout/complexity), 1 dex2jar failure.
- [x] 15h.4 Commit with `refs #9`.

**Gate**: PASSED — 179 > 140. All recoverable APKs included.

---

## Dataset Assembly (PENDING)

### 16. Assemble Dataset — DONE

- [x] 16.1 Copied 358 files (179 APKs + 179 JSONs) to `modules/rv-agent-validation/data/calibration_dataset_v2/`.
- [x] 16.2 Created `all_valid_apks.txt` (179 APK names).
- [x] 16.3 Integrity check passed: every APK has matching non-empty `.json`.
- [x] 16.4 Commit dataset files with `refs #9`.

**Gate**: PASSED — 179 valid APKs (exceeds expected ~145-150). Every APK has its `.json`.

---

## Phase B — Baseline (PENDING)

Baseline runs FIRST, before any calibration, to establish reference performance with current defaults.

### 17. Phase B — Execute Baseline

*Runbook reference: design.md Section 2*

- [ ] 17.1 Run `baseline_docker.py` with ALL valid APKs, 3 tools (ape, fastbot, rvagent:pure_algorithm), 3 reps, `--timeout TIMEOUT_SECS`.
- [ ] 17.2 Monitor progress: check batch directories for `tasks.json` growth.
- [ ] 17.3 If interrupted: re-run same command (resume is automatic via `RV_EXPERIMENT_NAME`).

### 18. Phase B — Verify Results

*Runbook reference: design.md Section 2 "Verification"*

- [ ] 18.1 All 6 batch summaries exist.
- [ ] 18.2 Aggregated `summary.csv` has 3 × N × 3 data rows (N = valid APKs).
- [ ] 18.3 All 3 tools present in summary.
- [ ] 18.4 Compute and record `BASELINE_MAX_ERRORS` value.
- [ ] 18.5 Symlink `aggregated_summary.csv` intact.

**Gate**: All 5 checks pass. BASELINE_MAX_ERRORS is a finite positive number.

---

## Pre-Calibration (PENDING)

Validates that Optuna can find params better than defaults using a 20-APK subset. Uses the real `BASELINE_MAX_ERRORS` from Phase B. B0 is not needed — the full baseline already exists.

### 19. Select 20 Pre-Calibration APKs

- [ ] 19.1 Select 20 APKs from valid dataset (stratified by category from `apks_complete.csv`).
- [ ] 19.2 Save as `modules/rv-agent-validation/data/precal_set.txt`.
- [ ] 19.3 Verify: all 20 APKs exist in `calibration_dataset_v2/` with SA files.

### 20. Phase C0 — Execute Pre-Macro

*Runbook reference: design.md Section 1b*

- [ ] 20.1 Run `calibration_orchestrator.py --phase macro --n-trials 30 --filter-file precal_set.txt --baseline-dir ./results/baseline_v2 --timeout TIMEOUT_SECS`.
- [ ] 20.2 Monitor progress (30 trials, ~5.5-8.3h expected).

### 21. Phase C0 — Verify Convergence

- [ ] 21.1 30 trials completed.
- [ ] 21.2 Convergence visible: last 10 trials avg > first 10 avg.
- [ ] 21.3 `optimal_params.json` saved with 11 MACRO params.

### 22. Phase D0 — Execute Pre-Micro

**Prerequisite**: SGLang server running at `localhost:30000`.

- [ ] 22.1 Start SGLang server.
- [ ] 22.2 Run `calibration_orchestrator.py --phase micro --n-trials 40 --filter-file precal_set.txt --best-macro precal_macro/optimal_params.json --baseline-dir ./results/baseline_v2 --sglang-url ... --timeout TIMEOUT_SECS`.
- [ ] 22.3 Monitor progress (40 trials, ~7.4-11.1h expected).

### 23. Phase D0 — Verify + Decision Gate

- [ ] 23.1 40 trials completed.
- [ ] 23.2 `optimal_params.json` contains 37 parameters (11 macro + 26 micro).
- [ ] 23.3 Compare pre-cal best score vs baseline defaults on the same 20 APKs.
- [ ] 23.4 **Decision**: if pre-cal improved → update defaults, proceed to full calibration. If not → investigate before committing.

**Gate**: Pre-cal shows meaningful improvement over baseline defaults.

### 24. Update Defaults from Pre-Cal Results

- [ ] 24.1 Update `parameter_space.py` defaults from C0 + D0 `optimal_params.json`.
- [ ] 24.2 Optionally narrow ranges to +/-30% around best values (clamped to original bounds).
- [ ] 24.3 Run tests: 86/86 must pass.
- [ ] 24.4 Commit with `refs #9`.

---

## Full Calibration Campaign (PENDING)

Only proceed after pre-cal validates the approach. Cal/holdout split is decided here based on dataset size.

### 25. Create Cal/Holdout Split

- [ ] 25.1 Run `select_dataset.py` to split valid APKs into calibration + holdout sets.
- [ ] 25.2 Verify `calibration_set_v2.txt`, `holdout_set_v2.txt`.
- [ ] 25.3 Commit split files with `refs #9`.

### 26. Phase C — Execute Macro Calibration (11 MACRO params)

*Runbook reference: design.md Section 3*

- [ ] 26.1 Run `calibration_orchestrator.py --phase macro --n-trials 80 --filter-file calibration_set_v2.txt --baseline-dir ./results/baseline_v2 --timeout TIMEOUT_SECS`.
- [ ] 26.2 Monitor progress: check `trial_history.json` growth, `orchestrator.log` for errors.
- [ ] 26.3 If interrupted: re-run with `--resume`.

### 27. Phase C — Verify Results

- [ ] 27.1 All 80 trials completed (check `trial_history.json`).
- [ ] 27.2 Best score > 0.0.
- [ ] 27.3 Convergence visible: last 20 trials score higher than first 20 on average.
- [ ] 27.4 `optimal_params.json` and `param_string.txt` exist and are valid.

**Gate**: All 4 checks pass before proceeding to Phase D.

### 28. Phase D — Execute Micro Calibration (26 MICRO params)

*Runbook reference: design.md Section 4*

**Prerequisite**: SGLang server running at `localhost:30000`.

- [ ] 28.1 Start SGLang server: `cd rvsec-vision-llm && docker compose up -d`.
- [ ] 28.2 Verify SGLang server: `curl -s http://localhost:30000/v1/models`.
- [ ] 28.3 Run `calibration_orchestrator.py --phase micro --n-trials 100 --filter-file calibration_set_v2.txt --best-macro calibration_macro_v2/optimal_params.json --baseline-dir ./results/baseline_v2 --sglang-url ... --timeout TIMEOUT_SECS`.
- [ ] 28.4 Monitor progress: check `trial_history.json` growth, SGLang server health.
- [ ] 28.5 If interrupted: re-run with `--resume`.

### 29. Phase D — Verify Results

- [ ] 29.1 All 100 trials completed.
- [ ] 29.2 Best score > 0.0.
- [ ] 29.3 `optimal_params.json` contains all 37 parameters (11 macro + 26 micro).
- [ ] 29.4 Compare micro best score vs macro best score (improvement expected).

**Gate**: All 4 checks pass before proceeding to Phase E.

### 30. Phase E — Execute Validation

*Runbook reference: design.md Section 5*

- [ ] 30.1 Verify SGLang server: `curl -s http://localhost:30000/v1/models`.
- [ ] 30.2 Run `baseline_docker.py` with holdout APKs, calibrated params, `--sglang-url`.
- [ ] 30.3 Monitor progress.

### 31. Phase E — Verify Results

- [ ] 31.1 `summary.csv` has expected data rows, 3 tools present.
- [ ] 31.2 Run statistical comparison (Wilcoxon) between calibrated and baseline RVAgent.
- [ ] 31.3 Document results: coverage improvement, error reduction, p-values.
- [ ] 31.4 Stop SGLang server: `cd rvsec-vision-llm && docker compose down`.

**Gate**: Calibrated RVAgent shows improvement over baseline on at least one metric.

---

## Post-Execution Tasks

### 32. Apply 37 Optimal Parameters to Code

*Runbook reference: design.md Section 6*

- [ ] 32.1 Update default values in `parameter_space.py` — 11 MACRO + 26 MICRO from `optimal_params.json`.
- [ ] 32.2 Update any unit tests that assert default parameter values.
- [ ] 32.3 Run `uv run pytest modules/rv-agent-validation/tests/calibration/ -v` — all must pass.

### 33. Update Agent Spec

- [ ] 33.1 Create FF SDD delta spec for `openspec/specs/agent/spec.md` with calibrated default values.
- [ ] 33.2 Sync delta spec to main spec.

### 34. Archive and Close

- [ ] 34.1 Run `openspec archive "gh9-docker-calibration" --skip-specs` (archives to `openspec/changes/archive/YYYY-MM-DD-gh9-docker-calibration/`).
- [ ] 34.2 Commit with `closes #9`.
- [ ] 34.3 Verify issue closed on GitHub.
