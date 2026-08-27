# Delta Spec: instrumentation (gh109-crysl-coverage)

## Purpose

This delta moves the coverage boundary of the `jca_android` specification set. Since gh104/gh105 the set answers to a single pinned oracle — the 49 expert-validated CrySL rules in `RVSec-replication-package/tools/rules/` (sha256 `d7bcc019…`, decision D-16) — but it still covers only the 22 rules its `jca` seed covered, a boundary gh105 kept deliberately ("no new accusation classes"). The consequence is structural: six predicates required by existing specifications (`preparedRSA`, `preparedDSA`, `preparedEC`, `preparedOAEP`, `preparedAlg`, `generatedManagerFactoryParameters`) have no possible producer in the set. The measured consequence is one step worse than "every read answers NOT_OBSERVED": **no site reads them**. Each consuming specification left the read closed and recorded why — the producer did not exist — together with the condition that would open it (`KeyPairGeneratorSpec.mop:135-141`, whose `init3`/`init4` bodies are empty; `TrustManagerFactorySpec.mop:135-141`, which measures the site at "three lines"). Landing the producers removes that premise, so this delta also requires the reads it unblocks to open. Whole misuse classes named by the oracle — password-to-key derivation via `SecretKeyFactory`, weak curves via `ECGenParameterSpec`, `KeyAgreement`, TLS configuration via `SSLEngine`/`SSLParameters` — are invisible to the instrument.

After this change the master question — *is everything the oracle covers also covered by MOP?* — has a derivable answer. Every one of the 49 rules ends in exactly one of **three** terminal states: **covered** by a paired `.mop`; **N/A by platform**, adjudicated with archive evidence (`Cookie`: `javax.servlet` has zero entries in the api30 jar; `DSAGenParameterSpec`: the class appears only at API 35); or **N/A by value**, adjudicated where no runtime-realizable verdict exists (`PasswordAuthentication`, ratified).

An **oracle defect is an attribute of a rule, not a destination for it**. The three verified defects — `Cipher.crysl:140-141` requires `preparedOAEP` under a `mode(...)` antecedent over strings the same rule classifies as paddings, so the clause is vacuous; `SSLEngine.crysl:12` references the undeclared label `cp1`; `KeyAgreement.crysl:31` references `g2` where `gs2` is meant — are recorded in `divergence_record.csv`, never edited upstream, and their rules are transcribed by evident intent and end **covered**, carrying the divergence row as warrant. A fourth terminal state for them would put `Cipher` in two states at once, since it is already paired. Coverage claims are derived by enumeration over rules and specifications, never asserted as literals.

The delta also states, as requirements, the two lessons the verification of the existing set taught. First, a value clause transcribed from the oracle must be *able to accuse*: `DHGenParameterSpecSpec` carries `exponentSize < primeSize` as a `condition(...)` on its only event, so a violating construction takes no transition, emits nothing, and does not even write its predicate — the violation is total silence, which is worse than a false negative because the record marks the clause implemented. Second, predicate values must survive the producer→reader hop: `KeyGeneratorSpec` validates an algorithm through the alias table but writes the raw spelling into the store, while readers query the canonical name the platform returns — the propagation breaks silently and surfaces as an unattributable NOT_OBSERVED several specifications downstream.

## Data Contracts

- **`data/jca_android/coverage_matrix.csv`** — the derived coverage matrix of INV-INS-150. Produced only by `scripts/gh109_coverage_matrix.py`, which enumerates the pinned oracle directory against the `jca_android` set directory; never edited by hand. Columns: `rule` (the `.crysl` stem), `terminal_state` (`covered` | `na-platform` | `na-value`), `evidence` (the paired `.mop` name, the api30 archive-listing line, or the adjudication record), `oracle_defect_row` (the `divergence_record.csv` anchor of a defect in this rule, or empty — derived by joining on `kind = oracle-wart` with the rule path in the record's `file` column, never typed by hand). One row per rule; the derivation fails when any rule has zero states or two.

  **What `covered` asserts, and what it does not.** `covered` is a verdict of *pairing and adjudication*: a `.mop` of the set answers for this rule and carries no platform-dead disposition. It is **not** a verdict of clause completeness. The depth of a transcription — which of the rule's EVENTS/ORDER/CONSTRAINTS/REQUIRES/ENSURES obligations actually reach a verdict surface — is measured elsewhere and is not re-derived here: by M0–M4 of the `rvsec-crysl` conformance component (`M0Vitality`, `M1Events`, `M2Order`, `M3Constraints`, `M4Predicates`, with `SpecRulePairing` and `ConformanceReport`), and clause by clause by `constraint_table.csv` and `predicate_ledger.csv`. A second derivation of that depth inside this matrix would be a second translation of the oracle, which this delta forbids for the `Cipher` tables and forbids here for the same reason. One caveat is measured and belongs to any citation of M0–M4 as evidence for this set: the component reads its oracle at `rvsec-cognicrypt/CrySL-Rules` commit `f2f4d3b`, which differs from the pinned expert copy in exactly one file and two lines — `Cipher.crysl:97` and `:113`, the `CCM` entry in the AES mode and padding clauses — a difference already carried as an `oracle-wart` divergence row.

  Two adjudicated mappings are part of the contract: `SecretKey → SecretKeySpec.mop` is `covered` — the file realizes the rule's ENSURES and the rule's `Destroy` tail is recorded platform-dead (INV-INS-137), so no reachable trace yields a further verdict; the ledger's `NON_PAIRING_FILES` governs specification pairing, not coverage. And `HMACParameterSpec` is `na-platform` despite its `.mop` (INV-INS-155).

## Invariants

- **INV-INS-150**: Every rule of the pinned expert oracle SHALL have exactly one terminal state in the coverage matrix, drawn from three: *covered* (a paired `.mop` exists in `jca_android` and carries no platform-dead disposition), *N/A-by-platform* (recorded with api30 archive-listing evidence), or *N/A-by-value* (recorded where no runtime-realizable verdict exists — see INV-INS-156). A defect in the rule's own text SHALL be recorded as an **attribute** of that rule's row (`oracle_defect_row`) and SHALL NOT be a terminal state: a defective rule transcribed by evident intent is *covered*, with the divergence row as its warrant. `covered` asserts pairing and adjudication, not clause completeness; the depth of a transcription is measured by the `rvsec-crysl` conformance component and by the per-clause records, and SHALL NOT be re-derived in this matrix. The matrix SHALL be derived by enumeration over the rules directory and the set directory; no artifact may assert the totals as literals.
- **INV-INS-151**: Every predicate read by any specification in the set SHALL have at least one producing specification in the set, or a recorded disposition naming the reason production is impossible (platform absence or oracle defect). `unmonitored-producer` SHALL NOT be a terminal disposition for a rule whose specification is writable. The obligation is symmetric: a predicate **written** by a specification of the set, whose consuming rule also has a `.mop`, SHALL have its read opened at that consuming site — or carry a recorded reason why the site cannot bind the clause's objects (the generator ceiling and the platform are the only reasons admitted). A predicate written by a new specification and read by nobody is monitoring without a verdict surface, which is the same ground on which a rule is adjudicated N/A-by-value.
- **INV-INS-152**: A value clause transcribed from the oracle SHALL be able to emit an accusation on its reachable violated branch. A transcription whose only realization is a `condition(...)` guard — where the violating call takes no transition and emits nothing — is defective, and the conformance record MUST NOT mark such a clause as implemented.
- **INV-INS-153**: A predicate value written into the `PredicateStore` SHALL be the canonical algorithm name under the set's alias semantics, and every reader SHALL resolve its query with the same semantics. A spelling divergence between a producer and a reader of the same predicate is a defect of the set, not a legitimate NOT_OBSERVED.
- **INV-INS-154**: Every new specification SHALL stay within the generator ceiling (17 events; 18 overflows the enable-set parser) and every pointcut owner and member SHALL be verified present in the declared platform jar by archive listing (`unzip -l`), never by `javap -cp`, which resolves against the host JDK and reports members the platform does not have.
- **INV-INS-155**: A specification whose subject class exists in no Android API level SHALL carry a recorded platform-dead disposition and SHALL NOT be counted as coverage of its rule; its rule's terminal state is N/A-by-platform even though a `.mop` file exists.
- **INV-INS-156**: A rule is *N/A-by-value* when no specification written for it could reach a verdict a reader would act on: every CONSTRAINTS clause is a static-analysis predicate the instrument cannot evaluate at run time, and the rule's ENSURES predicate has no consumer among the 49. The adjudication SHALL name both legs and SHALL record what the rule's ORDER would still accuse, so that the departure is measured rather than assumed away.

## MODIFIED Requirements

### Requirement: Cipher Transformation Tables of the Derived Set

The `Cipher` transformation tables consulted by the derived set — the admissible algorithms, their modes, and per mode the admissible paddings — SHALL transcribe the expert `Cipher` rule of the pinned oracle (D-16), and SHALL be reached by `jca_android/CipherSpec.mop` naming its own utility (`CipherTransformationNormalizer`) rather than by any runtime selection over a shared one.

`CipherSpec` is the only specification in the set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java. The normalizer SHALL admit every algorithm family the expert rule admits — including the eight `PBEWithHmacSHA{224,256,384,512}AndAES_{128,256}` families of `Cipher.crysl:90-105`, with their CBC mode and PKCS5 padding clauses — because a table narrower than the rule accuses programs the oracle declares conforming, which is a false positive manufactured by the instrument. A hand-maintained table is inadmissible even where it currently agrees with the rule, because agreement maintained by hand is a second translation of the oracle.

The `GENERATED_KEY` read in `CipherSpec` SHALL split the transformation with the normalizer's alias-resolving splitter (`CipherTransformationNormalizer.alg`), not the frozen raw splitter, so that an alias spelling and its canonical form compare equal; and the comparison SHALL treat the platform's keysize-suffixed service names (`AES_128`, `AES_256`) as equal to their family name (`AES`) in the key×transformation check, because Conscrypt registers them as distinct services over the same family and a key generated for the family is not a misuse when used with the suffixed service. Producers of algorithm-valued predicates SHALL write the canonical name (INV-INS-153).

Selection by the *specification* rather than by the *runtime* is what keeps the frozen set frozen. The frozen `CipherTransformationUtil` and the `jca` set remain byte-identical; every widening lands in the normalizer that only `jca_android` names.

#### Scenario: Expert-admitted PBE family is not accused

- **WHEN** the `jca_android` set is active and an application calls `Cipher.getInstance("PBEWithHmacSHA256AndAES_128")`, a transformation `Cipher.crysl:90-105` admits with CBC/PKCS5
- **THEN** `isValid` MUST return true and no `CIPHER-ALG-*` report may be emitted for it
- **AND** the frozen `jca` set's verdict for the same call MUST be unchanged, because the class it calls was not modified

#### Scenario: Suffixed service name compares equal to its family

- **WHEN** a key is generated by `KeyGenerator.getInstance("AES")` and consumed by `Cipher.getInstance("AES_128/CBC/PKCS5Padding")`
- **THEN** the `GENERATED_KEY` read MUST answer SATISFIED
- **AND** no `CIPHER-CONSTR-00` may be emitted for the pair

#### Scenario: Producer writes a raw alias spelling

- **WHEN** a program calls `KeyGenerator.getInstance("HMAC/SHA256")` (a Conscrypt alias of `HmacSHA256`) and the generated key later reaches a reader that queries `key.getAlgorithm()`
- **THEN** the producer MUST have written the canonical name, so the reader's query matches
- **AND** the propagation MUST NOT break into a downstream NOT_OBSERVED on account of spelling

#### Scenario: A shared table selected at runtime is proposed

- **WHEN** an implementation would give both sets one utility whose tables are chosen by the active specification set
- **THEN** it MUST be rejected under INV-INS-112
- **AND** the reason MUST be recorded as the frozen set's verdict depending on state set outside its own specification

## ADDED Requirements

### Requirement: Expert Oracle Coverage Parity

The `jca_android` set SHALL cover the pinned expert oracle completely, in the sense of INV-INS-150: each of the 49 rules is covered by a paired specification, adjudicated N/A (by platform, with archive evidence; or by value, where no runtime-realizable verdict exists), or the subject of a recorded oracle defect. The coverage matrix SHALL be a versioned artifact derived by enumeration, and the predicate ledger SHALL close under it: after this change, no predicate read in the set has the disposition `unmonitored-producer` for a rule that is writable on the platform (INV-INS-151).

#### Scenario: Producer gap closes when the producing specification lands

- **WHEN** `RSAKeyGenParameterSpecSpec.mop` lands, writing `preparedRSA` at its rule's ORDER acceptance point
- **THEN** the ledger re-derivation MUST move the `KeyPairGenerator` `preparedRSA` clause from `unmonitored-producer` to wired
- **AND** the write alone MUST NOT be reported as the gap closing, because `KeyPairGeneratorSpec`'s `init3`/`init4` bodies read nothing: a verdict surface exists only once the guarded read is opened at the consuming site

#### Scenario: The unblocked read opens at the consuming site

- **WHEN** the producer of `preparedRSA` exists and `KeyPairGeneratorSpec`'s `init3`/`init4` gain the guarded read of `KeyPairGenerator.crysl:35`
- **THEN** a program that initializes an RSA `KeyPairGenerator` from a conforming `RSAKeyGenParameterSpec` MUST read SATISFIED, and one that initializes it from a parameter spec the rule refuses MUST be accused on the VIOLATED branch
- **AND** the NOT_OBSERVED branch MUST carry a code of its own, so that a program whose parameter spec was built outside the monitored set is distinguishable from one that violated the clause

#### Scenario: A producer gap hides behind a producing rule that is paired

- **WHEN** the ledger is re-derived after `DigestInputStreamSpec.mop` and `DigestOutputStreamSpec.mop` land, and the `generatedMessageDigest` they read names a producing rule — `MessageDigest` — that already has a paired `.mop`
- **THEN** the disposition MUST be decided by whether `MessageDigestSpec.mop` writes the predicate, and not by whether the producing rule has a `.mop`: a paired producer that writes nothing is a gap, and it is the one form the absent-rule enumeration cannot see
- **AND** the write MUST stand at the acceptance point the rule names (`generatedMessageDigest[this] after Get`, `MessageDigest.crysl:46`), so that a program which digests through a conforming `getInstance` reaches the SATISFIED branch instead of NOT_OBSERVED

#### Scenario: A producer lands a group before its consumers and the interval is named

- **WHEN** `MessageDigestSpec.mop` gains the `generatedMessageDigest` write in group G1 and the two rules that require it — `DigestInputStream.crysl:33` and `DigestOutputStream.crysl:34` — have no specification until group G3
- **THEN** the write's recorded disposition MUST name the absent consumer and MUST NOT name a deliberate omission, because two rules of the oracle do require the predicate and an omission would record as settled the gap this change exists to close
- **AND** the disposition MUST NOT outlive its reason: when the consuming specifications land, the re-derivation MUST move the write to wired, and the final verification MUST report that no transitory disposition remains

#### Scenario: A recorded omission expires when a landing consumer reads its predicate

- **WHEN** a specification landed by this change reads a predicate that an existing specification writes under the disposition `omission`, and the closure gate — which accumulates written and read predicate names over the whole set — therefore stops raising that write row
- **THEN** the group's records pass MUST re-derive the disposition of every write row of the graph, not only the rows its own tasks created
- **AND** a recorded reason the landing consumer falsified MUST be amended in that same pass, because a reason no gate reads any more is where a false record survives unnoticed

#### Scenario: A read that cannot bind its clause is recorded, not dropped

- **WHEN** `Cipher.crysl:136` requires `preparedAlg[params, alg(transformation)]` but `CipherSpec`'s fused `i2` binds only `mode` and `key` (`args(mode, key, ..)`) and the specification stands at 17 of the 17 events the generator admits
- **THEN** the read MUST NOT be opened by adding an event or by re-shaping `i2`
- **AND** the clause MUST carry a recorded deferral naming the ceiling and the missing binding, so that the ledger's disposition for it is a measured impossibility and not an unexplained silence

#### Scenario: A rule absent from the platform is adjudicated, not specified

- **WHEN** the coverage matrix is derived and reaches `Cookie.crysl` (`javax.servlet.http.Cookie`, zero entries in the api30 jar) or `DSAGenParameterSpec.crysl` (class present only from API 35)
- **THEN** the rule's terminal state MUST be N/A-by-platform with the archive listing as evidence
- **AND** no `.mop` may be written for it

#### Scenario: An oracle defect is recorded, never repaired upstream

- **WHEN** a rule cannot be transcribed as written — `SSLEngine.crysl:12` references the undeclared label `cp1`, `KeyAgreement.crysl:31` references `g2` for `gs2`, `Cipher.crysl:140-141` guards `preparedOAEP` with a vacuous antecedent
- **THEN** the defect MUST become a `divergence_record.csv` row naming the rule and line, and the specification MUST transcribe the evident intent with the row as its warrant
- **AND** the pinned oracle files MUST remain byte-identical

### Requirement: Producer Specifications for Expert Rules

Each new specification SHALL be written against its expert rule alone: the event alphabet realizes the rule's EVENTS (overloads fused per the existing fusion rules), the automaton realizes the rule's ORDER, every value CONSTRAINT is transcribed with an accusing branch (INV-INS-152), predicates are written at the ORDER acceptance point and read in event bodies per the gh105 substrate rules, and every accusation site has a `codes.csv` row. Platform viability is verified before writing (INV-INS-154).

#### Scenario: Trivial parameter-spec rule becomes a specification

- **WHEN** a rule with `ORDER = Con` and value constraints (e.g. `ECGenParameterSpec.crysl`: `stdName` in the admitted curve list, ensuring `preparedEC`) is implemented
- **THEN** the specification MUST accuse on construction with a name outside the list, write `preparedEC` only on the conforming branch, and declare no events beyond the rule's alphabet
- **AND** the generated monitor MUST be inspected as an artifact (INV-INS-145), never trusted from the generator's exit code

#### Scenario: Value clause transcribed as a silent guard is rejected

- **WHEN** a new or edited specification carries a value constraint only as `condition(...)` on the event, so the violating call takes no transition and emits nothing
- **THEN** the specification MUST be treated as defective under INV-INS-152
- **AND** the repair MUST fuse the test into the event body with an accuser on the violated branch, following the existing `IvParameterSpec` fusion form

#### Scenario: New specification enters the enforcement apparatus

- **WHEN** a new `.mop` is added to the set
- **THEN** it MUST enter every enumeration the apparatus derives — a `new-file` divergence-record row, `codes.csv` bijection, predicate-graph rows for its predicate sites, an alphabet mapping (or a declared skip) for G-ORDER, and the re-pinned counting constants that CI enforces
- **AND** the additions MAY be batched per task group, but the final verification pass MUST show every gate green over the enlarged set

### Requirement: Platform-Dead Specification Disposition

A specification whose subject class exists in no Android API level SHALL carry a recorded platform-dead disposition (INV-INS-155). The current instance is `HMACParameterSpecSpec.mop`: `javax.xml.crypto.dsig.spec.HMACParameterSpec` has zero archive entries at every scanned API level, so the specification generates a monitor that can never fire an event. The disposition — kept as documentation of the rule's untranslatability, or retired to `backup/` — is a researcher decision recorded in the change; either way the rule's terminal state is N/A-by-platform.

#### Scenario: Dead specification does not count as coverage

- **WHEN** the coverage matrix is derived and reaches `HMACParameterSpec.crysl`
- **THEN** the terminal state MUST be N/A-by-platform regardless of the `.mop` file's existence
- **AND** the `preparedHMAC` ledger rows MUST agree with that disposition on both the ENSURES and REQUIRES sides
