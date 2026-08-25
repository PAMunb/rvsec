# Design: gh106-mop-crysl-conformance

**GitHub Issue**: #106 · **Track**: Full SDD · **Capability**: `conformance` (new, `INV-CONF`)
**FRs/NFRs**: FR01, FR03, NFR03, NFR06

## Context

The proposal establishes *why* a mechanical MOP–CrySL conformance verifier is needed and the delta spec establishes *what* it must do. This document establishes *how*, and its main job is to record the decisions that Phase 0 paid for by measuring them, so that implementation does not re-derive them or quietly reverse them.

The component is **Java**, not Python, and lives in the sibling `rvsec` Maven reactor rather than in the `rv-android` uv workspace. That follows from the inputs: the only complete `.mop` parser is `javamop.parser.SpecExtractor` and the only complete CrySL parser is `crysl.parsing.CrySLModelReader` (Xtext/EMF), both JVM libraries. Fourteen of the eighteen existing `gh10*` Python scripts parse `.mop` by regular expression precisely because Python has no access to either, and the resulting duplication — seven `ORDER` comparators, eleven CrySL readers — is the cost this change removes.

Three constraints are inherited and non-negotiable, each measured:

1. **A fresh `CrySLModelReader` per rule.** The reader leaks `OBJECTS` scope between rules in both directions — measured on the upstream corpus too (`SecretKey.crysl` read before `Key.crysl` breaks `Key.crysl`). Under a shared reader the set of rules that load is a function of read order (40 random orders over the abandoned `api30` corpus gave the histogram `{29:3, 30:15, 31:22}`); under a fresh reader it is invariant — 47 of 49 over the upstream oracle.
2. **`guava.version` overridden, `scala.version` not.** The reactor root's `dependencyManagement` pins Guava 19.0 and reaches every descendant; `CrySLParser 4.0.6` pulls Guice 7 which needs Guava ≥ 31, so with the pin inherited the code compiles cleanly and dies at runtime on `NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()`. Overriding `guava.version` in the component's parent fixes it, and the effect lands in one child only (`-crysl`) because `javamop` pulls no Guava at all. Overriding `scala.version` to 2.13.14 kills `ptltl` with `NoClassDefFoundError: scala/Serializable`, and `ptltl` cannot be excluded.
3. **`android.jar` is an index, never a classpath.** `CrySLModelReaderClassPath.getClassPath()` returns the union of the JVM's `java.class.path` with the virtual entries, and the reader builds a `URLClassLoader` with the default parent, so resolution is parent-first and the host JDK wins every name it has. Targeting API 30 through the parser is impossible; checking each resolved signature against an index of `android.jar` afterwards is cheap and gives the same information.

The corpus is a moving target — `jca_android` changed in every prior round and now stands at 24 specifications with gh105 at 72 of 74 — which is why a **per-corpus** `version` stamp is a model requirement rather than a reporting convenience.

## Architecture

```
                        ┌──────────────────────────────────────────────┐
   .mop  ──── lift ────▶│                                              │
  (215 files,           │            rvsec-crysl-core                  │
   5 corpora)           │                                              │
                        │   SpecModel · Automaton · h⁻¹(L)             │──▶ ConformanceReport
                        │   M0 M1 M2 M3 M4 · Unknown · Witness         │    (JSON · CSV · MD)
  .crysl ─── lift ─────▶│                                              │
  (single oracle:       └──────────────────────────────────────────────┘
   upstream                        ▲                    │
   47/49)                          │                    ▼
                          alphabet map            rvsec-crysl-mop
                        (disposition col.)         model → MOPSpecFile
                                                   → DumpVisitor → .mop
                                                        │
                                                        ▼
                                              round-trip gate (2 layers)
```

One JVM, one process. JSON is an **output** of the canonical model, never an interchange format — the three-process alternative was rejected because its stated justification was measured false and because one of its costs ("a read error becomes an exit code instead of a typed `Unknown` item") contradicts the design's own non-negotiable.

```
rvsec-crysl                    (parent pom: guava.version=33.5.0-jre; scala.version inherited)
├── rvsec-crysl-core           canonical model, automata, M0–M4         [no parser deps]
├── rvsec-crysl-mop            lift  : SpecExtractor      → SpecModel   [javamop]
│                              lower : SpecModel → MOPSpecFile → DumpVisitor
└── rvsec-crysl-crysl          lift  : CrySLModelReader   → SpecModel   [CrySLParser 4.0.6,
                                                                          slf4j-simple excluded]
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `core.model.SpecModel` | canonical model, stamped per corpus with repository + commit | — | — |
| `core.model.Label` | distinct label type, so INV-CONF-03 is machine-checkable | — | — |
| `core.model.Event` | label, pointcut, signatures, guard, `declIndex` | — | — |
| `core.model.Unknown` | closed sealed hierarchy, five tags | — | — |
| `core.model.Witness` | word, `status`, normalizations applied | — | — |
| `core.automata.Nfa` / `Dfa` | determinization, minimization, product search | `Automaton` | `Automaton` |
| `core.automata.InverseMorphism` | builds `h`, computes `h⁻¹(L)` | `List<Event>`, `Automaton` | `Automaton` |
| `core.metric.M0Vitality` | indexes? accusation reachable? pointcut resolves? + AST checker | `SpecModel`, `ApiIndex` | `M0Result` \| refusal |
| `core.metric.M1Events` | signature-set coverage and both differences | two `SpecModel` | `M1Result` |
| `core.metric.M2Order` | `h⁻¹(L_mop)` vs `L(A_crysl)`, both directions | two `SpecModel`, `AlphabetMap` | `M2Result` |
| `core.metric.M3Constraints` | idiom classification A/B/C/D/absent, two ceilings | two `SpecModel` | `M3Result` |
| `core.metric.M4Predicates` | predicate graph, arity/polarity/position | two `SpecModel` | `M4Result` |
| `core.calibration.CalibrationGate` | the eight targets, each with a route the component does not produce | `ConformanceReport` | pass \| `CalibrationMismatch` |
| `core.emit.{JsonEmitter,CsvEmitter,MarkdownEmitter}` | stamped output in the committed CSV schemas | `ConformanceReport` | files |
| `mop.MopLifter` | `SpecExtractor` → `SpecModel`, `MOPNameSpace.init()` per file | `Path` | `SpecModel` |
| `mop.PredicateIdioms` | recognises substrate A (`ExecutionContext`) and B (`PredicateStore`) | `BlockStmt` | `List<PredicateRef>` |
| `mop.FormulaParser` | mini-parser for `ere`/`fsm` text | `String` | `Automaton` |
| `mop.MopLowerer` | `SpecModel` → `MOPSpecFile` → `DumpVisitor` | `SpecModel` | `.mop` text |
| `mop.RoundTripGate` | Layer 1 AST checker, Layer 2 product search as evidence | `.mop` text, `SpecModel` | verdict |
| `crysl.CryslLifter` | fresh reader per rule, no normalization, `StateMachineGraph` → automaton | `Path` | `SpecModel` |
| `crysl.CryslProvenance` | EMF route (`XtextResource` + `NodeModelUtils`): event/aggregate names, `file:line`, `resource.getErrors()` | `Path` | provenance + validity |
| `crysl.ApiIndex` | indexes `android.jar` by class and by method signature | `Path` | `ApiIndex` |
| `cli.ConformanceCli` | subcommands `compare`, `lower`, `calibrate` | args | exit code |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|-------------|---------------|------|
| Canonical Model with Version Stamp | `core.model.SpecModel`, `core.emit.JsonEmitter` | `SpecModelVersionTest` |
| INV-CONF-01 (version populated) | `JsonEmitter` throws `MissingVersionError` | `test_inv_conf_01_unstamped_refused` |
| INV-CONF-02 (rule + commit on every table) | `core.emit.StampedTable` wraps all emitters | `test_inv_conf_02_table_carries_rule` |
| INV-CONF-03 (no `Map<Label,Set<Signature>>`) | `core.model.Event` list + ArchUnit rule | `ModelShapeArchTest` |
| MOP Lift over Five Corpora | `mop.MopLifter` | `MopLiftCorpusTest` (215 files) |
| INV-CONF-05 (`MOPNameSpace.init()` per file) | `MopLifter.lift()` | `test_inv_conf_05_init_per_file` |
| CrySL Lift, Fresh Reader per Rule | `crysl.CryslLifter` | `CryslLiftOracleTest` |
| INV-CONF-04 (fresh reader) | `CryslLifter` constructs per call; ArchUnit forbids field-held reader | `test_inv_conf_04_order_invariance` (shuffled order, 47/49 always) |
| INV-CONF-17 (`android.jar` as index only) | `crysl.ApiIndex`; no classpath wiring exists | `ApiIndexTest` |
| M0 Monitor Vitality | `core.metric.M0Vitality` | `M0VitalityTest` |
| INV-CONF-09 (M0 blocks M1–M4) | `core.compare.Pipeline` short-circuits | `test_inv_conf_09_refusal_blocks` |
| M1 Event Coverage | `core.metric.M1Events` | `M1EventsTest` |
| M2 Order Comparison | `core.metric.M2Order`, `core.automata.*` | `M2OrderTest` |
| INV-CONF-10 (disposition, not inference) | `M2Order` reads `AlphabetMap`; no shape heuristic exists | `test_inv_conf_10_unmapped_emits_unknown` |
| INV-CONF-13 (`M2-decl` label) | `M2Result.toString()` | `test_inv_conf_13_label_present` |
| M3 Constraint Census | `core.metric.M3Constraints` | `M3ConstraintsTest` |
| M4 Predicate Graph | `core.metric.M4Predicates` | `M4PredicatesTest` |
| INV-CONF-15 (judgement provenance) | `M4Result.rows[].origin ∈ {derived, inherited}` | `test_inv_conf_15_rows_marked` |
| Closed Unknown Taxonomy | `core.model.Unknown` sealed interface, five permits | `UnknownTaxonomyTest` |
| INV-CONF-06 / INV-CONF-07 | sealed hierarchy; `OverlappingDispatch.labels` non-empty in ctor | `test_inv_conf_07_labels_required` |
| Witness Status | `core.model.Witness` | `WitnessStatusTest` |
| INV-CONF-08 (ABSTRACT vs claim) | `MarkdownEmitter` refuses the pairing | `test_inv_conf_08_abstract_no_claim` |
| Single-Oracle Discipline | `Pipeline` + report header; pairing by declared type | `SingleOracleDisciplineTest` |
| INV-CONF-11 (oracle identity + pairing rule) | every report header names oracle repository, commit and pairing rule | `test_inv_conf_11_report_identity` |
| MOP Lower and Round-Trip Gate | `mop.MopLowerer`, `mop.RoundTripGate` | `RoundTripGateTest` |
| Calibration | `core.calibration.CalibrationGate` | `CalibrationGateTest` (the eight targets) |
| INV-CONF-14 (mismatch is a finding) | `CalibrationGate` throws, never adjusts | `test_inv_conf_14_mismatch_reported` |
| Reactor Placement / Dependency Discipline | the four `pom.xml` | `ReactorBuildIT`, `DependencyDisciplineTest` |
| INV-CONF-16 (guava yes, scala no) | parent pom properties | `test_inv_conf_16_effective_pom` |
| INV-CONF-12 (read-only corpora) | no write path outside the output dir | `test_inv_conf_12_no_corpus_write` |
| Retirement of Ad-Hoc Comparators | `backup/` move + grep gate | `tests/parity/test_gh106_retirement.py` |

## Goals / Non-Goals

**Goals**

- A single durable home for the MOP↔CrySL comparison, replacing seven `ORDER` comparators and eleven CrySL readers.
- Five metrics whose results are countable, stamped, and refusable — a refusal is data, not a gap.
- A literal comparison against the upstream rules as the single oracle, with every divergence accused and its adjudication (deliberate adaptation × infidelity) left to the corpus record — the separation of instrument and object that no engineering choice of this group can blur.
- A calibration gate that makes the instrument prove itself against numbers produced by another route before it is trusted.

**Non-Goals**

- **`crysl.lower`.** No known consumer, and the CrySL project ships no formatter, so it would cost ~400 lines of pretty-printer for output nobody reads. Recorded as future work with the reason.
- **Executing traces.** All five metrics are structural. The behavioural half is the gh104 harness, which already exists; promoting it to an M2 oracle needs a word enumerator and an event → call-with-arguments map, neither of which exists.
- **Repairing any specification, rule or template.** Findings are recorded; nothing upstream or in-corpus is edited (INV-CONF-12). Repairing while measuring loses traceability.
- **Changing the instrumentation contract.** No `.mop` edited, no pipeline step altered, no monitor accuses differently.
- **Retiring the CI gates in this change.** They stay green and authoritative until the component reproduces their verdicts.
- **A multi-dialect translation framework.** Two languages, one use case. P1.

## Decisions

**D-01 · One JVM and three Maven modules, not three processes stitched by JSON.**
*Chosen because* the justification for the split was measured false — `javamop` pulls neither Guava nor Soot — and one line of `<guava.version>33.5.0-jre</guava.version>` in the component's parent puts both parsers in the same process, verified by probe. *Alternative rejected:* three processes. It charged three costs, and one of them ("a read error becomes an exit code instead of a typed `Unknown` item") contradicts the design's own non-negotiable. The earlier evidence for the split showed only that three processes *work*; it never ran the control of whether one process fails, and it does not. *Consequence:* the core needs no `ere` parser of its own on the wire, there is no DFA state-numbering contract to fix across a boundary, and lift errors stay typed.

**D-02 · `events` is an ordered `List`; `order` is a symbolic automaton over signatures; the comparison object is `h⁻¹(L)`.**
*Chosen because* the alphabet is not disjoint in the corpus: `IvChainJunction` `use`/`useRandomSpec` both match one `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` call with no `condition` on either side, so one call emits two letters. *Alternative rejected:* `Map<Label, Set<Signature>>` with a minimal DFA over labels. It presupposes one letter per observed call, which is false, and it discards the information before any normalization can use it. *Consequence:* N4 stops being a normalization applied to an already-lossy model and becomes a construction step; inverse morphism preserves regularity, so the comparison stays decidable and cheap; and where the guard is not statically decidable the honest output is `Unknown{OverlappingDispatch, labels:[…]}`. This decision is *forbidden to reverse*: the witness that motivated it was replaced once already (the `CipherSpec` `f1`/`f2` pair died when gh105 narrowed the pointcut, and a new one appeared in the same set on the same day), which is what proves the phenomenon structural rather than accidental.

**D-03 · M0 runs first and refuses.**
*Chosen because* an order verdict over a monitor that does not run is empty, and the corpus contains the case: five specifications do not index, one of which cannot accuse under any trace. *Alternative rejected:* running M1–M4 unconditionally and letting the reader notice. That publishes four confident verdicts about a dead artifact. *Consequence:* M0 is also the non-normalized AST checker the round-trip gate needed — the same piece, promoted from internal gate to published metric — and the "specification absorbs misuse" phenomenon becomes an M0 property instead of an ad-hoc regex census.

**D-04 · M0 separates three causes of silence.**
*Chosen because* the behavioural measurement showed that "does not build a `MapOfMonitor`" fuses three different phenomena and only one is a repairable defect: a live monitor blind to end-of-trace (the `ere` `c1 (r1|r2)+ cl1` accepts `c1 r1` as a live prefix and JavaMOP has no end-of-trace event, so "opened and never closed" is undetectable by construction of the formalism); a live monitor whose target class is absent from the platform; and a specification with an empty `@match` and no `@fail`. *Consequence:* the first is a `divergence_record` row, the second is `Unknown{UnresolvedSignature}`, and only the third is an M0 refusal. Collapsing them would report a limit of the formalism as a defect of the file.

**D-05 · ε-erasure comes from the `disposition` column, never from automaton shape.**
*Chosen because* an erasure the comparator infers is a decision nobody reviewed, and the shape criterion is provably insufficient: it does not license erasing `KeyGeneratorSpec.g3`, which loops only at the initial state. What licenses it is N1, valid there by the decidable `MapOfMonitor` criterion — and since gh105 task 7.1 the alphabet map declares the disposition with a written reason for all 22 pairable specifications. *Alternative rejected:* inferring from self-loops. *Consequence:* where an unmapped event has no disposition row, M2 emits `Unknown` rather than choosing.

**D-06 · One oracle: the upstream `CrySL-Rules`. The generated `api30` corpus is abandoned.**
*Chosen because* the comparison is literal and mechanical, and measured against upstream the `api30` generation deletes 25 `CONSTRAINTS` clauses across 12 of the 22 paired rules (`−33` net across 16 rules over the full sets, under R1) — an oracle that demands less than the source of truth understates what the specifications must encode, and a specification faithful to the upstream rule would be accused of implementing clauses "without base". *Alternative rejected:* both oracles with the difference published as an "oracle ceiling" — an axis that measured the quality of a corpus this project no longer consumes (researcher decision, 2026-08-24). *Consequence:* the deletion measurement survives as the method note recording *why* `api30` was abandoned; pairing is **by declared type** (`SPEC` FQN against the spec's parameter type; the pointcut's declaring type for the two parameterless specs), measured at 22 of 24 with the same two skips — pairing by file name is forbidden as ambiguous (`SecretKeySpec.mop` matches two rules by name).

**D-07 · `MOPNameSpace.init()` per file, at measured zero cost.**
*Chosen* for determinism and for symmetry with D-08, not because it changes a number: probed over the five corpora with and without, `ok=215 fail=0 eventos=905 parametros=381` both ways, identical in all three aggregates. *Consequence:* the asymmetry with the CrySL side closes, and the design says so honestly instead of inflating it into a correctness fix.

**D-08 · A fresh `CrySLModelReader` per rule, with no sharing option.**
*Chosen because* scope leaks in both directions and the loaded set becomes a function of read order — measured on the upstream corpus itself: `SecretKey.crysl` read before `Key.crysl` breaks `Key.crysl`. *Consequence:* the corpus number is 47 of 49, invariant under read order; the two failures (`OAEPParameterSpec`, `SSLEngine`) are genuine defects of the upstream files, recorded as findings. No configuration flag enables sharing, because a flag that reintroduces non-determinism is a flag that will be set.

**D-09 · `android.jar` as an a-posteriori index.**
*Chosen because* restricting the parser's classpath is impossible in principle: the virtual classpath is additive, resolution is parent-first, and `java.base` comes from the module layer rather than `java.class.path`, so not even `parent = null` removes it. *Consequence:* 215 resolved signature lines over the upstream oracle, identical with and without the jar; checking them afterwards costs an index of 4 750 classes and decomposes as `175 exact + 29 arity-only + 5 absent-class + 6 declared inheritance limitations of the checker` — the absent classes being `javax.servlet.http.Cookie` (no `javax.servlet` on Android), `DSAGenParameterSpec` (absent before API 35) and `HMACParameterSpec` (absent from every level). With a single oracle this check is the only place the Android platform enters the computation, which raises its standing rather than lowering it.

**D-10 · Every witness carries `ABSTRACT`/`CONCRETE` and its normalizations.**
*Chosen because* a word accepted by an automaton is not an executable trace: `javax.crypto.Cipher` carries a mode state machine that neither the `.mop` nor the rule models, so an automaton-valid witness can be impossible in Java. *Consequence:* the emitter refuses to place a false-positive claim beside an `ABSTRACT` witness, and every verdict prints which normalizations produced it — a specification that only passes under N3 and N4 is saying something.

**D-11 · The `Unknown` taxonomy is a sealed hierarchy of exactly five types.**
*Chosen because* a refusal category with no fixed schema is not countable, and the whole reporting discipline of the capability depends on it being countable. Enforcing it in the type system rather than by convention means adding a tag is a visible change of contract. *Consequence:* five permitted subtypes, `OverlappingDispatch.labels` non-empty by construction, and per-metric per-corpus refusal counts emitted beside every coverage figure.

**D-12 · The round-trip gate is two layers with different standing.**
*Chosen because* a language-equivalence gate compares generator output against the rule *through the same normalization layer the comparator uses*, so it cannot see a defect living inside its own quotient — and the two named failure modes are exactly of that kind: "declared event absent from the `ere`" is local and can even be erased by ε-normalization, and "`@match` without `@fail`" is about handlers, so two specifications differing only in the handler have identical languages. *Consequence:* Layer 1 is the gate (cheap, non-circular, catches both); Layer 2 is evidence.

**D-13 · Calibration before trust.**
*Chosen because* an instrument that ships without calibration publishes numbers that look like measurement and are not. *Consequence:* eight targets, each produced by an independent route at a named commit, each with its counting rule; a disagreement is a `CalibrationMismatch` resolved by measuring both sides, never by adjusting the component. This is the single most important gate in the change and it is the reason G12 exists as its own task group.

**D-14 · Ad-hoc retirement in two stages, on a written criterion.**
*Chosen because* P3 requires complete deletion but the CI gates are load-bearing. *Consequence:* the criterion is *the ad-hoc dies when the component reproduces its verdict, not when it compiles*; the 13 audit-era files move to `backup/` in this change, and the five CI gates retire in a later cleanup change.

**D-16 · `-core` depends on neither parser, and that is the whole layering rule.**
*Chosen because* the constraint that matters is that the model must not know about `javamop` or
`CrySLParser`; "zero external dependencies" overstates it and contradicts the Phase 0 pom, which
declares Gson because the JSON emitter lives here. *Consequence:* `-core` may carry a serialization
library and JUnit/ArchUnit in test scope; importing either parser into it is the error the rule
exists to prevent, and that is what the ArchUnit rule checks.

**D-17 · The stamp is per corpus, not per run.**
*Chosen because* the input spans two git repositories and one SDK directory, and only one of them
is the repository this change lives in. A table stamped `5fbe8173` beside an upstream-derived number
states a commit unrelated to the artifact that produced it — which is INV-CONF-02's own failure mode
one level up. *Consequence:* `Version` carries a `SourceStamp{repository, commit, data}` per corpus,
and a table reporting specification and rule side by side carries both stamps.

**D-18 · A target whose route is the component's own rule is not a calibration.**
*Chosen because* two of the eight targets as first written could not fail: pairing "by name" is the
rule the component applies, and the `MapOfMonitor` census "by AST proxy" is the proxy the component
implements. *Consequence:* target 6 calibrates against the declared skips of
`order_alphabet_map.csv` (an artifact the component does not produce) and target 8 against the
**regenerated monitors** — which costs one `rv-monitor-generator` pass and buys the only version of
that check that can come out wrong. Target 5 is the upstream M3 denominator (`80` under R1 over the
22 paired rules), routed through the two independent R1 implementations of the adjudication harness;
the committed `constraint_table.csv` (`25/55`, `api30`-anchored human judgement over `jca_android`)
remains a labelled historical reconciliation, not a calibration. Quantities with no independent
route are published as self-consistency checks, labelled, and not counted as calibration.

**D-20 · `h⁻¹(L)` is applied at the lift, not in M2.** (researcher decision, 2026-08-24)
*Chosen because* this document contradicted itself and two task groups implemented opposite readings without knowing: INV-CONF-03 and the API sketch above say `SpecModel.order` is *over `Signature`, not `Label`*, while Data Flow §5 said M2 computes `h⁻¹(L_mop)`. If the preimage happens in M2, the MOP side of the canonical model holds a label language while the CrySL side holds a signature language — the two sides of one model mean different things, and M2 compares automata with disjoint alphabets. *Alternative rejected:* keeping the label language in the model and amending INV-CONF-03; rejected because `SpecModel` is the **canonical** model and an asymmetric `order` is not canonical. *Consequence:* the MOP lift reads the `ere`/`fsm` into a `LabelAutomaton`, builds `InverseMorphism.of(events, site)` and stores the preimage, so M2 compares two real-signature automata directly. Two effects must be handled rather than discovered: the morphism's refusals (`Unknown{OverlappingDispatch}`) now arise **at lift**, so the lift result carries them — and a consumer reading `order` without consulting them reads a language narrower than the file, a narrowing that belongs to the refusal and not to the specification; and `mop.lower` cannot run the preimage backwards, so the `LabelAutomaton` and the morphism are retained on the `-mop` lift result (never on `SpecModel`) for the lowerer. *Measured while implementing it:* the witness this whole line of reasoning rests on did not exist in code — `InverseMorphism.of` grouped events by exact `Signature` equality, under which `IvChainJunction`'s `use` (written with a trailing AspectJ `..`) and `useRandomSpec` (written exactly) never claim the same call. Matching the trailing `..` is what makes D-02's witness real; verified by two routes that no `call(...)` pattern in the 215 files carries a non-trailing `..` or a `*` parameter type.

**D-15 · Shape from `rvsec-mop-extractor`, not code.**
*Chosen because* the sibling module already solves pom layout, CLI wiring, facade and writer conventions inside this reactor. Copying its code would import an unrelated model.

**D-19 · The CrySL façade computes; the EMF route names and locates.**
*Chosen because* the façade `CrySLRule` does not expose what three of the change's own obligations need: CrySL event names and aggregate names (`TransitionEdge.getLabel()` returns `Collection<CrySLMethod>`, which reconstructs method signatures, not labels), `file:line` positions (no position API anywhere in `crysl.rule.*`), and rule validity (`CrySLModelReader` recovers from errors; only `XtextResource.getErrors()` says whether the parse was clean). The metrics need none of that — `order` is an automaton **over `Signature`, not `Label`** (INV-CONF-03), and `CrySLMethod` supplies declaring type, name and parameter types — so the comparison runs entirely on the façade. *Alternative rejected:* pulling event names into the comparison alphabet, which would contradict INV-CONF-03 and re-open the non-disjointness problem at a second level. *Consequence:* `crysl.CryslProvenance` walks the EMF AST (`CrySLStandaloneSetup` → `XtextResourceSet`, positions via `NodeModelUtils`, validity via `resource.getErrors()`) **for reporting and provenance only**; on the MOP side, provenance comes from the parallel text scan (the fork's `getBeginLine()` returns 0/1 and is unusable), and no artifact of the change may instruct an implementer to read names or positions from the façade.

## API Design

```java
// ── rvsec-crysl-core ──────────────────────────────────────────────────────────

/** One stamp per corpus, not one per run: the input spans two git repositories
 *  (rvsec, rvsec-cognicrypt) plus $ANDROID_HOME. A single scalar commit
 *  would attribute an upstream-derived number to a repository that did not produce it. */
public record SourceStamp(String repository, String commit, Instant data) {}
public record Version(String corpus, SourceStamp source) {}

/** Distinct type, not String — INV-CONF-03's ArchUnit rule needs something to key on,
 *  and a rule stated over Map<String, ?> would be unenforceable. */
public record Label(String name) {}

public record Signature(String declaringType, String name,
                        List<String> paramTypes, String returnType) {}

public record Event(Label label, String pointcutText, Set<Signature> signatures,
                    Optional<Guard> guard, int declIndex) {}

public record SpecModel(Version version, String type, Set<ObjectDecl> objects,
                        List<Event> events,              // ORDERED — INV-CONF-03
                        Automaton order,                 // over Signature, not Label
                        List<Constraint> constraints,    // List: same clause, different provenance
                        List<PredicateRef> ensures, requires, negates,
                        Set<Signature> forbidden,
                        Map<Object, Provenance> provenance) {}

/** Closed by construction — INV-CONF-06. Adding a variant is a contract change. */
public sealed interface Unknown
    permits UnrecognizedConstraint, OverlappingDispatch,
            MultiSlicedOrder, UnresolvedSignature, UntranslatableConstraint {
    Provenance site();
}
/** labels MUST be non-empty — INV-CONF-07, enforced in the canonical constructor. */
public record OverlappingDispatch(List<String> labels, Signature signature,
                                  Provenance site) implements Unknown { … }

public enum WitnessStatus { ABSTRACT, CONCRETE }
public record Witness(List<Signature> word, WitnessStatus status,
                      List<Normalization> normalizations,
                      Optional<String> harness) {}   // present iff status == CONCRETE

/**
 * Runs M0 first; if M0 refuses, M1–M4 are not computed (INV-CONF-09).
 * The report header names the oracle's repository, commit and the pairing rule
 * (INV-CONF-11); pairing is by declared type, never by file name.
 *
 * @throws MissingVersionError if any model reaches emission unstamped (INV-CONF-01)
 */
ConformanceReport compare(SpecModel mop, SpecModel rule,
                          AlphabetMap alphabet, ApiIndex android);

/** h : Σ_sig* → Label*, carrying a signature to the concatenation, in declIndex
 *  order, of every label whose pointcut matches it. Returns h⁻¹(L). */
Automaton inverseMorphism(List<Event> events, Automaton labelLanguage);

/** Throws CalibrationMismatch carrying BOTH measurements and BOTH counting rules.
 *  Never mutates the component to agree — INV-CONF-14. */
void calibrate(ConformanceReport report, CalibrationTargets targets)
        throws CalibrationMismatch;

// ── rvsec-crysl-mop ───────────────────────────────────────────────────────────

/** Calls MOPNameSpace.init() before each parse (INV-CONF-05). NOT thread-safe:
 *  JavaMOPParser holds state in a static field, so the parse is never parallelised. */
SpecModel lift(Path mopFile, Version version);

/** SpecModel → MOPSpecFile → DumpVisitor. Never StringBuilder. */
String lower(SpecModel model);

/** Layer 1 = non-normalized AST check (the gate). Layer 2 = product search (evidence). */
RoundTripVerdict gate(String generatedMop, SpecModel rule, ApiIndex android);

// ── rvsec-crysl-crysl ─────────────────────────────────────────────────────────

/** Constructs a NEW CrySLModelReader for this rule alone (INV-CONF-04).
 *  No overload accepts a shared reader; no lexical normalization of any kind. */
SpecModel lift(Path cryslRule, Version version);

/** EMF route, for reporting and provenance only (D-19): event and aggregate names,
 *  file:line via NodeModelUtils, validity via resource.getErrors(). Never feeds
 *  the comparison alphabet, which stays over Signature (INV-CONF-03). */
CryslProvenance provenance(Path cryslRule);

/** Indexes android.jar by class and by (class, method, paramTypes). Index only —
 *  never wired into any parser classpath (INV-CONF-17). */
ApiIndex index(Path androidJar);
```

## Data Flow

1. **Read.** The caller supplies `commit` and the corpus paths. `MopLifter` parses each `.mop` (`MOPNameSpace.init()` first); `CryslLifter` reads each upstream rule with a fresh reader and no normalization. `ApiIndex` indexes `android.jar` once. `AlphabetMap` loads `order_alphabet_map.csv`.
2. **Stamp.** Every `SpecModel` receives `version = {commit, now, corpus}` at construction. An unstamped model cannot reach emission.
3. **Pair.** Specifications pair with rules **by declared type** (INV-CONF-11) — 22 of 24, the two unpaired being exactly the two the alphabet map declares as skips.
4. **M0.** For each specification: index check, accusation-site reachability, signature resolution against `ApiIndex`, plus the non-normalized AST check. A refusal short-circuits: M1–M4 do not run, and the typed `Unknown` is the specification's whole result.
5. **M1–M4.** Each metric runs against the paired upstream rule. M2 compares two automata that are **already over real signatures**: the MOP lift built `h` from the ordered event list and applied `h⁻¹(L_mop)` at read time (D-20), so M2 determinizes the rule automaton and searches the product in both directions, taking ε-erasure decisions from the `disposition` column. M3 classifies by idiom and counts its two ceilings separately. M4 builds both predicate graphs and marks each row derived or inherited.
6. **Calibrate.** The gate checks the eight targets. A mismatch stops publication of the affected metric and is reported with both measurements.
7. **Emit.** JSON, CSV in the committed schemas (re-anchored to `.crysl` references, the committed `.cryptsl`-anchored files remaining readable as history), Markdown evidence — every table carrying its counting rule and the commit.

`mop.lower` is a separate entry point: model → `MOPSpecFile` → `DumpVisitor` → text → Layer 1 gate → Layer 2 evidence.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `CorpusReadError` | an input directory missing or unreadable | fatal before any metric runs | fix the path; nothing partial is emitted |
| `LiftFailure` | a `.mop` or `.crysl` fails to parse | recorded per file with the underlying exception; run continues | expected for the 2 upstream residuals (`OAEPParameterSpec`, `SSLEngine`) — they are findings, not incidents |
| `MissingVersionError` | a model reaches emission unstamped | fatal, by construction | supply `commit`; INV-CONF-01 |
| `Unknown{…}` | a metric cannot decide | **not an error** — a typed result, counted per metric and per corpus | none needed; that is the point |
| `CalibrationMismatch` | a target the component does not reproduce | reported with both measurements and both counting rules; the affected metric is not published | measure both sides and adjudicate with evidence — never adjust the component to agree |
| `NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()` | Guava 19.0 inherited from the reactor root | prevented by `guava.version` override in the parent pom | INV-CONF-16; caught by `DependencyDisciplineTest`, not at runtime |
| `NoClassDefFoundError: scala/Serializable` | `scala.version` overridden to 2.13.14 | prevented: the property is never overridden | INV-CONF-16 |

## Risks / Trade-offs

- **[The corpus moves under the component.]** `jca_android` changed in every prior round. → a `SourceStamp{repository, commit, data}` per corpus on every model and every table; the calibration targets carry the commit they were taken at; gh105 is at 72 of 74 with the remainder blocked on gh104 archival, so the movement in *this* front has stopped.
- **[`CrySLParser 4.0.6` drags Guice 7 and Guava 33.5, and `slf4j-simple` in `compile` scope.]** With the root pin inherited it compiles clean and dies at runtime. → override `guava.version` in the component's parent, exclude `slf4j-simple`; the effect lands in `-crysl` only, so a test asserts the effective pom rather than trusting the build to be silent.
- **[`scala.version` is a trap that looks like the same fix.]** → never overridden; `ptltl` is not excludable; no specification of the current corpus uses `ptltl`, so the constraint protects a future specification. Asserted by `DependencyDisciplineTest`.
- **[The reader leaks scope, and the leak is invisible.]** It both hides a defect and creates one. → fresh reader per rule with no sharing option, plus an order-invariance test that shuffles the rules and asserts 47 of 49 every time.
- **[All five metrics are structural, and structure does not see behaviour.]** Measured twice over: the `KeyGeneratorSpec` whose `ORDER` is equivalent and whose monitor accuses anyway, and the two stream specifications silent on their own violating traces. → the limitation is *published*, not mitigated: every M2 verdict carries the `M2-decl` label and the statement that it says nothing about what the monitor accuses; the behavioural half is the gh104 harness.
- **[The instrument could be tuned until it agrees with the targets.]** The cheapest way to pass a calibration gate is to break the instrument. → INV-CONF-14 makes a mismatch a finding with both sides measured; the gate reports, it does not reconcile.
- **[Retiring a CI gate too early loses coverage silently.]** → two-stage retirement on a written criterion; the five CI gates stay green through this change.
- **[The component's entire contract is Java tests, and CI runs the reactor with `-DskipTests`.]** `.github/workflows/ci.yml:30` builds with `-DskipTests`; the only module whose tests run is dexlib2 `grammar-tests`, via an explicit `-DskipTests=false` step at `:44`. So the 17 invariant tests, the ArchUnit rules, the 40-shuffle order-invariance test and the calibration gate would be a **local-only green** — the same false green this repository has already shipped twice. → add a CI step for the four new modules in the shape of the existing `grammar-tests` step. It is the cheapest High mitigation in the change. See `risk-register.md` RISK-001.
- **[The oracle and the SDK live outside the repository.]** `rvsec-cognicrypt` is a separate git repo and `android.jar` comes from `$ANDROID_HOME`; the CI checkout has neither. Even with the step above, the oracle-dependent tests cannot run in CI. → split the suite: corpus-only tests run in CI; oracle-dependent tests are tagged and run locally with a documented setup, and the split is declared rather than discovered. See `risk-register.md` RISK-002.
- **[`Unknown` could become a dumping ground.]** → sealed hierarchy, five permits, per-metric counts emitted beside every coverage figure so a rising refusal rate is visible rather than absorbed.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | model shape, automata (determinization, minimization, product, `h⁻¹`), idiom recognisers, the `Unknown` hierarchy, `Witness` invariants | JUnit 5, no I/O; synthetic automata with closed-form answers, including the non-deterministic `ORDER con, a?, a` | ~80 |
| Integration | lift over all 215 `.mop` and the 49 upstream rules; M0–M4 end to end on named specifications; round-trip lower→lift; emitters against the committed CSV schemas | real corpora on disk, read-only | ~40 |
| Invariant | one test per `INV-CONF-01`…`INV-CONF-17`, each asserting the *violation* is refused | JUnit + ArchUnit (INV-CONF-03 forbids the `Map<Label,Set<Signature>>` shape; INV-CONF-04 forbids a reader held in a field) | 17 |
| Calibration | the eight targets, each against a route the component does not produce (target 8 regenerates the monitors; target 6 reads the alphabet map's declared skips, stated as header prose rather than as rows) | `CalibrationGateTest` at pinned per-corpus stamps | 8 |
| Order-invariance | 40 shuffled read orders of the 49 upstream rules, asserting 47 every time | property-style repetition | 1 (×40) |
| Reactor | the four poms build; effective `guava.version` is 33.5.0-jre and `scala.version` is 2.11.12; `ptltl` present; `slf4j-simple` absent; JUnit 5 and ArchUnit pinned in the component's parent, since the reactor root manages JUnit 4 | Maven integration test | ~5 |
| CI | the four new modules' tests actually run in CI, with the oracle-dependent subset tagged and excluded there rather than silently skipped | a workflow step in the shape of the existing `grammar-tests` step | 1 step |
| Parity (Python) | the audit-era comparators are gone from `audit/` and present in `backup/`; no dangling references | `tests/parity/test_gh106_retirement.py`, run with `--import-mode=importlib -o "addopts="` | ~3 |

## Open Questions

1. **The `KeyGeneratorSpec` M2 verdict must be recomputed.** Its `ere` changed between the commit the published verdict was computed at and today (`(g3* g1+ | g3* g2+) ((init gk1) | gk1)` → `… (((init | initRandom | initRandomSize | initRandomSpec) gk1) | gk1)`), and the alphabet map already maps the four `init*` to the rule's `i1`…`i5`. The recomputation is work for the component, in G10; what is open is whether the verdict changes.
2. **Resolved (2026-08-24): the upstream pairing rule is by declared type.** The rule's `SPEC` FQN pairs against the type of the specification's declared parameter (the pointcut's declaring type for the two parameterless specs); measured at 22 of 24 with the same two skips, including the case file-name pairing cannot resolve (`SecretKeySpec.mop` → `SecretKey.crysl`, `SecretKeySpecSpec.mop` → `SecretKeySpec.crysl`). Kept here because any number published under the old by-name pairing must be re-stamped before reuse.
3. **The counting rule for overlapping pointcut pairs is unreconstructed.** Two rules were reconstructed and give `15/32` and `22/40`; the previously published `10/26` matches neither. Until a rule that reproduces it is written, the component publishes the pair of bounds under both declared rules rather than a single figure.
4. **`152 × 141`** — the two sides of the resolved-event count disagreed over the abandoned `api30` corpus, and the `141` side is superseded by the upstream remeasurement (215 lines, `diff`-free, decomposing `175/29/5/6` against `android.jar`). What stays open is whether the other side's arithmetic survives the oracle switch; the component recomputes both over upstream.
5. **The four parcels of the M4 decomposition (`fiéis + fiação + substrato + cobertura`) need a re-census.** The substrate parcel is measurably paid; the other three depend on the judgement columns, which is exactly what giving them a derivable home resolves. Until then the structure is published and the four scalars are not.
