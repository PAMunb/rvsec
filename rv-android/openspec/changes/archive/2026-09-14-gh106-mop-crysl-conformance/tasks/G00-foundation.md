# G00 · Foundation — the four poms and the types only

**Depends on:** nothing. **Blocks:** G01, G02, G03, G04, G05 (and transitively everything else).
**Parallel with:** G13a.
**Size:** 4 poms + ~20 type files. That is **above** the 3–15 file guidance of WORKFLOW.md §5 by
file count and deliberately below it by content: every one of the twenty is a single record or a
single sealed interface, so a subagent holds twenty declarations, not twenty implementations. The
sizing rule guards against compaction inside a subagent, and declarations do not compact. If the
types turn out to carry logic — they should not — split into `G00a poms` and `G00b types`.

Deliberately small in effort: fixing the types is what releases six tracks the next day, and every
hour this group is late is six hours the team is not spending.

**Already validated (V10, Phase 0):** the four poms build inside the reactor with `main.basedir`
resolving, the `guava.version` override takes effect, and the `slf4j-simple` exclusion leaves only
`org.slf4j:slf4j-api:2.0.17`. This group re-establishes that, it does not re-discover it.

## Reference
- `design.md` D-01 (one JVM, three modules), D-11 (sealed `Unknown`), D-10 (witness status)
- `specs/conformance/spec.md` — INV-CONF-01, -03, -06, -07, -08, -16
- Shape template: `rvsec/rvsec-mop-extractor/pom.xml` — **by shape, not by code**

## Tasks

### The four poms

- [x] 0.1 Create `rvsec/rvsec-crysl/pom.xml` — packaging `pom`, parent `br.unb.cic:rvsec-parent`, artifactId `rvsec-crysl`, `<modules>` listing the three children. In `<properties>` set `<guava.version>33.5.0-jre</guava.version>` and **do not** declare `scala.version` (INV-CONF-16).
- [x] 0.2 Create `rvsec/rvsec-crysl/rvsec-crysl-core/pom.xml` — **no dependency on either parser**. It may carry a serialization library for the JSON emitter (the Phase 0 V10 pom declares Gson for exactly that reason), plus JUnit 5 and ArchUnit in test scope. The rule that matters is narrower than "zero dependencies": if this module ever imports `javamop` or `CrySLParser`, the layering is wrong, and that is what the ArchUnit rule checks.
- [x] 0.2-bis Pin JUnit 5 and ArchUnit **in the component's parent** `dependencyManagement`. The reactor root manages **JUnit 4** and `surefire-junit4`; inheriting that silently is how a JUnit 5 suite ends up collected by a JUnit 4 provider and reports zero tests run — a green with nothing behind it. `risk-register.md` RISK-010.
- [x] 0.3 Create `rvsec/rvsec-crysl/rvsec-crysl-mop/pom.xml` — depends on `-core` and on `br.unb.cic.javamop:javamop:0.9.3-SNAPSHOT`. It inherits `scala-library:2.11.12` transitively through `javamop → rv-monitor → ptltl`; that is expected and harmless (the module is Java 21).
- [x] 0.4 Create `rvsec/rvsec-crysl/rvsec-crysl-crysl/pom.xml` — depends on `-core` and on `de.darmstadt.tu.crossing.CrySL:CrySLParser:4.0.6`, **excluding `org.slf4j:slf4j-simple`** (it arrives in `compile` scope).
- [x] 0.5 Register `rvsec-crysl` in `rvsec/rvsec/pom.xml` `<modules>`, positioned after `rvsec-mop-extractor`.
- [x] 0.6 Build: `cd $W/rvsec && mvn clean install -DskipMopAgent -DskipTests` with JDK 21 in the prefix. All four modules build.
- [x] 0.7 Assert the dependency discipline instead of trusting the build to be silent: a test that reads the effective pom and asserts `guava.version == 33.5.0-jre`, `scala.version == 2.11.12`, `ptltl` present on the `-mop` classpath, `slf4j-simple` absent from the `-crysl` classpath, and `guava` **absent** from the `-mop` resolved classpath (`javamop` pulls none).

### The types, in `-core` only

- [x] 0.8 `model/{SourceStamp,Version}.java` — `record SourceStamp(String repository, String commit, Instant data)` and `record Version(String corpus, SourceStamp source)`. **One stamp per corpus, not one per run.** The input spans two git repositories (`rvsec` for the `.mop` sets, `rvsec-cognicrypt` for the upstream oracle) plus the SDK (`$ANDROID_HOME`); a single scalar `commit` would stamp an upstream-derived number with the commit of a repository that did not produce it — INV-CONF-02's own failure mode one level up. `risk-register.md` RISK-003.
- [x] 0.9 `model/{Signature,ObjectDecl,Guard,Provenance}.java` — the leaf value types. `Provenance` is `file:line`, **stamped at lift time, never parsed back out of text**.
- [x] 0.10 `model/Label.java` — `record Label(String name)`. A **distinct type**, not a bare `String`: INV-CONF-03's ArchUnit rule needs something to key on, and a rule stated over `Map<String, ?>` would be unenforceable because `String` keys are pervasive and legitimate. One line, and it is what makes the invariant machine-checkable. `risk-register.md` RISK-008.
- [x] 0.11 `model/Event.java` — `record Event(Label label, String pointcutText, Set<Signature> signatures, Optional<Guard> guard, int declIndex)`. `declIndex` is not optional: declaration order is dispatch order.
- [x] 0.11b `model/{Constraint,PredicateRef}.java` — both held in `List`, never `Set`: identical clauses at different sites have different provenance and a set collapses them.
- [x] 0.12 `model/SpecModel.java` — `events` is a `List<Event>` and `order` is an `Automaton` over `Signature`. **No field of any type in this module may be `Map<Label, Set<Signature>>`** (INV-CONF-03).
- [x] 0.13 `model/Unknown.java` — `sealed interface Unknown permits UnrecognizedConstraint, OverlappingDispatch, MultiSlicedOrder, UnresolvedSignature, UntranslatableConstraint`. Exactly five, closed by the type system so that adding a tag is a visible contract change (INV-CONF-06).
- [x] 0.14 The five records, each with its declared field schema. `OverlappingDispatch` takes `List<String> labels` and its canonical constructor **rejects an empty list** (INV-CONF-07) — a refusal that does not name the overlapping labels does not say how many letters the call emits.
- [x] 0.15 `model/{Witness,WitnessStatus,Normalization}.java` — `WitnessStatus` is `ABSTRACT | CONCRETE`; `Witness` carries the word, the status, the list of normalizations applied, and an `Optional<String> harness` that is present **iff** the status is `CONCRETE` (INV-CONF-08).
- [x] 0.16 `metric/{M0Result,M1Result,M2Result,M3Result,M4Result,MetricResult,ConformanceReport}.java` — the result types of the five metrics. Each carries its counting rule as data, not as a comment, because INV-CONF-02 needs to read it at emission time.

### Tests

- [x] 0.17 `SpecModelVersionTest` — a model constructed without a version cannot be built; the record's canonical constructor rejects `null`.
- [x] 0.18 `UnknownTaxonomyTest` — the sealed hierarchy has exactly five permitted subtypes (assert via reflection on `getPermittedSubclasses()`, so a sixth breaks the test rather than slipping in).
- [x] 0.19 `test_inv_conf_07_labels_required` — `new OverlappingDispatch(List.of(), sig, site)` throws.
- [x] 0.20 `ModelShapeArchTest` (ArchUnit) — INV-CONF-03: no field anywhere in the component has a type assignable to `Map<Label, ?>`; and no class in `-core` depends on `javamop.**` or `crysl.**`. Both are checkable precisely because `Label` is a distinct type and the parsers are distinct packages.
- [x] 0.21 `mvn -pl rvsec/rvsec-crysl -am test` green — **but that command runs zero tests**.
  `-pl` selects the aggregator alone and `-am` adds only its ancestors (`rvsec-parent`, `rvsec`),
  never its children, so the command reports `BUILD SUCCESS` over three pom modules and no
  surefire execution at all — the same silent green RISK-010 is about, one level up. The command
  that actually runs the component's suite is `mvn -f rvsec/rvsec-crysl/pom.xml test`, and that
  is what was run: 17 tests, 0 failures (9 in `-core`, 4 in `-mop`, 4 in `-crysl`).

## Closing

G00 closes when all 23 checkboxes — 0.1–0.21, including 0.2-bis and 0.11b — are `[x]`. **Do not close it early to unblock the parallel tracks**: the
whole point of the split is that the types are stable when the six tracks start, and a type that
changes on day two costs six merges.
