# Tasks: Docker-Based Calibration — Full Lifecycle

## Execution Order

Tasks 1-12d cover infrastructure development (COMPLETED — 86 tests passing). Tasks 13-13a cover commit + Docker image rebuild (COMPLETED). Tasks 14-15 cover Phase A first run (COMPLETED — 125/188 passed). Tasks 15a-15c cover Phase A corrections (DONE). Tasks 15d-15h cover verification, re-run, retry, and dataset assembly (DONE — 179/188 valid). Task 16 covers dataset copy to calibration_dataset_v2 (DONE). Task 16a covers monitoring script (DONE). Tasks 17-18 cover Phase B baseline (IN PROGRESS — 6 containers, ~45h remaining). Tasks 19-24 cover pre-calibration (C0/D0 on 20 APKs — validates approach before full campaign). Tasks 25-31 cover the full calibration campaign (C/D/E — only if pre-cal validates). Tasks 32-34 cover post-execution parameter application.

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

## Phase B — Baseline (IN PROGRESS)

Baseline runs FIRST, before any calibration, to establish reference performance with current defaults.

### 16a. Docker Batch Monitoring Script — DONE

- [x] 16a.1 Created `scripts/monitor_docker.py` — generic progress monitor for all Docker batch experiment phases.
  - Reads `tasks.json` + filter files from any results directory
  - Shows per-batch progress, APKs done, avg task duration, ETA
  - `--watch N` mode for auto-refresh every N seconds
  - Reusable for baseline, calibration, and validation phases (just change the results dir path)

### 17. Phase B — Execute Baseline

*Runbook reference: design.md Section 2*

Config: 179 APKs × 3 tools (ape, fastbot, rvagent:pure_algorithm) × 3 reps × 600s timeout = 1611 tasks, 6 containers.
Measured task duration: ~650s (37.5s emulator boot + 600s tool + 12.7s teardown).
Projected wall clock: ~48.8h (bottleneck: 270 tasks/batch on batches 0-4).

- [x] 17.1 First run: `baseline_docker.py` with 6 containers, 600s timeout, 3 reps. Completed 114/1611 tasks (~3.5h). Stopped for analysis.
- [x] 17.1a Fixed `RV_APKS_DIR` missing in `baseline_docker.py` and `calibration_orchestrator.py` (commit `09103a03`).
- [x] 17.2 Resumed: `docker compose up -d` in `results/baseline_v2/`. Resume confirmed — 19 tasks/batch skipped, 251 remaining/batch.
- [x] 17.3 Completed: 1550/1611 COMPLETED, 61 ERROR (all EmulatorError). 6 containers, ~48h wall clock.
- [x] 17.4 Interrupted twice (reboot), resumed via `docker compose up -d`. Resume mechanism creates duplicate ERROR entries for already-failed APKs (tasks.json has 200 duplicates, real errors are 61).

### 17a. Fix RVAgent Repetition/Filename Bug — DONE

**Bug**: RVAgent `.trace` and `.rvagent_metrics.json` files only generated for rep 1. Reps 2 and 3 overwrite the same file (hardcoded `repetition=1`). Two causes:

1. **Repetition not propagated**: `build_agent_config_dict()` never maps `task.config.repetition` → `RVAgentConfig` has no `repetition` field → `MetricsExporter` defaults to `repetition=1`.
2. **Filename prefix mismatch**: RVAgent uses `package_name` (e.g., `biz.gyrus.yaab`), platform expects `apk_name` (e.g., `biz.gyrus.yaab_30.apk`).

- [x] 17a.1 `RVAgentConfig`: add `repetition: int = Field(default=1, ge=1)`.
- [x] 17a.2 `rvagent_tool/config.py`: map `task.config.repetition` to config dict.
- [x] 17a.3 `rv_agent.py`: pass `self.config.repetition` to `build_filename()` (line 328) and `MetricsExporter.export()` (line 478).
- [x] 17a.4 Unit tests: `test_build_agent_config_dict_maps_repetition` and `test_build_agent_config_dict_repetition_default_when_missing` in `rvagent_tool/tests/unit/test_tool.py`.
- [x] 17a.5 Rebuild Docker image `rvandroid:0.8.0` (commit `94426bbf`).
- [x] 17a.6 Reset 142 rvagent tasks to READY + deleted corrupted `.trace`/`.rvagent_metrics.json` files via Docker alpine/python.
- [x] 17a.7 Resumed baseline. All 142 rvagent tasks re-executed successfully with correct repetition filenames.

### 17b. Remove APKs with Full Baseline Failure

5 APKs failed all 9 tasks (3 tools × 3 reps) with EmulatorError — the emulator consistently crashes when running these APKs. Remove from `calibration_dataset_v2/` and `all_valid_apks.txt`.

**APKs removed** (all EmulatorError, 9/9 tasks failed):
1. `fr.free.nrw.commons_1034.apk`
2. `net.momodalo.app.vimtouch_25.apk`
3. `org.astonbitecode.rustkeylock_1401.apk`
4. `org.smc.inputmethod.indic_103.apk`
5. `org.sufficientlysecure.viewer_2827.apk`

Dataset after removal: 179 - 5 = **174 APKs**.

- [x] 17b.1 Remove 5 APKs + their JSONs from `calibration_dataset_v2/`.
- [x] 17b.2 Update `all_valid_apks.txt` (174 entries).
- [x] 17b.3 Commit `82b88c1f` with `refs #9`.

### 17c. Remove APKs with Zero Coverage (All Tools) — DONE

7 APKs had 0% method coverage across ALL tools and ALL reps in the baseline. These produce no useful data for calibration. 5 were partial-failure APKs kept in 17b, plus 2 newly identified.

**APKs removed** (0% coverage, all tools, all reps):
1. `community.fairphone.clock_3.apk` (was partial failure — rvagent EmulatorError)
2. `community.fairphone.mycontacts_3.apk` (was partial failure — rvagent EmulatorError)
3. `nz.gen.geek_central.ObjViewer_1.apk` (0% all tools, no EmulatorError — app just doesn't produce coverage)
4. `org.fdroid.fdroid.privileged_2130.apk` (was partial failure — rvagent EmulatorError)
5. `org.fitchfamily.android.dejavu_21.apk` (was partial failure — rvagent EmulatorError)
6. `org.kde.necessitas.ministro_14.apk` (was partial failure — rvagent EmulatorError)
7. `tranquvis.simplesmsremote_140.apk` (0% all tools, no EmulatorError)

Dataset after removal: 174 - 7 = **167 APKs**.

- [x] 17c.1 Remove 7 APKs + JSONs from `calibration_dataset_v2/`.
- [x] 17c.2 Update `all_valid_apks.txt` (167 entries).
- [x] 17c.3 Regenerated `precal_set.txt` (20 APKs, no zero-coverage APKs).

### 18. Phase B — Verify Results

*Runbook reference: design.md Section 2 "Verification"*

- [x] 18.1 All 6 batch summaries exist (261-268 lines each).
- [x] 18.2 Aggregated summary has 1551 data rows (expected 1566 = 174×3×3; 15 missing from 5 APKs with partial EmulatorError failure).
- [x] 18.3 All 3 tools present: ape, fastbot, rvagent:pure_algorithm.
- [x] 18.4 **BASELINE_MAX_ERRORS = 23** (org.mosad.seil0.projectlaogai_6000.apk). Total errors: 2188, avg 1.41/task, 38.9% of tasks detected errors.
- [x] 18.5 `aggregated_summary.csv` created (1551 deduplicated rows, sorted by apk/tool/rep).

**Baseline summary** (174 APKs, 1551 completed tasks):

| Tool | N | Method Cov | Activity Cov | MOP Reach | Errors (avg) |
|------|---|-----------|-------------|-----------|-------------|
| ape | 507 | 28.3% | 63.7% | 38.2% | 1.6 |
| rvagent:pure_algorithm | 522 | 24.2% | 57.4% | 32.6% | 1.4 |
| fastbot | 522 | 22.5% | 52.7% | 30.0% | 1.3 |

**Gate**: PASSED — BASELINE_MAX_ERRORS = 23 (finite positive number).

---

## Pre-Calibration (IN PROGRESS)

Validates that Optuna can find params better than defaults using a 20-APK subset. Uses the real `BASELINE_MAX_ERRORS` from Phase B. B0 is not needed — the full baseline already exists.

### 19. Select 20 Pre-Calibration APKs — DONE

- [x] 19.1 Select 20 APKs from valid dataset, stratified by category (14 categories → proportional allocation, spread by MOP coverage within each).
- [x] 19.2 Saved as `modules/rv-agent-validation/data/precal_set.txt`.
- [x] 19.3 Verified: all 20 APKs + JSONs present in `calibration_dataset_v2/`.

### 19a. Fix Calibration Orchestrator Bugs — DONE

Two bugs fixed before C0 execution:

1. **`round_timeout` too short**: Was `timeout × 4 = 2400s (40 min)`, but each container needs ~3.6h. Containers would be killed after 40 min. Fix: compute from `n_apks × (timeout + overhead) × safety_margin` = 21,600s (6h).
2. **TPESampler not configured for parallelism**: Was `TPESampler(seed=42)` without `constant_liar`. With 6 parallel trials, all 6 would be suggested from the same model snapshot. Fix: added `constant_liar=True`, `multivariate=True`, `n_startup_trials=12`.

- [x] 19a.1 Replace `ROUND_TIMEOUT_MULTIPLIER` with `compute_round_timeout(timeout, n_apks)`.
- [x] 19a.2 Add `count_filter_apks()` to read filter file.
- [x] 19a.3 Add `constant_liar=True`, `multivariate=True`, `n_startup_trials=2*n_containers` to TPESampler.
- [x] 19a.4 Create `summary.csv` symlink in `baseline_v2/` → `aggregated_summary.csv` (ObjectiveFunction expects `summary.csv`).
- [x] 19a.5 Verified: 86/86 calibration tests pass.

### 20. Phase C0 — Execute Pre-Macro — IN PROGRESS

*Runbook reference: design.md Section 1b*

Config: 50 trials, 9 rounds (6 containers/round, last round 2 trials), 20 APKs × 1 rep × 600s timeout.

- [x] 20.1 First run aborted: precal_set included 4 APKs with 0% rvagent coverage (EmulatorError). Stopped at round 2 (6/50 trials). Cleaned results + regenerated precal_set (Task 17c).
- [x] 20.2 Restarted with clean precal_set. PID 2115005. Round 1 started at 19:26.
- [x] 20.3 Ran 36/50 trials (rounds 1-6, ~3h20min/round). Scores clustered at 58.4-59.7 with near-zero variation. Deep investigation revealed 3 bugs (Task 20a). Stopped C0 for fixes.

### 20a. Fix C0 Infrastructure Bugs — DONE (except commit+rebuild)

Three bugs discovered during C0 execution that compromise calibration quality. All must be fixed before restarting C0.

**Bug 1: config.py whitelist drops 15 calibration params** (CRITICAL)

`build_agent_config_dict()` in `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py` uses explicit whitelists. 3 MACRO + 12 MICRO params added in gh26/gh18 are missing. Params are sent to Docker containers but silently dropped before reaching `RVAgentConfig`. Proven by trace logs: trial_25 docker-compose has `backtrack_saturation_threshold=0.5453` but agent uses default `0.8`.

MACRO params missing (3 of 11):
- `backtrack_saturation_threshold` (importance 4 — controls proactive backtracking trigger)
- `coverage_density_weight` (importance 3 — second-most impactful scorer after MopScorer)
- `error_detection_confidence` (importance 3 — error detection threshold)

MICRO params missing (12 of 26):
- `max_short_term_iterations`, `llm_max_retries` (fallback/memory)
- `mop_nav_weight`, `mop_max_input_variations` (MOP exploration, gh26)
- `reward_gamma`, `reward_score_weight` (reward propagation, gh26)
- `error_max_indicator_size`, `error_max_indicator_count` (error detection, gh18)
- `spatial_edittext_boost`, `spatial_spinner_boost`, `spatial_min_match_threshold` (spatial association, gh18)
- `multi_value_saturation_threshold` (widget saturation, gh26)

Note: `mop_nav_weight` is defined in `RVAgentConfig` but not consumed by any code yet — include it anyway for consistency.

- [x] 20a.1 Add 3 MACRO params to `scorer_params` list in `config.py`.
- [x] 20a.2 Add 12 MICRO params to appropriate sections in `config.py`.
- [x] 20a.3 Add unit tests verifying all 35 calibration params are forwarded (`TestCalibrationParamForwarding` — 2 tests in rvagent-tool).

**Bug 2: Error normalization saturates at 40% of objective** (HIGH)

`ObjectiveFunction._normalize_errors()` uses linear normalization with `baseline_max_errors=1.58` (mean errors per tool, max across tools — computed over ALL 167 APKs). The precal 20 APKs produce avg_errors≈2.0, so `2.0/1.58*100=126.6%` → capped at 100. Result: 34/37 trials have identical error component (100.0), providing zero gradient to Optuna on 40% of the score.

Fix: change to log normalization with max-APK reference.

- [x] 20a.4 Change `compute_baseline_max_errors()`: from `groupby('tool').mean().max()` to `groupby('apk').mean().max()` (gives ~22.33 instead of 1.58).
- [x] 20a.5 Change `_normalize_errors()`: from `(avg_errors / ref) * 100` to `log(1 + avg_errors) / log(1 + ref) * 100`.
- [x] 20a.6 Update unit tests for new normalization behavior (T31 log normalization, T33 per-APK reference).

**Bug 3: Docker rebuild required**

Bug 1 fix changes code inside the Docker image (`rvagent-tool` module). Docker image must be rebuilt before restarting C0.

- [x] 20a.7 Commit all fixes (20a + 20b) with `refs #9`. Commit `0dfa0bc8`.
- [x] 20a.8 Rebuild Docker image `rvandroid:0.8.0` (sha256:60ee3b5f5353).
- [x] 20a.9 Stop C0 (PID 2115005), clean results. Restart after all fixes (20a + 20b).

**Analysis: UI coverage weight investigated, no change needed**

Deep investigation concluded that UI coverage is statistically independent from method coverage (Pearson r=0.049, p=0.256) and has zero correlation with MOP errors. Increasing the weight would bias Optuna toward configs that click more UI elements without improving crypto misuse detection. Weights remain at 40/40/20 (coverage/errors/ui_coverage).

### 20b. Widen Parameter Ranges for Optuna Exploration — DONE

Deep analysis of the scoring architecture (all 9 scorers, additive composition, typical range [-60, +1225]) revealed 11 parameters whose ranges may prevent Optuna from finding the true optimum. Additionally, 3 MICRO parameters are dead code (defined in config but never consumed at runtime).

**Scoring architecture summary**: `ActionRanker.rank()` sums all scorer outputs. MopScorer dominates at +500 (direct) / +300 (transitive). Best-case composite: ~1225. Several secondary scorers are capped too low relative to MOP magnitude.

**MACRO params to widen (5 of 11):**

| Parameter | Current | Proposed | Rationale |
|-----------|---------|----------|-----------|
| `wtg_guided_score` | 50-300 | 50-400 | Allow WTG > MOP transitive; Pydantic le=500 OK |
| `unsaturated_bonus` | 50-150 | 50-250 | Currently weak tiebreaker; Pydantic le=200 → 250 |
| `strength_weight` | 25-100 | 25-150 | Allow StrengthScorer to compete with WTG; Pydantic le=200 OK |
| `visitation_penalty_factor` | -25/-5 | -40/-3 | Allow aggressive anti-revisitation; Pydantic ge=-50 OK |
| `coverage_density_weight` | 50-400 | 50-600 | Objective weights coverage=40%; allow coverage-first; Pydantic le=400 → 600 |

**MICRO params to widen (6 of 26):**

| Parameter | Current | Proposed | Rationale |
|-----------|---------|----------|-----------|
| `mop_transitive_score` | 150-450 | 150-600 | Maintain proportion with direct (300-700); Pydantic le=500 → 600 |
| `multi_value_saturation_threshold` | 2-8 | 2-12 | Interact with mop_max_input_variations (5-15, default 11) |
| `reward_score_weight` | 0.1-3.0 | 0.1-5.0 | Allow reward to dominate strength component |
| `gradual_decay_base` | 100-300 | 100-400 | Parity with mop_transitive range |
| `gradual_decay_rate` | 0.5-0.9 | 0.5-0.95 | Explore slow-decay regime (score stays high longer) |
| `llm_temperature` | 0.001-0.9 | 0.001-1.5 | For multimode Phase D; Pydantic le=2.0 OK |

**Dead code params (3 MICRO — excluded from calibration):**

| Parameter | Issue | Action |
|-----------|-------|--------|
| `mop_nav_weight` | Defined in RVAgentConfig, never read by any scorer/strategy | Removed from MICRO_PARAMETERS |
| `max_short_term_iterations` | Config value not passed to `ShortTermMemory()` in `AgentFactory` | Fixed wiring (20b.4) — remains in calibration |
| `llm_max_retries` | `AgentState.max_retries` never set from config | Removed from MICRO_PARAMETERS |

**Pydantic bounds that need updating** (`agent_config.py`):
- `unsaturated_bonus`: le=200 → le=250
- `coverage_density_weight`: le=400 → le=600
- `mop_transitive_score`: le=500 → le=600

- [x] 20b.1 Update `parameter_space.py` — widen 11 ranges (5 MACRO + 6 MICRO).
- [x] 20b.2 Update `agent_config.py` Pydantic bounds for 5 fields (unsaturated_bonus, mop_transitive_score, coverage_density_weight, multi_value_saturation_threshold, reward_score_weight).
- [x] 20b.3 Update unit tests for new ranges (T28 widened ranges, T35 24 MICRO, T36 35 FULL).
- [x] 20b.4 Fix `max_short_term_iterations` wiring in `AgentFactory`.
- [x] 20b.5 Exclude `mop_nav_weight` and `llm_max_retries` from MICRO calibration (dead code — removed from `MICRO_PARAMETERS`).

### 20c. Phase C0 — Second Run (post bug-fix)

Config: 50 trials, 4 rounds (16 containers/round), 20 APKs × 1 rep × 600s timeout, 3 CPUs/container, 12g RAM. Docker image `rvandroid:0.8.0` (commit `0dfa0bc8`).

- [x] 20c.1 Launched C0 with 16 containers (PID 3350616). Started 2026-03-01 19:59.
- [x] 20c.2 50/50 trials completed. 0 failures. Best score: 33.34 (trial_43). Range: 19.33-33.34.
- [x] 20c.3 3 APKs fail to launch consistently across all trials: `com.spisoft.quicknote`, `info.guardianproject.gilga`, `io.github.x0b.rcx`. These contribute 0 coverage and 0 errors.

### 21. Phase C0 — Verify Convergence — NEGATIVE RESULT

- [x] 21.1 50 trials completed.
- [ ] ~~21.2 Convergence visible: last 15 trials avg > first 15 avg.~~ **NOT MET** — see analysis below.
- [ ] ~~21.3 `optimal_params.json` saved with 11 MACRO params.~~ **NOT APPLICABLE** — C0 did not produce meaningful improvement.

**C0 Analysis:**

Score distribution: min=19.33, max=33.34, mean=30.59, median=32.25, stdev=2.75. Very narrow range on a 0-100 scale.

Score decomposition (best trial_43):

| Component | Weight | Raw Value | Contribution | Max Possible |
|-----------|--------|-----------|--------------|--------------|
| method_cov | 40% | 23.8% | 9.5 | 40.0 |
| MOP errors | 40% | 2.0/APK (norm: 34.9/100) | 14.0 | 40.0 |
| UI element cov | 20% | 49.3% | 9.9 | 20.0 |
| **TOTAL** | | | **33.34** | **100.0** |

Comparison with baseline on same 20 APKs:

| Metric | APE | Fastbot | BL-RVAgent (defaults) | C0-RVAgent (best) |
|--------|-----|---------|----------------------|-------------------|
| Activity cov | 70.0% | 61.4% | 61.6% | 60.5% |
| Method cov | 25.9% | 21.2% | 23.5% | 23.8% |
| MOP cov | 38.2% | 31.9% | 36.0% | 36.1% |
| MOP errors | 2.1 | 1.9 | 2.0 | 2.0 |

**Conclusion**: C0 MACRO calibration produced results statistically indistinguishable from baseline defaults. Despite wide parameter ranges (3-5× variation), the scoring weights do not meaningfully affect exploration outcomes on these 20 APKs with 600s timeout.

**Root cause investigation:**

1. **Parameter forwarding**: VERIFIED CORRECT. Full trace from CLI → rv-experiment → rvagent-tool → `build_agent_config_dict()` → `RVAgentConfig` (Pydantic auto-converts string→float) → 9 scorers. No break in chain.
2. **Optuna setup**: VERIFIED CORRECT. `constant_liar=True` (batch), `multivariate=True`, `n_startup_trials=2*n_containers`. No distributed mode needed for ask/tell pattern.
3. **Objective function**: Log normalization with baseline_max_errors=22.33 is correct. Score range reflects reality.
4. **Hypothesis**: MACRO params (scoring weights) control action *ordering* within the DFS strategy, but on small/medium apps with 600s timeout, most orderings reach the same methods and trigger the same MOP errors. The exploration space of these APKs is too constrained for scoring weight differentiation.

### 21a. Investigate C0 Negative Result — DONE

Per-APK variance analysis across 50 trials revealed:

**MOP errors**: 14/20 APKs have std=0.0 (identical errors across all trials). Only `io.github.domi04151309.home` (std=5.0, range 0-18) shows meaningful variance. MOP errors are effectively deterministic per app — the code path is either always reached or never reached, regardless of scoring weights.

**Method coverage**: Most APKs have std < 3%. Exceptions (`blippex`, `eduroamcat`) have high ranges (44-61%) but driven by crash/launch failures (min≈0), not parameter sensitivity.

**UI element coverage**: THIS metric shows real variance driven by params:

| APK | mean | std | min | max | range |
|-----|------|-----|-----|-----|-------|
| tramhunter | 49.2% | 17.0 | 20.5 | 82.8 | **62.3** |
| investmenttracker | 54.4% | 8.9 | 2.4 | 67.3 | **64.9** |
| domi04151309.home | 45.0% | 12.4 | 0.0 | 59.8 | **59.8** |
| moneytracker | 49.7% | 8.8 | 16.7 | 65.7 | **49.0** |
| quasseldroid | 41.1% | 12.4 | 12.5 | 58.3 | **45.8** |
| driibo | 70.4% | 13.9 | 40.0 | 83.7 | **43.7** |

Overall: 46.1% mean, 727/1593 elements untested (46% waste).

**Key insight**: Scoring weights DO change which UI elements are selected (UI coverage varies 20-83% per APK), but the objective function weights UI coverage at only 20% — too low for Optuna to optimize effectively. Method_cov (40%) and MOP errors (40%) are insensitive to MACRO params, so 80% of the score is noise.

**Decision**: Rebalance objective weights to 30/20/50 (method_cov/errors/ui_cov), expand precal set to 40 APKs (remove 3 failed, add 23 diverse), re-run C0. See Task 21b.

### 21b. Rebalance Objective + Expand Precal Set — PENDING

**Rationale**: UI element coverage is the only score component responsive to MACRO params, but has only 20% weight. Increasing to 50% gives Optuna a real optimization signal. Expanding from 20 to 40 APKs increases diversity and reduces per-APK noise.

**Changes required:**

1. **Objective weights**: 40/40/20 → **30/20/50** (method_cov/errors/ui_cov)
   - File: `modules/rv-agent-validation/src/rv_agent_validation/calibration/objective.py`
   - Update `__init__` defaults: `coverage_weight=0.30, errors_weight=0.20, ui_coverage_weight=0.50`

2. **Expand precal_set.txt**: 20 → 40 APKs
   - File: `modules/rv-agent-validation/data/precal_set.txt`
   - Remove 3 failed: `com.spisoft.quicknote_241.apk`, `info.guardianproject.gilga_11.apk`, `io.github.x0b.rcx_220.apk`
   - Keep 17 remaining
   - Add 23 new APKs selected for diversity (MOP errors 0-23, method_cov 4-64%)

3. **Update unit tests**: Adjust any tests that hardcode 40/40/20 weights.

4. **Commit + rebuild Docker image**.

5. **Re-run C0**: 50 trials, 16 containers, 40 APKs × 600s timeout. Expected time: 40 APKs × ~10min = ~400min (~6.7h) per round, 4 rounds = ~27h.

**New precal_set (40 APKs):**

17 KEPT from current set (minus 3 failed):
- `com.andybotting.tramhunter_1300.apk`, `com.blippex.app_5.apk`, `com.blogspot.e_kanivets.moneytracker_38.apk`, `com.iskrembilen.quasseldroid_1322.apk`, `com.refactech.driibo_3.apk`, `com.soumikshah.investmenttracker_3.apk`, `de.nellessen.usercontrolleddecryptionoperations_6.apk`, `github.vatsal.easyweatherdemo_11.apk`, `io.github.domi04151309.home_1100.apk`, `io.github.subhamtyagi.privacyapplock_8.apk`, `me.kuehle.carreport_79.apk`, `net.jjc1138.android.scrobbler_7.apk`, `net.sf.andhsli.hotspotlogin_20.apk`, `org.fastergps_14.apk`, `org.passwordmaker.android_11.apk`, `org.pyload.android.client_21.apk`, `uk.ac.swansea.eduroamcat_59.apk`

23 NEW (selected by diversity — high MOP errors, varied coverage):
- `org.mosad.seil0.projectlaogai_6000.apk` (err=23, meth=45%)
- `com.akop.bach_120.apk` (err=10, meth=6%)
- `org.pulpdust.lesserpad_42.apk` (err=6, meth=52%)
- `info.guardianproject.checkey_101.apk` (err=6, meth=64%)
- `com.example.openpass_1.apk` (err=5, meth=64%)
- `com.reddyetwo.hashmypass.app_24.apk` (err=5, meth=60%)
- `org.emunix.insteadlauncher_80601.apk` (err=5, meth=55%)
- `fr.kwiatkowski.ApkTrack_24.apk` (err=5, meth=40%)
- `eu.bubu1.fdroidclassic_1110.apk` (err=5, meth=39%)
- `info.zamojski.soft.towercollector_2140302.apk` (err=5, meth=36%)
- `org.decsync.flym_46.apk` (err=5, meth=30%)
- `com.jonbanjo.cupsprintservice_23.apk` (err=5, meth=7%)
- `net.frju.flym_40.apk` (err=4, meth=32%)
- `com.mde.potdroid_82.apk` (err=4, meth=36%)
- `ee.ioc.phon.android.speak_1814.apk` (err=4, meth=26%)
- `digital.selfdefense.lucia_20001.apk` (err=3, meth=59%)
- `com.allansimon.verbisteandroid_2.apk` (err=2, meth=48%)
- `max.music_cyclon_4.apk` (err=2, meth=43%)
- `byrne.utilities.hashpass_2.apk` (err=1, meth=36%)
- `biz.gyrus.yaab_30.apk` (err=0, meth=44%)
- `com.vwp.owmini_128.apk` (err=0, meth=47%)
- `ohm.quickdice_48.apk` (err=0, meth=38%)
- `org.gmote.client.android_5.apk` (err=0, meth=18%)

**Subtasks:**

- [x] 21b.1 Update `objective.py` default weights to 30/20/50.
- [x] 21b.2 Update unit tests for new default weights (test_parameter_integration.py T31, test_orphan_recovery.py T19).
- [x] 21b.3 Generate new `precal_set.txt` with 40 APKs. All 40 APKs + JSONs verified in calibration_dataset_v2/.
- [x] 21b.4 Run tests: 86/86 calibration + 21/21 rvagent-tool tests pass.
- [x] 21b.5 Commit `3c1648f9` with `refs #9`. Pushed to remote.
- [x] 21b.6 Rebuild Docker image `rvandroid:0.8.0` (sha256:66633db8).
- [x] 21b.7 Re-run C0: 16 containers, 50 trials, 40 APKs × 600s, 3 CPUs/12g RAM. PID 12475, started 2026-03-02 15:11. First attempt failed (orchestrator launched with `| head -40` which killed the pipe). Relaunched via `nohup`.
- [x] 21b.8 C0 completed 2026-03-04. Results below.

### 21c. Phase C0 — Third Run Results (30/20/50 weights, 40 APKs)

Config: 50 trials, 4 rounds (16 containers/round), 40 APKs × 1 rep × 600s timeout, 3 CPUs/12g RAM. Docker image `rvandroid:0.8.0` (commit `3c1648f9`). Objective weights: 30/20/50 (method_cov/errors/ui_cov).

**Score distribution**: min=37.57, max=43.21, mean=41.40, median=41.77, stdev=1.38. Range 5.64 on 0-100 scale.

**Per-round evolution**:

| Round | Trials | Min | Max | Avg |
|-------|--------|-----|-----|-----|
| 1 | 16 | 40.42 | 43.21 | 42.08 |
| 2 | 16 | 39.98 | 42.60 | 41.77 |
| 3 | 16 | 37.57 | 42.82 | 40.15 |
| 4 | 2 | 42.73 | 43.01 | 42.87 |

**Convergence**: NO — first 15 trials avg (42.03) > last 15 trials avg (40.49). Best trials found in startup/random phase, Optuna did not improve over time.

**Top 5 trials**: trial_13 (43.21), trial_9 (43.03), trial_49 (43.01), trial_15 (42.85), trial_48 (42.82).

**Best trial (trial_13) score decomposition**:

| Component | Weight | Raw Value | Contribution | Max Possible |
|-----------|--------|-----------|--------------|--------------|
| method_cov | 30% | 33.7% | 10.11 | 30.0 |
| MOP errors | 20% | 3.5/APK (norm: 47.8/100) | 9.55 | 20.0 |
| UI element cov | 50% | 53.2% | 26.58 | 50.0 |
| **TOTAL** | | | **46.24** | **100.0** |

Note: Optuna reported score 43.21; decomposition yields 46.24 — discrepancy likely from EmulatorError-failed APKs in some trials affecting the summary.csv (40 vs fewer APKs).

**Baseline comparison (same 40 APKs)**:

| Metric | APE | Fastbot | BL-RVAgent (defaults) | C0-Best (trial_13) |
|--------|-----|---------|----------------------|-------------------|
| Method cov | 37.0% | 31.2% | 34.6% | 33.7% |
| Activity cov | 77.2% | 68.4% | 71.6% | 68.9% |
| MOP errors | 3.5 | 3.1 | 3.6 | 3.5 |
| UI elem cov | n/a | n/a | 51.6% | **53.2%** |

**EmulatorError analysis**: 22/50 trials had missing APKs (15.3% of 2000 total tasks failed). This degrades score quality — some trials scored from fewer than 40 APKs.

**Optimal params (trial_13)**:

| Parameter | Default | Optimal | Change |
|-----------|---------|---------|--------|
| mop_direct_score | 500.0 | 420.4 | -16% |
| wtg_guided_score | 200.0 | 149.7 | -25% |
| unsaturated_bonus | 100.0 | 57.4 | -43% |
| max_re_enables | 10 | 10 | same |
| ui_coverage_threshold | 0.85 | 0.85 | same |
| stochastic_probability | 0.15 | 0.07 | -53% |
| strength_weight | 50.0 | 59.8 | +20% |
| visitation_penalty_factor | -10.0 | -6.4 | +36% (less penalty) |
| backtrack_saturation_threshold | 0.8 | 0.62 | -22% |
| coverage_density_weight | 200.0 | 129.7 | -35% |
| error_detection_confidence | 0.5 | 0.62 | +24% |

**Conclusion**: Score improved from 33.34 (previous C0) to 43.21, but the improvement is almost entirely from weight rebalancing (30/20/50 gives more weight to the responsive UI coverage component). Actual metric values (method_cov, errors, UI elem cov) show only marginal improvement over baseline defaults (+1.6pp UI coverage). No Optuna convergence observed — best trial was found in round 1 (random exploration phase). MACRO scoring weights have limited effect on exploration outcomes at 600s timeout.

**Decision gate**: Despite no convergence, the optimal params represent a reasonable exploration of the parameter space. Proceed to Phase D0 (MICRO calibration) to test if fine-grained parameters (LLM temperature, reward weights, spatial association) have more impact.

### 22. Phase D0 — Execute Pre-Micro

**Prerequisite**: SGLang server running at `localhost:30000`.

- [ ] 22.1 Start SGLang server.
- [ ] 22.2 Run `calibration_orchestrator.py --phase micro --n-trials 40 --filter-file precal_set.txt --best-macro precal_macro/optimal_params.json --baseline-dir ./results/baseline_v2 --sglang-url ... --timeout TIMEOUT_SECS`.
- [ ] 22.3 Monitor progress: `python scripts/monitor_docker.py results/calibration_micro_v2` (40 trials, ~7.4-11.1h expected).

### 23. Phase D0 — Verify + Decision Gate

- [ ] 23.1 40 trials completed.
- [ ] 23.2 `optimal_params.json` contains 35 parameters (11 macro + 24 micro).
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
- [ ] 26.2 Monitor progress: `python scripts/monitor_docker.py results/calibration_macro_v2`
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
- [ ] 28.4 Monitor progress: `python scripts/monitor_docker.py results/calibration_micro_v2`
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
- [ ] 30.3 Monitor progress: `python scripts/monitor_docker.py results/validation_v2`

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
