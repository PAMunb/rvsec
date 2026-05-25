## Why

GitHub Issue: #60. The `RvsecAnalysisClient` in `rvsec-gator` is a 1625 LOC god class hardcoded to load `.mop` specs via `JavamopFacade`, blocking use of GATOR in non-RV-Android pipelines (papers, audits, third-party toolchains) and entangling target loading, BFS reachability, WTG extraction, and JSON writing in one module. The JSON contract leaks the term "MOP" into field names (`reachesMop`, `directlyReachesMop`, `mopMethods`) which becomes semantically hostile the moment a user loads `--targets-file` of taint sinks or auditing methods unrelated to MOP specs. Phase-0 ideation (`docs/20260515_plano_gator_targets_generic.md`) is authoritative for decisions.

## What Changes

- **Abstract target source** — introduce `TargetMethod` POJO + `TargetMethodSource` interface in `rvsec-gator/commons`, with two implementations: `MopSpecsTargetSource` (LENIENT match by class+name, preserves current `.mop` behavior byte-for-byte) and `SignatureFileTargetSource` (STRICT match by full Soot signature).
- **CLI `--targets-file PATH`** in `rv-static-analysis`, mutually exclusive with existing `--mop-dir` via `argparse.add_mutually_exclusive_group()`. No default value — the user explicitly selects the source.
- **Decompose `RvsecAnalysisClient`** into `TargetResolver` + `ReachabilityEngine` + `ReachabilityIndex` + `ReachabilityEnricher` + `JsonReportWriter`. Client becomes ~200 LOC orchestrator. Characterization fixture (`cryptoapp.apk.json`) freezes baseline pre-decomposition.
- **`ReachabilityEnricher`** between engine and writer (ADR-5) — visitor injected into the writer; `enrich*(node)` callbacks per item resolve flags from the `ReachabilityIndex` on the fly. Writer remains pure (zero direct `ReachabilityIndex` reference) and continues to emit each section with `flush()` to preserve partial-recovery semantics under timeout (D3 revision 2 — no batch `ReportModel`).
- **JSON sentinel `"complete": true`** (ADR-6) — last top-level field written; parser checks; absent or false ⇒ sample is truncated and excluded from gates requiring completeness.
- **Shared JSON key constants** (ADR-7) — `JsonSchema.Keys` (Java) + `_JK` SimpleNamespace (Python) eliminate ~45 magic strings and the historical `eventType`/`type` drift between listeners and transitions.
- **BREAKING — Rename MOP→Target end-to-end** (ADR-1 revoking earlier preservation decision). Empirical grep 2026-05-25: **41 files / 266+ live occurrences** (excl. deprecated `rv-agent/`, `backup/`, `results/`):
  - JSON: `reachesMop`/`directlyReachesMop`/`mopMethods`/`handlerReachesMop`/`handlerDirectlyReachesMop` → `reachesTarget`/`directlyReachesTarget`/`targetMethods`/`handlerReachesTarget`/`handlerDirectlyReachesTarget`.
  - Python Pydantic in `rv-android-core`: `Method.reaches_mop`/`Widget.reaches_mop`/`ComponentInfo.reaches_mop`/`ComponentInfo.mop_methods`/`WidgetEvent.handler_reaches_mop`/`WindowTransition.handler_reaches_mop`/`target_reaches_mop` → `*_reaches_target` / `ComponentInfo.target_methods` / `handler_reaches_target` / `target_reaches_target`.
  - rv-coverage CSV header + Python attrs: `cov_reaches_mop` → `cov_reaches_target`.
  - GATOR Java: class `MopMethod` → `TargetMethod` (consolidated with new POJO); methods `loadMopSignatures`/`resolveMopInScene`/`findDirectMopCallersByBytecodeScan` → `loadTargetSignatures`/`resolveTargetsInScene`/`findDirectTargetCallersByBytecodeScan`. Includes 6 Java test files (`BytecodeScanMatchTest`, `BaselineComparisonIT`, `MopSignatureLoaderTest`, `RvsecAnalysisClientIT`, `JsonOutputTest`, `ReachabilityBfsTest`).
  - CLI `--mop-dir` and `mop_dir` config attribute preserved (semantically identify the source as JavaMOP specs, not the generalized concept).
- **Expose `--cg-algorithm {spark,cha,rta,vta}`** (default `spark`) in the `rv-static-analysis` CLI; forwarded to GATOR as `-cgAlgorithm`. Mechanical alignment with existing Soot capability (D8 — moved from C2 into gh60 because it is pure CLI plumbing).
- **Extract `JimpleDefUtils`** to deduplicate `definitionRhs`/`resolveInt`/`resolveStr` between `MenuExtractor` and `SpinnerItemExtractor`. Backed by Requirement "Shared Jimple Helpers" + INV-ANA-38 in the `analysis` spec.
- **Atomic JSON write + two-stage parser read** (ADR-4) — CONDITIONAL. Enters only if Phase 1 task-zero investigation confirms gh57 had real corruption (not parseable truncation). Sentinel covers truncation independently.
- **Sweep post-merge** — all 380 APKs reprocessed; no legacy `*Mop` JSONs preserved.

## Capabilities

### New Capabilities

None. All additions live within existing `analysis` and `core` specs.

### Modified Capabilities

- `analysis`: target loading abstraction (TargetMethodSource), decomposition of RvsecAnalysisClient, JSON contract rename (MOP→Target), JSON sentinel `complete=true`, shared JSON keys, CLI `--targets-file` mutex with `--mop-dir`. Touches both `rv-static-analysis` (Python wrapper + parser) and the producer-side `rvsec-gator` Java module that this spec implicitly governs via the JSON contract it consumes.
- `core`: rv-android-core Pydantic domain model rename for `Method`, `Widget`, `Component`, `WidgetEvent`, `WindowTransition` reachability fields. No new fields in this change (G7/G8 enrichment fields belong to a follow-up change C3).

## Impact

**Modules edited (counts from empirical grep 2026-05-25):**

- `rvsec-gator` (Java, ~880-980 new LOC + 108 renamed occurrences across 7 files — 1 src `RvsecAnalysisClient.java` + 6 tests): new abstraction (`TargetMethod`, `TargetMethodSource`, `MopSpecsTargetSource`, `SignatureFileTargetSource`), decomposition into 4 classes + visitor enricher (no batch `ReportModel`), `JsonReportWriter` streaming walker, sentinel emission with `fsync`, `JsonSchema.Keys` constants, `JsonSchemaKeysDump` reflection helper, `JimpleDefUtils` extract, MOP→Target rename in producer and in all Java tests.
- `rv-static-analysis` (Python, ~75-90 new LOC + 4 renamed sites in `config.py` + `parser/static/static_analysis_parser.py`): `--targets-file` CLI flag with mutex, `--cg-algorithm {spark,cha,rta,vta}` flag, parser via `_JK` constants, sentinel check, `window_methods_index` built to feed `WindowTransition.target_reaches_target`.
- `rv-android-core` (Python, ~10 fields renamed): rename in `domain/classes.py` (`Method`), `domain/widget.py` (`Widget`), `domain/components.py` (`ComponentInfo.reaches_mop` + `ComponentInfo.directly_reaches_mop` + `ComponentInfo.mop_methods` → `target_methods`), `domain/wtg.py` (`WindowTransition.target_reaches_target` property), `domain/coverage.py` (`cov_reaches_mop`), `util/android/repository_initializer.py`. Includes new field `StaticAnalysisData.complete: bool` in `domain/static.py`.
- `rv-coverage` (Python, 2+ test files + aggregators): `cov_reaches_mop` → `cov_reaches_target` across CSV header, attributes, aggregation scripts, fixtures.
- `rv-platform` (Python): `components/result_processor.py` + tests — mechanical rename of attribute reads in coverage components.
- `rv-experiment` (Python): search `reaches_mop` in `modules/rv-experiment/src/` (grep found no current src occurrences; touched only via transitive chain — re-grep at implementation time and rename any emergent sites).
- `rv-screen-parser` (Python, 4 visitor files + 4 test files): `abstract_visitor.py`, `default_visitor.py`, `enhanced_visitor.py`, `model.py` — reference the propagated reachability flags.
- `aperv-tool` (Python): empirical grep returned 0 occurrences — aperv-tool is the target consumer of the new `--targets-file` workflows but does not yet consume renamed reachability flags; mechanical rename if any emergent site appears during implementation.
- `scripts/` (Python, 7 files): `aperv_objective.py`, `aperv_parameter_space.py`, `select_jca_stratified.py`, `jca557_vs_paper.py`, `static_analysis_sweep.py`, `augment_planilha.py`, `regenerate_results/{verify,regenerate_container}.py` — mechanical rename.
- `rv-agent` (deprecated per CLAUDE.md): **zero edits** by policy — `modules/rv-agent/` is explicitly excluded by the `G_no_legacy_mop` gate. Reads stale JSONs by inertia; not a live consumer.
- `rv-tools`: zero (does not consume reachability fields).
- CSVs published under `results/` and `experimento-*/`: zero retroactive change — immutable by scientific principle; cross-experiment comparison requires header normalization (one-line script).

**FRs/NFRs (PRD):**

- **FR04** (static analysis pipeline) — modified: source abstraction added, CLI surface expanded with `--targets-file`.
- **FR05** (reachability data exposed to downstream consumers) — modified: field names changed; semantic content preserved.
- **FR06** (coverage tracking) — modified by attribute rename only; behavior unchanged.
- **FR33-FR37** (core domain models) — modified by Pydantic field rename.
- **NFR02** (robustez frente a timeout/falha do produtor) — strengthened by sentinel `complete=true` and (if enabled) two-stage read.
- **NFR04** (P3 no backward compatibility) — honored: rename is atomic per module, no shims, no dual-naming, no `_unused` renames, no `# removed` comments.

**Cross-module risk:** the rename is broad but mechanical (266 occurrences across 41 files). Mitigated by atomic per-module commit (C1f, dispatchable in parallel via subagents per consumer module) + `G_no_legacy_mop` CI gate that greps `rvsec-gator/ modules/ scripts/` (excluding `modules/rv-agent/` per deprecation policy) for any `reachesMop`/`reaches_mop`/`MopMethod`/`mop_methods`/`cov_reaches_mop` outside the documented exclusions (CLI `--mop-dir`, `mop_dir` config, `MopSpecsTargetSource`, immutable published CSVs, archived OpenSpec deltas).

**ADR numbering note:** decisions named in `design.md` are D1-D10 (referencing ADR-1 revoked, ADR-3 through ADR-7). There is no "ADR-2" — the numbering was consolidated during the Phase-0 multi-LLM convergence (the entry that would have occupied ADR-2 was absorbed into ADR-3 on matching policy). New decisions introduced in this change (D7 bytecode-scan contract, D8 `--cg-algorithm` in C1, D9 atomic write conditional renumbered from the prior D7, D10 `targetReachesTarget` collision) are internal to gh60 and do not receive an ADR number.

**Conditional scope (C1h):** atomic write + two-stage read enters only after Phase 1 task-zero investigates 2-3 gh57 failure samples and confirms real corruption (junk bytes, JSON not parseable up to the `_recover_truncated_json` recovery point). If the failures were parseable truncation, the sentinel suffices and C1h is dropped.

## Follow-up Changes (NOT in this change — required to complete the static analyzer overhaul)

This change is **C1** of a 3-change sequence decided in the Phase-0 ideation (`docs/20260515_plano_gator_targets_generic.md` §9). C1 lays the foundation (target abstraction + decomposition + rename + sentinel + shared keys); the static analyzer overhaul is **only complete after C2 and C3 also merge**.

- **C2 — `gh<N+1>-hardening-package`** (depends on C1 merged):
  - G6.2 `resolveStringReference` cache (perf under timeout regime)
  - G6.3 `findOnCreateOptionsMenu` walks superclass hierarchy (fixes FN for menus in base classes)
  - G6.4 `parseArraysXml` handles `<integer-array>` and `<array>` (not just `<string-array>`)
  - G6.5a-c dead code removal expanded: `client/.../wtg/model/` + `FlowgraphRebuilder.createDefineIntentContentOpNode` (commented block) + `FlowgraphRebuilder.buildCallGraphLegacy` (subject to grep of live callers)
  - G6.6 log warn in `WidgetType.from_class_name` when fallback to `OTHER` (drift detection post-ProGuard/AndroidX)
  - G11 dual package emission: `manifestPackage` + `codePackage` top-level fields (fixes `am start` for 27.5% of corpus on game-engine/hybrid-fw)
  - G5.7-G5.8 (residual): README sync (output path, Java version) + expose `--cg-algorithm` CLI flag
- **C3 — `gh<N+2>-agent-enrichment`** (depends on C1 merged; C2 idealmente merged):
  - G7 emit `handlerReachesTarget`/`handlerDirectlyReachesTarget` per widget listener (annotation in `ReachabilityEnricher`; writer stays pure)
  - G8.1 same per transition event; per-transition aggregate `targetReachesTarget` derived as Python `@property target_reaches_target` (not emitted)
  - G9 mark `externalExit=True`/`exitKind` for transitions to `ACTION_VIEW`/`ACTION_SHARE`/`ACTION_DIAL`/`ACTION_SENDTO`/`ACTION_CALL` (agents avoid browser/dialer dead-ends)
  - G12 extend Python parser to cover full `EventType` enum (audit G12.1 already confirmed Cenário A — GATOR Java already emits correctly; fix is parser-only ~10 LOC)
- **Final sweep post-C3:** all 380 APKs reprocessed with final schema; `G_sweep` thresholds applied.

Both C2 and C3 are blocked by C1 (this change) merging. C2 builds on the decomposed `JsonReportWriter` + renamed `JsonSchema.Keys`; C3 adds new annotations inside `ReachabilityEnricher` (introduced here in C1d) without modifying the writer. The fragmentation into 3 changes is non-negotiable per the multi-LLM convergence recorded in §9 of the Phase-0 doc (single change exceeds review capacity; ≥9 groups co-touch `RvsecAnalysisClient.java`).
