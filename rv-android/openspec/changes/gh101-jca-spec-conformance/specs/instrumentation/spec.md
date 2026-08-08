## Purpose

This delta governs what a JCA specification set is allowed to contain, what relates the two sets to one another, and what makes a predicate written by one specification and read by another a contract rather than a convention.

A CrySL rule has parts that depend on the platform and parts that do not. The membership constraints — which algorithms, modes, paddings, protocols and key sizes a provider offers — are platform-dependent, and they are exactly what the MetaCrySL derivation recomputes for a given API level. The order of operations, the predicates a rule ensures and requires, and the negations it declares are properties of the API's semantics, not of the platform that ships it. This is why the `jca_android` set was produced by derivation instead of a second hand translation, and why the derivation itself may only touch allow-lists. That constraint governs how the derived set is *produced*, and it is stated here so that a later derivation cannot erode it by degrees.

It does not, however, govern where a repair may land, and the distinction is the crux of this delta. A defect in the platform-independent part of a specification — a binding that names the wrong variable, an event absent from its own automaton, a `Property` constant copied from a neighbouring specification — is by that same reasoning a defect in **both** sets, since it sits in the portion the derivation copies unchanged. Repairing both would be the tidier outcome. It is nonetheless forbidden here, because the `jca` set is the one that produced published measurements, and a specification set that has been measured and reported is an experimental instrument: changing it silently invalidates the reproduction of results computed with it. The `jca` set is therefore frozen, the repairs land in the derived set alone, and the sets are allowed to diverge outside their allow-lists for the first time.

What that costs has to be carried explicitly rather than assumed away. The defects stay standing in the set that produced the published numbers, so those numbers remain reproducible without becoming correct. And the two sets stop differing along a single axis: a difference in outcome between them used to be attributable to the platform allow-list alone, and can now come from the allow-list or from a repair present in one set only, with no way to separate the contributions after the fact. Divergence between the sets consequently stops being forbidden and becomes something enumerated — every hunk outside an allow-list carries a recorded reason — because an unenumerable difference is precisely what would make the two sets incomparable rather than merely differently scoped.

The third concern is the predicate graph. Specifications communicate through a static map keyed by `Property` constants: one specification writes that a key was generated or a value randomised, another reads that fact to decide whether a later call is a misuse. Nothing links the write to the read. The constant is an enum member on both sides, so a specification that writes `GENERATED_KEY_MANAGERS` where it meant the trust-manager constant compiles, runs, and reports nothing — and two specifications do exactly that today. Because a read of an absent key returns false, the failure mode is not a crash but a quiet accusation or a quiet silence, depending on the direction of the guard. The graph is also strikingly one-sided: 83% of the CrySL `ENSURES` clauses have a written counterpart and only 22% of the `REQUIRES` have a reader, which means the translation produces predicates with fidelity and then rarely consumes them.

A word on what conformance to the derived rules can and cannot mean. The `android` profile of the derivation models **availability**, not recommendation: the API 30 rule for `MessageDigest` admits `MD5` and `SHA-1` because the platform publishes them. Aligning a specification to its derived rule can therefore make it accept more, not less, and a fall in the number of reported violations is not evidence that the analysed code improved. Any reading of results across the two sets has to carry that caveat, which is why it is written into the requirement rather than left to a report.

## Data Contracts

### Input

- `mop_specs_dir: Path` — the directory of `.mop` files selected by `ExperimentConfig.specification_set` (source: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}`)
- `generated_rules_dir: Path` — the 33 generated `.cryptsl` rules for API 30 (source: the MetaCrySL tree, read-only)
- `transformation: String` — the `Cipher.getInstance` argument evaluated by `isValid` (source: the monitored application at runtime)

### Output

- `conformance_record` — per specification: the anchoring generated rule, the verdict (adapted, verbatim-uncontradicted, no-anchor), and the evidence
- `predicate_inventory` — every `ExecutionContext` write, read and removal across the set, with file, line, specification, event and the `Property` constant involved
- `divergence_record` — every hunk by which `jca_android` differs from `jca` outside an allow-list, with the reason it exists and the task that introduced it

### Side-Effects

- **[Runtime]**: `ExecutionContext.setProperty` stores a strong reference in a static map, keyed by object identity; the predicate graph's edges are these entries
- **[Generation]**: an event absent from its specification's `fsm` receives a transition row that sends every state to `fail`

### Error

- `InvalidSequenceOfMethodCalls` — emitted spuriously today when a bound event is absent from the automaton
- `ConfigurationError` — raised by `RVGeneratorConfig` when the selected specification directory is missing or empty

## Invariants

- **INV-INS-109**: The `jca` specification set and the `CipherTransformationUtil` it delegates to MUST remain byte-identical to their state at this change's base commit, and every divergence between `jca_android` and `jca` outside allow-list content MUST appear in the divergence record with its reason. An unrecorded divergence is a defect; a recorded one is a deliberate repair confined to the derived set. Any edit reaching the frozen paths fails the check regardless of its merit.

  The check bounds what it can establish, and the bound is part of the invariant rather than a caveat on it. Byte-identity of the frozen paths, and of the monitor generated from them, does **not** establish that the frozen set behaves as it did: shared runtime code the specifications call is outside both, so a repair there changes behaviour with every mechanical check still passing. Such a repair is governed by the admissibility conditions above, and its effect on the frozen set MUST be enumerated site by site in the change's records. Establishing the effect empirically would require the corpus re-measured, which this change does not do.

- **INV-INS-110**: An event that appears in a specification's event list MUST appear in that specification's `fsm` or `ere`. An event bound but absent from the automaton receives a transition row to `fail` from every state, which turns the specification into an unconditional accuser.

- **INV-INS-111**: Every `Property` constant written by any specification MUST be read by at least one specification, or MUST be recorded in the deliberate-omission list with its reason. A constant that is neither read nor recorded is a silent defect, not a spare.

- **INV-INS-112**: The `Cipher` transformation tables consulted by a specification set MUST originate in the same derivation that produced that set's rules, and each set MUST reach them without any runtime selection: the specification names the utility it calls. A hand-maintained table that duplicates a derived rule is inadmissible regardless of whether it currently agrees, and a shared table chosen by a mutable switch is inadmissible because it would place the frozen set's verdict under the control of state set elsewhere.

- **INV-INS-114**: A specification's events MUST be granular enough to bind every argument its rule's clauses quantify over. Fusing several method signatures into one pointcut is admissible only where no `REQUIRES`, `ENSURES`, `NEGATES` or `CONSTRAINTS` clause refers to an argument the fusion leaves unbound. Fusion is lossless for the `ORDER`, which names only the rule's aggregate, and lossy for everything that names its individual events — which is why a fused specification can look well-formed and still be unable to state most of its rule. The converse also binds: an event that carries no binding and no body another event does not already carry MUST NOT be split out, because the alphabet is a scarce resource under INV-INS-115.

- **INV-INS-115**: A specification's event count MUST be verified to generate. The monitor generator computes, for the `fail` category of any specification declaring an `@fail` handler, a coenable set of exactly `n × (2ⁿ − 1)` members over an alphabet of `n` events; measured on this machine, 17 events generate in 53 s, 18 raise `StackOverflowError` in the enable-set parser, and 24 exceed Java's maximum `String` length and cannot be built at all. The notation does not change this — `ere`, `ltl` and `ptltl` are rewritten into `fsm` and reach the same computation. A specification MUST therefore be generated end to end before its alphabet is accepted, and a design that cannot be generated MUST be recorded as such rather than left in the plan.

- **INV-INS-113**: Every `.mop` in the `jca_android` set MUST carry a conformance verdict against the generated rules for its target API level: anchored to a named rule, or declared uncontradicted with the rule that was checked, or declared to have no anchor with the reason. A file with no verdict is unverified, not verbatim.

## ADDED Requirements

### Requirement: Derivation Provenance of the Android Specification Set

The `jca_android` specification set SHALL be a derivation of the `jca` set against generated CrySL rules for a declared Android API level. The derivation itself SHALL alter allow-list content and nothing else: the platform-dependent portion of a CrySL rule is the membership constraint, while `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe API semantics and do not vary with API level.

This constrains how the derived set is produced, not what may later be repaired in it. Repairs to the platform-independent portion are governed by `Requirement: The Java SE Specification Set Is Frozen`, which confines them to the derived set and requires each resulting divergence to be recorded.

Each specification in the derived set SHALL carry a conformance verdict against the generated rules: **anchored** (a named generated rule contradicted the `jca` allow-list and the allow-list was changed to follow it), **uncontradicted** (the generated rule was checked and does not contradict the inherited allow-list), or **no anchor** (no generated rule corresponds, with the reason stated). Thirteen files are currently carried verbatim and only three of them state which of these applies.

The derived profile models **availability, not recommendation**. Aligning to it can widen an allow-list — the API 30 `MessageDigest` rule admits `MD5` and `SHA-1`. Any report comparing violation counts across the two sets MUST carry that caveat, because a lower count under the derived set is not evidence of better analysed code.

#### Scenario: Derivation alters something other than an allow-list

- **WHEN** a derivation run against a new API level would change an event, a binding, a pointcut, an `fsm` row, a handler, or an `ExecutionContext` call
- **THEN** the derivation MUST be treated as defective rather than the specification
- **AND** the change MUST NOT be accepted as derived output

#### Scenario: Verbatim file carries a verdict

- **WHEN** a `.mop` in the derived set is carried over from `jca` without an allow-list change
- **THEN** the conformance record MUST state whether the corresponding generated rule was checked and found not to contradict it, or that no generated rule corresponds
- **AND** "carried verbatim" alone MUST NOT be accepted as a verdict

#### Scenario: A derived rule widens an allow-list

- **WHEN** a generated rule admits an algorithm the `jca` allow-list rejects, and the derived set follows the rule
- **THEN** the conformance record MUST note that the derived profile models availability rather than recommendation
- **AND** any comparison of violation counts across the sets MUST carry that caveat

### Requirement: The Java SE Specification Set Is Frozen

The `jca` specification set, together with the `CipherTransformationUtil` its `CipherSpec` delegates to, SHALL remain byte-identical to its state at this change's base commit. A specification set that has produced published measurements is an experimental instrument, and altering it retroactively invalidates the reproduction of every result computed with it.

Corrections to the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, or an `ExecutionContext` read or write — SHALL therefore be applied to the `jca_android` set alone, even though the same defect is present in `jca`. Each such correction SHALL be entered in the divergence record naming the hunk, the reason, and the task that introduced it. Divergence between the sets outside allow-lists is the expected outcome; divergence that is not recorded is not.

Two consequences SHALL be carried in the change's records rather than left to be inferred. The `jca` set knowingly retains its defects and the spurious reports they produce, so results measured under it are reproducible without being correct. And a difference in outcome between the two sets can no longer be attributed to the platform allow-list alone, because it may equally arise from a repair present in one set only; no measurement separates the two contributions after the fact.

The freeze governs what the instrument **states** — the specifications and the transformation tables the frozen `CipherSpec` delegates to — and not the runtime it executes on. Additive changes to shared Java are admissible where the frozen set cannot observe them at all: a new `Property` constant that no `jca` specification references, or a new class that no `jca` specification imports, leaves the frozen set's generated monitor unchanged.

A **repair to shared runtime code the frozen set does reference** is also admissible, under two conditions and not otherwise. The repair MUST apply identically to both sets — shared code MUST NOT branch on the active specification set, because that would place the frozen set's verdict under state set outside its own specification, which is the hazard INV-INS-112 exists to prevent. And its effect on the frozen set MUST be enumerated site by site in the change's records rather than assumed absent. A defect in the machinery is not made correct by having been present when a measurement was taken, and a rule forbidding its repair would forbid repairing the weaver as well.

The distinction is between a correction of what counts as a misuse, which is confined to the derived set, and a correction of the mechanism that decides it, which is not confinable and is therefore recorded.

#### Scenario: Correction reaches the frozen set

- **WHEN** a layer-2 correction is applied to a file under `jca/`, or to `CipherTransformationUtil.java`
- **THEN** the freeze check MUST fail against the base commit
- **AND** the correction MUST be moved to `jca_android` alone, however clearly it repairs a real defect

#### Scenario: Correction lands in the derived set

- **WHEN** a binding defect present in both sets is corrected in `jca_android` only
- **THEN** the freeze check MUST pass
- **AND** the divergence record MUST gain an entry naming the hunk and the reason
- **AND** the `jca` set MUST retain the defect, recorded as knowingly retained

#### Scenario: Divergence appears without a record entry

- **WHEN** the two sets differ outside allow-list content in a hunk that no divergence-record entry names
- **THEN** the check MUST fail
- **AND** the hunk MUST either gain an entry with its reason or be reverted

#### Scenario: Shared Java gains a symbol the frozen set cannot observe

- **WHEN** `Property` gains a constant, or `rvsec-core` gains a class, that no `jca` specification references or imports
- **THEN** the freeze check MUST pass
- **AND** the monitor generated from the `jca` set MUST be unchanged, which is what makes the addition admissible

#### Scenario: Shared runtime code the frozen set references is repaired

- **WHEN** a defect is corrected in `rvsec-core` code that specifications of both sets call
- **THEN** the repair MUST apply identically to both sets, with no branch on the active specification set
- **AND** the sites at which the frozen set's behaviour changes MUST be enumerated in the change's records
- **AND** the freeze check passing MUST NOT be reported as evidence that the frozen set's behaviour is unchanged

### Requirement: Event Membership in the Specification Automaton

Every event declared in a specification SHALL appear in that specification's `fsm` or `ere`. The monitor generator assigns an event absent from the automaton a transition row that moves every state to `fail`, so such an event does not merely go unmodelled — it makes the specification accuse unconditionally.

This makes automaton membership part of any binding correction rather than a follow-up: repairing the binding of an event that is absent from the automaton converts a dead event into an unconditional accuser. `g3` in `TrustManagerFactorySpec` and `unsafe_protocol` in `SSLContextSpec` are both in this state today.

#### Scenario: Bound event absent from the automaton

- **WHEN** a specification declares an event that appears in no row of its `fsm` or `ere`
- **THEN** the specification MUST be treated as defective
- **AND** the correction MUST add the event to the automaton in the same change that repairs its binding

#### Scenario: Binding repaired without automaton membership

- **WHEN** an event's binding is corrected while the event remains absent from the automaton
- **THEN** every call outside the allow-list MUST be expected to emit a spurious `InvalidSequenceOfMethodCalls`
- **AND** the change MUST NOT be accepted in that state

#### Scenario: A fused pointcut leaves a required argument unbound

- **WHEN** a specification collapses several of its rule's events into one pointcut, and a `REQUIRES`, `ENSURES`, `NEGATES` or `CONSTRAINTS` clause quantifies over an argument the fusion leaves unbound
- **THEN** the fusion MUST be replaced by one event per distinct binding profile — the set of arguments the clauses mentioning that event need bound — each taking exactly the transitions of the fused event it replaces
- **AND** the automaton's accepted language MUST be unchanged, only its alphabet refined
- **AND** signatures that share a binding profile and a body MUST stay fused, since the weaver resolves overloads on owner, name, return type and parameter types, so splitting them binds nothing new and spends alphabet that INV-INS-115 makes scarce
- **AND** where a fusion binds the varying argument as `Object+` and discriminates by type in the body, the fused signatures MUST share an arity, because `args(a, b, third, ..)` requires arity ≥ 3 and drops a shorter overload out of the automaton entirely, and none of the varying positions may be primitive, because `Object+` rejects primitives
- **AND** each resulting pointcut MUST be verified against the target API's real overload set, showing that the candidates jointly cover every signature the rule names and are pairwise disjoint

#### Scenario: Two events match the same call

- **WHEN** two pointcuts in one specification both match a single call, as an argument-less signature and the same signature with `(..)` do
- **THEN** the specification MUST be treated as defective, because one call takes two transitions
- **AND** the narrower pointcut MUST be made disjoint from the wider one

### Requirement: Cipher Transformation Tables of the Derived Set

The `Cipher` transformation tables consulted by the derived set — the admissible algorithms, their modes, and per mode the admissible paddings — SHALL originate in the generated CrySL rule for the declared API level, and SHALL be reached by `jca_android/CipherSpec.mop` naming its own utility rather than by any runtime selection over a shared one.

`CipherSpec` is the only specification in the set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java, where the tables are method locals covering two algorithm families. The derived rule admits eight, and the effect is a set that contradicts itself, generating keys for algorithms whose use it reports as misuse. A hand-maintained table is inadmissible even where it currently agrees with the rule, because agreement maintained by hand is the second translation the derivation exists to eliminate.

Selection by the *specification* rather than by the *runtime* is what keeps the frozen set frozen. A shared utility parameterised by the active set would place the `jca` verdict under the control of state set elsewhere, so that a defect in the selection would alter published behaviour; a distinct utility named by the derived specification alone cannot. The existing class is consequently left untouched, and the parsing it already performs correctly — splitting a transformation into algorithm, mode and padding — is reused rather than restated, so only the tables and the admissibility decision are new.

#### Scenario: Android set evaluates an algorithm its own rule admits

- **WHEN** the `jca_android` set is active and an application calls `Cipher.getInstance("ChaCha20/NONE/NoPadding")`, an algorithm the generated API 30 rule admits
- **THEN** the derived utility MUST be the one consulted
- **AND** the call MUST NOT be reported as a misuse
- **AND** the set MUST NOT accept generating a key for an algorithm whose use it rejects

#### Scenario: Java SE set behaviour is unchanged

- **WHEN** the `jca` set is active
- **THEN** `isValid` MUST return the same verdict it returns today for every transformation
- **AND** that MUST hold because the class it calls was not modified, not because a test asserts it

#### Scenario: A shared table selected at runtime is proposed

- **WHEN** an implementation would give both sets one utility whose tables are chosen by the active specification set
- **THEN** it MUST be rejected under INV-INS-112
- **AND** the reason MUST be recorded as the frozen set's verdict depending on state set outside its own specification

### Requirement: Predicate Contract Between Specifications

A `Property` constant written through `ExecutionContext` by one specification and read by another SHALL be treated as a contract with two enforced properties: every constant written is read somewhere or recorded as a deliberate omission with its reason, and the inventory of writes and reads is a versioned artefact rather than an ad-hoc derivation.

Nothing links the constant written to the constant read. Both sides are enum members, so a specification that writes a neighbouring specification's constant compiles and runs and reports nothing; two specifications do this today. A read of an absent key returns false, so the failure is quiet in both directions — a missing write turns a guarded accusation into an unconditional one, and a wrong write turns a real accusation into silence.

The store SHALL identify objects the way the monitor index identifies them: **by identity**. JavaMOP keys a monitor by `System.identityHashCode` confirmed with `==`, so it never conflates two alike instances; a predicate store keyed by `equals` does, and the two halves of one mechanism then disagree about what "the same object" means. The consequence is not academic and runs in all three directions: a write over an object equal to a stored one adds nothing, so two monitors share a mark; a `REQUIRES` succeeds for an object that no monitored sequence produced, provided an equal one was; and a removal in one monitor's `@fail` takes another monitor's mark. It bites wherever `equals` is value-based — `Key` implementations, `String`, boxed primitives — and is invisible wherever it is not, which is why it survived a translation that is otherwise careful.

Predicates that cannot be expressed by this mechanism SHALL be recorded rather than approximated. A predicate asserting **provenance** over a primitive remains inexpressible under identity keying, for a different reason than under `equals`: a boxed primitive has no stable identity across boxing operations, so `randomized[lSeed]` — that a `long` came from a CSPRNG — is asserted of a box that the next autoboxing of the same value does not reproduce. The residual unsoundness on the write side narrows to the `Integer` cache, where equal small values genuinely *are* one object, so marking one still marks every equal literal in the process.

The contract binds in both directions, and the converse failure is the more damaging one. A constant written and never read is inert: nothing consumes it, so nothing misreports because of it. A constant *read* and never written is the opposite, because a requirement that cannot be satisfied is not silent — a read placed in an event body reports whenever it fails, which is exactly why reads are placed there rather than in a `condition(...)`. So a `REQUIRES` whose producing rule has no specification in the set MUST NOT be given a reader on the strength of the rule alone: the rule names a producer this set does not model, and transcribing only the consumer half turns every conforming execution into a reported misuse. Such an edge SHALL be recorded as unclosable, naming the rule that would have produced it, so that the gap is attributable to a missing specification rather than mistaken for a translation defect.

#### Scenario: Constant written and never read

- **WHEN** the inventory shows a `Property` constant written by at least one specification and read by none
- **THEN** the guard MUST fail
- **AND** the constant MUST either gain a reader or be recorded in the deliberate-omission list with its reason

#### Scenario: Specification writes a neighbouring specification's constant

- **WHEN** a specification writes a `Property` constant that does not correspond to the predicate its CrySL rule ensures
- **THEN** the guard MUST detect the mismatch from the inventory
- **AND** the defect MUST NOT depend on code review to be caught

#### Scenario: Two equal objects are monitored separately

- **WHEN** an application constructs two `SecretKeySpec` instances with the same key material and algorithm, one through a conforming sequence and one through a violating branch
- **THEN** the store MUST mark only the instance the conforming sequence produced
- **AND** a later `Cipher.init` over the other instance MUST NOT be validated by the first
- **AND** a `@fail` unmarking either MUST leave the other's mark untouched

#### Scenario: A predicate's whole set is deleted

- **WHEN** a specification's `@fail` removes a `Property` without naming the object it wrote
- **THEN** every other monitor's mark for that predicate is erased as well
- **AND** the removal MUST name the object, which requires the specification to hold it in a monitor field

#### Scenario: Required predicate has no producer in the set

- **WHEN** a rule's `REQUIRES` names a predicate whose producing rule has no specification in the set
- **THEN** the requirement MUST be recorded as unclosable, naming the producing rule that is absent
- **AND** a reader MUST NOT be added against a predicate no specification in the set writes, because a body read of an unwritten predicate reports on every execution

#### Scenario: Inexpressible predicate is recorded, not approximated

- **WHEN** a CrySL predicate asserts provenance over a primitive value
- **THEN** it MUST be recorded as inexpressible with the reason, together with the unsoundness of the corresponding write side
- **AND** it MUST NOT be approximated by a value-keyed entry that would conflate unrelated equal values

## MODIFIED Requirements

### Requirement: Specification Set Support (FR03)

The system MUST support multiple, independent specification sets for different API monitoring domains. Each specification set represents a collection of `.mop` files targeting a specific category of API usage patterns. The system MUST ensure that specification sets are never mixed within a single experiment run.

Four predefined specification sets are supported:

1. **JCA (Java Cryptography Architecture)** -- 23 specifications derived from CrySL rules, detecting misuses of cryptographic APIs. This set is frozen against the measurements published from it:
   - `CipherSpec.mop`: Cipher initialization and usage sequences. Unlike the other 22, it carries no allow-list of its own and delegates its transformation constraints to shared Java (`rvsec-core`), naming the utility it calls
   - `MessageDigestSpec.mop`: Hash algorithm validation
   - `SSLContextSpec.mop`: TLS protocol validation
   - `SecretKeySpecSpec.mop`: Key specification validation
   - `KeyGeneratorSpec.mop`: Key generation operation sequences
   - `SignatureSpec.mop`: Digital signature operation sequences
   - `MacSpec.mop`: Message Authentication Code operation sequences
   - `KeyStoreSpec.mop`: Keystore operation sequences
   - And 15 additional specifications covering SecureRandom, PBE, IvParameterSpec, etc.

2. **JCA Android** -- the same 23 specifications, derived against generated CrySL rules for a declared Android API level. The derivation altered allow-list content only. Repairs to the platform-independent portion land here alone, because the `jca` set is frozen, and each resulting divergence is entered in the divergence record with its reason (INV-INS-109). Its `CipherSpec` names its own transformation utility, whose tables come from the generated `Cipher` rule.

3. **Generic (FSM)** -- 118 specifications from the JavaMOP specification database, detecting general API pattern violations such as Iterator hasNext/next ordering, stream resource management, and collection modification during iteration.

4. **Generic (new)** -- 27 curated specifications with descriptive names, such as `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`.

The specification set is determined by the `specification_set` field in `ExperimentConfig`, which maps to a subdirectory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The `get_monitored_operations_config()` JIT method resolves the mapping:
- `"jca"` maps to `{mop_base_dir}/jca/`
- `"jca_android"` maps to `{mop_base_dir}/jca_android/`
- `"generic"` maps to `{mop_base_dir}/generic/`
- `"custom"` uses `custom_specs_dir` (MUST be explicitly provided)

The derived set MUST be selectable by name. Reaching it through `"custom"` with a hand-written path was tolerable while it was identical to `jca` outside allow-lists; it is not once it is the only set carrying the corrections, because a mistyped path then silently selects the uncorrected instrument.

When no `mop_specs_dir` is explicitly provided to `RVGeneratorConfig`, it defaults to the JCA specification set.

Specifications within a set communicate through `Property` constants written and read via `ExecutionContext`. Those constants form a contract across specifications, governed by `Requirement: Predicate Contract Between Specifications`, not a per-specification implementation detail.

#### Scenario: JCA specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **AND** the directory MUST contain 23 `.mop` files

#### Scenario: JCA Android specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain 23 `.mop` files and no `.aj` file
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: Derived set diverges from the frozen set

- **WHEN** the diff between the two set directories is taken after the corrections have landed
- **THEN** hunks outside allow-list content MUST be present, since the repairs are confined to the derived set
- **AND** every such hunk MUST be named by an entry in the divergence record

#### Scenario: Generic specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"generic"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`

#### Scenario: Custom specification set with valid directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` points to a directory containing `.mop` files
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` set to `custom_specs_dir`
- **AND** the directory MUST be validated to contain at least one `.mop` file

#### Scenario: Custom specification set without directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` is `None`
- **THEN** `get_monitored_operations_config()` MUST raise a `ConfigurationError` with message indicating that `custom_specs_dir` is required

#### Scenario: Invalid specification set value

- **WHEN** `ExperimentConfig.specification_set` is set to a value not in the supported set
- **THEN** `ExperimentConfig.validate()` MUST raise a `ValueError` with message listing the valid specification sets

#### Scenario: Default specification set when using RVGeneratorConfig directly

- **WHEN** `RVGeneratorConfig` is created with only `rvsec_root` (no explicit `mop_specs_dir`)
- **THEN** `mop_specs_dir` MUST default to `{rvsec_root}/rvsec/rvsec-mop/src/main/resources/jca/`
