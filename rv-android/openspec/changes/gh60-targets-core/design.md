## Context

This change generalizes GATOR static analysis from MOP-only reachability to a polymorphic `TargetMethodSource` abstraction and decomposes the 1625 LOC `RvsecAnalysisClient` god class. Phase-0 ideation in `docs/20260515_plano_gator_targets_generic.md` is authoritative; this document records the technical decisions that flow from it.

Cross-module: the JSON contract produced by `rvsec-gator` (Java, outside the uv workspace but versioned in the same monorepo) is consumed by `rv-static-analysis` (Python parser), which materializes Pydantic models defined in `rv-android-core`. Live consumers of those models include `rv-coverage`, `rv-platform`, `rv-experiment`, `aperv-tool`, and `scripts/`. `rv-agent` is deprecated and ignored.

Baseline gh57 commit: `b2e04a26`. Sweep 380 APKs (gh57) provides empirical ground truth that timeout is the normal regime (30-50% of large sweeps), not an exception — this shapes ADR-4 e ADR-6.

PRD references: FR04 (static analysis pipeline), FR05 (reachability data downstream), FR06 (coverage tracking), FR33-FR37 (core domain models), NFR02 (robustez frente a timeout), NFR04 (P3 no backward compatibility).

## Architecture

```
PRODUCER SIDE (Java — rvsec-gator/client + rvsec-gator/commons + rvsec-gator/sootandroid)

  CLI args (--mop-dir OR --targets-file)
        |
        v
  +----------------------+
  | TargetMethodSource   |  <-- new (G1.2)
  +----------+-----------+
             |
   +---------+---------+
   v                   v
 MopSpecsTargetSource  SignatureFileTargetSource
  (LENIENT class+name)  (STRICT full signature)
   |                   |
   +---------+---------+
             v
       Set<TargetMethod>
             |
             v
     TargetResolver (G3.1) ---> Set<SootMethod> in Scene
             |
             v
     ReachabilityEngine (G3.2) ---> ReachabilityIndex
             |                       (reachesTargetSet, directTargetSet, lookup API)
             v
     ReachabilityEnricher (G3.2b)  <-- new (ADR-5)
             |  visitor: enrich(node) -> annotated values, invoked per-node
             |  by the writer during section walk; NO ReportModel batch.
             v
     JsonReportWriter (G3.3) ---> JSON file on disk (streaming)
             |                    one section at a time:
             |                      reachability → flush → windows → flush
             |                      → transitions → flush → components → flush
             |                      → "complete":true → close (ADR-6)
             |                    all keys via JsonSchema.Keys (ADR-7)
             v
     RvsecAnalysisClient (G3.4)  <-- orchestrator only, ~200 LOC


CONSUMER SIDE (Python — rv-static-analysis + rv-android-core + downstream)

  StaticAnalyzer.analyze(apk)
        |
        v (two-stage read if ADR-4 enters: <output> then <output>.tmp)
  +-------------------------+
  | static_analysis_parser  |
  +-----+-------------------+
        |  reads via _JK (ADR-7)
        |  checks sentinel "complete"
        v
  StaticAnalysisData (Pydantic v2 in rv-android-core)
   + Method.reaches_target          (renamed)
   + Widget.reaches_target          (renamed)
   + ComponentInfo.reaches_target   (renamed)
   + ComponentInfo.target_methods   (renamed from mop_methods)
   + WindowTransition.target_reaches_target  (@property, renamed; resolves via
                                               parser-injected window_methods_index)
   + StaticAnalysisData.complete: bool       (new — sentinel)
        |
        v
  Downstream consumers (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts)
   (mechanical rename propagated)
```

### Key Components

| Component | Responsibility | Input | Output |
|---|---|---|---|
| `presto.android.gui.clients.target.TargetMethod` (Java POJO) | Canonical representation of a method of interest | `className`, `methodName`, `params: List<String>`, `signature`, `MatchPolicy` | self |
| `presto.android.gui.clients.target.TargetMethodSource` (Java interface) | Polymorphic loading of targets | implementation-specific | `Set<TargetMethod>` |
| `MopSpecsTargetSource` | Wraps `JavamopFacade.listUsedMethods(mopDir, false)` | `mopDir: Path` | LENIENT `Set<TargetMethod>` (class+name) |
| `SignatureFileTargetSource` | Parses text file (one Soot signature per line, `#` comments) | `Path` | STRICT `Set<TargetMethod>` (full signature); wildcard `(..)` or `(*)` entries → LENIENT per entry |
| `TargetResolver` | Loads via source and resolves into Soot `Scene` | `TargetMethodSource` | `Set<SootMethod>` |
| `ReachabilityEngine` | Multi-source BFS (JGraphT) + reverse BFS + bytecode scan for direct callers | `Set<SootMethod>`, call graph | `ReachabilityIndex` |
| `ReachabilityIndex` | Encapsulated lookup ADT | `SootMethod` | `boolean reachesTarget(m)`, `boolean directlyReachesTarget(m)`, `Set<String> reachesTargetSignatures()` |
| `ReachabilityEnricher` | Visitor invoked per-node by the writer to compute per-method/per-widget/per-transition reachability flags via `ReachabilityIndex` lookups; classifies external exit; resolves dual package metadata at the top level. Stateless beyond its index/metadata references. NO batch `ReportModel` materialization. | `ReachabilityIndex` + raw node (window OR widget OR transition OR component) + app metadata | annotated key/value pairs for the writer to emit |
| `JsonReportWriter` | Streaming walker over Soot/GATOR raw collections; calls the injected `ReachabilityEnricher` per node and emits the result through `JsonSchema.Keys`; `flush()` between sections; emits `"complete":true` last, just before `close()` (after a deliberate `f.getFD().sync()` to defend against post-close write-back loss on networked FS) | raw collections, enricher, output `Path` | JSON file with `"complete": true` final |
| `JsonSchema.Keys` (Java) | `public static final String REACHES_TARGET = "reachesTarget";` ~45 entradas. Reflected by `JsonSchemaKeysDump` for parity testing. | — | string constants |
| `JsonSchemaKeysDump` (Java main class) | Reflection helper invoked by Python parity test via subprocess; prints each `Keys.*` value on its own line | — | stdout listing of all key values |
| `JimpleDefUtils` (Java) | Shared `definitionRhs` / `resolveInt` / `resolveStr` Jimple helpers (INV-ANA-38); consumed by `MenuExtractor` and `SpinnerItemExtractor` | `Unit`, `Local` | resolved RHS |
| `RvsecAnalysisClient` (post-decomposition) | Orchestrator; ~200 LOC | CLI args | wires the pipeline |
| `rv_static_analysis.parser.static.static_analysis_parser._JK` (Python) | `SimpleNamespace(reaches_target="reachesTarget", ...)` mirror of `JsonSchema.Keys` | — | string constants |
| `StaticAnalysisParser.parse_json` | Reads JSON via `_JK`, populates Pydantic models, propagates `complete` flag | JSON `Path` | `StaticAnalysisData` |
| `StaticAnalyzer.analyze` (existing, modified) | Two-stage read if ADR-4 enters: `<output>` then `<output>.tmp` | APK | `StaticAnalysisData` with `complete: bool` |
| `rv_static_analysis.__main__:cli` (Python) | Adds `--targets-file PATH` mutex with `--mop-dir`; exposes `--cg-algorithm` (G5.8) | argv | parsed `Namespace` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|---|---|---|
| FR04 (static analysis pipeline supports multiple target sources) | `TargetMethodSource`, `MopSpecsTargetSource`, `SignatureFileTargetSource`, `TargetResolver` | `TargetMethodSourceTest.java`, `tests/analysis/test_targets_file_cli.py` |
| FR04 (CLI `--cg-algorithm` exposure) | `rv_static_analysis.__main__` + `config.py` | `tests/cli/test_cg_algorithm.py` |
| FR05 (reachability data emitted under stable, generic field names) | `JsonReportWriter` via `JsonSchema.Keys`; parser via `_JK` | `tests/parity/json_keys.py`, `tests/parity/reachability.py` |
| FR06 (coverage tracking uses renamed attribute) | `rv-coverage` CSV header + Python attr | `tests/rv_coverage/test_csv_schema.py` |
| FR33-FR37 (core Pydantic field rename) | `rv_android_core.domain.classes.Method.reaches_target`, idem `Widget`, `ComponentInfo` (incl. `target_methods`), `WidgetEvent`, `WindowTransition.target_reaches_target` (`@property` resolved via parser-injected `window_methods_index`) | `tests/domain/test_classes.py`, `test_widget.py`, `test_components.py`, `test_wtg.py` |
| NFR02 (robust against timeout, parser tolerance preserved + sentinel) | `complete` field; streaming flush per section in `JsonReportWriter`; parser default-False for new fields | `tests/parser/test_sentinel.py`, `tests/parser/test_truncated_recovery.py` |
| NFR04 (P3 no backward compat) | atomic rename, no shims | `tests/parity/no_legacy_mop.py` (CI gate) |
| INV-ANA-30 (writer holds no direct `ReachabilityIndex` reference) | `JsonReportWriter` accepts only raw collections + injected enricher (which itself holds the index) | `JsonReportWriterPurityTest.java` (AST/reflection inspection) |
| INV-ANA-31 (sentinel always emitted on success) | last `out.append` em `JsonReportWriter.write`, after `fsync` | `SentinelEmissionTest.java` (uses `--inject-failure-after-section` harness, not `kill JVM`) |
| INV-ANA-32 (Java↔Python key set parity) | `JsonSchema.Keys` ↔ `_JK` via reflection dumper | `tests/parity/json_keys.py` (subprocess to `JsonSchemaKeysDump`) |
| INV-ANA-33 (CLI mutex `--mop-dir` ⊕ `--targets-file`) | `argparse.add_mutually_exclusive_group(required=True)` | `tests/cli/test_mutex.py` |
| INV-ANA-34 (signature-file parser tolerates `#` comments, blank lines, wildcards) | `SignatureFileTargetSource.parse` | `SignatureFileTargetSourceTest.java` |
| INV-ANA-35 (MopSpecsTargetSource preserva baseline byte-for-byte) | `MopSpecsTargetSource.load` ⇒ `loadMopSignatures` antigo | `MopSpecsParityTest.java` |
| INV-ANA-36 (MatchPolicy is not a CLI flag) | `RVStaticAnalysisConfig` carries `target_source` only; no `--match-mode` action registered | `tests/cli/test_no_match_mode_flag.py` |
| INV-ANA-37 (no legacy MOP refs post-rename) | atomic rename across 41 files / 266 occurrences | `tests/parity/no_legacy_mop.py` (gate `G_no_legacy_mop`, excludes `modules/rv-agent/`) |
| INV-ANA-38 (Jimple helpers single class) | `presto.android.util.JimpleDefUtils` | `JimpleDefUtilsTest.java` + grep audit in extractor sources |
| INV-CORE-33 (no `_mop`/`mop_methods` fields) | atomic rename in `rv-android-core` Pydantic models | `tests/domain/test_no_legacy_mop_fields.py` (AST inspection) |
| INV-CORE-34 (`target_reaches_target` is `@property`, not stored) | `@property` decorator in `WindowTransition` | `tests/domain/test_wtg.py::test_target_reaches_target_is_property` (`isinstance(..., property)`) |
| S5 (malformed targets-file line) | `SignatureFileTargetSource.parse` raises `IllegalArgumentException` with line number | `SignatureFileTargetSourceTest.java::malformedLine` |
| S14 (bytecode-scan resilience on corrupted bodies) | `ReachabilityEngine.bytecodeScan` try/catch + WARN log + `bodies_skipped` counter | `BytecodeScanResilienceTest.java` |
| S15 (bytecode-scan scope = appClasses) | `ReachabilityEngine.bytecodeScan` iterates `appClasses` only | `BytecodeScanScopeTest.java` |

## Goals / Non-Goals

**Goals:**

- Polymorphic target loading without a global matching-policy flag.
- Decompose the god class into independently testable components (TargetResolver, ReachabilityEngine, ReachabilityIndex, ReachabilityEnricher, JsonReportWriter).
- Pure writer — no runtime lookup; every enrichment decision lives in `ReachabilityEnricher`.
- Sentinel `complete=true` to distinguish truncation from corruption without atomic-write cost.
- Mirrored JSON constants (Java + Python) eliminate an entire class of drift bugs.
- Atomic MOP→Target rename end-to-end (BREAKING; sweep regenerates).
- Enable the external use case (`--targets-file` for SQLi/MASVS audits), with `aperv-tool` as the concrete subscriber for the new workflow surface (rename mechanical even though aperv-tool has no current reachability-flag reads).

**Non-Goals (deferred to follow-up changes C2 and C3 — required to complete the static analyzer overhaul):**

- **Deferred to C2 (`gh<N+1>-hardening-package`):** G6.2 `resolveStringReference` cache; G6.3 `findOnCreateOptionsMenu` superclass walk; G6.4 `<integer-array>`/`<array>` handling; G6.5a-b expanded dead code removal (NOT G6.5c — `buildCallGraphLegacy` has a live caller; see Resolved Decisions); G6.6 `WidgetType.from_class_name` fallback warn; G11 dual package emission; G5.7 README sync.
- **Deferred to C3 (`gh<N+2>-agent-enrichment`):** G7 `handlerReachesTarget` per widget listener (annotation in `ReachabilityEnricher`); G8.1 same per transition event with the per-event aggregate (renamed in D10 to `transition_reaches_target_aggregate` to avoid collision); G9 external-exit marking (`externalExit`/`exitKind`); G12 Python parser full `EventType` coverage.
- **Out of scope permanently (no follow-up change planned):** Compose/Flutter support (the `EventType` enum stays closed); standalone GATOR distribution (uber-jar, external README, Maven Central — a future change after the thesis if real publication intent emerges); JSON schema versioning (explicitly forbidden by P3).

The 3-change sequence (C1=gh60, C2, C3) was decided in Phase-0 §9 as convergent multi-LLM recommendation. The static analyzer overhaul completes only after C2 and C3 merge.

## Decisions

### D1 — `TargetMethodSource` is an interface, not an abstract class

Java interface with a single method `Set<TargetMethod> load()`. Allows lambda implementations in tests; no shared state that would justify inheritance.

**Rejected alternative:** abstract class with `loadInternal()`. Would add state without benefit; LENIENT vs STRICT is the responsibility of the source itself (ADR-3), not of the hierarchy.

### D2 — Matching policy is polymorphic behavior of the source (ADR-3)

`MopSpecsTargetSource` resolves LENIENT (class+name) because `.mop` specs use AspectJ wildcards (`init(int, Certificate, ..)`) where the full signature is semantically undefined at the origin. `SignatureFileTargetSource` resolves STRICT (full Soot signature) because the file author controls precision.

**Rejected alternative:** global CLI flag `--match-mode`. Forcing MOP to strict breaks the AspectJ contract; forcing file to lenient confuses the user who wrote a complete signature. Policy is semantics of the source, not preference.

**Per-entry wildcard in the targets-file:** a line containing `(..)` or `(*)` resolves LENIENT for that entry only. Syntax aligned with AspectJ; both tokens accepted as synonyms.

### D3 — `ReachabilityEnricher` as injected visitor, no batch `ReportModel` (ADR-5, revision 2 2026-05-25)

Original multi-LLM convergence (Claude Opus 4.7, Codex GPT-5, Gemini 2.5 Pro): god-writer risk if `JsonReportWriter` looked up `ReachabilityIndex` at serialization runtime. First solution (revision 1): `ReachabilityEnricher` produced a fully-annotated `ReportModel` POJO in batch; writer was a pure walker over the POJO.

**Revision 2 (2026-05-25, post Gemini 2.5 Pro F01):** materializing the full report into `ReportModel` before serialization **destroys section-level `flush()`** which today preserves partial recovery under timeout (the normal regime: 30-50% of large sweeps per gh57 ground truth). For APKs with 10k+ methods × 100+ widgets × 50+ transitions, the in-memory POJO consumes unnecessary intermediate heap and negates the invariant "the partial JSON is parseable up to the last flushed section".

**Adopted solution:** `ReachabilityEnricher` is a stateless visitor (beyond holding `ReachabilityIndex` + app metadata) with methods `enrichMethod(SootMethod) → Map`, `enrichWidget(Widget) → Map`, `enrichTransition(Transition) → Map`, `enrichComponent(Component) → Map`. `JsonReportWriter` receives `(enricher, rawCollections, output)`, iterates one section at a time, calls the enricher per node, emits via `JsonSchema.Keys`, **flushes** between sections. The writer never calls `ReachabilityIndex` directly (INV-ANA-30 honored via enricher delegation); the enricher is independently testable; partial recovery is preserved.

**Accepted trade-off:** writer + enricher coupled by interface (not by intermediate POJO); ~5 extra calls per method/widget/transition compared to the batch design.

**Gain:** zero OOM risk on large APKs; incremental flush preserved; sentinel remains the final write after all sections flush; enricher stays mockable (inject a fake returning `Map.of(...)`).

### D4 — Sentinela `"complete": true` (ADR-6)

Last top-level field in the JSON; emitted only after all sections complete successfully and after `f.getFD().sync()`. Parser checks: absent or `false` ⇒ truncated sample. Cost: ~5 LOC writer + ~3 LOC parser. Covers the dominant case (timeout interrupts writer mid-stream); set-comparison gates filter `complete=false` samples to avoid flakiness.

**Durability reinforcement:** the `fsync` before `close()` defends against NFS/cifs scenarios where the page cache reorders writes — without it, a crash between the sentinel write and directory flush can produce a file that looks complete but lacks the sentinel on disk. Cost: 1 syscall per analysis.

**Rejected alternative:** schema versioning. Already forbidden by P3 — post-merge sweep regenerates everything.

**Rejected alternative:** atomic write as the single solution (ADR-4 standalone). Pure atomic destroys partial recovery (timeout → orphan `.tmp` → parser has no data). The sentinel is Pareto-superior for truncation.

### D5 — Mirrored JSON constants with reflection parity (ADR-7, revision 2 2026-05-25)

`presto.android.gui.clients.json.JsonSchema.Keys` (Java) + `rv_static_analysis.parser.static.static_analysis_parser._JK` (Python `SimpleNamespace`). Test parity `tests/parity/json_keys.py` valida `set(Java.values) == set(Python.values)`.

**Revision 2 (post multi-LLM analysis Claude/Codex/Gemini/DeepSeek):** rejected regex extraction `final String X = "Y"` from `.java` (fragile against multi-line Javadoc, annotations, concatenation). Adopted **reflection-based dumper**: Java class `JsonSchemaKeysDump` whose `main()` iterates `JsonSchema.Keys.class.getDeclaredFields()`, filters `Modifier::isStatic`, prints each value on its own line; the Python test invokes via `subprocess.run(["java", "-cp", "...", "presto.android.gui.clients.json.JsonSchemaKeysDump"])` and compares against `set(_JK.__dict__.values())`. Cost: +1 Java class of ~12 LOC, +5 LOC subprocess in the test; gain: zero textual fragility.

**Rejected alternative:** code generation from a shared YAML. Violates P1 — two manual constants fit in 50 + 10 LOC and are easier to review than a generation pipeline.

### D6 — Atomic MOP→Target rename (ADR-1 revoked)

Revision 2: complete rename in a single per-module C1f commit. Earlier version (preserve names) was revoked after multi-LLM convergence identified zero cost (post-merge sweep regenerates; deprecated rv-agent breaks but is not a live consumer) and real cognitive cost (the name `reachesMop` is hostile in a `--targets-file PATH` audit context).

**Real surface (empirical grep 2026-05-25):**

| Category | Files | Occurrences |
|---|---:|---:|
| Java (1 src + 6 tests) under `rvsec-gator/client/` | 7 | 108 |
| Python src under `modules/` (excl. `rv-agent/`, `backup/`, `tests/`) | 12 | 158 |
| Python tests under `modules/` (excl. `rv-agent/`, `backup/`) | 15 | — |
| Scripts under `scripts/` | 7 | — |
| `aperv-tool` (target consumer of this change, no current reads) | 0 | 0 |
| **Total surface** | **41 files** | **266+** |

Includes `ComponentInfo.mop_methods: List[str]` at `domain/components.py:49` → `target_methods` (missed by the original design — corrected here). Includes all Java tests under `client/src/test/java/...` (`BytecodeScanMatchTest`, `BaselineComparisonIT`, `MopSignatureLoaderTest`, `RvsecAnalysisClientIT`, `JsonOutputTest`, `ReachabilityBfsTest`) — renamed together with production.

**Preserved (not renamed):** `--mop-dir` CLI flag, `mop_dir` config attr, class `MopSpecsTargetSource`. These names describe the **source** (JavaMOP specs), not the generalized concept.

**Excluded by policy:** `modules/rv-agent/` (deprecated per CLAUDE.md + memory). The `G_no_legacy_mop` gate excludes this directory explicitly; rv-agent retains the legacy names until eventual removal of the whole module (out of scope).

### D7 — Bytecode-scan policy contract (new, 2026-05-25)

`findDirectTargetCallersByBytecodeScan` (renamed in C1f) operates **outside** the SPARK call graph, walking `Body.getUnits()` and matching `InvokeExpr.getMethodRef()` against `(declaringClass.getName(), methodRef.name())` — historically a LENIENT (class+name) comparison. This behavior is load-bearing for BUG-INV-ANA-19 (apps that invoke `SecureRandom` / `javax.crypto.*` but whose edges SPARK drops).

**Explicit contract introduced by gh60:** the scanner consumes a `Set<String>` precomputed from `ReachabilityIndex.reachesTargetSignatures()` — **independent of the source's `MatchPolicy`**. Rationale: bytecode literal-match is LENIENT by construction (the JVM resolves by name+descriptor; the scanner has no cheap access to the full signature of the call site). For a STRICT source (`SignatureFileTargetSource`), the scanner still fires on any call with matching class+name — this is **deliberately conservative**: the scanner may produce false positives on parameter mismatch but never false negatives.

**Implication:** `directlyReachesTarget` for a STRICT source can be a strict superset of "methods whose call site fully signature-matches". `--targets-file` users must be aware. Documented in `specs/analysis/spec.md` (Scenario `directlyReachesTarget detects literal library invocations`) and in the CLI `--targets-file` help text.

### D8 — `--cg-algorithm` lives in C1, not C2 (new, 2026-05-25)

Phase-0 left `--cg-algorithm` ambiguous (mechanical C1 plumbing vs C2 hardening). Decision for gh60: **lives in C1** because it is pure CLI plumbing → `-cgAlgorithm` (Soot already implements CHA/RTA/VTA; no new analysis code). Cost: +1 argparse argument, +1 field in `RVStaticAnalysisConfig`, +1 line in the assembled GATOR command, +3 tests. Holding it back to C2 would force a second change just for a flag, violating P1.

### D9 — Atomic write CONDITIONAL (ADR-4 enters or not per Phase 1) → **VERDICT: DROPPED (2026-05-25)**

The sentinel covers truncation. Atomic write only adds value if gh57 had real corruption (junk bytes). Phase 1 task-zero: classify 2-3 gh57 failures as corruption vs truncation.

- Truncation dominates → C1h does not exist.
- Real corruption → C1h enters with `<output>.tmp` + `Files.move(ATOMIC_MOVE)` + parser two-stage read (`<output>` or `<output>.tmp`). No non-atomic fallback if the filesystem does not support it — halt with error (fallback would be a P3 shim).

**Empirical verdict (task 0.1-0.3, executed 2026-05-25):**

Classification script (`python -c` over `out/sweep_jca400_v1/*/*.json`, excluding `mop_signatures.json` / `analysis_signatures.json`):

| Bucket | Count | Share |
|---|---|---|
| Parses cleanly (`json.loads` succeeds first try) | 826 / 826 | 100.0% |
| Truncation-recoverable (parses only after `_recover_truncated_json` bracket fix) | 0 / 826 | 0.0% |
| Corruption-unrecoverable (junk bytes / no closing bracket / recovery fails) | 0 / 826 | 0.0% |

Of the 826 valid JSONs, **651 (78.8%) have empty `windows[]` and `transitions[]`** — these are the cases the gh51-D5 *write-first-JSON* strategy intercepts: `RvsecAnalysisClient` writes the JSON with empty sections **before** entering the WTG build, then the timeout kills the JVM mid-WTG. The on-disk file is therefore fully written and fully valid; the data sections are simply empty (consistent with `docs/20260513_gator_analise_wtg.md` finding of 71.6% empty-WTG rate on the post-instr `APKS_FINAL_JCA_DEXLIB` corpus).

This is a third category neither D9 nor ADR-4 anticipated: **"complete-and-empty"** (not truncation, not corruption — a valid JSON with empty arrays). Atomic write defends against zero observed failures: there is no `.tmp` orphan scenario in the sweep data, no junk-bytes scenario, no parser unable to reach the closing brace. The sentinel `"complete": true` (ADR-6) remains the right defense — it lets consumers distinguish "complete with empty data" (timeout reached WTG but write happened first) from "incomplete because writer itself died" (would emit no sentinel).

**Decision:** **C1h DROPPED**. Task 0.4 commits this verdict. Group 8 in `tasks.md` is removed entirely (per ADR-3 atomic match policy and CLAUDE.md P3 no-shim). The `<inject-failure-after-section>` harness flag remains in scope for `SentinelEmissionTest` (task 5.9) — that flag tests the sentinel, not atomic write.

**Residual risk acknowledged:** if a future sweep on a different filesystem (NFS, FUSE, networked storage) produces real corruption, the decision should be revisited as a separate change. The Phase-0 §6 ADR-4 footnote is updated to record the empirical basis.

### D10 — Rename aggregate `targetReachesTarget` (C3) to avoid collision (new, 2026-05-25)

Semantic collision identified by Claude F27: original `proposal.md` used "targetReachesTarget" for the per-transition aggregate (C3 scope, sum of handler reachabilities), while `specs/core/spec.md` introduces `target_reaches_target` as a `@property` on `WindowTransition` (gh60 scope, derived from the target window). Two different things with the same name.

**Decision:** gh60 keeps `target_reaches_target` (window-level, `@property`). When C3 lands it will adopt the name `transition_reaches_target_aggregate` for the per-event aggregate. Convention recorded here so the C3 author does not recreate the collision.

### D11 — `enrichFromElement` covers `android:hint` and `android:text` inline literals (post-merge gap, 2026-05-26)

Discovered after the gh60 smoke run on cryptoapp: the produced JSON had 0/51 widgets populated for `hint` and `text` despite the source layouts declaring 4 `android:hint` and 17 `android:text` attributes. The bug is a dual-path coverage gap inherited from gh57 — not introduced by gh60, but exposed by the gh60 validation regime:

- **Path A (`collectWidgets`, `RvsecAnalysisClient.java:917-921`)** seeds `widget["text"]` and `widget["hint"]` from `PropertyManager.getTextsOrTitlesOfView` / `getHintOfView`. PropertyManager only sees strings reached via the Soot call graph (programmatic `setText`/`setHint`) and `@string/` references — it does NOT walk layout XML for inline literals.
- **Path B (`enrichFromElement`, lines 1080-1114, introduced by gh57)** reads attributes directly from the decoded layout XML, but its initial scope was `inputType`, `entries`, `prompt`, `spinnerMode`, `contentDescription`, `tooltipText`. `hint`/`text` were never wired in.

**Consequence on the corpus:** any app that declares hint/text as inline literals (not via `@string/`) ends up with empty hint/text. Cryptoapp is one such app; the JCA-400 sweep almost certainly has many more.

**Decision:** extend `enrichFromElement` with two `putStringAttr` calls for `android:hint` and `android:text`, immediately after the existing `tooltipText` call. `putStringAttr` already short-circuits on null/empty raw input, so the Path-A seed survives when the XML carries no inline literal. Idempotent against the gh57 attribute pass.

**Why this is gh60 scope (not a follow-up):** the writer surface, widget enrichment plumbing, and the JSON contract for these fields are all governed by `specs/analysis/spec.md` already modified by this change. The previous validation only cross-checked the new gh57 attributes vs source XML, never hint/text — that validation gap is also closed by Group 11 (the smoke step now counts hint/text occurrences against the source XML declarations).

**Why the validation passed pre-merge:** `BaselineComparisonIT` and `G_widget_reachability` (deferred to C2/C3) do not assert hint/text dimensions; the gh57 add-on tests pinned only inputType/entries/prompt/spinnerMode/contentDescription/tooltipText. Lesson — register `G_widget_xml_hint_text` for the C2 hardening package so future regressions surface during PR review, not after merge.

**Out of scope (registered, not fixed here):** any other PropertyManager-only fallthroughs for non-XML programmatic state. If observed in the JCA-400 sweep, opened as separate issue.

### D12 — Reachability parity gates were bypassed by cached `LENIENT_OUTPUT` + stale baseline (post-merge investigation, 2026-05-26)

Triggered by the D11 investigation. After rebuilding `lib/gator/rvsec-analysis-client.jar` from current sources, the freshly-generated cryptoapp output diverged sharply from the in-tree baseline at `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`: `directlyReachesTarget=21` matched, but `reachable` dropped 67→55 (−12) and `reachesTarget` 61→32 (−29), losing core app methods (`MainActivity.onCreate`, all Activity.onCreate variants, `CryptographyActivity.{validateInputs,initializeViews,setupTabLayout,...}`, 4× `databinding.*Binding.inflate`).

**Instinctive read: "gh60 broke reachability."** Bisect with `git worktree add /tmp/gator_bisect b2e04a26` (pre-gh60 baseline commit) + rebuild + smoke disproved that: the b2e04a26 jar produces the exact same 55/32/21 as HEAD. Engine internal counts (`Reachable: 1766, reachesMop: 124, directlyReachesMop: 22`) are byte-equivalent between pre-gh60 and HEAD.

**Real root cause:** the divergence is between (a) in-tree baseline content frozen at `4a8a6342 feat(gh45)` (2026-03-31) — *before* `860f00ee feat(gh51): flip default -cgAlgorithm cha → spark` landed; and (b) the current build, running with spark default. SPARK is points-to pointer-analysis (more precise, smaller reachable closure); CHA is class-hierarchy (more permissive, larger closure). The 67→55 / 61→32 drop is the *intended* precision improvement of gh51 D5. It was never propagated to the in-tree fixture.

**How the gate masked this for two months:**
- `tests/parity/test_reachability_parity.py::_ensure_fresh_lenient_output` reuses `/tmp/gh60_g_subset/lenient.json` whenever the file exists with `st_size > 0`, with no `mtime(jar)` vs `mtime(cache)` check.
- The `.m2` snapshot of `rvsec-gator-sootandroid` was last built from sources predating gh51 (per `066694da chore: bump 0.8.0→0.9.0-SNAPSHOT` 2024 era). Until somebody ran `mvn install -am` against the gator source, the cached jar carried cha-default behavior.
- Result: cache and baseline both reflected the *same pre-gh51 era*. Set-equality between them held, gate reported PASS, no human ever saw a divergence — until a fresh build invalidated both sides at once.
- `pytest.skip` when `RVSEC_HOME` is unset compounds the issue: a minimal-env CI run reports 4 tests "passed" while executing zero behavior.

**Decision (Group 11 tasks 11.7-11.11):**
1. Shared helper `tests/parity/_lenient_cache.py::ensure_fresh_lenient` deletes `/tmp/gh60_g_subset/lenient.json` when older than `lib/gator/rvsec-analysis-client.jar`. Applied to `test_reachability_parity.py`, `test_sentinel_emission.py`, `test_signature_file_subset.py`, `scripts/check_signature_file_subset.py`.
2. Regenerate the in-tree baseline with the current jar (spark default + current schema with `components`/`complete`/`targetMethods`). Diff vs old baseline MUST be fully explained by: cha→spark precision improvement (gh51 D5), gh57 schema additions, C1f key rename. Anything else is a regression to investigate before committing.
3. Add `tests/parity/test_baseline_freshness.py` with two tripwires — schema currency check + `mtime(baseline) ≥ mtime(jar)` — so a future divergence between baseline and producer surfaces at PR time, not months later.
4. Introduce `RV_GATOR_REQUIRED=1` env-var contract — when set, gates that currently `pytest.skip` MUST `pytest.fail`. Catches the silent-skip regime.
5. Cross-check the regenerated baseline's method-name set against the historical static-analysis at `/home/pedro/desenvolvimento/RV_ANDROID/ALL_METHODS/cryptoapp.apk.methods` (pre-gh27 toolchain) — independent evidence that the new baseline isn't structurally missing app methods.

**Out of scope (follow-up):** multi-APK baseline (cryptoapp is a 16-class toy; Compose/R8/lambda-heavy apps need separate fixtures); sweep gate execution on the full 380-APK corpus (Group 9.3/9.4). `modules/rv-agent/` fixtures NEVER touched per CLAUDE.md deprecation policy.

### D13 — `parseArraysXml` covers all three array tag kinds (G6.4 pulled forward from C2, 2026-05-26)

`parseArraysXml` historically called `doc.getElementsByTagName("string-array")` exclusively — `<integer-array>` and `<array>` resource forms were ignored. Any `android:entries="@array/foo"` reference where `foo` was declared as `<integer-array>` (numeric pickers, color palettes, ID lists) or `<array>` (mixed @drawable/@string/@dimen items) silently produced `entries=[]` in the JSON. The agent's spinner-selection logic then saw an empty inventory and skipped those widgets — a quiet false-negative in UI exploration coverage.

The original scope decision (proposal.md §Follow-up Changes) put this in C2 alongside other hardening items (cache, menu superclass walk, dead code expansion). Two arguments for pulling it forward into gh60:

1. **Same-file precedent.** Group 11 already pulled the hint/text fix from "out of scope" into gh60 under the rationale "we are already in this file". The same logic applies: `parseArraysXml` lives in `RvsecAnalysisClient.java` immediately below the `enrichFromElement` Group 11 touched. The patch is ≤5 LOC: replace one `getElementsByTagName` call with a loop over three tag names.

2. **Trivial test coverage.** `XmlInputTypeTest` already exercises `parseArraysXml` for `string-array` (`testParseArraysXmlPlainItems`, `testParseArraysXmlWithStringRefs`). Mirroring three more cases (`integer-array`, generic `array`, all-three-coexist) is mechanical and follows the existing fixture pattern.

Implementation: keep the existing per-item handling (text content + `@string/` resolution) verbatim — `<integer-array>` items are stringified naturally (`"42"`), `<array>` items pass through verbatim or via `@string/` if applicable, downstream consumer (`widget.entries: List<String>`) is unaffected.

**Cryptoapp baseline impact: none — but for a non-obvious reason.** The cryptoapp source XML at `examples/cryptoapp/app/src/main/res/values/arrays.xml` declares `<array name="messageDigestAlgorithms">` (generic `<array>`, NOT `<string-array>`). Yet the pre-G6.4 baseline already showed the spinner's entries populated with all 13 algorithms. Investigation revealed: apktool decodes the binary APK's resource table into `<string-array>` for any array whose items are all strings — the source-XML distinction `<array>` vs `<string-array>` is lost during the build → apktool round-trip. GATOR only sees the decoded XML, never the source. So cryptoapp's `<array>` was already showing up to `parseArraysXml` as `<string-array>`.

**Empirical 30-APK sample from JCA-400 (2026-05-26):**

| Tag observed in decoded XML | APKs (n=30) | Coverage notes |
|------------------------------|-------------|----------------|
| `<string-array>` only        | 25 (83%)    | apktool normalized any source `<array>` to `<string-array>` |
| `<array>` (generic)          | 5 (17%)     | apktool preserved generic — items mix non-string types |
| `<integer-array>`            | 0 (0%)      | rare in modern Android UI resources |

The 5 generic-`<array>` cases need separate verification on whether the items are actually referenced by Spinners' `android:entries`; the ones inspected (e.g. `net.aliasvault.app_2702900.apk` has `<array name="crypto_fingerprint_fallback_prefixes" />`) are empty placeholders, so the practical coverage uplift is smaller than 17%. The fix is still worth landing because (a) the patch is ≤5 LOC, (b) unit tests pin behavior so a future apktool upgrade producing `<integer-array>` more often automatically benefits, (c) the redundancy is harmless when apktool already produced `<string-array>`.

**Decision rationale:** the G6.4 entry in the C2 hardening list assumed source-XML semantics (where the three tags are distinct) without accounting for the apktool normalization layer. The 30-APK empirical sample shows the real-world uplift is small but non-zero; given the same-file proximity and zero-cost test maintenance, pulling it forward into gh60 is justified, but the C2 author should NOT cite "fixes silently-empty spinner inventories" as motivation for the broader package — that motivation barely survives empirical scrutiny.

**Out of scope (still in C2):** G6.2 (`resolveStringReference` cache), G6.3 (`findOnCreateOptionsMenu` superclass walk), G6.5 (dead-code expansion), G6.6 (`WidgetType` drift warn log), G11 (dual `manifestPackage`/`codePackage` emission). Pulling G6.4 alone is justified by the same-file proximity; pulling everything else means re-doing the multi-LLM convergence that produced the 3-change split.

## API Design

### Java: `TargetMethodSource`

```java
public interface TargetMethodSource {
    Set<TargetMethod> load();
}

public final class TargetMethod {
    public final String className;
    public final String methodName;
    public final List<String> params;
    public final String signature;
    public final MatchPolicy policy;

    public enum MatchPolicy { LENIENT, STRICT }
}
```

**Preconditions:** none beyond constructor argument types.
**Postconditions:** `load()` returns immutable set; idempotent (cacheable).
**Errors:** `MopSpecsTargetSource.load()` raises `IllegalStateException` if `mopDir` is invalid; `SignatureFileTargetSource.load()` raises `IOException` if file is unreadable or `IllegalArgumentException` if syntax invalid (line content, not blank/comment).

### Java: `ReachabilityIndex`

```java
public final class ReachabilityIndex {
    public boolean reachesTarget(SootMethod m);
    public boolean directlyReachesTarget(SootMethod m);
    public Set<String> reachesTargetSignatures();
    public Set<String> directlyReachesTargetSignatures();
}
```

**Preconditions:** index built from a completed `ReachabilityEngine.run()`.
**Postconditions:** all lookups O(1); returned sets are immutable views.

### Java: `ReachabilityEnricher` (visitor, no `ReportModel`)

```java
public final class ReachabilityEnricher {
    public ReachabilityEnricher(ReachabilityIndex index,
                                String manifestPackage,
                                String codePackage,
                                String mainActivity);

    public Map<String, Object> enrichMethod(SootMethod m);
    public Map<String, Object> enrichWidget(Widget w);
    public Map<String, Object> enrichTransition(Transition t);
    public Map<String, Object> enrichComponent(Component c);
    public Map<String, Object> topLevelMetadata();   // manifestPackage, codePackage, mainActivity
    public Set<String> targetSignatures();           // for the targetMethods[] section
}
```

**Postconditions:** every `enrich*` call is stateless beyond constructor injection (idempotent, thread-safe by construction since `ReachabilityIndex` is read-only post-build). Returned maps contain exactly the key/value pairs that the writer will emit for that node — no further computation on the writer side.

### Java: `JsonReportWriter` (streaming)

```java
public final class JsonReportWriter {
    public JsonReportWriter(ReachabilityEnricher enricher);

    public void write(List<SootMethod> methods,
                      List<Window> windows,
                      WTG wtg,
                      ComponentSet components,
                      Path output) throws IOException;
}
```

**Behavior:** opens the file, emits top-level metadata, then for each section: iterates raw collection, calls `enricher.enrich*(node)` per item, emits the resulting key/value pairs via `JsonSchema.Keys.*`, `flush()`. After all sections flushed and before `close()`: write `,"complete":true}`, `flush()`, `f.getFD().sync()`, `close()`.

**Postconditions:** on successful completion, the file ends with `,"complete":true}` durably (fsync'd). Keys are emitted exclusively through `JsonSchema.Keys.*` constants. The writer holds zero references to `ReachabilityIndex` (verified by `JsonReportWriterPurityTest`). On any `IOException` mid-write, the file ends without the sentinel.

### Java: `JsonSchemaKeysDump` (parity helper)

```java
public final class JsonSchemaKeysDump {
    public static void main(String[] args) {
        for (Field f : JsonSchema.Keys.class.getDeclaredFields()) {
            if (Modifier.isStatic(f.getModifiers()) && f.getType() == String.class) {
                System.out.println(f.get(null));
            }
        }
    }
}
```

**Usage:** invoked from `tests/parity/json_keys.py` via `subprocess.run(["java", "-cp", "<gator-jar>", "presto.android.gui.clients.json.JsonSchemaKeysDump"], capture_output=True)`. Python parses stdout line-by-line into a set and compares against `set(_JK.__dict__.values())`.

### Python: parser via `_JK`

```python
from types import SimpleNamespace

_JK = SimpleNamespace(
    reaches_target="reachesTarget",
    directly_reaches_target="directlyReachesTarget",
    target_methods="targetMethods",
    manifest_package="manifestPackage",
    code_package="codePackage",
    complete="complete",
    # ~45 entries total
)

class StaticAnalysisData(BaseValidatedModel):
    manifest_package: str
    code_package: str
    methods: list[Method]
    windows: list[Window]
    transitions: list[WindowTransition]
    components: ComponentSet
    target_methods: list[str]
    complete: bool = False  # sentinel default for truncated samples
```

**Parser behavior:** missing key on a renamed field never falls back to legacy `*Mop` name (P3). All new fields (`reachesTarget`, `directlyReachesTarget`, `handlerReachesTarget` future, `target_methods`, `complete`) tolerate absence via Pydantic defaults to handle truncated JSON.

### Python: CLI mutex

```python
parser = argparse.ArgumentParser(...)
src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("--mop-dir", type=Path, help="JavaMOP specs directory")
src.add_argument("--targets-file", type=Path, help="Soot signatures file (one per line, '#' comments)")
parser.add_argument("--cg-algorithm", choices=["spark", "cha", "rta", "vta"], default="spark", help="Soot call graph algorithm")
```

## Data Flow

1. CLI parses `--mop-dir` xor `--targets-file` and constructs the appropriate `TargetMethodSource`.
2. `TargetResolver` loads from source, resolves each `TargetMethod` to one or more `SootMethod` instances per matching policy.
3. `ReachabilityEngine` builds JGraphT call graph, runs multi-source BFS (forward to find reaches, reverse from app entries to find direct callers), augments via bytecode scan for direct callers missed by SPARK.
4. `ReachabilityIndex` materializes `reachesTargetSet` and `directTargetSet` for O(1) lookup.
5. `ReachabilityEnricher` traverses raw windows/transitions/components, looks up each `handlerMethod` in the index, classifies external-exit transitions, resolves dual package, produces `ReportModel`.
6. `JsonReportWriter` walks the model, emits JSON using `JsonSchema.Keys` constants; emits `"complete":true` last.
7. Python `StaticAnalyzer.analyze()` reads JSON; if ADR-4 enters, two-stage read (`<output>` else `<output>.tmp`).
8. Parser populates `StaticAnalysisData` via `_JK`; downstream Pydantic models propagate to `rv-coverage`, `rv-platform`, `rv-experiment`, `aperv-tool`, `scripts/`.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| `IOException` on `SignatureFileTargetSource.load()` | invalid path or unreadable file | propagate as `RuntimeException` with file path in message | user fixes CLI argument |
| `IllegalArgumentException` (malformed signature line) | bad syntax in targets-file | propagate with line number | user fixes file |
| `IllegalStateException` (mopDir invalid) | `MopSpecsTargetSource.load()` | propagate via existing `JavamopFacade` path | user fixes `--mop-dir` |
| `TimeoutException` during analysis | external timeout enforcement | producer halts mid-stream; sentinel `complete=false` (absent) | parser yields partial `StaticAnalysisData`; downstream gates filter `complete=false` |
| `JSONDecodeError` parsing truncated output | parser | existing `_recover_truncated_json` recovery (load-bearing) | yield best-effort partial data; `complete=False` |
| `AtomicMoveNotSupportedException` (if ADR-4 enters) | filesystem without ATOMIC_MOVE | producer halts with clear message — no fallback (shim P3) | user uses local filesystem instead of NFS/cifs |
| `argparse.ArgumentError` (both `--mop-dir` and `--targets-file`) | mutex group | argparse rejects with help text | user passes exactly one |
| Pydantic `ValidationError` on renamed field | parser receives unexpected schema | propagate; do not silently fall back to legacy `*Mop` (P3) | regenerate JSON via sweep |

## Risks / Trade-offs

- **G3 decomposition introduces silent regression** → G3.0 characterization fixture (snapshot of `cryptoapp.apk.json` pre-decomposition) used as set-equivalent oracle for C1a-C1g; plus a regression suite for gh57 inherited scenarios (S7, S9, S10, S11) that validate INV-ANA-17/18 under the new decomposition.
- **OOM risk in batch `ReportModel`** → mitigated by D3 revision 2 (visitor streaming); writer flush per section preserves heap profile and partial-recovery semantics.
- **Set iteration order changes JSON byte-order cosmetically** → gates compare `set ==` per section, not byte-equivalent diff.
- **Rename breaks unmapped consumer** → empirical grep over 41 files / 266 occurrences + `G_no_legacy_mop` CI gate scans `rvsec-gator/`, `modules/` (excl. `rv-agent/`), and `scripts/`; unmapped consumer detected at gate stage.
- **God-writer risk in `JsonReportWriter`** → ADR-5 visitor delegation; `G_enricher_purity` test asserts writer has zero `ReachabilityIndex` import/reference.
- **Flaky gates by truncation** → ADR-6 sentinel filter; `G_paridade_reachability` excludes `complete=false` samples; sentinel fsync'd before close to harden against NFS/cifs writeback reorder.
- **Java↔Python key drift** → ADR-7 + reflection-based parity (D5 revision 2) eliminates regex fragility.
- **Atomic write removes partial recovery (if ADR-4 enters)** → two-stage read in parser preserves it.
- **Mutex CLI without precedent in codebase** → trivial argparse; one positive test per flag + one negative for both.
- **Bytecode-scan policy gap for STRICT sources** → D7 contract explicit: scanner is always LENIENT-by-construction; STRICT users informed via spec + CLI help text. False-positive rate documented; false-negative rate zero.
- **`JavamopFacade` may be deprecated upstream** (Phase-0 §4.3 risk catalog) → `MopSpecsTargetSource` is a thin wrapper layer; if `JavamopFacade.listUsedMethods` is removed upstream, impact is contained inside `MopSpecsTargetSource.load()` (≤30 LOC) and the rest of the pipeline stays intact. Active mitigation: if the removal happens before this change merges, replace `MopSpecsTargetSource` with a local `.mop` parser (estimated effort: 0.5 day).
- **Sentinel test flakiness via `kill JVM`** → replaced by the `--inject-failure-after-section=<name>` harness in `JsonReportWriter` (already scoped in conditional task 8.5); reuse eliminates a second flaky implementation.

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Unit (Java) | `MopSpecsTargetSource` parity vs `loadMopSignatures` baseline; `SignatureFileTargetSource` parsing (`#`, blanks, wildcards); `TargetResolver` LENIENT vs STRICT dispatch; `ReachabilityIndex` lookup O(1); `ReachabilityEnricher` annotation correctness; `JsonReportWriter` walker emits sentinel last; `JsonSchema.Keys` set integrity; `JimpleDefUtils` post-extract | JUnit 5; Mockito for Soot Scene mocks where possible | ~30 |
| Unit (Python) | Parser via `_JK`; sentinel default-False for absent key; CLI mutex; `--cg-algorithm` exposure; Pydantic field rename round-trip | pytest + Pydantic factories | ~20 |
| Integration | End-to-end `gator --mop-dir cryptoapp.mop cryptoapp.apk` vs baseline `b2e04a26`; `gator --targets-file demo.txt cryptoapp.apk` produces STRICT-subset of MOP path | run real GATOR jar on 5 canonical APKs | ~10 |
| Parity (CI gates) | In gh60 scope: `G_paridade_reachability`, `G_paridade_targets`, `G_json_keys` (reflection-based), `G_no_legacy_mop` (scans `rvsec-gator/` + `modules/` excluding `rv-agent/` + `scripts/`), `G_mutex_cli`, `G_enricher_purity`, `G_sentinela_complete`, `G_cg_algorithm_cli`, `G_jimple_def_utils`, `G_no_match_mode_flag`, `G_no_json_literals_in_writer`. Deferred (NOT executed in gh60): `G_widget_reachability`, `G_transition_reachability`, `G_dead_code_wtg`, `G_dead_code_flowgraph` (all await C2/C3). | scripts in `tests/parity/*.py` and Java tests | ~12 |
| Sweep | 380 APKs background; per-APK `|count_new - count_old| / count_old ≤ 0.05` em `reachesTarget`/`windows`/`transitions` (vs `reachesMop` baseline — set-comparison transparente ao rename) | post-merge background job | 1 sweep |

Total: ~70-90 new tests + 1 sweep gate.

## Resolved Decisions (formerly Open Questions)

All previously-open items are decided. No open question remains — implementation can proceed without further clarification.

- **Phase 1 task-zero — which 2-3 gh57 sweep APKs to investigate for corruption vs truncation?** _Decided:_ select the three APKs from `experimento-20260508/RELATORIO.md` that the relatório already flags with "JSON unparseável" (the relatório identifies them by package). _Owner:_ executor of task 0.1; the candidate list is no longer dynamic — read the relatório section "Falhas de parser" and pick the top-3 by frequency. _Closes:_ task 0.2 records the classification per APK.
- **C1h enters or not?** _Decided:_ deterministic decision rule already encoded in task 0.3 (≥2/3 truncation → DROP; ≥1/3 real corruption → ENTER). No further authorial judgment required. _Owner:_ executor of task 0.3.
- **Targets-file wildcard syntax `(..)` vs `(*)`?** _Decided:_ accept BOTH. `SignatureFileTargetSource.parse` treats either token as the LENIENT-per-entry marker (a one-line `if` covers both cases). Documented in `specs/analysis/spec.md` scenarios. Eliminates the question entirely.
- **`buildCallGraphLegacy` at `FlowgraphRebuilder.java:1036-1085` — has a live caller?** _Decided 2026-05-25:_ **YES**, called from `FlowgraphRebuilder.java:980` inside the `if (Configs.cgDelegation) { ... } else { buildCallGraphLegacy(...); }` branch. The method is NOT dead code; removing it would also require eliminating the `cgDelegation=false` branch, which is an architectural change beyond the scope of mechanical dead-code removal. _Action:_ explicitly excluded from any "dead code" gate in this change and in C2; recorded as a future-architectural item if/when the `cgDelegation` mode is reconsidered.
- **Operational threshold for `complete=true` rate** — _Decided:_ observational metric only; **hard floor of 80%** in any single sweep. If a sweep reports `complete=true` rate below 80%, the PR/run author MUST open a GitHub issue tagged `gator-regression` before merging anything that consumes that sweep's data. Encoded as a guard in task 9.4.
