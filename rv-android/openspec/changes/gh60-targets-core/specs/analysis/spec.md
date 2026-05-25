## Purpose

This delta updates the `analysis` capability to (a) generalize the GATOR static analysis input from MOP-only specs to a polymorphic `TargetMethodSource` abstraction, (b) decompose the 1625 LOC `RvsecAnalysisClient` god class into single-responsibility components, (c) rename the JSON contract field family from `*Mop` to `*Target` end-to-end (BREAKING — sweep regenerates), (d) introduce a JSON completion sentinel `"complete": true` to distinguish truncation from corruption without atomic-write overhead, and (e) introduce shared JSON-key constants on both Java and Python sides to eliminate the historical drift class (`eventType` vs `type`, etc.).

The delta preserves the existing analysis pipeline semantics: the same set of methods reaches the same set of targets under the equivalent source. Comparison against the gh57 baseline (`b2e04a26`) is performed via **set-equivalence** of method signatures, not byte-equivalent JSON diff — BFS over Java `Set` may reorder JSON sections cosmetically without changing content.

Phase-0 ideation in `docs/20260515_plano_gator_targets_generic.md` is authoritative for decisions already taken (7 ADRs decided, multi-LLM convergence absorbed). Hardening bug fixes and JSON enrichment for agents are out of scope here — see follow-up changes C2 and C3.

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to a `TargetMethodSource` (coverage denominator), (2) window and widget inventory with event listeners, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and target reachability. The JSON output MUST end with a sentinel `"complete": true` as the last top-level field on successful completion (INV-ANA-31).

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. Following decomposition, `RvsecAnalysisClient` is an orchestrator (~200 LOC) that wires four single-responsibility components plus a streaming enricher: `TargetResolver` (loads from a `TargetMethodSource` and resolves into Soot `Scene`), `ReachabilityEngine` (builds JGraphT call graph, runs multi-source BFS, complements with bytecode scan), `ReachabilityIndex` (encapsulated lookup ADT), `ReachabilityEnricher` (per-node visitor that annotates each window/transition/component/method on the fly using `ReachabilityIndex`, called by the writer during the section walk — NOT a batch materializer), and `JsonReportWriter` (incremental walker that emits each section to the output stream and flushes immediately, invoking `ReachabilityEnricher` callbacks per node to obtain the annotated values; `flush()` per section preserves partial recovery on timeout). The `JsonReportWriter` MUST NOT itself call any `ReachabilityIndex` lookup method (INV-ANA-30); all flag decisions go through the injected `ReachabilityEnricher` callback interface, which is purely a delegate — the writer holds no direct reference to the index.

GATOR initializes Soot once with defensive configuration (INV-ANA-16), builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the orchestrator writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file (no sentinel emitted — `complete` is absent or implicitly `false`). The writer MUST NOT buffer all sections into memory before serialization — this would defeat the partial-recovery guarantee when timeout is the dominant failure mode (~30-50% of large sweeps per gh57 ground truth). Each section is enriched and emitted in one stream, then flushed before the next section is computed.

The `Flowgraph.processApplicationClasses()` method MUST handle individual method failures gracefully (INV-ANA-17). When `retrieveActiveBody()` or `createOpNode()` throws an exception for a specific method, the Flowgraph MUST skip that method and continue processing remaining methods. The resulting Flowgraph may be incomplete (missing OpNodes, widgets, or listeners for skipped methods), but the GUIAnalysis pipeline MUST complete and the `RvsecAnalysisClient` MUST produce JSON output. Reachability data (computed from `Scene.v().getCallGraph()` via BFS) is NOT affected by Flowgraph incompleteness — it depends on the Soot call graph, not on the Flowgraph.

The GATOR MUST use Soot 4.7.1 (`org.soot-oss:soot`, INV-ANA-18) with defensive configuration (INV-ANA-16). The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) is not fixed in Soot 4.7.1, but the improved Dexpler in 4.x reduces crash frequency. The defensive options (excluding `kotlin.*`, `kotlinx.*`, and `androidx.compose.*` from body loading, disabling `jb.sils`/`jb.dae`) further reduce the crash surface.

Crash recovery is bounded by phase: failures inside `Flowgraph.processApplicationClasses()` are method-local (skip method, continue — INV-ANA-17) and the analysis pipeline completes. Failures inside Soot's call-graph construction phase (e.g., SPARK `InternalTypingException`) are NOT recoverable at the Flowgraph level — the JVM exits with a non-zero code and no JSON is produced. This boundary is load-bearing: it prevents the silent emission of a "complete-looking" report built on a corrupt call graph. Together, these recovery rules form a layered defense — prevention (defensive Soot config), method-local skip (Flowgraph try-catch), and hard halt (call-graph phase) — each at a distinct layer with non-overlapping responsibility.

When comparing analysis output against a baseline (e.g., gh57 commit `b2e04a26`), tolerances reflect Soot 4.7.1 non-determinism: for set-based reachability comparisons the contract is **strict equality** (BFS is deterministic over a fixed call graph and target set); for cardinality metrics derived from Flowgraph skips (window/transition/widget counts) a ±10% tolerance is permitted to absorb crash-frequency variation across Soot runs. `directlyReachesTarget` MUST be a strict superset or equal to the baseline `directlyReachesMop` set (BUG-INV-ANA-19: the bytecode-scan complement can only add direct callers SPARK missed, never remove them).

The execution order inside `run()`:

1. **Loads target methods via `TargetMethodSource` and resolves into Soot `Scene`**. The source is constructed from CLI input: `--mop-dir <dir>` yields a `MopSpecsTargetSource` wrapping `JavamopFacade.listUsedMethods(mopDir, false)`; `--targets-file <path>` yields a `SignatureFileTargetSource` parsing a text file of Soot signatures (one per line, `#` comments, blank lines tolerated). The two CLI flags are mutually exclusive (INV-ANA-33). The `TargetResolver` calls `source.load()` to produce a `Set<TargetMethod>`, then resolves each to one or more `SootMethod` instances per the source's matching policy: LENIENT (class+name only) for `MopSpecsTargetSource` because AspectJ wildcards in `.mop` specs leave the full signature semantically undefined; STRICT (full Soot signature) for `SignatureFileTargetSource` because the user controls precision. Wildcard parameter lists in a targets-file entry (`(..)` or `(*)`) resolve LENIENT for that entry only.

2. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). For each application method, the `ReachabilityEngine` computes: `reachable` (reachable from entry points), `reachesTarget` (has path to a resolved target method — renamed from `reachesMop`), and `directlyReachesTarget` (directly invokes a resolved target method — renamed from `directlyReachesMop`). The `ReachabilityIndex` materializes these as `Set<String>` for O(1) lookup. This section is written and flushed first.

3. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners. Two fields not available via GATOR APIs — `inputType` and `entries` — are extracted by parsing the decoded layout XML files at `Configs.resourceLocation`.

4. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures.

5. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager`, `android:exported` attribute, and target reachability cross-referenced with the reachability BFS results. This section is written and flushed last.

6. **Emits sentinel `"complete": true`** as the final top-level field, after all sections are flushed. Parser uses this to distinguish a successful run from a truncated one (INV-ANA-31).

The `complementWithCallbacks()` method, which propagates target reachability flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null` when the method belongs to no component) and `isMain` (boolean) fields. The legacy `isActivity` and `isMainActivity` fields are removed (no shim — P3). The `StaticAnalysisParser` (Python) MUST parse the new fields into the `Clazz` domain model as `component_type: str | None` and `is_main: bool`. The `null` handler exists because `getSootClassUnsafe` may return `null` for methods declared on synthetic or excluded classes; the producer emits `componentType=null` rather than dropping the entry, preserving the reachability set cardinality.

All JSON keys MUST be emitted via constants in `presto.android.gui.clients.json.JsonSchema.Keys` (Java) and consumed via `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` (Python). The two constant sets MUST be value-equal (INV-ANA-32) — verified by `tests/parity/json_keys.py`.

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components, `complete: bool`). Downstream consumers (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) receive renamed Pydantic fields per the `core` spec delta. rv-agent (deprecated) is not a live consumer; sweep regenerates JSONs and breaks rv-agent's stale reader by design.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages.

The reachability section also provides target prioritization data consumed by agents. The agent's action ranker assigns score boosts to actions whose handler method has `directly_reaches_target=true` or `reaches_target=true` (consumer side details outside this spec).

The call graph is built using SPARK (`-cgAlgorithm spark`) with `all-reachable:true`, which performs full points-to analysis to resolve virtual calls based on types effectively instantiated in the program. SPARK is the operational default. Other algorithms — CHA, RTA, VTA — remain available. JCA framework classes appear as call targets whenever any application method invokes them — they do not need to be entry points.

**Module**: rv-static-analysis (launcher + parser — modified for `--targets-file`, `_JK`, sentinel check), rvsec-gator (analysis client — decomposed + renamed + sentinel-emitting)
**Key components**: `Main.java` (Soot config), `Flowgraph.java` (error handling), `RvsecAnalysisClient` (orchestrator, ~200 LOC post-decomp), `TargetMethod`, `TargetMethodSource`, `MopSpecsTargetSource`, `SignatureFileTargetSource`, `TargetResolver`, `ReachabilityEngine`, `ReachabilityIndex`, `ReachabilityEnricher` (visitor callback, no `ReportModel` materialization), `JsonReportWriter` (streaming walker with `flush()` per section), `JsonSchema.Keys`, `JsonSchemaKeysDump` (reflection-based parity dumper), `JimpleDefUtils`, `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser` (consumes `_JK` + sentinel; builds `window_methods_index` for `WindowTransition.target_reaches_target`), `Clazz`.

#### Scenario: Successful static analysis with valid APK using --mop-dir

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path, the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`, and the user passed `--mop-dir <dir>` on the CLI
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -cgAlgorithm spark`
- **AND** the producer MUST instantiate `MopSpecsTargetSource(Path(mopDir))` and `TargetResolver` MUST resolve targets LENIENT (class+name)
- **AND** the resulting `.json` file MUST end with `"complete": true` as the final top-level field
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` with `complete == True`
- **AND** all JSON keys present in the output MUST match values declared in `JsonSchema.Keys`

#### Scenario: Successful static analysis using --targets-file

- **WHEN** the user invokes `rv-static-analysis --targets-file demo.txt <apk>` and `demo.txt` contains lines such as `<javax.crypto.Cipher: void init(int,java.security.Key)>` and `# comment` and blank lines
- **THEN** the CLI MUST accept the invocation (mutex group permits exactly one of `--mop-dir` or `--targets-file`, INV-ANA-33)
- **AND** GATOR MUST be invoked with `-clientParam targetsFile=<path>` instead of `mopDir=...`
- **AND** the producer MUST instantiate `SignatureFileTargetSource(Path(targetsFile))` and `TargetResolver` MUST resolve targets STRICT (full signature) for non-wildcard entries
- **AND** entries containing `(..)` or `(*)` MUST resolve LENIENT for that entry only
- **AND** the output JSON MUST follow the same schema as the `--mop-dir` path (same keys, sentinel last)

#### Scenario: CLI mutex rejects passing both --mop-dir and --targets-file

- **WHEN** the user invokes `rv-static-analysis --mop-dir /m --targets-file /t <apk>`
- **THEN** the argparse mutex group MUST emit an error to stderr explaining `--mop-dir` and `--targets-file` are mutually exclusive
- **AND** the process MUST exit with a non-zero return code before launching GATOR

#### Scenario: CLI rejects passing neither --mop-dir nor --targets-file

- **WHEN** the user invokes `rv-static-analysis <apk>` without specifying any target source
- **THEN** the argparse mutex group MUST emit an error indicating one of `--mop-dir` or `--targets-file` is required
- **AND** the process MUST exit with a non-zero return code

#### Scenario: --targets-file with malformed signature line

- **WHEN** the targets-file contains a line that is not blank, not a `#` comment, and is not a valid Soot signature (e.g., `Cipher.init` without angle brackets)
- **THEN** `SignatureFileTargetSource.load()` MUST raise `IllegalArgumentException` with the offending line number and content
- **AND** the GATOR process MUST exit with a non-zero code before producing any JSON

#### Scenario: MopSpecsTargetSource preserves baseline byte-for-byte

- **WHEN** GATOR analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` using the decomposed pipeline (`TargetResolver` + `ReachabilityEngine`)
- **THEN** the resulting `set(method.signature for method in data.methods if method.reaches_target)` MUST be equal to the same set computed from the gh57 baseline at commit `b2e04a26` (`reaches_mop` semantically — set comparison transparent to rename)
- **AND** the resulting `set(method.signature for method in data.methods if method.directly_reaches_target)` MUST be equal to the corresponding baseline set
- **AND** `cryptoapp.apk` MUST report exactly 16 target methods (INV-ANA-35)

#### Scenario: GATOR crashes during call graph construction

- **WHEN** Soot's call-graph builder throws an `InternalTypingException` during call graph construction for a method in a Kotlin class
- **THEN** the GATOR process MUST terminate with a non-zero exit code
- **AND** no `.json` output file MUST exist (the crash occurs before `RvsecAnalysisClient.run()` is invoked)
- **AND** the `StaticAnalyzer` wrapper MUST log the failure as `StaticAnalysisException`
- **AND** the `StaticAnalysisResult.analysis_file` MUST point to the expected output path (which does not exist)

#### Scenario: Timeout during JSON write produces truncated file without sentinel

- **WHEN** GATOR is killed by external timeout enforcement mid-way through `JsonReportWriter.write` (e.g., after `windows[]` is flushed but before `transitions[]` is complete)
- **THEN** the partial JSON file on disk MUST NOT contain the `"complete": true` sentinel
- **AND** `StaticAnalysisParser` MUST parse what is available via `_recover_truncated_json` (load-bearing recovery)
- **AND** `StaticAnalysisData.complete` MUST be `False` (Pydantic default for absent key)
- **AND** downstream gates requiring completeness MUST exclude this sample

#### Scenario: Flowgraph skips method with failing body (Scenario B recovery)

- **WHEN** `Flowgraph.processApplicationClasses()` calls `currentMethod.retrieveActiveBody()` and Soot throws an exception for a specific method
- **THEN** the exception MUST be caught by the try-catch around `retrieveActiveBody()` (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()` with the skipped method's signature and exception message
- **AND** the loop MUST continue to the next method via `continue`
- **AND** the Flowgraph MUST complete with partial data
- **AND** the `RvsecAnalysisClient.run()` MUST execute and produce a JSON file (with sentinel if no further failure)

#### Scenario: Flowgraph skips statement with failing OpNode creation

- **WHEN** `Flowgraph.processApplicationClasses()` calls `createOpNode(currentStmt)` and the method throws an exception for a specific statement
- **THEN** the exception MUST be caught by the existing catch block (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()`
- **AND** the loop MUST continue to the next statement via `continue`

#### Scenario: Kotlin stdlib exclusion impact on reachability

- **WHEN** GATOR analyzes an APK with Kotlin dependencies and `-exclude kotlin.`, `-exclude kotlinx.`, and `-exclude androidx.compose.` are active
- **THEN** classes in those packages MUST NOT have their bodies jimplified
- **AND** the call graph MUST still contain edges from application code to excluded package methods (as phantom refs)
- **AND** the `reachability` section MUST NOT include excluded-package classes
- **AND** for targets like `javax.crypto.*` / `java.security.*`, reachability MUST NOT be affected because those APIs are called by application code, not by Kotlin stdlib or Compose runtime

#### Scenario: Analysis output comparison after decomposition (refactor-only)

- **WHEN** the decomposed pipeline analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` and the output is compared against the saved characterization fixture captured immediately before C1c on the same Soot 4.7.1 + same baseline commit
- **THEN** window count MUST match exactly (±0)
- **AND** transition count MUST match exactly (±0)
- **AND** total method count MUST match exactly (±0)
- **AND** `set(reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(reaches_mop signatures)` (set-equivalence, transparent to field rename and to JSON byte-order)
- **AND** `set(directly_reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(directly_reaches_mop signatures)` (the decomposition is a refactor — no new direct edges introduced)

#### Scenario: Analysis output comparison against gh57 baseline across Soot runs

- **WHEN** the post-rename pipeline analyzes `cryptoapp.apk` and is compared against the gh57 baseline at commit `b2e04a26`, potentially across distinct Soot 4.7.1 invocations
- **THEN** `set(reaches_target signatures)` MUST equal `set(reaches_mop signatures)` from the baseline (strict equality — BFS is deterministic over the same call graph and target set)
- **AND** `set(directly_reaches_target signatures)` MUST equal the baseline `set(directly_reaches_mop signatures)` (the bytecode-scan complement is deterministic)
- **AND** window / transition / widget counts MAY differ by up to ±10% to absorb Soot 4.7.1 non-determinism from Flowgraph skips on borderline-broken methods
- **AND** the GESDA widget parity subset MUST match exactly (this subset is hand-curated and skip-free)

#### Scenario: directlyReachesTarget detects literal library invocations omitted by SPARK (BUG-INV-ANA-19)

- **WHEN** an application method's bytecode contains a literal `invoke-*` whose target's `(declaringClass.getName(), methodRef.name())` matches a resolved target from `ReachabilityIndex.reachesTargetSignatures()`
- **AND** Soot's SPARK call graph does NOT contain that target as a vertex
- **THEN** `findDirectTargetCallersByBytecodeScan` (renamed from `findDirectMopCallersByBytecodeScan`) MUST detect the invocation by walking the method's `Body.getUnits()`, casting each to `Stmt`, and inspecting `InvokeExpr.getMethodRef()` against the precomputed `Set<String>` of `"className#methodName"` keys
- **AND** the detection MUST be independent of the call graph
- **AND** the matched method MUST be unioned into `directTargetSet` after `findDirectTargetCallers` completes
- **AND** the output JSON MUST report `directlyReachesTarget=true` for that method
- **AND** the implementation MUST log scan statistics

#### Scenario: Bytecode-scan resilience on corrupted method bodies

- **WHEN** the bytecode scanner attempts `method.retrieveActiveBody()` and Soot raises a `RuntimeException` or `OutOfMemoryError` on a single application method
- **THEN** the scanner MUST catch the throwable, emit a WARN log, and `continue` to the next method
- **AND** the body-retrieval skip MUST be counted in the `bodies_skipped` log statistic
- **AND** the scanner MUST NOT abort the analysis

#### Scenario: Bytecode-scan scope is limited to application classes

- **WHEN** the bytecode scanner runs as part of the `ReachabilityEngine`
- **THEN** it MUST iterate only the `appClasses` map produced by `extractClasses` (filtered by `code_package`)
- **AND** it MUST NOT iterate every class in `Scene.v().getClasses()`
- **AND** the union with `directTargetSet` MUST never report a library class as a direct target caller

#### Scenario: JsonReportWriter purity — no runtime ReachabilityIndex lookup

- **WHEN** the post-decomposition `JsonReportWriter.write(ReportModel, Path)` is invoked
- **THEN** the writer MUST NOT hold any reference to `ReachabilityIndex` (verified by absence of import and absence of constructor parameter)
- **AND** every flag in the emitted JSON (`reachesTarget`, `directlyReachesTarget`, future `handlerReachesTarget`, etc.) MUST be read directly from the `ReportModel` fields populated upstream by `ReachabilityEnricher` (INV-ANA-30)

#### Scenario: JsonSchema.Keys ↔ _JK parity

- **WHEN** the parity test `tests/parity/json_keys.py` runs in CI
- **THEN** it MUST execute a small Java helper (`JsonSchemaKeysDump`) via subprocess that uses reflection (`Arrays.stream(JsonSchema.Keys.class.getDeclaredFields()).filter(Modifier::isStatic).map(f -> f.get(null))`) and prints the values one-per-line
- **AND** it MUST import `_JK` from Python and collect `set(_JK.__dict__.values())`
- **AND** the two sets MUST be equal (INV-ANA-32)
- **AND** the test MUST fail with a diff listing keys only in Java vs only in Python if they diverge
- **AND** the test MUST NOT rely on text-level regex against the `.java` source (fragile to Javadoc, multi-line concatenation, comments)

#### Scenario: MatchPolicy has no CLI flag

- **WHEN** any caller inspects the `rv-static-analysis` `argparse.ArgumentParser`
- **THEN** there MUST be no argument named `--match-mode`, `--matching`, `--lenient`, `--strict`, or any equivalent that would override policy at the CLI level (INV-ANA-36)
- **AND** the assertion is verified by `tests/cli/test_no_match_mode_flag.py` walking `parser._actions` for forbidden option strings

#### Scenario: G_no_legacy_mop CI gate finds zero legacy references

- **WHEN** the CI gate `tests/parity/no_legacy_mop.py` runs `git grep -nE "reachesMop|directlyReachesMop|mopMethods|handlerReachesMop|handlerDirectlyReachesMop|reaches_mop|directly_reaches_mop|handler_reaches_mop|handler_directly_reaches_mop|target_reaches_mop|cov_reaches_mop|\\bMopMethod\\b|loadMopSignatures|resolveMopInScene|findDirectMopCallersByBytecodeScan"` across `rvsec-gator/`, `modules/` (excluding `modules/rv-agent/` — deprecated per CLAUDE.md), and `scripts/`
- **THEN** the only matches MUST be inside the documented exclusion set: `MopSpecsTargetSource.java`, the CLI flag literal `--mop-dir`, the config attribute name `mop_dir`, published CSVs under `results/` and `experimento-*/`, archived OpenSpec deltas under `openspec/changes/archive/`, and historical commit messages
- **AND** zero matches MUST appear in any other location
- **AND** on any extra match the gate MUST exit non-zero with the file:line of each unexpected hit (INV-ANA-37)

#### Scenario: JsonReportWriter contains no inline string literals for JSON keys

- **WHEN** the audit `tests/parity/no_json_literals.py` parses `JsonReportWriter.java` and counts string literals that match the pattern `"[a-z][a-zA-Z0-9]*"` outside of `JsonSchema.Keys.*` references
- **THEN** the count MUST be zero
- **AND** the test MUST fail with the offending line numbers if any inline literal is found

#### Scenario: JimpleDefUtils replaces duplicated helpers in MenuExtractor and SpinnerItemExtractor

- **WHEN** the post-extraction GATOR jar is inspected
- **THEN** `presto.android.util.JimpleDefUtils` MUST exist with public static methods `definitionRhs(Unit, Local)`, `resolveInt(Value)`, `resolveStr(Value)`
- **AND** `MenuExtractor.java` and `SpinnerItemExtractor.java` MUST contain zero private duplicates of those helpers (grep within those two files yields zero hits for `private.*definitionRhs|private.*resolveInt|private.*resolveStr`)
- **AND** `MenuExtractor` and `SpinnerItemExtractor` MUST invoke the helpers via `JimpleDefUtils.*` qualified calls

## ADDED Requirements

### Requirement: Target Method Source Abstraction (FR04)

The GATOR analysis client MUST load methods of interest via a `TargetMethodSource` interface with at least two production implementations: `MopSpecsTargetSource` (loads from JavaMOP `.mop` specs via `JavamopFacade.listUsedMethods`) and `SignatureFileTargetSource` (loads from a plain-text file of Soot method signatures). The interface decouples target loading from JavaMOP, enabling use of GATOR for use cases outside RV-Android (taint sinks for auditing, custom method lists for papers, third-party toolchains).

The `TargetMethod` POJO (in `presto.android.gui.clients.target`) carries `className: String`, `methodName: String`, `params: List<String>`, `signature: String`, and `policy: MatchPolicy` where `MatchPolicy` is the enum `{ LENIENT, STRICT }`. The policy is populated by the source — it is NOT a CLI-level concern (INV-ANA-36).

`MopSpecsTargetSource` MUST resolve LENIENT (match by class+name only) to preserve compatibility with AspectJ pointcuts in `.mop` specs whose parameter lists contain wildcards (`init(int, Certificate, ..)`, `getInstance(String, Object+)`).

`SignatureFileTargetSource` MUST resolve STRICT (full Soot signature match) for each non-wildcard entry. Entries whose parameter list is `(..)` or `(*)` resolve LENIENT for that entry only — wildcard syntax is opt-in per entry, not file-wide.

The `SignatureFileTargetSource` parser MUST tolerate blank lines and lines beginning with `#` (comments), and MUST raise `IllegalArgumentException` (with line number) on any other malformed line.

**Module**: rvsec-gator (`commons/target/TargetMethod.java`, `commons/target/TargetMethodSource.java`, `client/target/MopSpecsTargetSource.java`, `client/target/SignatureFileTargetSource.java`).

#### Scenario: TargetMethodSource interface is the only entry point to target loading

- **WHEN** `RvsecAnalysisClient.run()` needs to load methods of interest
- **THEN** it MUST construct a `TargetMethodSource` (from CLI argument dispatch) and call `source.load()` to obtain `Set<TargetMethod>`
- **AND** it MUST NOT call `JavamopFacade.listUsedMethods` directly (that call lives inside `MopSpecsTargetSource` only)

#### Scenario: SignatureFileTargetSource parses comments, blanks, and signatures

- **WHEN** `SignatureFileTargetSource.load()` is invoked on a file containing:
  ```
  # JCA crypto sinks
  <javax.crypto.Cipher: void init(int,java.security.Key)>

  <javax.crypto.Cipher: byte[] doFinal(byte[])>
  # LENIENT wildcard
  <javax.crypto.Cipher: void init(..)>
  ```
- **THEN** the returned set MUST contain exactly 3 `TargetMethod` instances
- **AND** the first two MUST have `policy == STRICT`
- **AND** the third MUST have `policy == LENIENT`

#### Scenario: MopSpecsTargetSource is a thin wrapper over JavamopFacade

- **WHEN** `MopSpecsTargetSource(Path.of("/m")).load()` is invoked
- **THEN** it MUST delegate to `JavamopFacade.listUsedMethods(/m, false)`
- **AND** it MUST convert each `MopMethod` to a `TargetMethod` with `policy == LENIENT`
- **AND** the resulting `Set<TargetMethod>` MUST be equal in cardinality to the historical `Set<MopMethod>` produced by `loadMopSignatures` on the same input (INV-ANA-35)

### Requirement: JSON Completion Sentinel (NFR02)

The `JsonReportWriter` MUST emit the literal field `"complete": true` as the **final** top-level field of the JSON output, written only after all preceding sections have been flushed successfully. The Python parser MUST surface this field as the `complete: bool` attribute on `StaticAnalysisData`, with default `False` when the key is absent (truncated or corrupted output).

The sentinel is NOT a schema version. It carries no version number, no schema identifier, no producer metadata — it is a single binary invariant: "the producer reached the end of write successfully". P3 (no backward compatibility) is preserved because `complete` is a new field, not a transformation of any existing one.

Downstream gates and consumers MAY filter samples where `complete is False` to avoid false positives caused by truncation. Gates that compare against the baseline (`G_paridade_reachability`, `G_widget_reachability`, `G_transition_reachability`) MUST apply this filter.

**Module**: rvsec-gator (`client/json/JsonReportWriter.java`), rv-static-analysis (`parser/static/static_analysis_parser.py`).

#### Scenario: Successful run emits sentinel as last field

- **WHEN** GATOR completes analysis of `cryptoapp.apk` without timeout or crash
- **THEN** the JSON file MUST end with `,"complete":true}` (allowing for whitespace and field ordering of preceding fields)
- **AND** `JSON.parse(...)["complete"] == true`

#### Scenario: Truncated run does not emit sentinel

- **WHEN** GATOR is killed mid-write by external timeout enforcement after `windows[]` flushed but before `transitions[]` completes
- **THEN** the partial JSON file MUST NOT contain the literal `"complete":true`
- **AND** `StaticAnalysisParser` MUST parse what is recoverable via `_recover_truncated_json`
- **AND** the resulting `StaticAnalysisData.complete` MUST be `False`

#### Scenario: Parser default for absent sentinel key

- **WHEN** `StaticAnalysisParser.parse_json` reads a JSON object that does not contain the `complete` key
- **THEN** the resulting `StaticAnalysisData.complete` MUST be `False`
- **AND** no warning or error MUST be raised

### Requirement: Shared JSON Schema Keys (P1, NFR04)

All field names in the JSON contract between `rvsec-gator` (Java producer) and `rv-static-analysis` (Python consumer) MUST be defined as constants in two parallel locations: `presto.android.gui.clients.json.JsonSchema.Keys` on the Java side (public static final String fields), and `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` on the Python side.

The two constant sets MUST be value-equal (INV-ANA-32). A parity test `tests/parity/json_keys.py` MUST run in CI and fail if they diverge.

This eliminates a category of historical drift bugs (e.g., listener events emitted under key `"eventType"` while transitions emitted `"type"`, both read as `"type"` by the Python parser with a silent default).

**Module**: rvsec-gator (`client/json/JsonSchema.java`), rv-static-analysis (`parser/static/static_analysis_parser.py`).

#### Scenario: JsonSchema.Keys and _JK are value-equal

- **WHEN** the CI parity test runs `python tests/parity/json_keys.py`
- **THEN** it MUST extract the values of all `public static final String` fields declared in `JsonSchema.Keys` (Java, via parsing the source file)
- **AND** it MUST extract `set(_JK.__dict__.values())` (Python)
- **AND** the test MUST assert the two sets are equal (using `xor` to find differences)
- **AND** if they differ, the test MUST print which keys are only-Java and only-Python, then fail

#### Scenario: All JSON writes use the constants

- **WHEN** code review or grep audit examines `JsonReportWriter.java`
- **THEN** it MUST NOT contain string literals matching `"[a-zA-Z]+":` outside of `JsonSchema.Keys` references
- **AND** all `out.append("\"...\"")` for key names MUST use `JsonSchema.Keys.X` references

### Requirement: ReachabilityEnricher Materializes ReportModel (P1, NFR04)

A `ReachabilityEnricher` component MUST sit between `ReachabilityEngine` (producer of `ReachabilityIndex`) and `JsonReportWriter` (consumer of the model). The enricher takes raw collections (`List<Window>`, `WTG`, `ComponentSet`), the index, and metadata (manifest package, code package), and produces an immutable `ReportModel` POJO with every JSON-bound field already computed.

The `JsonReportWriter` MUST receive only the `ReportModel` as input. It MUST NOT hold a reference to `ReachabilityIndex` or invoke any `index.reachesTarget(...)` style lookup during serialization (INV-ANA-30). This decouples enrichment logic from serialization, making each independently testable and preventing god-writer regression as future enrichments (G7/G8/G9/G11 in change C3) are added.

**Module**: rvsec-gator (`client/reach/ReachabilityEnricher.java`, `client/json/ReportModel.java`, `client/json/JsonReportWriter.java`).

#### Scenario: Writer has no ReachabilityIndex dependency

- **WHEN** a static analysis check (CI gate `G_enricher_purity`) inspects `JsonReportWriter.java`
- **THEN** the file MUST NOT contain `import ...ReachabilityIndex;`
- **AND** the constructor of `JsonReportWriter` MUST NOT accept `ReachabilityIndex` as a parameter
- **AND** no method body MUST reference any `ReachabilityIndex` instance

#### Scenario: Enricher produces fully-annotated ReportModel

- **WHEN** `ReachabilityEnricher.enrich(...)` is invoked with raw collections and a populated `ReachabilityIndex`
- **THEN** the returned `ReportModel` MUST contain all per-method reachability flags resolved
- **AND** for every method `m` in `model.reachability`, `m.reachesTarget == index.reachesTarget(soot(m))`
- **AND** the model MUST be deep-immutable (final fields, no setters)

### Requirement: Mutex CLI for Target Source Selection (FR04)

The `rv-static-analysis` CLI MUST expose `--mop-dir PATH` and `--targets-file PATH` as mutually exclusive options. Exactly one of the two MUST be specified on every invocation. The mutex is enforced via `argparse.add_mutually_exclusive_group(required=True)` (INV-ANA-33).

**Module**: rv-static-analysis (`src/rv_static_analysis/__main__.py`, `src/rv_static_analysis/config.py`).

#### Scenario: Both flags passed simultaneously

- **WHEN** the user runs `rv-static-analysis --mop-dir /m --targets-file /t cryptoapp.apk`
- **THEN** argparse MUST emit an error containing `--mop-dir` and `--targets-file` to stderr
- **AND** the process MUST exit with code 2 (argparse default error code) without launching GATOR

#### Scenario: Neither flag passed

- **WHEN** the user runs `rv-static-analysis cryptoapp.apk`
- **THEN** argparse MUST emit an error indicating one of the two flags is required
- **AND** the process MUST exit with code 2

#### Scenario: Only --mop-dir passed

- **WHEN** the user runs `rv-static-analysis --mop-dir /m cryptoapp.apk`
- **THEN** argparse MUST accept the invocation
- **AND** `RVStaticAnalysisConfig.target_source` MUST be `("mop_dir", "/m")` (or equivalent representation)

#### Scenario: Only --targets-file passed

- **WHEN** the user runs `rv-static-analysis --targets-file /t cryptoapp.apk`
- **THEN** argparse MUST accept the invocation
- **AND** the GATOR command MUST include `-clientParam targetsFile=/t`

### Requirement: Shared Jimple Helpers (P1)

GATOR analysis code duplicates a small Jimple-expression resolution layer (`definitionRhs`, `resolveInt`, `resolveStr`) across `MenuExtractor` and `SpinnerItemExtractor`. The duplication is mechanical and load-bearing for menu / spinner static extraction. A single `presto.android.util.JimpleDefUtils` class MUST host the canonical implementation; both extractors MUST call it. New consumers of Jimple definition resolution MUST use the helper class.

**Module**: rvsec-gator (`sootandroid/src/main/java/presto/android/util/JimpleDefUtils.java`, `client/src/main/java/presto/android/gui/clients/menu/MenuExtractor.java`, `client/src/main/java/presto/android/gui/clients/spinner/SpinnerItemExtractor.java`).

#### Scenario: JimpleDefUtils is the single Jimple-def resolution layer

- **WHEN** any GATOR component needs to resolve the RHS of a local assignment, an integer literal, or a string literal in Jimple
- **THEN** it MUST call `JimpleDefUtils.definitionRhs(...)`, `JimpleDefUtils.resolveInt(...)`, or `JimpleDefUtils.resolveStr(...)` (INV-ANA-38)
- **AND** no other class MUST contain a private copy of these helpers

### Requirement: Call Graph Algorithm CLI Exposure (FR04)

The `rv-static-analysis` CLI MUST expose `--cg-algorithm {spark,cha,rta,vta}` (default `spark`) and forward it to GATOR as `-cgAlgorithm <value>`. SPARK remains the operational default (full points-to analysis, validated in gh57 sweep); the alternatives exist because Soot supports them and they are useful for experiments comparing reachability precision. This flag is mechanical CLI plumbing — it does not introduce new analysis behavior beyond what Soot already provides.

**Module**: rv-static-analysis (`src/rv_static_analysis/__main__.py`, `src/rv_static_analysis/config.py`).

#### Scenario: --cg-algorithm forwards to GATOR

- **WHEN** the user runs `rv-static-analysis --mop-dir /m --cg-algorithm cha cryptoapp.apk`
- **THEN** the assembled GATOR command MUST include `-cgAlgorithm cha`
- **AND** `RVStaticAnalysisConfig.cg_algorithm` MUST be `"cha"`

#### Scenario: --cg-algorithm rejects invalid values

- **WHEN** the user runs `rv-static-analysis --cg-algorithm bogus --mop-dir /m cryptoapp.apk`
- **THEN** argparse MUST reject the invocation with a `choices` error listing `spark`, `cha`, `rta`, `vta`
- **AND** the process MUST exit with code 2

#### Scenario: Default --cg-algorithm is spark

- **WHEN** the user omits `--cg-algorithm`
- **THEN** the GATOR command MUST include `-cgAlgorithm spark`

## Invariants

- **INV-ANA-30**: `JsonReportWriter` MUST NOT hold a reference to `ReachabilityIndex` or invoke any reachability lookup during serialization. All reachability flags emitted in the JSON are read from `ReportModel` fields populated upstream by `ReachabilityEnricher`.
- **INV-ANA-31**: The JSON output of a successful (non-truncated) GATOR run MUST end with the literal field `"complete": true` as the final top-level field. Truncated outputs MUST NOT contain this field.
- **INV-ANA-32**: The set of values declared in `JsonSchema.Keys` (Java) MUST equal the set of values in `_JK` (Python). Verified by `tests/parity/json_keys.py` in CI.
- **INV-ANA-33**: The `rv-static-analysis` CLI MUST require exactly one of `--mop-dir` or `--targets-file`. Both or neither MUST cause the process to exit with a non-zero code before GATOR launches.
- **INV-ANA-34**: `SignatureFileTargetSource` MUST tolerate blank lines and `#` comments. Other malformed content MUST raise `IllegalArgumentException` with line number.
- **INV-ANA-35**: `MopSpecsTargetSource.load()` MUST produce a `Set<TargetMethod>` whose cardinality and `(className, methodName)` pairs equal those produced by the historical `loadMopSignatures()` on the same `mopDir`. For `cryptoapp.mop`, this set has exactly 16 entries (gh57 baseline `b2e04a26`).
- **INV-ANA-36**: `MatchPolicy` is an attribute of the source / target, never a CLI-level override. No `--match-mode` or equivalent flag exists.
- **INV-ANA-37**: After C1f rename, the monorepo MUST NOT contain references to the legacy field names `reachesMop`, `directlyReachesMop`, `mopMethods`, `handlerReachesMop`, `handlerDirectlyReachesMop`, `reaches_mop`, `directly_reaches_mop`, `handler_reaches_mop`, `handler_directly_reaches_mop`, `target_reaches_mop`, `cov_reaches_mop`, `mop_methods` (Pydantic field), or the class name `MopMethod` outside of these documented exclusions: `MopSpecsTargetSource.java`, CLI flag `--mop-dir`, config attribute `mop_dir`, published CSVs under `results/` and `experimento-*/`, archived OpenSpec deltas, historical commit messages, and `modules/rv-agent/` (deprecated per CLAUDE.md — excluded by directory). The gate MUST scan `rvsec-gator/`, `modules/` (minus `rv-agent/`), and `scripts/`. Verified by `G_no_legacy_mop` CI gate.
- **INV-ANA-38**: GATOR Jimple definition-resolution helpers (`definitionRhs`, `resolveInt`, `resolveStr`) MUST live in `presto.android.util.JimpleDefUtils` only. `MenuExtractor`, `SpinnerItemExtractor`, and any future consumer MUST call them via the helper class.

## Data Contracts

### Input

- `--mop-dir PATH` — directory containing JavaMOP `.mop` specs (from CLI; consumed by `MopSpecsTargetSource`).
- `--targets-file PATH` — text file of Soot signatures, one per line, `#` comments allowed (from CLI; consumed by `SignatureFileTargetSource`).
- `--cg-algorithm {spark,cha,rta,vta}` — Soot call graph algorithm (from CLI; default `spark`). Forwarded to GATOR as `-cgAlgorithm`.
- APK file path — positional argument.

### Output

- JSON file at `<output_dir>/<package>/<app>.json` with top-level fields: `manifestPackage`, `codePackage`, `mainActivity`, `reachability[]`, `windows[]`, `transitions[]`, `components{}`, `targetMethods[]`, `complete` (boolean sentinel, last).
- Python `StaticAnalysisData` Pydantic model populated by `StaticAnalysisParser` from the JSON, surfaced to `rv-coverage`, `rv-platform`, `rv-experiment`, `aperv-tool`, `scripts/`.

### Side-Effects

- **Filesystem**: writes one JSON file per APK; if ADR-4 enters (conditional G6.1), also writes `<output>.tmp` before atomic move.
- **Logging**: WARN entries for Flowgraph skips, bytecode-scan body-retrieval skips, `WidgetType` fallback to `OTHER`; INFO entries for analysis statistics.

### Error

- `StaticAnalysisException` — wraps GATOR failures (call-graph crash, missing JAR, malformed CLI).
- `IllegalArgumentException` (Java) — invalid line in targets-file.
- `argparse.ArgumentError` (Python) — mutex violation.
- `JSONDecodeError` recovered to partial data via `_recover_truncated_json`.
