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

### Requirement: Demand-Driven Closures for High-Traffic Constructs

The dexlib2 instrumenter SHALL implement functional equivalents for the eight high-traffic AspectJ/JavaMOP constructs that are present in the four `.mop`/`.aj` corpora and whose dexlib2 path is currently silently broken. Each closure SHALL flip its matrix row from `SILENT-GAP` to `COVERED` with an enabled test in `grammar-tests/` asserting the post-fix behaviour against the corpus pattern that motivated it.

1. **`condition(...)` MOP-extension guard emit** — 74 sites across `jca/`+`generic_new/`. The JavaMOP semantics is "evaluate `<expr>` in the advice context; skip the monitor dispatch if false". The dexlib2 advice-emitter SHALL emit a boolean guard before the monitor invoke that short-circuits dispatch when `<expr>` evaluates to false. Errors during expression evaluation SHALL log at WARN level and SHALL NOT dispatch (conservative default).
2. **Positive `within(typePattern)` matcher** — 28 sites (24 in `aspect/Coverage.aj`, 2 in `jca/`, 2 in `generic_new/`). The matcher SHALL filter `classDef` FQN against the `typePattern` using the existing `matchesTypePattern` helper from `NotWithinPC:343-359`, returning no match when the class does not satisfy the pattern.
3. **`T+` in `call()` owner position** — extensive demand in `generic_new/`. The matcher SHALL extend the gh61 parameter-position subtype expansion to owner descriptors at `PointcutMatcher.java:153-157`, using `cpsAwareOwnerMatch` semantics (the same subtype check gh61 applied to params).
4. **`!target(T)` / `!args(T)` parser specialization** — 32 sites in `generic_new/` (28 `!target`, 4 `!args`). `PointcutExpressionParser.parseUnary()` SHALL recognize `!target(Type)` and `!args(Type)` and route them to inverting matchers, instead of collapsing into `NamedRefPC` always-match.
5. **Method-name glob `name*`** — ~16 sites in `generic_new/`. The matcher at `PointcutMatcher.java:161-167` SHALL recognize a trailing `*` in the expected method name and use `startsWith(prefix)` matching; exact-equals remains the default when no `*` appears.
6. **`__STATICSIG` JavaMOP macro support** — 3 sites in `generic_new/` (`Collection_HashCode.mop`, `Serializable_NoArgConstructor.mop`, `URLConnection_OverrideGetPermission.mop`). The advice-emitter SHALL recognize `__STATICSIG` in the advice body and replace it with an emit of a constant `Signature` (using either `java.lang.String` carrying the descriptor or a minimal local Signature class — implementation discretion) populated from weave-time class+method metadata. The downstream monitor consumes the result as a value, not as a typed reference, so the emit only needs to satisfy the source-level type binding.
7. **`staticinitialization(T+)` synthesis when `<clinit>` is absent** — 6 sites in `generic_new/`. When the matcher identifies a class matching `staticinitialization(T+)` but the class has no `<clinit>` method, the weaver SHALL synthesize a minimal `<clinit>` containing only the advice invocation, with the synthesized method flagged for auditability.
8. **`after() throwing(...)` end-to-end install** — 2 sites in `generic_new/` + the existing `AfterThrowingEmitter` plan that `DexWeaver.java:560-566` discards silently. The weaver SHALL implement the `TRY_CATCH_WRAP` case in `applyPlan`, installing a try-range over the matched invoke and an exception-handler emitting the advice invocation.

#### Scenario: condition(...) short-circuits the monitor invoke

- **WHEN** an advice body is woven for `call(* Cipher.getInstance(String)) && condition(thisJoinPoint != null)` (illustrative; real corpus uses simpler guards)
- **AND** the `condition(...)` payload evaluates to `false` at the runtime join point
- **THEN** the monitor invoke SHALL NOT be dispatched (the guard short-circuits)
- **AND** when the payload evaluates to `true`, the monitor invoke SHALL be dispatched as if the condition were absent

#### Scenario: positive within(typePattern) filters classDef FQN

- **WHEN** a pointcut `call(* Hashtable.get(..)) && within(com.example.app..*)` is evaluated at a `Hashtable.get` call inside `com.example.app.Foo`
- **THEN** the matcher SHALL return a match
- **AND** when the same pointcut is evaluated inside `com.other.lib.Bar`, the matcher SHALL return no match

#### Scenario: T+ in call() owner expands to subtypes

- **WHEN** a pointcut `call(* javax.crypto.Cipher+.doFinal(..))` is evaluated at a call to a method declared on `javax.crypto.spec.IvParameterSpec` (a Cipher subtype receiver — illustrative)
- **THEN** the matcher SHALL recognize the receiver type as a subtype of `javax.crypto.Cipher` and return a match
- **AND** the existing exact-equals match for receivers of the exact declared type SHALL continue to succeed

#### Scenario: !target(T) inverts the target match

- **WHEN** a pointcut `call(* Object.toString()) && !target(MyClass)` is evaluated at `myClassInstance.toString()`
- **THEN** the matcher SHALL return no match (the receiver IS a `MyClass`, so its negation is false)
- **AND** when evaluated at `anotherClassInstance.toString()`, the matcher SHALL return a match

#### Scenario: method-name glob matches by prefix

- **WHEN** a pointcut `call(* java.util.Collection+.add*(..))` is evaluated at calls to `add(E)`, `addAll(Collection)`, and `addLast(E)`
- **THEN** all three calls SHALL match (the `add*` prefix is satisfied)
- **AND** a call to `remove(E)` SHALL NOT match

#### Scenario: __STATICSIG resolves to a populated Signature constant

- **WHEN** an advice body containing `Signature initsig = __STATICSIG;` is woven for `staticinitialization(Hashtable+)` in the matched class `java.util.Hashtable`
- **THEN** the emitted bytecode SHALL bind `initsig` to a value whose `getDeclaringType()` resolves to `java.util.Hashtable` and whose `getName()` resolves to `<clinit>` (or the equivalent representation chosen by the emitter)
- **AND** the monitor consuming `initsig` SHALL receive a non-null value carrying the weave-time-known class metadata

#### Scenario: staticinitialization synthesis emits a minimal clinit

- **WHEN** a `staticinitialization(MyClass+)` pointcut matches a class `MyClass` that has no existing `<clinit>` method
- **THEN** the weaver SHALL synthesize a `<clinit>` containing only the advice invocation
- **AND** the synthesized method SHALL be flagged in the DEX output as `weaver-synthesized` for auditability (via comment or annotation discoverable by `dexdump`)

#### Scenario: after throwing installs try-range and exception handler

- **WHEN** an advice `after() throwing(Exception e): call(* Foo.bar(..))` is processed by the weaver
- **AND** the matched call site is `obj.bar()` at a known offset
- **THEN** the weaver SHALL install a try-range covering the invoke and an exception handler emitting the advice invocation with `e` bound to the caught exception register
- **AND** the resulting DEX SHALL pass ART verification (no new VerifyError) and the advice SHALL fire when the call throws

### Requirement: NamedRefPC Resolver via commonPointcut

The dexlib2 pointcut matcher SHALL resolve named-pointcut references at evaluation time using the existing `AspectDescriptor.getCommonPointcut()` field. The `PointcutMatcher.Context` SHALL be plumbed with access to the active `AspectDescriptor`; the `NamedRefPC` matcher SHALL look up the referenced name in `getCommonPointcut()` and evaluate the resolved expression against the join point. Unresolved references (the named pointcut is not in `commonPointcut`) SHALL log at WARN level and fall back to the existing always-match behaviour so that no closure regression hides behind silent always-true semantics.

#### Scenario: named pointcut reference resolves against commonPointcut

- **WHEN** an advice `before(): myPointcut()` references a pointcut `pointcut myPointcut(): call(* Foo.bar(..))` declared via `commonPointcut` in the active `AspectDescriptor`
- **AND** the runtime reaches `call Foo.bar()`
- **THEN** the matcher SHALL evaluate the resolved `call(* Foo.bar(..))` against the join point and produce a match
- **AND** at unrelated join points, the resolved pointcut SHALL produce no match (and the advice SHALL NOT fire)

#### Scenario: unresolved named pointcut reference logs and falls back

- **WHEN** an advice `before(): unknownPointcut()` references a name not present in `getCommonPointcut()`
- **THEN** the matcher SHALL log a WARN-level message naming the unresolved reference
- **AND** the matcher SHALL return the existing always-match result so that future ledger work can address the gap without a regression

## Invariants

- **INV-INS-88**: For every row in the closed enumeration declared under `Requirement: AspectJ Grammar Coverage Matrix as Contract`, `docs/aspectj_grammar_coverage.md` MUST contain exactly one matrix row. New AspectJ versions or new corpora MUST result in a new row added by amendment, not implicit support.
- **INV-INS-89**: For every matrix row, the `Verdict` column MUST take exactly one value from the set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. The matrix MUST NOT contain rows with empty or composite verdicts. `NOT-NEEDED` is permitted via exactly two paths: (path α) `DemandCounter` zero across all four corpora AND no parser/matcher/emitter implementation (i.e. both Parser and Matcher are `MISSING`); OR (path β) the row reflects an AspectJ production that may exist in the corpora at *source* level but is consumed by an upstream toolchain stage (the JavaMOP compiler producing JSON descriptors, the DEX-level reachability filter, or any other documented absorber) before reaching the dexlib2 pipeline, so the dexlib2 parser/matcher/emitter never receives the token shape. Path β requires the matrix Evidence column to (a) cite the demand counts (which MAY be non-zero at source level), AND (b) name the upstream stage that absorbs the production, AND (c) cite an enabled passing test asserting that the equivalent descriptor input is produced (or absorbed equivalently) regardless of upstream source syntax. Path β was added in the round-3 cross-LLM review for `aspect Foo { ... }` and named `pointcut p(): ...` declarations and extended in round-5 to also cover `handler(...)` (no DEX-level analogue — absorbed by source-level decisions) and `declare precedence` (runtime monitor-dispatch property — absorbed by the runtime loop, not the weaver).

  `MatrixIntegrityTest.testVerdictsAreValid` SHALL enforce path α (demand sum == 0 AND parser/matcher anchors == `MISSING`); the test SHALL ALSO enforce path β by parsing the Evidence column with a regex that requires three matched groups: an `upstream-stage:` reference (e.g. `upstream-stage:JavaMOP-descriptor-reader`), a `demand-source:` reference quoting at least one corpus + count, AND a `test-fqn:` reference resolving to an enabled passing test method.
- **INV-INS-90**: For every matrix row with `Verdict = COVERED`, there MUST exist an enabled (non-`@Disabled`) passing test in `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` whose FQN appears in the row's `Evidence` column. `@Disabled` inherited from the test class also disqualifies the row from `COVERED`.
- **INV-INS-91**: For every matrix row with `Verdict = SILENT-GAP`, there MUST exist a `@Disabled`-annotated test in `grammar-tests/` whose disabled-reason message starts with `"gh62 SILENT-GAP: "`. The **ledger entry** requirement is scoped to SILENT-GAP rows present at gh62 archive time only — the ledger is a one-shot snapshot (see design D4) and is not maintained after archive. The ledger snapshot is content-addressed: a `ledger.snapshot.sha256` file containing the SHA-256 of `ledger.md` at archive time SHALL be committed to `grammar-tests/src/test/resources/`; `testSilentGapRowsHaveDisabledTestAndLedgerEntry` SHALL verify the live ledger's SHA against the snapshot and fail if they diverge (catches post-archive mutation of an artefact that is contractually frozen). SILENT-GAP rows introduced in subsequent changes MUST satisfy the `@Disabled`-test requirement above but are not retroactively added to the archived ledger; instead they are scheduled by opening the closure's own OpenSpec change.
- **INV-INS-92**: For every enabled (non-`@Disabled`) test method in `grammar-tests/`, there MUST be exactly one matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP}` resolving to it; for every `@Disabled` test method, there MUST be exactly one matrix row with `Verdict = SILENT-GAP` resolving to it. Orphan tests (no matrix row) and orphan rows (no test) MUST break the build. Closure atomicity is enforced by this invariant directly — a closure commit that flips one side without the other produces an orphan and fails CI. (Replaces the original aspirational "closure atomicity" invariant; an earlier draft proposed a cross-repo PR-check GitHub Action for the same purpose, rejected on simplicity grounds in design D6.)
- **INV-INS-93**: The matrix demand counts MUST be reproducible by `DemandCounter` invoked from `MatrixIntegrityTest.testDemandCountsReproducible`. Counts MUST be re-verified whenever a new `.mop` OR `.aj` file is added to any of the four corpora. `DemandCounter` SHALL scan BOTH `.mop` AND `.aj` files (the cross-LLM Round-5 review showed that scanning only `.mop` undercounts substantially because the `aspect/` corpus is entirely `.aj` and `generic_new/` contains `.aj` templates like `MultiSpec_1MonitorAspect.aj`). The per-designator regex SHALL distinguish *pointcut* uses from *Java statement* uses (the canonical false positive is `if(...)` in advice bodies appearing as Java `if` statements). The helper MUST be portable Java (no shell, no `ProcessBuilder`, no `LC_ALL`).
- **INV-INS-94**: For every matrix row covered by the **eight demand-driven closures** (`condition(...)`, positive `within(typePattern)`, `T+` in `call()` owner, `!target(T)`/`!args(T)`, method-name glob `name*`, `__STATICSIG`, `staticinitialization` synthesis, `after() throwing(...)`) plus the **`NamedRefPC` resolver via `commonPointcut`**, the `Verdict` MUST be `COVERED` and the `Evidence` MUST cite an enabled test in `grammar-tests/` exercising the corpus pattern that motivated the closure (the test weaves the pointcut/advice combination against a synthetic fixture mirroring the corpus shape and asserts the post-fix behaviour). `MatrixIntegrityTest.testDemandDrivenClosuresAreCovered` SHALL fail the build if any of these rows regresses from `COVERED`.
- **INV-INS-95**: The eight demand-driven closures + `NamedRefPC` resolver SHIP as bisect-friendly atomic commits (one closure per commit, §4.G/W/O/N/X/S/Y/T/D in tasks). For every commit landing a closure, the matrix row flip (`SILENT-GAP` → `COVERED`) and the `@Disabled` removal MUST occur in the same commit; orphan tests and orphan rows are caught by INV-INS-92. `MatrixIntegrityTest.testClosureLocFootprintMatchesMatrixDelta` SHALL log (advisory; non-blocking) the LOC delta per closure commit and the number of matrix rows flipped, so reviewers can audit at archive time whether the realized scope matched the round-6 demand-driven budget.
