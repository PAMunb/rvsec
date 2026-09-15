## Purpose

This delta changes how the successor specification set `jca_android` and the `rvsec-core` classes it calls are documented, and nothing about what they do.

A specification of this set is a transcription of a CrySL rule into JavaMOP. Its comments are the only place a reader learns which clause of the rule an event realises, why a check sits in the event body rather than in a `condition(...)` guard, why a predicate write waits in a field for a handler, or why a handler cannot fire. Those explanations are part of the specification in every sense that matters to someone maintaining it: without them, a missing check cannot be told apart from a deliberate one.

The comments the set carries today mix those explanations with the history of how the set was built: identifiers of OpenSpec invariants and design decisions, task numbers, issue numbers, dates of decisions, rows of the CSV records under `data/jca_android/`, campaign measurements, and line numbers of the rule files and of other specifications. None of that describes the code, all of it requires a document outside the file to be understood, and every line-number citation becomes wrong as soon as either file is edited. The requirement added here fixes the convention a comment of the set follows, so that each comment explains itself and stays true while the code it annotates does.

The same convention binds the helper classes the set calls — the predicate store and its property and verdict types, the report types, the alias table and the `Cipher` transformation normaliser — because their comments carry the same history and a specification comment that explains a call is only as readable as the class it calls. `CipherTransformationUtil` is the one class the set calls that is excluded, because the `jca` set freezes it byte-identical.

Two existing requirements change for a separate reason. They state that `Api30CipherTransformationUtil` stays in the tree as the record of an anchor the set no longer uses. A class kept only to record history is the same kind of content this delta removes from comments: no specification calls it, so it moves to `backup/` together with its test, and the two requirements stop naming it. Nothing else in either requirement changes.

## Data Contracts

### Input
- `rvsec/rvsec-mop/src/main/resources/jca_android/*.mop` — the 47 specifications whose comments are rewritten
- `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/{Property,PredicateStore,PredicateVerdict}.java`, `jca/util/{ConscryptAliasTable,CipherTransformationNormalizer}.java`, `eh/{ErrorType,ErrorDescription,ErrorSummary,Evidence}.java` — the helper classes whose comments are rewritten
- `CROSSINGTUD/Crypto-API-Rules` at commit `6d844ab402229aaefa4c5e45bf080987b787624b`, `JavaCryptographicArchitecture/src/*.crysl` — the upstream rules each specification header cites; 48 of the 49 are byte-identical to the expert copy pinned by `data/jca_android/oracle/expert_rules.sha256`, and `Cipher.crysl` differs from it only by `CCM` in the AES mode clause and in the AES `NoPadding` clause

### Output
- The same files, differing from their previous state only inside comments
- `rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv` — `file_line` column pointing at the line each code is emitted from after the rewrite
- `rv-android/data/jca_android/NEW_SPEC_CONVENTIONS.md` — the convention, for the author of the next specification
- `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` — a "Documentation conventions" section stating the Java documentation convention the helper classes follow

### Side-Effects
- **Repository**: `Api30CipherTransformationUtil.java` and `Api30CipherTransformationUtilTest.java` move to `backup/gh116/`; the two `EXEMPT_CORE` entries naming them in `rv-android/scripts/gh105_sole_oracle_gate.py` are deleted
- **Monitoring**: none — the generated monitor, the instrumented APKs and every violation report are unchanged

### Error
- None. The change adds no code path.

## Invariants

- **INV-INS-168**: A comment of a `jca_android` specification or of a helper class listed in "Documentation Convention of the `jca_android` Specification Set" MUST NOT contain a line number of any file, an identifier of an OpenSpec invariant, decision, task, change or issue (`INV-INS-133`, `D-15`, `task 11.5`, `gh105`, `#101`), a date, a reference to a record under `data/jca_android/` or to a report, a campaign measurement, a reference to the `jca` set, or promotional or bias language ("modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge", "advanced"); the set's own `codes.csv` MAY be named. The review that establishes this MUST keep every comment that already complies and MUST leave every non-comment token of those files unchanged.

## ADDED Requirements

### Requirement: Documentation Convention of the `jca_android` Specification Set

Every comment of a `.mop` file under `rvsec-mop/src/main/resources/jca_android/`, and of the helper classes `Property`, `PredicateStore`, `PredicateVerdict`, `ConscryptAliasTable`, `CipherTransformationNormalizer`, `ErrorType`, `ErrorDescription`, `ErrorSummary` and `Evidence` in `rvsec-core`, SHALL be self-contained: a reader MUST be able to understand it with the file open and nothing else. A comment SHALL describe what the code does now (P4) and SHALL NOT refer to anything outside the code and the CrySL rules — no change, issue, invariant, decision, task, date, record under `data/jca_android/`, report, measurement, other specification set, or line of any file — and SHALL NOT use promotional or bias language ("modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge", "advanced") (INV-INS-168). The set's own `codes.csv`, which maps each report code to its site, MAY be named.

The documentation of the `.mop` set SHALL be detailed. Every event, predicate read and predicate write carries its own comment, even where a neighbouring event realises the same rule label, and a comment explains its site completely rather than briefly: the reader of a specification is reconstructing why a check exists or is absent, and a comment left out because the code looked self-evident is indistinguishable from an omission. A comment that already complies with this requirement SHALL be kept as it is.

**Java helper classes.** The helper classes SHALL follow the Java documentation convention written in the "Documentation conventions" section of `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`, which maps the `rv-doc-code` conventions onto Javadoc and keeps the house style of that module: (1) depth by tier — full Javadoc for public API and orchestrators, summary with `@param`/`@return` for internal methods over ten lines, one line for small helpers, and no Javadoc for self-evident accessors, setters and `toString`; (2) a package or class Javadoc opens with a noun phrase saying what it is, a method Javadoc with an imperative sentence ending in a period; (3) class sections are topical `<h2>`/`<h3>` headings, not a fixed vocabulary; (4) `@param`, `@return` and `@throws` carry no types, and `@throws` states its condition with "when" or "if"; (5) a field with meaningful state carries a one-line Javadoc; (6) a `@return` of a map or JSON document lists its keys; (7) inside a method, `// Phase N:` marks orchestration phases, `// Step N:` marks algorithm steps, and a rationale block sits directly above the code it explains; (8) contracts use `MUST`/`MUST NOT` and `Precondition:`/`Postcondition:`; (9) code is cited with `{@code}` and `{@link}`, and every `{@link}` target exists; (10) no invariant, decision, task, change or issue identifier, date, `file:line`, reference to `architecture.md` or to a report, history narrative, or promotional language; (11) `TODO(topic)` and `FIXME(topic)` name a module or topic, never an issue number. Unlike the `.mop` set, trivial Java members are not documented: a comment is written only where it tells the reader something the signature does not.

**Relation to the CrySL rule.** The file header SHALL name the class the specification monitors and the CrySL rule it transcribes, summarise what the specification checks (the order, the value constraints, the predicates it requires and ensures), and state the divergences from the rule and the reach limits of the monitor. Its `@see` SHALL point to the rule in `CROSSINGTUD/Crypto-API-Rules` at commit `6d844ab402229aaefa4c5e45bf080987b787624b`, not at a moving branch or a ruleset release: that commit holds the JCA rules the specifications transcribe, and it is byte-identical to the rule set the CogniCrypt 5.0.1 baseline ran. Where a specification admits a value its cited rule does not list, the header SHALL state it as behaviour; in the set this is `CipherSpec`, which also admits `CCM` for AES, with `NoPadding`. Each event, predicate read and predicate write SHALL say which label or clause of the rule it realises, **quoting the clause by its text** — its section (`EVENTS`, `ORDER`, `CONSTRAINTS`, `REQUIRES`, `ENSURES`, `NEGATES`, `FORBIDDEN`), its label, and the clause between backticks — and SHALL NOT cite it by line number, because the clause text identifies the clause in every version of the rule and a line number identifies it in one.

**Mechanism.** Where the placement or shape of the code is not obvious at the site, the comment SHALL explain it where it appears, even when the same explanation appears in another file: that a clause is checked in the event body because a `condition(...)` guard runs before the transition and would silence a violating call; that a predicate write is staged in a field because a handler receives no event arguments and runs after the transition is decided; that an `@fail` handler of a single-symbol order cannot fire and is written because the generator expects it; that a read separates a violated predicate from an unobserved one because the second is as often a reach limit of the instrumentation as a misuse. A comment MAY name another specification of the set, and its event, as the producer or consumer of a predicate, provided the comment is understandable without opening that file.

**Divergences and constraints of the toolchain.** A difference between the specification and its rule SHALL be stated as behaviour with its technical reason, never as the decision that produced it. A constraint of the monitor generator that fixes the shape of a file — the 17-event ceiling, the deduplication of imports by class name across the merged monitor — SHALL be stated briefly where it applies.

**Scope of the review.** A change that reviews comments under this requirement SHALL rewrite only the comments that do not comply, SHALL leave every non-comment token of the files unchanged, and SHALL update the `file_line` column of `jca_android/codes.csv` to the line each code is emitted from afterwards. `CipherTransformationUtil` SHALL NOT be edited, because the `jca` set freezes it byte-identical. `data/jca_android/NEW_SPEC_CONVENTIONS.md` SHALL state this convention, so a specification added to the set is written under it.

#### Scenario: a value constraint is cited by its text

- **WHEN** the comment above the digest list of `MGF1ParameterSpecSpec.mop` relates the list to its rule
- **THEN** it MUST quote the clause as `CONSTRAINTS` of `MGF1ParameterSpec.crysl`: `mdName in {"SHA-256", "SHA-384", "SHA-512"}`
- **AND** it MUST NOT contain `MGF1ParameterSpec.crysl:14` or any other line number

#### Scenario: a mechanism is explained instead of cited

- **WHEN** a comment of `CipherSpec.mop` explains why the key-origin read of event `i2` is in the event body
- **THEN** it MUST say that a `condition(...)` guard compiles to an early return ahead of the body and of the transition, so a key whose producer was never observed would drop the `init` out of the automaton and the next call would be reported as a wrong call sequence
- **AND** it MUST NOT contain `INV-INS-133`, a decision identifier, or the words "used to"

#### Scenario: a reach limit is stated as behaviour

- **WHEN** the comment of `MGF1ParameterSpecSpec.mop` explains objects obtained from the static constant `MGF1ParameterSpec.SHA256`
- **THEN** it MUST say that the constant is built inside the platform, where nothing is instrumented, so the constructor event never fires for it and the object carries no `preparedMGF1` predicate
- **AND** it MAY say that `OAEPParameterSpecSpec` therefore reports such an object as not observed rather than as a violation
- **AND** it MUST NOT cite the invariant that separates the two report families or a campaign count

#### Scenario: a file that exists because of a generator limit says why

- **WHEN** the header of `IvChainJunction.mop` explains why the file exists beside `CipherSpec.mop`
- **THEN** it MUST say that the clauses it reads bind the parameter-spec, `SecureRandom` and plaintext arguments of `Cipher` calls that `CipherSpec`'s events do not bind, and that `CipherSpec` cannot gain an event because it already declares 17, the most the monitor generator can build
- **AND** it MUST NOT justify the file's name by the changes, traces or reports that cite it

#### Scenario: the header cites the upstream rule at the pinned commit

- **WHEN** the header of `CipherSpec.mop` is read
- **THEN** its `@see` MUST be `https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b/JavaCryptographicArchitecture/src/Cipher.crysl`
- **AND** the header MUST state that the specification also admits `CCM` for AES, with `NoPadding`, which that rule does not list
- **AND** no other header of the set MUST carry such a statement, because the other 48 rules the set answers to are identical to the cited commit

#### Scenario: the rewrite leaves the code unchanged

- **WHEN** the comments of `KeyStoreSpec.mop` are rewritten
- **THEN** removing every comment from the file before and after the rewrite MUST yield the same token sequence
- **AND** the `file_line` of every `KEYSTORE-*` row of `jca_android/codes.csv` MUST name the line that emits that code after the rewrite

#### Scenario: a compliant comment is kept and every event keeps its own comment

- **WHEN** the comments of `MGF1ParameterSpecSpec.mop` and `CipherSpec.mop` are reviewed, and the field comment `Bound only on the conforming branch, which is what carries the object to `@match`.` of `MGF1ParameterSpecSpec.mop` already complies
- **THEN** that comment MUST be left byte-identical
- **AND** each of the five `update` events `u1`–`u5` of `CipherSpec.mop` MUST carry its own comment naming the rule's `Update` label and the overload it binds, even though all five realise the same label
- **AND** a comment MAY say that a report code is registered in the set's `codes.csv`, and MUST NOT name `data/jca_android/predicate_ledger.csv` or any other record under `data/jca_android/`
- **AND** no comment MUST describe the set or its checks as "modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge" or "advanced"

#### Scenario: a helper class follows the same convention

- **WHEN** the class comment of `CipherTransformationNormalizer.java` is rewritten
- **THEN** it MUST describe what the normaliser resolves and folds before delegating to `CipherTransformationUtil`, and MUST NOT name a class that is no longer in the tree, a decision identifier or a task
- **AND** `CipherTransformationUtil.java` MUST be byte-identical before and after the change
- **AND** a self-evident member such as a plain getter MUST carry no Javadoc, while `PredicateStore.validate` MUST carry a method Javadoc opening with an imperative sentence and stating what each `PredicateVerdict` answer means

#### Scenario: the Java convention is written where the module keeps its conventions

- **WHEN** `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` is read after the change
- **THEN** it MUST contain a section titled "Documentation conventions" that states the eleven rules of the Java convention of this requirement
- **AND** that section MUST NOT cite invariant, decision, task or issue identifiers, and MUST NOT refer to `architecture.md` sections as a substitute for an explanation

#### Scenario: the next specification is written under the convention

- **WHEN** an author opens `data/jca_android/NEW_SPEC_CONVENTIONS.md` to write a new specification for the set
- **THEN** the document MUST state the comment convention of this requirement: self-contained comments, clauses quoted by text, no line numbers, no references outside the code and the rules
- **AND** its own guidance MUST NOT cite invariants, decisions or line numbers of `.mop` files

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

The `Cipher` transformation tables SHALL stay in Java. `CipherTransformationUtil` — the class of the frozen `jca`, which transcribes the expert `Cipher.crysl` and is what the published numbers were measured with — stays byte-identical: the freeze (INV-INS-109/118) forbids **editing** it, not **calling** it, and `jca_android/CipherSpec.mop` imports it and reaches it through `CipherTransformationNormalizer`, so no verdict of the frozen set moves. The normaliser is the one place the successor set's `Cipher` values move, under `Requirement: Cipher Transformation Tables of the Successor Set`: it reproduces `CipherTransformationUtil`'s value clauses, resolves the pinned Conscrypt aliases and folds case before comparing, and admits the eight `PBEWithHmacSHA{224,256,384,512}AndAES_{128,256}` families `Cipher.crysl` admits (D-20.1). G-CONF keeps comparing against the frozen class (its `--cipher-util` input names `CipherTransformationUtil.java` for both `jca` and `jca_android`).

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
- **AND** the same MUST hold for `AES/ECB/NoPadding`, `DESede/CBC/PKCS5Padding`, `DESede/ECB/PKCS5Padding`, `BLOWFISH/ECB/NoPadding`, `ARC4` and `ChaCha20`
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

`CipherSpec` is the only specification of any JCA set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java, where the tables are method locals. Selection by the *specification* rather than by the *runtime* is what keeps each set's verdict its own — a shared utility parameterised by the active set would place the `jca` verdict under the control of state set elsewhere (INV-INS-112) — and the successor set names its own utility, `CipherTransformationNormalizer`, which reads through the frozen `jca`'s `CipherTransformationUtil` without editing it (`Requirement: Cipher Transformation Tables of the Successor Set`). Each set names the utility it answers to, and none is selected at runtime.

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
