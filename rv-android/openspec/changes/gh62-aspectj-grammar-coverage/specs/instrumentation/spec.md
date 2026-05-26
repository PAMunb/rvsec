# Instrumentation — Delta Spec for gh62-aspectj-grammar-coverage

## ADDED Requirements

### Requirement: AspectJ Grammar Coverage Matrix as Contract

The dexlib2 instrumenter (`rvsec-android/rvsec-instrumentation-dexlib2/`) SHALL document the AspectJ pointcut surface it supports as a **grammar coverage matrix** anchored to the AspectJ Programming Guide §"Pointcuts" grammar and the AspectJ 5 quick reference. The matrix lives at `docs/aspectj_grammar_coverage.md` in the rv-android repository and is the authoritative contract for what dexlib2 weaves correctly today.

For every production listed under the **closed enumeration** below, the matrix SHALL contain exactly one row with the following columns:

- **AspectJ syntax** — the normative form (e.g. `call(MethodPattern)`, `args(name)`, `T+`, `after() throwing(Id):`).
- **Demand** — integer counts per `.mop` corpus shipped by the project (`aspect/Coverage.aj`, `jca/`, `generic/`, `generic_new/`). Counts SHALL be produced by `DemandCounter` (a deterministic Java helper in the `grammar-tests` Maven module), invoked directly by `MatrixIntegrityTest.testDemandCountsReproducible`. The matrix MAY quote the per-designator `java.util.regex.Pattern` inline so reviewers can read it without opening Java code, but the canonical source of truth for the counts is the helper.
- **Parser** — one of `IMPL` / `STUB` / `MISSING`, with a `file:line` anchor in `PointcutExpressionParser.java` or the corresponding parser source.
- **Matcher** — one of `IMPL` / `ALWAYS-MATCH` / `MALFORMED-DESC` / `MISSING`, with a `file:line` anchor in `PointcutMatcher.java` or sibling matchers.
- **Emitter** — one of `IMPL` / `NO-OP` / `N/A`, with a `file:line` anchor in `DexWeaver.java`, `WrapperEmitter.java`, or the relevant emitter.
- **Verdict** — exactly one value from `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`.
- **Evidence** — for `COVERED`, the FQN of an enabled passing test in `grammar-tests/`; for `SILENT-GAP`, the FQN of a `@Disabled` test in `grammar-tests/` whose assertion describes the correct AspectJ behaviour; for `EXPLICIT-NO-OP`, BOTH the FQN of a passing test asserting `UnsupportedOperationException` (or equivalent documented assertion) AND the `file:line` of the no-op declaration; for `NOT-NEEDED`, the `DemandCounter` zero result.

#### Verdict composition rule (worst-of-pipeline)

A row's `Verdict` SHALL be derived from its `Parser` / `Matcher` / `Emitter` cells by the **worst-of-pipeline** rule: the row is `COVERED` only if every cell in scope for that row is `IMPL`; otherwise the verdict downgrades to the first defective stage encountered in left-to-right order (Parser → Matcher → Emitter). Specifically:

- Any cell of `MISSING`, `STUB`, `ALWAYS-MATCH`, `MALFORMED-DESC`, or `NO-OP` downgrades the row to `SILENT-GAP` — UNLESS the defective cell is documented (a) as `NO-OP` paired with an explicit `UnsupportedOperationException` assertion and a `file:line` anchor, in which case the verdict is `EXPLICIT-NO-OP`; or (b) as `MISSING` in every cell paired with `DemandCounter` zero across all four corpora AND no behavioural-parity dependency, in which case the verdict is `NOT-NEEDED`.
- The row `if(...)` is the canonical worked example: Parser `IMPL`, Matcher `ALWAYS-MATCH`, Emitter `IMPL` (`IfGuardEmitter` wired) → worst stage = Matcher → verdict `SILENT-GAP`. The presence of a working `IfGuardEmitter` does NOT upgrade the row, because the matcher decides whether the emitter is ever invoked at a relevant join point.
- A `NOT-NEEDED` verdict is the only verdict that may be assigned when the cells alone would suggest `SILENT-GAP`. The matrix MUST state the demand evidence in the `Evidence` column.

`MatrixIntegrityTest.testVerdictMatchesWorstOfPipeline` SHALL enforce this rule by parsing each row's cells and asserting the declared `Verdict` equals the rule's output (with the `NOT-NEEDED` and `EXPLICIT-NO-OP` exception paths checked explicitly).

#### Closed enumeration of matrix rows

The matrix SHALL contain **exactly** the following rows (not "at minimum"; new AspectJ versions or new corpora add new rows via amendment, not implicit support). `AspectJDesignators.DESIGNATORS` in `grammar-tests` is the single source of truth and `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` enforces equality with the matrix.

**Classical pointcut designators**: `call`, `execution`, `target` *(binding sub-row)*, `target` *(type-matching sub-row)*, `this` *(binding)*, `this` *(type-matching)*, `args` *(binding)*, `args` *(type-matching)*, `args` *(mixed, e.g. `args(*, name, ..)`)*, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references. (Note: `within`/`!within` are NOT in this list — they live under "Within-family per-stage delegation rows" below, because the dexlib2 pipeline diverges per polarity.)

**AspectJ 5 annotation pointcut designators**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.

**Advice forms** (each one row — the dexlib2 weaver/emitter pipeline diverges per form): `before`, `after`, `after returning`, `after throwing`, `around`. Note: `returning(Id)` and `throwing(Id)` are advice modifiers (`after() returning(name): ...`), NOT pointcut designators; they appear only inside the advice-form rows.

**Type-pattern modifiers**: `T+` *(subtype, in `call()` param position)*, `T+` *(in `call()` owner position)*, `T+` *(in `call()` return position)*, `T+` *(inside `!within(...)`)*, `*` wildcard, `..` *(standalone varargs)*, `..` *(trailing-mixed, e.g. `(T, ..)`)*, dot-glob (`..*`), single-level glob (`.*`), arrays (`T[]`, `T[][]`), inner-class qualifier (`Outer.Inner` vs `Outer$Inner`).

**SignaturePattern modifiers**: positive visibility (`public`/`private`/`protected`), negated visibility (`!public`), `static`, `final`, `throws ExceptionPattern`.

**Within-family per-stage delegation rows**: `within(...)` positive (matcher always-match, weaver-side filter required to satisfy AspectJ semantics), `!within(...)` (matcher implements via `NotWithinPC`).

**Composition operators**: `&&`, `||`, `!`, parentheses.

**Advice-body reflective API** (behavioural-parity rows — each row reflects a runtime contract the advice body depends on; if dexlib2 weaves the advice but does not populate these, the monitor silently emits empty events): `thisJoinPoint` *(binding)*, `thisJoinPointStaticPart` *(binding)*, `thisEnclosingJoinPointStaticPart` *(binding)*, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` *(includes `MethodSignature` / `ConstructorSignature` / `FieldSignature` subtype accessors)*, `JoinPoint.getTarget()` *(or `.getThis()` — grouped, same emitter responsibility)*, `JoinPoint.getKind()` *(or `.getSourceLocation()` — grouped, metadata)*.

**Around-advice mechanics**: `proceed(...)` *(keyword inside around body — one row, consistent with `around` being EXPLICIT-NO-OP at the emitter)*.

**Aspect declaration mechanics**: `aspect Foo { ... }` *(top-level declaration syntax — the parser must distinguish `aspect` from `class`)*, `pointcut p(): ...` *(named-pointcut declaration — distinct from the named-pointcut *reference* row under Classical above; declaration binds a name, reference uses it)*, `abstract aspect` + concrete subaspect *(the JavaMOP `BaseAspect` idiom relies on this — abstract aspect declares the pointcut family, concrete subaspect picks the implementation)*, aspect inheritance `aspect Bar extends Foo`, `declare precedence: A, B;` *(advice ordering across aspects)*, privileged aspect *(access to private members of woven types)*.

**Runtime linkage**: `org.aspectj.lang.JoinPoint` class *(plus `JoinPoint.StaticPart` and `Signature` subtypes)* SHALL be available in the instrumented bytecode classpath — without this row, every advice-body reflective API row is meaningless. (One row covers the linkage; per-subtype availability is implicit.)

The matrix is the contract that downstream changes consume. Any new closure (e.g. `gh-XX`-trailing-varargs) MUST update the matrix row(s) it touches as part of its `tasks.md`, and MUST NOT introduce a parser/matcher/emitter path that does not correspond to an existing row.

#### Scenario: every enumerated designator has a matrix row

- **WHEN** a reviewer reads `docs/aspectj_grammar_coverage.md`
- **THEN** the table SHALL contain exactly one row for each entry in the closed enumeration above (mirrored by `AspectJDesignators.DESIGNATORS`)
- **AND** every row SHALL have non-empty values in every column

#### Scenario: every COVERED row has an enabled passing test

- **WHEN** a reviewer audits a row with `Verdict = COVERED`
- **THEN** the `Evidence` column SHALL cite a test method by FQN in the `grammar-tests/` Maven module
- **AND** running `mvn -pl grammar-tests test -Dtest=<that-fqn>` SHALL produce a passing result on the current `HEAD` of `origin/modules`
- **AND** the cited test method SHALL NOT carry `@Disabled` (neither on the method nor inherited from its class)

#### Scenario: every SILENT-GAP row has a @Disabled test that describes the gap

- **WHEN** a reviewer audits a row with `Verdict = SILENT-GAP`
- **THEN** the `Evidence` column SHALL cite a test method in `grammar-tests/` marked `@Disabled("gh62 SILENT-GAP: <one-line explanation>")`
- **AND** the disabled test body SHALL contain an assertion whose failure message names the gap by AspectJ syntax and dexlib2 component (parser / matcher / emitter)
- **AND** a corresponding entry SHALL exist in the scope ledger (`openspec/changes/gh62-aspectj-grammar-coverage/ledger.md`) for SILENT-GAP rows present at gh62 archive time. SILENT-GAP rows introduced in later changes are scheduled by their own OpenSpec change, not by amending the archived ledger

#### Scenario: every EXPLICIT-NO-OP row pins both the assertion and the no-op location

- **WHEN** a reviewer audits a row with `Verdict = EXPLICIT-NO-OP`
- **THEN** the `Evidence` column SHALL cite BOTH the FQN of a passing test asserting `UnsupportedOperationException` (or an equivalent documented assertion — e.g. `assertThrows(IllegalStateException.class, ...)`) AND the `file:line` of the no-op declaration in production code
- **AND** silent removal of the no-op (replacing the `throw` with `// TODO`) SHALL break the build via the cited test

#### Scenario: bidirectional matrix↔tests consistency

- **WHEN** `MatrixIntegrityTest` runs in CI
- **THEN** for every enabled (non-`@Disabled`) test method in `grammar-tests/`, there SHALL be exactly one matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP}` whose `Evidence` column resolves to that method (EXPLICIT-NO-OP rows cite an enabled passing test that asserts `UnsupportedOperationException` or equivalent — they are NOT `@Disabled`)
- **AND** for every `@Disabled` test method, there SHALL be exactly one matrix row with `Verdict = SILENT-GAP` whose `Evidence` column resolves to that method
- **AND** the count of skipped tests in the test report SHALL equal the count of `SILENT-GAP` rows in the matrix
- **AND** a `@Disabled` test that begins to pass silently (gap closed accidentally without matrix update) SHALL break the build

#### Scenario: demand counts reproducible by the Java helper

- **WHEN** a reviewer runs `DemandCounter.countAll()` against `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/`
- **THEN** the resulting counts SHALL match every `Demand` column in the matrix to the integer
- **AND** the helper SHALL be portable (no `bash`, no `LC_ALL`, no shell quoting) — invoked directly from `MatrixIntegrityTest.testDemandCountsReproducible`

### Requirement: Grammar Tests Maven Submodule

The sibling rvsec repository SHALL contain a Maven submodule `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` that materialises the matrix as executable tests. The module is test-only: its `pom.xml` declares no `main/java/` source, no shaded jar, and is excluded from the `instr-cli` shade plugin.

For every row in `docs/aspectj_grammar_coverage.md`, the module SHALL contain exactly one test method in `src/test/java/`. The mapping from matrix row to test method SHALL be one-to-one and bidirectionally discoverable: the matrix row cites the test FQN; the test method's Javadoc cites the matrix row by its AspectJ syntax. Tests SHALL exercise the full `pointcut-engine` → `advice-emitter` → `dex-mutator` pipeline against a synthetic fixture class (or, when realistic, against a snippet from one of the JCA `.mop` files).

#### Scenario: green bar on COVERED rows

- **WHEN** a developer runs `mvn -pl grammar-tests test` on a clean checkout of `origin/modules`
- **THEN** the test runner SHALL report zero failures
- **AND** every test method whose Javadoc cites a `COVERED` matrix row SHALL be `Passed`
- **AND** every test method whose Javadoc cites a `SILENT-GAP` matrix row SHALL be `Skipped` (via `@Disabled`)
- **AND** the test report SHALL list every skipped test by name so the gap inventory is visible in the test output

#### Scenario: closure of a SILENT-GAP flips the verdict and removes @Disabled atomically

- **WHEN** a sub-change implements a closure for a gap and lands on `origin/modules`
- **THEN** the same commit SHALL remove the `@Disabled` annotation from the corresponding `grammar-tests/` method AND update the matrix row in `docs/aspectj_grammar_coverage.md` to change `Verdict` from `SILENT-GAP` to `COVERED` and replace the `Evidence` entry with the now-passing test FQN
- **AND** `MatrixIntegrityTest` running in CI SHALL fail the build if either side moves alone — a closure commit that removes `@Disabled` without flipping the matrix row produces an orphan enabled test, caught by `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`; a closure commit that flips the matrix row without removing `@Disabled` produces an orphan SILENT-GAP without a `@Disabled` test, caught by `testSilentGapRowsHaveDisabledTestAndLedgerEntry`

### Requirement: Scope Ledger for Future Closures

The change directory `openspec/changes/gh62-aspectj-grammar-coverage/` SHALL contain a `ledger.md` document that classifies every `SILENT-GAP` matrix row into exactly one of three buckets. The ledger is a **snapshot** of bucket assignments at archive time — it is not maintained as a live document after the change is archived. The live source of truth for outstanding work is `docs/aspectj_grammar_coverage.md` itself: any row with `Verdict = SILENT-GAP` is by definition open work. Future closures are scheduled by opening one OpenSpec change per closure (with its own GitHub issue), not by maintaining a parallel issue list.

- **Fix-now** — closures recommended for scheduling against the current milestone, with rationale (active demand or otherwise high-value). Each entry names: AspectJ syntax / matrix row(s) it flips, demand summary, planned sub-change identifier (`gh-XX-<kebab>`), `Owner: @user`, `Target milestone: vX.Y`.
- **Follow-up** — real work but no current demand to schedule. Each entry names matrix rows + a one-sentence rationale for deferral + `Owner` + `Target milestone: TBD`.
- **Deferred-by-design** — closures that the project explicitly will NOT implement, with production code raising `UnsupportedOperationException` (or equivalent) AND a passing test asserting the throw. `Verdict = EXPLICIT-NO-OP`. Evidence cites both the test FQN AND the `file:line` of the no-op (per INV-INS-89). Example: `around` advice + `proceed(...)`. No `Owner` is needed for EXPLICIT-NO-OP sub-rows (the no-op is structural; no future work is planned).

The ledger SHALL NOT contain implementation detail for the planned closures — it is a schedule, not a design.

Rows with `Verdict = NOT-NEEDED` (path α: zero demand + no implementation; path β: production absorbed by an upstream toolchain stage before reaching the dexlib2 pipeline) do NOT appear in the ledger — they are not open work by construction. Round-5 review reclassified four rows from SILENT-GAP-permanent to NOT-NEEDED path β: `handler(...)` (no DEX-level analogue; absorbed by source-level decisions before the matcher); `declare precedence` (runtime monitor-dispatch property, not a weaver concern); `aspect Foo { ... }` (the dexlib2 pipeline reads JSON `AspectDescriptor`, not `.aj` source); `pointcut p(): ...` named declaration (same path β — `.aj` source consumed upstream by JavaMOP). These rows remain in the matrix with `Verdict = NOT-NEEDED` and carry enabled passing tests asserting equivalent-descriptor production regardless of upstream syntax; they do NOT have ledger entries.

#### Scenario: ledger covers every SILENT-GAP row

- **WHEN** a reviewer audits the matrix and the ledger together
- **THEN** every matrix row with `Verdict = SILENT-GAP` SHALL appear in exactly one ledger bucket (`Fix-now`, `Follow-up`, or `Deferred-by-design`)
- **AND** no ledger entry SHALL reference a matrix row that does not exist
- **AND** no two ledger entries SHALL claim the same matrix row
- **AND** every `Fix-now` and `Follow-up` entry SHALL declare `Owner` and `Target milestone` (which MAY be `TBD` for `Follow-up`)

#### Scenario: opening a sub-change consumes a Fix-now entry

- **WHEN** a developer opens a sub-change (e.g. `gh-XX`) implementing a closure
- **THEN** the sub-change's `proposal.md` SHALL cite gh62 issue #62 and the specific matrix rows it intends to flip
- **AND** upon archive of the sub-change, the matrix rows SHALL be flipped from `SILENT-GAP` to `COVERED` and the corresponding `@Disabled` annotations removed in the same commit (closure atomicity enforced by `MatrixIntegrityTest` in CI per the previous scenario)

### Requirement: JoinPoint Reflective API Behavioural Parity

The dexlib2 instrumenter SHALL provide AspectJ-equivalent runtime substrate for advice bodies that read the JoinPoint context. Specifically, when an advice body references `thisJoinPoint`, `thisJoinPointStaticPart`, `thisEnclosingJoinPointStaticPart`, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` (including the `MethodSignature` / `ConstructorSignature` / `FieldSignature` subtype accessors `.getName()` / `.getDeclaringType()` / `.getParameterTypes()` / `.getReturnType()`), `JoinPoint.getTarget()`, `JoinPoint.getThis()`, `JoinPoint.getKind()`, or `JoinPoint.getSourceLocation()`, the instrumented bytecode SHALL emit construction of a populated `JoinPoint` instance carrying real runtime values derived from the matched join point, NOT a string-typed placeholder.

`org.aspectj.lang.JoinPoint`, `org.aspectj.lang.Signature`, and the three signature subtypes SHALL be available on the instrumented APK's runtime classpath. The implementation ships local equivalents in the `br.unb.cic.rv.aspectjlang` package, embedded in the DEX output of `instr-cli`, to avoid a new transitive dependency on `aspectjrt.jar`.

#### Scenario: thisJoinPoint.getSignature().getName() returns the matched method's actual name

- **WHEN** an advice body containing `thisJoinPoint.getSignature().getName()` is woven around `call(* java.util.Hashtable.get(Object))`
- **AND** the instrumented APK invokes `Hashtable.get` at runtime
- **THEN** the advice body SHALL observe `getName()` returning `"get"`
- **AND** it SHALL NOT observe a raw pointcut expression string (`"call(* java.util.Hashtable.get(Object))"` or similar)

#### Scenario: JoinPoint subtype matches the matched join-point kind

- **WHEN** an advice body containing `thisJoinPoint.getSignature() instanceof MethodSignature` is woven around a `call(* ...)` pointcut
- **THEN** the runtime check SHALL evaluate to `true`
- **AND** when the same advice body is woven around `staticinitialization(...)`, the runtime check against `MethodSignature` SHALL evaluate to `false` and `instanceof Signature` (the supertype) SHALL evaluate to `true`

#### Scenario: JoinPoint.getArgs() returns the actual argument list

- **WHEN** an advice body containing `Object[] a = thisJoinPoint.getArgs()` is woven around `call(* Foo.bar(int, String))`
- **AND** the instrumented APK invokes `Foo.bar(42, "x")` at runtime
- **THEN** `a.length` SHALL equal `2`
- **AND** `a[0]` SHALL equal `Integer.valueOf(42)` (boxed)
- **AND** `a[1]` SHALL equal `"x"`

### Requirement: Pointcut Matcher Correctness

The dexlib2 pointcut matcher SHALL correctly evaluate the following classes of pointcut expression that current code mishandles as always-match:

1. **Standalone `target(name)` / `args(name)` binding**: when these designators appear at the top level of a pointcut expression (not in `&&`-composition with `call(...)`), the matcher SHALL still perform receiver / argument binding from the runtime join-point, instead of returning an empty match (`PointcutMatcher.java:106-108` current behaviour).
2. **Negation specialisation beyond `!within`**: `parseUnary` SHALL produce specialised negation matchers for `!handler(...)`, `!cflow(...)`, `!if(...)` in addition to `!within(...)`, evaluating the negated inner pointcut and inverting the verdict, instead of collapsing to `NamedRefPC` always-match.
3. **Named-pointcut reference resolution**: when an advice references a named pointcut defined in the same aspect (or an inherited aspect), the matcher SHALL resolve the reference against the aspect's pointcut table (`AspectDescriptor.namedPointcuts()`) and evaluate the resolved pointcut against the join point, instead of treating `NamedRefPC` as unconditional always-match.

#### Scenario: standalone target(name) binds the receiver register

- **WHEN** a pointcut `target(h)` is matched at the call site `obj.method()`
- **THEN** the resulting `Match` SHALL bind `h` to the register holding `obj`
- **AND** the bound register SHALL be accessible by the advice body via the generated parameter list

#### Scenario: !cflow excludes join points reached via the cflow

- **WHEN** a pointcut `!cflow(execution(* Setup.*(..)))` is evaluated at a join point reached from within `Setup.init()`
- **THEN** the matcher SHALL return no match (the negated inner is true, so its negation is false)
- **AND** when evaluated at a join point reached outside any `Setup.*` method, the matcher SHALL return a match

#### Scenario: named pointcut reference resolves against aspect pointcut table

- **WHEN** an advice `before(): myPointcut()` references a pointcut declared as `pointcut myPointcut(): call(* Foo.bar(..))` in the same aspect
- **AND** the runtime reaches `call Foo.bar()`
- **THEN** the matcher SHALL evaluate the resolved `call(* Foo.bar(..))` against the join point
- **AND** the resolved pointcut SHALL succeed, and the advice SHALL run
- **AND** the matcher SHALL NOT return an always-match result that would also fire `before(): myPointcut()` at unrelated join points

## Invariants

- **INV-INS-88**: For every row in the closed enumeration declared under `Requirement: AspectJ Grammar Coverage Matrix as Contract`, `docs/aspectj_grammar_coverage.md` MUST contain exactly one matrix row. New AspectJ versions or new corpora MUST result in a new row added by amendment, not implicit support.
- **INV-INS-89**: For every matrix row, the `Verdict` column MUST take exactly one value from the set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. The matrix MUST NOT contain rows with empty or composite verdicts. `NOT-NEEDED` is permitted via exactly two paths: (path α) `DemandCounter` zero across all four corpora AND no parser/matcher/emitter implementation (i.e. both Parser and Matcher are `MISSING`); OR (path β) the row reflects an AspectJ production that may exist in the corpora at *source* level but is consumed by an upstream toolchain stage (the JavaMOP compiler producing JSON descriptors, the DEX-level reachability filter, or any other documented absorber) before reaching the dexlib2 pipeline, so the dexlib2 parser/matcher/emitter never receives the token shape. Path β requires the matrix Evidence column to (a) cite the demand counts (which MAY be non-zero at source level), AND (b) name the upstream stage that absorbs the production, AND (c) cite an enabled passing test asserting that the equivalent descriptor input is produced (or absorbed equivalently) regardless of upstream source syntax. Path β was added in the round-3 cross-LLM review for `aspect Foo { ... }` and named `pointcut p(): ...` declarations and extended in round-5 to also cover `handler(...)` (no DEX-level analogue — absorbed by source-level decisions) and `declare precedence` (runtime monitor-dispatch property — absorbed by the runtime loop, not the weaver).

  `MatrixIntegrityTest.testVerdictsAreValid` SHALL enforce path α (demand sum == 0 AND parser/matcher anchors == `MISSING`); the test SHALL ALSO enforce path β by parsing the Evidence column with a regex that requires three matched groups: an `upstream-stage:` reference (e.g. `upstream-stage:JavaMOP-descriptor-reader`), a `demand-source:` reference quoting at least one corpus + count, AND a `test-fqn:` reference resolving to an enabled passing test method.
- **INV-INS-90**: For every matrix row with `Verdict = COVERED`, there MUST exist an enabled (non-`@Disabled`) passing test in `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` whose FQN appears in the row's `Evidence` column. `@Disabled` inherited from the test class also disqualifies the row from `COVERED`.
- **INV-INS-91**: For every matrix row with `Verdict = SILENT-GAP`, there MUST exist a `@Disabled`-annotated test in `grammar-tests/` whose disabled-reason message starts with `"gh62 SILENT-GAP: "`. The **ledger entry** requirement is scoped to SILENT-GAP rows present at gh62 archive time only — the ledger is a one-shot snapshot (see design D4) and is not maintained after archive. The ledger snapshot is content-addressed: a `ledger.snapshot.sha256` file containing the SHA-256 of `ledger.md` at archive time SHALL be committed to `grammar-tests/src/test/resources/`; `testSilentGapRowsHaveDisabledTestAndLedgerEntry` SHALL verify the live ledger's SHA against the snapshot and fail if they diverge (catches post-archive mutation of an artefact that is contractually frozen). SILENT-GAP rows introduced in subsequent changes MUST satisfy the `@Disabled`-test requirement above but are not retroactively added to the archived ledger; instead they are scheduled by opening the closure's own OpenSpec change.
- **INV-INS-92**: For every enabled (non-`@Disabled`) test method in `grammar-tests/`, there MUST be exactly one matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP}` resolving to it; for every `@Disabled` test method, there MUST be exactly one matrix row with `Verdict = SILENT-GAP` resolving to it. Orphan tests (no matrix row) and orphan rows (no test) MUST break the build. Closure atomicity is enforced by this invariant directly — a closure commit that flips one side without the other produces an orphan and fails CI. (Replaces the original aspirational "closure atomicity" invariant; an earlier draft proposed a cross-repo PR-check GitHub Action for the same purpose, rejected on simplicity grounds in design D6.)
- **INV-INS-93**: The matrix demand counts MUST be reproducible by `DemandCounter` invoked from `MatrixIntegrityTest.testDemandCountsReproducible`. Counts MUST be re-verified whenever a new `.mop` OR `.aj` file is added to any of the four corpora. `DemandCounter` SHALL scan BOTH `.mop` AND `.aj` files (the cross-LLM Round-5 review showed that scanning only `.mop` undercounts substantially because the `aspect/` corpus is entirely `.aj` and `generic_new/` contains `.aj` templates like `MultiSpec_1MonitorAspect.aj`). The per-designator regex SHALL distinguish *pointcut* uses from *Java statement* uses (the canonical false positive is `if(...)` in advice bodies appearing as Java `if` statements). The helper MUST be portable Java (no shell, no `ProcessBuilder`, no `LC_ALL`).
- **INV-INS-94**: For every matrix row in the **JoinPoint Reflective API family** (`thisJoinPoint`, `thisJoinPointStaticPart`, `thisEnclosingJoinPointStaticPart`, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` + subtypes, `JoinPoint.getTarget()`/`.getThis()`, `JoinPoint.getKind()`/`.getSourceLocation()`, AspectJ runtime linkage), the `Verdict` MUST be `COVERED` and the `Evidence` MUST cite an enabled test in `grammar-tests/JoinPointReflectiveApiGrammarTest` that exercises the runtime contract (the test creates a synthetic class, weaves an advice that reads the JoinPoint surface, runs the instrumented class on a JVM/Android runtime, and asserts the observed values match the AspectJ specification). The instrumented bytecode MUST link against `br.unb.cic.rv.aspectjlang.{JoinPoint,Signature,MethodSignature,ConstructorSignature,FieldSignature,SourceLocation}` (local equivalents shipped in the DEX, NOT `org.aspectj.lang.*`). `MatrixIntegrityTest.testReflectiveApiRowsAreCovered` SHALL fail the build if any reflective-API row regresses from `COVERED`.
- **INV-INS-95**: For every matrix row in the **Matcher Correctness family** (`target(name)` standalone, `args(name)` standalone, `!` negation beyond `!within`, named-pointcut reference resolution), the `Verdict` MUST be `COVERED` and the `Evidence` MUST cite an enabled test in `grammar-tests/` that exercises the correctness property (standalone binding produces a non-empty `Match`; negation matchers invert the inner verdict; named references resolve against the aspect's pointcut table). `MatrixIntegrityTest.testMatcherCorrectnessRowsAreCovered` SHALL fail the build if any matcher-correctness row regresses from `COVERED`.
