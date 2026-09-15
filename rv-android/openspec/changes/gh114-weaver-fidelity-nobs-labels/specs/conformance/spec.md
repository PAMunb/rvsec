## Purpose

This delta repairs two readings of the MOP–CrySL conformance component (`rvsec/rvsec-crysl`) that the refused creation twins of `jca_android` (instrumentation, "Label Codes") turned from a narrowing into a blind spot, and brings the MOP lift in line with two weaver rules this change introduces.

The inverse morphism `h` refuses, as `Unknown{OverlappingDispatch}`, every signature claimed by two or more labels when a guard separates them, and the lift builds `SpecModel.order` without the refused letter. The negated-twin idiom always overlaps. While only the one-argument creation had a twin, M2 still compared through the two-argument letter. Once every guarded creation gained a refused twin for each overload, both creation letters left the order, and M2 compared nothing over the calls that create the object. `CipherSpec` lost both witnesses of its incomparability, and six specifications read MOP_MORE_RESTRICTIVE on letters the component could not read. The alphabet map already says what a twin is: every twin row of `order_alphabet_map.csv` and `order_alphabet_map_expert.csv` is `order-unmapped`, because an `ORDER` has no symbol for a call it rejects on a constraint. M2 therefore reads an overlap the map reduces to one label as that label's letter, and reports the erasure it applied. Overlaps the map does not reduce, such as `KeyPairGeneratorSpec` `init1`/`initError`, stay refused.

The lift also read overlaps no woven program produces. `PointcutExpander` expanded `call(KeyManagerFactory.getInstance(String, ..))` without reading the `args(alg, *)` beside it, so the two-argument event claimed the one-argument call as well. The weaver enforces the arity of every `args` form (INV-INS-159), and the lift now does the same. Separately, a nested type imported as `java.security.KeyStore.ProtectionParameter` lifted to its dotted name, while CrySL renders the same type as `java.security.KeyStore$ProtectionParameter`, so one call was two letters. The weaver resolves nested types by existence (INV-INS-162), and the lift now does too.

Measured on `jca_android` against the upstream `CrySL-Rules` with `order_alphabet_map.csv`:
- The lift carries 19 refusals and M2 resolves 17; the two left are the genuine `KeyPairGeneratorSpec` overlaps.
- Over the five corpora the lift's refusals go from 65 to 62, and the files carrying one stay at 43.
- `CipherSpec` goes back to INCOMPARABLE with both witnesses.
- `KeyGeneratorSpec`, `MessageDigestSpec`, `SignatureSpec`, `TrustManagerFactorySpec`, `KeyManagerFactorySpec` and `KeyStoreSpec` read EQUIVALENT with no refusal.
- `MacSpec` reads INCOMPARABLE over a witness the refusal hid.

## Data Contracts

### Input
- `MopLift.labelOrder: LabelAutomaton` — the specification's order over labels, now an input of M2 beside `SpecModel` and `InverseMorphism`
- `alphabetMap: Path` — unchanged; its `disposition` column now also decides which refused overlaps M2 resolves

### Output
- `M2Result.refusals` — the refusals M2 could not resolve, plus undeclared events; a resolved overlap is not among them
- `M2Result.normalizations` — gains the `N-EPS` entry of every erased label of a resolved overlap
- `Event.signatures` — a trailing `..` narrowed to `*` positions by a conjoined `args(...)`, and nested types under their binary names

### Side-Effects
- None. The lift and M2 stay read-only over every corpus (INV-CONF-12)

### Error
- None new

## Invariants

- **INV-CONF-18**: M2 MUST resolve a refused `OverlappingDispatch` exactly when the alphabet map erases all of its labels but one, and MUST then read the signature as that label's letter and report each erased label of the overlap as an applied declared erasure. An overlap with two or more unerased labels, or with every label erased, MUST stay a refusal. The resolution MUST happen in M2 and MUST NOT happen in the lift: the lift MUST keep carrying every refusal on `MopLift.morphism()`, because only M2 reads the map (INV-CONF-10).
- **INV-CONF-19**: The MOP lift MUST narrow a call pattern ending in `..` by an `args(...)` without `..` conjoined with it, replacing the `..` by one `*` per remaining position, and a call pattern of fixed arity that such a clause contradicts MUST name no signature. An `args(...)` carrying `..` MUST NOT narrow. The lift MUST spell a nested type by its binary name when the platform class loader knows that name, and MUST keep a name no replacement of dots by `$` turns into a known class.

## ADDED Requirements

### Requirement: The MOP Lift Reads args Arity and Nested Type Names (FR03)

The lift SHALL expand an event's pointcut into the signatures a woven program can actually match. An `args(...)` clause without `..` fixes the arity of the call it is conjoined with, so a trailing `..` in the call pattern SHALL become one single-parameter wildcard `*` per remaining position, and a fixed-arity call pattern the clause contradicts SHALL name no signature. An `args(...)` carrying `..` bounds the arity only from below and SHALL NOT narrow. The morphism SHALL read `*` as one parameter of any type when it decides which letters an event claims (INV-CONF-19).

The lift SHALL spell nested types the way the rule side does. A name resolved through the file's imports, through the declared parameter types or as written SHALL have its dots replaced by `$` from the right until the platform class loader knows the name, and SHALL be kept when no replacement does. The lower SHALL import a nested type under its canonical dotted name, which is how Java source imports it, so a lowered file lifts back to the same signatures.

#### Scenario: A two-argument event does not claim the one-argument call
- **WHEN** the lift reads `jca_android/KeyManagerFactorySpec.mop`, whose `g2` is `call(public static KeyManagerFactory KeyManagerFactory.getInstance(String, ..)) && args(alg, *)` and whose `g1` is `call(public static KeyManagerFactory KeyManagerFactory.getInstance(String)) && args(alg)`
- **THEN** `g2` SHALL name the signature `KeyManagerFactory.getInstance(String, *)`
- **AND** the refusal over `getInstance(String)` SHALL name the labels `g1` and `g3` only, not `g2` or `g4`

#### Scenario: A contradicted arity names no signature
- **WHEN** the lift reads an event `call(* Condition.await(long, TimeUnit)) && target(c) && args(t)`
- **THEN** the event SHALL name no signature, because a one-position `args` matches no two-argument call

#### Scenario: A nested type is spelled by its binary name
- **WHEN** the lift reads `jca_android/KeyStoreSpec.mop`, which imports `java.security.KeyStore.ProtectionParameter` and declares `call(public Entry KeyStore.getEntry(String, ProtectionParameter))`
- **THEN** the event SHALL name `java.security.KeyStore.getEntry(java.lang.String, java.security.KeyStore$ProtectionParameter)` returning `java.security.KeyStore$Entry`
- **AND** M2 SHALL identify that letter with the rule's `getEntry`
- **AND** lowering the model and lifting it back SHALL give the same signatures

## MODIFIED Requirements

### Requirement: M2 Order Comparison over the Inverse Morphism (FR03)

M2 SHALL compare `L(A_mop)` with `L(A_crysl)` by product search in both directions, over `h⁻¹(L)` rather than over labels, and SHALL emit one of: equivalent, MOP more permissive, MOP more restrictive, or incomparable — each labelled `M2-decl`, each accompanied by the shortest witness with its status, and each with the set of normalizations applied printed beside it.

M2 SHALL determinize the rule automaton before comparing. Determinization is required for correctness — the Glushkov construction is genuinely non-deterministic for a rule of the form `ORDER con, a?, a`. Over the abandoned `api30` corpus it was measured as a no-op; over the 47 upstream rules that load, the no-op status is a **new measurement** the component SHALL publish, not an assumption it may carry over.

M2 SHALL take ε-erasure from the `disposition` column of the alphabet map, never from automaton shape. An erasure that a comparator infers is a decision nobody reviewed; an erasure the map declares is an assertion with an owner, a written reason and provenance, and M2's job is to check it.

M2 SHALL read a refused overlap through the same map (INV-CONF-18). The lift refuses, as `Unknown{OverlappingDispatch}`, every signature two or more labels claim when a guard separates them, and builds `SpecModel.order` without that letter. The corpus's instance is the negated-twin idiom: an admitting event and a refused twin over one call, under complementary `condition`s, whose twin row in the map is `order-unmapped` because an `ORDER` has no symbol for a call it rejects on a constraint. When the map erases every label of a refused overlap but one, the call SHALL be that label's letter, and each erased label of the overlap SHALL be reported as an applied declared erasure with its reason. The guard that chooses between the twins is M3's subject, as every guard is. M2 SHALL take the specification's order again, from the label automaton the lift keeps, over the morphism so resolved. Without this reading, a set in which every guarded creation has a refused twin for each overload leaves M2 with no creation letter to compare.

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
- **AND WHEN** an overlap is separated by a guard that is not statically decidable and the alphabet map leaves two or more of its labels unerased, as `KeyPairGeneratorSpec` `init1` and `initError` over `KeyPairGenerator.initialize(int)`, M2 SHALL emit `Unknown{OverlappingDispatch, labels: [...]}` with the labels named (INV-CONF-07)

#### Scenario: A twin overlap the map reduces to one label is that label's letter
- **WHEN** the lift of `jca_android/KeyGeneratorSpec.mop` refuses `KeyGenerator.getInstance(String)`, claimed by `g1` and by its refused twin `g3` under complementary `condition`s, and `getInstance(String, Object)`, claimed by `g2` and `g4`
- **AND** the alphabet map declares `g3` and `g4` `order-unmapped` and `g1` and `g2` `mapped`
- **THEN** M2 SHALL read `getInstance(String)` as the letter of `g1` and `getInstance(String, Object)` as the letter of `g2`
- **AND** the verdict SHALL list the normalizations `N-EPS·KeyGeneratorSpec.g3` and `N-EPS·KeyGeneratorSpec.g4` with the map's reasons
- **AND** `M2Result.refusals` SHALL carry no `OverlappingDispatch` for either signature, while `MopLift.morphism().refusals()` still carries both
- **AND** the verdict SHALL NOT be marked refusal-borne

### Requirement: Closed Unknown Taxonomy (NFR06)

The component SHALL emit refusals only under the five tags of the closed taxonomy, each with its declared field schema, and SHALL report the count of each tag per metric and per corpus. Adding a tag is a change of contract.

| Tag | Emitted when | Fields |
|---|---|---|
| `UnrecognizedConstraint` | the `condition`/`action` matches no known idiom | `{textoCru, site}` |
| `OverlappingDispatch` | two or more labels match one signature and the guard is not statically decidable; at M2, only when the alphabet map leaves two or more of those labels unerased | `{labels, signature, site}` |
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
