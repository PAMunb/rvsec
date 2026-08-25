# Change Plan: Experiment ↔ static-analysis coupling — sentinel, `mop_dir`, exit code, SDK root

**Date**: 2026-08-25
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#108](https://github.com/PAMunb/rvsec/issues/108)
**PRD Reference**: FR06 (REACH — `reaches_target` / `directly_reaches_target`), FR12 (method coverage tracking), FR16 (CLI), NFR05 (configurability), NFR06 (observability), NFR08 (reproducibility)
**Domains**: experiment, analysis, platform

## 1. Context

Six defects sit on the seam between `rv-experiment` and the static-analysis subsystem. They are what survived a triage of 24 initial claims: 15 died because an existing invariant or guard already covered the case, and 3 more (the `gator` cleanup) died on a second pass. Nothing entered without a checked `file:line` citation, an answer to *"is there already an invariant, spec or guard covering this?"*, and a consumer that reads what the fix repairs.

The source analysis, with the four reproductions and the full refutation table, is `docs/20260821_plano_correcao_analise_estatica.md` (Phase-0 reference material, not an OpenSpec artifact). Read it for the reasoning behind each verdict; this plan carries only what implementation needs.

### J1 — the `complete` sentinel lies

`JsonReportWriter.java:111` emits `"complete": true` at the end of **every** successful `write()` call, including the pre-WTG write issued at `RvsecAnalysisClient.java:165-170`. A run killed by the timeout inside WTG construction therefore leaves on disk an artifact marked complete. This violates INV-ANA-31 (`openspec/specs/analysis/spec.md:363`), which states that truncated outputs MUST NOT contain the field.

Five APKs of the `SA_RERUN_gh91_wtg` campaign prove it in production data: all five have `timed_out: true`, `returncode: 206` (`sys.exit(-50)` from `lib/gator/gator:113`, i.e. the internal `TimeoutExpired` branch), `transitions: []` — and `"complete": true`.

The gate exists and is crossed. `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py:249-253` raises `DerivationError` when the sentinel is missing; it exists precisely to reject these five, and they pass. `scripts/gh91_campaign.py:126-147` already compensates by hand, requiring the sentinel **and** `timed_out == False` from the `_progress` record; the `rv-platform` pipeline does not compensate. Since the APE-RV path is what the gh104 campaign runs, this is a live consumer.

Scoping, stated honestly: the coverage denominator (`reachability`) is intact in all five, because it is written before WTG. What is lost is `transitions`/`windows`. No published coverage number is inflated by this defect.

The comment at `RvsecAnalysisClient.java:157-163` asserts the opposite of what the code does — *"the pre-WTG write does NOT emit the sentinel"* — and is what kept the defect invisible.

The rule the repair installs is not "the first write never claims completeness" but "a write claims completeness only when it is the run's last". The two differ on one path: with `skipWtg=true` the client returns immediately after the pre-WTG write, so that write is the run's end and its sentinel is legitimate — which is exactly why the gh91 campaign, which passed `skipWtg=true`, could not hit this defect.

### D2 — the numerator comes from one specification set, the denominator from another

Two configurations are derived from the same `specification_set` through independent paths:

- `ExperimentConfig.get_monitor_generation_config()` (`modules/rv-experiment/src/rv_experiment/config.py:695-719`) dispatches all four values correctly and raises `ConfigurationError` on the default branch. The monitors woven into the APK match the requested set.
- `ExperimentConfig.get_static_analysis_config()` (`config.py:949-958`) **never passes `mop_dir`**. The string does not appear anywhere in `modules/rv-experiment/src/`, so the default at `modules/rv-static-analysis/src/rv_static_analysis/config.py:199-208` pins the literal `jca` for every run, whatever the requested set.

That value becomes `-clientParam mopDir=...` in the GATOR argv (`rv-static-analysis/config.py:369`). `MopSpecsTargetSource:30-31` resolves the target-method list from it via `JavamopFacade`, which produces `reachesTarget` in the `.apk.json`, which `modules/rv-platform/src/rv_platform/components/result_processor.py:487-490` converts into `cov_reaches_target` and `cov_directly_reaches_target`.

Severity graded by set (counts produced by `JavamopFacade` itself — the same resolver GATOR uses, not a regex approximation):

| Set | `.mop` files | signatures | pairs | owners | Effect |
|---|---|---|---|---|---|
| `jca` | 23 | 120 | 68 | 22 | none — matches the pinned default |
| `jca_android` | 23 | 131 | 68 | 22 | none in pairs: measured again on 2026-08-25, after gh105 restored the missing `(MessageDigest, reset)` pair, it now covers the same 68 pairs as `jca` over 131 signatures (the plan's original 119/67 reading dates from 2026-08-21, before that repair) |
| `generic` | 118 | 296 | 284 | 95 | **intersection with `jca`: zero pairs** |
| `custom` | arbitrary | — | — | — | unpredictable, same mechanism |

In a `--specification-set generic` run the APK is woven over 284 `(class, method)` pairs of `ReentrantLock`/`Condition`/`Iterator`, while `cov_reaches_target` answers *"how many app methods reach one of the 68 JCA pairs?"* — two sets with no element in common. It is not a loss of precision; it is a different question, and the correct one is never computed.

Decision 7 of `openspec/specs/experiment/spec.md:67` states that specification sets are never mixed within a single experiment. Its following sentence covers only monitor generation; the coupling with static analysis was never written down, and that is the gap this change closes in code (not in the spec — see Scope).

Observed damage across the project's whole history is **zero**. A sweep of every `experiment_config.json` outside `backup/` (968 files) returns 963 `jca`, 4 `jca_android`, 1 `custom`, 0 `generic`. The single `custom` run (`results/gh99_jca_android_monitors`) has `run_static_analysis: false`, so the defect could not bite. The only two exposed runs are the gh105 probes (`results/gh105_reach_probe`, `results/gh105_reach_probe_b` — `jca_android` with analysis on; the fourth `jca_android` hit is `data/gh105/evidence/reach-probe/`, an evidence copy of the same probe), where the pair sets now coincide and the end-to-end measurement produced 0 differing verdicts over 106 methods. The manual path already works around it: `scripts/static_analysis_sweep_generic.py:878-879` accepts an explicit `--mop-dir`.

What the fix buys is that `generic` and `custom` stop being unusable for coverage, and that a silent failure mode — a plausible, wrong number in a `summary.csv` column — goes away.

**Declared side effect.** Today every run points GATOR at 120 signatures. After the fix a `generic` run points at 296, so target-resolution cost and the content of `reachesTarget` change for that set. Nothing regresses, because no campaign runs `generic` through `rv-experiment`, but it is an observable behavior change and acceptance must measure it rather than assume it.

### P3 — the CLI declares unconditional success

`execute_with_config()` is declared `-> bool` (`modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py:386-400`) and returns the `False` that `ExperimentController.run()` produces when Phase 2 reports failure. `modules/rv-experiment/src/rv_experiment/__main__.py:747` discards it, so `✅ Experiment completed successfully!` prints unconditionally and `sys.exit(1)` happens only inside the `except`. `experiment/spec.md:276` and `:281` mandate that `False`, and no caller reads it. `__main__.py:747` is the only call site in the repository.

The blast radius matters because both Docker entrypoints `exec` the CLI (`docker/rvandroid/docker-entrypoint.sh:101`, `docker/rvandroid/docker-entrypoint.frozen-no-dev.sh:94`), so the container exit code becomes the CLI's. A sweep of every campaign orchestrator that reads `State.ExitCode`:

| Orchestrator | What it does with the exit code | Effect of the fix |
|---|---|---|
| `experimento-gh104/scripts/cycle.sh:30-33` | keys resume on `State != "running"` — does not read the code | none; the campaign in preparation is indifferent |
| `experimento-20260706/scripts/restart_exited.sh:12-20` | restarts only `ExitCode 137` (OOM-kill), *"e SOMENTE esses"* | none; exiting 1 triggers no re-run |
| `experimento-20260604/scripts/run_smoke.sh:19-25` | `exit $EXIT` — aborts the smoke on non-zero | **changes**: a smoke with a partial Phase-2 failure now fails, which is the correct outcome |

The remaining scripts (`monitor_*.sh`, `rv_status.py`) read `State.Status`, not the code.

### D1 + G1 — the SDK root never reaches GATOR

`lib/gator/gator:62-64` reads `os.environ['ANDROID_SDK_HOME']` with a bare subscript — no `get`, no default, no alternative. Anyone with only `ANDROID_HOME` exported (the normal case outside Docker) gets a raw `KeyError`. Two traps come with it:

1. The flag is **`--sdk`** (`lib/gator/gator:195`, `dest='sdkpath'`). **There is no `--sdkpath`**, and because `:254` uses `parse_known_args()`, passing it raises no error: the token is forwarded to the JVM and the `KeyError` fires anyway. The wrong name is reproduced in four documents.
2. The fallback must apply **only when the root is resolvable**, so as not to regress setups that export only `ANDROID_SDK_HOME`, which is what the documentation has been prescribing since July.

Fixing it in the launcher covers all ten entry points, including the callers that assemble the argv themselves (`gh91_sa_rerun`, the sweeps under `scripts/`). Editing the file is legitimate: `git blame` puts it at `2649eae0` (imported GATOR upstream), and it already carries three local edits — the jar name plus `-outputFile` (`cf649214`), `--jvm-memory` (`912269e4`), and `-cgAlgorithm` (`1086ebaf`). The reactor copies only the jar (`rvsec/rvsec-android/rvsec-gator/pom.xml:82-89`, a single `<include>`), and `gator` is tracked in git.

A known incoherence is left unrepaired on purpose: the Python config reads `ANDROID_HOME`, derives `android_platforms_dir` and `android_jar`, and discards both, because the `gator` launcher recomputes its own. Emitting `--sdk` from `get_tool_command()` would be a second layer over the same defect, covering 5 entry points where the launcher covers 10, and it cannot be validated while `validate_on_init=False` (`rv-experiment/config.py:956`) is in force.

### Dead parameter

`ExecutionController._create_platform_config` (`modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py:219-228`) takes `apks: List[App]` and never reads it — the body resolves the directory itself at `:260-262`. It enters under principle P3 (dead code is deleted outright), not under damage.

### Documentation defects

`--sdkpath` appears in two live documents, and `docs/architecture/static-analysis.md:85` claims a validation that never runs on the `rv-experiment` path, because `validate_on_init=False` disables it.

## 2. Scope

Six groups. They share one surface — the experiment ↔ static-analysis seam — and are deliberately not split into six changes: two of them total four lines, and separate changes for that would be the sledgehammer-for-a-nut anti-pattern named in `docs/WORKFLOW.md:193`.

| Group | Item | Modules touched |
|---|---|---|
| A | J1 — sentinel only on the post-WTG write | Java reactor (`rvsec-gator/client`) |
| B | D2 — `mop_dir` derives from `specification_set` | rv-experiment, rv-static-analysis |
| C | P3 — the CLI consumes the boolean | rv-experiment |
| D | D1 + G1 — SDK-root fallback | `lib/gator/gator` |
| E | dead `apks` parameter | rv-experiment |
| F | documentation defects | `docs/` |

**No main spec is edited, and that is a condition of the track.** Adding the coupling to decision 7 of `openspec/specs/experiment/spec.md` would be new normative text — the trigger for FF SDD in `docs/WORKFLOW.md:184` — and Quick Path archives with `--skip-specs`, so it has no way to sync one. The two track precedents confirm the rule in practice: `openspec/changes/archive/2026-07-22-gh86-dexlib2-apk-paths-contract/` and `.../2026-05-25-gh59-fix-wide-slot-binding/` carry only `plan.md` + `tasks.md` and their commits never touched `openspec/specs/`. The coupling is recorded in `docs/architecture/static-analysis.md`, which is architecture documentation, not contract. If decision 7 must grow, that is a second change on the FF SDD track, after this one.

Adding a test for INV-ANA-31, which already exists, is not a spec edit and stays in scope.

**Escalation point.** If, while fixing D2, the decision becomes to **remove** the `jca` default at `rv-static-analysis/config.py:199-208` rather than just pass the correct `mop_dir`, that changes the behavior of every standalone caller and the change escalates to FF SDD. While the default stands as a safety net, Quick Path suffices.

## 3. File Inventory

### Group A — J1, the sentinel

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/json/JsonReportWriter.java:111` | Edit | Add an `emitSentinel` parameter to `write(...)`; emit `w.name(COMPLETE).value(true)` only when it is `true` |
| `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java:165-170` | Edit | Pre-WTG call passes `emitSentinel = skipWtg()` — `false` when WTG is still going to run (the J1 repair) and `true` when WTG is skipped by client parameter, because the client then returns right after this write and it *is* the run's end |
| `.../RvsecAnalysisClient.java:202-203` | Edit | Post-WTG call passes `emitSentinel=true` |
| `.../RvsecAnalysisClient.java:157-163` | Edit | Rewrite the comment, which currently asserts the opposite of what the code does (P4: describe current state) |
| `rvsec/rvsec-android/rvsec-gator/client/src/test/java/presto/android/gui/clients/json/SentinelEmissionTest.java` | Edit | Add a case that calls `write(..., emitSentinel=false)` directly and asserts the file has no `complete` key |

Paths are relative to the sibling reactor root `rvsec/`, not to `rv-android/`.

### Group B — D2, `mop_dir`

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-experiment/src/rv_experiment/config.py:695-719` | Edit | Extract the `specification_set → directory` dispatch (including the `custom` validation and the `ConfigurationError` default) into one method |
| `modules/rv-experiment/src/rv_experiment/config.py:949-958` | Edit | Call that method and pass the result as `mop_dir` in the `RVStaticAnalysisConfig(...)` kwargs |
| `modules/rv-experiment/tests/` (config test module) | Add | Assert the resulting `mop_dir` for all four values of `specification_set` |

`rv-static-analysis/config.py:199-208` is **not** edited: the default stays as a safety net for standalone callers (removing it is the escalation point above). `targets_file` is never set anywhere in `modules/rv-experiment/src/`, so passing `mop_dir` cannot trip the INV-ANA-33 mutex at `rv-static-analysis/config.py:297`.

### Group C — P3, the exit code

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-experiment/src/rv_experiment/__main__.py:747` | Edit | Consume the return of `execute_with_config()`; on `False`, skip the success message and exit non-zero |

### Group D — D1, the SDK root

| File | Action | Detail |
|------|--------|--------|
| `lib/gator/gator:62-64` | Edit | Fall back to `ANDROID_HOME` when `ANDROID_SDK_HOME` is absent, only when the resulting root is resolvable; keep `--sdk` as the highest-priority source |

### Group E — dead parameter (five sites)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py:219-228` | Edit | Remove `apks: List[App]` from the signature |
| `.../execution_controller.py:236` | Edit | Remove the `apks: Application objects to test` line from the docstring |
| `.../execution_controller.py:140` | Edit | Drop the argument at the only call site |
| `modules/rv-experiment/tests/experiment/test_execution_controller.py:207` | Edit | Drop `apks=mock_apks` |
| `modules/rv-experiment/tests/experiment/test_execution_controller.py:232` | Edit | Drop `apks=mock_apks` |

Check whether `List[App]` and the `App` import remain used elsewhere in the file before removing them.

### Group F — documentation

| File | Action | Detail |
|------|--------|--------|
| `docs/20260730_verificacao_consistencia_gh91.md:617` | Edit | `--sdkpath` → `--sdk` |
| `docs/20260821_relatorio_analise_estatica_defeitos.md:92` | Edit | `--sdkpath` → `--sdk` |
| `docs/architecture/static-analysis.md:85` | Edit | Drop the claim that the config "validates that the gator launcher, the analysis-client JAR, `android.jar` and the MOP/targets source exist" — with `validate_on_init=False` it does not, on the `rv-experiment` path |
| `docs/architecture/static-analysis.md` §3 | Edit | Record the `specification_set → mop_dir` coupling that group B establishes |

Deliberately **not** edited: `openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/design.md:143` and `.../tasks.md:69`, which carry the same `--sdkpath` error but are the historical record of an archived change; and `docs/20260821_verificacao_relatorio_analise_estatica.md`, which mentions the flag correctly, as the thing that does not exist.

## 4. Execution Order

No hard dependencies between the six groups; the order below is by ascending cost, so cheap wins land first and the expensive rebuild is last.

1. **C** (P3) — one line
2. **D** (D1) — three lines, no tests touched
3. **E** (dead parameter) — five sites, breaks at import/test time if wrong
4. **F** (documentation) — four edits
5. **A** (J1) — Java side; the only group that needs a reactor rebuild
6. **B** (D2) — widest reach; touches both sides of the same map

Group A is the only one requiring `mvn clean install -DskipMopAgent -DskipTests` (JDK 21 in the prefix) plus the jar re-copy into `rv-android/lib/gator`, so keep it in its own commit. Groups C, D, E and F are independent enough to run in parallel, but at four files each the subagent-dispatch threshold of `docs/WORKFLOW.md` Section 5 is not met — direct edits are faster.

## 5. Acceptance Criteria

- [x] `JsonReportWriter.write(...)` takes an `emitSentinel` flag; the post-WTG call passes `true`, and the pre-WTG call passes `skipWtg()` — `false` on the normal path, `true` when WTG is skipped by client parameter. A literal `false` there would be wrong: under `skipWtg=true` the client returns right after that write, so it is the run's last, and stripping its sentinel would make every skipped-WTG run look like a timeout to `derive_mop_artifact.py` (this is what `tests/parity/test_gh91_completeness.py` records)
- [x] A new case in `SentinelEmissionTest` exercises the writer's own sentinel decision with `emitSentinel=false` and asserts the resulting file contains no `complete` key, plus its counterpart with `true`. It calls `JsonReportWriter.writeCompletionSentinel(w, emitSentinel)` — the call `write(...)` itself makes — and not `write(...)` directly: driving `write(...)` needs a fully-initialised Soot Scene and GATOR's `XMLParser` factory, available only at the end of a real GATOR run, which is what that test file's own header already records. This is the gap none of the three existing layers reaches: `SentinelEmissionTest` today replicates the sequence in-test and injects exceptions (the J1 case has no exception); `tests/parity/test_sentinel_emission.py` runs GATOR end-to-end, where the second write overwrites the first; `modules/rv-static-analysis/tests/parser/test_sentinel.py` tests the reader, not the writer
- [x] The `rvsec-gator` client tests are executed explicitly with tests enabled (e.g. `mvn -pl rvsec/rvsec-android/rvsec-gator/client test -DskipTests=false`) and pass. `rvsec-gator/pom.xml:18` pins `<skipTests>true</skipTests>`, so a green reactor build proves nothing
- [x] The comment at `RvsecAnalysisClient.java:157-163` describes what the code now does
- [x] A test asserts the `mop_dir` produced by `get_static_analysis_config()` for all four values of `specification_set` (`jca`, `jca_android`, `generic`, `custom` with `custom_specs_dir`), and that an unsupported value still raises `ConfigurationError`
- [x] The D2 side effect is measured, not assumed: a `--specification-set generic` run on `apks_examples/cryptoapp.apk` with static analysis on shows `mopDir=.../generic` in the GATOR argv and 296 resolved signatures, against 120 before the change
- [x] A `jca` run is unchanged end to end — same `mopDir`, same 120 signatures — confirming the frozen ruler is untouched
- [x] With Phase 2 reporting failure, the CLI prints no success message and `echo $?` is non-zero; with Phase 2 succeeding, it exits 0
- [x] The orchestrator table in Section 1 is re-checked against the tree: gh104 indifferent, `restart_exited.sh` reacting only to 137, and `run_smoke.sh` now failing on a partial Phase-2 failure
- [x] `env -u ANDROID_SDK_HOME ANDROID_HOME=<sdk> python3 lib/gator/gator a --sdk ... ` and the same invocation with no `--sdk` both get past `gator:64`; a setup exporting only `ANDROID_SDK_HOME` still resolves the same root as before
- [x] `grep -rn "apks" modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py` shows no reference to the removed parameter, and `grep -rn -- "--sdkpath" docs/` finds nothing in the two live documents
- [x] `uv run pytest --import-mode=importlib -o "addopts=" tests/` is green in `modules/rv-experiment` and `modules/rv-static-analysis`
- [x] `/rv-qa-lint-fix` and `/rv-verify` clean on both touched Python modules
