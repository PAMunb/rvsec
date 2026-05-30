# AspectJ Grammar Coverage Matrix — dexlib2 instrumenter

> **This document is the authoritative contract** for the AspectJ pointcut surface that the
> DEX-native dexlib2 instrumenter (`rvsec-android/rvsec-instrumentation-dexlib2/`) weaves
> correctly today. It supersedes `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and
> `docs/AJ_TO_DEXLIB2_MAPPING.md` (INV-INS-102). The matrix is materialised as executable
> tests in the `grammar-tests/` Maven submodule; `MatrixIntegrityTest` breaks the build if the
> matrix and the code/tests move independently.

## References

- **AspectJ Programming Guide §"Pointcuts"** — https://eclipse.dev/aspectj/doc/latest/progguide/semantics-pointcuts.html (snapshot 2026-05-29)
- **AspectJ 5 Quick Reference** — https://eclipse.dev/aspectj/doc/latest/quick5.pdf (snapshot 2026-05-29)
- **smali-dexlib2 version** — `3.0.9` (verified against `https://maven.google.com/com/android/tools/smali/group-index.xml`, §0.4; pinned in `rvsec-instrumentation-dexlib2/pom.xml`)

## Verdict vocabulary

Every matrix row carries exactly one `Verdict` from the closed set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}` (INV-INS-89). After gh62 archives there are **zero `SILENT-GAP` rows** (INV-INS-91).

- **COVERED** — the construction is woven correctly by dexlib2 today. Evidence is an enabled, passing test FQN in `grammar-tests/`.
- **SILENT-GAP** — the construction reaches the instrumenter with non-zero pipeline demand but is dropped without an error. **No row may carry this verdict post-archive** — it must be closed (flip to COVERED) or reclassified (EXPLICIT-NO-OP / NOT-NEEDED). Retained in the vocabulary only so `MatrixIntegrityTest.testNoSilentGapRowsRemain` has a value to forbid.
- **EXPLICIT-NO-OP** — the construction is deliberately not woven and the code raises `UnsupportedOperationException` at the weave attempt. Evidence cites BOTH the UOE-asserting test FQN AND the `file:line` of the no-op. (Currently only `around` / `proceed(...)`.)
- **NOT-NEEDED** — the construction need not be woven, via one of two paths:
  - **path α** — `DemandCounter.countMop == 0` across all four corpora AND no parser/matcher/emitter implementation. Zero demand everywhere; no absorber needed.
  - **path β** — `DemandCounter.countMop ≥ 1` (source demand exists) BUT `DemandCounter.countCompiledAj == 0` (pipeline demand is zero — the construction is absorbed by a named upstream stage before reaching dexlib2). Evidence cites both demand counts, the named absorber, the empirical evidence, and an enabled passing assertion test.

## Demand counting

Demand is counted by the portable Java helper `DemandCounter` in `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/DemandCounter.java` (no shell, no `ProcessBuilder`):

- `countMop(designator, corpus)` — **SourceDemand**: walks `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/` matching **only `*.mop` files plus `aspect/Coverage.aj`** (never the git-ignored `-s` stray `*.aj` build artifacts in those dirs).
- `countCompiledAj(designator, corpus)` — **PipelineDemand**: walks the committed `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj` snapshot (byte-identical to a fresh `rv-monitor-generator` run WITHOUT `-s`). **PipelineDemand is the authoritative scope signal**: closures ship in-change when PipelineDemand ≥ 1, not when SourceDemand ≥ 1.

Each designator's `java.util.regex.Pattern` is the audit trail and is pinned in `DemandCounter`'s regex map; `MatrixIntegrityTest.testSourceDemandCountsReproducible` and `.testPipelineDemandCountsReproducible` assert the matrix columns against the helper's output at every CI run (INV-INS-93). The per-row counting rule (per-occurrence vs per-line, negated-form ownership) is pinned per INV-INS-93 so the counts reproduce deterministically.

## Matrix

| AspectJ syntax | SourceDemand (aspect,jca,generic,generic_new) | PipelineDemand (compiled .aj) | Parser | Matcher | Emitter | Verdict | Evidence | Deferral note |
|---|---|---|---|---|---|---|---|---|
| `call(MethodPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `execution(MethodPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `target(name)` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `target(Type)` type-matching | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `this(name)` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `this(Type)` type-matching | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `args(name)` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `args(Type)` type-matching | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `args(*, name, ..)` mixed | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `withincode(MethodPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `cflow(Pointcut)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `cflowbelow(Pointcut)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `if(BooleanExpression)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `handler(TypePattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `get(FieldPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `set(FieldPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `staticinitialization(TypePattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `initialization(ConstructorPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `preinitialization(ConstructorPattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `adviceexecution()` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| named-pointcut reference | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `condition(BooleanExpression)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `__STATICSIG` macro | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `within(pkg..*)` positive simple | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `within(*..Log)` suffix-wildcard | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `within(T+)` T+-inside-positive | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `!within(TypePattern)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@annotation(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@target(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@this(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@args(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@within(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `@withincode(AnnotationType)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `before()` advice | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `after()` advice | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `after() returning(Id)` advice | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `after() throwing(Id)` advice | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `around()` advice | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `T+` in `call()` param | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `T+` in `call()` owner | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `T+` in `call()` return | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `T+` inside `!within(...)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `*` wildcard | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `..` standalone varargs | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `(T, ..)` trailing-mixed | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `..*` dot-glob | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `.*` single-level glob | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `T[]` / `T[][]` arrays | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `Outer.Inner` inner-class qualifier | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| positive visibility (`public`) | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| negated visibility (`!public`) | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `static` signature modifier | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `final` signature modifier | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `throws ExceptionPattern` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `&&` composition | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `\|\|` composition | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `!` negation | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| parentheses grouping | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `thisJoinPoint` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `thisJoinPointStaticPart` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `thisEnclosingJoinPointStaticPart` binding | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `JoinPoint.getArgs()` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `JoinPoint.getSignature()` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `JoinPoint.getTarget()` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `JoinPoint.getKind()` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `proceed(...)` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `aspect Foo { ... }` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `pointcut p(): ...` declaration | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `abstract aspect` + concrete subaspect | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| aspect inheritance | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `declare precedence` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| privileged aspect | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `org.aspectj.lang.JoinPoint` family | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

<!-- Round-8 scaffold: SourceDemand/PipelineDemand/Parser/Matcher/Emitter/Verdict/Evidence/Deferral
     are TBD; populated in tasks §1 (demand) and §5 (verdicts+evidence) against the DemandCounter
     output and the grammar-tests evidence FQNs. The "AspectJ syntax" column is the stable key:
     it MUST stay in 1:1 set-equality with AspectJDesignators.DESIGNATORS (INV-INS-88). 73 rows. -->
