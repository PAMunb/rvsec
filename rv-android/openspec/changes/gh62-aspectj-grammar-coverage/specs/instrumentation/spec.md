# Instrumentation — Delta Spec for gh62-aspectj-grammar-coverage (round-10)

> **ROUND-10 BANNER (2026-05-29) — authoritative override** (see `EMPIRICAL-DEMAND.md` for the full evidence chain). An empirical pipeline-level demand audit against `empirical-monitors/{jca,generic,generic_new}/` revised three classifications:
>
> - **AA-decision**: §4.E `execution(...)` — pipeline POSITIVE = 0,0,0 → **NOT-NEEDED β** (was COVERED in round-9). Absorber: JavaMOP compiler call-rewrite. `ExecutionPointcutGrammarTest.executionPositiveAbsorptionAssertion` enforces.
> - **AB-decision**: §4.W positive `within(typePattern)` simple `pkg..*` — pipeline POSITIVE = 0,0,0 → **NOT-NEEDED β** (was COVERED in round-9). Absorber: MOP macro-body. `WithinPositiveGrammarTest.withinPositiveAbsorptionAssertion` enforces.
> - **AC-decision**: §4.JP `thisJoinPoint*` `getStaticPart().getSignature()` — 3 live sites in `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328` → **REMOVED from path-β; capability reactivated as §4.Y Signature-delivery sub-closure (COVERED)**. The Coverage.aj absorption claim covers coverage-logging use only.
>
> **Closure count**: 14 → **12** (§4.E and §4.W exit; §4.JP folds into §4.Y).
> **Count corrections** (applied below per-row): §4.I 8→3, §4.T 2→1, §4.Y 6→3+Signature, §4.TT 44→22, §4.AT 10→5, §4.N 32→16, §4.O ~73→64, §4.X ~16→14.
>
> Where any narrative below conflicts with this banner, this banner wins. Round-8/9 framing preserved for historical context.

## ADDED Requirements

### Requirement: AspectJ Grammar Coverage Matrix as Contract

The dexlib2 instrumenter (`rvsec-android/rvsec-instrumentation-dexlib2/`) SHALL document the AspectJ pointcut surface it supports as a **grammar coverage matrix** anchored to the AspectJ Programming Guide §"Pointcuts" grammar and the AspectJ 5 quick reference. The matrix lives at `docs/aspectj_grammar_coverage.md` in the rv-android repository and is the authoritative contract for what dexlib2 weaves correctly today.

For every production listed under the **closed enumeration** below, the matrix SHALL contain exactly one row with the following columns:

- **AspectJ syntax** — the normative form (e.g. `call(MethodPattern)`, `args(name)`, `T+`, `after() throwing(Id):`).
- **SourceDemand** — integer counts per `.mop`/`.aj` source corpus shipped by the project (`aspect/Coverage.aj`, `jca/`, `generic/`, `generic_new/`). Counts SHALL be produced by `DemandCounter.countMop(designator, corpus)`.
- **PipelineDemand** — integer counts per **post-JavaMOP-compilation** corpus, measured against the `.aj` files actually consumed by the dexlib2 instrumenter (`results/gh53_smoke_dexlib2/monitors/`). Counts SHALL be produced by `DemandCounter.countCompiledAj(designator, corpus)`. **Round-8 introduction**: this column is the authoritative demand signal for scope decisions — closures ship in-change when PipelineDemand ≥ 1, not when SourceDemand ≥ 1. Divergences between SourceDemand and PipelineDemand surface upstream absorption (see `Requirement: Upstream Absorption Verdict` below).
- **Parser** — one of `IMPL` / `STUB` / `MISSING`, with a `file:line` anchor.
- **Matcher** — one of `IMPL` / `ALWAYS-MATCH` / `MALFORMED-DESC` / `MISSING`, with a `file:line` anchor.
- **Emitter** — one of `IMPL` / `NO-OP` / `N/A`, with a `file:line` anchor.
- **Verdict** — exactly one value from `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. After round-8 absorption, **no row SHALL carry `SILENT-GAP`**; every row is `COVERED` (closure shipped in-change), `EXPLICIT-NO-OP` (UOE + assertion test), or `NOT-NEEDED` (zero pipeline demand with documented rationale).
- **Evidence** — for `COVERED`, the FQN of an enabled passing test in `grammar-tests/`; for `EXPLICIT-NO-OP`, BOTH the FQN of a passing test asserting `UnsupportedOperationException` AND the `file:line` of the no-op declaration; for `NOT-NEEDED` path α, an enabled passing test asserting `DemandCounter.countMop == 0`; for `NOT-NEEDED` path β, an enabled passing test asserting `DemandCounter.countCompiledAj == 0` plus the named upstream absorber (e.g. `JavaMOP-compiler`, `coverage-weaver`, `MonitorRuntime-dispatch-loop`, `DescriptorReader`, `dexlib2-inline-emission-model`).
- **Deferral note** — for `EXPLICIT-NO-OP` and `NOT-NEEDED` rows only: a one-paragraph rationale quoted from `deferred.md` explaining why the construction is not implemented.

#### Verdict composition rule (worst-of-pipeline, with absorption override)

A row's `Verdict` SHALL be derived from its `Parser` / `Matcher` / `Emitter` cells by the **worst-of-pipeline** rule with **absorption override**: the row is `COVERED` only if every cell in scope for that row is `IMPL` AND `PipelineDemand ≥ 1`; otherwise the verdict downgrades or upgrades as follows:

- Any cell of `MISSING`, `STUB`, `ALWAYS-MATCH`, `MALFORMED-DESC`, or `NO-OP` downgrades the row to `SILENT-GAP` — UNLESS one of two overrides applies:
  - **EXPLICIT-NO-OP override**: the defective cell is `NO-OP` paired with an explicit `UnsupportedOperationException` assertion and a `file:line` anchor.
  - **NOT-NEEDED override**: `PipelineDemand == 0`. Path α requires additionally `SourceDemand == 0` across all four corpora AND no behavioural-parity dependency. Path β requires `SourceDemand ≥ 1` AND the matrix Evidence column to (a) cite the source-level demand counts, AND (b) name the upstream absorber, AND (c) cite the empirical evidence (file:line in `coverage-weaver`/the compiled `.aj`/the experimento RELATORIO) that proves the absorption.
- A `NOT-NEEDED` verdict is the only verdict that may be assigned when the cells alone would suggest `SILENT-GAP`. The matrix MUST state the demand evidence (both source and pipeline) AND the absorption claim (for path β) in the `Evidence` column.

`MatrixIntegrityTest.testVerdictMatchesWorstOfPipeline` SHALL enforce this rule. After round-8 absorption, `MatrixIntegrityTest.testNoSilentGapRowsRemain` SHALL additionally fail the build if any row carries `Verdict = SILENT-GAP` (the round-8 archive condition).

#### Closed enumeration of matrix rows

The matrix SHALL contain **exactly** the following rows (not "at minimum"). `AspectJDesignators.DESIGNATORS` in `grammar-tests` is the single source of truth and `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` enforces equality with the matrix.

**Classical pointcut designators**: `call`, `execution`, `target` *(binding sub-row)*, `target` *(type-matching sub-row)*, `this` *(binding)*, `this` *(type-matching)*, `args` *(binding)*, `args` *(type-matching)*, `args` *(mixed, e.g. `args(*, name, ..)`)*, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references.

**JavaMOP MOP-extensions**: `condition(...)`, `__STATICSIG` macro.

**Within-family per-stage delegation rows**: `within(...)` positive simple `pkg..*`; `within(*..Log)` suffix-wildcard; `within(T+)` `T+`-inside-positive-within; `!within(...)`.

**AspectJ 5 annotation pointcut designators**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.

**Advice forms**: `before`, `after`, `after returning`, `after throwing`, `around`.

**Type-pattern modifiers**: `T+` *(in `call()` param)*, `T+` *(in `call()` owner)*, `T+` *(in `call()` return)*, `T+` *(inside `!within(...)`)*, `*` wildcard, `..` *(standalone varargs)*, `..` *(trailing-mixed, e.g. `(T, ..)`)*, dot-glob (`..*`), single-level glob (`.*`), arrays (`T[]`, `T[][]`), inner-class qualifier (`Outer.Inner` vs `Outer$Inner`).

**SignaturePattern modifiers**: positive visibility (`public`/`private`/`protected`), negated visibility (`!public`), `static`, `final`, `throws ExceptionPattern`.

**Composition operators**: `&&`, `||`, `!`, parentheses.

**Advice-body reflective API**: `thisJoinPoint` *(binding)*, `thisJoinPointStaticPart` *(binding)*, `thisEnclosingJoinPointStaticPart` *(binding)*, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` *(includes `MethodSignature` / `ConstructorSignature` / `FieldSignature` subtype accessors)*, `JoinPoint.getTarget()` *(or `.getThis()` — grouped)*, `JoinPoint.getKind()` *(or `.getSourceLocation()` — grouped)*.

**Around-advice mechanics**: `proceed(...)` *(keyword inside around body — one row, consistent with `around` being EXPLICIT-NO-OP)*.

**Aspect declaration mechanics**: `aspect Foo { ... }`, `pointcut p(): ...` *(named-pointcut declaration)*, `abstract aspect` + concrete subaspect, aspect inheritance, `declare precedence`, privileged aspect.

**Runtime linkage**: `org.aspectj.lang.JoinPoint` class *(plus `JoinPoint.StaticPart` and `Signature` subtypes)* availability in the instrumented bytecode. **Round-8**: this row's verdict is `NOT-NEEDED β` with `coverage-weaver` as the named upstream absorber; the round-7 plan to ship a local `br.unb.cic.rv.aspectjlang.*` substrate is dropped (see `deferred.md` §2.2.1-D).

The matrix is the contract. Future changes that introduce a parser/matcher/emitter path MUST also introduce or update a matrix row; `MatrixIntegrityTest` running in CI breaks the build if either side moves alone.

#### Scenario: every enumerated designator has a matrix row

- **WHEN** a reviewer reads `docs/aspectj_grammar_coverage.md`
- **THEN** the table SHALL contain exactly one row for each entry in the closed enumeration above
- **AND** every row SHALL have non-empty values in every column

#### Scenario: every COVERED row has an enabled passing test

- **WHEN** a reviewer audits a row with `Verdict = COVERED`
- **THEN** the `Evidence` column SHALL cite a test method by FQN in the `grammar-tests/` Maven module
- **AND** running `mvn -pl grammar-tests test -Dtest=<that-fqn>` SHALL produce a passing result on the current `HEAD` of `origin/modules`
- **AND** the cited test method SHALL NOT carry `@Disabled` (neither on the method nor inherited from its class)

#### Scenario: every EXPLICIT-NO-OP row pins both the assertion and the no-op location

- **WHEN** a reviewer audits a row with `Verdict = EXPLICIT-NO-OP`
- **THEN** the `Evidence` column SHALL cite BOTH the FQN of a passing test asserting `UnsupportedOperationException` AND the `file:line` of the no-op declaration in production code
- **AND** the `Deferral note` column SHALL cite the corresponding entry in `deferred.md`

#### Scenario: every NOT-NEEDED row carries demand-zero evidence with absorption claim

- **WHEN** a reviewer audits a row with `Verdict = NOT-NEEDED`
- **THEN** the `Evidence` column SHALL cite an enabled passing test
- **AND** for path α the test SHALL assert `DemandCounter.countMop(designator) == 0` across all four corpora
- **AND** for path β the test SHALL assert `DemandCounter.countCompiledAj(designator) == 0` AND cite the named upstream absorber AND cite the empirical evidence (`coverage-weaver` javadoc + RELATORIO, compiled `.aj` grep result, or APK smali inspection)
- **AND** the `Deferral note` column SHALL cite the corresponding rationale paragraph in `deferred.md`

#### Scenario: no SILENT-GAP row survives round-8 archive

- **WHEN** `MatrixIntegrityTest.testNoSilentGapRowsRemain` runs in CI against the post-archive state of gh62
- **THEN** the test SHALL fail the build if any matrix row carries `Verdict = SILENT-GAP`
- **AND** the failure message SHALL name the row(s) and direct the reader to either ship a closure (flip to COVERED) or document the deferral (flip to EXPLICIT-NO-OP or NOT-NEEDED with a `deferred.md` rationale)

#### Scenario: bidirectional matrix↔tests consistency

- **WHEN** `MatrixIntegrityTest` runs in CI
- **THEN** for every enabled test method in `grammar-tests/`, there SHALL be exactly one matrix row whose `Verdict` and `Evidence` column resolves to that method
- **AND** orphan tests (no matrix row) and orphan rows (no test) MUST break the build
- **AND** the count of skipped tests in the test report SHALL equal zero after round-8 (no `@Disabled` annotations remain)

#### Scenario: source-level and pipeline-level demand counts reproducible by the Java helper

- **WHEN** a reviewer runs `DemandCounter.countAllMop()` against `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/` AND `DemandCounter.countAllCompiledAj()` against `results/gh53_smoke_dexlib2/monitors/`
- **THEN** the resulting counts SHALL match every `SourceDemand` and `PipelineDemand` column in the matrix to the integer
- **AND** the helper SHALL be portable (no `bash`, no `LC_ALL`, no shell quoting) — invoked directly from `MatrixIntegrityTest.testSourceDemandCountsReproducible` and `MatrixIntegrityTest.testPipelineDemandCountsReproducible`

### Requirement: Grammar Tests Maven Submodule

The sibling rvsec repository SHALL contain a Maven submodule `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` that materialises the matrix as executable tests. The module is test-only: its `pom.xml` declares no `main/java/` source, no shaded jar, and is excluded from the `instr-cli` shade plugin.

For every row in `docs/aspectj_grammar_coverage.md`, the module SHALL contain exactly one test method in `src/test/java/`. After round-8 absorption, NO test method SHALL carry `@Disabled` — every test is enabled and either passes (COVERED), asserts `UnsupportedOperationException` (EXPLICIT-NO-OP), asserts `DemandCounter.countMop == 0` (NOT-NEEDED α), or asserts `DemandCounter.countCompiledAj == 0` plus the upstream absorption claim (NOT-NEEDED β).

#### Scenario: green bar across all rows post-round-8

- **WHEN** a developer runs `mvn -pl grammar-tests test` on a clean checkout of `origin/modules` after gh62 archives
- **THEN** the test runner SHALL report zero failures
- **AND** the test runner SHALL report zero skips (every test is enabled)
- **AND** every test method SHALL resolve to exactly one matrix row whose verdict matches the test's expected outcome

#### Scenario: closure of a future construction adds row + test atomically

- **WHEN** a future sub-change adds a new AspectJ construction (e.g. a new corpus introduces pipeline demand for `cflow(...)`)
- **THEN** the same commit SHALL add the matrix row AND the enabled passing test asserting the closure's behaviour
- **AND** `MatrixIntegrityTest` running in CI SHALL fail the build if either side is missing — an orphan row without a test fails `testEveryDesignatorHasMatrixRow` (via the test FQN resolution); an orphan test without a row fails `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`

### Requirement: Upstream Absorption Verdict

The matrix verdict vocabulary `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}` SHALL recognise **path β** as a first-class assignment of `NOT-NEEDED`: a construction may have non-zero source-level demand (`DemandCounter.countMop ≥ 1`) and still carry `NOT-NEEDED` if the construction is consumed by an upstream pipeline stage before reaching the dexlib2 instrumenter (`DemandCounter.countCompiledAj == 0`).

The set of recognised upstream absorbers and their evidence anchors SHALL be:

- **JavaMOP compiler** — absorbs `condition(...)` (folds into `*RuntimeMonitor.*Event(...)` method body) and `__STATICSIG` macro (expands before emitting `.aj`). Evidence: `results/gh53_smoke_dexlib2/monitors/MultiSpec_1MonitorAspect.aj:212-218` (post-compilation absence of `condition(`) plus the `generic_new` audit (archive precondition for `__STATICSIG`).
- **`coverage-weaver` module** — absorbs `Coverage.aj` end-to-end, the AspectJ runtime substrate, `thisJoinPoint*` bindings, `within(*..Log)`, `within(Coverage+)`, and `MethodSignature.toLongString()`. Evidence: `coverage-weaver/CoverageWeaver.java:23-32` javadoc ("Semantically equivalent to the AspectJ rule in `Coverage.aj`") + `SignatureFormatter.java:14-17` javadoc ("reproduces it byte-for-byte") + `experimento-20260508/RELATORIO.md` §3.2 / §7.2 (190 APKs, dexlib2 variant exclusive, all coverage via `coverage-weaver`).
- **`MonitorRuntime` dispatch loop** — absorbs `declare precedence`. Evidence: deterministic dispatch ordering documented in the monitor builder's emitter.
- **`DescriptorReader`** — absorbs aspect-declaration mechanics (`aspect Foo { ... }`, `pointcut p(): ...`, aspect inheritance, abstract aspect, privileged aspect). Evidence: `DescriptorReader.java:13-15` reads `AspectDescriptor` JSON; the `.aj` source tokens never reach `PointcutExpressionParser`.
- **dexlib2 inline-call emission model** — absorbs `adviceexecution()`. The dexlib2 instrumenter emits `invoke-static *RuntimeMonitor.*Event(...)` at the matched call site rather than synthesising AJC-style advice methods (`ajc$before$...`); the `!adviceexecution()` clause of `commonPointcut` is satisfied trivially because no advice-body executions exist as separate join points. Evidence: APK inspection of `results/gh53_smoke_ajc/instrumented_apks/cryptoapp.apk` (AJC variant has `ajc$after$...` methods; dexlib2 variant has zero such methods).

A path-β classification requires an enabled passing assertion test in `grammar-tests/` that names BOTH the absorber AND the empirical evidence file path; the test SHALL fail the build if any of the three conditions changes: (a) the absorber file/module is removed, (b) the empirical evidence file is deleted, (c) `DemandCounter.countCompiledAj()` returns non-zero for the construction.

#### Scenario: path-β assertion test cites the absorber by name

- **WHEN** a reviewer audits a `NOT-NEEDED path β` row (e.g. `condition(...)`)
- **THEN** the `Evidence` column SHALL name `JavaMOP-compiler` as the absorber
- **AND** the assertion test FQN SHALL be `ConditionGrammarTest.conditionAbsorbedByRuntimeMonitor`
- **AND** running that test SHALL pass on `origin/modules` HEAD
- **AND** the test body SHALL assert: (a) `DemandCounter.countMop("condition") ≥ 1` (source demand is non-zero); (b) `DemandCounter.countCompiledAj("condition") == 0` (pipeline demand is zero); (c) the corresponding `*RuntimeMonitor.*Event` method exists in the descriptor

#### Scenario: pipeline-demand spike re-opens an absorbed closure

- **WHEN** a future corpus update causes `DemandCounter.countCompiledAj("condition") ≥ 1`
- **THEN** `MatrixIntegrityTest.testPipelineDemandCountsReproducible` SHALL fail the build
- **AND** the matrix amendment workflow opens a new sub-change reintroducing the `§4.G ConditionGuardEmitter` closure (or an equivalent runtime-delegation alternative)
- **AND** the `ConditionGrammarTest.conditionAbsorbedByRuntimeMonitor` assertion test SHALL be retired in the same commit (replaced by the COVERED-row's assertion)

### Requirement: Deferred-by-Design Document

The change directory `openspec/changes/gh62-aspectj-grammar-coverage/` SHALL contain a `deferred.md` document that enumerates every construction with `DemandCounter.countCompiledAj() = 0` at the dexlib2 pipeline stage, with the deferral rationale per construction. The document replaces the round-6 `ledger.md` (which was removed in round-7 because no `Fix-now` or `Follow-up` bucket survives — all non-zero-pipeline-demand constructions ship in-change).

The document SHALL contain exactly two sections plus an evidence appendix:

- **§1 Deferred-by-design (EXPLICIT-NO-OP)** — constructions where the project explicitly will NOT implement the closure, with production code raising `UnsupportedOperationException` (or equivalent) AND a passing test asserting the throw. Currently the only entry is `around` advice + `proceed(...)`. Each entry names: AspectJ syntax, the production `file:line` of the no-op, the assertion test FQN, and a one-paragraph rationale.
- **§2 Deferred-by-design (NOT-NEEDED)** — split into two subsections:
  - **§2.1 Path α** — constructions where the matcher/parser is absent (`MISSING` in every pipeline stage) AND `DemandCounter.countMop` is zero across all four corpora.
  - **§2.2 Path β** — constructions with non-zero source-level demand absorbed by an upstream pipeline stage. Each entry names: AspectJ syntax, source-level demand counts, the named upstream absorber, the empirical evidence (file:line/RELATORIO/APK inspection), the assertion test FQN, and the rationale paragraph.
- **§Appendix The Three Empirical Audits** — narrative of the 2026-05-26 audits that produced the round-8 reclassifications (APK AJC inspection, compiled `.aj` audit, `coverage-weaver` overlap analysis).

The document is a one-shot snapshot archived with the change; the matrix at `docs/aspectj_grammar_coverage.md` is the live contract. A future corpus introducing pipeline demand for any deferred row triggers `MatrixIntegrityTest.testPipelineDemandCountsReproducible` failure (the matrix row's pipeline-demand cell diverges from the helper's output) and forces amendment via a new sub-change.

The deferred-document snapshot is content-addressed: a `deferred.snapshot.sha256` file containing the SHA-256 of `deferred.md` at archive time SHALL be committed to `grammar-tests/src/test/resources/`; `testDeferredDocumentIsFrozenPostArchive` SHALL verify the live document's SHA against the snapshot and fail if they diverge (positive enforcement of the "frozen post-archive" property; replaces the round-6 `ledger.snapshot.sha256` mechanism — see design D7). **Round-8 race-condition fix**: the snapshot SHALL be generated and committed in the same commit as the final `deferred.md` edit (tasks §1.4), not in a separate post-archive step.

#### Scenario: deferred document covers every EXPLICIT-NO-OP and NOT-NEEDED row

- **WHEN** a reviewer audits the matrix and `deferred.md` together
- **THEN** every matrix row with `Verdict ∈ {EXPLICIT-NO-OP, NOT-NEEDED}` SHALL appear in exactly one section of `deferred.md`
- **AND** no entry in `deferred.md` SHALL reference a matrix row that does not exist
- **AND** every entry SHALL declare its assertion test FQN, its absorber (for path β), and a rationale paragraph

### Requirement: Demand-Driven Closures for All Pipeline-Demand Constructions

The dexlib2 instrumenter SHALL implement functional equivalents for **every** AspectJ/JavaMOP construct measured with `DemandCounter.countCompiledAj ≥ 1` at the instrumenter stage in any of the four corpora. Each closure SHALL flip its matrix row(s) from `SILENT-GAP` to `COVERED` with an enabled test in `grammar-tests/` asserting the post-fix behaviour against the corpus pattern that motivated it. The closures are bisect-friendly atomic commits.

**Round-10 in-change closures (12)** *(round-9 fourteen minus §4.E and §4.W per AA/AB-decisions 2026-05-29; §4.JP folded into §4.Y per AC-decision)*:

1. ~~**§4.W**~~ — **REMOVED (round-10 AB-decision)**: pipeline POSITIVE `within(...)` count = 0 across all corpora. NOT-NEEDED β — see `deferred.md` §2.2.1 entry I.
2. **§4.O** — `T+` in `call()` owner (round-10 empirical: 64 sites generic_new).
3. **§4.R** — `T+` in `call()` return (subset of generic_new T+ usage).
4. **§4.N** — `!target(T)` / `!args(T)` parser specialization (round-10 empirical: 14 + 2 = 16 sites generic_new).
5. **§4.V** — `(T, ..)` trailing-mixed varargs (counts PROVISIONAL — pipeline re-grep deferred).
6. **§4.X** — method-name glob `name*` (round-10 empirical: 14 sites generic_new).
7. **§4.TT** — `target(Type)` type-matching (round-10 empirical: 22 sites generic_new).
8. **§4.AT** — `args(Type)` type-matching (round-10 empirical: 5 sites generic_new).
9. **§4.Y** — `staticinitialization(T+)` synthesis (round-10 empirical: 3 sites generic_new) **+ `org.aspectj.lang.Signature` delivery for `*staticinitEvent(Signature)` calls** (round-10 AC-decision: refutes round-8 `thisJoinPoint*` absorption claim; 3 live `thisJoinPoint.getStaticPart().getSignature()` sites in `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328` — the JavaMOP compiler retains the binding for the staticinit advice family).
10. **§4.T** — `after() throwing(...)` end-to-end install (round-10 empirical: 1 site generic_new).
11. **§4.B** — `BaseAspect.notwithin()` macro expansion.
12. **§4.D** — `NamedRefPC` resolver via the existing `baseAspectExclusions` field (round-8 empirical A-decision; round-10 unchanged).
13. **§4.I** — `if(...)` AspectJ PCD via **runtime-helper delegation** (round-10 empirical: 3 sites generic_new).
14. ~~**§4.E**~~ — **REMOVED (round-10 AA-decision)**: pipeline POSITIVE `execution(...)` count = 0 across all corpora (only `!adviceexecution()` substring hits). NOT-NEEDED β — see `deferred.md` §2.2.1 entry H. Defensive shipping rationale dominated by P1 (No speculative features).

**Round-7 closures reclassified to NOT-NEEDED β in round-8 (7)** — see `deferred.md` §2.2.1 for the full evidence base:

- **§4.G `condition(...)` guard emit** → absorbed by JavaMOP compiler.
- **§4.S `__STATICSIG` macro support** → absorbed by JavaMOP compiler (generic_new audit PASS 2026-05-26).
- **§4.A `adviceexecution()` real semantics** → vacuously true in dexlib2 inline-call emission model.
- **§4.RT AspectJ runtime substrate** (~600 LOC + ~150 LOC remap) → absorbed by `coverage-weaver` (Coverage.aj was sole consumer of substrate; Coverage.aj absorbed).
- **§4.JP `thisJoinPoint*` bindings** (~250 LOC) → absorbed by `coverage-weaver` (Coverage.aj) and JavaMOP compiler (`__STATICSIG`).
- **§4.CV Coverage.aj end-to-end** → absorbed by `coverage-weaver` (byte-for-byte equivalent per module javadoc).
- **§4.WW `within(*..Log)` + `within(Coverage+)`** → absorbed by `coverage-weaver` (only Coverage.aj used these forms).

**Note**: round-8 initially planned to also reclassify §4.E to NOT-NEEDED β. Round-9 RESTORED §4.E as defensive shipping per user decision 2026-05-26. **Round-10 AA-decision 2026-05-29 re-RECLASSIFIED §4.E to NOT-NEEDED β** based on empirical pipeline POSITIVE = 0 across all three corpora — see closure #14 above and `deferred.md` §2.2.1 entry H.

#### Scenario: positive within(typePattern) absorbed by MOP macro-body (round-10 AB-decision, REPLACES round-8 §4.W matcher scenario)

- **WHEN** a reviewer audits the empirical pipeline-level demand for positive `within(typePattern)` across the three corpora
- **THEN** `DemandCounter.countCompiledAj(WITHIN_POSITIVE_PREDICATE, jca)` SHALL equal 0
- **AND** `DemandCounter.countCompiledAj(WITHIN_POSITIVE_PREDICATE, generic)` SHALL equal 0
- **AND** `DemandCounter.countCompiledAj(WITHIN_POSITIVE_PREDICATE, generic_new)` SHALL equal 0
- **AND** every `within(` substring occurrence in `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj` SHALL be inside `pointcut notwithin()` or `MOP_CommonPointCut(): !within(... RVMObject+) && ...` body declarations, NOT used as an event predicate by any spec
- **AND** `WithinPositiveGrammarTest.withinPositiveAbsorptionAssertion` SHALL pin this verdict; `!within(...)` semantics flows through §4.B `BaseAspect.notwithin()` expansion + §4.D `NamedRefPC` resolver (both COVERED in-change)

#### Scenario: T+ in call() owner expands to subtypes

- **WHEN** a pointcut `call(* javax.crypto.Cipher+.doFinal(..))` is evaluated at a call to a method declared on a Cipher subtype receiver
- **THEN** the matcher SHALL recognize the receiver type as a subtype of `javax.crypto.Cipher` and return a match
- **AND** the existing exact-equals match for receivers of the exact declared type SHALL continue to succeed

#### Scenario: T+ in call() return position expands to subtypes

- **WHEN** a pointcut `call(Cipher+ Foo.factory(..))` is evaluated at a method whose declared return type is a Cipher subtype
- **THEN** the matcher SHALL return a match
- **AND** when the return type is unrelated to Cipher, the matcher SHALL return no match

#### Scenario: !target(T) inverts the target match

- **WHEN** a pointcut `call(* Object.toString()) && !target(MyClass)` is evaluated at `myClassInstance.toString()`
- **THEN** the matcher SHALL return no match (the receiver IS a `MyClass`, so its negation is false)
- **AND** when evaluated at `anotherClassInstance.toString()`, the matcher SHALL return a match

#### Scenario: (T, ..) trailing-mixed varargs match by head + accept-rest

- **WHEN** a pointcut `call(* SecureRandom.getInstance(String, ..))` is evaluated at calls `getInstance("SHA1PRNG")` and `getInstance("SHA1PRNG", "SUN")`
- **THEN** both SHALL match (the head `String` matches the first param; the trailing `..` accepts any number of remaining params)
- **AND** a call with a non-String first param SHALL NOT match

#### Scenario: method-name glob matches by prefix

- **WHEN** a pointcut `call(* java.util.Collection+.add*(..))` is evaluated at calls to `add(E)`, `addAll(Collection)`, and `addLast(E)`
- **THEN** all three calls SHALL match (the `add*` prefix is satisfied)
- **AND** a call to `remove(E)` SHALL NOT match

#### Scenario: target(Type) type-matching filters by declared receiver type (round-8 V-decision)

- **WHEN** a pointcut `target(Cipher)` is evaluated at a call whose **declared receiver type** in the DEX `MethodReference` is `Cipher` (or a subtype, applying the `+` subtype semantics when the pattern is `Cipher+`)
- **THEN** the matcher SHALL return a match
- **AND** when the declared receiver type is unrelated to `Cipher`, the matcher SHALL return no match
- **AND** round-8 V-decision: the matcher uses the **declared** (static) type from the call-site `MethodReference`, NOT the runtime instance-of. Declared-type is the conservative AspectJ semantics: it is testable at weave time without dynamic dispatch, matches the existing `CallPC.matchOwner` semantics already shipped (consistent with `T+` in `call()` owner per §4.O), and avoids the runtime overhead of `instance-of` checks injected into every advice fire. A future closure MAY upgrade to runtime instance-of if positive demand surfaces (currently zero pipeline demand for that variant)

#### Scenario: args(Type) type-matching filters by declared argument types (round-8 V-decision)

- **WHEN** a pointcut `args(String)` is evaluated at a call whose first (and only) argument's **declared type** in the DEX `MethodReference` parameter list is `String`
- **THEN** the matcher SHALL return a match
- **AND** when the declared argument type is unrelated to `String`, the matcher SHALL return no match
- **AND** round-8 V-decision: declared-type semantics (same rationale as `target(Type)`); subtype expansion via `+` follows `T+` rules from §4.O/R

#### Scenario: staticinitialization synthesis emits a minimal clinit

- **WHEN** a `staticinitialization(MyClass+)` pointcut matches a class `MyClass` that has no existing `<clinit>` method
- **THEN** the weaver SHALL synthesize a `<clinit>` containing only the advice invocation
- **AND** the synthesized method SHALL be flagged in the DEX output as `weaver-synthesized` for auditability

#### Scenario: after throwing installs try-range and exception handler

- **WHEN** an advice `after() throwing(Exception e): call(* Foo.bar(..))` is processed by the weaver
- **AND** the matched call site is `obj.bar()` at a known offset
- **THEN** the weaver SHALL install a try-range covering the invoke and an exception handler emitting the advice invocation with `e` bound to the caught exception register
- **AND** the resulting DEX SHALL pass ART verification (no new VerifyError) and the advice SHALL fire when the call throws

#### Scenario: after throwing range-splitting policy under nested try-catch (round-8 F-decision)

- **WHEN** the matched call site is already covered by one or more pre-existing try-blocks (e.g. the call sits inside a user `try { obj.bar(); } catch (IOException ioe) { ... }` clause)
- **THEN** the weaver SHALL apply the **range-splitting** policy (round-8 F-decision, per cross-LLM meta-review): instead of wrapping the invoke in a new innermost try-block (which produces overlapping-not-nested ranges that ART's verifier rejects), the weaver SHALL split each enclosing try-block into a head segment (instructions before the matched invoke, preserving the original handler list) + the matched invoke itself (covered by BOTH the original handlers AND the new `after-throwing` handler with the new handler listed FIRST so it intercepts the exception before delegating to the original) + a tail segment (instructions after the invoke, preserving the original handler list)
- **AND** the new `after-throwing` handler block SHALL start with `move-exception vException` as its first instruction (ART invariant: handlers begin with `move-exception` for the caught register)
- **AND** the new `after-throwing` handler SHALL re-throw the exception after firing the advice (so user-level `catch` clauses still run); the re-throw is emitted as `throw vException` at the end of the handler block
- **AND** when a `RegisterShifter` (gh61) widening is required to free the exception register, the weaver SHALL honour the shift across the split ranges so register liveness analysis remains consistent
- **AND** the dexlib2 `MethodImplementationBuilder` SHALL serialise the resulting try-blocks in start-offset order, with the new `after-throwing` handler listed BEFORE the user handlers for the matched invoke (ART scans handlers in declaration order; "first-most-specific" semantics requires the new handler to fire first)
- **AND** `DexWeaverNestedTryCatchTest.afterThrowingInsideExistingTryBlockSplitsRangesCleanly` SHALL exercise this policy with a synthetic fixture and assert (a) ART installation succeeds (no VerifyError), (b) when the call throws an exception that matches the user catch, both the new advice handler AND the user catch fire (in that order), (c) when the call throws an exception that the user catch does not match, the new advice handler still fires and the exception propagates to the caller

#### Scenario: BaseAspect.notwithin() macro expands inline from baseAspectExclusions (round-8 A-decision)

- **WHEN** an advice's `commonPointcut` references `BaseAspect.notwithin()` AND the `AspectDescriptor` JSON's `baseAspectExclusions` field is populated by the JavaMOP toolchain (e.g. the canonical twelve-entry list `["sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*", "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*", "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"]` emitted by `DescriptorWriter.defaultBaseAspectExclusions()`)
- **THEN** the §4.B `BaseAspectExpander` SHALL iterate `descriptor.getBaseAspectExclusions()` and build an AND-chain of `NotWithinPC(pattern)` matchers — one per list entry — that evaluates to true only when the class being woven is OUTSIDE every excluded package
- **AND** the resulting composed matcher SHALL be substituted in-place of the `NamedRefPC("BaseAspect.notwithin")` node by the matcher entry-point
- **AND** when the list contains a single entry, the §4.B expander returns the single `NotWithinPC` (no degenerate AND-of-one)
- **AND** `NamedReferenceGrammarTest.baseAspectNotwithinExpandsTwelveExclusionsList` SHALL assert correct expansion against the canonical twelve-entry list AND the single-entry edge case AND the empty-list fail-closed case

#### Scenario: NamedRefPC resolves BaseAspect.notwithin() via baseAspectExclusions

- **WHEN** an `AspectDescriptor` JSON for a JCA aspect contains `commonPointcut: "...&& !adviceexecution() && BaseAspect.notwithin()"` AND the JSON's existing `baseAspectExclusions` field (`List<String>` of package patterns such as `["sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*", "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*", "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"]`) is populated by the JavaMOP toolchain's `DescriptorWriter.defaultBaseAspectExclusions()`
- **THEN** the `NamedRefPC` matcher SHALL recognise the literal reference `BaseAspect.notwithin` and, via the §4.B `BaseAspectExpander`, compose an OR-chain of `!within(<pattern>)` matchers — one per entry of `descriptor.getBaseAspectExclusions()`
- **AND** the composed matcher SHALL be combined with the rest of the `commonPointcut` expression via the existing parser AST
- **AND** when the `NamedRefPC` name is NOT `BaseAspect.notwithin` AND the `AspectDescriptor` carries no other recognised named reference, the matcher SHALL fail closed by throwing `br.unb.cic.rv.pointcut.UnresolvedNamedRefException` carrying the name and the descriptor's `aspectName` — this aligns with the gh62 goal of eliminating silent always-match paths (P3 / round-8 fail-closed policy) and replaces the round-7 always-match-with-WARN fallback flagged as a "trap" by the cross-LLM meta-reviews
- **AND** when `descriptor.getBaseAspectExclusions()` returns an empty list (legacy descriptor produced by a JavaMOP build pre-dating the `baseAspectExclusions` field), the matcher SHALL fail closed with `LegacyDescriptorException` so the instrumenter regenerates the descriptor against the current JavaMOP toolchain rather than silently inlining a permissive filter

#### Scenario: if(...) PCD short-circuits via runtime helper delegation

- **WHEN** an advice `before() : call(* Foo.bar(..)) && if(<boolean-expr>)` is woven
- **THEN** the weaver SHALL assign a stable integer `ifId` to the `<boolean-expr>` at weave time
- **AND** the woven bytecode SHALL emit `invoke-static MonitorRuntime.evaluateIf(<ifId>, args_boxed)` BEFORE the monitor invoke
- **AND** when `MonitorRuntime.evaluateIf(...)` returns `false`, the monitor invoke SHALL NOT fire (the guard short-circuits)
- **AND** when it returns `true`, the monitor invoke SHALL fire as if the `if(...)` clause were absent
- **AND** the per-spec generated `*RuntimeMonitor.evaluateIf(int, Object[])` SHALL contain a switch-case where each case arm holds the actual boolean expression for that `ifId`, lowered by the existing JavaMOP compiler (NOT by the dexlib2 weaver)

#### Scenario: execution(...) absorbed by JavaMOP compiler call-rewrite (round-10 AA-decision, REPLACES round-8 RESTORED §4.E)

- **WHEN** a reviewer audits the empirical pipeline-level demand for `execution(...)` POSITIVE across the three corpora
- **THEN** `DemandCounter.countCompiledAj(EXECUTION_POSITIVE, jca)` SHALL equal 0
- **AND** `DemandCounter.countCompiledAj(EXECUTION_POSITIVE, generic)` SHALL equal 0
- **AND** `DemandCounter.countCompiledAj(EXECUTION_POSITIVE, generic_new)` SHALL equal 0
- **AND** the only `execution(` substring occurrences in `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj` SHALL be inside the `!adviceexecution()` clause of `MOP_CommonPointCut`
- **AND** `ExecutionPointcutGrammarTest.executionPositiveAbsorptionAssertion` SHALL pin this verdict and fail the build if any future corpus introduces `countCompiledAj(EXECUTION_POSITIVE) > 0` — forcing amendment via a new sub-change

#### Scenario: staticinit advice receives org.aspectj.lang.Signature (round-10 AC-decision — §4.Y Signature-delivery sub-closure)

- **WHEN** a class without `<clinit>` is matched by `staticinitialization(T+)` AND the JavaMOP-compiled advice body invokes `thisJoinPoint.getStaticPart().getSignature()` (the canonical generic_new staticinit pattern — see `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328`)
- **THEN** the `StaticInitSynthesizer` SHALL append a minimal `<clinit>` containing `return-void` and a debug marker
- **AND** the `SignatureFactory` SHALL construct an `org.aspectj.lang.Signature` object describing the synthesized `<clinit>` (declaring-class FQN + `<clinit>` name + modifiers) immediately before the runtime call
- **AND** the woven bytecode SHALL emit `invoke-static *RuntimeMonitor.*staticinitEvent(<signature>)` with the constructed `Signature` as the argument
- **AND** the `Signature` argument SHALL be non-null at runtime (the advice body invokes `Signature` accessors that would NPE otherwise)
- **AND** `StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent` SHALL verify the three steps for a synthetic class that mirrors the three live `generic_new` staticinit sites
- **AND** for the dual-instrumentation case where a method is matched by both a `call()` MOP pointcut at one or more call sites AND an `execution()` pointcut at the method body, the weaver SHALL emit ONE advice invocation per distinct (pointcut, advice-form) pair — NOT a deduped single invocation. The emit-plan key SHALL be `dedup_key = sha1(emitter_class + ":" + advice_form + ":" + ifId + ":" + pointcut_AST_hash + ":" + resolved_MethodReference)` (round-8 E-decision: MethodReference-equality with composite key per Claude meta-review refinement). Two emit plans collide ONLY when they share the same `dedup_key` AND the same resolved DEX-level injection site (same instruction offset for `call()`, same method-entry / method-return offset for `execution()`); colliding plans collapse to a single emitter invocation. Two emit plans that share `dedup_key` but inject at distinct DEX offsets (e.g. `call()` at offset 0x12 inside the same method whose body is matched by `execution()` at offset 0x00) MUST emit two distinct invocations — they are semantically distinct join points

## Invariants

- **INV-INS-88**: For every row in the closed enumeration declared under `Requirement: AspectJ Grammar Coverage Matrix as Contract`, `docs/aspectj_grammar_coverage.md` MUST contain exactly one matrix row. New AspectJ versions or new corpora MUST result in a new row added by amendment, not implicit support.
- **INV-INS-89**: For every matrix row, the `Verdict` column MUST take exactly one value from the set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. `NOT-NEEDED` is permitted via exactly two paths: (path α) `DemandCounter.countMop` zero across all four corpora AND no parser/matcher/emitter implementation; OR (path β) the row reflects an AspectJ production with non-zero source-level demand absorbed by an upstream pipeline stage before reaching the dexlib2 pipeline. Path β requires the matrix Evidence column to (a) cite both source and pipeline demand counts, AND (b) name the upstream absorber from the set declared in `Requirement: Upstream Absorption Verdict`, AND (c) cite the empirical evidence (file:line or RELATORIO citation), AND (d) cite an enabled passing test asserting the absorption claim.
- **INV-INS-90**: For every matrix row with `Verdict = COVERED`, there MUST exist an enabled (non-`@Disabled`) passing test in `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` whose FQN appears in the row's `Evidence` column.
- **INV-INS-91**: (Round-8 reformulation.) The matrix MUST NOT contain any row with `Verdict = SILENT-GAP` post-archive. `MatrixIntegrityTest.testNoSilentGapRowsRemain` SHALL fail the build if any row carries `SILENT-GAP` after gh62 archives. The round-6 `ledger.md` requirement was superseded in round-7 by `Requirement: Deferred-by-Design Document`; the `ledger.snapshot.sha256` tripwire was replaced by `deferred.snapshot.sha256` covering the new document. The round-8 reformulation additionally formalises path β via `Requirement: Upstream Absorption Verdict`, eliminating the round-7 ambiguity where source-level non-zero-demand constructions absorbed by upstream stages had to be force-fit into path α or shipped as in-change closures attacking nothing.
- **INV-INS-92**: For every enabled test method in `grammar-tests/`, there MUST be exactly one matrix row whose `Verdict ∈ {COVERED, EXPLICIT-NO-OP, NOT-NEEDED}` and `Evidence` column resolves to that method. Orphan tests and orphan rows MUST break the build. Post-round-8, no `@Disabled` annotation remains; `testSkipCountEqualsZero` SHALL enforce this.
- **INV-INS-93**: The matrix demand counts MUST be reproducible by `DemandCounter` invoked from `MatrixIntegrityTest.testSourceDemandCountsReproducible` AND `MatrixIntegrityTest.testPipelineDemandCountsReproducible`. Counts MUST be re-verified whenever a new `.mop` OR `.aj` file is added to any of the four corpora OR whenever the JavaMOP toolchain regenerates the `results/gh53_smoke_dexlib2/monitors/` outputs. `DemandCounter` SHALL scan BOTH `.mop` AND compiled `.aj` files via two distinct helpers (`countMop` and `countCompiledAj`); the per-designator regex SHALL distinguish *pointcut* uses from *Java statement* uses; the helper MUST be portable Java.
- **INV-INS-94**: For every matrix row covered by the **twelve round-10 in-change closures** (§4.{O,R,N,V,X,TT,AT,Y,T,B,D,I} — §4.E and §4.W removed per AA/AB-decisions; §4.JP folded into §4.Y per AC-decision), the `Verdict` MUST be `COVERED` and the `Evidence` MUST cite an enabled test in `grammar-tests/` exercising the corpus pattern that motivated the closure. `MatrixIntegrityTest.testRoundEightClosuresAreCovered` SHALL fail the build if any of these rows regresses from `COVERED`. (Test method name retained for cross-commit stability; it asserts the round-10 twelve-closure set.)
- **INV-INS-95**: The fourteen round-8 closures SHIP as bisect-friendly atomic commits (one closure per commit, §4.{W,O,R,N,V,X,TT,AT,Y,T,B,D,I,E} in tasks). For every commit landing a closure, the matrix row flip (`SILENT-GAP` → `COVERED`) MUST occur in the same commit; orphan tests and orphan rows are caught by INV-INS-92. `MatrixIntegrityTest.testClosureLocFootprintMatchesMatrixDelta` SHALL log (advisory; non-blocking) the LOC delta per closure commit and the number of matrix rows flipped.
- **INV-INS-96**: (Round-8 introduction.) For every matrix row with `Verdict = NOT-NEEDED β`, the assertion test SHALL exercise THREE properties: (a) `DemandCounter.countMop(designator) ≥ 1` to confirm source-level demand exists; (b) `DemandCounter.countCompiledAj(designator) == 0` to confirm pipeline absorption; (c) the named upstream absorber file/module exists and contains the documented evidence anchor. The test FAILS if any of the three properties changes — guarding against silent regression of an upstream stage that would re-surface the construction at the instrumenter without notice. `AbsorptionClaimsContractTest` SHALL aggregate all path-β absorber assertions.
- **INV-INS-97**: (Round-8 introduction; **round-8 empirical revision 2026-05-28** — the round-7/early-round-8 draft assumed a new `namedPointcuts: Map<String, PointcutExpression>` field would be added cross-repo to the JavaMOP-emitted `AspectDescriptor` JSON. Empirical inspection of `descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/AspectDescriptor.java` and the production JSON fixture `descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` proved that the schema already exposes a load-bearing `baseAspectExclusions: List<String>` field — the pre-expanded output of `BaseAspect.notwithin()` populated by `javamop.output.descriptor.DescriptorWriter#defaultBaseAspectExclusions()` (twelve package patterns including `sun..*`, `java..*`, `mop..*`, `com.runtimeverification..*`). The cross-repo `namedPointcuts` change is therefore RETIRED.) The `AspectDescriptor` schema MUST continue to carry the existing `baseAspectExclusions: List<String>` field as the source of truth for `BaseAspect.notwithin()` expansion. The `NamedRefPC` matcher MUST resolve the literal reference `BaseAspect.notwithin` against `descriptor.getBaseAspectExclusions()` (consumed by the §4.B `BaseAspectExpander`); any other `NamedRefPC` name not recognised by the matcher MUST cause `UnresolvedNamedRefException` (fail-closed). `NamedRefResolverTest` SHALL cover three paths: (a) successful `BaseAspect.notwithin` expansion against the canonical twelve-entry exclusion list; (b) fail-closed on unrecognised names; (c) fail-closed when `baseAspectExclusions` is empty (legacy descriptor). The round-8 archive precondition (tasks §0.5) is correspondingly downgraded from "verify cross-repo `namedPointcuts` emission" to "verify `baseAspectExclusions` is non-empty in production descriptors and matches the `defaultBaseAspectExclusions()` baseline".
- **INV-INS-98**: (Round-8 introduction; **round-8 hash-key revision 2026-05-28**.) The `MonitorRuntime.evaluateIf(int, Object[])` helper MUST exist in every generated `*RuntimeMonitor` class for specs that use the `if(...)` PCD. The helper's switch-case MUST contain one arm per `ifId` assigned at descriptor-emission time. **Hash-key contract (round-8 cross-LLM convergence)**: `ifId` is derived from a content hash of the `if(...)` clause, NOT from source-order traversal — `ifId = (int) (SHA1_first_8_bytes(normalize(pointcut_expr) + " " + advice_form + " " + aspect_FQN) & 0x7FFFFFFF)`, where `normalize` strips comments and inter-token whitespace and lower-cases keywords. Both the dexlib2 weaver and the JavaMOP `MonitorRuntimeIfHelperEmitter` MUST derive `ifId` from the same hashing function and the same canonical inputs (aspect FQN + advice form + normalised pointcut expression); cross-repo reordering of clauses is therefore stable by construction. **ABI contract**: `evaluateIf(int ifId, Object[] args)` receives `args` ordered as (a) advice-bound values from `target(name)` and `args(name1, name2, ..)` in source-order, then (b) `thisJoinPoint` if referenced, then (c) `returning(name)` / `throwing(name)` if applicable. Primitive bindings are boxed via the standard `Integer.valueOf` / `Boolean.valueOf` / `Long.valueOf` family. The argument-name → array-index mapping is generated alongside the switch-case in `*RuntimeMonitor` and emitted as a static final `String[] $ifIdArgs<ifId>` constant for debuggability. The default-case arm MUST throw `IllegalStateException("evaluateIf invoked with unknown ifId=" + ifId)` — silent `return false` is forbidden because it would suppress monitor events without trace. `IfRuntimeDelegationTest` SHALL verify (a) the weaver emits `ifId` values derived from the content hash (regenerate two `.aj` files with clauses re-ordered → same `ifId`s); (b) the helper switch-case covers every assigned `ifId`; (c) the boolean expression for each `ifId` matches the source-level `if(<expr>)` payload semantics; (d) the default-case throws `IllegalStateException`.

#### Scenario: ifId is derived from content hash, not source-order

- **WHEN** a `.aj` file declares two `if(...)` clauses A and B, and a second `.aj` file declares the same clauses in reverse order
- **THEN** the `ifId` for clause A SHALL be identical in both files
- **AND** the `ifId` for clause B SHALL also be identical in both files
- **AND** the dexlib2 weaver and the JavaMOP `MonitorRuntimeIfHelperEmitter` SHALL agree on the assigned `ifId` value for every `if(...)` clause regardless of which side parses the file first

#### Scenario: evaluateIf default-case is fail-loud

- **WHEN** `*RuntimeMonitor.evaluateIf(int ifId, Object[] args)` is invoked with an `ifId` value that does not match any generated switch-case arm
- **THEN** the helper SHALL throw `IllegalStateException("evaluateIf invoked with unknown ifId=" + ifId)`
- **AND** the exception SHALL propagate to the calling thread, surfacing the mismatch at runtime rather than silently short-circuiting the monitor invocation
- **INV-INS-99**: (Round-8 round-7-supersession.) The round-7 invariants INV-INS-96 (substrate contract), INV-INS-97 (FQN remap), INV-INS-99 (Coverage.aj e2e) are SUPERSEDED — those invariants asserted properties of artefacts that round-8 does not ship (the `aspectjlang/` substrate and the Coverage.aj end-to-end smoke test). The round-8 renumbering preserves INV-INS-96 (path-β absorber contract), INV-INS-97 (namedPointcuts schema), INV-INS-98 (if-runtime-delegation) as the active invariants in the 96-98 slot. The round-7 numbering above 100 (none existed) is unaffected.
- **INV-INS-100**: The `deferred.md` document MUST contain exactly one entry per matrix row with `Verdict ∈ {EXPLICIT-NO-OP, NOT-NEEDED}` (path α and path β). The document is content-addressed via `deferred.snapshot.sha256` (committed to `grammar-tests/src/test/resources/`); `testDeferredDocumentIsFrozenPostArchive` SHALL verify the live document's SHA against the snapshot and fail if they diverge. Round-8 race-condition fix: the snapshot generation SHALL occur in the same commit as the final `deferred.md` edit (tasks §1.4) to eliminate the round-7 race between `deferred.md` mutations during closure implementation and the post-archive snapshot creation.
- **INV-INS-101**: (Round-8 introduction — Z-decision per cross-LLM meta-review.) The §4.B `BaseAspectExpander` consumes a `List<String>` whose canonical length in production is twelve (per `DescriptorWriter.defaultBaseAspectExclusions()`); the matcher behaviour MUST be tested at N≥2 to guarantee future-proofing against descriptors that override `--baseaspect` with shorter lists. `NamedReferenceGrammarTest.baseAspectNotwithinExpandsTwelveExclusionsList` SHALL exercise (a) the canonical twelve-entry expansion (production baseline); (b) a synthetic two-entry list (smallest non-degenerate AND-chain — `["foo..*", "bar..*"]`); (c) a synthetic one-entry list (degenerate AND-of-one returns the single `NotWithinPC` directly); (d) the empty-list fail-closed case (`LegacyDescriptorException` per INV-INS-97).
- **INV-INS-102**: (Round-8 introduction — W-decision per cross-LLM meta-review.) `docs/aspectj_grammar_coverage.md` is the **single source of truth** for the dexlib2 AspectJ surface. The legacy inventory documents at `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and `docs/AJ_TO_DEXLIB2_MAPPING.md` SHALL carry a header banner declaring "SUPERSEDED — see `docs/aspectj_grammar_coverage.md` as the live contract; this file preserved as historical inventory only" and SHALL NOT be cited by any test, scenario, or invariant in this delta spec. `MatrixIntegrityTest.testNoCompetingSourceOfTruth` SHALL fail the build if either legacy document is amended without the banner present (a `git grep -L 'SUPERSEDED' docs/AJ_CONSTRUCTIONS_INVENTORY.md docs/AJ_TO_DEXLIB2_MAPPING.md` style check).
