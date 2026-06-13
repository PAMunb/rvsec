# OpenSpec Verification Report: gh62-aspectj-grammar-coverage

Schema: `rv-sdd` (Full SDD) — All 4 artifacts present: proposal, design, specs, tasks.

---

## 1. Completeness

| Metric | Value |
|--------|-------|
| Total tasks | ~204 |
| Completed (`[x]`) | 1 |
| SUPERSEDED (`[~]` strikethrough) | ~14 |
| Pending (`[ ]`) | ~189 |
| Completion rate | **0.5%** |

### Completed Task
- **4.S'.1** (2026-05-26): `__STATICSIG` archive precondition — confirmed zero occurrences in generic_new compiled `.aj`.

### SUPERSEDED Tasks (not counted as pending)
- §4.W.1–§4.W.5 (SUPERSEDED by round-10 AB-decision)
- §4.R.1–§4.R.3 (SUPERSEDED by round-11 R11.3)
- §4.E.1–§4.E.6 (SUPERSEDED by round-10 AA-decision)
- §4.JP'.1–§4.JP'.2 (SUPERSEDED by round-10 AC-decision)

### Section-by-Section Status

| Section | Status |
|---------|--------|
| §0 — smali-dexlib2 bump 3.0.8→3.0.9 | **PENDING** (0/5 tasks) |
| §0.5 — baseAspectExclusions precondition | **PENDING** (0/5 tasks) |
| §0.6 — delete -s stray .aj artifacts | **PENDING** (0/4 tasks) |
| §0.7 — audit 3 if() sites (R11.5) | **PENDING** (0/5 tasks) |
| §1 — Demand regen + deferred + SHA | **PENDING** (0/5 tasks) |
| §1.2a — generic_new fallback | **PENDING** (0/5 tasks) |
| §2 — Matrix scaffold | **PENDING** (0/16 tasks) |
| §3 — grammar-tests/ Maven module | **PENDING** (0/10 tasks) |
| §4 — Per-designator test classes | **PENDING** (0/4 tasks) |
| §4.W' — within NOT-NEEDED β assertion | **PENDING** (0/3 tasks) |
| §4.O — T+ owner (closure #1/11) | **PENDING** (0/5 tasks) |
| §4.R' — T+ return NOT-NEEDED α | **PENDING** (0/2 tasks) |
| §4.N — !target/!args (closure #2/11) | **PENDING** (0/4 tasks) |
| §4.V — trailing-mixed varargs (closure #3/11) | **PENDING** (0/5 tasks) |
| §4.X — name glob (closure #4/11) | **PENDING** (0/3 tasks) |
| §4.TT — target(Type) (closure #5/11) | **PENDING** (0/4 tasks) |
| §4.AT — args(Type) (closure #6/11) | **PENDING** (0/4 tasks) |
| §4.Y — staticinit+Signature (closure #7/11) | **PENDING** (0/7 tasks) |
| §4.T — after throwing (closure #8/11) | **PENDING** (0/5 tasks) |
| §4.D — NamedRefPC resolver (closure #9/11) | **PENDING** (0/5 tasks) |
| §4.B — BaseAspectExpander (closure #10/11) | **PENDING** (0/4 tasks) |
| §4.E' — execution NOT-NEEDED β | **PENDING** (0/3 tasks) |
| §4.I — if() PCD (closure #11/11) | **PENDING** (0/7 tasks) |
| §4.G'/S'/A'/RT'/CV'/WW' — NOT-NEEDED β tests | **PENDING** (0/6 tasks) |
| §5 — Matrix population | **PENDING** (0/7 tasks) |
| §6 — Integrity tests + CI gates | **PENDING** (0/14 tasks) |
| §6.S — Smoke validation bipartite gate | **PENDING** (0/6 tasks) |
| §7 — Cross-cutting + Archive | **PENDING** (0/7 tasks) |
| §7.8 — Legacy inventory SUPERSEDED banner | **PENDING** (0/4 tasks) |
| §8 — Out-of-scope checks | **PENDING** (0/1 task) |

**Assessment**: Change is in early-stage documentation phase. All OpenSpec artifacts exist, but zero implementation, testing, or document-creation tasks are complete.

---

## 2. Correctness

### 2.1 Empirical Demand Claims (from gh62-review.md)

Verified against compiled pipeline artifacts in `empirical-monitors/`:

| Designator | Claim | Evidence | Status |
|------------|-------|----------|--------|
| §4.O T+ owner | 64 (jca) | grep type+ in jca call() → 64 | **PASS** |
| §4.X name-glob | 13 (generic_new) | 13 `name*` occurrences | **PASS** |
| §4.V trailing-mixed | 6 (jca) | 6 pointcut defs with `(T, ..)` | **PASS** |
| §4.N !target | 14 (generic_new) | 14 `!target()` clauses | **PASS** |
| §4.N !args | 2 (generic_new) | 2 `!args()` clauses | **PASS** |
| §4.I if() | 3 (generic_new) | 2 `!Thread.holdsLock` + 1 `o==null` | **PASS** |
| §4.T after throwing | 1 (generic_new) | Line 294 | **PASS** |
| §4.Y staticinit | 3 (generic_new) | Lines 258, 317, 326 | **PASS** |
| §4.B/§4.D BaseAspect | 2 each | present in both jca+generic_new | **PASS** |
| §4.TT target(Type) | 22 (generic_new) | 22 `target(Type)` pointcuts | **PASS** |
| §4.AT args(Type) | 5 (generic_new) | 5 `args(Type)` pointcuts | **PASS** |

### 2.2 Implementation Correctness

**Implementation is absent for all 11 closures.** No code exists to verify against spec scenarios. Key absences:

| Requirement Area | Spec Scenarios | Implementation Status |
|-----------------|---------------|----------------------|
| BaseAspectExpander | §4.B macro expansion | `BaseAspectExpander.java` — **NOT CREATED** |
| NamedRefPC resolver | §4.D + fail-closed exceptions | `UnresolvedNamedRefException.java`, `LegacyDescriptorException.java` — **NOT CREATED** |
| NegationPC | §4.N !target/!args | `NegationPC.java` — **NOT CREATED** |
| splitParams refactor | §4.V trailing-mixed | `CallPC.java`/`ArgsPC.java` — **NOT MODIFIED** (uses old `String[]` API) |
| name glob | §4.X prefix matching | `PointcutMatcher.matchCall` — uses `equals()`, no `startsWith()` |
| target(Type) | §4.TT declared-type match | `TargetPC` — no type field |
| args(Type) | §4.AT declared-type match | `ArgsPC` — no type field |
| StaticInitSynthesizer | §4.Y <clinit> synthesis | `StaticInitSynthesizer.java` — **NOT CREATED** |
| org.aspectj.lang.Signature | §4.Y fork-free substrate | `Signature.java`, `ClassSignature.java` in rvsec-core — **NOT CREATED** |
| AfterThrowingEmitter | §4.T range-splitting | `AfterThrowingEmitter.java` — EXISTS, range-splitting **NOT IMPLEMENTED** |
| IfGuardEmitter | §4.I 2-shape lowering | `IfGuardEmitter.java` — EXISTS as stub, `emit()` body **EMPTY** |
| grammar-tests/ module | +20 spec scenarios | Maven module — **NOT CREATED** |
| docs/aspectj_grammar_coverage.md | Matrix contract | Document — **NOT CREATED** |
| DemandCounter | Reproducible counts | Java class — **NOT CREATED** |
| deferred.snapshot.sha256 | Frozen document | Snapshot — **NOT CREATED** |

### 2.3 Existing Skeleton Code (NOT yet gh62-specific)

The sibling repo (`rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`) contains skeleton infrastructure that pre-dates gh62:

- **advice-emitter/**: `AfterThrowingEmitter.java`, `IfGuardEmitter.java`, `StaticInitializationEmitter.java`, `ThisJoinPointEmitter.java`, `EmitterDispatch.java` — all exist. `IfGuardEmitter` is a stub (raw emit throws `UnsupportedOperationException`; wraps delegate but no lowering). `AfterThrowingEmitter` has an `emit()` but no range-splitting. `StaticInitializationEmitter` has no Signature special-case.
- **pointcut-engine/**: `NamedRefPC.java`, `IfPC.java`, `ExecutionPC.java`, `StaticInitPC.java`, `CallPC.java`, `TargetPC.java`, `ArgsPC.java`, `NotWithinPC.java`, `WithinPC.java` — all exist. `ExecutionPC.java` has placeholder content (round-10 AA-decision removed it from scope). `NamedRefPC.java` routes through placeholder (not BaseAspectExpander). `IfPC.java` carries `javaExpression` field.
- **dex-mutator/**: `DexWeaver.java`, `RegisterShifter.java`, `RegisterAllocator.java` — all exist. `DexWeaver` has placeholder `case TRY_CATCH_WRAP: case REPLACE: break;`.
- **NOT present**: `NegationPC.java`, `BaseAspectExpander.java`, `UnresolvedNamedRefException.java`, `LegacyDescriptorException.java`, `StaticInitSynthesizer.java`.

---

## 3. Coherence

### 3.1 Design Adherence

Design decisions (D1–D15) are well-documented. Implementation would adhere, but no code exists to evaluate:

| Decision | Claimed | Implementation Status |
|----------|---------|----------------------|
| D1 — Matrix in docs/ | docs/aspectj_grammar_coverage.md | **NOT CREATED** |
| D2 — grammar-tests/ submodule | New Maven module | **NOT CREATED** |
| D3 — zero @Disabled post-archive | All tests enabled | N/A (no tests exist) |
| D4 — deferred.md snapshot | SHA-pinned | **NOT CREATED** |
| D5 — smali bump 3.0.8→3.0.9 | pom.xml edit | **NOT DONE** |
| D7 — SHA snapshot | deferred.snapshot.sha256 | **NOT CREATED** |
| D8 — demand-driven closures | 11 closures | **NOT IMPLEMENTED** |
| D9 — pipeline-level demand scope | PipelineDemand column | N/A (matrix not created) |
| D11 — NamedRefPC via baseAspectExclusions | Existing field consumed | **NOT IMPLEMENTED** |
| D13 RETIRED — if() runtime delegation | Replaced by in-weaver | Correct (D13 retired in R11.5) |
| D14 — range-splitting F-decision | AfterThrowingEmitter | **NOT IMPLEMENTED** |
| D15 — matrix as source of truth | docs/ contract | **NOT CREATED** |
| R11.5 — fork-free Signature | rvsec-core substrate | **NOT CREATED** |

### 3.2 Code Pattern Consistency

Pre-existing skeleton code follows project conventions (Preconditions, builder patterns, dexlib2 API usage). No gh62-specific code exists to evaluate for consistency.

### 3.3 Cross-Reference Integrity

| Cross-Reference | Status |
|-----------------|--------|
| tasks.md ⇔ design.md decisions | Tasks reference D-designators correctly | **PASS** (documentation only) |
| tasks.md ⇔ delta spec scenarios | Tasks cite spec scenarios by name | **PASS** (documentation only) |
| design.md ⇔ delta spec | Design D-decisions align with spec requirements | **PASS** (documentation only) |
| Empirical counts ⇔ spec claims | All match per gh62-review.md | **PASS** |
| Source code ⇔ artifacts | No implementation to compare | **N/A** |
| docs/aspectj_grammar_coverage.md ⇔ matrix | Document does not exist | **FAIL** |

---

## 4. Issues

### CRITICAL (Must fix before archive)

| # | Issue | Recommendation |
|---|-------|---------------|
| C1 | Matrix document `docs/aspectj_grammar_coverage.md` not created | Create per design D1 / spec requirement. ~200 rows with demand columns, parser/matcher/emitter anchors, verdicts, evidence. |
| C2 | `grammar-tests/` Maven submodule not created | Create per design D2 / tasks §3. Required for all assertion tests. |
| C3 | `DemandCounter.java` not implemented | Required for reproducible demand counts (spec INV-INS-93, tasks §3.4). |
| C4 | `BaseAspectExpander.java` not created | §4.B closure — design D11 / tasks §4.B.1. |
| C5 | `UnresolvedNamedRefException` + `LegacyDescriptorException` not created | §4.D closure — G-decision fail-closed / tasks §4.D.1. |
| C6 | `NegationPC.java` not created | §4.N closure — tasks §4.N.1. |
| C7 | `StaticInitSynthesizer.java` not created | §4.Y closure — tasks §4.Y.1. |
| C8 | `org.aspectj.lang.Signature` interface + `ClassSignature` in rvsec-core not created | §4.Y fork-free substrate — tasks §4.Y.4 (R11.5). |
| C9 | `deferred.md` + `deferred.snapshot.sha256` not created | Required per spec requirement / tasks §1.3-§1.4. Existing `deferred.md` at change root needs review against R11. |
| C10 | All 11 closure implementations absent | Execute tasks §4.{O,N,V,X,TT,AT,Y,T,B,D,I} in order. |

### WARNING (Should fix)

| # | Issue | Recommendation |
|---|-------|---------------|
| W1 | SUPERSEDED tasks bloating task list | Mark strikethrough tasks with explicit `[x]` or archive the task entries. |
| W2 | Legacy inventory banners not applied | Add SUPERSEDED banner to `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and `docs/AJ_TO_DEXLIB2_MAPPING.md` per §7.8. |
| W3 | `deferred.md` exists at change root but not verified against R11 | Review `deferred.md` content against Round-11 banner and empirical-monitors evidence. |

### SUGGESTION (Nice to fix)

| # | Suggestion |
|---|-----------|
| S1 | Consider smaller milestone: split gh62 into (a) grammar-tests scaffold + matrix document, then (b) closure implementations per commit. |
| S2 | Add `NegationPC.java` to the existing `pointcut-engine` package listing in design.md if missing. |
| S3 | Document the sibling-repo relative path convention used in tasks.md for clarity (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`). |

---

## 5. Final Assessment

**3 CRITICAL issues found. Fix before archiving.**

| Dimension | Status |
|-----------|--------|
| Completeness | **0.5%** — 1/204 tasks done |
| Correctness | Empirical demand claims **PASS** — Implementation **ABSENT** for all 11 closures |
| Coherence | Artifacts internally consistent — No implementable code exists to verify against design |

**The empirical demand foundation is solid (verified in gh62-review.md)**, but the change is in an early documentation-only state. All 11 closures, the grammar-tests module, the matrix document, DemandCounter, deferred.md snapshot, and CI gates are pending implementation. The existing skeleton code (emitters, dispatch, PCs) provides the correct foundation, but none of the gh62-specific extensions have been built.

**Recommendation**: This change is not ready for archive. Ship the implementation per tasks.md execution order — §0 (smali bump) → §0.5/§0.6/§0.7 (preconditions) → §3 (grammar-tests scaffold) → §4.D+§4.B (prerequisite closures) → remaining closures → §2 (matrix document) → §5 (populate) → §6 (integrity tests) → §7 (archive).
