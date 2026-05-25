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

#### Closed enumeration of matrix rows

The matrix SHALL contain **exactly** the following rows (not "at minimum"; new AspectJ versions or new corpora add new rows via amendment, not implicit support). `AspectJDesignators.DESIGNATORS` in `grammar-tests` is the single source of truth and `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` enforces equality with the matrix.

**Classical pointcut designators**: `call`, `execution`, `target` *(binding sub-row)*, `target` *(type-matching sub-row)*, `this` *(binding)*, `this` *(type-matching)*, `args` *(binding)*, `args` *(type-matching)*, `args` *(mixed, e.g. `args(*, name, ..)`)*, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references. (Note: `within`/`!within` are NOT in this list — they live under "Within-family per-stage delegation rows" below, because the dexlib2 pipeline diverges per polarity.)

**AspectJ 5 annotation pointcut designators**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.

**Advice forms** (each one row — the dexlib2 weaver/emitter pipeline diverges per form): `before`, `after`, `after returning`, `after throwing`, `around`. Note: `returning(Id)` and `throwing(Id)` are advice modifiers (`after() returning(name): ...`), NOT pointcut designators; they appear only inside the advice-form rows.

**Type-pattern modifiers**: `T+` *(subtype, in `call()` param position)*, `T+` *(in `call()` owner position)*, `T+` *(in `call()` return position)*, `T+` *(inside `!within(...)`)*, `*` wildcard, `..` *(standalone varargs)*, `..` *(trailing-mixed, e.g. `(T, ..)`)*, dot-glob (`..*`), single-level glob (`.*`), arrays (`T[]`, `T[][]`), inner-class qualifier (`Outer.Inner` vs `Outer$Inner`).

**SignaturePattern modifiers**: positive visibility (`public`/`private`/`protected`), negated visibility (`!public`), `static`, `final`, `throws ExceptionPattern`.

**Within-family per-stage delegation rows**: `within(...)` positive (matcher always-match, weaver-side filter required to satisfy AspectJ semantics), `!within(...)` (matcher implements via `NotWithinPC`).

**Composition operators**: `&&`, `||`, `!`, parentheses.

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
- **AND** a corresponding entry SHALL exist in the scope ledger (`openspec/changes/gh62-aspectj-grammar-coverage/ledger.md`)

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
- **AND** a PR-check GitHub Action SHALL block any PR that modifies `rvsec-android/rvsec-instrumentation-dexlib2/{pointcut-engine,advice-emitter,dex-mutator,coverage-weaver}/src/main/` without modifying `docs/aspectj_grammar_coverage.md`

### Requirement: Scope Ledger for Future Closures

The change directory `openspec/changes/gh62-aspectj-grammar-coverage/` SHALL contain a `ledger.md` document that classifies every `SILENT-GAP` matrix row into exactly one of three buckets. Because the change directory is archived after merge, the ledger SHALL be treated as a snapshot of the bucket assignments at archive time; ongoing tracking moves to GitHub issues (one issue per Fix-now and Follow-up entry, labelled `gh62`) opened by task 7.4. The archived `ledger.md` remains discoverable via `git log --follow` and the issue tracker is the live source of truth for closure progress.

- **Fix-now** — closures recommended for scheduling against the current milestone, with rationale (active demand or otherwise high-value). Each entry names: AspectJ syntax / matrix row(s) it flips, demand summary, planned sub-change identifier (`gh-XX-<kebab>`), `Owner: @user`, `Target milestone: vX.Y`.
- **Follow-up** — real work but no current demand to schedule. Each entry names matrix rows + a one-sentence rationale for deferral + `Owner` + `Target milestone: TBD`.
- **Deferred-by-design** — closures that the project explicitly will NOT implement. Each entry names the matrix rows AND references the design decision that established the deferral (typically an ADR or the existing `EXPLICIT-NO-OP` evidence). No `Owner` needed.

The ledger SHALL NOT contain implementation detail for the planned closures — it is a schedule, not a design.

#### Scenario: ledger covers every SILENT-GAP row

- **WHEN** a reviewer audits the matrix and the ledger together
- **THEN** every matrix row with `Verdict = SILENT-GAP` SHALL appear in exactly one ledger bucket (`Fix-now`, `Follow-up`, or `Deferred-by-design`)
- **AND** no ledger entry SHALL reference a matrix row that does not exist
- **AND** no two ledger entries SHALL claim the same matrix row
- **AND** every `Fix-now` and `Follow-up` entry SHALL declare `Owner` and `Target milestone` (which MAY be `TBD` for `Follow-up`)

#### Scenario: opening a sub-change consumes a Fix-now entry

- **WHEN** a developer opens a sub-change (e.g. `gh-XX`) listed in the `Fix-now` bucket
- **THEN** the sub-change's `proposal.md` SHALL cite gh62 issue #62 and the specific matrix rows it intends to flip
- **AND** upon the sub-change's archive, the linked GitHub issue (opened by task 7.4) SHALL be closed with a reference to the sub-change's PR

## Invariants

- **INV-INS-88**: For every row in the closed enumeration declared under `Requirement: AspectJ Grammar Coverage Matrix as Contract`, `docs/aspectj_grammar_coverage.md` MUST contain exactly one matrix row. New AspectJ versions or new corpora MUST result in a new row added by amendment, not implicit support.
- **INV-INS-89**: For every matrix row, the `Verdict` column MUST take exactly one value from the set `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`. The matrix MUST NOT contain rows with empty or composite verdicts. `NOT-NEEDED` requires `DemandCounter` zero across all four corpora AND no parser/matcher/emitter implementation (i.e. both Parser and Matcher are `MISSING`).
- **INV-INS-90**: For every matrix row with `Verdict = COVERED`, there MUST exist an enabled (non-`@Disabled`) passing test in `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/` whose FQN appears in the row's `Evidence` column. `@Disabled` inherited from the test class also disqualifies the row from `COVERED`.
- **INV-INS-91**: For every matrix row with `Verdict = SILENT-GAP`, there MUST exist a `@Disabled`-annotated test in `grammar-tests/` whose disabled-reason message starts with `"gh62 SILENT-GAP: "`, AND the ledger MUST place this row in exactly one bucket.
- **INV-INS-92**: For every enabled (non-`@Disabled`) test method in `grammar-tests/`, there MUST be exactly one matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP}` resolving to it; for every `@Disabled` test method, there MUST be exactly one matrix row with `Verdict = SILENT-GAP` resolving to it. Orphan tests (no matrix row) and orphan rows (no test) MUST break the build. (Replaces the original aspirational "closure atomicity" invariant — atomicity is enforced operationally by the PR-check GitHub Action declared in the closure scenario above.)
- **INV-INS-93**: The matrix demand counts MUST be reproducible by `DemandCounter` invoked from `MatrixIntegrityTest.testDemandCountsReproducible`. Counts MUST be re-verified whenever a new `.mop` file is added to any of the four corpora. The helper MUST be portable Java (no shell, no `ProcessBuilder`, no `LC_ALL`).
