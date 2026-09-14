# Proposal: gh111-cadeia-medicao

**GitHub Issue**: #111
**Track**: Full SDD
**Reference material**: `docs/20260828_cadeia_medicao_rvandroid.md` (rev. 5 — §15 is its executive summary and fixes this scope) and `docs/20260828_d9_colapso_denominador.md` (the live-reproduced mechanism of the denominator collapse). Neither is an OpenSpec artefact; both are Phase-0 material whose measurements this change treats as the verification baseline. A third document, `docs/20260829_adjudicacao_revisoes_gh111.md`, adjudicates five external reviews of this change against the primary sources; the corrections it established are folded in below.
**Predecessors that cornered the same defect without closing it**: gh91 (`sa-rerun-manifest-key`, re-analysed 30 APKs by invoking GATOR directly with a frozen key), gh98 (`manifest-package-default`, froze the manifest verbatim as the default and delegated suffix stripping to "whoever curates the corpus" without giving them a channel), gh102 (`artifact-scoped-parse`, removed the parser's second filter and measured "75 of 162 applications parse to zero classes"). Each had a legitimate cut that excluded the production path.

## Why

The chain that produces every coverage number in this project — the scope key, the static analysis, the coverage weaver, the crossing, the report — has seven defects that all surface as the same symptom: **a wrong denominator, published with nothing accusing the error**. Four of the 162 artefacts in the article corpus carry 1, 2, 6 and 21 classes where the compiled universe under the correct key holds 771, 1971, 3589 and 550 (the artefacts carry less than the compiled universe by the generated-class strip; the exact delivered counts are re-derived under D9c's segment-anchored filter — see the verification baseline); two of those four publish `cov_class = 100.00%`. Seven other APKs carry 465 corrupted class names. Seventy-five of the 162 produce an **empty artefact** on today's production path: `static_analysis.py:277` passes `code_package=self.app.code_package`, which since gh98 (`553ae54a`, 05/08) is the declared applicationId, and `RvsecAnalysisClient.isAppClass` on a suffixed key matches no compiled class. (This is not the defect gh102 measured with the same population and the same number — that was the parser's second filter, removed and archived on 16/08. Same 75 APKs, one stage earlier, still live. The stored artefacts are non-empty because they were produced when `App.code_package` ran `PackageDetector` unconditionally, before gh98 — a pipeline configuration that no longer exists.)

The article was not published and the campaign will be re-run. This change is therefore not errata — it is **the gate that must be closed before the new campaign runs**, and today's numbers are the baseline each repair must move in a predicted direction.

Two properties make the defects hard to see and are the reason they survived three prior changes. First, **the aggregate hides the redistribution**: swapping the scope key on 30 of 219 APKs changed 26 per-APK medians by factors from ×7.0 to ÷5.6 and moved the global median from 17.63 to 17.92. Second, **every failure is silent**: the crossing discards unmatched calls at `logger.debug` with no counter, the parser's `ParserDiagnostics` is never serialized, `LoggingManager.setup_file_logging` has no production caller, and the effective scope key never reaches disk in any form.

Relates to FR21 (coverage measurement of monitored operations), FR24 (static analysis of reachability), NFR03 (measurement reproducibility), NFR06 (traceability of experiment artefacts).

## The measurement chain, end to end

This section exists because the seven items are not seven independent bugs — they are seven points on one pipeline, and three of them are only intelligible against the identifier forms the pipeline carries. Each link below names **what identifier shape crosses it**, **whether the signature is complete or reduced to class+name**, and **where a format conversion happens**.

### Link 0 — The `.mop` specification declares the targets

A JavaMOP event declares an AspectJ pointcut, e.g. `call(* Cipher.doFinal(..))` or `call(SecretKeySpec.new(byte[], String))`. `UsedJcaMethodsVisitor` (rvsec-mop-extractor) walks the AST and resolves the **simple owner name** written in the pointcut to a fully-qualified name through three ordered routes:

1. explicit `import` in the spec;
2. wildcard-import packages, probed with `Class.forName(fqn, false, …)`;
3. the implicit `java.lang` package.

Route 3 is recorded (`ownerFromImplicitSeed`), because a target reaching its owner that way is emitted STRICT downstream — resolving `String#valueOf` leniently would match every overload. An owner that none of the three routes resolves is now reported (`skippedOwners`) instead of falling through silently.

Two AspectJ operators survive the boundary as flags rather than being flattened: a trailing `+` on the owner becomes `includeSubtypes`; a trailing `*` on the member name becomes `nameIsPattern`. The pointcut member name `new` is rewritten to Soot's `<init>`.

| what crosses | form |
|---|---|
| `MopMethod.className` | **dotted JDK FQN** — `javax.crypto.Cipher` |
| `MopMethod.name` | bare method name, or `<init>` |
| `MopMethod.parameters` | `List<String>` of declared type names, dotted, arrays as `byte[]` |
| `MopMethod.signature` | the **pointcut text** (`MethodPattern.toString()`) — **never used for matching**; it is a record, not a key |

**Classpath caveat, load-bearing**: route 2 and route 3 answer from the *extractor's own JVM*, not from the `android.jar` the analysis will run against. `java.lang.String` resolves against the host JDK. An owner that exists only in an Android package cannot be resolved here at all, and is reported as "skipped" when the true cause is "not on this classpath".

### Link 1 — Targets become Soot methods inside GATOR

`MopSpecsTargetSource.load()` converts each `MopMethod` into a `TargetMethod` carrying a `MatchPolicy`:

- **LENIENT** — matches on `(owner, methodName)` only. **Parameters are ignored entirely.** This is the historical MOP→Soot contract (INV-ANA-35) and covers almost every target.
- **STRICT** — matches on owner, name **and the full parameter type list**.

`TargetResolver.resolveInScene` iterates `Scene.getClasses() × methods × targets`. `TargetMatching.matches` tests the **name first** (string compare, or prefix when `nameIsPattern`) and only then the owner — exact FQN equality when `includeSubtypes` is off, `FastHierarchy.canStoreType` against the declared super-type when it is on. STRICT then adds `paramsMatch`, comparing `method.getParameterType(i).toString()` — Soot's dotted type name — against the declared string.

**This is the first granularity asymmetry in the chain, and it is deliberate but undocumented**: a target is *seeded by name without parameters*, while coverage downstream is *matched by complete signature*. `reachesTarget` therefore answers a coarser question than `called` does.

### Link 2 — Soot loads the APK

GATOR runs Soot in APK mode with `-process-dir <apk>`. Soot marks **every class it reads from the DEX files as an application class** — in `br.com.colman.petals` that is 36,800 of 38,932 across 18 DEX files. There is no multidex option to set: `soot.dexpler.DexFileProvider.acceptFile` is `{ return true; }` in Soot 4.7.1, and `set_process_multiple_dex` does not exist.

| what crosses | form |
|---|---|
| `SootClass.getName()` | **JVM binary name** — package segments separated by `.`, nested classes by `$` |
| `SootMethod.getSignature()` | **complete Soot signature** — `<com.example.Foo: java.lang.String bar(int,java.lang.String)>` |

### Link 3 — The app/library classification (item D9)

`AnalysisEntrypoint.java:111-126` is the only thing that shrinks the application set. Three clauses, in order:

1. **`:112` rescue** — a class named in an `<activity>` of the manifest is application, unconditionally. Only `<activity>` is read (`:96`); services, receivers and providers are not rescued.
2. **`:119` guard** — `c.getName().startsWith(appPkg)`, where `appPkg` is the manifest `package` attribute read verbatim at `:87-94`. There is no alternative source; `Configs.clientParams` is not consulted here. The match has **no dot boundary**.
3. **`:121` demotion** — what the guard did not protect is offered to `Configs.isLibraryClass`, backed by `libPackages.txt` (2,170 patterns, all ending in `.*`; the match *does* carry a dot boundary because the trailing `.` is kept).

The corpus is built with `assembleDebug`, and Gradle's `applicationIdSuffix` appends a segment to the applicationId without touching the class namespace. So `appPkg = br.com.colman.petals.debug`, no compiled class starts with it, the guard is dead, and the pattern `br.com.*` demotes 33,089 classes. One class survives under the app prefix: the `MainActivity`, returned by the rescue. `#AppClasses` drops to 3,711 — byte-for-byte the campaign log.

**The collapse requires both conditions** — a dead guard *and* a code package matching a `libPackages.txt` pattern. Over the 162 artefacts the conjunction selects exactly the four collapsed ones, with no false positive or negative. The control `app.pachli` carries the same build-type suffix (equally dead guard) and is invariant, because `app.pachli` matches no pattern.

### Link 4 — The client filters what survived

`RvsecAnalysisClient.java:86-90` resolves a **second scope key**: `filterPackage = codePackage ?: manifestPackage`, where `codePackage` arrives as `-clientParam codePackage=<X>`. `extractClasses` then keeps `Scene.v().getApplicationClasses()` entries passing `isAppClass` — `startsWith(filterPackage)`, again **without a dot boundary**, minus the generated `.R`, `.R$*` and `.BuildConfig`.

**The run therefore has two scope keys, and the first is always the manifest.** This is why passing `codePackage=` on the command line — the workaround the gh91 rerun used — repairs the client's filter and cannot reach the guard that already emptied the Scene.

### Link 5 — The artefact on disk

`JsonReportWriter.java:84` writes `"package"` = `output.getAppPackageName()` — **the manifest**, not the key that filtered the contents. `ReachabilityEnricher.topLevelMetadata()` would return `{manifestPackage, codePackage, mainActivity}` and has no production caller. Measured over the 162 artefacts: **zero classes start with the recorded `package`, and 162/162 start with the neutralized key**. The effective key reaches disk nowhere.

| field | form |
|---|---|
| `reachability[].className` | JVM binary name, `$` for genuine nesting |
| `reachability[].methods[].signature` | complete Soot signature, parameters as dotted FQNs |
| `reachability[].methods[].{reachable,reachesTarget,directlyReachesTarget}` | booleans from the reachability engine |

### Link 6 — The Python parser

`static_analysis_parser.py:371` passes every `className` through `SignatureNormalizer.normalize_class_name`; `:455` does the same for every window name. The heuristic converts `.` to `$` whenever both sides of the dot start with an uppercase letter (`signature_normalizer.py:246-312`).

`:390` stores `signature=signature` **verbatim**. The normalizer therefore touches the class name and **not** the signature, producing a record that is internally inconsistent whenever it fires: `class_name = …ZoomView$ZoomView` alongside `signature = <…ZoomView.ZoomView: …>`.

Since GATOR already emits the binary name, every dot between two capitalized segments in its output is a **package boundary**, and the heuristic is always wrong there. Measured: 465 classes across 7 of the 162 corpus artefacts; 413 classes across 9 of 195 in the ajc-era archive, with a clean dose-response (100% of classes corrupted → 0.00% coverage; 5.6% → coverage present but understated).

### Link 7 — The coverage repository

`repository_initializer.py:52-72` builds `ClassCoverageData` keyed by the **normalized** class name and `MethodCoverageData` keyed by `method.signature` — the **verbatim** Soot signature.

### Link 8 — The weaver emits the numerator

**dexlib2** (`SignatureFormatter.java`) reads the **DEX type descriptor** and converts it: strip leading `[` counting array depth, map the single-letter primitives (`I` → `int`, `[Ljava/lang/String;` → `java.lang.String[]`), and for reference types take `L…;` and replace `/` with `.`. It then assembles `<FQN: retType name(p1,p2)>` — the same shape as Soot's signature, deliberately so.

**ajc** (`Coverage.aj:64`) uses `method.getDeclaringClass().getName()`, the **JVM binary name**, plus `MethodSignature.toLongString()` for the parameters.

Both weavers emit `.` for package boundaries and `$` only for genuine nesting. **They agree with GATOR byte for byte, and no normalization is needed on either side.** The historical diagnosis in `docs/NOVO/06_normalizacao_inner_classes.md` (a document external to this repository's tree, cited here as provenance only), which attributes the spurious `$` to AspectJ, is inverted: `Class.getName()` never inserts `$` at a package boundary, and the `$` came from the normalizer on the static side.

Scope on this side is **not** the app key: both dexlib2 weavers use a library deny-list (`PackageFilter.java:20-61`), which is why `com.google.android.stardroid` measures 0% with a correct 705-class denominator.

### Link 9 — The logcat

| tag | payload | parsed by |
|---|---|---|
| `RVSEC-COV` | the complete signature `<class: ret name(params)>` | `logcat_parser._parse_coverage_message` — regex `<([^:]+):\s+([^ ]+)\s+([^:(]+)\(([^)]*)\)>`; the whole raw message becomes `RvCoverageLog.signature` |
| `RVSEC` | `class.method(File.java:NN) ::: SPEC went into an error state.` | `ErrorDescription.createErrorSummary` — splits class from method at the **last dot** of the frame prefix |

A legacy triple-colon coverage format (`class:::method:::params`) is still parsed, because an APK is instrumented once and replayed across runs.

### Link 10 — The crossing

`domain/coverage.py:640-674` performs two literal-equality lookups:

1. `get_class(coverage_log.clazz)` — the raw binary name from the logcat against the **normalized** name in the repository;
2. `signature in class_data.methods` — the raw logcat message against the **verbatim** Soot signature.

Both discards are `logger.debug` with **no counter** (`:660`, `:672`). The normalizer breaks step 1 for capitalized-package apps; when it happens to leave the class name alone, step 2 still holds, which is why the corruption is a subtractive bias rather than a total zero in most APKs.

`_percentage` (`:446-449`) returns `0.0` for `0/0`, so an empty denominator is indistinguishable from an app that covered nothing — and a *degenerate* denominator (1 class of 771, both covered) publishes `100.00%`.

### Link 11 — The report

`result_processor.py` writes `summary.csv` with `cov_class`, `cov_method`, `mop_errors_total` and kin. The denominators themselves are not published, and no provenance column records which scope key, specification set or instrumentation variant produced the row.

### What the map makes visible

- **The identifier form is stable everywhere except one point.** Every producer in the chain emits the JVM binary name and the complete Soot signature. The single transformation is `SignatureNormalizer`, applied to one side of an equality test — which is why removing it is a repair and not a trade-off.
- **The DEX descriptor never escapes the weaver.** `SignatureFormatter.toFqn` converts it at the emission point, so nothing downstream needs to know about `L…;` forms.
- **Two granularities coexist and neither is documented**: targets seeded by class+name without parameters (LENIENT), coverage matched by complete signature.
- **The scope key is answered twice per run**, by two different mechanisms, and the artefact records neither.

## What Changes

Seven items, in the order the researcher decided (D9 → D1 → D2 → D3 → D4 → D10' → D9b). Three change measurement; the ordering exists so each delta is attributable.

- **D9 — the GATOR guard reads the code key.** `AnalysisEntrypoint.java:119` consults `Configs.getClientParamCode("codePackage=")`, falling back to the manifest when the parameter is absent. One site, few lines, in `rvsec-gator` — with one trap that compiles clean: `getClientParamCode` returns the **whole** parameter string, `"codePackage=com.foo"`, not its value (`Configs.java:292-302`; `RvsecAnalysisClient.getCodePackage():244-250` already carries the manual strip every caller repeats). Forgetting the strip makes the guard test `startsWith("codePackage=…")`, which no class name satisfies, so the guard never fires and D9 becomes invisible with no error and no log; an absent parameter returns `null` and would NPE inside `startsWith`; an empty value returns `""` and `startsWith("")` promotes every library class in the Scene. The resolution is therefore extracted as `static String resolveScopeKey(String clientParam, String manifestPackage)` and unit-tested on those four cases — `AnalysisEntrypoint` has no JUnit coverage at all today. `Configs.clientParams` is already populated when `AnalysisEntrypoint.run()` executes (parsing happens in `Main.main` before `setupAndInvokeSoot()`), so no new module dependency appears. This aligns the run's two scope keys: the guard protects exactly the set the client will filter. **BREAKING for measurement** in 4 of the 162 corpus artefacts.
- **D1 — the crossing and the denominator get accounting.** `unmatched_*` counters in `ParserDiagnostics` (which lives in `rv-android-core`, `domain/coverage.py:453`, not in `rv-coverage`), **split into out-of-scope × in-scope** — the separation that distinguishes "the app did not use it" from "the analysis did not see it" — plus a denominator plausibility gate that **fails loud** and refuses the empty, the **degenerate** and the zero-universe case. The gate reads `class_defs_under_key` **from the artefact**, recorded there at write time next to the effective key: the parser's entry points see a path and a filename, never an APK, and INV-ANA-61 forbids handing them a package key — recording the count at the producer is what makes the gate a pure artefact predicate, valid on resume and `--process-results` as well as on a fresh run. The ratio is taken after subtracting `<key>.R`, `<key>.R$*` and `<key>.BuildConfig` from the compiled side, because the client already strips them from the parsed side; the threshold is **0.15** on that corrected ratio. A non-vacuity gate alone would have caught none of the four collapsed APKs: 1 class of 771 is not empty. No measurement change; this is what makes D2 and D3 verifiable.
- **D2 — a global run flag neutralizes the build-type suffix.** The manifest verbatim stays the rule (INV-CORE-18 unchanged in its default). The flag applies the denylist already normative in the article's `mneut_scope.py`: `{debug, dev, beta, staging, qa, nightly, alpha, snapshot, current, head, indev}`, `MIN_SEGMENTS = 2`, applied **repeatedly** (this is what handles `.qa.debug` and `.debug.HEAD`) and **in lowercase** (this is what handles `.BETA`). The policy is a run scalar propagated like `package_detector` under INV-EXP-34 — **no per-APK channel, no curated map**. The effective key is recorded on disk. **BREAKING for measurement.**
- **D2 does not apply to the ajc instrumenter.** Feeding the neutralized key to the 8 `App(` sites would activate the anti-quarantine guard at `ajc_instrumentation.py:854-885`, today inert precisely in the suffixed apps — a change in the instrumentation path, not the analysis path. The divergence is **recorded, not repaired**: the pipeline will deliberately hold two answers for `code_package` depending on the consumer, and the comment at `ajc_instrumentation.py:858-866` already anticipates the tension.
- **D3 — the normalizer is removed.** Both calls (`static_analysis_parser.py:371` and `:455`) go, and they go **together**: removing only the first leaves the activity denominator normalized while classes are not, breaking the window↔class match of INV-ANA-60. `SignatureNormalizer` then has zero consumers in all of `modules/*/src`, so under P3 the class, its test module and INV-ANA-02 are deleted rather than left dormant. Five tests break, one structurally: `test_dot_notation_normalized` plus the four of `TestNormalizerSafetyNet`, of which `test_normalizer_is_noop_on_correct_json` monkeypatches the method (task 4.5). **BREAKING for measurement** — in the direction already measured. Automatable witness: `com.hwloc.lstopo_80283`, the only affected case that exists in dexlib2, in the live corpus, with 99 executions.
- **D4 — what is already counted gets serialized.** `ParserDiagnostics.to_dict()` and `TaskResult.write_errors` reach `to_dict()`; `LoggingManager.setup_file_logging` gains a production caller. The last is not "re-wiring what exists": `setup_file_logging` has a caller (`manager.py:147`) guarded by `if self.log_path:`, and `log_path` is assigned only *inside* `setup_file_logging` — a closed cycle whose only caller, `configure_output`, itself has no production caller. Adding a key to `TaskResult.to_dict()` touches the `tasks.json` format the resume protocol reads, so `from_dict` is verified alongside.
- **D10' — three pre-processing side effects.** `--skip-instrument` silently kills static analysis (`_get_target_apks_for_analysis` lists `instrumented_apks/`, which does not exist, yielding `[]` and a warning that does not name the cause); INV-EXP-16 does not hold (the cosmetic fallback at `pre_processor.py:484-492` emits a factually false message, and APKs without `.apk.json` are logged as excluded and then executed anyway); `--skip-monitors` lets a leftover `out/monitors` from a **different specification set** be consumed with no check and no log.
- **INV-EXP-16 is resolved by executing, not by excluding** (researcher decision, 29/08). The filtered list `get_instrumented_apks()` returns decides nothing today — `execution_controller.setup` consumes its `apks` parameter on one line, the log context at `:130`, while the executed set comes from the directory glob at `:258-260`. The function stops filtering and reports instead: an APK with no `.apk.json` runs, its violation columns are written because violations do not depend on static analysis, and its coverage cells are **empty rather than `0.00`**. Excluding it would contradict Q8, repeat the exclusion anti-pattern that already cost this corpus 55 applications, and make irreversible in the pipeline a choice that the published denominator (INV-PLT-33) now lets a reader make.
- **D9c — generated resource classes leave the denominator at every segment.** `RvsecAnalysisClient.isAppClass` anchors its `.R` / `.R$*` / `.BuildConfig` test at the scope key's root, so `app.pachli.R` goes and `app.pachli.core.database.R` stays, and a key that is an *ancestor* of the resource namespace escapes the test entirely. Measured over the 162 artefacts: **505** such classes sit in today's denominators — 117 in `app.pachli_50` alone — carrying 547 methods of which **zero** are non-trivial. They are constant tables with nothing to cover, and their only effect is to depress `cov_class`. The test moves to the class name's last segment. This entered scope because the change was otherwise about to ratify the leak: task 1.8's asserted `550` for `screenshottile` was justified *by* it. The rule stops at resource classes — annotation-processor output (5,816 classes, 36,264 non-trivial methods that execute) stays in the denominator, recorded as an open question rather than acted on. **BREAKING for measurement.**
- **D9b — documentation that contradicts the code.** `rv-static-analysis/CLAUDE.md:27-28` and the `process()` header at `pre_processor.py:83-90`, which claims static analysis runs "on original APKs (NOT instrumented)" and is last "by convention" with no dependency on step 2 — the opposite of what the code does.

### Two corrections this proposal folds in against the reference material

1. **D9 and D2 are conjunctive under the default policy — which is how every recorded run has executed.** `App.code_package` returns the manifest verbatim when both package policies are off (`app.py:146-147`), which is the default, so under that policy a guard reading `codePackage` reads today's value and changes nothing. The four collapsed artefacts come from the gh91 rerun, which handed the code key to the client without reaching the guard.

   The earlier wording of this correction said D9 is *not observable in isolation through the pipeline*, and that is false. `--package-detector` / `RV_PACKAGE_DETECTOR` is a live, documented and **spec-mandated** run policy (INV-EXP-34, `openspec/specs/experiment/spec.md:213`), resolved at both entry points and threaded to `App(package_detector=…)`; it supplies `codePackage != manifest` today. Measured: the detector elects `com.github.cvzi` for `com.github.cvzi.screenshottile_148`, and under that key the class count moves 21 → 550 with no D2 anywhere. What makes the practical risk small is a different fact — no recorded run has ever enabled the policy (`grep '"package_detector": true'` over `experiment_config.json` finds none).

   Consequence for verification, and it is the reverse of what the earlier wording implied: **D9 has an end-to-end witness available today**, and that witness is its acceptance (task 1.8). `D9Probe.java` stays as the fast prediction — it imports nothing from `presto.android`, reimplements the demotion predicate and prints both guards without mutating the Scene, so editing `AnalysisEntrypoint.java:119` changes its output by exactly zero. A probe that cannot fail is not an acceptance test. The ordering D9 → D2 stands; only its justification narrows to the default policy.
2. **The historical normalizer diagnosis is inverted** (see Link 8). This matters beyond bookkeeping: it is the reason D3 is a removal rather than a symmetric-normalization design decision.

## Capabilities

### New Capabilities

None. Every change modifies an existing capability.

### Modified Capabilities

- `analysis`: the GATOR demotion guard resolves scope from the code key; the analysis artefact records the key that produced it, that key's origin (on a client parameter of its own — nothing carries it today) and the **net** count of compiled classes under it; generated resource classes leave the denominator at every package segment, not only at the key's root; the parser stops transforming class and window names; parse diagnostics gain in-scope/out-of-scope discard counters and are serialized; a denominator gate refuses empty and degenerate results.
- `core`: `App` gains the build-type-suffix neutralization policy as a run-scalar input; the coverage crossing (`LogcatRepository.register_method_call`) counts what it discards; `TaskResult` serializes write errors **and the run persists them after result processing**, without which the serialization is inert; file logging acquires a production entry point; `SignatureNormalizer` is removed.
- `experiment`: the suffix policy is resolved at the entry point and propagated to every `App(` construction except the ajc instrumenter; `--skip-instrument`, `--skip-static` and `--skip-monitors` stop failing silently.
- `platform`: the discard and denominator counters reach `summary.csv`, together with a `measured` boolean; a task with no denominator writes empty coverage cells across all six percentage columns rather than `0.00`. This is the report half of D1 and D4 — the accounting those items create is worthless if it never reaches the published artefacts, which is what INV-PLT-33…36 and Group 8's column tasks deliver. (`tasks.json`'s `coverage_metrics` deliberately keeps `0.0` — researcher decision, 30/08: the field is read as a number by the resume protocol and by aperv-tool; the distinction is carried by the CSVs' empty cells and `measured`.)

## Impact

**Modules** — `rv-static-analysis` (parser, GATOR invocation, denominator gate, artefact cache, module CLAUDE.md), `rv-android-core` (`domain/app.py`, `domain/coverage.py` — which is where **both** `LogcatRepository` and `ParserDiagnostics` live —, `domain/task.py`, `util/logging/manager.py`, deletion of `util/android/signature_normalizer.py`), `rv-experiment` (`experiment/workflow/pre_processor.py`, `config.py`, `__main__.py`), `rv-platform` (`result_processor.py`, `platform.py` for the post-processing save), `rv-coverage` (task 2.2 threads the scope key through three of its files, and the INV-ANA-62 identity tests live in its suite — task 2.11 runs it), `aperv-tool` (the primary consumer of both campaign artefacts: `analysis/loader.py` gains the `measured` column, `analysis/tasks_record.py` excludes `write_errors` from retry identity — tasks 8.3 and 5.7), `rv-instrumentation-ajc` (record only, no behaviour change).

**Outside `modules/`** — `scripts/gh91_gate.py` imports and executes `SignatureNormalizer` (`:53`, `:65`, `:80`, `:94`) and dies at import once D3 lands, diagnosing a venv problem that does not exist; the grep gate of task 4.7 covers `modules/*/src` **and** `scripts/` and disposes of it (after 4.11 captures its output). `scripts/regenerate_results/regenerate_container.py:78-91` hard-codes a `SUMMARY_HEADER` copied from `result_processor.py` and would silently write a narrower CSV — with `0.00` where rv-platform writes empty — than the one rv-platform writes (task 8.6). The consumers whose meaning changes under empty cells are `scripts/aperv_objective.py` and `scripts/analyze_calibration.py` (both feed `scipy.stats.trim_mean`, which does not skip `NaN`), `scripts/verify_phase.py` (informational means only — it has no coverage gate), and `modules/aperv-tool` (`analysis/loader.py`'s fixed `_PAYLOAD_COLUMNS`, `analysis/tasks_record.py`'s `_payload` retry-identity — tasks 8.3 and 5.7); three more scripts read summary-schema CSVs with `csv.DictReader` + `float()`, where an empty cell raises instead of skipping (named in task 8.3).

**Cross-language** — this change edits the sibling Java reactor in **two** modules: `rvsec-gator/sootandroid/.../AnalysisEntrypoint.java` (the guard) and `rvsec-gator/client/.../json/JsonReportWriter.java` plus `ReachabilityEnricher.java` (the recorded key and `class_defs_under_key`). Both edits belong to **one** reactor build, which is why the artefact half of the old task 3.7 moves into Group 1: the copy into `rv-android/lib/gator/` is bound to the `install` phase, so a later `mvn package` would not refresh it and every artefact produced after a second, unbuilt edit would come from a stale jar. The reactor is not part of the `rv-android` uv workspace; it is rebuilt with `mvn clean install -DskipMopAgent` under JDK 21 — **without** `-DskipTests`, per task 1.5: no gator pom sets `skipTests`, so that flag was the only thing suppressing the reactor's unit suites — and delivers `rvsec-gator.jar` into `rv-android/lib/gator/` through the `main.basedir` mechanism. Verification of the Java side runs against that jar, not against the sources.

**Not in this change, with a named destination** — D9a (`new`→`<init>` and the unresolved-owner log-and-skip) closes in **#69**, already written in the working tree and needing verification and a commit, not re-implementation; the spec-side repairs R1–R6 and D-1…D-9 close in **#109** group G8; the dexlib2 `TypeResolver` nested-type defect and the `after()` divergence take their own module change; the negated environment variables have `gh-tbd-env-vars-architecture`.

**Recorded debt, deliberately unowned** — pruning `libPackages.txt` (2,170 patterns inherited verbatim from the GATOR fork at commit `d94e33cc` and never edited, containing app-author namespaces `br.com.*`, `com.github.*`, `io.github.*`, `com.nononsenseapps.*`, `me.zhanghai.*`, `info.metadude.*`, `uk.org.*` and 127 single-segment patterns such as `c.*`, `domain.*`, `flow.*`). **After D9 lands this list can no longer touch the *class* denominator** — everything under the app prefix leaves the loop at the guard — but it keeps governing what the GUI/WTG analysis treats as library (`Hierarchy.java:305` → `FlowgraphRebuilder.java:72`), and therefore the `reachable`, `reachesTarget` and `directlyReachesTarget` predicates — which are the denominators of `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target`, three of the six published coverage columns. Calling this "not a denominator risk" would be a false dichotomy: it stops being a risk to the *class* denominator and stays one to three others. Pruning it changes measurement for every app. Likewise unowned: the three inert `-exclude` options at `Main.java:225-227` (`Scene.isExcluded` accepts a `.*` or `$*` suffix, or exact equality — `"kotlin."` satisfies none); the dot boundary of `isAppClass` (decision D-C, deferred); the unsatisfiable `CoverageValidator` gate and its `<init>`-truncating regex; the frame-split fallback in `ErrorDescription`; provenance columns in the CSVs; and the resume checksum that can never diverge (`platform.py:171` installs fresh metadata before the comparison at `:293` — current against current, always equal).

**Explicitly withdrawn by researcher decision (28/08)** — D5 (provenance in columns and checksum; verification additionally showed it would be inert, since the resume path forces all three pre-processing flags to `False`), D6 (logcat cross-task contamination — verified non-existent, four independent mechanisms prevent it), Q8 (filtering violations against the static analysis — two legitimate scenarios forbid it).

**Verification baseline** — the four denominators move from 1 / 2 / 6 / 21 to the full universe under their key: the probe predicts the **raw** counts 771 / 1971 / 3589 / 550, and the delivered counts are those minus the generated classes **under D9c's segment-anchored filter**, recorded by task 1.7 and asserted by 8.10. The earlier figures 762 / 1952 / 3578 / 550 are superseded — they subtracted only the root-anchored generated classes, and the 550 in particular *included* the leaked `com.github.cvzi.screenshottile.R*` that the ancestor key let through, with an invariance control drawn from the six live-guard APKs of `docs/20260828_d9_colapso_denominador.md:133-135` (`app.pachli` is a null control: no `libPackages.txt` pattern matches it) — D9, predicted by the probe and **accepted by an end-to-end run**; 75/162 APKs whose artefact is empty on today's production path — the client filter, not the parser's, which gh102 already removed (D2, baseline named in task 3.15); 465 corrupted classes across 7 APKs, `com.hwloc.lstopo_80283` as the automatable witness (D3).

**Test baseline** — measured 29/08 with the CI invocation (`-m "not (slow or online or sglang or performance or dataset)" --import-mode=importlib -o "addopts="`), the suite had **five pre-existing failures**: two in `rv-static-analysis` (`test_directly_reaches_target_exact`, `test_reaches_target_within_tolerance` — the `BASELINE` dict and `baselines/MANIFEST.json` were never updated when `2a0f5280` regenerated the `cryptoapp` fixture) and three in `tests/parity/` (`test_baseline_not_older_than_jar`, `test_no_legacy_mop::test_repo_is_clean`, `test_sentinel_emission::test_real_gator_json_parses_with_complete_true`). **All five were repaired on 29/08**, before this change starts: `tests/parity/` is 204 passed and all 16 modules are green. That is the line against which task 8.12 reads, so a failure appearing during implementation is attributable to this change rather than inherited. (Re-measured 30/08: all 16 modules green, `tests/parity/` 204 passed, both gates clean — the line still holds.)

One of the five is a standing hazard for this change and not merely history: `test_baseline_not_older_than_jar` compares `mtime(baseline) >= mtime(jar)`, and task 1.5 rebuilds the jar. Group 1 therefore regenerates the baseline after the rebuild, or the tripwire fires again by construction.
