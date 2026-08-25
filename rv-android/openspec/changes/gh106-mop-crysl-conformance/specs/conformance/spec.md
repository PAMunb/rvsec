# conformance Specification

## Purpose

`conformance` is the capability that answers, mechanically, whether a JavaMOP specification set encodes what the CrySL rules it was translated from require. The comparison is **literal**: where the specification diverges from the rule, the capability accuses the divergence. Whether a given divergence is translation infidelity or deliberate Android adaptation is adjudicated in the corpus record (`data/jca_android/divergence_record.csv`, the gh104/gh105 lineage), never inside this capability (researcher decision, 2026-08-24).

RVSec monitors Android cryptographic API misuse at runtime. Two specification languages meet inside it. **CrySL** is the DSL of CogniCrypt/CROSSING: a `.crysl` rule declares, for one JCA type, its `OBJECTS`, its `EVENTS`, an `ORDER` (an extended regular expression over calls), its `CONSTRAINTS`, and the predicates it `REQUIRES`, `ENSURES` or `NEGATES`. **JavaMOP** is what RVSec actually instruments and executes: a `.mop` specification with AspectJ pointcuts, an `ere` or `fsm` formula, and `@match`/`@fail` handlers. The `.mop` files of the `jca_android` set were translated **by hand** from CrySL rules, and until this capability existed nothing checked that the translation says what the rule requires.

Three corpora enter the computation and must never be conflated. `R_java` is the upstream `CrySL-Rules` — **the single oracle** (49 files, 47 of which load without any lexical normalization; the two failures are `OAEPParameterSpec.crysl`, which uses the grammar's reserved word `alg` as an object name, and `SSLEngine.crysl`, an upstream defect referencing the undeclared event `cp1`). `S_java` is the frozen `jca` specification set (23 `.mop` files), which is the set the published measurements were taken over and therefore the set any historical comparison must be able to read. `S_android` is the current `jca_android` set (24 `.mop` files). The generated `MetaCrySL/generated/api30` corpus is **not an oracle**: measured under counting rule R1 it deletes 25 `CONSTRAINTS` clauses across 12 of the 22 paired rules relative to upstream, so a comparison against it would understate what the specifications must encode; its abandonment is recorded as a method note, not measured against. Running `S_android` against `R_java` is the design, not a conflation: every divergence is accused, and the adjudication of deliberate adaptation happens in the corpus record.

The capability computes **five** metrics. **M0 (vitality)** runs first and can refuse: it asks whether the specification indexes (does the generated monitor build a `MapOfMonitor`?), whether the accusation site is reachable at all, and whether each pointcut resolves against the platform. A refused specification does not reach the other four, because an order verdict over a monitor that does not run is empty — and this is not hypothetical: of the five specifications that do not index, one (`RandomStringPassword`) has an empty `@match` and no `@fail` and therefore cannot accuse anything under any trace — and a second specification, `SecretKeySpec`, cannot accuse either yet **does** index, so it is invisible to that census and is caught only by asking the reachability question directly — and one (`HMACParameterSpecSpec`) monitors a class that exists in no Android API level. **M1 (events)** compares sets of concrete signatures. **M2 (order)** compares the language accepted by the `.mop` automaton with the language of the rule's `ORDER`. **M3 (constraints)** classifies each `CONSTRAINTS` clause by the idiom that implements it, or records its absence. **M4 (predicates)** compares the `ENSURES`/`REQUIRES`/`NEGATES` graph by arity, polarity and argument position.

Three design commitments make the results trustworthy rather than merely available, and each was paid for by a measured failure during Phase 0.

First, **the event alphabet is not disjoint**. In the corpus a single observed call can match two pointcuts and emit two letters — measured on `IvChainJunction` `use`/`useRandomSpec`, where one `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` call matches both with no `condition` on either side. A model that stores `Map<Label, Set<Signature>>` has already lost that information, so `events` is an ordered list (declaration order is dispatch order) and `order` is a symbolic automaton over signatures; the object compared is the inverse morphism `h⁻¹(L)`, where `h` carries a signature to the concatenation, in declaration order, of every label whose pointcut matches it. Inverse morphism preserves regularity, so the comparison stays decidable and cheap.

Second, **refusals are typed and countable**. Without a category that separates "I could not read this" from "this is not there", a coverage number silently absorbs the reader's own limitations: a minimal-scope extractor would report eleven implemented clauses as absent. The `Unknown` taxonomy is therefore closed to five tags, each with a fixed field schema, and every emitted item is countable per metric and per corpus.

Third, **every number carries its counting rule and the identity of the artifact it came from**. Phase 0 published four scalars that no reconstructible counting rule reproduces, and the predicate-substrate signature of `jca_android` moved five times in four days. The canonical model therefore carries a `version` as a requirement, and no emitted table omits it. The stamp names a repository and a commit **per corpus**, not one commit for the run: the input spans two git repositories and one SDK directory, and a single scalar would attribute an upstream-derived number to the commit of a repository that did not produce it.

This capability **measures** the instrumentation contract; it does not change it. It edits no `.mop` file, alters no pipeline step, and changes nothing about what the monitors accuse. It is the **structural half** of a two-instrument design whose behavioural half already exists: the gh104 differential trace harness (`TraceRunner`, `scripts/gh104_diff_harness.py`, 131 versioned traces). All five metrics read artifacts; none executes a trace. That boundary is not a limitation to be apologised for but a fact to be published, because Phase 0 measured a case where the two halves disagree and only the behavioural half is right: the `KeyGeneratorSpec` `ORDER` is equivalent to its `ere` **and** the generated monitor accuses order against a program the rule accepts.

The implementation lives in the sibling `rvsec` Maven reactor as `rvsec-crysl` plus three children — `-core` (model, automata, comparison; **no dependency on either parser** — it may carry a serialization library for the JSON emitter, but importing `javamop` or `CrySLParser` into it would break the layering), `-mop` (lift and lower through `javamop`), `-crysl` (lift through `CrySLParser 4.0.6`) — in one JVM and one process. JSON is an output of the canonical model, never an interchange format between processes.

## Data Contracts

### Input
- `mopDirs: List<Path>` — directories of `.mop` files, read-only (`$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android,jca_android_bug_predicate,generic,generic_new}`)
- `sources: Map<CorpusId, SourceStamp>` — per corpus, the repository identity and commit it was read at, plus the `android.jar` API level and file digest. Supplied by the caller; there is no single commit that describes the whole input
- `cryslDir: Path` — the directory of CrySL rules, read-only. One oracle: `rvsec-cognicrypt/CrySL-Rules` (`.crysl`, 49 rules, read with no lexical normalization of any kind)
- `androidJar: Path` — `$ANDROID_HOME/platforms/android-30/android.jar`, used only as an a-posteriori signature index, never as a parser classpath
- `alphabetMap: Path` — `data/jca_android/order_alphabet_map.csv`, whose `disposition` column declares, per row and with a written reason, why a MOP event has no symbol in the rule. The committed map is anchored to the abandoned `api30` corpus (its `rule_line` values cite `.cryptsl` files); the component, as the map's new producer, re-anchors those references to the upstream `.crysl` rules, and the committed map remains readable as the historical input
- `commit: String` — **deprecated in favour of `sources`**; retained only as the identity of the `rvsec` checkout, which is the repository the change itself lives in

### Output
- `SpecModel` — the canonical model of one `.mop` or one `.crysl`, carrying `version : {corpus, repository, commit, data}`
- `ConformanceReport` — per specification: one `MetricResult` for each of M0–M4, each carrying its counting rule, its `Unknown` items and its witnesses
- JSON serialization of the above (an output, not an interchange format)
- CSV in the schemas of `data/jca_android/{predicate_graph,constraint_table,order_alphabet_map,divergence_record}.csv`
- Markdown reports in the shape of `data/gh104/evidence/*.md`
- A generated `.mop` file, when `mop.lower` is invoked

### Side-Effects
- **[Filesystem]**: writes JSON, CSV and Markdown to a caller-supplied output directory. Reads every input path read-only; no input corpus, oracle or `.mop` file is ever modified
- **[Process]**: none. No subprocess is spawned, no device is contacted, no network call is made

### Error
- `CorpusReadError` — an input directory does not exist or is unreadable. Fatal, before any metric runs
- `LiftFailure` — a `.mop` or `.crysl` file fails to parse. Recorded per file with the underlying exception; does not abort the run
- `MissingVersionError` — a `SpecModel` reaches serialization with an unpopulated `version`. Fatal by construction
- `CalibrationMismatch` — the calibration gate finds a target the component does not reproduce. Reported with both measurements and the counting rule of each; never silently reconciled

## Invariants

- **INV-CONF-01**: Every `SpecModel` the component emits MUST carry a populated `version`, and the `version` MUST identify the commit **of the repository that artifact came from**. The corpus spans two git repositories (`rvsec` for the `.mop` sets, `rvsec-cognicrypt` for the oracle) plus one SDK directory (`android.jar`), so a single scalar commit field would stamp an oracle-derived number with a commit unrelated to the artifact that produced it. Serialization of a model with an unpopulated `version` MUST raise `MissingVersionError` rather than emit.
- **INV-CONF-02**: Every emitted table — JSON, CSV or Markdown — MUST carry the commit stamp and the counting rule of each aggregate it reports. A table that reports a count without naming the rule that produced it MUST NOT be emitted.
- **INV-CONF-03**: `SpecModel.events` MUST be a `List` ordered by declaration index, and `SpecModel.order` MUST be an automaton over signatures. The component MUST NOT contain a representation of the form `Map<Label, Set<Signature>>`. An event's label MUST be a distinct `Label` type rather than a bare `String`, so that this prohibition is machine-checkable: a rule stated over `Map<String, Set<Signature>>` would be unenforceable, since `String` keys are pervasive and legitimate.
- **INV-CONF-04**: Each `.crysl` rule MUST be read with a `CrySLModelReader` instance constructed for that rule alone. Reusing a reader across rules MUST NOT occur: `OBJECTS` scope leaks between rules in both directions, and the set of rules that load is otherwise a function of read order.
- **INV-CONF-05**: `MOPNameSpace.init()` MUST be called before each `.mop` file is parsed. This is required for determinism and for symmetry with INV-CONF-04; its measured effect on the current corpus is nil.
- **INV-CONF-06**: The `Unknown` taxonomy MUST be closed to exactly six tags — `UnrecognizedConstraint`, `OverlappingDispatch`, `MultiSlicedOrder`, `UnresolvedSignature`, `UntranslatableConstraint`, `UnreachableAccusationSite` — each with its declared field schema. The sixth was added deliberately (researcher decision, 2026-08-24) because INV-CONF-09 requires M0's refusal to be a typed `Unknown` and none of the original five names an unreachable accusation site: `UnresolvedSignature` asserts something else, that the platform lacks a signature. Adding a tag is a visible change of contract, which is exactly what the closed hierarchy is for; it is not licence to add a seventh by convenience. The component MUST NOT emit an untagged refusal, and MUST NOT emit a tag outside this set.
- **INV-CONF-07**: `Unknown{OverlappingDispatch}` MUST carry a non-empty `labels` field. A refusal that does not name which labels overlap does not say how many letters the call emits.
- **INV-CONF-08**: Every published witness MUST carry `status ∈ {ABSTRACT, CONCRETE}` and the list of normalizations applied to obtain it. A witness with `status = ABSTRACT` MUST NOT be emitted with a false-positive or false-negative claim attached: a word accepted by an automaton is not an executable trace.
- **INV-CONF-09**: M0 MUST run before M1–M4 for each specification, and a specification M0 refuses MUST NOT receive an M1, M2, M3 or M4 verdict. The refusal MUST be emitted as a typed `Unknown` item.
- **INV-CONF-10**: M2 MUST take ε-erasure decisions from the `disposition` column of the alphabet map. It MUST NOT infer erasure from automaton shape. Where the map declares no disposition for an event that has no symbol in the rule, M2 MUST emit `Unknown` rather than choose.
- **INV-CONF-11**: Every emitted report MUST name the oracle (repository and commit) it was computed against and the pairing rule that matched specifications to rules. Pairing MUST be by declared type — the rule's `SPEC` FQN against the type of the specification's declared parameter (the pointcut's declaring type for a parameterless specification) — and MUST be **injective**: a rule is the oracle of at most one specification. Injectivity is not a refinement of convenience. `IvChainJunction.mop` declares `IvChainJunctionSpec(Cipher c)` and `CipherSpec.mop` declares `CipherSpec(Cipher c)` — byte-identically the same type — so pairing as a plain function of the declared type yields 23 of 24, not 22, and would make `Cipher.crysl`'s clauses enter M4's `absent` list twice. Where two specifications declare one type, the tie-break MUST be signature-derived and MUST NOT be name-derived: the rule goes to the specification covering more of its declared signatures, then more events, then lexicographically; the loser is reported as unpaired, naming the winner. Pairing MUST NOT be by file name, which is ambiguous in this corpus (`SecretKeySpec.mop` would match both `SecretKey.crysl` and `SecretKeySpec.crysl`, and five files declare a specification named differently from the file).
- **INV-CONF-12**: The component MUST NOT write to any path under a corpus or oracle directory. Defects found in a rule or a template are recorded as findings, never repaired in place.
- **INV-CONF-13**: M2 verdicts MUST be labelled `M2-decl` and MUST be accompanied by the statement that a declared-automaton verdict says nothing about what the generated monitor accuses. The component MUST NOT emit an unqualified "equivalent" verdict.
- **INV-CONF-14**: The calibration gate MUST run before the component's output is treated as measurement, and a `CalibrationMismatch` MUST be reported with both measurements and both counting rules. The component MUST NOT be adjusted to agree with a target as a way of clearing the gate.
- **INV-CONF-15**: The M4 report MUST carry, beside every aggregate, the statement that the FIEL/PROJETADO/CONFLADO/AUSENTE classification is human judgement wherever it is inherited rather than derived, and MUST mark each row as derived or inherited.
- **INV-CONF-16**: The component's parent pom MUST override `guava.version` and MUST NOT override `scala.version`. Overriding `scala.version` to `2.13.14` breaks `ptltl` with `NoClassDefFoundError: scala/Serializable`, and `ptltl` MUST NOT be excluded.
- **INV-CONF-17**: `android.jar` MUST be used only as an a-posteriori signature index. The component MUST NOT attempt to restrict the CrySL parser's classpath to it: the virtual classpath is strictly additive and resolution is parent-first, so the host JDK wins every name it has.

## ADDED Requirements

### Requirement: Canonical Model with Mandatory Version Stamp (FR03, NFR06)

The component SHALL represent every specification and every rule as one `SpecModel`, and every `SpecModel` SHALL carry the commit, the data timestamp and the corpus identifier it was read from. The version stamp is a requirement rather than a convenience because Phase 0 measured the predicate-substrate signature of `jca_android` changing five times in four days; two runs of the component a day apart are not comparable without it.

The model SHALL hold: the fully-qualified `type`; the `objects` declared; `events` as a `List<Event>` ordered by declaration index, each `Event` carrying its label, its pointcut, the set of concrete signatures it matches, an optional guard and its `declIndex`; `order` as a symbolic automaton over signatures with optional guards; `constraints` as a `List` (not a `Set` — identical clauses at different sites have different provenance); `ensures`, `requires` and `negates` as `List<PredicateRef>`; `forbidden` as a set of signatures; and `provenance` as `file:line` per item.

#### Scenario: Version stamp names the repository the artifact came from
- **WHEN** the component lifts `jca_android/CipherSpec.mop` from the `rvsec` checkout at `5fbe8173`
- **THEN** the resulting `SpecModel.version` SHALL name repository `rvsec` and commit `5fbe8173`
- **AND WHEN** it lifts `CrySL-Rules/Cipher.crysl` in the same run
- **THEN** that model's `version` SHALL name repository `rvsec-cognicrypt` and **its own** commit, not `5fbe8173`
- **AND** a table that reports both SHALL carry both stamps, because one commit does not describe the pair

#### Scenario: Serialization refuses an unstamped model
- **WHEN** a `SpecModel` reaches the JSON serializer with `version.commit` unset
- **THEN** the component SHALL raise `MissingVersionError`
- **AND** SHALL NOT write any output file for that model

#### Scenario: Events keep declaration order
- **WHEN** the component lifts a `.mop` declaring `f1` at line 198 and `f2` at line 210
- **THEN** `SpecModel.events` SHALL list `f1` before `f2`
- **AND** `f1.declIndex` SHALL be less than `f2.declIndex`
- **AND** `Event.label` SHALL be of type `Label`, not `String`
- **AND** no field of the model SHALL have a type assignable to `Map<Label, ?>` (INV-CONF-03), which is checkable precisely because `Label` is a distinct type

### Requirement: MOP Lift over the Five Corpora (FR01, FR03)

The component SHALL lift `.mop` files through `javamop.parser.SpecExtractor`, calling `MOPNameSpace.init()` before each file, and SHALL read all 215 files of the five corpora without a parse failure. It SHALL recognise **both** predicate substrates: `ExecutionContext` (arity 1, keyed by `equals`, boolean) and `PredicateStore` (arity N, keyed by identity, three-valued, with `validateAbsent`). The frozen `jca` set uses the first exclusively and the current `jca_android` uses the second exclusively, so reading only one makes the historical comparison impossible.

The lift SHALL survive the seven measured parser traps: `BlockStmt.getStmts()` returns `null` rather than an empty list for `{ }`; `MOPNameSpace` is a static global; `JavaMOPParser` keeps state in a static field, so the parse SHALL NOT be parallelised; `JavaParserAdapter` swallows exceptions from Java blocks, turning a malformed handler into a `null` `BlockStmt` with no warning; `getHandlers()` keys arrive lowercased (`@match1` → `"match1"`); the `BlockStmt` types come from the internal fork rather than `com.github.javaparser`; and `getRetType()` is always `null`, the real return type coming from `MethodPattern.getType()` inside the `MethodPointCut`.

#### Scenario: All five corpora lift without failure
- **WHEN** the component lifts `jca` (23 files), `jca_android` (24), `jca_android_bug_predicate` (23), `generic` (118) and `generic_new` (27)
- **THEN** it SHALL report `215 files, 215 ok, 0 fail`
- **AND** the aggregate event count SHALL be 905 and the aggregate parameter count 381
- **AND** the counting rules `spec.getEvents().size()` and `spec.getParameters().size()` SHALL be stated beside those two numbers

#### Scenario: Both predicate substrates are recognised
- **WHEN** the component lifts `jca/MacSpec.mop`, which calls `ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output)`
- **THEN** the model SHALL record an `ENSURES` of `GENERATED_MAC` with arity 1
- **AND WHEN** it lifts `jca_android/MacSpec.mop`, which calls `PredicateStore.instance().validateAbsent(Property.ENCRYPTED, ...)`
- **THEN** the model SHALL record a negated `REQUIRES` on the three-valued substrate
- **AND** each `PredicateRef` SHALL carry `file:line` provenance

#### Scenario: Empty handler block does not silently vanish
- **WHEN** the component lifts a specification whose `@match` block is `{ }` and whose `getStmts()` therefore returns `null`
- **THEN** the component SHALL record an empty handler rather than dereference `null`
- **AND** the model SHALL distinguish "handler present and empty" from "handler absent", because M0 depends on that distinction

### Requirement: CrySL Lift with a Fresh Reader per Rule (FR03)

The component SHALL construct a new `crysl.parsing.CrySLModelReader` for each rule it reads. Reusing one reader across rules leaks `OBJECTS` scope in both directions: `Signature.crysl` uses `offset` and `len` without declaring them and loads only if `GCMParameterSpec`, `IvParameterSpec` or `Mac` was read first in the same reader, while `SecretKey.crysl` read before `Key.crysl` breaks `Key.crysl`. Under a shared reader the set of rules that load is a function of read order: 40 random orders yield the histogram `{29:3, 30:15, 31:22}`. Under a fresh reader per rule the result is invariant.

The component SHALL apply **no lexical normalization of any kind** to the oracle: the upstream `CrySL-Rules` are read as they stand. (The five-substitution normalizer existed only for the abandoned `api30` corpus and has no consumer.)

#### Scenario: Upstream CrySL-Rules loads 47 of 49 without normalization
- **WHEN** the component reads the 49 upstream rules with a fresh reader per rule and no lexical substitution
- **THEN** it SHALL report `ok = 47, fail = 2`
- **AND** the two failures SHALL be `OAEPParameterSpec` (`:8: mismatched input 'alg' expecting RULE_ID` — the reserved word `alg` used as an object name) and `SSLEngine` (`:12: Couldn't resolve reference to Event 'cp1'` — the declared event is `ep1`), each recorded as a `LiftFailure` with its `CrySLParserException`
- **AND** the two failures SHALL be recorded as findings against the upstream corpus, never repaired in place (INV-CONF-12)
- **AND** the result SHALL be identical whatever order the rules are read in

#### Scenario: A shared reader is not offered as an option
- **WHEN** any code path in the component reads more than one rule
- **THEN** it SHALL construct one reader per rule
- **AND** no configuration flag SHALL exist that enables reader sharing

### Requirement: M0 Monitor Vitality, and Typed Refusal (FR01, NFR06)

M0 SHALL run before M1–M4 for each specification and SHALL answer three questions, all decidable from artifacts the design already produces. **M0.1 — does it index?** The generated monitor builds a `MapOfMonitor` when the specification's parameter binding is effective; a specification with `0/N` binding or with no declared parameter compiles to one monitor for the whole program, and parametric slicing is a no-op in it. **M0.2 — is the accusation site reachable?** The criterion is reachability of an accusation, not any one syntactic shape of it: a specification with no `@fail` and no reachable `addError` cannot accuse under any trace, whether or not its `@match` is empty. Two specifications of the corpus meet it, in both sets — `RandomStringPassword` (empty `@match`, no `@fail`) and `SecretKeySpec` (a **non-empty** `@match` that writes a predicate, no `@fail`, no `addError` anywhere). `SecretKeySpec` indexes, so a census framed on the specifications that do not index never sees it. **M0.3 — does the pointcut resolve?** Each resolved signature is checked a posteriori against the `android.jar` index.

M0 SHALL also run the non-normalized AST checker: identifiers unique, the formula's alphabet a subset of the declared identifiers, every declared event reachable in the formula, every `@match` paired with a `@fail`. This class of defect passes parser, monitor generator and Java compiler with zero errors, so no downstream stage can be relied on to catch it.

A specification M0 refuses SHALL NOT receive an M1–M4 verdict, and the refusal SHALL be emitted as a typed `Unknown`. M0 SHALL distinguish the three causes of silence, because only one of them is a repairable defect: a live monitor blind to end-of-trace, a live monitor whose target class is absent from the platform, and a specification with no accusation site.

#### Scenario: Five specifications of jca_android do not index
- **WHEN** M0 runs over `jca_android` at commit `5fbe8173`
- **THEN** it SHALL report exactly five specifications that do not build a `MapOfMonitor`: `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`, `KeyStoreSpec` and `RandomStringPassword`
- **AND** the counting rule SHALL be stated: `0/N` parameter binding, plus specifications declared with no parameter
- **AND** the report SHALL state that the AST-derived answer is a proxy and the generated monitor is the real oracle

#### Scenario: A specification with no accusation site is refused
- **WHEN** M0 examines `jca_android/RandomStringPassword.mop`, which declares `ere : vo gb`, an empty `@match` and no `@fail`
- **THEN** M0 SHALL refuse the specification with a typed `Unknown` naming an unreachable accusation site
- **AND** M1, M2, M3 and M4 SHALL NOT emit a verdict for it
- **AND** the report SHALL state that no trace can make it accuse, which is a property of the file and not of any corpus

#### Scenario: An unresolvable pointcut emits UnresolvedSignature
- **WHEN** M0.3 checks `jca_android/HMACParameterSpecSpec.mop`, whose pointcut names `javax.xml.crypto.dsig.spec.HMACParameterSpec`
- **THEN** M0 SHALL emit `Unknown{UnresolvedSignature, class: "javax.xml.crypto.dsig.spec.HMACParameterSpec", mode: CLASSE-AUSENTE}`
- **AND** the report SHALL record that the class exists in no verified Android API level (26, 30, 33, 35), so the pointcut can never match on device
- **AND** it SHALL NOT report the monitor as dead: the monitor is live and the target is absent, which are different findings

#### Scenario: The AST checker catches what the pipeline passes
- **WHEN** M0 examines `jca/GCMParameterSpecSpec.mop`, which declares two events with the identifier `c1` and whose `ere` references a non-existent `c2`
- **THEN** M0 SHALL report a duplicate-identifier violation and an alphabet violation
- **AND** the report SHALL note that this file parses, generates a monitor and compiles with zero errors, so neither "it parsed" nor "it compiled" is an oracle of sanity

### Requirement: M1 Event Coverage against the Oracle (FR03)

M1 SHALL compare the set of concrete signatures the `.mop` events match against the set the rule's `EVENTS` declares, and SHALL emit coverage plus **both** differences — signatures the specification monitors and the rule does not name, and signatures the rule names and the specification does not monitor. Its output SHALL feed the label alignment M2 consumes. Pairing follows INV-CONF-11: by declared type, never by file name.

#### Scenario: Both differences are emitted, never a single coverage number
- **WHEN** M1 compares `jca_android/MessageDigestSpec.mop` against `CrySL-Rules/MessageDigest.crysl`
- **THEN** it SHALL emit the coverage fraction, the list of MOP-only signatures and the list of rule-only signatures
- **AND** it SHALL NOT emit a coverage percentage without both lists beside it

#### Scenario: The declared-type pairing is 22 of 24
- **WHEN** M1 pairs the 24 `jca_android` specifications with the 49 upstream rules by declared type
- **THEN** it SHALL report 22 pairs — including `SecretKeySpec.mop` (declares `SecretKeySpec(SecretKey ...)`) paired with `SecretKey.crysl` and `SecretKeySpecSpec.mop` paired with `SecretKeySpec.crysl`, the case file-name pairing cannot resolve
- **AND** the two unpaired specifications SHALL be `IvChainJunction` and `RandomStringPassword`, which are exactly the two the alphabet map declares as skips

### Requirement: M2 Order Comparison over the Inverse Morphism (FR03)

M2 SHALL compare `L(A_mop)` with `L(A_crysl)` by product search in both directions, over `h⁻¹(L)` rather than over labels, and SHALL emit one of: equivalent, MOP more permissive, MOP more restrictive, or incomparable — each labelled `M2-decl`, each accompanied by the shortest witness with its status, and each with the set of normalizations applied printed beside it.

M2 SHALL determinize the rule automaton before comparing. Determinization is required for correctness — the Glushkov construction is genuinely non-deterministic for a rule of the form `ORDER con, a?, a`. Over the abandoned `api30` corpus it was measured as a no-op; over the 47 upstream rules that load, the no-op status is a **new measurement** the component SHALL publish, not an assumption it may carry over.

M2 SHALL take ε-erasure from the `disposition` column of the alphabet map, never from automaton shape. An erasure that a comparator infers is a decision nobody reviewed; an erasure the map declares is an assertion with an owner, a written reason and provenance, and M2's job is to check it.

#### Scenario: A verdict carries its label, its normalizations and its witness status
- **WHEN** M2 compares `jca_android/SecureRandomSpec.mop` against `CrySL-Rules/SecureRandom.crysl`
- **THEN** the verdict SHALL read `M2-decl: MOP more permissive, under N1 + N2`
- **AND** the witness SHALL be emitted with `status = ABSTRACT` because it was not executed
- **AND** the report SHALL state that an `M2-decl` verdict says nothing about what the generated monitor accuses

#### Scenario: Erasure comes from the disposition column
- **WHEN** M2 encounters `KeyGeneratorSpec.g3`, which has no symbol in the rule
- **THEN** it SHALL read the alphabet map row `KeyGeneratorSpec,g3,,,KeyGenerator.crysl,,order-unmapped,<reason>` (re-anchored; `KeyGenerator.cryptsl` in the committed historical map) and erase on that authority
- **AND** the emitted verdict SHALL quote the declared reason
- **AND WHEN** an unmapped event has no `disposition` row, M2 SHALL emit `Unknown` rather than infer an erasure

#### Scenario: Determinization always runs and its no-op status is measured
- **WHEN** M2 determinizes the automata of the 47 upstream rules that load
- **THEN** it SHALL report how many were already deterministic, as a measurement (over the abandoned `api30` corpus all 30 were; the upstream figure is new)
- **AND** the determinization step SHALL still execute, because a future rule of the shape `ORDER con, a?, a` is genuinely non-deterministic

#### Scenario: An overlapping dispatch with a non-static guard refuses
- **WHEN** M2 builds `h` for `jca_android/IvChainJunction.mop`, where `use` and `useRandomSpec` both match `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` and neither carries a `condition`
- **THEN** `h` SHALL map that signature to the concatenation `use useRandomSpec`, in declaration order
- **AND WHEN** an overlap is separated by a guard that is not statically decidable, M2 SHALL emit `Unknown{OverlappingDispatch, labels: [...]}` with the labels named (INV-CONF-07)

### Requirement: M3 Constraint Census by Idiom (FR03)

M3 SHALL classify each `CONSTRAINTS` clause of the rule by the idiom that implements it in the specification — **A** `Arrays.asList(...)` plus `ConscryptAliasTable.matches(...)`; **B** direct arithmetic in a `condition(...)` or an event body over `args()`-bound variables; **C** a helper method declared inside the specification; **D** an external helper class in `rvsec-core` — or record it absent. Clauses whose idiom the reader does not recognise SHALL emit `Unknown{UnrecognizedConstraint}` rather than be counted as absent, because a minimal-scope extractor would otherwise report eleven implemented clauses as missing.

M3 SHALL declare the counting rule of every denominator it publishes. The rule R1 counts one clause per `;` inside `CONSTRAINTS`, with comments removed and `&&` conjunctions not split; under other rules the same corpus yields different totals, and any upstream number entering a publication needs its rule beside it. Measured over the 49 upstream rules by three independent routes that agree: R1 gives **119**, splitting `&&` (6 occurrences) gives **125**, and splitting the sides of `=>` (26 occurrences) gives **145**. Any figure claiming a split total **below** the R1 total is impossible by construction, since splitting a clause can only raise a count.

M3 SHALL report **two distinct ceilings** and never sum them: the ceiling of the subject (clauses in rules with no specification) and the ceiling of the instrument (idioms the extractor does not follow). They err in different places and each needs its own line. (A third ceiling — clauses the generated `api30` oracle lost relative to upstream — existed while `api30` was an oracle; with the oracle switch it survives only as the method note recording why `api30` was abandoned: 25 clauses deleted across 12 of the 22 paired rules under R1.)

#### Scenario: The M3 denominator over the upstream oracle is 80
- **WHEN** M3 runs over `jca_android` against the upstream oracle
- **THEN** the denominator SHALL be 80 — the R1 clause count of the 22 paired rules (119 over all 49) — with the counting rule R1 printed beside it
- **AND** the numerator SHALL be measured, not carried over: the committed `constraint_table.csv` (59 data rows − 4 `MOP-SEM-BASE` = 55, − 30 `CRYSL-NAO-IMPLEMENTADO` = 25) is anchored to the abandoned `api30` oracle, and its 4 `MOP-SEM-BASE` rows are clauses `api30` had no base for that the upstream oracle does — each SHALL be re-examined rather than assumed unimplemented
- **AND** the report SHALL state that the fraction is expected to drop relative to the historical `25/55 = 45,5 %`, because the denominator grew for the measured reason that the upstream rules demand more, not because the specifications changed

#### Scenario: An unrecognised idiom is refused, not counted absent
- **WHEN** M3 encounters a clause implemented through a call the reader does not follow
- **THEN** it SHALL emit `Unknown{UnrecognizedConstraint, textoCru: <clause text>, site: <file:line>}`
- **AND** the clause SHALL be counted in the `Unknown` total for M3 and SHALL NOT be counted as absent

### Requirement: M4 Predicate Graph with Declared Provenance of Judgement (FR03, NFR06)

M4 SHALL build the `ENSURES`/`REQUIRES`/`NEGATES` graph of the specification and of the rule and compare them by arity, polarity and argument position, emitting edges present, edges absent and edges inverted. It SHALL recognise both substrates and SHALL emit both the site-level vocabulary of `predicate_graph.csv` (`disposition`, `verdict`) and the clause-level fidelity classification, because the two describe different objects and emitting one as a substitute for the other would replace a manual table with an automatic table that measures something else.

Every M4 aggregate SHALL carry the statement that the FIEL/PROJETADO/CONFLADO/AUSENTE classification is human judgement wherever it is inherited, and every row SHALL be marked derived or inherited. Giving those columns a derivable home is a named deliverable of this capability, not a side effect.

M4 SHALL detect the class of defect where a predicate is written and read over objects that are not the same object — a propagation bridge across type conversions. This is decidable from the graph: producer and consumer have incompatible types, or the keying is by identity over a value that is recreated.

#### Scenario: Every M4 number is stamped and rule-qualified
- **WHEN** M4 emits any aggregate over `jca_android`
- **THEN** the aggregate SHALL carry the commit stamp and the counting rule
- **AND** the report SHALL state that the substrate signature moved five times in four days (`64/21/5` → `47/26/7` → `28/35/12` → `0/45/19` → `0/70/21`), which is why the stamp is a requirement

#### Scenario: Inherited judgement columns are marked as such
- **WHEN** M4 emits a row whose fidelity class it could not derive
- **THEN** the row SHALL be marked `inherited`
- **AND** the aggregate that includes it SHALL carry the human-judgement caveat
- **AND** a row M4 derives SHALL be marked `derived`, so a reader can compute the derived fraction

#### Scenario: A propagation bridge across a type conversion is detected
- **WHEN** M4 examines a producer that ensures a predicate over a `byte[]` and a consumer that requires it over the `char[]` obtained through `String.valueOf(Object).toCharArray()`
- **THEN** M4 SHALL report the edge as broken, naming the type incompatibility
- **AND** the report SHALL state that identity keying over a recreated value cannot carry the predicate

### Requirement: Closed Unknown Taxonomy (NFR06)

The component SHALL emit refusals only under the five tags of the closed taxonomy, each with its declared field schema, and SHALL report the count of each tag per metric and per corpus. Adding a tag is a change of contract.

| Tag | Emitted when | Fields |
|---|---|---|
| `UnrecognizedConstraint` | the `condition`/`action` matches no known idiom | `{textoCru, site}` |
| `OverlappingDispatch` | two or more labels match one signature and the guard is not statically decidable | `{labels, signature, site}` |
| `MultiSlicedOrder` | a specification of *k* > 1 parameters whose `ORDER` interleaves events over different objects | `{params, site}` |
| `UnresolvedSignature` | a resolved signature is absent from the `android.jar` index | `{signature, class, mode, site}` |
| `UnreachableAccusationSite` | the specification has no `@fail` and no reachable `addError`, so no trace can make it accuse | `{spec, site}` |
| `UntranslatableConstraint` | the clause is about the origin's static type (`neverTypeOf`, `notHardCoded`) or is a liveness obligation over `ORDER` symbols (`callTo`) rather than about runtime values — `noCallTo` is not in this family: a prohibition is safety, its violation observable when it happens | `{clause, family, site}` |

#### Scenario: An untagged refusal is rejected
- **WHEN** any metric attempts to record a refusal without one of the five tags
- **THEN** the component SHALL fail rather than emit
- **AND** the closed set SHALL be enforced in the type system, not by convention

#### Scenario: Refusal counts travel with coverage numbers
- **WHEN** the component emits the M3 coverage figure for `jca_android`
- **THEN** the `Unknown` count for M3 over that corpus SHALL be emitted in the same table
- **AND** the report SHALL make plain that "could not read" and "is not there" are different columns

#### Scenario: neverTypeOf and notHardCoded are refused, not commented
- **WHEN** M3 encounters the seven `neverTypeOf[..., java.lang.String]` clauses of the upstream corpus (across five rules), which are properties of the origin's static type and unobservable at runtime where the signature is already `char[]`
- **THEN** the component SHALL emit `Unknown{UntranslatableConstraint, family: "neverTypeOf"}` for each
- **AND** SHALL NOT record them as a comment, because a comment is not countable and does not enter a metric

### Requirement: Witness Status and Normalization Disclosure (NFR06)

Every witness the component publishes SHALL carry `status ∈ {ABSTRACT, CONCRETE}` and the list of normalizations applied to reach it. `ABSTRACT` means a word over the alphabet; `CONCRETE` means a trace that was executed, with the harness that executed it named. An `ABSTRACT` witness SHALL NOT be published with a false-positive or false-negative claim attached.

The distinction is not pedantry. Phase 0 measured a witness valid at automaton level and impossible in Java: `javax.crypto.Cipher` carries a mode state machine that neither the `.mop` nor the rule models, so `wrap` after `ENCRYPT_MODE` throws `IllegalStateException` before any monitor sees it.

#### Scenario: An abstract witness may not carry a behavioural claim
- **WHEN** M2 emits the witness `g1 i2 i2 f2` for `CipherSpec`, obtained by product search and never executed
- **THEN** the witness SHALL carry `status = ABSTRACT`
- **AND** the emitted text SHALL NOT contain a false-positive or false-negative claim about it
- **AND** the normalizations that produced it SHALL be listed beside it

#### Scenario: A concrete witness names its harness
- **WHEN** a witness was produced by replaying a trace through a generated monitor
- **THEN** it SHALL carry `status = CONCRETE` and the identifier of the harness and trace that produced it

### Requirement: Single-Oracle Discipline (FR03)

The component SHALL compare against the upstream `CrySL-Rules` as the single oracle and SHALL NOT read the abandoned `generated/api30` corpus. Every report SHALL name the oracle's repository, commit and pairing rule (INV-CONF-11). The reason `api30` is not an oracle is recorded, not measured against: under R1 it deletes 25 `CONSTRAINTS` clauses across 12 of the 22 paired rules relative to upstream, so a specification faithful to the upstream rule would be accused of implementing clauses "without base".

#### Scenario: A specification faithful to the rule is not accused
- **WHEN** M3 evaluates `jca_android/DHGenParameterSpecSpec.mop`, which implements `exponentSize < primeSize` — a clause present in `DHGenParameterSpec.crysl` upstream and deleted by the abandoned `api30` generation
- **THEN** the clause SHALL be counted as implemented
- **AND** the report SHALL NOT emit `MOP-SEM-BASE` for it, because the oracle that lacked the base is no longer consulted

#### Scenario: A report without oracle identity is refused
- **WHEN** any metric attempts to emit a report that does not name the oracle repository, its commit and the pairing rule
- **THEN** the component SHALL fail rather than emit (INV-CONF-11)

### Requirement: MOP Lower and the Two-Layer Round-Trip Gate (FR01)

The component SHALL emit `.mop` text by constructing a `MOPSpecFile` and handing it to `DumpVisitor`, never by string concatenation, and SHALL validate what it emits through a gate in two layers with different standing.

Layer 1 is the **non-normalized AST checker over the generated tree** — the same piece M0 runs: identifiers unique, formula alphabet ⊆ identifiers, every declared event reachable, every `@match` paired with a `@fail`, every pointcut resolving against `android.jar`. It is cheap, non-circular, and catches the two failure modes a language-equivalence gate cannot see: a declared event absent from the `ere` (which is local, and which ε-normalization can even erase) and a `@match` with no `@fail` (which is about handlers, so two specifications differing only in the handler have identical languages).

Layer 2 is product search against the rule, kept as **evidence** rather than as the gate, with the applied normalizations printed beside each verdict — because a specification that passes only under N3 and N4 is saying something.

`crysl.lower` is out of scope for this capability, with the reason recorded: it has no known consumer and the CrySL project ships no formatter.

#### Scenario: Generated text reparses to an equivalent model
- **WHEN** the component lowers a `SpecModel` to `.mop` and lifts the result back
- **THEN** the two models SHALL agree on type, objects, events in declaration order, order automaton, constraints and predicates
- **AND** any disagreement SHALL be reported per field, never as a single boolean

#### Scenario: Layer 1 catches what language equivalence cannot
- **WHEN** the generated specification declares an event that the `ere` does not reference
- **THEN** Layer 1 SHALL fail the generation
- **AND** the failure SHALL be reported even when Layer 2 finds the languages equivalent

### Requirement: Calibration against Independently Measured Targets (NFR03)

The component SHALL reproduce, before its output is treated as measurement, eight targets each produced by an independent route at commit `5fbe8173`. A measuring instrument that ships without calibration publishes numbers that look like measurement and are not, which is precisely the failure mode this capability exists to remove.

| Target | Value | Independent route |
|---|---|---|
| `SpecExtractor` over the five corpora | `215/215 ok, 0 fail` | `Census.java` probe |
| multi-parameter specifications in `generic` | `93`, buckets `{1:25, 2:39, 3:28, 4:18, 5:7, 6:1}` | `Census.java`, and an earlier independent count |
| multi-parameter specifications in `jca_android` | `0 of 24` | `Census.java` |
| upstream rules that load, fresh reader per rule, no normalization | `47 of 49` (failures: `OAEPParameterSpec`, `SSLEngine`) | `V3Fresh.java` probe |
| M3 denominator over the upstream oracle (R1, 22 paired rules) | `80` (119 over all 49) | two independent R1 implementations in `docs/handoff/20260824_arnes_adjudicacao/`, reproduced digit for digit by a third during verification; the committed `constraint_table.csv` (`25 of 55`, `api30`-anchored human judgement over `jca_android`) remains a labelled historical reconciliation, not a calibration |
| `.mop` ↔ rule pairing | `22 of 24` | the two unpaired specifications as `order_alphabet_map.csv` declares them — **as prose in the file's header, deliberately never data rows**, which is how that file states a skip — an artifact the component does not produce — **not** re-running the declared-type rule, which is the component's own rule |
| specifications with partial parameter binding | `5 of 22` | `Binding.java` probe |
| specifications without `MapOfMonitor` | `5 of 24` | **the generated monitors**, regenerated and read for the presence of a `MapOfMonitor` — **not** the AST proxy, which the component implements and could therefore never contradict |

**A target whose route is the component's own rule is not a calibration.** Two of the eight were originally stated that way — the pairing target routed through the component's own pairing rule, and the `MapOfMonitor` census taken from the AST proxy the component implements — and a gate built on them could not fail. Both now name a route the component does not produce. Where no independent route exists for a quantity, the component SHALL publish it as a **self-consistency check**, labelled as such, and SHALL NOT count it among the calibration targets.

A disagreement SHALL be reported as `CalibrationMismatch` carrying both measurements and both counting rules, and SHALL be resolved by measuring both sides. The component SHALL NOT be adjusted until it agrees.

#### Scenario: Calibration passes and the run proceeds
- **WHEN** the calibration gate runs against the `rvsec` checkout at `5fbe8173`
- **THEN** all eight targets SHALL be reproduced, each with its counting rule printed
- **AND** each target SHALL record the repository and commit **its own route** was taken at, alongside the corresponding stamp of the run

#### Scenario: A target whose route is the component's own rule is refused as a target
- **WHEN** a proposed calibration target's independent route is a rule the component itself implements
- **THEN** the gate SHALL NOT accept it as a calibration target
- **AND** the quantity SHALL be published as a self-consistency check, labelled as such, so a reader does not count it as external validation

#### Scenario: A disagreement is a finding, not a tuning signal
- **WHEN** the component computes `4 of 24` where the target says `5 of 24` specifications without `MapOfMonitor`
- **THEN** it SHALL emit `CalibrationMismatch` with both values, both counting rules and the differing specifications named
- **AND** the run SHALL NOT proceed to publish that metric
- **AND** the resolution SHALL be to measure both sides, never to alter the component until the numbers match

### Requirement: Reactor Placement, Dependency Discipline and CLI (NFR01, NFR03)

The component SHALL live at `rvsec/rvsec-crysl/` in the sibling `rvsec` reactor as a parent pom plus three children, built by the reactor's existing command with no change to it. The parent SHALL override `guava.version` to `33.5.0-jre` and SHALL exclude `slf4j-simple`, which `CrySLParser 4.0.6` pulls in `compile` scope. It SHALL NOT override `scala.version`, and `ptltl` SHALL NOT be excluded.

The dependency boundary is measured, not assumed: the root `dependencyManagement` pins `guava.version = 19.0` and reaches any descendant, so a probe that only depends on `CrySLParser` compiles cleanly and dies at runtime with `NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()`. Overriding the property in the component's parent resolves it, and the effect appears in one child only — `-crysl` — because `javamop` pulls no Guava at all.

The CLI SHALL follow the shape of `rvsec-mop-extractor` (pom, CLI, facade, visitor, writer) rather than its code, and SHALL expose subcommands for the comparison, for `mop.lower`, and for the calibration gate.

#### Scenario: The four poms build inside the reactor
- **WHEN** `mvn clean install -DskipMopAgent -DskipTests` runs at the reactor root with the component registered in `rvsec/rvsec/pom.xml` `<modules>`
- **THEN** the parent and the three children SHALL build
- **AND** `main.basedir` SHALL resolve in the new modules
- **AND** the reactor build command SHALL be unchanged

#### Scenario: Both parsers run in one JVM
- **WHEN** the component parses a `.mop` file and reads a `.crysl` rule in the same process
- **THEN** both SHALL succeed with `guava-33.5.0-jre` on the classpath
- **AND** no subprocess SHALL be spawned and no JSON SHALL cross a process boundary

#### Scenario: scala.version stays inherited
- **WHEN** the component's effective pom is resolved
- **THEN** `scala.version` SHALL be the reactor's `2.11.12`
- **AND** `ptltl` SHALL be present on the classpath of `rvsec-crysl-mop`
- **AND** the report SHALL record that no specification of the current corpus uses `ptltl`, so the constraint protects a future specification rather than a present one

### Requirement: Retirement of Superseded Ad-Hoc Comparators (NFR01)

The component SHALL replace ad-hoc implementations on a written criterion: **the ad-hoc dies when the component reproduces its verdict, not when it compiles.** Retirement happens in two stages.

Stage one, in this change: the six `ORDER` comparators and the seven CrySL readers under `audit/20260808_*` — 3 907 lines between them, one file counting in both categories — move to `backup/` under P3 (complete deletion, backup first, all callers updated). Nothing in CI depends on them.

Stage two, in a later cleanup change: `scripts/gh105_order_gate.py`, the three `gh10{1,4}_*.py` scripts that read `.cryptsl`, and `tests/parity/test_gh105_predicate_gates.py` retire only after the component reproduces their verdicts. Until then they stay green and they stay authoritative. (Those scripts read the historical `.cryptsl` corpus the component no longer consults; "reproduces their verdicts" therefore means reproducing the verdict on the same historical input, stamped as such, not re-deriving it from the upstream oracle.)

#### Scenario: Audit-era comparators move to backup in this change
- **WHEN** stage one completes
- **THEN** the six comparators and seven readers under `audit/20260808_*` SHALL exist under `backup/` and not under `audit/`
- **AND** a grep for references to their module paths SHALL return nothing outside `backup/`
- **AND** no CI job SHALL change status

#### Scenario: CI gates survive until reproduced
- **WHEN** the component is complete and calibrated
- **THEN** `scripts/gh105_order_gate.py` and `tests/parity/test_gh105_predicate_gates.py` SHALL still exist and still run
- **AND** their retirement SHALL be a separate change, entered only after the component reproduces their verdicts on the same corpus
