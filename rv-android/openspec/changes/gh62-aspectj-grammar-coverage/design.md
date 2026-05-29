# Design: gh62-aspectj-grammar-coverage

## Round-11 banner (2026-05-29) — AUTHORITATIVE OVERRIDE (supersedes Round-10 banner below)

A root-cause re-audit (full evidence: `EMPIRICAL-DEMAND.md` Round-11 addendum; mirrored in `proposal.md` Round-11 section) corrected several round-10 rationales/counts and made both hard closures fork-free. **Where this section conflicts with anything below — including the Round-10 banner — this section wins.**

| Item | Round-10 state | Round-11 state | Evidence |
|---|---|---|---|
| `.aj` divergence root cause | (unexplained; assumed JavaMOP absorption) | **`-s`/`-statistics` flag** emits the `ForkedBooter` stats dump (`MOPStatistics.java:69-78`); the `resources/*.aj` are git-ignored `-s` stray artifacts, NOT on the production path; JavaMOP unchanged | reproduced: `javamop -merge -n -s` → 23 blocks |
| §4.E `execution()` absorber | "JavaMOP rewrites execution→call" | **`coverage-weaver`** (sole consumer = `Coverage.aj:50`; JavaMOP emits verbatim, `DumpVisitor.java:558`). `.mop` demand = 0. NOT-NEEDED β | `Creation.mop.aj:45` keeps `execution()` |
| §4.W positive `within()` absorber | "no consumer / macro inflation" | **`coverage-weaver`** (only positive `within()` = `Coverage.aj` `excludedPackages()`). NOT-NEEDED β | `Coverage.aj:22-46` |
| §4.R `T+` in `call()` return | COVERED in-change | **REMOVED — NOT-NEEDED α** (demand = 0 in `.mop`, `Coverage.aj`, all 3 pipeline `.aj`) | 2 independent greps |
| §4.Y `Signature` delivery | (AC-decision; mechanism unclear; aspectjlang substrate dropped) | **fork-free**: minimal `org.aspectj.lang.Signature` + `ClassSignature(Class)` in `rvsec-core` (already dexed); weaver emits `const-class`+`new-instance`+`invoke-direct`+`invoke-static` at `<clinit>`; `StaticInitializationEmitter` special-cases the `getSignature()` arg token (today → `UnresolvedBindingException` → skipped) | `MultiSpec_1RuntimeMonitor.java:1524` only calls `getDeclaringType()` |
| §4.I `if()` PCD | D13 runtime-delegation (`evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter`) | **D13 RETIRED** — fork-free in-weaver 2-shape lowering completing the `IfGuardEmitter` stub (`o==null`, `!Thread.holdsLock(o)`, fail-loud default) | `evaluateIf`/`ifId` exist in neither fork |
| Counts | §4.X=14, §4.V=8/14 PROVISIONAL | **§4.X=13, §4.V=6 jca** (resolved); others confirmed | fresh-regen + empirical-monitors agree |
| `DemandCounter.countMop()` | scans `resources/{…}` (catches stray `.aj`) | scans **only `*.mop`** (+ `aspect/Coverage.aj`); stray `.aj` deleted in §0 | — |

**Closure count: 12 → 11** (§4.{O,N,V,X,TT,AT,Y,T,B,D,I}). **LOC: ~470-560** (~435-525 weaver/engine + ~35 `rvsec-core`).

## Round-10 banner (2026-05-29) — AUTHORITATIVE OVERRIDE (now subordinate to the Round-11 banner above)

A pipeline-level demand audit over freshly compiled monitors for all three corpora (preserved in `empirical-monitors/{jca,generic,generic_new}/`) revised three load-bearing classifications. **Where this section conflicts with any narrative below, this section wins**; the per-decision deltas are documented in `EMPIRICAL-DEMAND.md` and consumed by `proposal.md` Round-10 section.

| Decision | Closure | Round-9 status | Round-10 status | Empirical evidence |
|---|---|---|---|---|
| **AA** | §4.E `execution(...)` matcher + emitter | COVERED in-change (~230 LOC) | **NOT-NEEDED β** (absorbed by JavaMOP compiler) | Pipeline POSITIVE count = 0,0,0 across `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj`; only `!adviceexecution()` substring hits exist |
| **AB** | §4.W positive `within(typePattern)` simple `pkg..*` | COVERED in-change (~80 LOC) | **NOT-NEEDED β** (no positive consumer) | Pipeline POSITIVE count = 0,0,0; every `within(` hit is inside `notwithin()` or `MOP_CommonPointCut()` declarations |
| **AC** | §4.JP `thisJoinPoint*` / `Signature` | NOT-NEEDED β (alleged Coverage.aj absorption) | **COVERED inside §4.Y as Signature-delivery sub-closure** | 3 live `thisJoinPoint.getStaticPart().getSignature()` sites in `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328` (staticinit advice bodies) |

**Closure count**: 14 → **12** (§4.E and §4.W exit; §4.JP folds into §4.Y).
**LOC**: ~865-940 → **~565-660**.
**Bipartite smoke gate**: §4.O/§4.V/§4.B/§4.D validated against ≥10 JCA APKs on ART; §4.I/§4.Y/§4.X/§4.N/§4.TT/§4.AT/§4.T validated via `grammar-tests` fixture + `dexdump` (no current production APK exercises generic_new end-to-end — resolves round-9 H-iv).

Counts tightened by the same audit (kept as PROVISIONAL where pipeline re-grep is deferred):
- §4.I: 8 → **3** sites (generic_new)
- §4.T: 2 → **1** site (generic_new)
- §4.Y: 6 → **3** staticinit sites (generic_new) + 3 Signature-delivery sub-sites
- §4.TT: 44 → **22** sites (generic_new)
- §4.AT: 10 → **5** sites (generic_new)
- §4.N: 28 + 4 → **14 + 2** sites (generic_new)
- §4.O: ~73 → **64** sites (generic_new)
- §4.X: ~16 → **14** sites (generic_new)
- §4.V: PROVISIONAL (pipeline re-grep deferred)

The narrative below preserves round-7/8/9 framing as historical context. Any §4.E or §4.W in-change reference, any "fourteen closures" claim, or any round-9 LOC figure should be read THROUGH this banner.

## Context

The dexlib2 instrumenter has been built incrementally against the demand of the JCA spec set since `gh52` (initial port, 2026-Q1). Each subsequent gap — `gh56` wide-param binding, `gh57` static-analysis overhaul, `gh59` wide-slot tracking, `gh61` RegisterShifter frame growth + `Object+` in `call()` params — was framed and solved as a *single visible bug*. Production code that is silently wrong but parses-and-compiles is invisible to that posture.

Five rounds of cross-LLM artifact review (Codex GPT-5, DeepSeek, Gemini 2.5 Pro, Claude Opus 4.7) — round-3 audited the round-4 state, round-5 expanded D8 by nominal AspectJ family, round-6 (opus47_deep + four supporting reports) empirically refuted three round-5 premises and reframed D8 by corpus demand, and round-7 (this design) absorbs every non-zero-demand construction in-change after a direct audit of the project's **logging aspect** (`aspect/Coverage.aj`) — inverted the reactive lens. The reviews surfaced **five** classes of silent failure in the dexlib2 parser/matcher/emitter:

1. **Matcher always-match for unmodelled designators.** `PointcutMatcher.java:109-114` treats `IfPC`, `NamedRefPC`, and `WithinPC` as always-match. The parser routes every unmodelled *identifier-named* designator to `NamedRefPC` (`PointcutExpressionParser.java:131-132`), so `this`, `withincode`, `cflow`, `cflowbelow`, `handler`, `initialization`, `preinitialization`, `get`, `set`, and `adviceexecution` all silently match every join point. The AspectJ 5 `@*` family (`@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`) reaches a *different* failure mode: `PointcutExpressionParser.isIdentPart()` rejects `@` as part of an identifier, so the parser raises `PointcutParseException` before the `NamedRefPC` fallback fires. Same end-state verdict (SILENT-GAP — the exception is caught upstream and the pointcut is treated as inert) but a distinct code path. Matrix rows for the `@*` family MUST cite the parser-crash anchor (`PointcutExpressionParser.isIdentPart()`), NOT the matcher always-match anchor at `PointcutMatcher.java:109-114`.
2. **Malformed-descriptor exact-match for partially-modelled forms.** `T+` in `call()` owner position (`PointcutMatcher.java:153-157`), `T+` in return type, `*` wildcard in method name, and trailing-mixed `(T, ..)` varargs all produce descriptors like `Ljava/io/OutputStream+;` or `Ljava/lang/..;` that never match anything.
3. **Silent emitter no-op.** `DexWeaver.java:560-566` is `case TRY_CATCH_WRAP: case REPLACE: break;` — `after() throwing(...)` plans are generated by `AfterThrowingEmitter` and silently discarded by the weaver with no log, no counter, no exception. The earlier draft of this change misclassified `after throwing` as `EXPLICIT-NO-OP` and cited `DexWeaver.java:534-540`; that line range is the `MutableImplSupplier` interface (Codex/Deepseek concurring). The silent-discard is a **SILENT-GAP**, not a documented no-op.
4. **Demand-driven matcher/emitter gaps for MOP constructs that reach the pipeline (round-8 absorption-aware refinement).** Round-5 framed the fourth failure class as "wrong-payload emit in `ThisJoinPointEmitter.signatureFor()`"; round-6 cross-LLM review (opus47_deep) re-grepped the compiled monitor bytecode and found zero `org.aspectj.*` references — `signatureFor()` has zero callers in production. Round-7 attempted to ship closures for every source-level non-zero-demand construction (twenty closures). Round-8 audits proved that seven of those twenty target constructions the upstream pipeline absorbs before they reach the instrumenter (see "Round-7 closures reclassified to NOT-NEEDED β" below). The actual fourth class, after absorption, is the corpus-measured set of constructs whose dexlib2 path is silently broken AND that survive the upstream pipeline: positive `within(typePattern)` (28 sites at source, 26 sites at pipeline — matcher always-true at `PointcutMatcher.java:109-114`), `T+` in `call()` owner position (~73 sites, exact-equals at `PointcutMatcher.java:153-157`), `T+` in `call()` return (subset of owner), `!target(T)`/`!args(T)` (32 sites, parser collapses to `NamedRefPC`), method-name glob `name*` (~16 sites, exact-equals at `PointcutMatcher.java:161-167`), `(T, ..)` trailing-mixed varargs (14 jca + 2 generic_new), `target(Type)`/`args(Type)` type-matching (54 sites in generic_new), `staticinitialization` synthesis when `<clinit>` is absent (6 sites), `after() throwing(...)` end-to-end install (2 sites, plan discarded at `DexWeaver.java:560-566`), `BaseAspect.notwithin()` named-ref expansion (2 sites), `NamedRefPC` resolver via per-aspect symbol table needed by `BaseAspect.notwithin()` (1 entry per JCA descriptor — narrower than round-7's two-pointcut Coverage.aj demand), and `if(...)` AspectJ PCD via runtime-helper delegation (8 sites in generic_new). Closures ship with this change; see D8 for the round-6 redesign rationale, D9 for the round-8 absorption-aware refinement.

**Round-7 closures reclassified to NOT-NEEDED β in round-8** (full evidence in `deferred.md` §2.2.1; aggregated in `docs/analise_sintese_macro.md`):
- `condition(...)` (round-7 §4.G, 74 source sites) — absorbed by JavaMOP compiler into `*RuntimeMonitor.*Event(...)` method body; compiled `.aj` JCA has zero references.
- `__STATICSIG` macro (round-7 §4.S, 3 source sites in `generic_new/`) — expanded by JavaMOP compiler; compiled `.aj` JCA has zero references (generic_new audit pending as archive precondition).
- `adviceexecution()` (round-7 §4.A, 2 source sites — both in `commonPointcut: !adviceexecution()`) — vacuously true in dexlib2 inline-call emission model.
- AspectJ runtime substrate `br.unb.cic.rv.aspectjlang.*` (round-7 §4.RT, ~600 LOC + ~150 LOC remap) — sole consumer was `Coverage.aj` (absorbed by `coverage-weaver`).
- `thisJoinPoint*` bindings (round-7 §4.JP, ~250 LOC) — APK AJC inspection shows 115/115 MOP advices have zero `JoinPoint` references; only `Coverage.aj` consumed these.
- `Coverage.aj` end-to-end (round-7 §4.CV) — `coverage-weaver/CoverageWeaver.java:23-32` javadoc declares semantic equivalence; `experimento-20260508` (190 APKs) ran dexlib2 exclusively with coverage via `coverage-weaver`, NOT via `Coverage.aj`.
- `within(*..Log)` suffix-wildcard + `within(Coverage+)` `T+`-in-positive-within (round-7 §4.WW) — sole consumer was `Coverage.aj` (absorbed). The simple `within(pkg..*)` form remains in-change as §4.W (other consumers exist in JCA/generic_new descriptors).

Verified corpus demand (re-counted 2026-05-25 against `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/`, with patterns that distinguish *pointcut* uses from *method-name* uses):

- `get(FieldPattern)` / `set(FieldPattern)` as field-access pointcuts: **0** across all four corpora. (Earlier draft's count of 356/158 was a substring grep that conflated `call(* Foo.get(...))` and `call(* Foo.set(...))` method-name calls with field-access pointcuts.)
- `target(name)` / `args(name)` value-binding: high (dominant pattern in `jca/`, `generic/`, `generic_new/` — e.g. `call(* Hashtable.get(Object)) && target(h) && args(o)`; raw `target(`/`args(` counts: jca=128/159, generic=356/96, generic_new=108/47).
- `target(Type)` / `args(Type)` type-matching: present in `generic_new/`, currently SILENT-GAP.
- `this(...)` (both sub-semantics, as pointcut): **0** across all four corpora — matrix completeness only, no urgent demand. (Earlier draft claimed "present in generic_new"; verified zero.)
- `execution(...)` against placeholder matcher (`PointcutMatcher.java:307-313`): aspect=1, jca=23, generic=0, generic_new=27. (Earlier draft claimed 28 in `generic_new/` only and 0 elsewhere; verified counts above.)
- `if(...)` AspectJ PCD against always-match matcher (`PointcutMatcher.java:109-114`): aspect=0, jca=0, generic=0, generic_new=8. **Round-8 correction**: round-7's design.md previously claimed 8/16/0/37 — that count conflated AspectJ-PCD `if(<expr>)` clauses with Java-statement `if (cond) { ... }` blocks inside advice bodies. The real PCD count uses the composition-aware regex `(?:^|[&|(])\s*if\s*\(` which yields 0/0/0/8. The round-8 §4.I closure delegates evaluation to `MonitorRuntime.evaluateIf(ifId, args)` (runtime-helper delegation) instead of attempting in-weaver DEX lowering — see D13 below.
- `(T, ..)` trailing-mixed varargs: jca=14, generic_new=4. (Earlier draft claimed "4+ in jca"; verified 14.)
- `adviceexecution()`: jca=1, generic_new=1. Currently parsed as `NamedRefPC` at `PointcutExpressionParser.java:131` → matcher always-match. SILENT-GAP, not COVERED. (Earlier draft misclassified as COVERED; the parser fall-through to `NamedRefPC` is the same defective path as the AspectJ 5 `@*` family.)
- `within(...)` positive: aspect=24, jca=13, generic_new=13 (positives + negatives combined; the matcher conflates them).
- AspectJ 5 `@*` family: **0** across all four corpora — matrix completeness only.
- `after() throwing(...)` end-to-end: generic_new=2 — `DexWeaver.java:560-566` silently discards the plan.
- **Advice-body reflective API** (behavioural-parity surface — added in the round-3 review): `thisJoinPoint` binding = 3 in `generic_new/`; `thisJoinPointStaticPart` = 1 in `aspect/`; `JoinPoint.getSignature()` = 4 across `aspect/`+`generic_new/`; `Signature` subtypes (`MethodSignature`/`ConstructorSignature`/`FieldSignature`) = 7 in `aspect/Coverage.aj`. Zero-demand sub-rows (`getArgs()`, `getTarget()`/`getThis()`, `getKind()`/`getSourceLocation()`) are still Fix-now because they are structurally required for MOP monitors to receive non-empty events.
- **Aspect declaration mechanics**: `aspect Foo { ... }` = 5 across corpora; `pointcut p(): ...` named declaration = 4. The remaining sub-rows (abstract aspects, inheritance, `declare precedence`, privileged) have zero current demand but cover the AspectJ surface a future MOP spec could legitimately use.

The systemic shape is consistent: silent matcher behaviour (always-match or malformed-descriptor exact-match) and silent weaver discard are the dominant failure modes, not parser crashes or weaver exceptions. The standard test surface — green bar against the JCA fixtures — cannot detect any of it.

This change moves from per-bug fixes to a **grammar-anchored coverage matrix** whose four-value verdict vocabulary (`COVERED`, `SILENT-GAP`, `EXPLICIT-NO-OP`, `NOT-NEEDED`) is the new contract for what the dexlib2 instrumenter weaves correctly. The matrix is *executable*: every row is bound to a test in a new `grammar-tests/` Maven submodule, and every `SILENT-GAP` row is bound to an explicitly-disabled failing test so the inventory is visible at every CI run. `MatrixIntegrityTest` enforces both directions of the matrix↔tests link.

Relevant PRD references: **FR02** (APK instrumentation — round-6 D8 ships eight demand-driven closures plus a `NamedRefPC` resolver; the matrix documents the behavioural delta row by row) and **NFR03** (Testability — improved by the new executable oracle plus an empirical 5-APK smoke gate). (An earlier draft cited `NFR06 (Testability)` and `NFR07 (Documentation completeness)`; corrected against `docs/PRD.md` where NFR03=Testability, NFR06=Observability, NFR07=Compatibility, and no `Documentation completeness` NFR exists.)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Authoritative artefacts                                         │
│                                                                 │
│  ┌──────────────────────────────────────┐                       │
│  │ docs/aspectj_grammar_coverage.md     │  ← matrix document    │
│  │  (one row per enumerated production) │                       │
│  └──────────────┬───────────────────────┘                       │
│                 │ cites by FQN                                  │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                       │
│  │ rvsec-instrumentation-dexlib2/       │                       │
│  │   grammar-tests/ (Maven submodule)   │  ← executable oracle  │
│  │     src/test/java/.../grammar/       │                       │
│  │       MatrixIntegrityTest            │                       │
│  │       *PointcutGrammarTest           │                       │
│  │       util/{DemandCounter,           │                       │
│  │             MatrixMarkdownParser}    │                       │
│  └──────────────┬───────────────────────┘                       │
│                 │ exercises                                     │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                       │
│  │ pointcut-engine, advice-emitter,     │  ← targets of test +  │
│  │ dex-mutator (round-8 D9: 14 demand-  │     production code   │
│  │ driven closures + `NamedRefPC`       │     changes ship here │
│  │ resolver via baseAspectExclusions)   │                       │
│  └──────────────────────────────────────┘                       │
│                                                                 │
│  ┌──────────────────────────────────────┐                       │
│  │ openspec/changes/gh62-.../deferred.md│  ← deferred snapshot  │
│  │  (EXPLICIT-NO-OP + NOT-NEEDED α/β)   │     (replaces round-6 │
│  │  one-shot, content-addressed via SHA;│      ledger.md)       │
│  │  matrix has zero SILENT-GAP rows     │                       │
│  └──────────────┬───────────────────────┘                       │
│                 │ catalogues                                    │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                       │
│  │ Future sub-changes (gh-XX-*) open    │                       │
│  │ ONLY when pipeline demand surfaces   │                       │
│  │ for a deferred row (caught by        │                       │
│  │ testPipelineDemandCountsReproducible)│                       │
│  └──────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|----------------|-------|--------|
| `docs/aspectj_grammar_coverage.md` (NEW) | Authoritative matrix: one row per enumerated production with verdict, demand counts, and evidence anchors | AspectJ grammar reference + `.mop` corpora + dexlib2 source state | Markdown table; the contract |
| `grammar-tests/` Maven submodule (NEW) | Executable oracle: one test per matrix row, `@Disabled` for SILENT-GAP rows; bidirectional integrity check via `MatrixIntegrityTest` | Synthetic fixtures (and snippets from JCA `.mop` where realistic) | JUnit report; green bar for COVERED, visible skips for SILENT-GAP |
| `DemandCounter` (NEW, in `grammar-tests`) | Deterministic Java counter for `.mop` corpora; replaces shell grep + `ProcessBuilder` | `$RVSEC_HOME` path + designator regex map | Per-(designator, corpus) integer counts |
| `MatrixMarkdownParser` (NEW, in `grammar-tests`, ~thin wrapper) | Parses `docs/aspectj_grammar_coverage.md` table into `List<MatrixRow>` | Markdown file | Records consumed by `MatrixIntegrityTest`. Implemented on `commonmark-java` (test dep), not a custom parser |
| `openspec/changes/gh62-.../deferred.md` (NEW; replaces round-6 `ledger.md`) | One-shot snapshot of EXPLICIT-NO-OP + NOT-NEEDED rows (path α and path β); content-addressed via `deferred.snapshot.sha256` tripwire (D7). Replaces the round-6 `ledger.md` because round-8 archives with zero SILENT-GAP rows — no `Fix-now`/`Follow-up` bucket survives | Matrix non-COVERED rows + upstream absorption evidence | Categorised list with absorber names and empirical evidence paths |
| `pointcut-engine` / `advice-emitter` / `dex-mutator` (MODIFIED in round-6) | Existing instrumenter — exercised by `grammar-tests/` AND extended in-change by the eight demand-driven closures (§4.G/W/O/N/X/S/Y/T) + `NamedRefPC` resolver (§4.D) | DEX bytecode + pointcut expressions | Instrumented DEX with corrected behaviour for the nine flipped rows |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|----------------|------|
| AspectJ Grammar Coverage Matrix as Contract (R1) | `docs/aspectj_grammar_coverage.md` | `MatrixIntegrityTest.{testEveryDesignatorHasMatrixRow,testVerdictsAreValid,testCoveredRowsCiteEnabledPassingTests,testNonCoveredRowsAppearInDeferredDocument,testEnabledTestsResolveToValidMatrixRow,testNoDisabledTestsRemain,testSkipCountEqualsZero,testSourceDemandCountsReproducible,testPipelineDemandCountsReproducible}` (round-8 J-cleanup: round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry`/`testDisabledTestsResolveToSilentGapRow`/`testSkipCountEqualsSilentGapCount` are replaced — the matrix archives with zero SILENT-GAP rows and zero `@Disabled` tests). |
| Grammar Tests Maven Submodule (R2) | `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/pom.xml` + `src/test/java/.../grammar/*.java` | `mvn -pl grammar-tests test` SHALL pass with 0 failures and `Skipped == 0` (round-8: no SILENT-GAP rows remain, no `@Disabled` tests remain — see INV-INS-91 round-8 reformulation). |
| Deferred-by-Design Document (R3) | `openspec/changes/gh62-.../deferred.md` (snapshot at archive) | `MatrixIntegrityTest.testNonCoveredRowsAppearInDeferredDocument` cross-checks every matrix row with `Verdict ∈ {EXPLICIT-NO-OP, NOT-NEEDED}` against `deferred.md`. The test resolves the deferred-document path via active-then-archive fallback (`openspec/changes/gh62-...` then glob `openspec/changes/archive/*-gh62-...`, asserting exactly one match — ambiguous globs fail loudly rather than picking silently); after gh62 archive the test continues to pass against the moved file. Round-8 J-cleanup: replaces the round-7 `ledger.md` / `testSilentGapRowsHaveDisabledTestAndLedgerEntry` design. |
| INV-INS-88 (closed enumeration) | Matrix + `AspectJDesignators.DESIGNATORS` | `testEveryDesignatorHasMatrixRow` (asserts set equality, not subset) |
| INV-INS-89 (verdict ∈ 4-value set; NOT-NEEDED requires zero demand AND no impl OR upstream absorption with path-β Evidence) | Matrix structure | `testVerdictsAreValid` (set + path-α/β checks) + `testVerdictMatchesWorstOfPipeline` (composition rule enforcement per spec §"Verdict composition rule") |
| INV-INS-90 (COVERED → enabled passing test, no inherited `@Disabled`) | Matrix `Evidence` column + `grammar-tests/` | `testCoveredRowsCiteEnabledPassingTests` (reflection walks superclasses for inherited `@Disabled`) |
| INV-INS-91 (round-8 reformulation: no SILENT-GAP rows survive archive) | Matrix `Verdict` column + `deferred.md` | `testNoSilentGapRowsRemain` + `testNonCoveredRowsAppearInDeferredDocument` (round-8 J-cleanup: replaces round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry` — the `ledger.md` artefact is RETIRED in favour of `deferred.md`) |
| INV-INS-92 (bidirectional: tests → matrix) | `grammar-tests/` test classpath + matrix | `testEnabledTestsResolveToValidMatrixRow` + `testNoDisabledTestsRemain` + `testSkipCountEqualsZero` (round-8 J-cleanup: replaces round-7 `testEnabledTestsResolveToCoveredOrExplicitNoOpRow` + `testDisabledTestsResolveToSilentGapRow` + `testSkipCountEqualsSilentGapCount` — no `@Disabled` annotations remain post-round-8, so the skip-count target is zero, not the SILENT-GAP count). Closure atomicity enforced by `MatrixIntegrityTest` running in CI at commit time — a closure that flips the test annotation without also flipping the matrix row breaks the build (see D6) |
| INV-INS-93 (demand counts via portable Java; `.aj`+`.mop` scan) | `DemandCounter` | `testDemandCountsReproducible` |
| `condition(...)` MOP guard emit (R4 — **round-8 reclassified NOT-NEEDED β**, JavaMOP compiler absorbs upstream; row retained for traceability) | NOT shipped — JavaMOP compiler folds into `*RuntimeMonitor.*Event(...)` | `ConditionGrammarTest.conditionAbsorbedByRuntimeMonitor` + `MatrixIntegrityTest.testRoundEightClosuresAreCovered` |
| Positive `within(typePattern)` matcher (R5) | `pointcut-engine/.../WithinPC` (NEW or refactor) reusing `matchesTypePattern` from `PointcutMatcher.java:343-358` (round-7 design.md incorrectly cited `NotWithinPC:343-359`; the helper lives in `PointcutMatcher`) | `WithinFamilyGrammarTest.withinPositiveFiltersClassDef` + `MatrixIntegrityTest.testRoundEightClosuresAreCovered` |
| `T+` in owner + method-name glob + `!target/!args` matcher fixes (R6) | `pointcut-engine/.../PointcutMatcher` owner subtype expansion (§4.O) + method-name `startsWith` (§4.X) + `PointcutExpressionParser.parseUnary` negation specialization (§4.N) | `CallPointcutGrammarTest.callTSubtypeInOwner`, `CallPointcutGrammarTest.methodNamePrefixGlob`, `CompositionGrammarTest.negativeTargetArgsParserSpecialization` + `MatrixIntegrityTest.testRoundEightClosuresAreCovered` |
| `staticinitialization` synthesis + `after throwing` install | `advice-emitter/.../StaticInitSynthesizer.java` (NEW §4.Y) + `DexWeaver.applyPlan` TRY_CATCH_WRAP install (§4.T) | `StaticInitializationGrammarTest.synthesizesClinitWhenAbsent`, `AfterThrowingGrammarTest.installsTryRangeAndHandler` + `MatrixIntegrityTest.testRoundEightClosuresAreCovered` |
| **Round-8: `__STATICSIG` macro → reclassified NOT-NEEDED β** | NOT shipped — JavaMOP compiler absorbs upstream | `StaticSigGrammarTest.staticSigAbsorbedByJavaMopCompiler` (assertion test for path β) |
| `NamedRefPC` resolver via the existing `baseAspectExclusions` field (R12, §4.D — **round-8 empirical revision 2026-05-28**: the cross-repo `namedPointcuts: Map` schema change is RETIRED; the existing `AspectDescriptor.baseAspectExclusions: List<String>` field populated by `DescriptorWriter.defaultBaseAspectExclusions()` already carries the pre-expanded twelve-entry exclusion list) | `pointcut-engine/.../NamedRefPC` + the EXISTING `AspectDescriptor.baseAspectExclusions` field consumed via `getBaseAspectExclusions()` | `NamedRefResolverTest.baseAspectNotwithinExpansion`, `.unrecognisedNameFailsClosed`, `.emptyExclusionsFailsClosed` (round-8 G-decision: fail-closed replaces the round-7 always-match-with-WARN trap) + `MatrixIntegrityTest.testRoundEightClosuresAreCovered` |
| `if(...)` PCD via fork-free in-weaver 2-shape lowering (R13, §4.I — **round-11 R11.5: D13 runtime-delegation RETIRED; no fork-side helper, no `ifId`, no `monitor-builder` class**) | EXISTING `advice-emitter/.../IfGuardEmitter.java` (completed `emit()` body — direct DEX lowering of `o==null` and `!Thread.holdsLock(o)`, fail-loud default) | `IfGuardLoweringTest.nullCheckShapeLowersToIfNez`, `.holdsLockShapeLowersToInvokeStaticAndBranch`, `.unsupportedShapeFailsLoud`, `.guardSkipsMonitorWhenFalse` |
| INV-INS-94 (round-11: eleven in-change closures COVERED) | Eleven round-11 closures (§4.{O,N,V,X,TT,AT,Y,T,B,D,I} — §4.E/§4.W NOT-NEEDED β [coverage-weaver]; §4.R NOT-NEEDED α [zero demand, R11.3]) | `testRoundEightClosuresAreCovered` *(test method name retained for cross-commit stability; verifies eleven closures)* |
| INV-INS-95 (matrix row count change matches LOC delta) | Matrix row verdict flips + git LOC count | `testClosureLocFootprintMatchesMatrixDelta` (advisory; logs only) |
| INV-INS-96 (round-10 path-β absorber contract) | Each path-β assertion test verifies (a) source demand ≥ 1, (b) pipeline demand == 0, (c) named absorber file/module exists | `AbsorptionClaimsContractTest` aggregates per-row tests: `ConditionGrammarTest` (absorber = JavaMOP compiler), `StaticSigGrammarTest` (JavaMOP compiler), `AdviceExecutionGrammarTest` (inline-call vacuity), `RuntimeSubstrateGrammarTest` (coverage-weaver), `CoverageAjAbsorptionGrammarTest` (coverage-weaver), `WithinExtensionsGrammarTest` (coverage-weaver), **`ExecutionPointcutGrammarTest` (round-11 R11.2: absorber = `coverage-weaver`, sole consumer `Coverage.aj:50`; NOT "JavaMOP rewrite")**, **`WithinPositiveGrammarTest` (round-11 R11.2: absorber = `coverage-weaver`, sole consumer `Coverage.aj` `excludedPackages()`)**. §4.JP `ThisJoinPointGrammarTest` is REMOVED from path-β aggregation (`thisJoinPoint*` survives in `generic_new` staticinit; Signature delivery is part of §4.Y COVERED, fork-free per R11.5). |
| INV-INS-97 (`baseAspectExclusions` consumption — round-8 empirical revision 2026-05-28) | EXISTING `AspectDescriptor.baseAspectExclusions: List<String>` field + EXISTING `DescriptorReader` Jackson binding | `NamedRefResolverTest` (3 paths: BaseAspect.notwithin expansion, unrecognised-name fail-closed, empty-list fail-closed) + `NamedReferenceGrammarTest.baseAspectNotwithinExpandsTwelveExclusionsList` (round-8 Z-decision INV-INS-101: N=12 canonical + N=2 smallest non-degenerate AND-chain + N=1 degenerate + N=0 fail-closed) |
| INV-INS-98 (**round-11 R11.5: repurposed** — fork-free `if()` lowering, no runtime helper) | `IfGuardEmitter.emit()` lowers the two corpus shapes (`o==null`, `!Thread.holdsLock(o)`) to DEX inline + fail-loud default; NO `evaluateIf`, NO `ifId` | `IfGuardLoweringTest` (shape coverage + fail-loud + skip-when-false) |

## Goals / Non-Goals

**Goals:**

- One authoritative grammar coverage matrix exists at `docs/aspectj_grammar_coverage.md`, covering exactly the closed enumeration declared in the delta spec (classical designators, AspectJ 5 `@*` family, advice forms, sub-semantic splits for `target`/`this`/`args`, type-pattern modifiers, signature-pattern modifiers, within-family delegation rows, composition operators, **advice-body reflective API**, **around-advice `proceed(...)` mechanics**, **aspect declaration mechanics**, **AspectJ runtime linkage**).
- Every matrix row carries a verdict from `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}` anchored to a `file:line` in the dexlib2 source and to a named test in `grammar-tests/`.
- A new Maven submodule `grammar-tests/` provides executable coverage of every matrix row. Post-round-8 every test is enabled (COVERED tests assert post-fix behaviour; EXPLICIT-NO-OP tests assert UOE; NOT-NEEDED α/β tests assert demand counters); `MatrixIntegrityTest` enforces both directions of the matrix↔tests link and asserts `Skipped == 0` (round-8 J-cleanup — round-7 wording was "@Disabled failing tests for every SILENT-GAP" + "Skipped == SILENT-GAP count", but post-round-8 the SILENT-GAP count is zero so the target collapses to a constant).
- `DemandCounter` (portable Java) replaces shell `grep` for demand counts; `MatrixIntegrityTest.testSourceDemandCountsReproducible` and `.testPipelineDemandCountsReproducible` invoke it directly (round-8 J-cleanup — round-7 had a single `testDemandCountsReproducible`; the split tracks the SourceDemand vs PipelineDemand columns introduced in D9).
- The non-COVERED row catalogue lives in `openspec/changes/gh62-aspectj-grammar-coverage/deferred.md` (round-8 — round-7 design called this `ledger.md` and split rows into `Fix-now`/`Follow-up`/`Deferred-by-design`; round-8 archives with zero SILENT-GAP rows so the `Fix-now`/`Follow-up` buckets are eliminated, and `deferred.md` only holds EXPLICIT-NO-OP + NOT-NEEDED α/β rows with rationale + empirical evidence). The deferred document is a one-shot snapshot archived with the change; the matrix is the live backlog. Immutability post-archive is positively enforced by `deferred.snapshot.sha256` (D7).
- Future closures (`gh-XX`) cite gh62, name the matrix rows they flip, and update the matrix and the test annotation atomically in the same commit; `MatrixIntegrityTest` running in CI fails the build if either side moves alone (orphan test or orphan row).
- **Eleven round-11 in-change closures** flip every non-zero-PIPELINE-demand row from SILENT-GAP to COVERED: §4.O (`T+` owner), §4.N (`!target(T)`/`!args(T)` parser), §4.V (`(T,..)` trailing-mixed varargs), §4.X (method-name glob `name*`), §4.TT (`target(Type)`), §4.AT (`args(Type)`), §4.Y (`staticinitialization` synthesis + fork-free Signature delivery via the `rvsec-core` substrate, R11.5), §4.T (`after throwing` install), §4.B (`BaseAspect.notwithin()` AND-chain macro), §4.D (`NamedRefPC` resolver), §4.I (`if(...)` PCD via fork-free in-weaver 2-shape lowering, R11.5). NOT-NEEDED: §4.G/S/A/RT/JP/CV/WW (round-8 β), §4.E/§4.W (β, absorber `coverage-weaver` — R11.2), §4.R (α, zero demand — R11.3). §4.JP folds into §4.Y. Net delta: 20 round-7 − 7 round-8 − 2 round-10 (§4.E,§4.W) − 1 round-11 (§4.R) − 1 fold-in (§4.JP→§4.Y) + 1 reactivation absorbed into §4.Y = **11 in-change closures**. The matrix archives with **zero `SILENT-GAP` rows**; `MatrixIntegrityTest.testNoSilentGapRowsRemain` enforces this at every CI run.

*(round-9 historical text — preserved verbatim below until /opsx:apply, banner-overridden by round-10 above. Original round-9 framing referenced 14 closures including §4.W and §4.E "RESTORED per user decision 2026-05-26 for defensive shipping". Round-10 AA/AB-decisions retract that scope.)*

**Non-Goals:**

- **Implementing zero-demand AspectJ constructions.** After round-7 absorption, every construction with `DemandCounter ≥ 1` ships in-change; constructions with `DemandCounter = 0` across all four corpora are documented in `deferred.md` and ship as enabled `NOT-NEEDED` rows (assertion test on `DemandCounter == 0`) or `EXPLICIT-NO-OP` rows (UOE + assertion test). The deferred constructions are: `around` advice + `proceed(...)` (EXPLICIT-NO-OP — substantial DEX-level engineering for zero current demand), `cflow`/`cflowbelow`, `get(FieldPattern)`/`set(FieldPattern)`, `this(name)`/`this(Type)`, `withincode`, `initialization`/`preinitialization`, AspectJ 5 `@*` family, standalone `target(name)`/`args(name)` without `&&`-composition, `!cflow`/`!cflowbelow`/`!if`/`!handler` parser specialization, `T+` inside `!within(...)`, SignaturePattern modifiers (`!public`/`static`/`final`/`throws`), aspect inheritance, abstract aspect, privileged aspect (all NOT-NEEDED — see `proposal.md` deferred table for per-row rationale).
- **AspectJ weaver parity diff vs. AJC offline reference.** Round-5 surfaced this as oracle-of-behaviour, not oracle-of-grammar. A future sub-change MAY add AJC parity tests for high-stakes rows; out of round-7 scope (the goal is correct AspectJ semantics in dexlib2, not byte-for-byte equivalence with AJC's output).
- **Re-running the full 190-APK validation pipeline.** The 5-APK JCA-226 smoke validation (post-implementation) is sufficient evidence of behavioural correctness for the eight demand-driven closures; a full re-run is a separate experiment.
- **Refactoring the AspectJ surface of the AJC instrumenter** (`rvsec-instrumentation-ajc/`). AJC is the reference for behaviour parity, not a target — the matrix's `Verdict` is dexlib2-specific.
- **Building a full AspectJ-compliant pointcut engine.** The matrix codifies what dexlib2 supports today; the ledger schedules closures in priority order.
- **Verifying that `BaseAspect.notwithin()`'s effective filter is applied by the weaver.** That verification belongs to the Fix-now sub-change that closes that SILENT-GAP, not to this change.
- **Gold-standard parity diff against the AJC offline weaver.** Round-5 review surfaced this as a Follow-up: SILENT-GAP `@Disabled` tests assert "the correct AspectJ behaviour" by reading the AspectJ Programming Guide, not by diffing against a real AJC run. A future Follow-up sub-change MAY add AJC parity tests for high-stakes rows; out of gh62 scope.

## Decisions

### D1 — Matrix lives in `docs/`, not in a code module

**Choice:** The authoritative matrix is `docs/aspectj_grammar_coverage.md` in the rv-android repository, written in Markdown with a fixed column structure. It is *not* generated from source, *not* embedded in a Python module, *not* a YAML file.

**Why:** The matrix is consumed primarily by humans (developers planning a sub-change, reviewers auditing a closure, the user evaluating production readiness) and by LLMs asked to plan or review work. Markdown is the lingua franca of both audiences and renders directly in every PR diff. Generating it from source (e.g. annotations on the parser) would couple the contract to the implementation it constrains, defeating the purpose; YAML would resist narrative justification per matrix row.

**Stable anchor:** the matrix table is located by the literal heading `## Matrix` followed by the first Markdown table. `MatrixMarkdownParser` (built on `commonmark-java`) targets that anchor explicitly; `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` fails if the anchor is absent or duplicated.

**Alternatives considered:**

- *Generate the matrix from annotations on parser classes.* Rejected: couples the contract to the implementation; an always-match matcher would generate a `COVERED` row by default.
- *Encode the matrix as YAML/JSON for machine validation.* Rejected: the matrix is dense narrative; YAML would either flatten the prose or duplicate it.
- *Put the matrix in `openspec/specs/instrumentation/spec.md`.* Rejected: specs document behavioural contracts; the matrix is a *coverage manifest*, more akin to a test report than to a behavioural requirement.

### D2 — `grammar-tests/` is a new Maven submodule, not new tests in existing modules

**Choice:** Add a sibling Maven submodule `grammar-tests/` next to `pointcut-engine/`, `advice-emitter/`, etc. Place every grammar-row test there. Do not scatter the tests across the existing per-component modules.

**Why:** The grammar tests exercise the *full* parser→matcher→emitter pipeline against fixtures, not individual component contracts; placing them under one of the existing modules (e.g. `pointcut-engine`) would force test classes there to depend on `advice-emitter` and `dex-mutator`, inverting the Maven dependency direction. A dedicated module makes the dependency direction (`grammar-tests` → `pointcut-engine`, `advice-emitter`, `dex-mutator`) correct, isolates the `@Disabled` skip surface from per-component test bars, and gives the matrix a single test-FQN namespace (`br.unb.cic.rv.grammar.*Test`).

**Alternatives considered:**

- *Add the tests to `pointcut-engine/src/test/`.* Rejected: forces `pointcut-engine` to depend on `advice-emitter` and `dex-mutator` for the test path.
- *Add the tests to a top-level `tests/` directory outside any Maven module.* Rejected: breaks the `mvn -pl … test` invocation pattern the project already uses.

### D3 — Use `@Disabled` (visible skip) for SILENT-GAP, not `@Ignore` and not "expected failure"

**Choice:** SILENT-GAP rows are bound to tests annotated `@Disabled("gh62 SILENT-GAP: <one-line gap description>")` (JUnit 5). The test body asserts the *correct* behaviour that dexlib2 SHOULD produce, so re-enabling the test (by removing the annotation) is the natural "did the closure work?" check.

**Why:** `@Disabled` keeps the gap visible in every test report (skipped count, with the disabled-reason message shown in the report). "Expected failure" annotations (e.g. `@ExpectedToFail`) would hide the gap once the closure lands and would require a second edit to flip the expectation. JUnit 4-style `@Ignore` has no programmatic reason field. Removing the annotation in the closure's commit is a single-line diff.

**Bidirectional enforcement** (round-8 J-cleanup — round-7 wording referenced `testEnabledTestsResolveToCoveredOrExplicitNoOpRow` / `testDisabledTestsResolveToSilentGapRow` / `testSkipCountEqualsSilentGapCount`; renamed below because post-round-8 every test is enabled and the SILENT-GAP count is constant zero): `MatrixIntegrityTest.testEnabledTestsResolveToValidMatrixRow` and `.testNoDisabledTestsRemain` ensure the relationship is symmetric. `MatrixIntegrityTest.testSkipCountEqualsZero` ensures any future `@Disabled` regression (gap re-opened without matrix update) breaks the build.

**Alternatives considered:**

- *Use `@ExpectedToFail` / `@FailingTest`-style annotations.* Rejected: would require flipping the annotation twice (once when the closure lands, once to remove the `@ExpectedToFail` once the test is stable).
- *Comment out the failing tests.* Rejected: hides the gap from the test report entirely.
- *Use `Assumptions.assumeFalse(true)` inside the test body.* Rejected: visually identical to a passing test in the report; removes the gap from `Skipped` count.

### D4 — Deferred document is a one-shot snapshot; the matrix itself is the live backlog (round-8 reformulation — round-7 title was "Ledger is a one-shot snapshot")

**Choice (round-8 reformulation 2026-05-26):** The matrix records *what is true today* (verdict + evidence). The deferred document records *what we explicitly do NOT implement* at the time of merging gh62 (EXPLICIT-NO-OP + NOT-NEEDED α/β with rationale + empirical evidence per row). They live in two files: `docs/aspectj_grammar_coverage.md` (matrix, persistent) and `openspec/changes/gh62-aspectj-grammar-coverage/deferred.md` (snapshot — archived with the change). The deferred document is **not** kept alive after archive (its immutability is positively enforced by `deferred.snapshot.sha256`, D7); the matrix is the live source of truth — any future closure flips its row directly. Round-7's `ledger.md` split rows into `Fix-now`/`Follow-up`/`Deferred-by-design`; round-8 eliminates the `Fix-now`/`Follow-up` buckets because the matrix archives with zero SILENT-GAP rows (every closure ships in-change or is reclassified NOT-NEEDED).

**Why:** The matrix is permanent — every future closure updates it but the document persists across milestones. The ledger is a planning artefact — it makes sense in the context of the current scheduling decision. The cross-LLM review flagged "ledger becomes dead document post-archive" as a top risk; an earlier draft of this design tried to mitigate that by creating one GitHub issue per `Fix-now`/`Follow-up` entry (task 7.4) for live tracking. That mitigation was rejected on simplicity grounds: it creates a parallel source of truth that must be kept in sync with the matrix, multiplies the artefacts a closure must update, and preemptively opens N issues for closures that may never be scheduled. The matrix already tells you what is open (count the `SILENT-GAP` rows). Future closures are scheduled by opening one OpenSpec change per closure (with its own GitHub issue at that point) — not by maintaining a backlog of issues created up-front.

**Alternatives considered:**

- *Embed Fix-now/Follow-up/Deferred columns in the matrix.* Rejected: blurs "current state" with "future plan"; matrix becomes a planning document and stops being a contract.
- *Place the ledger in `docs/` so it survives archive.* Rejected: nobody updates `docs/<ledger>.md` after merge; it would drift silently.
- *Open one GitHub issue per `Fix-now`/`Follow-up` entry at archive time.* Rejected: see "Why" above — parallel source of truth, preemptive scaffolding for hypothetical work.

### D5 — Pair the matrix with a `smali-dexlib2` 3.0.8 → 3.0.9 bump

**Choice:** The change updates `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml:32` from `<smali.version>3.0.8</smali.version>` to `<smali.version>3.0.9</smali.version>` as an isolated first commit (§0 in tasks), gated by `mvn package` AND a behavioural diff: 5 APKs from the INV-INS-31 baseline are re-instrumented pre/post-bump and `dexdump` output is diffed. Non-trivial divergence reverts the bump within gh62.

**Why:** The matrix's `Parser` / `Matcher` / `Emitter` columns anchor to `file:line` in code that compiles against `smali-dexlib2`. The current pin (3.0.8) was set in the initial gh52 commit and never bumped. Pairing the bump with gh62 means: (a) the new `grammar-tests/` module exercises the same dependency version reviewers consult; (b) every matrix `Evidence` anchor is verified against the latest API surface. The bump is mechanically a one-line pom property edit; the cost is a reactor build + `dexdump` diff to confirm no regressions.

**`dexdump` diff (added per Opus47 review M6):** `mvn package` catches compilation breaks but not serialization/parse behaviour changes. The diff covers the realistic emission surface (`DexPool.writeTo`, `DexBackedDexFile.fromInputStream`, label/handler/payload encoding) that gh61 and prior closures depend on. The 5 APKs are picked from the INV-INS-31 wrappers-substituted baseline so the diff is reproducible.

**Why not a separate `chore(deps)`:** That was the original gh61 OQ3 default. Reverted here because gh62's value proposition is "documentation that does not lie about the dependency surface" — keeping the documentation on 3.0.8 while every reviewer reads 3.0.9 defeats the purpose. If the bump introduces a regression the right move is to revert the property change in this change, not to keep the matrix on a fictional 3.0.8 surface.

**Risk:** smali-dexlib2 3.0.9 is published at `maven.google.com/com/android/tools/smali/` (no breaking-change announcement). The reactor build + `dexdump` diff is the regression gate.

**Alternatives considered:**

- *Defer to a separate `chore(deps)` after gh62 lands.* Rejected per the value-proposition argument above.
- *Bump to a hypothetical 3.0.10 / latest.* Rejected: 3.0.9 is the current latest published.

### D6 — Drop the cross-repo PR-check workflow; enforce closure atomicity via `MatrixIntegrityTest` only

**Choice:** Do not ship `.github/workflows/grammar-pr-check.yml`. Closure atomicity (a PR that flips a test annotation must also flip the matching matrix row, and vice versa) is enforced by `MatrixIntegrityTest.testEnabledTestsResolveToValidMatrixRow` + `testNoDisabledTestsRemain` + `testSkipCountEqualsZero` (round-8 J-cleanup — round-7 wording listed `testEnabledTestsResolveToCoveredOrExplicitNoOpRow` + `testDisabledTestsResolveToSilentGapRow` + `testSkipCountEqualsSilentGapCount` here) running in CI at commit time.

**Why:** An earlier draft proposed a GitHub Action in `rv-android/.github/workflows/` that would block PRs modifying `rvsec-android/rvsec-instrumentation-dexlib2/{pointcut-engine,advice-emitter,dex-mutator,coverage-weaver}/src/main/` without touching `docs/aspectj_grammar_coverage.md`. Second-round review surfaced that the workflow's enforcement target lives in the sibling `rvsec/` repository, while the workflow itself lives in `rv-android/`. Cross-repo PR enforcement is not natively supported by GitHub Actions; a workaround using `pull_request_target` on the sibling repo with shared workflows would double the operational surface, and a developer can still touch matrix and code in separate commits to bypass it. `MatrixIntegrityTest` already detects every closure-atomicity violation (orphan tests, orphan rows, skip-count drift) at commit time as a build failure — no second mechanism needed.

**Alternatives considered:**

- *Ship the cross-repo workflow anyway as defence-in-depth.* Rejected: per P1, the test in CI is sufficient; adding the workflow is preemptive scaffolding for the same invariant.
- *Move the workflow to `rvsec/.github/workflows/` to live with the code it protects.* Rejected: the matrix lives in `rv-android/`; the workflow still needs cross-repo checkout to read it. Same root problem at half the surface.

### D7 — Deferred-document snapshot is content-addressed via SHA-256 to resolve D4 vs. spec.md:125 tension (round-8 J-cleanup — round-7 title was "Ledger snapshot"; `ledger.md` retired per D4)

**Choice:** Commit `grammar-tests/src/test/resources/deferred.snapshot.sha256` (round-8 — round-7 path was `ledger.snapshot.sha256`) containing the SHA-256 of `deferred.md` (round-8 — round-7 source was `ledger.md`) at archive time. `MatrixIntegrityTest.testDeferredDocumentIsFrozenPostArchive` (round-8 J-cleanup — round-7 name was `testSilentGapRowsHaveDisabledTestAndLedgerEntry`) SHALL verify the live deferred-document's SHA against this snapshot and fail loudly if they diverge.

**Why:** The earlier D4 stated the ledger is a one-shot snapshot ("not maintained after archive"); spec.md:125 (round-3 SILENT-GAP-permanent provision) implied the ledger MUST be edited post-archive to remove permanent entries when those rows are eventually closed. Round-5 review (opus47) flagged this as architectural contradiction. The contradiction is now resolved by eliminating the SILENT-GAP-permanent sub-bucket entirely (`handler`/`declare precedence` reclassified NOT-NEEDED path β; see spec.md "Scope Ledger" Requirement update); the ledger really IS frozen at archive time. The SHA snapshot is a tripwire: any post-archive mutation of `ledger.md` flips the test red, providing positive enforcement of the "frozen" property instead of relying on convention.

**Alternatives considered:**

- *Trust convention (no snapshot)*. Rejected: an accidental commit touching `ledger.md` would silently invalidate INV-INS-91 cross-checks.
- *Use git-tag-based pinning*. Rejected: requires CI to know the archive commit SHA, which moves over time as the project tags differ; SHA-256 of file content is stable across branches and merges.

### D8 — Demand-driven D8: close the 8 highest-traffic gaps in-change (round-6 redesign)

**Choice:** gh62 ships closures for the eight constructs whose empirical corpus demand is highest and whose dexlib2 path is silently broken: `condition(...)` guard emit (§4.G, ~80 LOC, 74 sites), positive `within(typePattern)` matching (§4.W, ~50 LOC, 28 sites), `T+` in `call()` owner (§4.O, ~50 LOC, ~73 sites), `!target(T)`/`!args(T)` parser specialization (§4.N, ~30 LOC, 32 sites), method-name glob `name*` (§4.X, ~40 LOC, ~16 sites), `__STATICSIG` macro support (§4.S, ~80 LOC, 3 sites), `staticinitialization` synthesis (§4.Y, ~100 LOC, 6 sites), `after() throwing(...)` end-to-end install (§4.T, ~120 LOC, 2 sites). Plus one zero-cost matcher fix bundled because the trivial path exists: `NamedRefPC` resolves against `AspectDescriptor.getCommonPointcut()` (§4.D, ~30 LOC). All other Fix-now/Follow-up rows ship as separate sub-changes per the ledger.

**Why:** Round-6 cross-LLM review (opus47_deep + four supporting reports) re-verified the round-5 D8 scope against the actual corpus and the compiled monitor bytecode and found three premises that did not hold:

1. **Monitor bytecode has zero `org.aspectj.*` references.** Empirical: `grep -c "org\.aspectj\|JoinPoint" MultiSpec_1RuntimeMonitor.java` returns 0 (the `Signature` type that appears is `java.security.Signature` from the JCA crypto API, not `org.aspectj.lang.Signature`). The round-5 "WRONG-DATA in production" framing described a defect flow that does not exist: `ThisJoinPointEmitter.signatureFor()` has zero callers in production (only a Javadoc reference and the declaration itself). Round-5 §4.R proposed to ship 6 local classes in `br.unb.cic.rv.aspectjlang.*` (~600 LOC) for 4 demand sites; the demand-driven approach handles those 3 `__STATICSIG` sites with an 80-LOC inline-constant emit and defers the runtime substrate to Follow-up.
2. **`AspectDescriptor.namedPointcuts()` does not exist.** Empirical: `grep -rn "namedPointcuts" rvsec-instrumentation-dexlib2/` returns 0. The class exposes 8 fields, of which `commonPointcut` (a single String) is the only named-pointcut surface. Round-5 §4.M.5 silently assumed a cross-repo schema change in JavaMOP/RV-Monitor that was never planned. Round-6 §4.D resolves named references against the existing `getCommonPointcut()` field, with a fallback to always-match plus a warn-level log for unresolved references.
3. **Round-5 nominal-family scope misses the largest measured gap.** Empirical: `condition(...)` MOP-extension guard appears in 74 sites across `jca/`+`generic_new/` (the third-largest single construct after `call/target/args`); it does not appear in the round-5 proposal because round-5 conflated it with AspectJ-level `if()` PCD (which has zero `.mop` source demand). Similarly, positive `within(typePattern)` has 28 sites and was relegated to Follow-up. The eight demand-driven closures cover ~95% of measured high-traffic gaps; the round-5 reflective API + matcher correctness families covered ~30%.

The cost is ~530-580 LOC of production code plus ~25-35 unit tests, smaller than round-5's nominal ~700-1000 LOC and an order of magnitude smaller than the realistic ~1500-2000 LOC required to actually ship `aspectjlang.*` + standalone TargetPC/ArgsPC + `!cflow` flow tracking.

**Alternatives considered:**

- *Keep round-5 nominal-family D8 (Reflective API + Matcher Correctness)*. Rejected: empirical demand verification (opus47_deep) showed it mis-targets ~70% of effort against ~30% of corpus demand, blocks on `AspectDescriptor.namedPointcuts()` vaporware, and risks runtime linkage failures (VerifyError) against `org.aspectj.lang.*` references that the monitor never produces.
- *Documentation-only gh62 (no D8 closures)*. Rejected: leaves 8 measurable gaps documented as SILENT-GAP but unaddressed, and round-6 review surfaced that several of them (`condition`, `within` positive, `after throwing` install) are inexpensive enough to bundle without bloating the change.

### D9 — Round-8 absorption-aware demand: scope by pipeline-level demand, not source-level

**Choice (round-8 supersedes round-7):** gh62 ships closures for the constructs whose `DemandCounter.countCompiledAj() ≥ 1` AT THE INSTRUMENTER STAGE (post JavaMOP compilation, post `coverage-weaver` absorption, post `DescriptorReader` flattening). Constructions with `DemandCounter.countMop() ≥ 1` BUT `DemandCounter.countCompiledAj() == 0` are NOT-NEEDED β — the matrix records both demands separately so the absorption pattern is auditable. The change archives with **zero `SILENT-GAP` rows in the matrix**. No `Fix-now`/`Follow-up` ledger bucket survives; round-7's `ledger.md` was already replaced by `deferred.md`.

(round-9 historical:) Fourteen closures ship in-change (§4.{W,O,R,N,V,X,TT,AT,Y,T,B,D,I,E}); six round-7 closures are reclassified NOT-NEEDED β (§4.{G,S,A,RT,JP,CV,WW}). The §4.E `execution(...)` matcher + emitter was initially reclassified to NOT-NEEDED β in the round-8 draft but RESTORED as a full in-change closure on 2026-05-26 per user decision (defensive shipping — see "User decision on §4.E" note below).

**(round-11 current — supersedes all sentences above per the Round-11 banner at the top of this file):** **Eleven** closures ship in-change (§4.{O,N,V,X,TT,AT,Y,T,B,D,I}). NOT-NEEDED β: round-8 set §4.{G,S,A,RT,JP,CV,WW} + §4.E (absorber `coverage-weaver`, R11.2) + §4.W (absorber `coverage-weaver`, R11.2). NOT-NEEDED α: §4.R (zero demand everywhere, R11.3). §4.JP folds into §4.Y (fork-free Signature delivery, R11.5). Net delta: 20 − 7 round-8 − 2 round-10 (§4.E,§4.W) − 1 round-11 (§4.R) − 1 fold-in (§4.JP) + 1 reactivation-into-§4.Y = **11**.

**Why round-8 supersedes round-7:** Round-7 framed scope as "absorb every source-level non-zero-demand construction in-change" to escape the reactive posture. Three empirical audits on 2026-05-26 (`docs/analise_sintese_macro.md`) showed that seven of the twenty round-7 closures attacked constructions the upstream pipeline absorbs before they reach the instrumenter:

1. **APK AJC inspection** (`results/gh53_smoke_ajc/instrumented_apks/cryptoapp.apk`) — 115/115 MOP advices in `smali/mop/MultiSpec_1MonitorAspect.smali` are trivial pass-through `invoke-static *RuntimeMonitor.*Event(args_typed)`, with zero `thisJoinPoint`/`__STATICSIG`/`condition`/`Signature` references. Only `Coverage.aj` uses `JoinPoint.StaticPart`.
2. **Compiled `.aj` audit** (`results/gh53_smoke_dexlib2/monitors/MultiSpec_1MonitorAspect.aj`) — `condition(...)` is completely removed by the JavaMOP compiler (the condition logic moves into `*RuntimeMonitor.*Event(...)`); `__STATICSIG` has zero occurrences in the JCA-compiled `.aj`. Construction inventory of the compiled `.aj` is narrow: `pointcut`, `before`, `after`, `after returning`, `call`, `target`, `args`, `!within`, `&&`, `||`, `!adviceexecution()`. Nothing else.
3. **`coverage-weaver` overlap** — `CoverageWeaver.java:23-32` javadoc declares semantic equivalence with `Coverage.aj`. `experimento-20260508/RELATORIO.md` §3.2/§7.2 confirms the 190-APK production experiment ran dexlib2 exclusively with coverage via `coverage-weaver`, not via `Coverage.aj`. The AspectJ runtime substrate + `thisJoinPoint` binding + `execution()` emitter that round-7 planned (~1 000 LOC combined) had a single consumer (Coverage.aj), which is absorbed by `coverage-weaver`.

The trade-off is honest documentation — round-8's `deferred.md` §2.2.1 carries seven path-β entries with explicit absorber names and empirical evidence per row, so future readers understand exactly why these constructions did not ship as closures.

(round-9 historical:) The scope shrinks from ~2 000 LOC (round-7) to **~865-940 LOC** (round-8 with §4.E restored, per H-reconciliation 2026-05-28).

**(round-10 current):** The scope shrinks further to **~565-660 LOC** (round-10: round-9 minus ~230 LOC §4.E AA-decision minus ~80 LOC §4.W AB-decision plus ~30-50 LOC §4.Y Signature delivery AC-decision; see `EMPIRICAL-DEMAND.md` for the per-row evidence chain). The bisect-friendly atomic-commit discipline (one closure per commit) and the matrix integrity tests are preserved.

**(round-9 historical) User decision on §4.E (2026-05-26)**: round-8 audit found zero positive consumers; user RESTORED §4.E for defensive shipping (~230 LOC). **(round-10 supersession 2026-05-29 — AA-decision):** empirical pipeline-level audit against all three corpora (`empirical-monitors/{jca,generic,generic_new}/`) confirmed pipeline POSITIVE `execution(...)` = 0 across all three; the round-9 defensive-shipping rationale is dominated by P1 (No speculative features). §4.E reverts to NOT-NEEDED β. The `MatrixIntegrityTest.testPipelineDemandCountsReproducible` invariant provides the same future-corpus protection that defensive shipping was meant to deliver — without speculative LOC.

**Alternatives considered:**

- *Keep round-7 scope, ship the seven reclassified closures anyway "for completeness".* Rejected: each would attack a construction that does not reach the instrumenter — testable by construction (the corresponding compiled-`.aj` grep is zero), and the resulting code would either be unreachable or duplicate work already done by the upstream stage. Violates P1 (Simplicity) — no speculative scaffolding.
- *Keep round-6 scope (eight closures only), close round-7-style Fix-now via separate sub-changes.* Rejected per the round-7 user feedback that fragmenting mechanically-independent closures into sub-changes adds no value.
- *Split round-8 into a "lean closures" change and a "deferred document" change.* Rejected: the deferred document IS the round-8 redesign — without it, the seven reclassifications are unjustified. They must ship together.

### D10 — [SUPERSEDED by round-8 NOT-NEEDED β reclassification] Ship the AspectJ runtime substrate as a local `br.unb.cic.rv.aspectjlang.*` package with FQN remap

**Round-8 status**: SUPERSEDED. The substrate is NOT shipped. The sole consumer (`Coverage.aj`) is absorbed by `coverage-weaver` (see D9-round-8 and `deferred.md` §2.2.1-D). The round-7 D10 design is preserved below as historical context for reviewers tracing the decision; the round-8 disposition is documented at the end of this section.

**Original choice (round-7):**

**Choice:** Ship six classes under `br.unb.cic.rv.aspectjlang.*` (`JoinPoint`, `JoinPoint.StaticPart`, `Signature`, `MethodSignature`, `ConstructorSignature`, `FieldSignature`, `SourceLocation`) in a new Maven submodule `aspectjlang/`. The substrate is shaded into `instr-cli.jar`. The weaver rewrites references to `org.aspectj.lang.*` and `org.aspectj.lang.reflect.*` in the woven bytecode to point at `br.unb.cic.rv.aspectjlang.*` via `AspectJRuntimeRemapper` in `dex-mutator/`, applied during the dex serialisation pass.

**Why:** The round-6 review concluded "MultiSpec_1RuntimeMonitor.java has zero `org.aspectj.*` references" and deferred the substrate. That measurement was correct for the JCA monitor, but it missed `Coverage.aj`, which declares `import org.aspectj.lang.Signature; import org.aspectj.lang.reflect.MethodSignature;` and consumes `MethodSignature.getMethod()`, `.getDeclaringClass().getName()`, `.getReturnType()`, `.getParameterTypes()` at runtime. Without a substrate the woven bytecode raises `NoClassDefFoundError` on first invocation because the `org.aspectj.*` classes are not on the Android runtime classpath (Android does not ship AspectJ runtime).

Three alternatives were considered for the substrate:

1. **Pull `aspectjrt.jar` as a maven dependency and shade it into `instr-cli.jar`.** Rejected: pulls ~500 KB of dependencies (`aspectjrt` transitively depends on `aspectjtools`, `aspectjweaver`) for ~600 LOC of actual surface we need. Adds licence complexity (Eclipse Public License) and version-management overhead.
2. **Detect `org.aspectj.*` references in the advice body and rewrite them at the source level (in the JavaMOP-emitted aspect) to use `java.lang.reflect.*` equivalents.** Rejected: the advice body is consumed bytecode-level by the dexlib2 instrumenter (not source-level); rewriting at the JavaMOP toolchain would require a cross-repo change to a tool we do not own.
3. **Ship a local substrate under `br.unb.cic.rv.aspectjlang.*` and remap references at dex serialisation time.** Selected. The substrate is small (~600 LOC of straightforward POJOs implementing the API surface the corpora exercise — measured by re-grepping `Coverage.aj` + `generic_new/*.aj` for every method/property accessed on `org.aspectj.lang.*` types), the remap is a single-pass string-pool rewrite in `AspectJRuntimeRemapper`, and the substrate has zero transitive dependencies (the classes are POJOs with no AspectJ runtime semantics — they exist purely to satisfy bytecode linkage and provide the `getMethod()`/`getName()`/`getReturnType()`/etc. accessors).

The remap is deterministic and reversible: it is a pure FQN rename (no method-signature changes, no behavioural changes). `INV-INS-97` enforces no orphan `org.aspectj.lang.*` references in any woven DEX (verified by dex string-pool inspection in `AspectJRuntimeRemapperTest`).

**Alternatives considered:** see above; the trade-off is ~30-50 KB shaded into `instr-cli.jar` (six small POJO classes + the remap helper) against ~500 KB for `aspectjrt.jar` shading or a cross-repo schema change to JavaMOP.

**Round-8 disposition:** the empirical audit refuted the premise of this decision. The round-7 D10 reasoning hinged on "Coverage.aj is load-bearing for experimental coverage and consumes `org.aspectj.lang.*` types". The round-8 audit established two facts that invalidate this premise: (a) `coverage-weaver` is byte-for-byte semantically equivalent to `Coverage.aj` per its own javadoc, with no `org.aspectj.*` runtime dependency; (b) the 190-APK production experiment (experimento-20260508) used `coverage-weaver` exclusively, not `Coverage.aj`. With Coverage.aj absorbed, the substrate has no consumer. Round-8 drops the `aspectjlang/` Maven submodule, the `AspectJRuntimeRemapper`, and the associated `INV-INS-96`/`INV-INS-97` invariants; the matrix row for "Runtime linkage: `org.aspectj.lang.JoinPoint` family" carries `Verdict = NOT-NEEDED β` with `coverage-weaver` as the named upstream absorber.

### D11 — Named-pointcut resolver consumes the EXISTING `baseAspectExclusions` field; fail-closed on miss (round-8 empirical revision 2026-05-28; A + G decisions)

**Choice (round-8 empirical revision 2026-05-28):** the §4.D `NamedRefPC` matcher recognises the literal name `BaseAspect.notwithin` and delegates to the §4.B `BaseAspectExpander`, which consumes the EXISTING `AspectDescriptor.baseAspectExclusions: List<String>` field directly. **Fail-closed** behaviour: any unrecognised `NamedRefPC` name throws `UnresolvedNamedRefException`; an empty `baseAspectExclusions` list (legacy descriptor produced by a JavaMOP build pre-dating the field) throws `LegacyDescriptorException` so the caller regenerates the descriptor against the current JavaMOP toolchain rather than silently inlining a permissive filter.

**Why (round-8 empirical revision supersedes round-7 / early-round-8 design):** The round-7 and early-round-8 drafts of this decision assumed a new `namedPointcuts: Map<String, PointcutExpression>` field would need to be added cross-repo to the JavaMOP-emitted `AspectDescriptor` JSON. Empirical inspection 2026-05-28 of the canonical schema source (`descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/AspectDescriptor.java`, 50 LOC), the JavaMOP-side producer (`javamop/src/main/java/javamop/output/descriptor/DescriptorWriter.java#buildAspect` + `#defaultBaseAspectExclusions`), the production JSON fixture (`descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json`), and the consuming tests (`DescriptorReaderTest.java:41-42` asserting `"java..*"` and `"mop..*"` inclusion) proved that the schema ALREADY exposes a load-bearing `baseAspectExclusions: List<String>` field. The field is populated by `DescriptorWriter.defaultBaseAspectExclusions()` with the canonical twelve-entry expansion (`["sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*", "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*", "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"]`) — exactly the data the §4.D resolver needs to expand `BaseAspect.notwithin()`. The cross-repo schema change is therefore RETIRED; the §4.D / §4.B closures consume the existing field.

**Why fail-closed (round-8 G-decision per cross-LLM meta-review consensus):** The round-7 / early-round-8 fallback "always-match with WARN log" was identified by Codex's meta-review as "a trap" that preserves the silent-widening behaviour gh62 exists to eliminate. Three reviewers independently flagged the same concern: GPT-5-Codex ("fail-closed instead — WARN is not an executable failure and may be invisible in production instrumentation"), Nemotron ("contradicts round-8 goal to eliminate silent gaps"), DeepSeek ("philosophically required — proposal.md:9 names the always-match-on-unmodelled-designators failure mode as the change's first-class target"). The fail-closed exception path makes the mismatch visible at instrumentation time — the caller chooses whether to (a) extend the matcher with a new named-ref recogniser, (b) regenerate the descriptor against a JavaMOP toolchain that emits the missing data, or (c) explicitly accept the limitation by skipping the affected aspect.

**LOC implication:** round-8 empirical revision narrows the LOC estimate substantially. §4.D drops from the earlier ~80-120 LOC estimate to ~30-40 LOC (the entire cross-repo schema work disappears; only the matcher logic remains). §4.B drops from ~50-80 LOC to ~15-20 LOC (a one-method iterator over the existing list). The combined ~50-60 LOC is small enough that the closure ships with the §4.W and §4.O batch rather than as a standalone commit.

**Alternatives considered:**

- *Add the `namedPointcuts: Map<String, PointcutExpression>` field anyway, for future generality.* Rejected per P1 (Simplicity) and the round-8 demand-driven framing: no current pipeline construction needs more than the `BaseAspect.notwithin` reference; the cross-repo schema and the heuristic "first-identifier-before-paren" fallback documented in the early-round-8 draft were both purely speculative. The `baseAspectExclusions` consumption is generalisable when the demand surfaces — adding a new named-ref recogniser is a 5-LOC patch in the §4.D matcher dispatch.
- *Keep the always-match-with-WARN fallback as a "pragmatic shim for legacy descriptors".* Rejected per the round-8 G-decision cross-LLM consensus above. Legacy descriptors are detected explicitly (empty `baseAspectExclusions` list) and surfaced via `LegacyDescriptorException` — the caller has the visible signal needed to regenerate.
- *Resolve named references via runtime reflection on the woven aspect class.* Rejected per the round-7 design — the aspect lives in the to-be-instrumented APK, not on the weaver process's classpath.

The schema extension is additive: existing consumers continue to read `commonPointcut` unchanged. The JavaMOP-side emit verification is now an archive precondition (tasks §0.5) — round-7 assumed it; round-8 verifies it before shipping the consumer. `INV-INS-97` (round-8) covers all three resolution paths (table-hit, commonPointcut-fallback, always-match-fallback).

**Alternatives considered:**

- *Stuff multiple pointcuts into `commonPointcut` as a concatenated `&&`/`||` chain.* Rejected: loses the ability to reference individual pointcuts by name (`Coverage.aj`'s `traced()` references `!excludedPackages()`); fragile to ordering; not how JavaMOP emits the data.
- *Resolve named references via runtime reflection on the woven aspect class.* Rejected: requires the aspect to be loadable at weave time, which is fragile (the aspect lives in the to-be-instrumented APK, not on the classpath of the weaver process).
- *Defer Coverage.aj's named pointcuts to a future closure that ships the full symbol table.* Rejected in round-7 per D9; round-8 makes it moot — Coverage.aj is absorbed, the two-pointcut demand disappears.

### D12 — [Round-8 introduction] Upstream Absorption Verdict as first-class verdict path β

**Choice (new in round-8):** The matrix verdict vocabulary `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}` recognises **path β** as a first-class assignment of `NOT-NEEDED`. A construction may have `DemandCounter.countMop() ≥ 1` (source demand is non-zero) and still carry `NOT-NEEDED` if `DemandCounter.countCompiledAj() == 0` (pipeline demand is zero — the construction is absorbed by an upstream stage before reaching the dexlib2 instrumenter). The `Requirement: Upstream Absorption Verdict` in spec.md formalises the set of recognised absorbers (JavaMOP compiler, `coverage-weaver`, `MonitorRuntime` dispatch loop, `DescriptorReader`, dexlib2 inline-call emission model) with named evidence anchors per absorber.

**Why:** Round-7 path β existed in the spec but was applied only to descriptor-absorbed productions (`aspect Foo`, `pointcut p()`, aspect inheritance) — productions that exist in `.aj` source but never reach `PointcutExpressionParser`. Round-8 generalises path β to ALL upstream-absorbing stages, including the JavaMOP compiler's `condition()` lowering, `coverage-weaver`'s `Coverage.aj` substitution, and the dexlib2 inline-call model's `adviceexecution()` vacuity. The generalisation is justified by the absorption-aware demand framing (D9-round-8): scope decisions follow pipeline demand, so the verdict vocabulary must express the upstream-absorbed cases as a first-class category. Without D12, the seven round-8 reclassifications would have no honest verdict to land on — forcing either "ship the closure against nothing" (round-7's mistake) or "ship as SILENT-GAP with a documented exception" (defeating the round-8 zero-SILENT-GAP goal).

The path-β assertion test contract (INV-INS-96 in spec.md) requires THREE properties per absorbed row: (a) `DemandCounter.countMop ≥ 1` to confirm source-level demand exists; (b) `DemandCounter.countCompiledAj == 0` to confirm pipeline absorption; (c) the named absorber file/module exists and contains the documented evidence anchor. The test FAILS if any of the three properties changes — guarding against silent regression of an upstream stage that would re-surface the construction at the instrumenter without notice.

**Alternatives considered:**

- *Use path α for absorbed productions (treat as "zero demand" regardless of source-level count).* Rejected: hides the empirical fact that the construction exists in the corpora; loses the upstream-absorber audit trail; would make it impossible to detect a regression where a future JavaMOP toolchain stops absorbing a construction.
- *Add a fifth verdict `ABSORBED-UPSTREAM`.* Rejected: vocabulary growth has high cost (every reader must learn the new verdict; every test must handle it); path β under `NOT-NEEDED` carries the same information at lower vocabulary cost.
- *Document absorption informally in `deferred.md` without a verdict path.* Rejected: the matrix is the contract; informal documentation drifts. The verdict path makes the absorption claim testable.

### D13 — `if(...)` PCD lowering — RETIRED in round-11 (fork-free 2-shape in-weaver lowering replaces runtime delegation)

**Round-11 status (R11.5): RETIRED.** The runtime-delegation ABI below (`MonitorRuntime.evaluateIf(int, Object[])`, content-hashed `ifId`, `MonitorRuntimeIfHelperEmitter`, `IfRuntimeAbi`) required code generated on the JavaMOP/RV-Monitor fork side — and `evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter` exist in **neither** fork (confirmed by source grep). The firm constraint is "no JavaMOP fork change". §4.I is therefore realised **entirely in the dexlib2 weaver** by completing the existing `IfGuardEmitter.emit()` stub with direct DEX lowering of the only two expression shapes the corpus contains — `o == null` (→ `if-nez`) and `!Thread.holdsLock(o)` (→ `invoke-static Ljava/lang/Thread;->holdsLock(Ljava/lang/Object;)Z` + `move-result` + `if-nez`) — with a fail-loud `UnsupportedAspectConstructError` default. The bound register is already in `ctx.match` (`target(o)`/`args(o)`); the expression text is in `IfPC.javaExpression`; the branch label reuses `BuilderInstruction21t` + `newLabelForIndex` (proven in `RegisterShifter`). This is a 2-shape closed dispatch (3 sites, generic_new), NOT the general Java sub-grammar parser round-7 proposed and 6/6 reviews rejected. No runtime jar, no fork, no `ifId`, no `MonitorRuntime` helper. ~60 LOC, 1 file. The round-8 design is preserved below as historical context only.

**Original choice (round-8 — RETIRED):** The §4.I `if(...)` PCD closure DOES NOT lower the `<expr>` payload to DEX bytecode in the weaver. The weaver assigns a stable integer `ifId` per `if(...)` clause at weave time and emits `invoke-static MonitorRuntime.evaluateIf(<ifId>, args_boxed)` before the monitor invoke. The per-spec generated `*RuntimeMonitor.evaluateIf(int, Object[])` contains a switch-case where each case arm holds the actual boolean expression for that `ifId`, lowered by the existing JavaMOP compiler (which already lowers Java boolean expressions for the `*RuntimeMonitor.*Event(...)` method bodies — see the `condition()` absorption pattern in §4.G round-7 reclassification).

**Why:** Round-7 §4.I proposed an in-weaver `IfExpressionLowerer` (~80 LOC parser + ~20 LOC codegen) that would parse the `<expr>` payload as a Java boolean expression and emit DEX bytecode evaluating it. Six of six cross-LLM reviews (claude, codex_gpt5, deepseek, gemini25pro, opus47_deep, big-pickle) flagged this as a BLOCKER: 80 LOC is insufficient for a Java sub-grammar parser plus DEX codegen, the corpus exhibits non-trivial expressions (`!Thread.holdsLock(o)`, `instanceof`, method calls), and a frail in-weaver evaluator risks `VerifyError` on every advice it touches. Multiple reviewers proposed runtime delegation as the alternative; round-8 adopts it.

The runtime delegation pattern is already proven in the codebase: the JavaMOP compiler lowers `condition(...)` expressions into `*RuntimeMonitor.*Event(...)` method bodies that the dexlib2 instrumenter invokes via `invoke-static`. Round-8 §4.I uses the same pattern for `if(...)`: the JavaMOP compiler (or a small extension thereof) lowers the `<expr>` payload into a switch-case arm in `*RuntimeMonitor.evaluateIf(int, Object[])`, and the dexlib2 instrumenter emits `invoke-static` before the monitor invoke. The dexlib2 side becomes ~30-50 LOC (round-8 M-decision 2026-05-28: COMPLETES the EXISTING `IfGuardEmitter` at `advice-emitter/src/main/java/br/unb/cic/rv/emitter/IfGuardEmitter.java` rather than creating a new class — the existing emitter already has `wrapping(delegate)` + scratch-register allocation + javadoc explicitly anticipating "a compiler-generated static helper method that the advice-emitter stages during monitor-builder time"; creating `IfRuntimeDelegationEmitter` as a parallel class violates P3 and the existing tests reference `IfGuardEmitter` already); the monitor-side helper generation is ~50 LOC.

**ifId stability — round-8 B-decision 2026-05-28 (content-hash, not source-order).** The early-round-8 D13 specified "deterministic ordering by source-order traversal of the `.aj`" as the ifId stability mechanism. Five reviewers independently flagged this as a silent-mismatch trap because the dexlib2 weaver (parsing `.aj` via its parser) and the JavaMOP `MonitorRuntimeIfHelperEmitter` (walking the AST) are two independent producers reading the same input from different paths; reordering of `if(...)` clauses in either side's traversal yields swapped ifIds, and `evaluateIf(0, args)` ends up invoking the wrong boolean expression at runtime with no visible error. Round-8 substitutes content-addressed ifIds:
```
ifId = (int) (SHA1_first_8_bytes(normalize(pointcut_expr) + " " + advice_form + " " + aspect_FQN) & 0x7FFFFFFF)
```
where `normalize` strips comments and inter-token whitespace and lower-cases keywords. The hash is computed identically on both sides; clause reordering yields the same ifId; cross-repo coordination becomes a property of the input data, not the traversal order. INV-INS-98 codifies the hash function as a contract; `IfRuntimeDelegationTest.weaverEmitsContentHashedIfIdsAcrossClauseOrderings` regenerates a `.aj` with reordered clauses and asserts the ifIds are unchanged.

**ABI contract — round-8 Y-decision 2026-05-28.** `evaluateIf(int ifId, Object[] args)` receives `args` ordered as (a) advice-bound values from `target(name)` and `args(name1, name2, ..)` in source-order, then (b) `thisJoinPoint` if referenced, then (c) `returning(name)` / `throwing(name)` if applicable. Primitive bindings are boxed via the standard `Integer.valueOf` / `Boolean.valueOf` / `Long.valueOf` family. The argument-name → array-index mapping is generated alongside the switch-case in the per-spec `*RuntimeMonitor` and emitted as a static final `String[] $ifIdArgs<ifId>` constant for debuggability. The default-case arm of the generated switch MUST throw `IllegalStateException("evaluateIf invoked with unknown ifId=" + ifId)` — silent `return false` is forbidden because it would suppress monitor events without trace. This ABI is shared between the dexlib2 weaver (emitter of the `invoke-static`) and the JavaMOP `MonitorRuntimeIfHelperEmitter` (generator of the switch-case body); both sides reference `IfRuntimeAbi` as the single source-of-truth class so updates propagate by recompilation.

The cost is a small runtime indirection (one extra `invoke-static` per advice with an `if(...)` clause) and a small monitor-side code growth (one switch-case per `ifId`). The benefit is the elimination of the in-weaver parser/codegen risk surface (`VerifyError`, sub-grammar ambiguity, method-resolution complexity) and alignment with the established absorption pattern.

**Alternatives considered:**

- *Implement the in-weaver `IfExpressionLowerer` as round-7 planned.* Rejected per the BLOCKER convergence above. The estimate is honest only for a trivial subset (`x == null`, `!flag`); the corpus uses non-trivial subset (`!Thread.holdsLock(o)`).
- *Defer §4.I entirely (treat the 8 sites in `generic_new` as NOT-NEEDED β via JavaMOP absorption — same pattern as `condition()`).* Considered seriously. The reason §4.I ships and §4.G doesn't is that the JavaMOP compiler ALREADY absorbs `condition()` (verified by the compiled `.aj` audit) but does NOT currently absorb `if()` (the `.aj` retains the `if(...)` PCD clauses). If a future JavaMOP version absorbs `if()` too, §4.I migrates to NOT-NEEDED β and the runtime helper retires.
- *Use `MethodHandles` / `invokedynamic` for the runtime evaluation.* Rejected: Android API level constraints make `invokedynamic` fragile pre-API-26; `MethodHandle` introduces a heavier runtime dependency than the switch-case approach.

### D14 — `after() throwing(...)` try-range splitting under nested try-catch (round-8 F-decision 2026-05-28)

**Choice (new in round-8 — F-decision per cross-LLM meta-review on §4.T):** when `§4.T`'s `AfterThrowingEmitter` injects a handler at a call site that is already covered by one or more user try-blocks, the weaver applies the **range-splitting** policy: each enclosing try-block is split into a head segment (instructions before the matched invoke, preserving the original handler list) + the matched invoke covered by BOTH the original handlers AND the new `after-throwing` handler with the new handler listed FIRST + a tail segment (instructions after the invoke, preserving the original handler list). The new handler block starts with `move-exception vException` (ART invariant) and ends with `throw vException` (re-throw so user `catch` clauses still run).

**Why range-splitting and not nested-wrapping:** four cross-LLM reviewers (Gemini 2.5 Pro, GPT-5-Codex, Nemotron, DeepSeek) independently flagged that the early-round-8 §4.T spec was silent on the nested-try-catch case. The two candidate strategies are:
1. **Nested-wrapping**: install a new innermost try-block covering only the matched invoke; this produces overlapping-not-nested ranges (the new try-block's range is `[invoke, invoke+1)`; the user try-block's range is `[invoke-5, invoke+10)` or similar). ART's verifier rejects this in the general case because handler tables require strictly-nested or strictly-disjoint ranges per the DEX format spec; the failure mode is install-time `VerifyError` with no source-level trace.
2. **Range-splitting (D14 choice)**: split each enclosing user try-block at the matched invoke offset; the result is three sequential ranges `[start, invoke)` / `[invoke, invoke+1)` / `[invoke+1, end)`, each with its own handler list. The matched-invoke range carries the union of (new handler + original handlers) with the new handler listed FIRST (ART scans handlers in declaration order, "first-most-specific" semantics; the new advice handler fires before the user `catch`). Strictly-nested layout is preserved; ART verification passes.

**Edge cases:**
- *Re-throw semantics*: the new handler ends with `throw vException` so the user `catch` clauses still see the exception. Without re-throw, `after-throwing` advice would silently swallow exceptions matched by the new handler before user code sees them — semantically incorrect.
- *RegisterShifter (gh61) interaction*: when a register-widening shift is required to free the exception register, the shifter's emit-plan covers the new handler block too; register liveness analysis remains consistent across the split ranges.
- *Multiple enclosing try-blocks*: the split is applied per enclosing block (the matched invoke may be inside two or three nested user try-blocks); each split happens independently and the resulting `MethodImplementationBuilder` serialises the ranges in start-offset order.

**Alternatives considered:**
- *Nested-wrapping (option 1 above).* Rejected per the ART verifier failure mode.
- *Refuse to install when the matched invoke is inside any user try-block.* Rejected: the `after-throwing` semantics MUST fire on exceptional exits; refusing the install would silently drop the advice. Better to fail loudly via a logged diagnostic if the topology cannot be split (the gh61 RegisterShifter pattern already does this for unrelated register pressure).

**Test gate (LOC and complexity revision per Q-decision):** the round-7 / early-round-8 §4.T LOC estimate of ~80 LOC is revised up to **~150-200 LOC** to honestly account for the range-splitting logic, the RegisterShifter coordination, the handler-ordering reshuffle, and the dexlib2 `MethodImplementationBuilder` API friction. `DexWeaverNestedTryCatchTest.afterThrowingInsideExistingTryBlockSplitsRangesCleanly` exercises the policy with a synthetic fixture asserting (a) ART installation succeeds, (b) both new advice handler AND user catch fire in order when the call throws a matching exception, (c) new advice handler fires and the exception propagates when the user catch does not match.

### D15 — `docs/aspectj_grammar_coverage.md` is the single source of truth; legacy inventories are demoted (round-8 W-decision 2026-05-28)

**Choice (new in round-8 — W-decision per Codex meta-review):** the pre-existing inventory documents `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and `docs/AJ_TO_DEXLIB2_MAPPING.md` SHALL each carry a header banner declaring `SUPERSEDED — see docs/aspectj_grammar_coverage.md as the live contract; this file preserved as historical inventory only`. The matrix is the contract; the legacy inventories survive for historical reference but are removed from the test/CI dependency surface. `MatrixIntegrityTest.testNoCompetingSourceOfTruth` (INV-INS-102) fails the build if either legacy document is amended without the banner present.

**Why:** Codex's meta-review surfaced the risk of three documents drifting independently — the matrix declares verdict `COVERED §4.W` for positive `within(pkg..*)`, while the legacy inventory could still record `SILENT-GAP` against the same designator; readers landing on the legacy file would draw the wrong conclusion. The banner makes the demotion explicit without losing the historical breadcrumbs that pre-date the matrix. Removing the legacy files entirely would lose archeological context (when was `within(*..Log)` first identified as a suffix-wildcard gap? — round-3 review, captured in the inventory document); demoting them preserves that history while eliminating the competing-source-of-truth hazard.

**Alternatives considered:**
- *Delete the legacy inventories.* Rejected per the historical-context argument above.
- *Leave them in place without banner.* Rejected per the three-documents-drift hazard.
- *Auto-generate them from the matrix at build time so they stay in sync.* Rejected per P1 (Simplicity) — the banner-plus-CI-check approach is one line of test logic; auto-generation requires a Maven plugin and round-tripping the Markdown.

## API Design

This change introduces no Python API. The Java surface added is a single test-only class hierarchy in `grammar-tests/`:

```java
// grammar-tests/src/test/java/br/unb/cic/rv/grammar/MatrixIntegrityTest.java
package br.unb.cic.rv.grammar;

/**
 * Asserts the structural integrity of docs/aspectj_grammar_coverage.md and
 * the bidirectional link between matrix rows and grammar-tests/ test methods.
 * Enforces INV-INS-88..102 at every test run.
 *
 * Round-8 C-cleanup (2026-05-28 per cross-LLM meta-review): test names below
 * reflect the post-archive state (zero SILENT-GAP rows, zero @Disabled tests).
 * Round-7 names (testSilentGapRowsHaveDisabledTestAndLedgerEntry,
 * testDisabledTestsResolveToSilentGapRow, testSkipCountEqualsSilentGapCount)
 * are RETIRED — see the J-cleanup table in `## Mapping`.
 */
class MatrixIntegrityTest {
    // Matrix → tests
    @Test void testEveryDesignatorHasMatrixRow();              // INV-INS-88
    @Test void testVerdictsAreValid();                         // INV-INS-89 (path α/β membership)
    @Test void testVerdictMatchesWorstOfPipeline();            // INV-INS-89 (worst-of-pipeline composition rule)
    @Test void testCoveredRowsCiteEnabledPassingTests();       // INV-INS-90
    @Test void testNoSilentGapRowsRemain();                    // INV-INS-91 (round-8 reformulation)
    @Test void testNonCoveredRowsAppearInDeferredDocument();   // INV-INS-91 (round-8 J-cleanup: replaces testSilentGapRowsHaveDisabledTestAndLedgerEntry)
    @Test void testRoundEightClosuresAreCovered();             // INV-INS-94 (round-8 rename of round-7 testRoundSevenClosuresAreCovered)
    @Test void testClosureLocFootprintMatchesMatrixDelta();    // INV-INS-95 (round-6, advisory)
    @Test void testDeferredDocumentIsFrozenPostArchive();      // INV-INS-100 (round-8 SHA tripwire, replaces round-6 ledger SHA)
    @Test void testNoCompetingSourceOfTruth();                 // INV-INS-102 (round-8 W-decision: AJ_CONSTRUCTIONS_INVENTORY.md + AJ_TO_DEXLIB2_MAPPING.md carry SUPERSEDED banner)
    // Tests → matrix (bidirectional)
    @Test void testEnabledTestsResolveToValidMatrixRow();      // INV-INS-92 (round-8 J-cleanup: replaces testEnabledTestsResolveToCoveredOrExplicitNoOpRow; NOT-NEEDED rows are enabled in round-8)
    @Test void testNoDisabledTestsRemain();                    // INV-INS-92 (round-8 J-cleanup: replaces testDisabledTestsResolveToSilentGapRow; the assertion is now zero @Disabled, not "every @Disabled has a SILENT-GAP row")
    @Test void testSkipCountEqualsZero();                      // INV-INS-92 (round-8 J-cleanup: replaces testSkipCountEqualsSilentGapCount; target is 0, not the SILENT-GAP count which is also 0 post-round-8 but the name was misleading)
    // Demand
    @Test void testSourceDemandCountsReproducible();           // INV-INS-93 (round-8 split from round-6 testDemandCountsReproducible)
    @Test void testPipelineDemandCountsReproducible();         // INV-INS-93 (round-8 introduction)
    // Round-8 D11/D13 introductions
    @Test void testBaseAspectExclusionsSchemaPresent();        // INV-INS-97 (round-8 empirical revision: asserts AspectDescriptor has baseAspectExclusions: List<String>, NOT the retired namedPointcuts: Map)
}

// IMPORTANT — testSkipCountEqualsZero implementation note (round-8 J-cleanup):
// The test builds a LauncherDiscoveryRequest using selectPackage("br.unb.cic.rv.grammar")
// AND ClassNameFilter.includeClassNamePatterns("br\\.unb\\.cic\\.rv\\.grammar\\.[^.]*GrammarTest").
// The include filter — top-level package only, classes ending in `GrammarTest` —
// structurally excludes both MatrixIntegrityTest (suffix `Test`, not `GrammarTest`) AND
// the robustness subpackage (`[^.]*` does not cross `.`). Without these filters,
// Launcher.execute(request) re-discovers MatrixIntegrityTest itself and recurses into
// testSkipCountEqualsZero until StackOverflowError. Sentinel assertions inside
// the test verify the discovered TestPlan contains zero TestIdentifiers whose source class
// is MatrixIntegrityTest AND zero whose source class is in `br.unb.cic.rv.grammar.robustness.*`,
// so a regression in the filter fails loudly rather than silently re-introducing the
// recursion bug or counting RobustnessTest methods as enabled tests with no matrix row.

// Per-designator grammar test classes (one method per matrix row).
// Round-8 C-cleanup (2026-05-28 per cross-LLM meta-review): verdict annotations
// reflect the post-round-8 archive state (every gh62 in-change closure has flipped
// SILENT-GAP → COVERED; round-7's @Disabled is gone).
class CallPointcutGrammarTest { /* exact, T+, *, .., trailing-varargs (§4.V COVERED), owner T+ (§4.O COVERED), name glob (§4.X COVERED); return T+ = NOT-NEEDED α (§4.R REMOVED, R11.3) */ }
class ExecutionPointcutGrammarTest { /* execution(...) — NOT-NEEDED β (R11.2): pipeline POSITIVE = 0; test asserts countCompiledAj==0 + names `coverage-weaver` as absorber (sole consumer Coverage.aj:50) */ }
class TargetGrammarTest { /* target(name) binding [COVERED], target(Type) [COVERED §4.TT — declared-type semantics per V-decision] */ }
class ThisGrammarTest { /* this(name), this(Type) — both NOT-NEEDED α (zero corpus demand) */ }
class ArgsGrammarTest { /* args(name) binding [COVERED], args(Type) [COVERED §4.AT — declared-type per V-decision], args(*, name, ..) [COVERED via §4.V trailing-mixed] */ }
class WithinFamilyGrammarTest { /* within() positive simple [NOT-NEEDED β — round-10 AB-decision: pipeline POSITIVE = 0], !within() [COVERED via §4.B/§4.D], within(*..Log) suffix [NOT-NEEDED β — Coverage.aj absorbed], within(T+) [NOT-NEEDED β — Coverage.aj absorbed] */ }
// Note: returning(name)/throwing(name) advice modifiers are tested inside
// AdviceFormGrammarTest.afterReturningAdvice() and .afterThrowingAdvice(),
// not as a standalone test class — they bind only inside after()-form contexts.
class CflowGrammarTest { /* cflow(), cflowbelow() — both NOT-NEEDED α (zero corpus demand) */ }
class IfGrammarTest { /* if(...) — COVERED §4.I via runtime-helper delegation (D13 + B/Y-decisions) */ }
class HandlerGrammarTest { /* handler() — NOT-NEEDED α (round-8 P-decision: moved from path β; zero source demand) */ }
class FieldAccessGrammarTest { /* get(), set() — NOT-NEEDED α (zero corpus demand; earlier 356/158 conflated method-name calls with field-access) */ }
class StaticInitializationGrammarTest { /* staticinitialization(T+) — COVERED §4.Y (synthesis for absent <clinit>) */ }
class InitializationGrammarTest { /* initialization(), preinitialization() — both NOT-NEEDED α */ }
class AdviceExecutionGrammarTest { /* adviceexecution() — NOT-NEEDED β (vacuously true in dexlib2 inline-call emission model; deferred §2.2.1-C) */ }
class NamedReferenceGrammarTest { /* named refs, BaseAspect.notwithin() expansion — COVERED §4.B/§4.D via baseAspectExclusions per A-decision (NOT a new namedPointcuts schema); includes baseAspectNotwithinExpandsTwelveExclusionsList per Z-decision INV-INS-101 */ }
class AnnotationPointcutGrammarTest { /* @annotation, @target, @this, @args, @within, @withincode */ }
class AdviceFormGrammarTest { /* before, after, after returning, after throwing, around, around proceed(...) */ }
class TypePatternGrammarTest { /* T+ (param/owner/return/!within), *, .., dot-glob, arrays, inner classes */ }
class SignatureModifierGrammarTest { /* public/!public/static/final/throws */ }
class CompositionGrammarTest { /* &&, ||, !, parens */ }
// Behavioural-parity families — added so the matrix covers what advice bodies
// consume at runtime, not just what the pointcut parser sees.
class JoinPointReflectiveApiGrammarTest { /* thisJoinPoint, thisJoinPointStaticPart,
    thisEnclosingJoinPointStaticPart, JoinPoint.getArgs(), .getSignature() + Signature
    subtypes, .getTarget()/.getThis(), .getKind()/.getSourceLocation(),
    org.aspectj.lang.JoinPoint runtime linkage */ }
class AspectDeclarationGrammarTest { /* aspect Foo {...} declaration, named pointcut
    declaration `pointcut p(): ...`, abstract aspect + concrete subaspect (BaseAspect
    idiom), aspect inheritance, declare precedence, privileged aspect */ }
// proceed(...) is tested inside AdviceFormGrammarTest.aroundProceedSemantics(),
// not as a standalone class — it is an around-advice mechanic, not a designator.

// Adversarial / infrastructure robustness — does NOT correspond to matrix rows;
// asserts the surrounding infrastructure (parser, DemandCounter, MatrixMarkdownParser,
// ledger lookup) fails loudly with diagnostic messages under malformed inputs.
// Added per cross-LLM coverage review (option D). All methods enabled, none @Disabled.
// IMPORTANT: placed in subpackage `br.unb.cic.rv.grammar.robustness` and named
// `RobustnessTest` (not `*GrammarTest`) so MatrixIntegrityTest's bidirectional
// checks (§6.5/§6.6/§6.7) — which scan `br.unb.cic.rv.grammar.*GrammarTest` —
// structurally skip it. INV-INS-92 (enabled-test ↔ matrix-row bijection) holds
// without an exception clause: this class is outside the bijection scope.
package br.unb.cic.rv.grammar.robustness;
class RobustnessTest { /* malformedPointcutMissingClosingParen,
    malformedPointcutUnicodeIdentifier, malformedPointcutReservedAtSymbol,
    demandCounterWithoutRvsecHome, demandCounterWithEmptyCorpus,
    matrixMarkdownParserWithCorruptedTable, ledgerFallbackWithMissingActiveAndArchive,
    ledgerFallbackWithAmbiguousArchiveGlob */ }

// Helpers
class util.DemandCounter { /* Files.walk + compiled Pattern per designator */ }
class util.MatrixMarkdownParser { /* commonmark-java wrapper; locates table after `## Matrix` heading */ }
```

The exact set of test methods per class is enumerated in `tasks.md`. Each test method's Javadoc cites the matrix row it backs (e.g. `@see docs/aspectj_grammar_coverage.md row "args(name) binding"`).

## Data Flow

```
AspectJ Programming Guide §"Pointcuts" + AspectJ 5 quick ref       $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/
                 │                                                           │
                 │ grammar reference                                         │ DemandCounter (Files.walk + Pattern)
                 ▼                                                           ▼
        docs/aspectj_grammar_coverage.md ◀──────────────────────────── Demand column
                 │
                 │ Evidence column cites test FQNs
                 ▼
        grammar-tests/src/test/java/br/unb/cic/rv/grammar/
                 │
                 │ exercises (Maven dep)
                 ▼
        pointcut-engine + advice-emitter + dex-mutator (unchanged)
                 │
                 │ test bar
                 ▼
        mvn -pl grammar-tests test
                 │
                 │ PASS count = COVERED + EXPLICIT-NO-OP + NOT-NEEDED rows count
                 │ SKIP count = 0 (enforced by testSkipCountEqualsZero — round-8 J-cleanup)
                 │ FAIL count = 0 (any failure breaks CI)
                 ▼
        Visible at every CI run
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Matrix row count diverges from `AspectJDesignators.DESIGNATORS` | `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` | Fail the test with the missing/extra designator name (both directions) | Add or remove the row in the same commit |
| Matrix row cites a test FQN that does not exist | `MatrixIntegrityTest.testCoveredRowsCiteEnabledPassingTests` | Fail naming the dangling FQN | Either add the test or update the matrix |
| Enabled test exists in `grammar-tests/` but no matching matrix row | `MatrixIntegrityTest.testEnabledTestsResolveToValidMatrixRow` (round-8 J-cleanup — replaces round-7 `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`; post-round-8 all tests are enabled) | Fail naming the orphan test | Add the matrix row or delete the test |
| `@Disabled` annotation appears in `grammar-tests/` (zero post-round-8) | `MatrixIntegrityTest.testNoDisabledTestsRemain` (round-8 J-cleanup — replaces round-7 `testDisabledTestsResolveToSilentGapRow`) | Fail naming the offending disabled test | Remove `@Disabled` and re-classify the row (no SILENT-GAP rows survive archive) |
| Disabled-test count drifts from zero | `MatrixIntegrityTest.testSkipCountEqualsZero` (round-8 J-cleanup — replaces round-7 `testSkipCountEqualsSilentGapCount`; the SILENT-GAP count IS zero post-round-8 so the target collapses to a constant) | Fail when `Skipped != 0` | Either flip the matrix row to `COVERED` and remove `@Disabled`, or fix the regression |
| Non-COVERED matrix row missing from `deferred.md` | `MatrixIntegrityTest.testNonCoveredRowsAppearInDeferredDocument` (round-8 J-cleanup — replaces round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry`; the round-7 `ledger.md` artefact is RETIRED in favour of `deferred.md` per D4) | Fail naming the row and the missing `deferred.md` entry | Add the deferred entry with rationale OR move the row to COVERED |
| Demand counts diverge from `DemandCounter` | `MatrixIntegrityTest.testDemandCountsReproducible` | Fail naming the row and the actual count | Update the matrix |
| Sub-change modifies `*/src/main/` without matrix update | `MatrixIntegrityTest` (orphan-test or orphan-row detection in CI) | Fail the build | Update the matrix in the same commit |

Production code changes ship in this change (the **eleven round-11 closures** — §4.{O,N,V,X,TT,AT,Y,T,B,D,I} — including the `NamedRefPC` resolver that consumes `baseAspectExclusions`; §4.E/§4.W NOT-NEEDED β [coverage-weaver]; §4.R NOT-NEEDED α [R11.3]; §4.JP folded into §4.Y as the fork-free Signature-delivery sub-closure per R11.5). Each closure has its own error-handling discipline: emit failures (e.g. `__STATICSIG` cannot resolve declaring class metadata) log at WARN level and fall back to the pre-change behaviour for that single advice; matcher false negatives (e.g. method-name glob fails to recognise a pattern) are logged and the matcher returns no match (conservative — no spurious instrumentation); the `after throwing` install verifies try-range register liveness against `RegisterShifter` (gh61) and aborts the install with a logged diagnostic if the topology conflicts with an existing try-catch. No closure introduces a new `UnsupportedOperationException` path into production (those remain limited to `around`/`proceed` per D8 Deferred-by-design).

## Risks / Trade-offs

- **[Risk] Matrix drift in sub-changes** — historically, ad-hoc fixes ship without updating docs. → **Mitigation**: `MatrixIntegrityTest` runs on every CI invocation and fails on every structural divergence (orphan tests, orphan rows, skip-count mismatch). A separate cross-repo PR-check workflow was considered and rejected on simplicity grounds (D6) — the integrity test running at commit-time is the same enforcement at lower complexity.
- **[Risk] DemandCounter regex drift** — a designator whose regex is too loose (substring match) or too tight (missing form) corrupts the demand baseline. The original draft's 356/158 `get/set` count was exactly this failure mode. → **Mitigation**: each designator's `Pattern` is reviewed against a known-good sample from the corpus and quoted inline in the matrix; `testDemandCountsReproducible` runs at every CI invocation; the matrix row's `Demand` column is the visible value, the regex is the audit trail.
- **[Risk] AspectJ Programming Guide is a moving reference** — new AspectJ versions could add pointcut designators. → **Mitigation**: the matrix anchors to the AspectJ Programming Guide §"Pointcuts" + AspectJ 5 quick reference at a specific URL with a snapshot date in its header; bumping the reference is a new sub-change with explicit matrix amendment.
- **[Risk] Deferred document goes stale post-archive** (round-8 J-cleanup — round-7 risk title was "Ledger goes stale"; `ledger.md` retired in favour of `deferred.md` per D4) — `openspec/changes/gh62-.../deferred.md` is archived after merge. → **Mitigation**: the deferred document is a one-shot snapshot whose immutability is positively enforced by `deferred.snapshot.sha256` (D7); the matrix at `docs/aspectj_grammar_coverage.md` is the live backlog. Future closures are scheduled by opening one OpenSpec change per closure when pipeline demand surfaces, not by maintaining a parallel issue tracker.
- **[Trade-off] gh62 ships ~470-560 LOC of production code (round-11)** — was ~565-660 in round-10; round-11 removes §4.R (~30 LOC, zero demand R11.3), reshapes §4.Y to the fork-free `rvsec-core` substrate (~70 weaver + ~35 rvsec-core), and replaces the D13 §4.I path with ~60 LOC in-weaver lowering (no monitor-builder helper). The biggest LOC contributors are §4.T `after() throwing(...)` with range-splitting (~120-160 LOC) and §4.Y `staticinitialization(T+)` synthesis + fork-free Signature delivery (~105 LOC). §4.D and §4.B stay small (~50-60 LOC) by consuming the existing `baseAspectExclusions` field. → **Mitigation**: bisect-friendly task plan (one closure per commit: §4.{O,N,V,X,TT,AT,Y,T,B,D,I}); bipartite smoke gate (≥10 JCA APKs for §4.O/V/B/D + grammar-tests fixture+dexdump for §4.I/Y/X/N/TT/AT/T); the matrix integrity tests catch closure-atomicity violations at commit time.
- **[Risk — round-8] Path-β absorber regression — silent re-surfacing of an absorbed construction.** If a future JavaMOP toolchain stops absorbing `condition(...)` (or any path-β construction), the construction re-surfaces at the dexlib2 instrumenter without notice; the matrix row carries `Verdict = NOT-NEEDED β` but production would now be silently broken. → **Mitigation**: `INV-INS-96` (round-8) — every path-β assertion test verifies THREE properties at every CI run: (a) source demand ≥ 1, (b) pipeline demand == 0, (c) named absorber file/module exists. If property (b) flips (pipeline demand becomes non-zero), the test fails the build and the matrix amendment workflow opens a new sub-change to ship the closure.
- **[Risk RETIRED — round-8 A-decision 2026-05-28] Symbol-table resolver schema compatibility across rvsec repos.** The early-round-8 risk register included "extending `AspectDescriptor` with `namedPointcuts: Map<String, PointcutExpression>` requires JavaMOP toolchain coordination". Empirical inspection 2026-05-28 (`AspectDescriptor.java` + `MultiSpec_1MonitorAspect.json`) proved the schema already exposes `baseAspectExclusions: List<String>` populated by `DescriptorWriter.defaultBaseAspectExclusions()` — no cross-repo schema change is needed. The §4.D / §4.B closures consume the existing field; the risk is retired and tasks §0.5 is downgraded from "verify cross-repo `namedPointcuts` emission" to "verify `baseAspectExclusions` is non-empty in production descriptors and matches the canonical twelve-entry baseline". `NamedRefResolverTest` covers three paths: `BaseAspect.notwithin` expansion against the canonical list, fail-closed on unrecognised names (G-decision), fail-closed on empty list (legacy descriptor).
- **[Risk RETIRED — round-11 R11.5] §4.I runtime-helper delegation drift.** The round-8 design split `if()` evaluation across the dexlib2 weaver (content-hashed `ifId`) and a JavaMOP-side `MonitorRuntimeIfHelperEmitter` switch-case, creating a cross-repo `ifId`-drift hazard. That whole architecture is RETIRED: §4.I now lowers the two corpus shapes (`o==null`, `!Thread.holdsLock(o)`) directly in `IfGuardEmitter` with a fail-loud default — single repo, no `ifId`, no cross-side hash, no drift surface. The residual risk is only "an unforeseen `if()` shape appears in a future corpus", caught by the fail-loud default + `IfGuardLoweringTest.unsupportedShapeFailsLoud` and `MatrixIntegrityTest` pipeline-demand reproducibility.
- **[Trade-off] `grammar-tests/` is a new Maven module** — every developer running `mvn package` now builds an extra module. → **Mitigation**: test-only module, small incremental build cost; excluded from the shaded `instr-cli.jar` so the production artefact is unaffected.
- **[Risk] `smali-dexlib2` 3.0.8 → 3.0.9 bump regression** — no announced breaking changes, but the reactor build is not a behavioural oracle. → **Mitigation**: §0.3a re-instruments 5 APKs from the INV-INS-31 baseline pre/post-bump and `dexdump`-diffs the output. Any non-trivial divergence reverts the property change inside gh62.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|--------------|-----|-------|
| Document integrity | Matrix row count == `AspectJDesignators.DESIGNATORS` (both directions) | `testEveryDesignatorHasMatrixRow` | 1 |
| Document integrity | Every matrix `Verdict` is in `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`; `NOT-NEEDED` requires zero demand + no impl | `testVerdictsAreValid` | 1 |
| Document↔code link (matrix→tests) | Every COVERED row cites an enabled passing test FQN | `testCoveredRowsCiteEnabledPassingTests` | 1 |
| Document↔code link (matrix→deferred) | Every non-COVERED matrix row (EXPLICIT-NO-OP or NOT-NEEDED α/β) appears in `deferred.md` with rationale; active-then-archive path fallback (round-8 J-cleanup — replaces round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry` since the matrix archives with zero SILENT-GAP rows and `ledger.md` is retired) | `testNonCoveredRowsAppearInDeferredDocument` | 1 |
| Document↔code link (tests→matrix) | Every test method resolves to a valid matrix row (round-8 J-cleanup — replaces round-7 `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`; all tests are enabled post-round-8) | `testEnabledTestsResolveToValidMatrixRow` | 1 |
| Document↔code link (no skips) | Zero `@Disabled` annotations remain in `grammar-tests/` (round-8 J-cleanup — replaces round-7 `testDisabledTestsResolveToSilentGapRow`; EXPLICIT-NO-OP tests are enabled and assert UOE, NOT-NEEDED α/β tests are enabled and assert demand counters) | `testNoDisabledTestsRemain` | 1 |
| Document↔code link (skip count) | `Skipped` count == 0 (round-8 J-cleanup — replaces round-7 `testSkipCountEqualsSilentGapCount`; the SILENT-GAP count is itself zero post-round-8 so the target collapses to a constant) | `testSkipCountEqualsZero` | 1 |
| Document↔data link | Demand counts reproducible by `DemandCounter` | `testDemandCountsReproducible` | 1 |
| Grammar coverage | One test method per matrix row, exercising the end-to-end pipeline; round-8 adds parameterized scenarios for every in-change closure (`within` positive simple, `T+` owner/return, `!target/!args`, `(T,..)` trailing-mixed, method-name glob, `target(Type)`, `args(Type)`, `staticinitialization` synthesis, `after throwing`, `BaseAspect.notwithin`, named-pointcut resolver, `if(...)` runtime delegation) | The per-designator `*GrammarTest` classes | ~100-120 across all rows (closed-enumeration rows + 13 round-8 closure rows + parametric expansions + 8 robustness tests). **Round-8 removals**: ~30 substrate contract tests + 1 Coverage.aj end-to-end test + 1 FQN-remap test are NOT shipped (the underlying production code is also not shipped — see D10 SUPERSEDED). |
| Named-pointcut resolver (round-8 narrowed scope) | Table-hit + commonPointcut-fallback + always-match-fallback paths; single-entry-per-descriptor for JCA `BaseAspect.notwithin()` | `NamedRefResolverTest` | 3 tests |
| Descriptor schema compatibility (round-8 A-decision 2026-05-28) | Production descriptor JSON deserialises with the canonical twelve-entry `baseAspectExclusions` list AND with empty list (legacy descriptor → `LegacyDescriptorException`); the early-round-8 `namedPointcuts` schema field is RETIRED so no old/new format split exists | `DescriptorReaderCompatibilityTest` | 2 tests |
| Path-β absorber contract (round-8 introduction) | Each path-β assertion test verifies (a) source demand ≥ 1, (b) pipeline demand == 0, (c) named absorber file/module exists with documented evidence | `AbsorptionClaimsContractTest` aggregates per-row tests | 7 absorber-contract tests (one per round-8 reclassified closure) + 1 `execution(...)` test |
| `if(...)` fork-free in-weaver 2-shape lowering (round-11 R11.5; D13 retired) | `o==null`→`if-nez`; `!Thread.holdsLock(o)`→`invoke-static`+branch; unsupported shape fails loud; monitor skipped when guard false | `IfGuardLoweringTest` | 4 tests |
| Regression | Existing reactor build remains green | `mvn package` at the reactor root | 1 reactor build |
| Smali bump behavioural diff | 5 APKs pre/post-3.0.9 produce equivalent `dexdump` output | §0.3a script | 5 APK diffs |
| Smoke validation (round-10 bipartite gate) | **(i)** ≥10 APKs from JCA-226 baseline exercise §4.O/§4.V/§4.B/§4.D on ART; no new VerifyError; monotonic non-decrease event count. **(ii)** `grammar-tests` fixture + `dexdump` diff validates §4.I/§4.Y (incl. Signature delivery — AC-decision)/§4.X/§4.N/§4.TT/§4.AT/§4.T since no current production APK exercises generic_new end-to-end. **Round-7 Coverage.aj gate DROPPED**. **Round-9 §4.E execution-via-fixture gate REMOVED** (AA-decision: §4.E not in scope). | §6.S script + grammar-tests Maven module | ≥10 APK runs (gate i) + 7 fixture+dexdump verdicts (gate ii) |

The `grammar-tests` module imposes no integration or pipeline tests; matrix and `deferred.md` (round-8 J-cleanup — `ledger.md` retired per D4) are documentation-class artefacts and need no `validate_instrument_jca190.py` re-run.

## Open Questions

- **OQ1 — RESOLVED.** Earlier draft asked whether `T+` is a row or a modifier. Decision: **`T+` produces dedicated rows per position** (`T+` in `call()` params / owner / return / inside `!within()`), because the matcher diverges per position (params via `isAssignableFrom`, owner/return via exact descriptor). The closed enumeration in the delta spec lists each position as a distinct row. `T+` is NOT a modifier column.
- **OQ2 — RESOLVED.** Earlier draft asked whether `MatrixIntegrityTest` should parse Markdown directly or via a sidecar JSON. Decision: **Markdown directly, via `commonmark-java`** (test-scope dep). Sidecar JSON would double the maintenance surface; a custom ~50-LOC parser was rejected on robustness grounds (cross-LLM review pointed out happy-path-only handling of separator rows, whitespace, embedded pipes).
- **OQ3 — RESOLVED.** Earlier draft asked about AspectJ extensions (`lock`/`unlock`). Decision: **omit on demand-zero grounds**, not on "not in guide" grounds (they ARE in the AspectJ 1.5+ guide). Documented in the matrix header as a single line: `lock`/`unlock` are not in the closed enumeration because `DemandCounter` returns zero across all four corpora.
- **OQ4 — RESOLVED (round-3 cross-LLM review).** Cross-LLM review surfaced AspectJ-canonical productions that appear in the AspectJ Programming Guide and the AspectJ 5 Developer's Notebook but do NOT appear as rows in this change's closed enumeration. Decision: **document as AUSENTE-JUSTIFICADO once here**, do NOT inflate the matrix with `NOT-NEEDED` rows. Adding ten matrix rows that nobody ever runs and that have demand=0 is the kind of speculative scaffolding that P1 (Simplicity) forbids; the closed enumeration remains closed for the subset declared, and this OQ is the canonical reference for the subset omitted. The matrix header MUST link back to this OQ so reviewers can resolve "why isn't `<X>` a row?" in one hop. The omitted families and the AUSENTE-JUSTIFICADO rationale are:
  - **Per-clauses** (`issingleton()`, `perthis()`, `pertarget()`, `percflow()`, `percflowbelow()`, `pertypewithin()`): aspect instantiation models. `DemandCounter` returns zero across all four corpora; JavaMOP-generated aspects use the default `issingleton()` implicitly (the keyword is never written). New corpora that exercise per-clauses would add rows by amendment.
  - **Inter-Type Declarations** (`declare parents`, method introductions, field introductions, constructor introductions): the JavaMOP code generator does not emit ITDs and the four corpora contain none. Out of scope for the dexlib2 instrumenter's current use cases.
  - **Static declarations** (`declare warning`, `declare error`, `declare soft`): compile-time-only mechanisms with no runtime weaving footprint. The dexlib2 instrumenter is a runtime weaver; declare-warning/error fire at AspectJ compile time and produce no DEX bytecode artefact. Out of scope by construction.
  - **Annotation-style aspect syntax** (`@Aspect`, `@Before`, `@After`, `@Around`, `@Pointcut`): an alternative AspectJ 5 surface where aspects are plain Java classes annotated with `@Aspect`. The four corpora exclusively use code-style (`aspect Foo { ... }` declaration syntax with `pointcut p(): ...` and advice-form keywords); annotation-style aspects are a different parser input shape and would require a separate parser path. Demand=0. New corpora that adopt annotation-style would add rows by amendment.
  - **Generics in type patterns** (`<T extends X>`, `Foo<Bar>`, parameterised method signatures): the JavaMOP-generated pointcuts target erasure-level method signatures; generic-parameter syntax in pointcuts is not emitted by the JavaMOP code generator and is absent from all four corpora.

  None of these families overlap with the round-3 added behavioural-parity families (advice-body reflective API, around mechanics, aspect declaration mechanics, runtime linkage) — those ARE in the closed enumeration with non-zero demand. If a future MOP spec generator adopts any of the OQ4 families, the row(s) MUST be added by amendment to the closed enumeration and OQ4 updated to remove the entry; `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` will fail the build until the amendment lands.

- **OQ5 — RESOLVED (round-5 cross-LLM review).** Cross-LLM review (deepseek, opus47) flagged that the round-3 SILENT-GAP-permanent sub-bucket (`handler(...)`, `declare precedence`) and the round-4 Fix-now rows for `aspect Foo { ... }` and `pointcut p(): ...` declaration mechanics were better classified as `NOT-NEEDED` via INV-INS-89 path β than as SILENT-GAP. Decision: **reclassify the four rows to `Verdict = NOT-NEEDED` (path β)**, eliminate the SILENT-GAP-permanent sub-bucket entirely, and document the absorption mechanism per row:
  - `handler(...)` — no DEX-level analogue for exception-handler joinpoints; the matched syntax is absorbed by the matcher's family-of-pointcuts decision (the matcher routes `handler` to `NamedRefPC` instead of synthesising a handler-joinpoint matcher), making `handler` source-level present but pipeline-level absent. Evidence: `upstream-stage:PointcutExpressionParser-NamedRefPC-fallback`, `demand-source:0 across all corpora`, `test-fqn:HandlerGrammarTest.handlerAbsorbedByNamedRefPC`.
  - `declare precedence` — runtime monitor-dispatch property; the rvsec MonitorRuntime serialises monitor invocations through a deterministic dispatch loop, so the AspectJ "precedence" semantics are realised by the loop ordering, not by the weaver. Evidence: `upstream-stage:MonitorRuntime-dispatch-loop`, `demand-source:0`, `test-fqn:AspectDeclarationGrammarTest.declarePrecedenceAbsorbedByDispatchLoop`.
  - `aspect Foo { ... }` declaration syntax — `.aj` source is consumed by the upstream JavaMOP compiler, which emits JSON `AspectDescriptor`. `DescriptorReader.java` reads JSON; `PointcutExpressionParser` never sees `aspect`/`pointcut` source tokens. Evidence: `upstream-stage:JavaMOP-descriptor-emit + DescriptorReader.java:13-15`, `demand-source:source-level non-zero (aspect=1, jca=2, generic_new=2) but pipeline demand = 0`, `test-fqn:AspectDeclarationGrammarTest.aspectFooAbsorbedByDescriptorReader`.
  - `pointcut p(): ...` named declaration — same path β as `aspect Foo`. Evidence: `upstream-stage:JavaMOP-descriptor-emit`, `demand-source:source-level non-zero (aspect=2, jca=1, generic_new=1, and round-5 grep showed 55-115 in `.aj` templates) but pipeline demand = 0`, `test-fqn:AspectDeclarationGrammarTest.namedPointcutDeclarationAbsorbedByDescriptorReader`.

  None of these four rows appears in the ledger (NOT-NEEDED rows are not open work); each row carries an enabled passing test asserting equivalent-descriptor production regardless of upstream syntax. INV-INS-89's path β regex requirement (Evidence cites `upstream-stage:`, `demand-source:`, `test-fqn:`) is satisfied by the bullets above. Future closures of these rows (if a MOP spec generator ever needs DEX-level handler/precedence support) MUST flip the row from NOT-NEEDED to SILENT-GAP and add a ledger entry.
