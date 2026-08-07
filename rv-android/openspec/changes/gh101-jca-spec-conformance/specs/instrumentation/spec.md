## Purpose

This delta governs what a JCA specification set is allowed to contain, what relates the two sets to one another, and what makes a predicate written by one specification and read by another a contract rather than a convention.

A CrySL rule has parts that depend on the platform and parts that do not. The membership constraints — which algorithms, modes, paddings, protocols and key sizes a provider offers — are platform-dependent, and they are exactly what the MetaCrySL derivation recomputes for a given API level. The order of operations, the predicates a rule ensures and requires, and the negations it declares are properties of the API's semantics, not of the platform that ships it. This is why the `jca_android` set was produced by derivation instead of a second hand translation, and why the only admissible difference between `jca` and `jca_android` is the allow-list. That property is not an accident of how the derivation was run; it is the guarantee that makes the two sets comparable, and it is stated here so that a later change cannot erode it by degrees.

The corollary matters as much as the rule. A defect in the platform-independent part of a specification — a binding that names the wrong variable, an event absent from its own automaton, a `Property` constant copied from a neighbouring specification — is a defect in **both** sets, and correcting it in one alone would break the comparability the derivation exists to provide. Corrections of that kind therefore land in both sets identically, and the diff between the sets is checked mechanically after each one.

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

### Side-Effects

- **[Runtime]**: `ExecutionContext.setProperty` stores a strong reference in a static map; the predicate graph's edges are these entries
- **[Generation]**: an event absent from its specification's `fsm` receives a transition row that sends every state to `fail`

### Error

- `InvalidSequenceOfMethodCalls` — emitted spuriously today when a bound event is absent from the automaton
- `ConfigurationError` — raised by `RVGeneratorConfig` when the selected specification directory is missing or empty

## Invariants

- **INV-INS-109**: The diff between the `jca` and `jca_android` specification sets MUST consist of allow-list differences only. Any divergence in events, bindings, pointcuts, `fsm`/`ere`, `@match`/`@fail` handlers, or `ExecutionContext` reads and writes is a defect, whichever set introduced it.

- **INV-INS-110**: An event that appears in a specification's event list MUST appear in that specification's `fsm` or `ere`. An event bound but absent from the automaton receives a transition row to `fail` from every state, which turns the specification into an unconditional accuser.

- **INV-INS-111**: Every `Property` constant written by any specification MUST be read by at least one specification, or MUST be recorded in the deliberate-omission list with its reason. A constant that is neither read nor recorded is a silent defect, not a spare.

- **INV-INS-112**: The `Cipher` transformation tables MUST be selected by the active specification set and MUST originate in the same derivation that produced that set's rules. A hand-maintained table that duplicates a derived rule is inadmissible regardless of whether it currently agrees.

- **INV-INS-113**: Every `.mop` in the `jca_android` set MUST carry a conformance verdict against the generated rules for its target API level: anchored to a named rule, or declared uncontradicted with the rule that was checked, or declared to have no anchor with the reason. A file with no verdict is unverified, not verbatim.

## ADDED Requirements

### Requirement: Derivation Provenance of the Android Specification Set

The `jca_android` specification set SHALL be a derivation of the `jca` set against generated CrySL rules for a declared Android API level, and its **only** admissible divergence from `jca` SHALL be the allow-list content of its specifications. The platform-dependent portion of a CrySL rule is the membership constraint; `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe API semantics and do not vary with API level, so they MUST remain identical across the two sets.

This is a property to preserve, not a gap to close. It is what allows results measured under the two sets to be compared as the same analysis over different platform assumptions rather than as two different analyses.

Each specification in the derived set SHALL carry a conformance verdict against the generated rules: **anchored** (a named generated rule contradicted the `jca` allow-list and the allow-list was changed to follow it), **uncontradicted** (the generated rule was checked and does not contradict the inherited allow-list), or **no anchor** (no generated rule corresponds, with the reason stated). Thirteen files are currently carried verbatim and only three of them state which of these applies.

The derived profile models **availability, not recommendation**. Aligning to it can widen an allow-list — the API 30 `MessageDigest` rule admits `MD5` and `SHA-1`. Any report comparing violation counts across the two sets MUST carry that caveat, because a lower count under the derived set is not evidence of better analysed code.

#### Scenario: Set diff contains an events-section change

- **WHEN** the diff between `jca/SSLContextSpec.mop` and `jca_android/SSLContextSpec.mop` contains a change outside the allow-list — an event, a binding, a pointcut, an `fsm` row, a handler, or an `ExecutionContext` call
- **THEN** the parity check MUST fail
- **AND** the change MUST be applied to both sets or reverted from both, never left divergent

#### Scenario: Verbatim file carries a verdict

- **WHEN** a `.mop` in the derived set is carried over from `jca` without an allow-list change
- **THEN** the conformance record MUST state whether the corresponding generated rule was checked and found not to contradict it, or that no generated rule corresponds
- **AND** "carried verbatim" alone MUST NOT be accepted as a verdict

#### Scenario: A derived rule widens an allow-list

- **WHEN** a generated rule admits an algorithm the `jca` allow-list rejects, and the derived set follows the rule
- **THEN** the conformance record MUST note that the derived profile models availability rather than recommendation
- **AND** any comparison of violation counts across the sets MUST carry that caveat

### Requirement: Platform-Independent Corrections Apply to Both Specification Sets

A defect in the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, or an `ExecutionContext` read or write — SHALL be corrected in **both** specification sets, identically and in the same change.

Correcting one set alone produces a divergence that INV-INS-109 forbids and destroys the comparability of results across the sets. Where such a correction changes what the `jca` set reports, and therefore breaks exact reproduction of numbers already published from it, that consequence SHALL be recorded in the replication package rather than avoided by leaving the defect in place.

#### Scenario: Binding defect corrected in one set only

- **WHEN** a binding defect is corrected in `jca` and not in `jca_android`
- **THEN** the parity check MUST fail
- **AND** the change MUST NOT be considered complete

#### Scenario: Correction changes previously published numbers

- **WHEN** a platform-independent correction changes what the `jca` set reports for a corpus already measured and published
- **THEN** the replication package MUST record that exact reproduction of the published numbers no longer holds, and why
- **AND** the correction MUST still be applied to both sets

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

### Requirement: Cipher Transformation Tables Parameterised by Specification Set

The `Cipher` transformation tables — the admissible modes and, per mode, the admissible paddings — SHALL be selected by the active specification set and SHALL originate in the same derivation that produced that set's rules.

`CipherSpec` is the only specification in the set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java, where the tables are method locals covering two algorithm families. The derived Android rule admits eight, and the effect is a set that contradicts itself, generating keys for algorithms whose use it reports as misuse. A hand-maintained table is inadmissible even where it currently agrees with the rule, because agreement maintained by hand is the second translation the derivation exists to eliminate.

The behaviour of the `jca` set SHALL be preserved exactly by this parameterisation: the tables it selects MUST produce the same verdicts `isValid` produces today.

#### Scenario: Android set evaluates an algorithm its own rule admits

- **WHEN** the `jca_android` set is active and an application calls `Cipher.getInstance("ChaCha20/NONE/NoPadding")`, an algorithm the generated API 30 rule admits
- **THEN** `isValid` MUST consult the derived Android tables
- **AND** the call MUST NOT be reported as a misuse
- **AND** the set MUST NOT accept generating a key for an algorithm whose use it rejects

#### Scenario: Java SE set behaviour is unchanged

- **WHEN** the `jca` set is active
- **THEN** `isValid` MUST return the same verdict it returns today for every transformation
- **AND** the parameterisation MUST NOT alter any result measured under the `jca` set

### Requirement: Predicate Contract Between Specifications

A `Property` constant written through `ExecutionContext` by one specification and read by another SHALL be treated as a contract with two enforced properties: every constant written is read somewhere or recorded as a deliberate omission with its reason, and the inventory of writes and reads is a versioned artefact rather than an ad-hoc derivation.

Nothing links the constant written to the constant read. Both sides are enum members, so a specification that writes a neighbouring specification's constant compiles and runs and reports nothing; two specifications do this today. A read of an absent key returns false, so the failure is quiet in both directions — a missing write turns a guarded accusation into an unconditional one, and a wrong write turns a real accusation into silence.

Predicates that cannot be expressed by this mechanism SHALL be recorded rather than approximated. A predicate asserting **provenance** over a primitive cannot be represented by a map keyed on `equals`: `randomized[lSeed]` asserts that a `long` came from a CSPRNG, and the corresponding write side already carries the matching unsoundness, where marking small `int` values as randomised marks every equal literal in the process through the boxed-integer cache.

#### Scenario: Constant written and never read

- **WHEN** the inventory shows a `Property` constant written by at least one specification and read by none
- **THEN** the guard MUST fail
- **AND** the constant MUST either gain a reader or be recorded in the deliberate-omission list with its reason

#### Scenario: Specification writes a neighbouring specification's constant

- **WHEN** a specification writes a `Property` constant that does not correspond to the predicate its CrySL rule ensures
- **THEN** the guard MUST detect the mismatch from the inventory
- **AND** the defect MUST NOT depend on code review to be caught

#### Scenario: Inexpressible predicate is recorded, not approximated

- **WHEN** a CrySL predicate asserts provenance over a primitive value
- **THEN** it MUST be recorded as inexpressible with the reason, together with the unsoundness of the corresponding write side
- **AND** it MUST NOT be approximated by a value-keyed entry that would conflate unrelated equal values

## MODIFIED Requirements

### Requirement: Specification Set Support (FR03)

The system MUST support multiple, independent specification sets for different API monitoring domains. Each specification set represents a collection of `.mop` files targeting a specific category of API usage patterns. The system MUST ensure that specification sets are never mixed within a single experiment run.

Four predefined specification sets are supported:

1. **JCA (Java Cryptography Architecture)** -- 23 specifications derived from CrySL rules, detecting misuses of cryptographic APIs:
   - `CipherSpec.mop`: Cipher initialization and usage sequences. Unlike the other 22, it carries no allow-list of its own and delegates its transformation constraints to shared Java (`rvsec-core`), parameterised by the active specification set
   - `MessageDigestSpec.mop`: Hash algorithm validation
   - `SSLContextSpec.mop`: TLS protocol validation
   - `SecretKeySpecSpec.mop`: Key specification validation
   - `KeyGeneratorSpec.mop`: Key generation operation sequences
   - `SignatureSpec.mop`: Digital signature operation sequences
   - `MacSpec.mop`: Message Authentication Code operation sequences
   - `KeyStoreSpec.mop`: Keystore operation sequences
   - And 15 additional specifications covering SecureRandom, PBE, IvParameterSpec, etc.

2. **JCA Android** -- the same 23 specifications, derived against generated CrySL rules for a declared Android API level. Its only admissible divergence from the `jca` set is allow-list content (INV-INS-109); the platform-independent parts of every specification are identical, and defects in them are corrected in both sets in the same change.

3. **Generic (FSM)** -- 118 specifications from the JavaMOP specification database, detecting general API pattern violations such as Iterator hasNext/next ordering, stream resource management, and collection modification during iteration.

4. **Generic (new)** -- 27 curated specifications with descriptive names, such as `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`.

The specification set is determined by the `specification_set` field in `ExperimentConfig`, which maps to a subdirectory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The `get_monitored_operations_config()` JIT method resolves the mapping:
- `"jca"` maps to `{mop_base_dir}/jca/`
- `"generic"` maps to `{mop_base_dir}/generic/`
- `"custom"` uses `custom_specs_dir` (MUST be explicitly provided)

When no `mop_specs_dir` is explicitly provided to `RVGeneratorConfig`, it defaults to the JCA specification set.

Specifications within a set communicate through `Property` constants written and read via `ExecutionContext`. Those constants form a contract across specifications, governed by `Requirement: Predicate Contract Between Specifications`, not a per-specification implementation detail.

#### Scenario: JCA specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **AND** the directory MUST contain 23 `.mop` files

#### Scenario: JCA Android specification set selection

- **WHEN** the Android specification set is selected
- **THEN** `mop_specs_dir` MUST point to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain 23 `.mop` files and no `.aj` file
- **AND** its diff against the `jca` directory MUST contain allow-list differences only

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
