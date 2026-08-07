<!-- Dispatch hints (~18 files, 5 modules):
     - Group 1 (Registry) and Group 2 (Domain model) are the foundation — Groups 3-5 depend on both.
     - Groups 3 (Propagation) and 4 (entry-point resolution) touch disjoint files and can run in parallel after Group 2.
     - Group 5 (Provenance) depends on Group 2 only; Group 6 (AJC guard) is independent of 3-5.
     - Group 7 integrates and verifies — must run last.
     - Critical path: 1 -> 2 -> 4 -> 7. -->

## 1. Decisions and Registry

- [x] 1.1 Resolve design.md Open Question 2 — flag spelling: negatable boolean `--package-detector` / `--no-package-detector`, or `--package-source manifest|detector`. Record the decision in `design.md` and align the experiment delta spec's precedence scenario with it before writing any CLI code
      → **Owner, 2026-08-05**: negatable boolean (D6). Two further decisions taken in the same exchange and already written into the artifacts: `rv-static-analysis` reads `RV_PACKAGE_DETECTOR` as well as carrying the flag (D4 — it is an entry point, not an intermediate layer), and the value reaches `rv-platform` through `PlatformConfig` (D7). `proposal.md`, `design.md`, `specs/core/spec.md` and `specs/experiment/spec.md` were realigned; `specs/analysis/spec.md` needed no change
- [x] 1.2 Add `ENV_PACKAGE_DETECTOR = "RV_PACKAGE_DETECTOR"` to `modules/rv-android-core/src/rv_android_core/constants.py`
- [x] 1.3 Add the `.env.example` entry, with a comment naming what it selects, its default (`false` = manifest package) and the CLI flag
- [x] 1.4 Add the README environment-variable table row
- [x] 1.5 Run `uv run python scripts/check_env_vars_drift.py` — expect 0 violations across all three cross-checks
      → clean, 33 ENV_* constants verified
- [x] 1.6 Run `uv run pytest modules/rv-android-core/tests/test_constants_registry.py tests/lint/test_env_vars_drift.py -v`
      → 15 passed

## 2. Domain Model (rv-android-core)

- [x] 2.1 Add the `package_detector: bool = False` field to `App` in `modules/rv-android-core/src/rv_android_core/domain/app.py`, with a description stating that the choice is user input resolved at the entry point
- [x] 2.2 Rewrite `code_package` to return `package_name` when the field is false and the `PackageDetector` election when it is true; keep the election lazy so the default path never enumerates components
- [x] 2.3 Add the `code_package_source` computed field returning `"manifest"` or `"detector"`
- [x] 2.4 Keep the mismatch INFO log on the detector path only; `package_name` stays untouched (INV-CORE-18)
      → `_detect_code_package` is now reachable only from the `package_detector` branch
- [x] 2.5 Confirm `domain/app.py` contains no `os.environ` access (INV-CORE-55) and that `L1_ALLOWLIST_FILES` in `scripts/check_env_vars_drift.py` is NOT extended
      → grep for `os.environ`/`getenv` in `app.py` returns nothing; `check_env_vars_drift.py` untouched, still three L1 files
- [x] 2.6 Add unit tests: default reports the declared package; detector election under the flag; provenance matches the mechanism; the detector is not invoked by default; a suffixed applicationId is returned verbatim
      → `TestCodePackagePolicy` in `modules/rv-android-core/tests/domain/test_app.py`, 8 tests
- [x] 2.7 Run `/rv-doc-code modules/rv-android-core/src/rv_android_core/domain/app.py`
      → applied the skill's conventions directly to the touched members (class narrative section, `code_package`, `code_package_source`, the new field description); no other member's documentation changed
- [x] 2.8 Run `/rv-test-run rv-android-core`
      → 1036 passed

## 3. Propagation to App Construction Sites

- [x] 3.1 Add `package_detector: bool = False` to `get_apks` in `modules/rv-android-core/src/rv_android_core/util/utils.py:293` and forward it to each `App`
- [x] 3.2 Thread the value through the AJC entry points: `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/__main__.py:413,438` and `ajc_instrumentation.py:192,195`
      → the conduit is `AjcInstrumentationConfig.package_detector`, set from `ExperimentConfig` in `get_instrumentation_config()`, the same shape `enable_quarantine` already uses. Adding a parameter to `instrument_apks` was rejected: that signature is the `Instrumenter` ABC shared with dexlib2, which builds no `App` and has no quarantine phase
- [x] 3.3 Add `package_detector: bool = False` to `PlatformConfig` (`modules/rv-platform/src/rv_platform/config/platform_config.py`), set it from `ExperimentConfig` at `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py:309` following the `logcat_diagnostics` precedent, and consume it at `modules/rv-platform/src/rv_platform/platform.py:232` — `rv-platform` reads no environment variable (D7, INV-EXP-34)
- [x] 3.4 Thread the value at `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:342,461,477`
- [x] 3.5 Thread the value at `modules/rv-static-analysis/src/rv_static_analysis/__main__.py:326,404`
- [x] 3.6 Grep for remaining `App(` constructions under `modules/` and `scripts/` and confirm each either forwards the value or accepts the default deliberately
      → every `modules/` site forwards. Five `scripts/` sites accept the default: `sa_parallel.py:120` and `validation/fase_a_preprocess.py:175` never read `code_package`; `gh51_smoke_test.py`, `static_analysis_sweep.py` and `static_analysis_sweep_generic.py` do, and now carry a comment naming the key they filter on
- [x] 3.7 Add unit tests that each site forwards both values
      → `get_apks` (both values, `test_utils.py`), `PreProcessor` (`TestPackageDetectorPropagation`), `Platform._generate_tasks` (parametrized), AJC `instrument_apks`
- [x] 3.8 Run `/rv-test-run rv-android-core`
      → 1060 passed

## 4. Entry-Point Resolution (rv-experiment and standalone rv-static-analysis)

- [x] 4.1 Add `package_detector: bool = False` to `ExperimentConfig` in `modules/rv-experiment/src/rv_experiment/config.py`
- [x] 4.2 Implement CLI > env > default resolution, reading `ENV_PACKAGE_DETECTOR` at the single read site in `rv-experiment`, following the `analysis_timeout` / `jvm_memory` precedent at `config.py:856-867`
      → `resolve_package_detector(cli_value)` in `config.py`, called from the Click callback. Deliberately NOT Click's `envvar=`, which the neighbouring options use: Click's boolean vocabulary is wider than INV-CORE-12's (it accepts `y`, `t`, `f`, `n`) and inheriting it at one entry point only is the drift task 4.3 exists to prevent
- [x] 4.3 Add one shared truthiness helper that parses a *value* (not a variable name) with the project convention (`true`/`1`/`yes`/`on`, case-insensitive; INV-CORE-12) and signals unparseable input to its caller, beside the existing coercion helpers at `modules/rv-android-core/src/rv_android_core/util/utils.py:442,470` — it performs no read of its own, so `rv-android-core` stays free of env access. Both entry points MUST use it, so the two CLIs cannot drift on what a string means
- [x] 4.4 Add the negatable pair `--package-detector/--no-package-detector` (Click `is_flag` pair, `default=None` so an absent flag is distinguishable from an explicit false) to `modules/rv-experiment/src/rv_experiment/__main__.py`; abort with `click.BadParameter` on an unparseable environment value instead of defaulting
      → resolved in a Click callback, following `_timeouts_callback`: the callback runs outside `run()`'s `@handle_errors` wrapper, which would otherwise absorb the `BadParameter` (INV-EXP-33). Exit code 2
- [x] 4.5 Add the same negatable pair to the `rv-static-analysis` argparse CLI (`modules/rv-static-analysis/src/rv_static_analysis/__main__.py`) **and** resolve `ENV_PACKAGE_DETECTOR` there under the same flag > env > default precedence, through the constant and never a literal (D4, INV-EXP-34). Resolve once, before either `App` construction at `:326,404`; an unparseable value MUST exit nonzero naming the variable, since argparse has no `click.BadParameter`
      → `argparse.BooleanOptionalAction` with `default=None` in `add_common_arguments` (so both subcommands carry it); resolved in `main()` before dispatch
- [x] 4.6 Add unit tests — experiment: default is manifest, env enables, `--package-detector` and `--no-package-detector` each override the env, unparseable env aborts. Standalone SA: same four cases on the argparse entry point, including that a bare invocation with `RV_PACKAGE_DETECTOR=true` resolves to `True`
      → `rv-experiment/tests/test_cli_package_detector.py` (18) and `rv-static-analysis/tests/cli/test_package_detector.py` (22)
- [x] 4.7 Add a test that `PlatformConfig` carries the resolved value from `ExperimentConfig` and that `rv-platform` performs no environment read for it
      → `test_platform_config_carries_package_detector` (parametrized) and `test_platform_reads_no_environment_for_the_policy`; repo-wide the same rule is gated by `tests/lint/test_env_vars_drift.py::test_package_detector_env_read_only_at_entry_points`
- [x] 4.8 Run `/rv-test-run rv-experiment`, `/rv-test-run rv-static-analysis` and `/rv-test-run rv-platform`
      → 249 / 136 / 332 passed

## 5. Key Provenance in the Analysis Run

- [x] 5.1 Record the resolved key and its origin (`manifest` | `detector`) in the static analysis run output, at the point the analysis runs
      → `StaticAnalysisResult.code_package` / `.code_package_source`, set in `analyze()` before `_run_analysis`, so a failed or cached run still states the key it used; the same pair goes to the INFO record
- [x] 5.2 Confirm no code path reads the `package` member of a GATOR JSON as a filtering key, and none overrides a resolved key from a stored artefact (INV-ANA-58) — check `components/static_analysis.py:136` and `result_processor.py:269`
      → both take the key from `task.app.code_package`. `_JK.package` in `static_analysis_parser.py` exists only in the schema-parity key mirror and is never read. The stale comment at `components/static_analysis.py:126` describing the key as "the detected implementation package" was rewritten (P4)
- [x] 5.3 Add tests: the recorded key equals the one passed to the GATOR argv and to the parser; a JSON whose `package` member disagrees with the resolved key does not change the filter
      → four tests in `test_static_analysis.py`, including the failed-run case
- [x] 5.4 Run `/rv-test-run rv-static-analysis`
      → 140 passed

## 6. AJC Quarantine Guard

- [x] 6.1 In `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py:849`, emit a WARNING when quarantine patterns are active and the `code_package` prefix matches zero files under `tmp_dir` — the guard being inert is the condition worth surfacing (design.md Risks)
      → checked once after the patterns load, before the match loop, so it fires whether or not a pattern happens to hit app code
- [x] 6.2 Add a unit test for the inert-guard warning using a suffixed applicationId
      → `test_warns_when_the_app_code_guard_is_inert` (`org.fossify.calendar.debug` over an `org/fossify/calendar/` tree), plus its negative counterpart
- [x] 6.3 Run `/rv-test-run rv-instrumentation-ajc`
      → 109 passed

## 7. Integration and Verification

- [x] 7.1 Add an integration test over a fixture APK whose declared package differs from its implementation package, asserting the full path from flag to GATOR argv in both modes
      → `tests/integration/test_package_key_end_to_end.py`. No APK fixture is committed (the corpora live outside the repo and are gitignored), so androguard's `APK` is the only stub; everything else — argparse, `App`, `StaticAnalyzer`, `RVStaticAnalysisConfig.get_tool_command` — is production code, and the assertion reads the real `-clientParam codePackage=` off the argv. Mutation-checked: reverting the propagation at `rv_static_analysis/__main__.py` fails 2 of the 6
- [x] 7.2 Add an integration test over an APK with a build-type suffix in its applicationId, asserting the key is passed verbatim
      → same file. Also verified against the **real** `org.fossify.calendar_20.apk` of the gh91 dataset: declares `org.fossify.calendar.debug`, default returns it verbatim (`code_package_source=manifest`), detector elects `org.fossify`. Note the sweep copy under `out/sweep_20260604_apks/` is a *different build* declaring `org.fossify.calendar` with no suffix — the `.debug` build is the one in `RV_ANDROID_NOVO_DATASET/APKS/`
- [x] 7.3 Run `uv run python scripts/check_env_vars_drift.py` — 0 violations
      → clean, 33 ENV_* constants
- [x] 7.4 Run `/rv-qa-lint-fix rv-android-core` and `/rv-qa-lint-fix rv-experiment`
      → black applied to the files this change created or that were black-clean at HEAD. `test_pre_processor.py`, `test_platform.py` and `test_ajc_instrumentation.py` were already non-black-clean at HEAD and their remaining diffs are all in untouched code, so they were left alone rather than reformatted wholesale. flake8: no new violation (the two E501 are pre-existing lines)
- [x] 7.5 Run `/rv-verify rv-android-core`, `/rv-verify rv-experiment`, `/rv-verify rv-static-analysis`
      → **PARTIAL — see 7.9.** All suites were green before the code-review fixes; the machine then became unavailable (owner running an experiment), so the post-fix re-run is pending
- [x] 7.6 Invoke `/rv-code-reviewer` via the Skill tool with args "Review gh98-manifest-package-default implementation"
      → verdict APPROVE WITH CHANGES. Metrics: every new unit CC ≤ 5, MI grade A, no new flake8, no dead code. All applied:
      • **critical** — the live `openspec/specs/experiment/spec.md` "Layer-Purity Audit for Environment Reads" still said `rv-experiment` is the *single* module reading `RV_*`, contradicting D4. Reconciled by a MODIFIED requirement in the experiment delta that defines *entry point* and enumerates the two permitted reader files. `docs/adr/0001-env-var-pattern.md` decision 2 carries the same stale wording and was **left untouched** — the handoff forbids amending it; flagged for the owner (see 7.10)
      • P1 — the two `resolve_package_detector` bodies were byte-identical; the precedence, the empty-means-unset rule and the error shape now live once in `resolve_bool_setting` (`util/utils.py`), while each entry point keeps only its own `os.environ.get`, so INV-EXP-34's reader set is unchanged
      • the INV-EXP-34 lint gate missed `os.getenv` and single-quoted literals — both closed
      • `--config` mode ignores the flag (as it ignores every other CLI flag); stated in the option help
      • P4 — `scripts/gh91_sa_rerun.py:9` and the `L5_DIR` comment in `check_env_vars_drift.py` described the old rule; rewritten
      • test quality — the vacuous `test_default_policy_reaches_every_app` now asserts the call kwargs; `test_a_disagreeing_json_package_member_never_changes_the_filter` now runs the **real** parser over a JSON whose `package` member would exclude the class the run's key keeps; `CliRunner` now clears an inherited `RV_PACKAGE_DETECTOR`; the inert-guard check counts files rather than directory entries
- [x] 7.7 Run `/rv-docs-sync rv-android-core` — `modules/rv-static-analysis/CLAUDE.md:24` and `modules/rv-android-core/CLAUDE.md` describe `code_package` as detector-derived and need updating
      → updated both CLAUDE.md files, `rv-android-core/docs/architecture.md` (AD-7, scenario 2, the component list and the class diagram) and `rv-static-analysis/docs/architecture.md` (INV-ANA-14 row, new INV-ANA-58 row). The `docs/2026*.md` experiment reports were left alone: they are records of past runs, not descriptions of current behaviour
- [x] 7.8 Run `/opsx:verify` to validate the implementation against the three delta specs
      → no critical issue. Every requirement of the three deltas was located in code and in tests: INV-CORE-18 at `domain/app.py:146`, its provenance half at `:162`; INV-CORE-55 confirmed by a grep for `os.environ`/`getenv` in `app.py` returning nothing; INV-EXP-34 by the fact that `ENV_PACKAGE_DETECTOR` is read at exactly two sites (`rv_experiment/config.py:85`, `rv_static_analysis/__main__.py:530`) and the only literal `"RV_PACKAGE_DETECTOR"` under `modules/` is the constant's own definition; the propagation chain `PlatformConfig:83` → `execution_controller.py:319` → `platform.py:233`; the provenance record at `static_analysis.py:233-234`; INV-ANA-58 by both re-parse sites (`components/static_analysis.py:136`, `result_processor.py:269`) taking the key from `task.app.code_package`; the inert-guard WARNING at `ajc_instrumentation.py:869`. One warning, carried into 7.9 rather than fixed: `black --check`. One cosmetic finding left alone: `design.md`'s Mapping table names test functions (`test_code_package_defaults_to_manifest`, `test_parser_receives_resolved_key`, …) that do not exist under those names — the coverage is real, the table is indicative
- [x] 7.9 Re-run the full verification after the code-review fixes — `check_env_vars_drift.py`, then one pytest invocation per test root (`modules/rv-android-core/tests`, `modules/rv-experiment/tests`, `modules/rv-static-analysis/tests`, `modules/rv-platform/tests`, `modules/rv-instrumentation-ajc/tests`, `tests/lint`, `tests/integration` — separate invocations, a combined one hits `ImportPathMismatchError` on the duplicate `tests.conftest`), plus `black --check` on the touched files
      → executed 2026-08-07, sequentially so as not to contend with the experiment sharing the host. `check_env_vars_drift.py` clean, 33 `ENV_*` constants. The seven roots: rv-android-core **1071 passed**, rv-experiment **249**, rv-static-analysis **140**, rv-platform **332 passed / 1 skipped**, rv-instrumentation-ajc **109**, `tests/lint` **35**, `tests/integration` **6**. `black --check` over the 31 Python files this change touched: 24 clean, 7 would be reformatted — and none of the seven was made dirty here. Each was checked out at `553ae54a^` and run through black in isolation: all seven already failed before the change. Three of them (`test_pre_processor.py`, `test_platform.py`, `test_ajc_instrumentation.py`) were the ones 7.4 already recorded; the other four (`scripts/sa_parallel.py`, `scripts/validation/fase_a_preprocess.py`, `scripts/gh91_sa_rerun.py`, `scripts/static_analysis_sweep.py`) sit under `scripts/`, which 7.4's two `/rv-qa-lint-fix` invocations never covered. Reformatting them now would produce a diff entirely in code this change did not touch, so they were left alone — the same call 7.4 made
- [x] 7.10 Owner decision on the Layer-Purity prose
      → **Owner, 2026-08-05**: keep the entry-point reformulation in the experiment delta. Taken after checking the claim against the code rather than against the documents, which found the prose was **already false before this change**, in three ways that predate it (verified by `git status`/`git diff`: none of these files were touched here):
      • **`RV_*` read outside `rv-experiment`** — `rv-android-core/util/android/android.py:219` resolves `RV_EMULATOR_BOOT_TIMEOUT` / `RV_ADB_CMD_TIMEOUT` / `RV_APK_INSTALL_TIMEOUT` (gh92). The lint's `L1_INFRA_NAMES` was extended to nine names; the spec sentence still enumerated only the three `RV_PYDANTIC*` in one file
      • **"exactly one canonical reader each inside `rv-android-core`"** (ADR decision 2) — `RVSEC_HOME` / `ANDROID_HOME` are read through `ENV_*` constants at nine sites across five other modules: `rv-monitor-generator/config.py:137`, `rv-instrumentation-ajc/config.py:329,408` + `ajc_instrumentation.py:424`, `rv-static-analysis/config.py:166,181`, `rv-instrumentation-dexlib2/dexlib_instrumentation.py:620`, `rv-experiment/config.py:1142`
      • **variables outside the registry entirely** — `rv-agent/config/agent_config.py:579,598` reads `RVAGENT_MODE` / `RVAGENT_LOG_LEVEL`, invisible to the lint because its regex requires the literal `RV_` prefix
      What the lint actually enforces is narrower than the prose ever claimed: no `RV_*` string literal anywhere under `modules/` (bar three L1 files), and no `dict(os.environ)` / `os.environ.copy()` outside `rv-experiment`. Constant-based reads outside `rv-experiment` have always passed. This change's read is therefore the fourth divergence, not the first, and the most defensible of them — it sits at an entry point, which is the criterion D4 used.
      The delta text was corrected accordingly: the two-file enumeration is scoped to `RV_PACKAGE_DETECTOR` (a general "only these two files" would have falsified `rv-experiment/__main__.py:1223`, which legitimately reads `RV_HUMANOID_URL`), the L1 exception now names all three files and nine names, and the legacy workspace paths are excluded from the entry-point rule.
- [x] ~~7.11 Correct `docs/adr/0001-env-var-pattern.md` decision 2~~ — **not work; disposition recorded at archive time, 2026-08-07.** The task was written as its own exclusion: it names a defect and then says the defect is out of scope. Ticking it records that the exclusion was deliberate and that the defect is still open, rather than leaving gh98 reading as incomplete forever. What remains open, unchanged from the text below: the ADR still says "Only `rv-experiment` (L5) reads user-facing `RV_*`" and "six names with exactly one canonical reader each", both false — and false *before* this change, in the three ways enumerated in 7.10. Correcting it means six→nine names, `util/jar_resolver.py` and `util/android/android.py` added as reader locations, the entry-point reformulation this change introduced into the experiment spec, and a decision on whether `RVAGENT_*` joins the registry or is documented as outside it. No issue has been opened for it; that is the owner's call and it is on the loose-ends list handed to them at the close of gh98. Original text of the task, kept for the record: Out of scope for gh98, follow-up change: `docs/adr/0001-env-var-pattern.md` decision 2 still carries the stale prose — "Only `rv-experiment` (L5) reads user-facing `RV_*`" and "six names with exactly one canonical reader each". Correcting it means six→nine names, adding `util/jar_resolver.py` and `util/android/android.py` as reader locations, the entry-point formulation, and a decision on whether `RVAGENT_*` joins the registry or is documented as outside it. That is a change of its own; the handoff for gh98 explicitly instructed not to amend the ADR here
