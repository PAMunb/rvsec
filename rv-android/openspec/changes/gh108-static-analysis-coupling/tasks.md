<!-- Dependency hints:
     - Groups 1-4 are independent and can run in any order (or in parallel).
     - Group 5 (J1, Java) is the only group requiring a reactor rebuild — keep it in its own commit.
     - Group 6 (D2) is the widest in reach; run it after 1-4 so a failure is easy to isolate.
     - Group 7 (Verification) runs after all other groups.
     File counts per group are 1-5, below the subagent-dispatch threshold of docs/WORKFLOW.md Section 5. -->

## 1. P3 — the CLI consumes the boolean

- [x] 1.1 `modules/rv-experiment/src/rv_experiment/__main__.py:747`: capture the return of `execute_with_config(experiment_config)`; on `False`, skip the `✅ Experiment completed successfully!` message and exit non-zero
- [x] 1.2 Confirm `execute_with_config` is still declared `-> bool` at `rv_experiment/experiment/experiment_controller.py:386` and that `__main__.py:747` remains its only call site (`grep -rn execute_with_config modules/`)
- [x] 1.3 Re-check the orchestrator table in plan.md Section 1 against the tree: `experimento-gh104/scripts/cycle.sh:30-33` (indifferent), `experimento-20260706/scripts/restart_exited.sh:12-20` (only 137), `experimento-20260604/scripts/run_smoke.sh:19-25` (now fails on partial Phase-2 failure)

## 2. D1 — SDK-root fallback in the gator launcher

- [x] 2.1 `lib/gator/gator:62-64`: fall back to `ANDROID_HOME` when `ANDROID_SDK_HOME` is absent, applying the fallback only when the resulting root is resolvable; keep `--sdk` as the highest-priority source
- [x] 2.2 Run both reproductions from plan.md Section 5: with only `ANDROID_HOME` exported, the launcher gets past `:64` both with and without `--sdk`
- [x] 2.3 Confirm no regression for setups exporting only `ANDROID_SDK_HOME` — that root must still win and resolve exactly as before

## 3. Dead parameter — five sites

- [x] 3.1 `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py:219-228`: remove `apks: List[App]` from the `_create_platform_config` signature
- [x] 3.2 `.../execution_controller.py:236`: remove the `apks: Application objects to test` line from the docstring
- [x] 3.3 `.../execution_controller.py:140`: drop the argument at the only call site
- [x] 3.4 `modules/rv-experiment/tests/experiment/test_execution_controller.py:207` and `:232`: drop `apks=mock_apks`
- [x] 3.5 Check whether `List[App]` and the `App` import are still used elsewhere in `execution_controller.py`; remove them if not (P3 — no vestiges)
- [x] 3.6 Run `/rv-test-run rv-experiment`

## 4. Documentation defects

- [x] 4.1 `docs/20260730_verificacao_consistencia_gh91.md:617`: `--sdkpath` → `--sdk`
- [x] 4.2 `docs/20260821_relatorio_analise_estatica_defeitos.md:92`: `--sdkpath` → `--sdk`
- [x] 4.3 `docs/architecture/static-analysis.md:85`: drop the claim that the config validates launcher / client JAR / `android.jar` / MOP source existence — `validate_on_init=False` (`rv-experiment/config.py:956`) disables it on the `rv-experiment` path
- [x] 4.4 `docs/architecture/static-analysis.md` §3: record the `specification_set → mop_dir` coupling that Group 6 establishes
- [x] 4.5 Confirm the deliberate exclusions are untouched: `openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/{design.md:143,tasks.md:69}` (archived record) and `docs/20260821_verificacao_relatorio_analise_estatica.md` (mentions the flag correctly, as the thing that does not exist)

## 5. J1 — the sentinel only on the post-WTG write (Java; own commit)

- [x] 5.1 `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/json/JsonReportWriter.java:111`: add an `emitSentinel` parameter to `write(...)` and emit `w.name(COMPLETE).value(true)` only when it is `true`
- [x] 5.2 `.../RvsecAnalysisClient.java:169-170`: the pre-WTG call passes `emitSentinel = skipWtg()` — `false` when WTG will run, `true` when it is skipped by client parameter and this write is the run's last
- [x] 5.3 `.../RvsecAnalysisClient.java:202-203`: the post-WTG call passes `emitSentinel=true`
- [x] 5.4 `.../RvsecAnalysisClient.java:157-163`: rewrite the comment, which currently asserts the opposite of what the code does (P4 — describe current state)
- [x] 5.5 `.../client/src/test/java/presto/android/gui/clients/json/SentinelEmissionTest.java`: add a case calling `write(..., emitSentinel=false)` directly and asserting the resulting file contains no `complete` key
- [x] 5.6 Run the client tests **with tests enabled** — `mvn -pl rvsec/rvsec-android/rvsec-gator/client test -DskipTests=false`. `rvsec-gator/pom.xml:18` pins `<skipTests>true</skipTests>`, so a green reactor build proves nothing
- [x] 5.7 Rebuild the reactor (`mvn clean install -DskipMopAgent -DskipTests`, JDK 21 in the prefix) and confirm the refreshed jar landed in `rv-android/lib/gator`
- [x] 5.8 Commit Group 5 separately, together with the re-copied jar

## 6. D2 — `mop_dir` derives from the specification set

- [x] 6.1 `modules/rv-experiment/src/rv_experiment/config.py:695-719`: extract the `specification_set → directory` dispatch into a single method, preserving the `custom` validation and the `ConfigurationError` default branch
- [x] 6.2 `modules/rv-experiment/src/rv_experiment/config.py:949-958`: call that method and pass the result as `mop_dir` in the `RVStaticAnalysisConfig(...)` kwargs
- [x] 6.3 Confirm `get_monitor_generation_config()` still dispatches all four values through the extracted method with no behavior change
- [x] 6.4 Add a test asserting the resulting `mop_dir` for `jca`, `jca_android`, `generic` and `custom` (with `custom_specs_dir`), and that an unsupported value still raises `ConfigurationError`
- [x] 6.5 Do **not** edit the `jca` default at `rv-static-analysis/config.py:199-208` — it stays as the safety net for standalone callers. Removing it is the declared escalation point to FF SDD (plan.md Section 2)
- [x] 6.6 Measure the declared side effect: a `--specification-set generic` run on `apks_examples/cryptoapp.apk` with static analysis on shows `mopDir=.../generic` in the GATOR argv and 296 resolved signatures, against 120 before
- [x] 6.7 Contra-proof: a `jca` run is unchanged end to end — same `mopDir`, same 120 signatures — confirming the frozen ruler is untouched
- [x] 6.8 Run `/rv-test-run rv-experiment` and `/rv-test-run rv-static-analysis`

## 7. Verification

- [x] 7.1 Run `/rv-qa-lint-fix rv-experiment` and `/rv-qa-lint-fix rv-static-analysis`
- [x] 7.2 Run `/rv-verify rv-experiment` and `/rv-verify rv-static-analysis`
- [x] 7.3 `uv run pytest --import-mode=importlib -o "addopts=" tests/` green in both modules
- [x] 7.4 `grep -rn -- "--sdkpath" docs/` finds nothing in the two live documents; `grep -n "apks" modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py` shows no reference to the removed parameter
- [x] 7.5 Walk every acceptance criterion in plan.md Section 5 and check it off
- [ ] 7.6 Check off the acceptance criteria in issue #108, then close it (`closes #108` in the final commit) and move the Kanban card to Done
- [ ] 7.7 Archive with `openspec archive "gh108-static-analysis-coupling" --skip-specs`
