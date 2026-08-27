# CLAUDE.md - rvsec-crysl

## Purpose
MOP/CrySL conformance component (`br.unb.cic:rvsec-crysl`, packaging `pom`). Answers mechanically
whether a JavaMOP specification set encodes what the CrySL rules it was hand-translated from
require, and publishes five metrics (M0–M4) over that comparison. It **measures** the
instrumentation contract; it edits no `.mop` file and changes nothing about what the monitors
accuse.

Adjudication of whether a divergence is translation infidelity or deliberate Android adaptation
happens in the corpus record (`rv-android/data/jca_android/divergence_record.csv`), never inside
this component.

Capability spec: `conformance` (invariants `INV-CONF-NN`), in the sibling `rv-android` checkout —
`openspec/changes/gh106-mop-crysl-conformance/specs/conformance/spec.md` until that change is synced
to `openspec/specs/conformance/spec.md`.

## Role in the RVSEC pipeline
Off-pipeline instrument. It reads the same `.mop` corpora that `rvsec-agent`/`rvsec-android` compile
into monitors, but nothing in the runtime path depends on it. It is the **structural half** of a
two-instrument design whose behavioural half is the gh104 differential trace harness in `rv-android`
— all five metrics read artifacts, none executes a trace.

## Module layout
```
rvsec-crysl (pom)
 ├── rvsec-crysl-core    canonical model, automata, metrics, emitters   — no parser dependency
 ├── rvsec-crysl-mop     lift/lower through javamop                     — depends on -core
 └── rvsec-crysl-crysl   lift through CrySLParser 4.0.6 + the CLI       — depends on -core, -mop
```
One JVM, one process, three Maven modules. JSON is an **output** of the canonical model, never an
interchange format between processes.

| Module | Key packages (verified paths, under `src/main/java/br/unb/cic/rvsec/crysl/`) |
|---|---|
| `rvsec-crysl-core` | `core/model` (`SpecModel`, `Event`, `Signature`, `Constraint`, `PredicateRef`, `Unknown`, `Version`, `SourceStamp`), `core/automata` (`Determinizer`, `Minimizer`, `InverseMorphism`, `ProductSearch`, `Witnesses`), `core/metric` (`M0Vitality`…`M4Predicates`, `ConformanceReport`, `CountingRule`), `core/compare` (`Pipeline`, `AlphabetMap`, `CanonicalAlphabet`, `Normalizations`), `core/emit` (`JsonEmitter`, `CsvEmitter`, `MarkdownEmitter`, `CsvSchema`, `StampedTable`), `core/calibration` (`CalibrationGate`, `CalibrationTargets`, `MonitorIndexCensus`), plus `ApiIndex` (reads `android.jar` with ASM). |
| `rvsec-crysl-mop` | `mop` — `MopLifter`/`MopLift`, `MopLowerer`, `RoundTripGate`, `FormulaParser`, `PointcutExpander`, `PredicateIdioms`, `PredicateSite`, `HandlerBlock`. |
| `rvsec-crysl-crysl` | `crysl` — `CryslLifter`, `StateMachineAdapter`, `CryslProvenance`; `crysl/cli` — `ConformanceCli` (`main`), `CompareRun`/`LowerRun`/`CalibrateRun`, `ExitCode`. |

## CLI
`br.unb.cic.rvsec.crysl.crysl.cli.ConformanceCli`, program name `rvsec-conformance`, JCommander
(same shape as `rvsec-mop-extractor`). `main` is a two-line wrapper over `run(String[], PrintStream,
PrintStream)`, which returns an `ExitCode` and never calls `System.exit` — that separation is what
makes the exit-code contract testable.

| Subcommand | What it does | Main options |
|---|---|---|
| `compare` | M0–M4 of one `.mop` corpus against the upstream CrySL rules; emits JSON, CSV and Markdown | `--mop-dir/-m`, `--corpus/-c`, `--commit`, `--rules-dir/-r`, `--oracle-commit`, `--alphabet/-a`, `--android-jar/-j`, `--out/-o` |
| `lower` | Lowers each lifted model back to `.mop` text and runs the round-trip gate | `--mop-dir/-m`, `--corpus/-c`, `--commit`, `--out/-o` |
| `calibrate` | Measures the eight calibration quantities from the corpora and checks each against the independent route that produced its target | `--mop-root/-m`, `--rules-dir/-r`, `--commit/-c`, `--oracle-commit/-o`, `--monitor` |

Exit codes (`ExitCode`): `0 OK`, `1 USAGE`, `2 CORPUS_READ_ERROR`, `3 MISSING_VERSION`,
`4 CALIBRATION_MISMATCH`. The rule, not the numbers, is the point: **non-zero means the component
could not measure**. A report full of `Unknown` items and files that failed to lift is a *successful*
run with findings — collapsing the two would make the known upstream residuals
(`OAEPParameterSpec.crysl`, `SSLEngine.crysl`) turn every run red.

## Corpora
Read-only in every case (INV-CONF-12); nothing writes to a path it read.
- `.mop` corpora: the sibling `rvsec-mop` module **in the working tree**, not copies in test
  resources — `jca` (23), `jca_android` (24), `jca_android_bug_predicate` (23), `generic` (118),
  `generic_new` (27). A test that passes against a frozen copy while the live set has moved is worse
  than no test.
- CrySL oracle: `rvsec-cognicrypt/CrySL-Rules` — a **separate repository**, 49 `.crysl` files, read
  with no lexical normalization. Override the walk-up search with `RVSEC_CRYSL_RULES`.
- `android.jar`: `$ANDROID_HOME/platforms/android-30/android.jar`, overridable with
  `RVSEC_ANDROID_JAR`. API level 30 is what the `ApiIndex` assertions are anchored to.
- Committed CSV schemas: `rv-android/data/jca_android` (property `committed.schemas.dir` in
  `rvsec-crysl-core/pom.xml`). `CommittedSchemaDriftTest` fails — rather than skips — when that
  directory is absent.

**Editing a `.mop` in one of the five corpora is editing this component's inputs.** Reading the live
set is what makes the census meaningful and it is also what makes it fragile: `MopLiftCorpusTest`
pins the aggregate as a literal (currently 907 events, 383 parameters, 215 files), so a specification
repair that adds or removes an event or a parameter turns the CI red in `rvsec-crysl-mop` and nowhere
else — the reactor build above it passes with `-DskipTests` and says nothing. Whoever moves the
corpus re-runs the component and re-pins the census in the same change. That is the intended
workflow, not a failure of the test: the literal is the tripwire that tells a deliberate repair from
an accidental duplication. It happened once unnoticed — after gh106 pinned `905`/`381`, gh105 wired
one event into `KeyStoreSpec.mop` and one into `SSLContextSpec.mop` and gave `CipherInputStreamSpec`
and `CipherOutputStreamSpec` a parameter each, and the CI stayed red for three runs. The numbers live
in `MopLiftCorpusTest` (its `@DisplayName` and two assertions), `MopLift`'s javadoc and the gh106
conformance spec; all of them move together.

**Re-measure both counts, never just the one CI names.** The event assertion runs before the
parameter assertion in the same test, so a moved event count hides a moved parameter count: the three
red runs above reported only `905 -> 907` while `381 -> 383` was equally false and invisible. Run the
component and read the census off the run, rather than patching the number in the failure message.

## Build properties (parent `pom.xml`)
- **`guava.version` = `33.5.0-jre`** — overrides the reactor's 19.0. The root pins 19.0 for Soot;
  this component uses no Soot, and `CrySLParser 4.0.6` calls `ImmutableMap.Builder#buildOrThrow`,
  absent in 19.0: with the inherited pin the code compiles clean and dies at runtime with
  `NoSuchMethodError`. The root `dependencyManagement` is property-driven, so redefining the property
  here moves the managed version for the whole subtree. INV-CONF-16.
- **`scala.version` is deliberately NOT overridden.** It looks like the same fix and is not: raising
  it to 2.13.x breaks `ptltl` (reached transitively via `javamop` → `rv-monitor`) with
  `NoClassDefFoundError: scala/Serializable`, and `ptltl` may not be excluded. The reactor's 2.11.12
  is inherited unchanged. INV-CONF-16.
- `crysl.version` = 4.0.6, `gson.version` = 2.13.1, `junit-jupiter.version` = 5.12.2,
  `archunit.version` = 1.2.1, `asm.version` = 9.8 (declared in `-core`, pinned to what CrySLParser
  already resolves so the bytecode reader does not move when the parser does).
- Surefire is pinned to the **`surefire-junit-platform`** provider and its `<includes>` add
  `**/*IT.java`. The reactor manages JUnit 4 and the `surefire-junit4` provider; a JUnit 5 suite
  inheriting that setup reports "Tests run: 0" — a green with nothing behind it. Failsafe is not
  bound in this subtree, so an `*IT` class would otherwise compile and run nowhere.
- `maven-dependency-plugin:build-classpath` writes `target/resolved-classpath.txt` at
  `generate-test-resources`; the dependency-discipline tests assert over the **resolved artifacts**,
  not over pom text, so a version a transitive dependency moved is caught.
- Only `src/test/resources-filtered` is interpolated (`guava.version`, `scala.version`,
  `main.basedir`, `project.version`, `committed.schemas.dir`); `src/test/resources` has filtering
  off so a future binary fixture is not corrupted.

## test-jar and CI tags
`rvsec-crysl-core` publishes a **`test-jar`** (`maven-jar-plugin`, goal `test-jar`) whose only job is
to carry `br.unb.cic.rvsec.crysl.core.CiTags`. `CiTags.ORACLE_DEPENDENT` (`"oracle-dependent"`) is
the single definition of the JUnit tag name that the CI step excludes; `-mop` and `-crysl` consume
the test-jar in `test` scope, and `ReactorBuildIT` asserts the workflow text against the constant.
Written as three literals, a drifted name would exclude nothing and the excluded half would quietly
start running in CI and fail on a missing corpus. No test of `-core` is meant to be re-run elsewhere
— only the tag names travel this way.

CI (`rvsec/.github/workflows/ci.yml`, step "MOP/CrySL conformance component tests (gh106)"):
```bash
mvn -ntp -B -f rvsec/rvsec-crysl/pom.xml -DskipTests=false -DexcludedGroups=oracle-dependent test
```
That excludes 65 of 326 tests (64 in `-crysl`, 1 in `-mop`). The one outside `-crysl` is deliberate:
`RoundTripGateTest.test_the_fifth_check_resolves_pointcuts` resolves pointcuts against `android.jar`.

## Build
```bash
# what CI runs: everything that needs no input from outside this checkout
mvn -f rvsec/rvsec-crysl/pom.xml -DexcludedGroups=oracle-dependent test

# full local run including the oracle-dependent half — needs rvsec-cognicrypt beside rvsec
# (or RVSEC_CRYSL_RULES) and ANDROID_HOME with platforms/android-30
mvn -f rvsec/rvsec-crysl/pom.xml test

# as part of the reactor (JDK 21)
mvn clean install -DskipMopAgent -DskipTests
```

## Architectural rules enforced by tests
- `ModelShapeArchTest` (`-core`): no class of `rvsec-crysl-core` may depend on `javamop..` or
  `crysl..`. The model module knows neither parser. ASM is exempt — it parses bytecode, not a
  specification language.
- `DependencyDisciplineTest` (`-mop` and `-crysl`): asserts the effective `guava.version` /
  `scala.version` and, in `-mop`, that Guava is **absent** from that module's resolved classpath.
- `NoSharedReaderArchTest` (`-crysl`): the two lifts share no reader.
- `ReactorBuildIT` (`-crysl`): asserts module registration in the root and `rvsec/` poms, that
  `main.basedir` resolved (an unresolved property leaves the literal `${main.basedir}` in the
  filtered file), and the CI workflow's tag exclusion.

## Gotchas
- **`-crysl` depends on `-mop`, not the other way round.** The CLI needs all three modules; the
  direction was chosen because `javamop` pulls no Guava (so adding it to `-crysl` changes nothing
  about the classpath the single-JVM probe measured), whereas adding `CrySLParser` to `-mop` would
  put Guava on the module whose `DependencyDisciplineTest` asserts Guava is absent. Rationale is in
  `crysl/cli/package-info.java`.
- **There is deliberately no `crysl.lower`.** The absent symmetry is a decision, not an oversight: a
  `.crysl` pretty-printer has no consumer (the comparison runs over the shared model, never over rule
  syntax), while `mop.lower` has one — the round-trip gate — and JavaMOP ships `DumpVisitor`.
  Recorded in `mop/package-info.java`.
- **`MetaCrySL/generated/api30` is not an oracle.** Under counting rule R1 it deletes 25 `CONSTRAINTS`
  clauses across 12 of the 22 paired rules relative to upstream. The single oracle is
  `rvsec-cognicrypt/CrySL-Rules`.
- **No subcommand measures an empty corpus.** A directory holding no `*.mop` file is a
  `CorpusReadError`, because a report of zero rows that exits `0` is the same false green the
  component exists to remove.
- `CrySLParser` declares `slf4j-simple` in compile scope; `-crysl` excludes it so the reactor does not
  end up with two logging bindings on one classpath.
- Tests that need an external input use JUnit `Assumptions` that name the missing path, so a local
  run without the corpus says which path was missing instead of passing quietly.
