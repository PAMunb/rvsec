<!-- Subagent dispatch hints:
     - This change touches ~41 files / 266+ occurrences across Java (rvsec-gator: 1 src + 6 tests) + Python (rv-static-analysis, rv-android-core, rv-coverage, rv-platform, rv-screen-parser, scripts; aperv-tool has 0 current occurrences). Empirical grep 2026-05-25. modules/rv-agent/ is EXCLUDED per CLAUDE.md (deprecated).
     - Group 0 (Phase 1 task-zero — corruption-vs-truncation investigation) MUST complete first; it decides whether Group 8 (C1h atomic write) exists.
     - Group 1 (Java target abstraction — C1a) MUST complete first on the Java side.
     - Group 2 (CLI mutex + targets-file — C1b) depends on Group 1.
     - Group 3 (Java decomposition + characterization fixture — C1c) depends on Group 1.
     - Group 4 (ReachabilityEnricher + ReportModel — C1d) depends on Group 3.
     - Group 5 (Writer walker + sentinel + JsonSchema.Keys — C1e) depends on Group 4. Python parser via _JK is part of this group.
     - Group 6 (Rename MOP→Target atomic — C1f) depends on Groups 1-5 (constants in place; classes renamed; writer/parser via constants). MUST be atomic per-module commits.
     - Group 7 (JimpleDefUtils — C1g) is independent; can run in parallel to Groups 3-5.
     - Group 8 (C1h atomic write) — **DROPPED 2026-05-25** per Group 0 verdict (zero corruption in gh57 sweep; 826/826 JSONs parse cleanly).
     - Group 9 (Integration + sweep + verification) runs after Groups 1-7.
     - Critical path: 0 -> 1 -> 3 -> 4 -> 5 -> 6 -> 9.
     - Subagent parallelism candidates: Group 7 in parallel with Group 3-5; Group 6 consumer-side renames (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) can be dispatched in parallel per consumer module after C1f atomic commits land.
-->

## 0. Phase 1 task-zero — corruption-vs-truncation investigation (decides if Group 8 exists)

- [x] 0.1 Identified the gh57 sweep (`out/sweep_jca400_v1/`, 826 APK JSONs). RELATORIO had no parser-failure section; classification ran over the full sweep instead of a 2-3 APK sample — stronger empirical basis than originally scoped.
- [x] 0.2 Classification (Python script via `json.loads` + `_recover_truncated_json` mimic on each of 826 JSONs): **0 corruption-unrecoverable, 0 truncation-recoverable, 826 parse cleanly**. Of the 826 valid JSONs, 651 (78.8%) have empty `windows[]` + `transitions[]` — gh51-D5 *write-first-JSON* intercepts WTG-phase timeouts so the file is written complete-but-empty (not truncated, not corrupt). Recorded in `design.md` D9 verdict block.
- [x] 0.3 Verdict: **C1h DROPPED**. Zero corruption observed → atomic write defends against zero failures. Sentinel ADR-6 remains the right defense for the complete-but-empty third category (lets consumers distinguish timeout-during-WTG from writer-crash). Group 8 removed from this `tasks.md`.
- [x] 0.4 `design.md` D9 updated with empirical verdict; this `tasks.md` Group 8 deleted; commit `chore(gh60): Phase 1 task-zero verdict — C1h out`.

## 1. C1a — Target abstraction (Java foundation)

- [ ] 1.1 Create package `presto.android.gui.clients.target` in `rvsec-gator/commons/src/main/java/`
- [ ] 1.2 Add `TargetMethod.java` POJO with fields `className`, `methodName`, `params: List<String>`, `signature`, `policy: MatchPolicy` and nested enum `MatchPolicy { LENIENT, STRICT }` (immutable, `final` fields, no setters)
- [ ] 1.3 Add `TargetMethodSource.java` interface with single method `Set<TargetMethod> load()`
- [ ] 1.4 Add `MopSpecsTargetSource.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/target/`: wraps `JavamopFacade.listUsedMethods(mopDir, false)`, converts each `MopMethod` to `TargetMethod` with `MatchPolicy.LENIENT`
- [ ] 1.5 Refactor `RvsecAnalysisClient.loadMopSignatures()` to call `new MopSpecsTargetSource(mopDir).load()` and convert downstream; keep the old method name temporarily (will be renamed in Group 6)
- [ ] 1.6 Add `MopSpecsParityTest.java`: assert `MopSpecsTargetSource.load()` produces the same `Set<(className, methodName)>` as the historical `loadMopSignatures()` on `cryptoapp.mop` (16 entries — INV-ANA-35)
- [ ] 1.7 Add `TargetMethodTest.java`: equality, hashCode, immutability
- [ ] 1.8 Run GATOR Maven build and unit tests; verify no regression
- [ ] 1.9 Run `gator a -p cryptoapp.apk --client-jar lib/gator/rvsec-analysis-client.jar -client RvsecAnalysisClient -clientParam mopDir=<jca> --out /tmp/c1a.json -cgAlgorithm spark`; verify `set(reachesMop)` matches baseline `b2e04a26`
- [ ] 1.10 Commit `feat(gh60): C1a TargetMethod + TargetMethodSource + MopSpecsTargetSource (closes step in #60)`

## 2. C1b — `--targets-file` CLI + mutex with `--mop-dir`

- [ ] 2.1 Add `SignatureFileTargetSource.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/target/`: parses text file line-by-line, tolerates blank lines and `#` comments, raises `IllegalArgumentException` with line number for malformed signatures; per-entry wildcard (`(..)`, `(*)`) yields `MatchPolicy.LENIENT` for that entry
- [ ] 2.2 Add `SignatureFileTargetSourceTest.java` covering: comments, blanks, valid STRICT entries, valid LENIENT (wildcard) entries, malformed line raises `IllegalArgumentException` with correct line number (INV-ANA-34)
- [ ] 2.3 Extend `RvsecAnalysisClient.run()` to dispatch on CLI param: `targetsFile=<path>` → instantiate `SignatureFileTargetSource`, otherwise fall back to `MopSpecsTargetSource(mopDir)`
- [ ] 2.4 Update `rv_static_analysis/__main__.py`: add `argparse.add_mutually_exclusive_group(required=True)` with `--mop-dir` and `--targets-file` (INV-ANA-33); also add `--cg-algorithm` with `choices=["spark","cha","rta","vta"]` and `default="spark"` (D8)
- [ ] 2.5 Update `rv_static_analysis/config.py`: extend `RVStaticAnalysisConfig` to carry `target_source: tuple[str, Path]` (e.g., `("mop_dir", Path("/m"))` or `("targets_file", Path("/t"))`) and `cg_algorithm: Literal["spark","cha","rta","vta"]`; inject correct `-clientParam` and `-cgAlgorithm <value>` into the GATOR command
- [ ] 2.6 Add `tests/cli/test_mutex.py`: cases for (a) only `--mop-dir`, (b) only `--targets-file`, (c) both → error exit code 2, (d) neither → error exit code 2 (INV-ANA-33)
- [ ] 2.7 Add `tests/analysis/test_targets_file_cli.py`: end-to-end with a tiny synthetic targets file (one Soot signature), verify GATOR receives `-clientParam targetsFile=<path>`
- [ ] 2.8 Add `tests/cli/test_no_match_mode_flag.py`: assert `parser._actions` contains no option string in `{"--match-mode","--matching","--lenient","--strict"}` (INV-ANA-36)
- [ ] 2.9 Add `tests/cli/test_cg_algorithm.py`: cases for (a) default → `-cgAlgorithm spark`, (b) explicit `--cg-algorithm cha` → `-cgAlgorithm cha`, (c) invalid `--cg-algorithm bogus` → exit code 2 with `choices` error
- [ ] 2.10 Run `/rv-test-run rv-static-analysis`
- [ ] 2.11 End-to-end smoke: `rv-static-analysis --targets-file demo.txt cryptoapp.apk` produces JSON with `set(reaches_target signatures)` that is a strict subset of the MOP-path `set(reaches_target signatures)` for the same APK (STRICT must match a subset of the LENIENT result; no fixed threshold — `G_signature_file_subset`)
- [ ] 2.12 Commit `feat(gh60): C1b SignatureFileTargetSource + CLI --targets-file mutex + --cg-algorithm (refs #60)`

## 3. C1c — Java decomposition + characterization fixture

- [ ] 3.1 Capture characterization fixture: run `gator` on `cryptoapp.apk` at HEAD (post-C1b), copy resulting JSON to `tests/fixtures/gh60/cryptoapp_baseline_pre_decomp.json`, commit as `chore(gh60): G3.0 characterization fixture`
- [ ] 3.2 Extract `TargetResolver.java` from `RvsecAnalysisClient`: accepts `TargetMethodSource`, calls `load()`, resolves into `Set<SootMethod>` per `MatchPolicy`. Move `resolveMopInScene` logic here (keep name temporarily; rename in Group 6)
- [ ] 3.3 Extract `ReachabilityEngine.java`: encapsulates JGraphT BFS, reverse BFS from entry points, `findDirectMopCallersByBytecodeScan` (rename in Group 6). Constructor takes `Set<SootMethod> targets` + Soot `Scene`; method `run()` returns a `ReachabilityIndex`
- [ ] 3.4 Extract `ReachabilityIndex.java` (final class): immutable; constructor takes `Set<String> reachesTargetSet, Set<String> directTargetSet` (placeholder names — rename in Group 6); exposes `reachesTarget(SootMethod)`, `directlyReachesTarget(SootMethod)`, `reachesTargetSignatures(): Set<String>`, `directlyReachesTargetSignatures(): Set<String>` — all O(1)
- [ ] 3.5 Update `RvsecAnalysisClient.run()` to wire `TargetResolver → ReachabilityEngine → ReachabilityIndex`. Keep existing inline JSON writing for now (Group 4-5 extract the writer)
- [ ] 3.6 Add unit tests: `TargetResolverTest.java` (LENIENT vs STRICT dispatch), `ReachabilityEngineTest.java` (BFS over a synthetic call graph), `ReachabilityIndexTest.java` (lookup O(1), immutability)
- [ ] 3.7 Run `gator` on `cryptoapp.apk` after C1c; compare `set(reachesMop)` and `set(directlyReachesMop)` byte-equivalent set-comparison to `cryptoapp_baseline_pre_decomp.json` — diff zero (oracle of `G_paridade_reachability`)
- [ ] 3.8 Run on 5-APK canonical fixture (`cryptoapp` + 4 others from §3 of Phase-0 doc); same set-equivalence
- [ ] 3.9 Commit `refactor(gh60): C1c TargetResolver + ReachabilityEngine + ReachabilityIndex (refs #60)`

## 4. C1d — `ReachabilityEnricher` (visitor, no batch `ReportModel` — D3 revision 2)

- [ ] 4.1 Add `ReachabilityEnricher.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/reach/`: stateless visitor with constructor `(ReachabilityIndex index, String manifestPackage, String codePackage, String mainActivity)` and methods `enrichMethod(SootMethod) → Map<String,Object>`, `enrichWidget(Widget) → Map`, `enrichTransition(Transition) → Map`, `enrichComponent(Component) → Map`, `topLevelMetadata() → Map`, `targetSignatures() → Set<String>`. Each `enrich*` performs the `ReachabilityIndex` lookups and returns the key/value pairs the writer will emit for that node.
- [ ] 4.2 Update `RvsecAnalysisClient.run()` to construct the enricher after `ReachabilityEngine.run()` completes; pass it to Group 5's new `JsonReportWriter`. Inline JSON writer remains in place until Group 5 lands; for now, the existing writer is refactored to delegate per-node lookups to the new enricher (no batch POJO).
- [ ] 4.3 Add `ReachabilityEnricherTest.java`: assert `enrichMethod(m).get("reachesTarget") == index.reachesTarget(m)` for synthetic methods; assert idempotence (same input → same output, no internal mutation); assert `topLevelMetadata()` returns exactly `{manifestPackage, codePackage, mainActivity}` keys.
- [ ] 4.4 Add `ReachabilityEnricherMemoryTest.java`: invoke enricher 10k times against a mock index; assert heap delta is bounded (no internal accumulation) — guards against accidental batch caching regressions.
- [ ] 4.5 Run on 5-APK canonical fixture; `G_paridade_reachability` zero
- [ ] 4.6 Commit `refactor(gh60): C1d ReachabilityEnricher visitor (refs #60)`

## 5. C1e — Pure writer walker + sentinel complete + JsonSchema.Keys / `_JK`

- [ ] 5.1 Add `JsonSchema.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/json/` with nested `public static final class Keys`. Populate with all ~45 keys currently used by the inline writer (`PACKAGE`, `MAIN_ACTIVITY`, `REACHABILITY`, `WINDOWS`, `TRANSITIONS`, `COMPONENTS`, `TARGET_METHODS`, `REACHES_TARGET`, `DIRECTLY_REACHES_TARGET`, ..., `COMPLETE`). Use placeholder String values matching current names temporarily (e.g., `"reachesMop"`) — Group 6 will rename atomically.
- [ ] 5.2 Extract `JsonReportWriter.java` in same package: `public void write(ReportModel model, Path output) throws IOException`. Pure walker — only reads from `model` and emits keys via `JsonSchema.Keys.*`. NO field for `ReachabilityIndex`, NO method invocation against the index (INV-ANA-30).
- [ ] 5.3 At the end of `JsonReportWriter.write`, after all sections flushed, emit `,"complete":true}` as the last field. Ensure no exception path leaves the file with a complete sentinel (write sentinel after last flush; if any exception, file ends without sentinel) (INV-ANA-31).
- [ ] 5.4 Update `RvsecAnalysisClient.run()` to delegate JSON writing entirely to `new JsonReportWriter().write(model, outputPath)` after `ReachabilityEnricher.enrich(...)`. Remove inline JSON code.
- [ ] 5.5 Add `_JK = SimpleNamespace(...)` in `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py` mirroring `JsonSchema.Keys` value-for-value (same ~45 entries; placeholder names match `JsonSchema.Keys` exactly).
- [ ] 5.6 Refactor `StaticAnalysisParser` to read all keys via `_JK.x` instead of inline string literals. Add `complete: bool = False` field to `StaticAnalysisData` Pydantic model in `rv-android-core` (default False — Pydantic default for absent key); parser reads via `_JK.complete`.
- [ ] 5.7 Add `JsonSchemaKeysDump.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/json/`: `main()` iterates `JsonSchema.Keys.class.getDeclaredFields()`, filters `Modifier::isStatic` && `String.class`, prints each value on its own line. Add `tests/parity/json_keys.py`: invokes the dumper via `subprocess.run(["java","-cp","<gator-jar>","presto.android.gui.clients.json.JsonSchemaKeysDump"])`; imports `_JK` from Python; asserts `set(java_values) == set(python_values)`; on diff, prints which keys are only-Java and only-Python (INV-ANA-32). No regex against `.java` source.
- [ ] 5.8 Add `JsonReportWriterPurityTest.java`: assert `JsonReportWriter` constructor accepts only `ReachabilityEnricher` (plus output stream); assert no field is typed `ReachabilityIndex`; assert no method body references `ReachabilityIndex` (reflection-based field walk + bytecode scan via ASM) (INV-ANA-30). Also add `tests/parity/no_json_literals.py`: parses `JsonReportWriter.java` AST via `javalang`, walks string literals, asserts every key-like literal matches a value declared in `JsonSchema.Keys` (S25).
- [ ] 5.9 Add `SentinelEmissionTest.java`: (a) successful write ends with `,"complete":true}` and `fsync` was called once; (b) using the harness flag `--inject-failure-after-section=transitions` (added to `JsonReportWriter` for this test only — sole purpose is sentinel testing; C1h was dropped per Group 0 verdict so the flag has no other consumer), the writer raises `IOException` after the transitions flush; assert the partial file does NOT contain `"complete":true`. NO `kill JVM` mid-test — the harness flag replaces it.
- [ ] 5.10 Add `tests/parser/test_sentinel.py`: complete JSON parses to `data.complete == True`; truncated JSON (artificially cut after `windows[]`) parses to `data.complete == False`. Also add `tests/parser/test_truncated_recovery.py` covering the `_recover_truncated_json` path (preserved).
- [ ] 5.11 Run on 5-APK fixture; `G_sentinela_complete`, `G_json_keys`, `G_enricher_purity` all green
- [ ] 5.12 Run `/rv-test-run rv-static-analysis` and `/rv-test-run rv-android-core`
- [ ] 5.13 Commit `refactor(gh60): C1e JsonReportWriter walker + sentinel complete + JsonSchema.Keys/_JK (refs #60)`

## 6. C1f — Atomic rename MOP → Target across entire monorepo

<!-- This group MUST be atomic per-module commits. Subagent dispatch candidates: one subagent per consumer module (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) after the GATOR + parser + domain renames land. -->

- [ ] 6.1 GATOR Java rename (single commit `refactor(gh60): C1f rename MOP→Target in rvsec-gator`):
  - Rename class `MopMethod` → `TargetMethod` (already created in 1.2 — this step deletes the old class if any lingering reference remains)
  - Rename `loadMopSignatures` → `loadTargetSignatures` (and update callers)
  - Rename `resolveMopInScene` → `resolveTargetsInScene`
  - Rename `findDirectMopCallersByBytecodeScan` → `findDirectTargetCallersByBytecodeScan`
  - Rename internal fields `reachesMopSet` → `reachesTargetSet`, `directMopSet` → `directTargetSet` in `ReachabilityIndex` / `ReachabilityEngine`
  - Update `JsonSchema.Keys` values: `"reachesMop"` → `"reachesTarget"`, `"directlyReachesMop"` → `"directlyReachesTarget"`, `"mopMethods"` → `"targetMethods"`. Listener/transition future keys (`handlerReachesTarget`, `handlerDirectlyReachesTarget`) added as placeholders for C3.
  - Update Javadoc and any log strings mentioning "MOP method" to "target method"
- [ ] 6.2 Python parser rename (commit `refactor(gh60): C1f rename MOP→Target in rv-static-analysis`):
  - Update `_JK` values to mirror new `JsonSchema.Keys` (5.1 placeholders replaced by canonical Target names)
  - Remove any residual hard-coded `*Mop` string literals; replace with `_JK.*` references
- [ ] 6.3 rv-android-core domain rename (commit `refactor(gh60): C1f rename MOP→Target in rv-android-core`):
  - `Method.reaches_mop` → `Method.reaches_target` (and `directly_reaches_mop` → `directly_reaches_target`) in `modules/rv-android-core/src/rv_android_core/domain/classes.py` (the `Method` class lives in `classes.py:28`, not in `method.py`)
  - Same for `Widget` in `domain/widget.py`
  - `ComponentInfo.reaches_mop` → `ComponentInfo.reaches_target`, `ComponentInfo.directly_reaches_mop` → `ComponentInfo.directly_reaches_target`, AND `ComponentInfo.mop_methods` → `ComponentInfo.target_methods` in `domain/components.py:45,49,79` (the `mop_methods` field was missed in the original design; INV-CORE-33 covers it)
  - `@property target_reaches_target` in `WindowTransition` (`domain/wtg.py`) replacing `target_reaches_mop`; resolved via constructor-injected `window_methods_index: Mapping[str, list[Method]]` populated by the parser (see `specs/core/spec.md`); delete the legacy `@property` entirely
  - Add `StaticAnalysisData.complete: bool = False` in `domain/static.py` (new field — sentinel surface for parser)
  - Update Pydantic field descriptions: "MOP method" → "target method"
  - Update fixtures and tests in `modules/rv-android-core/tests/` (`test_classes.py`, `test_components.py`, `test_coverage.py`, `test_repository_initializer.py`)
  - Add `tests/domain/test_no_legacy_mop_fields.py` (AST inspection) — asserts no Pydantic model field name ends with `_mop` or `_directly_mop`, AND no field name equals `mop_methods` (INV-CORE-33)
  - Add `tests/domain/test_wtg.py::test_target_reaches_target_is_property` — asserts `isinstance(WindowTransition.__dict__['target_reaches_target'], property)` (INV-CORE-34)
  - `cov_reaches_mop` → `cov_reaches_target` in `domain/coverage.py` and `util/android/repository_initializer.py`
- [ ] 6.4 rv-coverage rename (commit `refactor(gh60): C1f rename cov_reaches_mop in rv-coverage`):
  - CSV header `cov_reaches_mop` → `cov_reaches_target` in `modules/rv-coverage/src/rv_coverage/...`
  - Python attributes / scripts mirroring the CSV
  - Update fixtures in `modules/rv-coverage/tests/`
- [ ] 6.5 rv-platform rename (commit `refactor(gh60): C1f rename in rv-platform`):
  - Grep `reaches_mop` in `modules/rv-platform/src/` (coverage components, result aggregators, TaskExecutor); update each site
  - Update tests
- [ ] 6.6 rv-experiment rename (commit `refactor(gh60): C1f rename in rv-experiment`):
  - Grep `reaches_mop` in `modules/rv-experiment/src/`; update sites in post-processing scripts
  - Update tests
- [ ] 6.7 aperv-tool rename (commit `refactor(gh60): C1f rename in aperv-tool`):
  - Re-grep `reaches_mop|mop_methods|MopMethod` in `modules/aperv-tool/src/` (initial grep 2026-05-25 returned 0; confirm at implementation time and rename any emergent site)
  - Update tests if any site is found
- [ ] 6.8 rv-screen-parser rename (commit `refactor(gh60): C1f rename in rv-screen-parser`):
  - Update 4 visitor files (`abstract_visitor.py`, `default_visitor.py`, `enhanced_visitor.py`, `model.py`) and 4 corresponding test files
- [ ] 6.9 scripts rename (commit `refactor(gh60): C1f rename in scripts`):
  - Update each of the 7 known-affected scripts: `aperv_objective.py`, `aperv_parameter_space.py`, `select_jca_stratified.py`, `jca557_vs_paper.py`, `static_analysis_sweep.py`, `augment_planilha.py`, `regenerate_results/{verify,regenerate_container}.py`
  - Document in the commit message that published CSVs under `results/` and `experimento-*/` are NOT touched (immutable scientific artifacts)
- [ ] 6.10 Documentation rename (commit `docs(gh60): C1f glossary updates`):
  - Update `CLAUDE.md` (root) glossary: "MOP method" → "target method"
  - Update `modules/rv-static-analysis/CLAUDE.md` + `docs/architecture.md`
  - Update `modules/rv-coverage/README.md` + `docs/architecture.md`
  - Update `modules/rv-android-core/CLAUDE.md` field-description nomenclature
- [ ] 6.11 `G_no_legacy_mop` CI gate — add `tests/parity/no_legacy_mop.py` that runs `git grep -nE "reachesMop|directlyReachesMop|mopMethods|handlerReachesMop|handlerDirectlyReachesMop|reaches_mop|directly_reaches_mop|handler_reaches_mop|handler_directly_reaches_mop|target_reaches_mop|cov_reaches_mop|mop_methods|\\bMopMethod\\b|loadMopSignatures|resolveMopInScene|findDirectMopCallersByBytecodeScan"` across `rvsec-gator/`, `modules/` (with `modules/rv-agent/` EXCLUDED — deprecated per CLAUDE.md), and `scripts/`. Exclusions: `MopSpecsTargetSource.java`, the literal `--mop-dir` and the `mop_dir` config attribute name, published CSVs under `results/` and `experimento-*/`, `openspec/changes/archive/`, and historical commit messages. Assert zero matches outside exclusions (INV-ANA-37, INV-CORE-33). Test file MUST emit each unexpected match as `file:line:content` on failure.
- [ ] 6.12 Run `/rv-test-run rv-android-core`, `/rv-test-run rv-coverage`, `/rv-test-run rv-platform`, `/rv-test-run rv-experiment`, `/rv-test-run rv-screen-parser`, `/rv-test-run aperv-tool` — all green post-rename
- [ ] 6.13 Run `/rv-qa-lint-fix` on each renamed module
- [ ] 6.14 End-to-end smoke: `gator` on cryptoapp + parse via updated `_JK` → `StaticAnalysisData` with `reaches_target`-named fields populated; downstream `rv-coverage` aggregation succeeds
- [ ] 6.15 gh57 regression suite — run `tests/regression/test_gh57_scenarios.py` covering inherited scenarios S7 (GATOR call-graph crash), S9 (Flowgraph body-skip recovery), S10 (Flowgraph opnode-skip recovery), S11 (Kotlin stdlib exclusion). New decomposition MUST honor INV-ANA-17/18 unchanged.

## 7. C1g — `JimpleDefUtils` extraction (independent of Groups 3-6)

- [ ] 7.1 Create `presto.android.util.JimpleDefUtils` in `rvsec-gator/sootandroid/src/main/java/`: extract `definitionRhs(Unit, Local)`, `resolveInt(Value)`, `resolveStr(Value)` methods currently duplicated in `MenuExtractor` and `SpinnerItemExtractor`
- [ ] 7.2 Replace duplicate methods in `MenuExtractor.java` and `SpinnerItemExtractor.java` with calls to `JimpleDefUtils`
- [ ] 7.3 Add `JimpleDefUtilsTest.java` covering the three methods with synthetic Jimple inputs
- [ ] 7.4 Verify existing `MenuExtractor` and `SpinnerItemExtractor` tests remain green
- [ ] 7.5 Coverage of `JimpleDefUtils` ≥ 90% via jacoco (`G_jimple_def_utils`)
- [ ] 7.6 Commit `refactor(gh60): C1g extract JimpleDefUtils (refs #60)`

## 8. C1h — DROPPED (Phase 1 task-zero verdict, 2026-05-25)

Atomic write + two-stage parser read removed from scope. Empirical basis: 826/826 gh57 sweep JSONs parse cleanly; zero corruption observed. Sentinel ADR-6 (task 5.3, 5.9, 5.10) remains the complete defense against the observed failure mode (timeout-during-WTG → fully written file with empty data sections). See `design.md` §D9 verdict block for the classification table and rationale.

## 9. Integration, sweep, and verification

- [ ] 9.1 Run full 5-APK canonical fixture smoke (`cryptoapp` + 4 others — list in `tests/fixtures/gh60/canonical_apks.txt`); the following in-scope gates MUST be green:
  - `G_paridade_reachability` — zero set-diff vs characterization fixture
  - `G_paridade_targets` — zero set-diff vs characterization fixture
  - `G_json_keys` — Java↔Python parity via reflection dumper (no regex)
  - `G_no_legacy_mop` — zero matches outside documented exclusions; scans `rvsec-gator/` + `modules/` (excl. `rv-agent/`) + `scripts/`
  - `G_mutex_cli` — all 4 mutex cases pass
  - `G_enricher_purity` — `JsonReportWriter` has zero `ReachabilityIndex` reference
  - `G_sentinela_complete` — successful runs end with `,"complete":true}` after fsync; injected-failure runs end without sentinel
  - `G_cg_algorithm_cli` — all 3 `--cg-algorithm` cases pass
  - `G_jimple_def_utils` — `MenuExtractor` and `SpinnerItemExtractor` contain zero private duplicates of the helpers; both call `JimpleDefUtils.*`
  - `G_no_match_mode_flag` — no forbidden CLI option string registered
  - `G_no_json_literals_in_writer` — `JsonReportWriter.java` contains no key-like string literal outside `JsonSchema.Keys` references
  - `G_signature_file_subset` — STRICT result is a subset of LENIENT result on `cryptoapp`
  - Deferred (NOT executed in gh60 — confirm by absence): `G_widget_reachability`, `G_transition_reachability`, `G_dead_code_wtg`, `G_dead_code_flowgraph` (all owned by C2/C3)
- [ ] 9.2 Run integration test full pipeline: `uv run rv-experiment run --tools aperv --apks-dir ./apks_examples --timeout 60` (aperv is the target consumer of `--targets-file`; rv-agent is deprecated — do NOT use it here). Sanity check that consumer-side rename did not break end-to-end execution.
- [ ] 9.3 Run sweep on 380 APKs in background (post all C1 commits): `bash scripts/run_jca_sweep.sh ...` (or equivalent); collect per-APK `|count_new - count_old| / count_old`; assert ≤ 5% per APK in `reachesTarget`/`windows`/`transitions` (vs `reachesMop` baseline — set-comparison transparent to rename); flag outliers > 5% for manual review and attach to PR.
- [ ] 9.4 Report the `complete=true` rate from the sweep. **Hard floor: 80%.** If below floor, open a `gator-regression` GitHub issue before merging anything downstream that consumes the sweep.
- [ ] 9.5 Run `/rv-qa-lint-fix rv-static-analysis`, `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-coverage`, `/rv-qa-lint-fix rv-platform`, `/rv-qa-lint-fix rv-experiment`, `/rv-qa-lint-fix rv-screen-parser`, `/rv-qa-lint-fix aperv-tool`
- [ ] 9.6 Run `/rv-verify rv-static-analysis`, `/rv-verify rv-android-core`, `/rv-verify rv-coverage` (full verification: tests + lint + type)
- [ ] 9.7 Run `openspec validate "gh60-targets-core"` — must pass structural validation
- [ ] 9.8 Invoke `/rv-code-reviewer` via Skill tool on the diff vs `master`; address any high-confidence findings
- [ ] 9.9 Run `/rv-docs-sync rv-static-analysis` and `/rv-docs-sync rv-android-core` to update CLAUDE.md and architecture.md for the renamed components and new abstractions
- [ ] 9.10 Open PR; reference issue #60; ensure PR body includes: `Closes #60`, gates table with green status, sweep outliers (if any), and link to the Phase-0 ideation doc
- [ ] 9.11 After PR merged: run `openspec instructions apply --change "gh60-targets-core"` and `/opsx:verify gh60-targets-core` (Phase 5); `/opsx:archive gh60-targets-core` (Phase 6) — syncs deltas to main specs and archives the change.

## 10. Follow-up tracking — open issues for C2 and C3 (NOT implementation tasks)

After C1 merges, open placeholder issues in GitHub PAMunb/rvsec using `docs/20260515_plano_gator_targets_generic.md` §10.2 and §10.3 as bodies. These issues do NOT become OpenSpec changes until they are ready to start — they only make the backlog visible and allow `refs #61`/`refs #62` on commits that touch preparatory code (rare). The static analyzer **is only complete after C2 and C3 merge**.

- [ ] 10.1 Open GitHub issue C2 — `[Refactor] GATOR: hardening (cache, menu superclass, integer-array, dead code expanded) + dual package + observability` (body from §10.2 of the Phase-0 doc). Note in body: G6.5c `buildCallGraphLegacy` is EXCLUDED from "dead code" scope — it has a live caller at `FlowgraphRebuilder.java:980`; removal requires architectural decision on the `cgDelegation` branch.
- [ ] 10.2 Open GitHub issue C3 — `[Feature] GATOR: JSON enrichment for agent prioritization (widget/transition reachability + external exit + event types)` (body from §10.3 of the Phase-0 doc). Note in body: the per-transition aggregate field MUST be named `transition_reaches_target_aggregate`, not `target_reaches_target` (which is already taken by the window-level `@property` introduced in gh60 — see D10).
- [ ] 10.3 Update the Phase-0 doc (`docs/20260515_plano_gator_targets_generic.md` §9) with the actual issue numbers assigned to C2 and C3 (replace `gh<N+1>`/`gh<N+2>` placeholders)
- [ ] 10.4 Add cross-reference in this change's archive metadata that "C1 of 3" and explicitly link the C2/C3 issue numbers when known

**Critical reminder:** the static analyzer overhaul is incomplete until C2 and C3 merge. Treat C1 (this change) as foundation, not completion. The 3-change fragmentation is non-negotiable per Phase-0 §9 multi-LLM convergence.
