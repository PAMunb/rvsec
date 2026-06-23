# Instrumentation — Delta Spec for gh62-aspectj-grammar-coverage (round-11)

> **ROUND-11 BANNER (2026-05-29) — AUTHORITATIVE OVERRIDE (supersedes the Round-10 banner below)** — full evidence: `EMPIRICAL-DEMAND.md` Round-11 addendum. A root-cause re-audit corrected round-10 rationales/counts and made both hard closures fork-free:
> - **§4.E / §4.W absorber = `coverage-weaver`** (NOT "JavaMOP call-rewrite" / "MOP macro-body"). The sole real consumer of positive `execution()` and positive `within()` is the hand-written `aspect/Coverage.aj` (`execution(* *.*(..))` at `:50`; the `excludedPackages()` macro), absorbed by `coverage-weaver`. `.mop` demand = 0. JavaMOP emits the pointcut keyword verbatim (`DumpVisitor.java:558`) — there is no execution→call rewrite. The round-10 "Source = 1,24,0,28 / 22,13,0,13" counts were grepped from git-ignored `-s` stray `.aj` artifacts (`MOPStatistics.java:69-78` emits the `ForkedBooter` stats dump only under `-s`); `DemandCounter.countMop()` scans **only `*.mop`** (+ `aspect/Coverage.aj`).
> - **§4.R REMOVED — NOT-NEEDED α** (`T+` in `call()` return = 0 in `.mop`, `Coverage.aj`, all 3 pipeline `.aj`). **Closure count 12 → 11** (§4.{O,N,V,X,TT,AT,Y,T,B,D,I}).
> - **§4.Y fork-free**: ship minimal `org.aspectj.lang.Signature` + `ClassSignature(Class)` in `rvsec-core` (already dexed); weaver emits `const-class`+`new-instance`+`invoke-direct`+`invoke-static` at `<clinit>` (monitor body only calls `getDeclaringType()`); `StaticInitializationEmitter` special-cases the `getSignature()` arg token. NO JavaMOP change.
> - **§4.I fork-free**: D13 runtime-delegation (`evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter`) RETIRED (exists in neither fork); complete the `IfGuardEmitter` stub with direct DEX lowering of the two corpus shapes (`o==null`, `!Thread.holdsLock(o)`) + fail-loud default. NO JavaMOP change, NO `ifId`.
> - **Counts**: §4.X = 13 (was 14); §4.V = 6 jca (resolves PROVISIONAL); §4.N = 14+2; others confirmed.
>
> Where any narrative below — including the Round-10 banner — conflicts with this banner, this banner wins.

> **ROUND-10 BANNER (2026-05-29) — subordinate to the Round-11 banner above** (see `EMPIRICAL-DEMAND.md` for the full evidence chain). An empirical pipeline-level demand audit against `empirical-monitors/{jca,generic,generic_new}/` revised three classifications:
>
> - **AA-decision**: §4.E `execution(...)` — pipeline POSITIVE = 0,0,0 → **NOT-NEEDED β** (was COVERED in round-9). Absorber: `coverage-weaver` (round-11 R11.2 correction — NOT "JavaMOP compiler call-rewrite"; JavaMOP emits `execution()` verbatim, the sole consumer is `Coverage.aj:50`). `ExecutionPointcutGrammarTest.executionPositiveAbsorptionAssertion` enforces.
> - **AB-decision**: §4.W positive `within(typePattern)` simple `pkg..*` — pipeline POSITIVE = 0,0,0 → **NOT-NEEDED β** (was COVERED in round-9). Absorber: `coverage-weaver` (round-11 R11.2 correction — NOT "MOP macro-body"; the sole consumer is `Coverage.aj`'s `excludedPackages()` macro). `WithinPositiveGrammarTest.withinPositiveAbsorptionAssertion` enforces.
> - **AC-decision**: §4.JP `thisJoinPoint*` `getStaticPart().getSignature()` — 3 live sites in `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328` → **REMOVED from path-β; capability reactivated as §4.Y Signature-delivery sub-closure (COVERED)**. The Coverage.aj absorption claim covers coverage-logging use only.
>
> **Closure count**: 14 → **12** (§4.E and §4.W exit; §4.JP folds into §4.Y).
> **Count corrections** (applied below per-row): §4.I 8→3, §4.T 2→1, §4.Y 6→3+Signature, §4.TT 44→22, §4.AT 10→5, §4.N 32→16, §4.O ~73→64, §4.X ~16→13 (round-11).
>
> Where any narrative below conflicts with this banner, this banner wins. Round-8/9 framing preserved for historical context.

## ADDED Requirements

### Requirement: AspectJ Grammar Coverage Matrix as Contract

The dexlib2 instrumenter (`rvsec-android/rvsec-instrumentation-dexlib2/`) SHALL document the AspectJ pointcut surface it supports as a **grammar coverage matrix** anchored to the AspectJ Programming Guide §"Pointcuts" grammar and the AspectJ 5 quick reference. The matrix lives at `docs/aspectj_grammar_coverage.md` in the rv-android repository and is the authoritative contract for what dexlib2 weaves correctly today.

For every production listed under the **closed enumeration** below, the matrix SHALL contain exactly one row with the following columns:

- **AspectJ syntax** — the normative form (e.g. `call(MethodPattern)`, `args(name)`, `T+`, `after() throwing(Id):`).
- **SourceDemand** — integer counts per `.mop`/`.aj` source corpus shipped by the project (`aspect/Coverage.aj`, `jca/`, `generic/`, `generic_new/`). Counts SHALL be produced by `DemandCounter.countMop(designator, corpus)`.
- **PipelineDemand** — integer counts per **post-JavaMOP-compilation** corpus, measured against the committed `empirical-monitors/{jca,generic,generic_new}/` snapshot in the change directory — the canonical pipeline corpus, byte-identical to a fresh `rv-monitor-generator` run WITHOUT `-s` (`results/gh53_smoke_dexlib2/monitors/` is an optional regeneration input, NOT the canonical path). Counts SHALL be produced by `DemandCounter.countCompiledAj(designator, corpus)`. **Round-8 introduction**: this column is the authoritative demand signal for scope decisions — closures ship in-change when PipelineDemand ≥ 1, not when SourceDemand ≥ 1. Divergences between SourceDemand and PipelineDemand surface upstream absorption (see `Requirement: Upstream Absorption Verdict` below).
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

**Runtime linkage**: `org.aspectj.lang.JoinPoint` class *(plus `JoinPoint.StaticPart`)* availability in the instrumented bytecode. **Round-8**: this row's verdict is `NOT-NEEDED β` with `coverage-weaver` as the named upstream absorber; the round-7 plan to ship a local `br.unb.cic.rv.aspectjlang.*` substrate is dropped (see `deferred.md` §2.2.1-D). **Round-11 scope correction**: `org.aspectj.lang.Signature` is NO LONGER part of this NOT-NEEDED β row — it is `COVERED` via §4.Y, which ships the minimal `org.aspectj.lang.Signature` + `ClassSignature` substrate in `rvsec-core` (only `getDeclaringType()` exercised) for `staticinitialization` advice bodies. This row covers the `JoinPoint` family only; Signature delivery is governed by the §4.Y Signature-delivery scenario and the reflective-API `JoinPoint.getSignature()` row.

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

- **WHEN** a reviewer runs `DemandCounter.countAllMop()` against `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/` AND `DemandCounter.countAllCompiledAj()` against the committed `empirical-monitors/{jca,generic,generic_new}/` snapshot (the canonical pipeline corpus; `results/gh53_smoke_dexlib2/monitors/` is an optional byte-identical regen input)
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

**Round-11 in-change closures (11)** *(round-10 twelve minus §4.R per R11.3)*

*(Numbered slots 1-14 are preserved for ordinal-stability cross-referencing; items 1, 3, 14 are placeholders pointing at NOT-NEEDED reclassifications — the active scope is exactly the eleven un-struck entries.)*

1. ~~**§4.W**~~ — **NOT-NEEDED β (absorber = `coverage-weaver`)**: pipeline POSITIVE `within(...)` = 0; sole positive consumer is `Coverage.aj` `excludedPackages()`. See `deferred.md` §2.2.1 entry I.
2. **§4.O** — `T+` in `call()` owner (R11: 64 sites generic_new).
3. ~~**§4.R**~~ — **REMOVED — NOT-NEEDED α (R11.3)**: `T+` in `call()` return = 0 in `.mop`, `Coverage.aj`, and all 3 pipeline `.aj`. All subtype use is owner-position (§4.O).
4. **§4.N** — `!target(T)` / `!args(T)` parser specialization (R11: 14 + 2 = 16 sites generic_new).
5. **§4.V** — `(T, ..)` trailing-mixed varargs (R11: **6 jca sites** — resolves PROVISIONAL).
6. **§4.X** — method-name glob `name*` (R11: **13 sites** generic_new — corrected from 14).
7. **§4.TT** — `target(Type)` type-matching (R11: 22 sites generic_new).
8. **§4.AT** — `args(Type)` type-matching (R11: 5 sites generic_new).
9. **§4.Y** — `staticinitialization(T+)` synthesis (R11: 3 sites generic_new) **+ fork-free `org.aspectj.lang.Signature` delivery** for `*staticinitEvent(Signature)`: ship a minimal `org.aspectj.lang.Signature` interface + `ClassSignature(Class)` impl in `rvsec-core` (already dexed; monitor body only calls `getDeclaringType()`); weaver emits `const-class`+`new-instance`+`invoke-direct`+`invoke-static` at the statically-known `<clinit>`; `StaticInitializationEmitter` special-cases the `thisJoinPoint.getStaticPart().getSignature()` arg token (today → `UnresolvedBindingException` → skipped). NO JavaMOP change (R11.5).
10. **§4.T** — `after() throwing(...)` end-to-end install (R11: 1 site generic_new).
11. **§4.B** — `BaseAspect.notwithin()` macro expansion (AND-chain `!within(p1) && … && !within(pN)`).
12. **§4.D** — `NamedRefPC` resolver via the existing `baseAspectExclusions` field.
13. **§4.I** — `if(...)` AspectJ PCD via **fork-free in-weaver 2-shape lowering** (R11.5: completes the `IfGuardEmitter` stub for `o==null` and `!Thread.holdsLock(o)`, fail-loud default; the round-8 D13 `evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter` runtime-delegation ABI is RETIRED — it exists in neither fork). 3 sites generic_new.
14. ~~**§4.E**~~ — **NOT-NEEDED β (absorber = `coverage-weaver`)**: pipeline POSITIVE `execution(...)` = 0; sole consumer is `Coverage.aj:50` `execution(* *.*(..))`, absorbed by `coverage-weaver`. `.mop` demand = 0; JavaMOP does NOT rewrite execution→call (R11.2). See `deferred.md` §2.2.1 entry H.

**Round-7 closures reclassified to NOT-NEEDED β in round-8 (7)** — see `deferred.md` §2.2.1 for the full evidence base:

- **§4.G `condition(...)` guard emit** → absorbed by JavaMOP compiler.
- **§4.S `__STATICSIG` macro support** → absorbed by JavaMOP compiler (generic_new audit PASS 2026-05-26).
- **§4.A `adviceexecution()` real semantics** → vacuously true in dexlib2 inline-call emission model.
- **§4.RT AspectJ runtime substrate** (~600 LOC + ~150 LOC remap) → absorbed by `coverage-weaver` (Coverage.aj was sole consumer of substrate; Coverage.aj absorbed).
- **§4.JP `thisJoinPoint*` bindings** (~250 LOC) → absorbed by `coverage-weaver` (Coverage.aj) and JavaMOP compiler (`__STATICSIG`).
- **§4.CV Coverage.aj end-to-end** → absorbed by `coverage-weaver` (byte-for-byte equivalent per module javadoc).
- **§4.WW `within(*..Log)` + `within(Coverage+)`** → absorbed by `coverage-weaver` (only Coverage.aj used these forms).

**Note**: round-8 initially planned to also reclassify §4.E to NOT-NEEDED β. Round-9 RESTORED §4.E as defensive shipping per user decision 2026-05-26. **Round-10 AA-decision 2026-05-29 re-RECLASSIFIED §4.E to NOT-NEEDED β** based on empirical pipeline POSITIVE = 0 across all three corpora — see closure #14 above and `deferred.md` §2.2.1 entry H.

#### Scenario: positive within(typePattern) absorbed by coverage-weaver (round-10 AB-decision / round-11 R11.2 absorber correction, REPLACES round-8 §4.W matcher scenario)

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

#### Scenario: T+ in call() return position is NOT-NEEDED α (round-11 R11.3 — §4.R REMOVED)

- **WHEN** a reviewer audits demand for `T+` in `call()` RETURN position (the `+` on the return-type token)
- **THEN** `DemandCounter.countMop` and `countCompiledAj` SHALL both equal 0 across `.mop`, `aspect/Coverage.aj`, and all three pipeline `.aj` — all subtype polymorphism is in the OWNER position (§4.O)
- **AND** the matrix row carries `Verdict = NOT-NEEDED α`; no matcher code ships for return-position `T+`

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
- **THEN** the `NamedRefPC` matcher SHALL recognise the literal reference `BaseAspect.notwithin` and, via the §4.B `BaseAspectExpander`, compose an **AND-chain** of `!within(<pattern>)` matchers — one per entry of `descriptor.getBaseAspectExclusions()` (matches the source `notwithin()` macro, which is `!within(p1) && !within(p2) && … && !within(pN)`; the class is woven only when it is outside **every** excluded package — an OR-chain would accept almost everything and is incorrect)
- **AND** the composed matcher SHALL be combined with the rest of the `commonPointcut` expression via the existing parser AST
- **AND** when the `NamedRefPC` name is NOT `BaseAspect.notwithin` AND the `AspectDescriptor` carries no other recognised named reference, the matcher SHALL fail closed by throwing `br.unb.cic.rv.pointcut.UnresolvedNamedRefException` carrying the name and the descriptor's `aspectName` — this aligns with the gh62 goal of eliminating silent always-match paths (P3 / round-8 fail-closed policy) and replaces the round-7 always-match-with-WARN fallback flagged as a "trap" by the cross-LLM meta-reviews
- **AND** when `descriptor.getBaseAspectExclusions()` returns an empty list (legacy descriptor produced by a JavaMOP build pre-dating the `baseAspectExclusions` field), the matcher SHALL fail closed with `LegacyDescriptorException` so the instrumenter regenerates the descriptor against the current JavaMOP toolchain rather than silently inlining a permissive filter

#### Scenario: weaver composes commonPointcut before matching (round-11 — closes the §4.B/§4.D integration gap)

- **WHEN** the weaver (`dex-mutator/.../DexWeaver`) evaluates an advice against a candidate instruction
- **THEN** it SHALL match against the AND-composition `CombinedPC(AND, parse(descriptor.getCommonPointcut()), parse(advice.getExpression()))` — NOT the advice expression in isolation — because the `NamedRefPC("BaseAspect.notwithin")` and `!within(...)` exclusion clauses live ONLY in the descriptor's top-level `commonPointcut` field, never in the per-advice `expression` field (verified against `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.json`)
- **AND** this composition is the load-bearing prerequisite for §4.B/§4.D: today `DexWeaver.parseCached` parses ONLY `advice.getExpression()` and `descriptor.getCommonPointcut()`/`getBaseAspectExclusions()` have ZERO production call-sites, so the production parse path never constructs a `NamedRefPC` node — §4.B/§4.D would resolve a node that never exists and the exclusion filter would be silently dropped (preserving the very silent-widening gh62 exists to eliminate)
- **AND** the parsed `commonPointcut` SHALL be cached per descriptor (parsed once, reused across all advices of that descriptor)
- **AND** a class whose fully-qualified name falls under any `baseAspectExclusions` pattern (e.g. `mop..*`, `java..*`) SHALL produce NO match even when its bytecode contains a call site whose signature matches the advice's `call(...)` clause
- **AND** a class outside every exclusion pattern SHALL match exactly as today
- **AND** `DexWeaverCommonPointcutCompositionTest` SHALL assert: (a) a class under `mop..*` yields zero matches despite a matching call-site signature; (b) a class outside all exclusions still matches; (c) the `commonPointcut` AST is parsed exactly once per descriptor

#### Scenario: §4.T after-throwing and §4.I if-guard compose on the shared join point (round-11 M1)

- **WHEN** the weaver processes the `Comparable_CompareToNullException_badexception` pointcut — `call(* Comparable+.compareTo(..)) && args(o) && if(o == null)` — whose `after() throwing(Exception e)` advice (`empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:294`) shares ONE join point with the `if(o == null)` guard (`:205`); this is the sole `after() throwing` demand site in the entire corpus AND it is simultaneously an §4.I `if(...)` site
- **THEN** the §4.T after-throwing handler-side advice invoke SHALL itself be gated by the §4.I `o == null` guard: the advice fires only when the caught exception arose with `o == null`, matching AspectJ semantics where the advice is bound by the FULL pointcut (including the `if`), NOT by `call() && args(o)` alone
- **AND** the §4.I `if-nez vO, :skip` guard SHALL gate the handler-side advice invoke (not only a `before`/`after returning` invoke at the normal-flow site), so an exception thrown with non-null `o` does NOT fire the after-throwing advice
- **AND** `DexWeaverIfGuardedAfterThrowingTest` SHALL exercise this shared site and assert the after-throwing advice fires when `o == null` and is skipped when `o != null`

#### Scenario: if(...) PCD short-circuits via fork-free in-weaver 2-shape lowering (round-11 R11.5 — REPLACES the round-8 runtime-helper delegation scenario)

- **WHEN** an advice `before() : call(* Object+.wait(..)) && target(o) && if(!Thread.holdsLock(o))` (or `... && args(o) && if(o == null)`) is woven
- **THEN** the weaver (`IfGuardEmitter.emit()`) SHALL read the bound register for `o` from `ctx.match` (already resolved from `target(o)`/`args(o)`) and the expression text from `IfPC.javaExpression`, and lower the guard inline into DEX:
  - for `o == null` → `if-nez vO, :skip_monitor` (skip the monitor invoke when `o` is non-null)
  - for `!Thread.holdsLock(o)` → `invoke-static {vO}, Ljava/lang/Thread;->holdsLock(Ljava/lang/Object;)Z` + `move-result vGuard` + `if-nez vGuard, :skip_monitor` (skip when the lock IS held)
- **AND** the monitor invoke and the `:skip_monitor` label SHALL be placed so the invoke is skipped exactly when the guard is false
- **AND** any `if(<expr>)` shape OTHER than the two above SHALL fail loud with `UnsupportedAspectConstructError` (no silent always-match) — a future shape forces a new sub-change
- **AND** NO `MonitorRuntime.evaluateIf`, NO `ifId`, and NO fork-side `*RuntimeMonitor` helper are generated (the round-8 D13 delegation ABI is RETIRED; `evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter` exist in neither fork)

#### Scenario: execution(...) absorbed by coverage-weaver (round-11 R11.2, REPLACES the round-10 "JavaMOP call-rewrite" scenario)

- **WHEN** a reviewer audits demand for `execution(...)` POSITIVE
- **THEN** `DemandCounter.countMop(EXECUTION_POSITIVE, {jca,generic,generic_new})` SHALL equal 0 (the `.mop` specs use only `call()`)
- **AND** `DemandCounter.countCompiledAj(EXECUTION_POSITIVE, {jca,generic,generic_new})` SHALL equal 0 (the only `execution(` substring is `!adviceexecution()` in `MOP_CommonPointCut`)
- **AND** the sole real `execution(...)` consumer SHALL be the hand-written `aspect/Coverage.aj:50` `execution(* *.*(..))`, which is absorbed by the `coverage-weaver` module (NOT by any JavaMOP execution→call rewrite — JavaMOP emits the pointcut keyword verbatim, `DumpVisitor.java:558`)
- **AND** `ExecutionPointcutGrammarTest.executionPositiveAbsorptionAssertion` SHALL pin this verdict with absorber = `coverage-weaver`, and fail the build if any future corpus introduces `countCompiledAj(EXECUTION_POSITIVE) > 0`

#### Scenario: staticinit advice receives org.aspectj.lang.Signature (round-10 AC-decision — §4.Y Signature-delivery sub-closure)

- **WHEN** a class without `<clinit>` is matched by `staticinitialization(T+)` AND the JavaMOP-compiled advice body invokes `thisJoinPoint.getStaticPart().getSignature()` (the canonical generic_new staticinit pattern — see `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328`)
- **THEN** the `StaticInitSynthesizer` SHALL append a minimal `<clinit>` containing the advice invocation + `return-void`, flagged `weaver-synthesized`
- **AND** the `Signature` argument SHALL be supplied **fork-free** (R11.5): `rvsec-core` ships a minimal `org.aspectj.lang.Signature` interface + `org.aspectj.lang.ClassSignature` one-field impl holding the declaring `java.lang.Class` (only `getDeclaringType()` is exercised by the monitor body — `MultiSpec_1RuntimeMonitor.java:1524`). `rvsec-core` is already on the dexlib2 packaging allowlist, so the substrate ships without re-introducing aspectjrt; the JavaMOP fork is NOT changed
- **AND** at the statically-known `<clinit>` the weaver SHALL emit `const-class vC, <DeclaringType>` + `new-instance vS, Lorg/aspectj/lang/ClassSignature;` + `invoke-direct {vS, vC}, ClassSignature.<init>(Ljava/lang/Class;)V` + `invoke-static {vS}, *staticinitEvent(Lorg/aspectj/lang/Signature;)V`, reusing the `CoverageWeaver` const+invoke + `RegisterShifter` register pattern
- **AND** `StaticInitializationEmitter` SHALL special-case the literal monitorCall arg token `thisJoinPoint.getStaticPart().getSignature()` (today routed through the generic binding resolver → `UnresolvedBindingException` → the site is silently skipped); the special-case SHALL be the only path that constructs the `ClassSignature`
- **AND** `StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent` SHALL verify, for a synthetic class mirroring the three live `generic_new` staticinit sites, that the woven `<clinit>` calls `*staticinitEvent` with a `ClassSignature` whose `getDeclaringType()` returns the matched class (assert `getDeclaringType() == Foo.class`, NOT merely non-null)

## Invariants

- **INV-INS-88**: For every row in the closed enumeration declared under `Requirement: AspectJ Grammar Coverage Matrix as Contract`, `docs/aspectj_grammar_coverage.md` MUST contain exactly one matrix row. New AspectJ versions or new corpora MUST result in a new row added by amendment, not implicit support.
- **INV-INS-89**: For every matrix row, the `Verdict` column MUST take exactly one value from the set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. `NOT-NEEDED` is permitted via exactly two paths: (path α) `DemandCounter.countMop` zero across all four corpora AND no parser/matcher/emitter implementation; OR (path β) the row reflects an AspectJ production with non-zero source-level demand absorbed by an upstream pipeline stage before reaching the dexlib2 pipeline. Path β requires the matrix Evidence column to (a) cite both source and pipeline demand counts, AND (b) name the upstream absorber from the set declared in `Requirement: Upstream Absorption Verdict`, AND (c) cite the empirical evidence (file:line or RELATORIO citation), AND (d) cite an enabled passing test asserting the absorption claim.
- **INV-INS-90**: For every matrix row with `Verdict = COVERED`, there MUST exist an enabled (non-`@Disabled`) passing test in `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` whose FQN appears in the row's `Evidence` column.
- **INV-INS-91**: (Round-8 reformulation.) The matrix MUST NOT contain any row with `Verdict = SILENT-GAP` post-archive. `MatrixIntegrityTest.testNoSilentGapRowsRemain` SHALL fail the build if any row carries `SILENT-GAP` after gh62 archives. The round-6 `ledger.md` requirement was superseded in round-7 by `Requirement: Deferred-by-Design Document`; the `ledger.snapshot.sha256` tripwire was replaced by `deferred.snapshot.sha256` covering the new document. The round-8 reformulation additionally formalises path β via `Requirement: Upstream Absorption Verdict`, eliminating the round-7 ambiguity where source-level non-zero-demand constructions absorbed by upstream stages had to be force-fit into path α or shipped as in-change closures attacking nothing.
- **INV-INS-92**: For every enabled test method in `grammar-tests/`, there MUST be exactly one matrix row whose `Verdict ∈ {COVERED, EXPLICIT-NO-OP, NOT-NEEDED}` and `Evidence` column resolves to that method. Orphan tests and orphan rows MUST break the build. Post-round-8, no `@Disabled` annotation remains; `testSkipCountEqualsZero` SHALL enforce this.
- **INV-INS-93**: The matrix demand counts MUST be reproducible by `DemandCounter` invoked from `MatrixIntegrityTest.testSourceDemandCountsReproducible` AND `MatrixIntegrityTest.testPipelineDemandCountsReproducible`. Counts MUST be re-verified whenever a new `.mop` OR `.aj` file is added to any of the four corpora OR whenever the JavaMOP toolchain regenerates the committed `empirical-monitors/` snapshot (the canonical pipeline corpus; `results/gh53_smoke_dexlib2/monitors/` is an optional byte-identical regen input). `DemandCounter` SHALL scan BOTH `.mop` AND compiled `.aj` files via two distinct helpers (`countMop` and `countCompiledAj`); the per-designator regex SHALL distinguish *pointcut* uses from *Java statement* uses; the helper MUST be portable Java. **Round-11 reproducibility pin**: each matrix row SHALL quote its per-designator `java.util.regex.Pattern` literal inline AND state the counting rule explicitly — (a) per-occurrence vs per-line (e.g. §4.O `T+`-owner counts per-occurrence of the `+.` owner token = 64, NOT the per-line figure of 39; a single pointcut line ORs several `Map+`/`Collection+` owners), and (b) whether negated forms are included and which row owns them (the negated `!target(Type)`/`!args(Type)` occurrences MUST be owned by exactly one of §4.TT/§4.AT or §4.N, not double-counted — disambiguate so `target(Type)` = 22 and `!target/!args` = 16 do not both claim the same 14 negated sites). Without these two rules pinned, `testPipelineDemandCountsReproducible` has no deterministic count to assert against.
- **INV-INS-94**: For every matrix row covered by the **eleven round-11 in-change closures** (§4.{O,N,V,X,TT,AT,Y,T,B,D,I} — §4.E/§4.W NOT-NEEDED β [absorber `coverage-weaver`]; §4.R NOT-NEEDED α [R11.3]; §4.JP folded into §4.Y), the `Verdict` MUST be `COVERED` and the `Evidence` MUST cite an enabled test in `grammar-tests/` exercising the corpus pattern that motivated the closure. `MatrixIntegrityTest.testRoundEightClosuresAreCovered` SHALL fail the build if any of these rows regresses from `COVERED`. (Test method name retained for cross-commit stability; it asserts the round-11 eleven-closure set.)
- **INV-INS-95**: The **eleven round-11 closures** SHIP as bisect-friendly atomic commits (one closure per commit, §4.{O,N,V,X,TT,AT,Y,T,B,D,I} in tasks). For every commit landing a closure, the matrix row flip (`SILENT-GAP` → `COVERED`) MUST occur in the same commit; orphan tests and orphan rows are caught by INV-INS-92. The NOT-NEEDED reclassification assertion tests (§4.E', §4.W' [coverage-weaver absorber], §4.R' [zero demand]) and the §4.Y.4-§4.Y.7 fork-free Signature-delivery sub-closure SHIP as their own atomic commits per tasks. `MatrixIntegrityTest.testClosureLocFootprintMatchesMatrixDelta` SHALL log (advisory; non-blocking) the LOC delta per closure commit and the number of matrix rows flipped.
- **INV-INS-96**: (Round-8 introduction.) For every matrix row with `Verdict = NOT-NEEDED β`, the assertion test SHALL exercise THREE properties: (a) `DemandCounter.countMop(designator) ≥ 1` to confirm source-level demand exists; (b) `DemandCounter.countCompiledAj(designator) == 0` to confirm pipeline absorption; (c) the named upstream absorber file/module exists and contains the documented evidence anchor. The test FAILS if any of the three properties changes — guarding against silent regression of an upstream stage that would re-surface the construction at the instrumenter without notice. `AbsorptionClaimsContractTest` SHALL aggregate all path-β absorber assertions.
- **INV-INS-97**: (Round-8 introduction; **round-8 empirical revision 2026-05-28** — the round-7/early-round-8 draft assumed a new `namedPointcuts: Map<String, PointcutExpression>` field would be added cross-repo to the JavaMOP-emitted `AspectDescriptor` JSON. Empirical inspection of `descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/AspectDescriptor.java` and the production JSON fixture `descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` proved that the schema already exposes a load-bearing `baseAspectExclusions: List<String>` field — the pre-expanded output of `BaseAspect.notwithin()` populated by `javamop.output.descriptor.DescriptorWriter#defaultBaseAspectExclusions()` (twelve package patterns including `sun..*`, `java..*`, `mop..*`, `com.runtimeverification..*`). The cross-repo `namedPointcuts` change is therefore RETIRED.) The `AspectDescriptor` schema MUST continue to carry the existing `baseAspectExclusions: List<String>` field as the source of truth for `BaseAspect.notwithin()` expansion. The `NamedRefPC` matcher MUST resolve the literal reference `BaseAspect.notwithin` against `descriptor.getBaseAspectExclusions()` (consumed by the §4.B `BaseAspectExpander`); any other `NamedRefPC` name not recognised by the matcher MUST cause `UnresolvedNamedRefException` (fail-closed). `NamedRefResolverTest` SHALL cover three paths: (a) successful `BaseAspect.notwithin` expansion against the canonical twelve-entry exclusion list; (b) fail-closed on unrecognised names; (c) fail-closed when `baseAspectExclusions` is empty (legacy descriptor). The round-8 archive precondition (tasks §0.5) is correspondingly downgraded from "verify cross-repo `namedPointcuts` emission" to "verify `baseAspectExclusions` is non-empty in production descriptors and matches the `defaultBaseAspectExclusions()` baseline".
- **INV-INS-98**: (**Round-11 R11.5 repurpose** — the round-8 `MonitorRuntime.evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter` runtime-delegation contract is RETIRED; it required fork-side generation and exists in neither the JavaMOP nor the RV-Monitor fork.) The `if(...)` PCD MUST be lowered **entirely in the dexlib2 weaver**, fork-free: `IfGuardEmitter.emit()` MUST recognise exactly the two expression shapes present in the corpus — `<bound> == null` (lowered to `if-nez <reg>, :skip`) and `!Thread.holdsLock(<bound>)` (lowered to `invoke-static Ljava/lang/Thread;->holdsLock(Ljava/lang/Object;)Z` + `move-result` + `if-nez`) — placing the monitor invoke after the skip-label so it is bypassed exactly when the guard is false. The bound register MUST come from `ctx.match` (`target`/`args` binding) and the expression text from `IfPC.javaExpression`. Any other shape MUST fail loud with `UnsupportedAspectConstructError` (no silent always-match). No `evaluateIf`, no `ifId`, no fork-side helper. `IfGuardLoweringTest` SHALL verify (a) the null-check shape lowers to `if-nez`; (b) the `holdsLock` shape lowers to `invoke-static` + branch; (c) an unsupported shape fails loud; (d) the monitor invoke is skipped exactly when the guard is false.

#### Scenario: unsupported if(...) shape fails loud at weave time (round-11 R11.5 — REPLACES the retired ifId/evaluateIf scenarios)

- **WHEN** the weaver encounters an `if(<expr>)` PCD whose `<expr>` is neither `<bound> == null` nor `!Thread.holdsLock(<bound>)` (the only two shapes in the corpus)
- **THEN** `IfGuardEmitter.emit()` SHALL throw `UnsupportedAspectConstructError` naming the unrecognised expression and the aspect — failing the build rather than emitting a silent always-match guard
- **AND** `IfGuardLoweringTest.unsupportedShapeFailsLoud` SHALL pin this behaviour; a future corpus introducing a new `if(...)` shape forces a new sub-change extending the lowering dispatch
- **INV-INS-99**: (Round-8 round-7-supersession.) The round-7 *meanings* of INV-INS-96 (substrate contract), INV-INS-97 (FQN remap), and INV-INS-99 (Coverage.aj e2e) are SUPERSEDED — those round-7 invariants asserted properties of artefacts that round-8+ does not ship (the `aspectjlang/` substrate and the Coverage.aj end-to-end smoke test). In the 96-98 slot the ACTIVE (round-8+) invariants are INV-INS-96 (path-β absorber contract), INV-INS-97 (`baseAspectExclusions` schema — the round-7 `namedPointcuts` plan was itself RETIRED), and INV-INS-98 (**round-11 R11.5: fork-free in-weaver `if()` lowering** — the round-8 `if`-runtime-delegation meaning is RETIRED). INV-INS-100/101/102 below are round-8 introductions, NOT round-7 invariants, and are unaffected by this supersession note (the earlier "round-7 numbering above 100 (none existed)" wording was itself stale — 100/101/102 now exist).
- **INV-INS-100**: The `deferred.md` document MUST contain exactly one entry per matrix row with `Verdict ∈ {EXPLICIT-NO-OP, NOT-NEEDED}` (path α and path β). The document is content-addressed via `deferred.snapshot.sha256` (committed to `grammar-tests/src/test/resources/`); `testDeferredDocumentIsFrozenPostArchive` SHALL verify the live document's SHA against the snapshot and fail if they diverge. Round-8 race-condition fix: the snapshot generation SHALL occur in the same commit as the final `deferred.md` edit (tasks §1.4) to eliminate the round-7 race between `deferred.md` mutations during closure implementation and the post-archive snapshot creation.
- **INV-INS-101**: (Round-8 introduction — Z-decision per cross-LLM meta-review.) The §4.B `BaseAspectExpander` consumes a `List<String>` whose canonical length in production is twelve (per `DescriptorWriter.defaultBaseAspectExclusions()`); the matcher behaviour MUST be tested at N≥2 to guarantee future-proofing against descriptors that override `--baseaspect` with shorter lists. `NamedReferenceGrammarTest.baseAspectNotwithinExpandsTwelveExclusionsList` SHALL exercise (a) the canonical twelve-entry expansion (production baseline); (b) a synthetic two-entry list (smallest non-degenerate AND-chain — `["foo..*", "bar..*"]`); (c) a synthetic one-entry list (degenerate AND-of-one returns the single `NotWithinPC` directly); (d) the empty-list fail-closed case (`LegacyDescriptorException` per INV-INS-97).
- **INV-INS-102**: (Round-8 introduction — W-decision per cross-LLM meta-review.) `docs/aspectj_grammar_coverage.md` is the **single source of truth** for the dexlib2 AspectJ surface. The legacy inventory documents at `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and `docs/AJ_TO_DEXLIB2_MAPPING.md` SHALL carry a header banner declaring "SUPERSEDED — see `docs/aspectj_grammar_coverage.md` as the live contract; this file preserved as historical inventory only" and SHALL NOT be cited by any test, scenario, or invariant in this delta spec. `MatrixIntegrityTest.testNoCompetingSourceOfTruth` SHALL fail the build if either legacy document is amended without the banner present (a `git grep -L 'SUPERSEDED' docs/AJ_CONSTRUCTIONS_INVENTORY.md docs/AJ_TO_DEXLIB2_MAPPING.md` style check).
