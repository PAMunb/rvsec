# Delta Spec: instrumentation (gh109-crysl-coverage)

## Purpose

This delta moves the coverage boundary of the `jca_android` specification set. Since gh104/gh105 the set answers to a single pinned oracle — the 49 expert-validated CrySL rules in `RVSec-replication-package/tools/rules/` (sha256 `d7bcc019…`, decision D-16) — but it still covers only the 22 rules its `jca` seed covered, a boundary gh105 kept deliberately ("no new accusation classes"). The consequence is structural: six predicates required by existing specifications (`preparedRSA`, `preparedDSA`, `preparedEC`, `preparedOAEP`, `preparedAlg`, `generatedManagerFactoryParameters`) have no possible producer in the set. The measured consequence is one step worse than "every read answers NOT_OBSERVED": **no site reads them**. Each consuming specification left the read closed and recorded why — the producer did not exist — together with the condition that would open it (`KeyPairGeneratorSpec.mop:135-141`, whose `init3`/`init4` bodies are empty; `TrustManagerFactorySpec.mop:135-141`, which measures the site at "three lines"). Landing the producers removes that premise, so this delta also requires the reads it unblocks to open. Whole misuse classes named by the oracle — password-to-key derivation via `SecretKeyFactory`, weak curves via `ECGenParameterSpec`, `KeyAgreement`, TLS configuration via `SSLEngine`/`SSLParameters` — are invisible to the instrument.

After this change the master question — *is everything the oracle covers also covered by MOP?* — has a derivable answer. Every one of the 49 rules ends in exactly one of **three** terminal states: **covered** by a paired `.mop`; **N/A by platform**, adjudicated with archive evidence (`Cookie`: `javax.servlet` has zero entries in the API 30 `android.jar`; `DSAGenParameterSpec`: the class appears only at API 35); or **N/A by value**, adjudicated where no runtime-realizable verdict exists (`PasswordAuthentication`, ratified).

An **oracle defect is an attribute of a rule, not a destination for it**. The three verified defects — `Cipher.crysl:140-141` requires `preparedOAEP` under a `mode(...)` antecedent over strings the same rule classifies as paddings, so the clause is vacuous; `SSLEngine.crysl:12` references the undeclared label `cp1`; `KeyAgreement.crysl:31` references `g2` where `gs2` is meant — are recorded in `divergence_record.csv`, never edited upstream, and their rules are transcribed by evident intent and end **covered**, carrying the divergence row as warrant. A fourth terminal state for them would put `Cipher` in two states at once, since it is already paired. Coverage claims are derived by enumeration over rules and specifications, never asserted as literals.

The delta also states, as requirements, the two lessons the verification of the existing set taught. First, a value clause transcribed from the oracle must be *able to accuse*: `DHGenParameterSpecSpec` carries `exponentSize < primeSize` as a `condition(...)` on its only event, so a violating construction takes no transition, emits nothing, and does not even write its predicate — the violation is total silence, which is worse than a false negative because the record marks the clause implemented. Second, predicate values must survive the producer→reader hop: `KeyGeneratorSpec` validates an algorithm through the alias table but writes the raw spelling into the store, while readers query the canonical name the platform returns — the propagation breaks silently and surfaces as an unattributable NOT_OBSERVED several specifications downstream.

## Data Contracts

- **`data/jca_android/coverage_matrix.csv`** — the derived coverage matrix of INV-INS-150. Produced only by `scripts/gh109_coverage_matrix.py`, which enumerates the pinned oracle directory against the `jca_android` set directory; never edited by hand. Columns: `rule` (the `.crysl` stem), `terminal_state` (`covered` | `na-platform` | `na-value`), `evidence` (the paired `.mop` name, the API 30 `android.jar` archive-listing line, or the adjudication record), `oracle_defect_row` (the `divergence_record.csv` anchor of a defect in this rule, or empty — derived by joining on `kind = oracle-wart` with the rule path in the record's `file` column, never typed by hand). One row per rule; the derivation fails when any rule has zero states or two.

  **What `covered` asserts, and what it does not.** `covered` is a verdict of *pairing and adjudication*: a `.mop` of the set answers for this rule and carries no platform-dead disposition. It is **not** a verdict of clause completeness. The depth of a transcription — which of the rule's EVENTS/ORDER/CONSTRAINTS/REQUIRES/ENSURES obligations actually reach a verdict surface — is measured elsewhere and is not re-derived here: by M0–M4 of the `rvsec-crysl` conformance component (`M0Vitality`, `M1Events`, `M2Order`, `M3Constraints`, `M4Predicates`, with `SpecRulePairing` and `ConformanceReport`), and clause by clause by `constraint_table.csv` and `predicate_ledger.csv`. A second derivation of that depth inside this matrix would be a second translation of the oracle, which this delta forbids for the `Cipher` tables and forbids here for the same reason. One caveat is measured and belongs to any citation of M0–M4 as evidence for this set: the component reads its oracle at `rvsec-cognicrypt/CrySL-Rules` commit `f2f4d3b`, which differs from the pinned expert copy in exactly one file and two lines — `Cipher.crysl:97` and `:113`, the `CCM` entry in the AES mode and padding clauses — a difference already carried as an `oracle-wart` divergence row.

  Two adjudicated mappings are part of the contract: `SecretKey → SecretKeySpec.mop` is `covered` — the file realizes the rule's ENSURES and the rule's `Destroy` tail is recorded platform-dead (INV-INS-137), so no reachable trace yields a further verdict; the ledger's `NON_PAIRING_FILES` governs specification pairing, not coverage. And `HMACParameterSpec` is `na-platform` despite its `.mop` (INV-INS-155).

## Invariants

- **INV-INS-150**: Every rule of the pinned expert oracle SHALL have exactly one terminal state in the coverage matrix, drawn from three: *covered* (a paired `.mop` exists in `jca_android` and carries no platform-dead disposition), *N/A-by-platform* (recorded with API 30 `android.jar` archive-listing evidence), or *N/A-by-value* (recorded where no runtime-realizable verdict exists — see INV-INS-156). A defect in the rule's own text SHALL be recorded as an **attribute** of that rule's row (`oracle_defect_row`) and SHALL NOT be a terminal state: a defective rule transcribed by evident intent is *covered*, with the divergence row as its warrant. `covered` asserts pairing and adjudication, not clause completeness; the depth of a transcription is measured by the `rvsec-crysl` conformance component and by the per-clause records, and SHALL NOT be re-derived in this matrix. The matrix SHALL be derived by enumeration over the rules directory and the set directory; no artifact may assert the totals as literals.
- **INV-INS-151**: Every predicate read by any specification in the set SHALL have at least one producing specification in the set, or a recorded disposition naming the reason production is impossible (platform absence or oracle defect). `unmonitored-producer` SHALL NOT be a terminal disposition for a rule whose specification is writable. The obligation is symmetric: a predicate **written** by a specification of the set, whose consuming rule also has a `.mop`, SHALL have its read opened at that consuming site — or carry a recorded reason why the site cannot bind the clause's objects (the generator ceiling and the platform are the only reasons admitted). A predicate written by a new specification and read by nobody is monitoring without a verdict surface, which is the same ground on which a rule is adjudicated N/A-by-value.
- **INV-INS-152**: A value clause transcribed from the oracle SHALL be able to emit an accusation on its reachable violated branch. A transcription whose only realization is a `condition(...)` guard — where the violating call takes no transition and emits nothing — is defective, and the conformance record MUST NOT mark such a clause as implemented.
- **INV-INS-153**: A predicate value written into the `PredicateStore` SHALL be the canonical algorithm name under the set's alias semantics, and every reader SHALL resolve its query with the same semantics. A spelling divergence between a producer and a reader of the same predicate is a defect of the set, not a legitimate NOT_OBSERVED.
- **INV-INS-154**: Every new specification SHALL stay within the generator ceiling (17 events; 18 overflows the enable-set parser) and every pointcut owner and member SHALL be verified present in the declared platform jar by archive listing (`unzip -l`), never by `javap -cp`, which resolves against the host JDK and reports members the platform does not have.
- **INV-INS-155**: A specification whose subject class exists in no Android API level SHALL carry a recorded platform-dead disposition and SHALL NOT be counted as coverage of its rule; its rule's terminal state is N/A-by-platform even though a `.mop` file exists.
- **INV-INS-156**: A rule is *N/A-by-value* when no specification written for it could reach a verdict a reader would act on: every CONSTRAINTS clause is a static-analysis predicate the instrument cannot evaluate at run time, and the rule's ENSURES predicate has no consumer among the 49. The adjudication SHALL name both legs and SHALL record what the rule's ORDER would still accuse, so that the departure is measured rather than assumed away.
- **INV-INS-157**: An event whose expert rule leaves an argument position anonymous (`getInstance(algorithm, _)`) SHALL realize that position for every overload the declared platform jar carries, or record why an overload is excluded. A pointcut that names a proper subset of the platform's overloads narrows the rule's alphabet without saying so: the unrealized route takes no event, its value clause cannot accuse, and the next observed call draws an ORDER verdict the rule does not state. The same obligation binds the accusing site's argument binding — an accuser bound at a fixed arity (`args(alg)`) does not realize an alphabet the rule wrote open.
- **INV-INS-158**: A report line whose code marks an unobserved predicate (`-NOBS-`) SHALL NOT be aggregated as conformance nor as violation by any consumer of the results. The `ErrorType` alone does not separate them — `-NOBS-` and `-CONSTR-` share `UnsatisfiedConstraint` by construction — so the separation SHALL be keyed on the `site_kind` column of `codes.csv`. This invariant governs consolidation only; it does not change what the monitors emit on the device, and it does not decide whether a NOBS branch retires (that follows the measurement, task 7.3).

## MODIFIED Requirements

### Requirement: Allow-List Conformance to the Expert-Validated CrySL Rules

Every allow-list of `jca_android` SHALL be a literal transcription of the `CONSTRAINTS` clause of the corresponding rule in the **pinned expert copy `RVSec-replication-package/tools/rules/`** — the 49 `.crysl` rules validated by the CogniCrypt authors, frozen here by sha256, and the copy the published RVSec numbers were measured against — and a gate SHALL compare the two mechanically for all 21 specifications (INV-INS-127). This requirement replaces, in force from D-15 (2026-08-24), the api30 anchor this change first adopted; the reason is measured and is stated in the audit `docs/20260824_auditoria_specs_jca_android.md`. The `.ref` tiers that refine the api30 lists were derived from **provider registries**, so a refined list answers "what does the platform offer" and not "what is safe to use". Transcribed into a clause whose purpose is security, that answer inverts the rule while leaving its syntax untouched: the api30 `MessageDigest` list admits `MD5` and `SHA-1`, `SSLContext` admits `SSL`/`TLSv1`/`TLSv1.1`, `Mac` admits `HmacMD5`/`HmacSHA1`, `KeyGenerator` admits `ARC4`/`DESede`/`BLOWFISH`, `Signature` admits `MD5withRSA`/`NONEwithRSA`/`SHA1withDSA`, and the api30 `Cipher` tables admit **`AES/ECB`**. A set faithful to that oracle cannot, by construction, accuse an insecure algorithm the platform ships — which is the opposite of what a crypto-misuse detector is for.

The scope of the anchor is **values only**. `ORDER`, event alphabets and the predicate clauses (`ENSURES`/`REQUIRES`/`NEGATES`) keep the generated api30 rules as their oracle: the audit measured that the protocol dimension survives the MetaCrySL chain nearly intact, so there is no defect there to correct, and moving that anchor would reopen G-ORDER's recorded divergences and the 36-clause predicate ledger for no detection gain. MetaCrySL is not modified by this contract, and the rules under `generated/api30/` are still read as they stand — for `ORDER` and predicates as the oracle, for values as the record of a withdrawn one.

**How the transcription is realised.** For each value clause, the list the successor set carries SHALL be the list the frozen `jca` carries, checked entry by entry against the expert `CONSTRAINTS` clause. The frozen list *is* the expert transcription — it is what the published measurement answered to — so re-transcribing from the rule text would risk a second hand-copy of the kind this requirement exists to undo. Where the two differ it is by **spelling variants** the frozen set hand-wrote into its lists (`SHA256` beside `SHA-256`; `HMAC-SHA256`, `HMAC/SHA256` beside `HmacSHA256`; `TLSV1.2` for `TLSv1.2`); those SHALL stay in the lists and SHALL each carry a `spelling-variant` note in the conformance record naming the expert entry they duplicate. They change no verdict — comparison already folds case and resolves aliases — so removing them would be an unvalidated narrowing for no gain, while the note is what lets the gate tell a redundant spelling from a value with no clause behind it.

Literal transcription alone leaves roughly three thousand of the measured events unresolved, because the rule writes the JCA standard name and the app writes what Conscrypt registers. The set SHALL therefore declare one normalisation rule and apply it uniformly: **comparison is case-insensitive**, and an observed value matches a list entry when a row of the set's **alias table** maps it to that entry. The alias table is derived from the Conscrypt `android11-release` branch, and every row SHALL carry its primary-source pointer: `X509` → `PKIX` from `OpenSSLProvider.java:90`, `SHA1` and `SHA` → `SHA-1` from `:115-116`, `SHA256` → `SHA-256` from `:124`. The extraction SHALL cover multi-line `put("Alg.Alias…")` registrations: the audit measured **11** real registrations a single-line regex missed — 6 `Signature` composite OIDs resolving to `SHA{224,256,384,512}withRSA` (`:234-263`) and 5 `Cipher.RSA/None/OAEP*` (`:339-355`) — and the `Signature` six are live false-accusation vectors, so the table SHALL carry them and its row count SHALL be recomputed by the task that derives it rather than fixed here. Each row's `in_allowlist` flag SHALL be recomputed against the **expert** lists after the recorded departures, since the flag's definition names the set's own allow-list and that list has changed. A spelling no registration in that file explains SHALL NOT be given a row; it belongs in `data/jca_android/divergence_record.csv`, where its evidence is declared for what it is.

Uniform case-insensitivity also removes an inconsistency the frozen set carries by accident: it compares case-sensitively in eight specifications (`Mac`, `Signature`, `SecureRandom`, `KeyGenerator`, `TrustManagerFactory`, `KeyManagerFactory`, `KeyStore`, `KeyPairGenerator`) and through `.toUpperCase()` in three (`MessageDigest`, `SSLContext`, `SecretKeySpecSpec`), so the same string is a misuse in one specification and not in another. That normalisation is kept from D-10 unchanged; only the oracle beneath it moves.

The alias table SHALL live in **`data/jca_android/alias_table.csv`, a file of its own** — not a column of the conformance record, which answers a different question and would make its rows illegible — and each row SHALL name, in its `service` column, the JCA service it applies to, which is how a specification finds its rows. Resolution SHALL happen **at runtime, and not by reading the CSV**: `ConscryptAliasTable`, under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`, SHALL carry the table as code, each `jca_android` allow-list check SHALL name that class in its call, and a test SHALL assert that the in-code table equals the CSV row for row. This is the pattern INV-INS-112 already fixes for the `Cipher` transformation tables, and it is what keeps the frozen `jca` out of reach: no `jca` specification names the class, so no verdict of the frozen set moves.

Expanding the aliases into the allow-lists instead SHALL NOT be done, for three reasons. (a) It cannot express what is being decided: case-insensitive comparison is not expansible, so an expanded list would have to enumerate every spelling of every entry in every case. (b) It destroys the gate: an expanded list is no longer equal to the expert clause, so G-CONF has nothing left to compare and the conformance argument collapses into a diff nobody can read. (c) It repeats the defect this contract removes — resolving aliases by mixing them into the allow-list, which is why nobody could tell from a file which entries came from a rule and which from a provider registration. The `spelling-variant` notes above are the concession this makes to the frozen lists, and they are notes precisely so the distinction survives.

**Departures from a literal transcription of the expert rule SHALL be one of the five kinds INV-INS-125 enumerates, and each SHALL be recorded.** Two of them widen a list and are stated here in full.

**`platform-value` — the one admissible widening, closed and cited.** A value enters an allow-list beyond the expert list **only** when rejecting it would accuse a practice the platform itself recommends, and only with a primary-source citation; an uncited candidate is dropped and stays accused. The enumerated set is closed: `TLS` in `SSLContextSpec`, and `{AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}` in `KeyStoreSpec`. Nothing else. `X509` needs no entry — the alias table maps it to `PKIX`, which the expert list carries. `SHA256WITHRSA` needs no entry — case folding covers it. `SSL` gets no entry either, and the reason is stated because the evidence looks at first like a reason to grant one: Conscrypt registers `SSLContext.SSL` and `SSLContext.TLS` on the same implementation class (`OpenSSLProvider.java:80-81`, both taking `defaultSSLContextSuffix`, which is the TLSv1.2 or TLSv1.3 suffix), so on API 30 the two names yield the same context. But the registration is a `put`, not an `Alg.Alias`, so it earns no alias row either; the expert rule names `TLSv1.2` and `TLSv1.3` and nothing else; and asking a provider for `"SSL"` is the misuse the rule is about, whatever this one platform resolves it to. The equivalence SHALL be recorded as a `behavioural` row so a reader of the report knows what the accused calls actually got at run time.

**Values the expert lists carry that Android does not offer SHALL stay in the lists.** `SunX509`, `NativePRNG`, `NativePRNGBlocking`, `NativePRNGNonBlocking`, `Windows-PRNG`, `PKCS11`, `JKS`, `JCEKS`, `DKS`: each is inert on the platform — no app can obtain them, so no verdict depends on them — and removing an entry from an expert-validated list because the local platform lacks it is exactly the unvalidated narrowing that produced the defect this requirement corrects. This reverses three narrowings D-10 took: `SecureRandomSpec` back to the six expert entries, `KeyManagerFactorySpec` and `TrustManagerFactorySpec` back to `{PKIX, SunX509}`, `KeyStoreSpec` back to the five JSE types plus the four platform values above.

**The set SHALL NOT enlarge the class of clauses it checks.** An expert `CONSTRAINTS` clause the frozen `jca` left unimplemented stays unimplemented, recorded as a `deferred-constant` row citing the **expert** clause text. The re-anchoring restores the lists the experts wrote; it does not add accusations the validated set never made and whose false-positive behaviour on the corpus is unmeasured. The measured case is `KeyGenerator.crysl`'s `algorithm in {"AES"} => keysize in {128, 192, 256}`, which `jca/KeyGeneratorSpec.mop` never tested and which stays deferred (researcher decision, 2026-08-24).

The `Cipher` transformation tables SHALL stay in Java. `CipherTransformationUtil` — the class of the frozen `jca`, which transcribes the expert `Cipher.crysl` and is what the published numbers were measured with — stays byte-identical: the freeze (INV-INS-109/118) forbids **editing** it, not **calling** it, and `jca_android/CipherSpec.mop` imports it and reaches it through `CipherTransformationNormalizer`, so no verdict of the frozen set moves. The normaliser is the one place the successor set's `Cipher` values move, under `Requirement: Cipher Transformation Tables of the Successor Set`: it reproduces `CipherTransformationUtil`'s value clauses, resolves the pinned Conscrypt aliases and folds case before comparing, and admits the eight `PBEWithHmacSHA{224,256,384,512}AndAES_{128,256}` families `Cipher.crysl` admits (D-20.1). G-CONF keeps comparing against the frozen class (its `--cipher-util` input names `CipherTransformationUtil.java` for both `jca` and `jca_android`). `Api30CipherTransformationUtil` SHALL NOT be deleted — it keeps no caller and stays as the record of what the withdrawn anchor said, which is what makes the two anchors comparable — and SHALL NOT be given a caller again.

#### Scenario: the constraint table is what G-CONF reproduces on the seed

- **WHEN** G-CONF runs on the frozen `jca` with the pinned expert copy as its value oracle
- **THEN** its per-clause report MUST equal `data/jca_android/constraint_table.csv` row for row — `spec`, the expert clause reference (rule file and line), `mop_line` and the verdict among `CRYSL-NAO-IMPLEMENTADO`, `IGUAL`, `MOP-SEM-BASE`, `MOP-MAIS-PERMISSIVO`, `DIVERGENTE`, `MOP-MAIS-RESTRITIVO`
- **AND** every `CRYSL-NAO-IMPLEMENTADO` row MUST have a matching `deferred-constant` row in `data/jca_android/conformance_record.csv` (INV-INS-125), so no declared clause is left neither transcribed nor deferred
- **AND** every such row MUST quote the **expert** clause text and MUST NOT quote an api30 reconstruction of it: the audit proved two api30 reconstructions (`pre_len > pre_off` in `MessageDigest`, `len > off` in the Cipher streams) are mangled, and a row that quoted them would license implementing a bug

#### Scenario: MD5 and SHA-1 are accused again

- **WHEN** `MessageDigest.getInstance("MD5")` fires against `jca_android/MessageDigestSpec.mop`
- **THEN** it MUST be reported with `error_type=UnsafeAlgorithm`, because the expert clause is `algorithm in {"SHA-256", "SHA-384", "SHA-512"}` and `MD5` is not in it
- **AND** the same MUST hold for `SHA-1`, and for the spellings `SHA1` and `SHA`, which the alias table resolves to `SHA-1` — a resolution that makes the accusation reach *more* calls, not fewer
- **AND** the 5,892 rows of the published corpus that this restores (3,552 `MD5`; 1,915 `SHA-1`; 424 `SHA1`; 1 `SHA`) MUST be the measured acceptance evidence of the re-anchoring, replayed by the C5 harness
- **AND** `SHA-224` MUST be absent from the list even though Android offers it, recorded as an `oracle-wart` row: the expert rule omits it, and correcting a wart privately is the failure mode this requirement exists to undo

#### Scenario: `AES/ECB` is accused again

- **WHEN** `Cipher.getInstance("AES/ECB/PKCS5Padding")` fires against `jca_android/CipherSpec.mop`
- **THEN** it MUST be reported, because `CipherTransformationUtil` admits for `AES` only the modes `{CBC, CCM, GCM, PCBC, CTR, CTS, CFB, OFB}` and `ECB` is not among them
- **AND** the same MUST hold for `AES/ECB/NoPadding`, `DESede/CBC/PKCS5Padding`, `DESede/ECB/PKCS5Padding`, `BLOWFISH/ECB/NoPadding`, `ARC4` and `ChaCha20`, every one of which `Api30CipherTransformationUtil` admits — verified by executing both classes over the same inputs
- **AND** this MUST be replayed by a trace of its own rather than by the C5 corpus: the published `CipherSpec` accusations are 109 rows all carrying the OAEP spelling, so no published number moves and the case would otherwise be an unwitnessed false negative
- **AND** `CipherTransformationUtil.java` MUST be byte-unchanged, gaining a caller and no edit

#### Scenario: the keystore list is the expert list plus the cited platform types

- **WHEN** the conformance gate compares `jca_android/KeyStoreSpec.mop` with `tools/rules/KeyStore.crysl`
- **THEN** the specification's allow-list MUST carry the five expert types `{JCEKS, JKS, DKS, PKCS11, PKCS12}` of the clause `type in {…}` **and** the four `platform-value` entries `{AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}`, and nothing else
- **AND** each of the four MUST have a `platform-value` row in `data/jca_android/divergence_record.csv` carrying a primary-source citation; a candidate without one MUST be dropped from the list and stay accused
- **AND** `KeyStore.getInstance("AndroidKeyStore")` MUST produce no report — 2,005 events over 11 apps and 12 misuses in the published measurement
- **AND** the four JSE types Android does not offer MUST stay in the list, inert, per the no-narrowing rule

#### Scenario: `TLS` is admitted and `SSL` is not

- **WHEN** the conformance gate compares `jca_android/SSLContextSpec.mop` with `tools/rules/SSLContext.crysl`, whose clause is `protocol in {"TLSv1.2", "TLSv1.3"}`
- **THEN** the specification's allow-list MUST be those two entries (in the frozen set's spelling, with its `spelling-variant` note) plus the single `platform-value` entry `TLS`
- **AND** `SSLContext.getInstance("TLS")` MUST produce no report — 8,648 events over 60 apps and 65 misuses, the largest single artefact of the published count — with its `platform-value` row citing `OpenSSLProvider.java:81`, where `SSLContext.TLS` is bound to the TLSv1.2/TLSv1.3 implementation
- **AND** `SSLContext.getInstance("SSL")` MUST still be reported — 103 events — with a `behavioural` row recording that Conscrypt binds `SSLContext.SSL` to that same implementation (`:80`) through a `put` and not an `Alg.Alias`, so the name earns neither a list entry nor an alias row
- **AND** `TLSv1`, `TLSv1.1` and `Default` MUST likewise be reported, none of them being in the expert clause or the closed platform set

#### Scenario: an alias matches and a non-alias does not

- **WHEN** `TrustManagerFactory.getInstance("X509")` fires against the transcribed list `{PKIX, SunX509}`
- **THEN** the alias row `X509 → PKIX`, sourced to `OpenSSLProvider.java:90`, MUST make it match and no report MUST be emitted — 643 events over 3 apps and 5 misuses in the published measurement
- **AND** `TrustManagerFactory.getInstance("SunX509")` MUST **also** produce no report, reversing D-10: `SunX509` is an entry of the expert clause `algorithm in {"PKIX", "SunX509"}`, and that it names a provider absent from Android makes it inert, not removable
- **AND** the alias row MUST appear in `data/jca_android/alias_table.csv` with `service=TrustManagerFactory`, and the allow-list of `TrustManagerFactorySpec.mop` MUST NOT absorb it, so the alias never enters the list it resolves against

#### Scenario: the alias table is code at runtime and a file on disk

- **WHEN** the allow-list check of `jca_android/TrustManagerFactorySpec.mop` resolves `X509`
- **THEN** it MUST call `ConscryptAliasTable` (`rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`) by name, and no runtime read of `alias_table.csv` MUST occur
- **AND** a Java test MUST assert that the class's table and `data/jca_android/alias_table.csv` hold the same rows, `in_allowlist` flag included, so a row added to one and not the other fails
- **AND** the table MUST carry the 11 multi-line registrations the original extraction missed, and the flag column MUST be recomputed against the expert lists
- **AND** no `.mop` of `jca` MUST name that class, so the frozen set's verdicts are unchanged by its existence

#### Scenario: case alone does not make a misuse

- **WHEN** `Signature.getInstance("SHA256WITHRSA")` fires against the transcribed list, which carries `SHA256withRSA`
- **THEN** the case-insensitive comparison MUST make it match and no report MUST be emitted — 4 events over 1 app and 1 misuse in the published measurement
- **AND** no alias row and no `platform-value` row MUST be needed for it, since the two strings differ only in case

#### Scenario: the weak signature algorithms are accused again, warts included

- **WHEN** G-CONF compares `jca_android/SignatureSpec.mop` with `tools/rules/Signature.crysl`
- **THEN** the allow-list MUST be exactly the seven entries of the expert clause — `SHA256withRSA`, `SHA256withECDSA`, `SHA256withDSA`, `SHA384withRSA`, `SHA512withRSA`, `SHA384withECDSA`, `SHA512withECDSA`
- **AND** `NONEwithRSA`, `MD5withRSA`, `SHA1withRSA`, `SHA1withDSA`, `DSAwithSHA1`, `NONEwithDSA`, `SHA224withECDSA` and the `*/PSS` variants MUST all be reported, every one of them having been admitted under the api30 anchor; `NONEwithRSA` carries 4 events of the published corpus and the alias rows for the composite OIDs and `MD5/RSA` make the `MD5withRSA` accusation reach the calls that spell it otherwise
- **AND** the two `api30-omits` rows of D-10 MUST be closed with a note rather than carried: `SHA1withECDSA`, `SHA256withECDSA`, `SHA384withECDSA` and `SHA512withECDSA` were added because api30 omitted them, and three of the four are in the expert clause already — the fourth, `SHA1withECDSA`, leaves the list, and `SHA224withECDSA` leaves it as an `oracle-wart` row

#### Scenario: `EC` and RSA-3072 need no exception any more

- **WHEN** the conformance gate compares `jca_android/KeyPairGeneratorSpec.mop` with `tools/rules/KeyPairGenerator.crysl`
- **THEN** the allow-list MUST be `{RSA, EC, DSA, DiffieHellman, DH}` and the key sizes MUST be RSA `{4096, 3072, 2048}`, DSA `2048`, DiffieHellman/DH `2048`, EC `256`, all five clauses being expert clauses
- **AND** the `api30-omits` divergence row that D-10 needed for `EC` MUST be closed with a note: `EC` is in the expert clause, so the exception it recorded no longer exists
- **AND** the two narrowings D-10 took MUST be undone — `3072` returns to the RSA sizes and `DiffieHellman` to the algorithm list — and their `MOP-MAIS-PERMISSIVO` rows MUST leave the constraint table, the frozen set having been right about both

#### Scenario: the `SecretKeySpec` algorithm check is restored

- **WHEN** `new SecretKeySpec(material, "DES")` fires against `jca_android/SecretKeySpecSpec.mop`
- **THEN** it MUST be reported, the expert clause being `keyAlgorithm in {"AES", "HmacSHA256", "HmacSHA384", "HmacSHA512"}`
- **AND** the list MUST be present in the file at all: D-10 removed it outright to conform to an api30 rule that states no algorithm clause, which the audit recorded as the clearest case of the withdrawn oracle destroying a check the monitor already had
- **AND** the restored check MUST sit in the event bodies beside the predicate reads gh105 placed there, under codes of its own, and MUST NOT re-enter `condition(...)`, which INV-INS-141 forbids for this set

### Requirement: Cipher Transformation Tables of the Archived Derived Set

The `Cipher` transformation tables consulted by the archived set `jca_android_bug_predicate` — the admissible algorithms, their modes, and per mode the admissible paddings — originate in the generated CrySL rule for its declared API level and are reached by `jca_android_bug_predicate/CipherSpec.mop` naming its own utility, `AndroidCipherTransformationUtil` (`rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`), rather than by any runtime selection over a shared one. This requirement now describes that archived pair and only it: the utility belongs to the archived set, is frozen with it, and SHALL stay byte-unchanged, exactly as `CipherTransformationUtil` stays byte-unchanged for the frozen `jca`.

`CipherSpec` is the only specification of any JCA set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java, where the tables are method locals. Selection by the *specification* rather than by the *runtime* is what keeps each set's verdict its own — a shared utility parameterised by the active set would place the `jca` verdict under the control of state set elsewhere (INV-INS-112) — and the successor set names its own utility, `CipherTransformationNormalizer`, which reads through the frozen `jca`'s `CipherTransformationUtil` without editing it (`Requirement: Cipher Transformation Tables of the Successor Set`). `Api30CipherTransformationUtil`, written against the withdrawn api30 anchor, stays in the tree as the record of what that anchor said and keeps no caller. Each set names the utility it answers to, and none is selected at runtime.

#### Scenario: The archived utility is unchanged

- **WHEN** the freeze check runs after any task of this contract
- **THEN** `AndroidCipherTransformationUtil.java` and `CipherTransformationUtil.java` MUST both be byte-identical to `pre-rename-head`
- **AND** `jca_android_bug_predicate/CipherSpec.mop` MUST still name `AndroidCipherTransformationUtil`, and no `.mop` of `jca_android` MUST name it

#### Scenario: Java SE set behaviour is unchanged

- **WHEN** the `jca` set is active
- **THEN** `isValid` MUST return the same verdict it returns today for every transformation
- **AND** that MUST hold because the class it calls was not modified, not because a test asserts it

#### Scenario: A shared table selected at runtime is proposed

- **WHEN** an implementation would give two or three of the sets one utility whose tables are chosen by the active specification set
- **THEN** it MUST be rejected under INV-INS-112
- **AND** the reason MUST be recorded as the frozen set's verdict depending on state set outside its own specification

## ADDED Requirements

### Requirement: Cipher Transformation Tables of the Successor Set

The `Cipher` transformation tables consulted by the successor set `jca_android` — the admissible algorithms, their modes, and per mode the admissible paddings — SHALL transcribe the expert `Cipher` rule of the pinned oracle (D-16), and SHALL be reached by `jca_android/CipherSpec.mop` naming its own utility (`CipherTransformationNormalizer`) rather than by any runtime selection over a shared one.

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

- **WHEN** the coverage matrix is derived and reaches `Cookie.crysl` (`javax.servlet.http.Cookie`, zero entries in the API 30 `android.jar`) or `DSAGenParameterSpec.crysl` (class present only from API 35)
- **THEN** the rule's terminal state MUST be N/A-by-platform with the archive listing as evidence
- **AND** no `.mop` may be written for it

#### Scenario: An oracle defect is recorded, never repaired upstream

- **WHEN** a rule cannot be transcribed as written — `SSLEngine.crysl:12` references the undeclared label `cp1`, `KeyAgreement.crysl:31` references `g2` for `gs2`, `Cipher.crysl:140-141` guards `preparedOAEP` with a vacuous antecedent
- **THEN** the defect MUST become a `divergence_record.csv` row naming the rule and line, and the specification MUST transcribe the evident intent with the row as its warrant
- **AND** the pinned oracle files MUST remain byte-identical

### Requirement: Producer Specifications for Expert Rules

Each new specification SHALL be written against its expert rule alone: the event alphabet realizes the rule's EVENTS (overloads fused per the existing fusion rules), the automaton realizes the rule's ORDER, every value CONSTRAINT is transcribed with an accusing branch (INV-INS-152), predicates are written at the ORDER acceptance point and read in event bodies per the gh105 substrate rules, and every accusation site has a `codes.csv` row. Platform viability is verified before writing (INV-INS-154).

The same obligations bind a specification **already in the set** when a verified finding shows it departs from its rule: the alphabet obligation is INV-INS-157 (the rule's anonymous argument position is realized for every platform overload), the accusation obligation is INV-INS-152 (a value clause living only in `condition(...)` is defective), the value-semantics obligation is INV-INS-153 (producer and reader of one predicate resolve spellings the same way), and the wiring obligation is INV-INS-151 read from the writing end (a predicate three sites read is written). A repair under these obligations changes what the instrument accuses, and SHALL therefore be stated as a ratified decision with a divergence-record row, never applied as silent hygiene.

#### Scenario: Trivial parameter-spec rule becomes a specification

- **WHEN** a rule with `ORDER = Con` and value constraints (e.g. `ECGenParameterSpec.crysl`: `stdName` in the admitted curve list, ensuring `preparedEC`) is implemented
- **THEN** the specification MUST accuse on construction with a name outside the list, write `preparedEC` only on the conforming branch, and declare no events beyond the rule's alphabet
- **AND** the generated monitor MUST be inspected as an artifact (INV-INS-145), never trusted from the generator's exit code

#### Scenario: Value clause transcribed as a silent guard is rejected

- **WHEN** a new or edited specification carries a value constraint only as `condition(...)` on the event, so the violating call takes no transition and emits nothing
- **THEN** the specification MUST be treated as defective under INV-INS-152
- **AND** the repair MUST fuse the test into the event body with an accuser on the violated branch, following the existing `IvParameterSpec` fusion form

#### Scenario: Existing specification narrows the rule's alphabet

- **WHEN** an expert rule writes `getInstance(algorithm, _)` and the platform jar declares three overloads, and the specification's pointcut names only two of them
- **THEN** the specification MUST be treated as departing from the rule under INV-INS-157, because the unnamed route emits no event at all: its value clause cannot accuse, and the object's next observed call draws an ORDER verdict the rule does not state
- **AND** the repair MUST add the missing overload to the same fused event rather than create a second event, so the automaton is untouched and only the alphabet widens to the rule's own

#### Scenario: Producer and reader of one predicate disagree on spelling

- **WHEN** a producer writes `generatedKey` with the algorithm name its own rule ensures (a PBE family name from `SecretKeyFactory.crysl:22-25`) and the consuming site queries with a folded family name derived from the transformation
- **THEN** the store answers VIOLATED for a program that satisfied both rules, which INV-INS-153 defines as a defect of the set rather than a legitimate verdict
- **AND** the repair MUST be made on the side that departed from the letter — here the reader, which SHALL accept the rule's own spelling as well as the folded family name — and MUST NOT introduce a value neither rule names

#### Scenario: Unobserved-predicate line reaches consolidation

- **WHEN** a results consumer aggregates a run whose report contains `-NOBS-` lines alongside `-CONSTR-` lines carrying the same `ErrorType`
- **THEN** the consumer MUST separate them on the `site_kind` column and MUST NOT count a `-NOBS-` line as conformance or as violation (INV-INS-158)
- **AND** the measurement of how often each site answers NOBS remains the harness checkpoint's business (task 7.3), not the consolidation's

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
