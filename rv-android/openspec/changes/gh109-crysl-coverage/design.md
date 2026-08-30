# Design: gh109-crysl-coverage

## Context

Successor of gh105 (`gh105-predicate-wiring`). The substrate that change built — `PredicateStore`, reads in event bodies, the gate layer (G-ORDER, G-PRED2, G-ACC, G-PARAM, G-CONF), the divergence record keyed by hunk, and the sole pinned oracle (D-16: `RVSec-replication-package/tools/rules/`, 49 rules, sha256 `d7bcc019…`) — is taken as given and not redesigned. What moves is the coverage boundary: from the seed's 22 rules to all 49, each with a derivable terminal state, plus 9 verified repairs to existing specifications. FR01–FR03 (monitor generation pipeline), NFR06 (measurement integrity), NFR07 (reproducibility).

Evidence base: the five external analyses (`docs/analise_gh105_{gemini3,glm53,gpt5,grok4,opus5}.md`) were mined for candidates only. Every adopted item was re-verified this session against primary sources — the expert rule text, the live `.mop`, the generated monitor, `rvsec-core` Java, and the API 30 `android.jar` via `unzip -l` (never `javap -cp`, which resolves against the host JDK). Verification changed several claims materially (see D-18), which is why adoption-without-verification is banned.

## Decisions

Numbering continues the gh104/gh105 chain (last: D-17; gh104 also holds the out-of-sequence D-30, which this chain avoids).

### D-18 — Analyses are candidate generators; only source-verified claims are adopted

Adopted after verification (with corrections the verification itself produced):

| # | Finding (verified state) | Evidence anchor |
|---|---|---|
| R1 | `DHGenParameterSpecSpec.mop:24` carries `exponentSize < primeSize` as `condition()` on the only event; violation = total silence (no transition, no report, no `PREPARED_DH` write); `codes.csv` has only the ORDER code | spec + `codes.csv:15` |
| R2 | `KeyPairGeneratorSpec.mop:101-105` `init2` (`initialize(int, SecureRandom)`) has the positive guard and no accusing twin; the 1-arg overload has `initError` (:155-162). Correction from verification: if the trace continues to `generateKeyPair()` an ORDER report fires late — the defect is silence *at the site* plus misattribution, not always total silence | spec |
| R3 | `MessageDigestSpec` 2-arg `getInstance` routes: `update`/`d2` carry the value check, `d1`/`d3` do not — `getInstance("MD5", provider)` + direct `digest()` yields ORDER only. Verified again at G0.7, the same file yielded a second finding of a different kind: it never writes `generatedMessageDigest`, which `MessageDigest.crysl:46` ensures and tasks 3.6/3.7 read (see the producer-gap paragraph below); the write joins R3's task as 1.3(b) | spec :54-64, :79-86, :94-98, :123-131; rule `MessageDigest.crysl:46` |
| R4 | `CipherOutputStreamSpec.mop:62` `ere: c1 (w1|w2|fl)+ cl` — `fl` erases to ε against the rule's alphabet, so `c1 fl cl` (close without ciphering) is accepted; rule `ORDER Con, Write+, Close` rejects it | spec + `CipherOutputStream.crysl:24` |
| R5 | `SecretKeySpec.mop:102-104` pointcut `call(public byte[] SecretKey.getEncoded())` without `+`: static-type `SecretKeySpec` receivers never weave; the `preparedKeyMaterial` bridge silently never fires for them. Only interface-owned pointcut in the set | spec |
| R6 | `CipherSpec.mop:177` `GENERATED_KEY` read uses the frozen raw splitter (`CipherTransformationUtil.alg`). Correction from verification: swapping to `CipherTransformationNormalizer.alg` fixes real aliases but NOT `AES_128` (no alias row — Conscrypt registers it as its own service); that half requires the D-20 value decision | `CipherTransformationUtil.java:10-15`, `ConscryptAliasTable.java:101-114` |
| R7 | `CipherTransformationNormalizer.isValid` collapses to `{AES, RSA}`; the 8 `PBEWithHmacSHA*AndAES_*` families `Cipher.crysl:90-105` admits are accused. The gap is documented in the normalizer's own javadoc as a deferred value decision — D-20 ratifies it now | `CipherTransformationNormalizer.java:140-152`, javadoc :44-45 |
| R8 | `KeyGeneratorSpec.mop:215` writes the raw user spelling into `GENERATED_KEY`; readers query canonical names; `PredicateStore` only lowercases. Alias spellings (`HMAC/SHA256`, OIDs, `RC4`→`ARC4`…) break propagation silently (symptom: downstream NOT_OBSERVED). `MacSpec` already immunizes itself via `validateAny` — the repair is to write canonical at the producer | `ConscryptAliasTable.java:143-146`, `PredicateStore.java:172-175` |
| R9 | `IvParameterSpec.mop:119-121` tests `len >= 0` where `IvParameterSpec.crysl:19` requires `len > 0`, in an `else if` with no accuser; the only reachable violating case is `len == 0`, which today passes *and* writes `PREPARED_IV` | spec comment :89-101 |

Rejected or corrected during verification (recorded so they are not re-adopted): the "one-line splitter fix" framing of R6 (see above); "Mac/Signature 2-arg guards silence the value accusation" — refuted, the accusation migrates to the init events (`MAC-ALG-00` + ORDER co-emission), the residue is a registered deliberate deferral and stays; "9 dead `current*` fields" — count is 8 (`KeyGeneratorSpec` reads its own at :172); `PBEKeySpecSpec.mop:72 remove(` — stale citation, site is `negate` at :188.

Not reopened (already adjudicated by the researcher): `KeyPair` mandatory constructor (gh105 task 11.6), `SSL` accused / `TLS` admitted (D-15), the two-argument-guard family deferral (gh105 task 10.8(a), divergence row F7).

### D-19 — Coverage terminal-state model (three states; a defect is an attribute)

The model has **three** terminal states — `covered | na-platform | na-value` — and an oracle defect is an attribute of the rule's row (`oracle_defect_row`), never a fourth state. A fourth state would put `Cipher` in two states at once: it is already paired, and 0.1 records a defect against `Cipher.crysl:140-141`. It would also be empty, since `SSLEngine` and `KeyAgreement` are transcribed by evident intent in 4.1 and 4.3 and end `covered`.

`covered` asserts pairing and adjudication, not clause completeness. That distinction is measured, not stylistic: under a strict reading — a REQUIRES clause with no possible producer, or a CONSTRAINTS clause the `.mop` does not implement — **15 of the 22 currently paired rules** carry at least one clause with no verdict surface (`constraint_table.csv` reads 42 `CRYSL-NAO-IMPLEMENTADO` and 14 `NAO-DERIVADO` against 22 `IGUAL`; `predicate_graph.csv` records 12 `omission` rows). The depth axis is therefore *not* re-derived here: it already exists, per rule, in the `rvsec-crysl` conformance component (M0 Vitality, M1 Events, M2 Order, M3 Constraints, M4 Predicates, plus `SpecRulePairing`, `Silence`, `ConformanceReport` and the `compare` CLI, all under CI) and clause by clause in `constraint_table.csv` / `predicate_ledger.csv`. Duplicating it inside the matrix would be the second translation of the oracle that this change's own MODIFIED requirement forbids for the `Cipher` tables — and the set already refused this granularity once, deliberately, in `ErrorType`'s javadoc ("*There is deliberately no `RequiredPredicate`*"). The caveat that rides along with citing M0–M4 is measured: the component's oracle is `rvsec-cognicrypt/CrySL-Rules` at `f2f4d3b`, which differs from the pinned expert copy in **one file and two lines** (`Cipher.crysl:97` and `:113`, the `CCM` entry in the AES mode and padding clauses) — already an `oracle-wart` divergence row.

49 rules = 22 paired today + 24 new specifications + 3 adjudicated N/A (`Cookie` — `javax.servlet` absent from the API 30 `android.jar`; `DSAGenParameterSpec` — class only at API 35+; `PasswordAuthentication` — class exists but both constraints (`neverTypeOf`, `notHardCoded`) are static-analysis predicates unrealizable in RV and `generatedPasswordAuthentication` has no consumer among the 49, so a producer-only spec would add monitoring with no verdict surface; adjudicated recorded-N/A-by-value, ratified, per INV-INS-156. The earlier wording — "the ORDER admits every trace" — is withdrawn as imprecise: `Con, (GetPassword | GetUserName)*` does refuse a `getPassword()` on an object whose construction went unobserved, exactly as any `ere : c1 …` of the set does. What the adjudication rests on is the other two legs, and the ORDER residue is recorded rather than assumed away). `HMACParameterSpec` keeps its `.mop` but its terminal state is N/A-by-platform (INV-INS-155). `SecretKey` is covered by adjudicated mapping: `SecretKeySpec.mop` realizes the rule's ENSURES and its `Destroy` tail is recorded platform-dead (INV-INS-137 — `destroy()` throws on every observable implementation), so no reachable trace yields a further verdict; the ledger's `NON_PAIRING_FILES` governs specification pairing only, and the coverage matrix carries the mapping explicitly (task 0.4). Work inventory for the 24, from the viability census (all classes confirmed in the API 30 `android.jar` by archive listing):

| Tier | Rules | Shape |
|---|---|---|
| Trivial (13) | RSAKeyGenParameterSpec, ECGenParameterSpec, ECParameterSpec, DSAParameterSpec, DHParameterSpec, OAEPParameterSpec, MGF1ParameterSpec, KeyStoreBuilderParameters, CertPathTrustManagerParameters, PKIXParameters, PKIXBuilderParameters, TrustAnchor, X509EncodedKeySpec | `ORDER = Con`, one event per overload the rule labels — 18 events over the 13 files (2 each for DHParameterSpec, PKIXParameters and PKIXBuilderParameters, 3 for TrustAnchor, 1 for the rest); value constraints with accusers, one predicate write on the conforming branch |
| Trivial-interface (1) | Key | `GetEnc*` — one event, `Key+.getEncoded()` (subtype owner, same lesson as R5), writes `preparedKeyMaterial` |
| Medium (7) | AlgorithmParameters, AlgorithmParameterGenerator, SecretKeyFactory, KeyFactory, CertificateFactory, DigestInputStream, DigestOutputStream | 2–4 events, short ORDER; Digest streams carry a FORBIDDEN `on(boolean)` |
| Complex (3) | KeyAgreement (5 events incl. `noCallTo[gs3]`), SSLEngine (2 events; oracle defect `cp1`), SSLParameters (3 constructor paths) | need the oracle-defect rows of D-21 before transcription |

Closing the trivial tier plus the first two medium specs closes all six producer gaps: `preparedRSA` (RSAKeyGen), `preparedEC` (ECGen/ECParam), `preparedDSA` (DSAParameterSpec — the Gen variant is N/A), `preparedOAEP` (OAEP+MGF1), `preparedAlg` (AlgorithmParameters/Generator — medium tier), `generatedManagerFactoryParameters` (KeyStoreBuilderParameters/CertPathTrustManagerParameters). Five of six close in the trivial tier; `preparedAlg` closes with 3.1/3.2. The ledger also carries two `unmonitored-producer` predicates beyond the six: `preparedDH` (closed by 2.5) and `preparedKeyMaterial` (written by 2.14, fully closed with 4.3) — INV-INS-151's zero-`unmonitored-producer` criterion counts all eight.

**A ninth, of a second shape, found while closing G0.** The eight above share one form — every rule that could produce the predicate is among the 27 absent, so no `.mop` writes it. `generatedMessageDigest` has the opposite form: its producing rule, `MessageDigest`, is present and paired, and the omission is in the transcription. `MessageDigest.crysl:46` ensures `generatedMessageDigest[this] after Get`; `MessageDigestSpec.mop` writes only `Property.DIGESTED`. The enumeration that produced the six could not see it, because it ran over the absent rules; and the ledger does not show it today either, because the two rules that require the predicate — `DigestInputStream` and `DigestOutputStream`, tasks 3.6 and 3.7 — have no `.mop` yet, so rows #17, #18 and #103 all rest on `unmonitored-consumer`/`unmonitored-consumer-side`. Landing those two specs falsifies that reason, and from that moment the honest disposition would be `unmonitored-producer` and the two reads would answer NOT_OBSERVED for every program: the shape D-24 exists to forbid. The write therefore lands in G1, folded into task 1.3 as **1.3(b)** — the researcher's call, taken because R3 already edits that file and the producer must exist before G3 opens its consumers. INV-INS-151's criterion counts nine from G3 on, and 1.3(b) is what keeps the ninth at zero.

### D-20 — Ratified value decisions (they change what is accused; stated here, once)

1. The normalizer admits the 8 expert-admitted PBE families (CBC/PKCS5 forms) — fidelity to the oracle beats the inherited `{AES, RSA}` collapse.
2. `AES_128`/`AES_256` compare equal to `AES` in the key×transformation check (Conscrypt keysize-suffixed services over the same family; a family key used with the suffixed service is not a misuse).
3. Producers of algorithm-valued predicates write the canonical name (`ConscryptAliasTable.canonical`); readers keep their existing semantics.
4. `p >= 1^2048` in `DSAParameterSpec.crysl`/`DHParameterSpec.crysl` is transcribed as *bit-length ≥ 2048* (`p.bitLength() >= 2048`), with a divergence-record row noting the oracle's notation (literally `1^2048 = 1`).
5. `SSLContext.getSocketFactory` is NOT added as an event: it is outside the oracle's alphabet, and this change adds no accusation surface the oracle does not name (AndroidKeyStore exclusion follows the same principle).

### D-21 — Oracle defects: recorded, transcribed by evident intent, never edited upstream

`Cipher.crysl:140-141` (`preparedOAEP` vacuous antecedent — `mode()` over padding literals; neighbor clauses :138-139 show the correct form), `SSLEngine.crysl:12` (`EnableProtocol := cp1` — label undeclared; evident intent `ep1`), `KeyAgreement.crysl:31` (`GenSecretBuffer := gs1 | g2` — evident intent `gs2`), the `1^2048` notation (D-20.4), and `OAEPParameterSpec.crysl:8` (orphan object `alg`, anomaly note only). Each becomes a `divergence_record.csv` narrative row before the specification that depends on it is written; the pinned rules stay byte-identical. The rows go in under the vocabulary that already exists — `kind = oracle-wart` (4 rows today) — and with the **rule** in the record's `file` column (`tools/rules/Cipher.crysl`, and so on; the column already carries non-`.mop` paths such as `MetaCrySL/generated/api30/`). That is what makes `coverage_matrix.csv`'s `oracle_defect_row` a join derivable by enumeration instead of a judgement typed by hand. A defect never becomes a terminal state (D-19): the rule it belongs to is transcribed by evident intent and ends `covered`, carrying the row as its warrant.

### D-22 — Light execution protocol (the anti-gh105-ceremony decision)

The gh105 apparatus stays in force; what changes is *when* it is fed:

- **Records per batch, not per hunk-edit-moment**: each task group ends with one records pass (`gh104_divergence_record.py --refresh` + fill, `gh105_predicate_graph.py --emit`, ledger/alphabet `--check`/re-emit). The recorder's refresh flow preserves reasons, so batching is safe.
- **New file = one `new-file` divergence row** (precedent: `IvChainJunction`), not a hunk-by-hunk baseline.
- **Differential harness at two checkpoints** (after G1 repairs; at final verification), not per task. Trace pairs are added only for the repairs whose accusation surface changes (R1, R4, R9) and per new-spec tier exemplar, not per file.
- **Monitor generation once per session/group** (77–79 s, inspect artifact per INV-INS-145), full `tests/parity` + Maven gh106 tests once per milestone.
- **Parallel dispatch**: `tasks.md` is the roadmap; `tasks/G*.md` carry per-group detail. Within G2/G3 every spec is an independent task touching disjoint files; shared files (`codes.csv`, records, CI constants) are owned by named tasks so parallel subagents never co-edit them.

### D-23 — Enforcement-surface changes a new file requires (measured, not guessed)

From the compliance-cost survey of this session, re-measured after the first pass under-counted the Java side: gh106 CI constants `Corpora.java:28` (24→N), `MopLiftCorpusTest.java:118,129` (215→N) **and the corpus-wide pins the same file carries — `:143` `assertEquals(907, total.events())`, `:144` `assertEquals(381, total.parameters())`, `:196` `assertEquals(907, checked)`, `:276`/`:277` (42 refusing files / 56 `OverlappingDispatch` refusals), plus the `@DisplayName` literals at `:122` and `:134`**; `CalibrationTargets.java:69` (string literal) **and `:70`, the per-corpus list (`"jca_android 24/24"`)**. Note that R2 alone moves the event total, so the re-pin is owed by G1 as well as by the first spec of G2. G-PARAM pinned count `tests/parity/test_gh105_predicate_gates.py:1868` (24→N) with the `.rvm`-preserving fixture regeneration (docstring :1836-1861); G-ORDER skip-set pin `:2287` and `MAP_HEADER` prose; alphabet-map chain via `gh105_expert_alphabet.py --emit`; ledger pairing is automatic for `<Rule>Spec.mop` names. These are owned by G6 tasks, updated once per milestone.

### D-24 — The producers land and the unblocked reads open (ratified)

Closing a producer gap moves a ledger disposition; it does not, by itself, move a verdict. Measured this session: of the eight predicates INV-INS-151 counts, `preparedKeyMaterial` already has a live read (`SecretKeySpecSpec` `c1`/`c2`) and four more gain one from the new specifications themselves (`preparedEC`, `preparedDH` from 4.3 and 3.1; `preparedAlg`, `preparedOAEP` from 3.1). The other three — `preparedRSA`, `preparedDSA`, `generatedManagerFactoryParameters` — would end this change **written by a brand-new specification and read by nobody**, which is exactly the ground on which D-19 adjudicates `PasswordAuthentication` N/A-by-value.

This is not new scope; it is the completion of a decision the set already recorded **conditionally**, and whose condition this change removes:

- `KeyPairGeneratorSpec.mop:107-144` — `init3`/`init4` "bind the `params` of the rule's four guarded REQUIRES clauses … **and read none of them**", because "*what would close it is a `.mop` for `DHParameterSpec`*". Task 2.5 writes that file; 2.1 and 2.4 write the RSA and DSA producers.
- `TrustManagerFactorySpec.mop:135-141` (twin at `KeyManagerFactorySpec.mop:114-141`) — "*the event already binds `arg` and already discriminates by runtime type, so an `else if (arg instanceof ManagerFactoryParameters)` would cost three lines. What it would buy is an accuser that can answer NOT_OBSERVED and nothing else*". Tasks 2.8 and 2.9 write the two producing rules.

**Ratified**: the three sites open, in group G1b, after G2 (the producer must exist first). Each read follows the gh105 substrate — read in the event body, guarded clause form for the four algorithm-conditioned ones — with an accuser on the VIOLATED branch and a `-NOBS-` code of its own on NOT_OBSERVED, so a program that built its parameter spec outside the monitored set stays distinguishable from one that violated the clause. This changes what is accused, so it carries divergence rows and trace pairs like the D-20 decisions, and the campaign-comparability caveat applies.

**One read stays closed, and the reason is structural, not editorial.** `Cipher.crysl:136` requires `preparedAlg[params, alg(transformation)]`, where `params` is bound only by the rule's `i5`/`i7` (`init(encmode, key, params[, random])`). `CipherSpec`'s `i2` fuses every `init(int, Key, ..)` overload under `args(mode, key, ..)` and binds no third argument; giving it one, or adding an event, collides with the 17/17 ceiling this design forbids moving. Recorded as a deferral in the F7 form, with the ceiling and the missing binding named, so the ledger's disposition for that clause is a measured impossibility rather than an unexplained silence.

**A producer gap can also hide behind a rule that is paired.** The six gaps this decision enumerates were derived from the 27 absent rules, and that derivation is complete only for gaps of that form. Closing G0 surfaced one of the other form — `generatedMessageDigest`, whose producing rule is paired and whose `.mop` simply does not write it (see the producer-gap paragraph above). The lesson is a check, not a scope change: a predicate is unwired when the *write* is missing, and a rule having a `.mop` does not establish that its `.mop` writes what the rule ensures. Task 3.R re-derives the ledger with that in mind, and 7.2 asserts the property over every predicate the set writes, from both sides.

**The NOBS branch is provisional until measured.** The three sites are the shape of the seventeen orphan accusers gh105 group 3 removed, and whether they are worth keeping is an empirical question about the corpus, not an argument. Task 7.3 reads the NOBS rate for each new site at harness checkpoint 2; the researcher decides then whether any NOBS branch is retired to a recorded silence.

**A producer that lands a group before its consumers needs a word for the interval, and the write-side vocabulary did not have one.** Task 1.3(b) writes `generatedMessageDigest` in G1; its only readers, 3.6 and 3.7, are G3. Between the two the set carries a predicate written and read by nobody, which is what G-PRED2 exists to catch, and it catches it — three findings, one per site. The gate closes a reader-less write on one of two words (`gh105_predicate_graph.py`, `RECORDED_WRITE_DISPOSITIONS`): `propagation`, which this is not, and `omission`, documented in the script itself as *"an `ENSURES`-only dead end"* — no rule of the oracle requires the predicate. That is false here: `DigestInputStream.crysl:33` and `DigestOutputStream.crysl:34` require it, and writing their specifications is the plan of this change. Recording `omission` would record as settled the very thing the change exists to undo. **Ratified (2026-08-26): `unmonitored-consumer` is admitted as a write disposition.** It is the word the read side already carries with the roles mirrored — a read whose producing rule has no `.mop` ↔ a write whose consuming rules have no `.mop` — and it is the word `predicate_ledger.csv` already uses for these three clauses, at rows #17, #18 and #103. Admitting it **does not loosen the gate**: a write with no reader still has to name why, and the count of closable rows is unchanged. What changes is which reasons are sayable, and before this the only sayable one was untrue. The disposition is **transitory by construction**: task 3.R must see it leave when 3.6/3.7 land. It is legitimately still standing at M1, because G3 is M2 work, so 7.2 enumerates the transitory dispositions and names the task that owes each retirement, and 7.3 asserts at M2 that none survived — a disposition that outlives its reason is a false record, which is the same rule that retired the `CipherOutputStreamSpec` allow-list line when R4 supplied the measurement it was waiting for. One record is amended in the same pass: `PBEKeySpecSpec.mop`'s row states that "`unmonitored-consumer` … is a *read* disposition and can close no write", which was true of the closure gh105 reached and is not true of the vocabulary this change needs.

**The same arithmetic makes every recorded omission perishable, and the group records passes are where it is checked.** G-PRED2 accumulates written and read predicate names over the whole set and then judges each row against those two sets (`gh105_predicate_graph.py:1511-1553`). So the moment any specification reads a name, *every* write row of that name stops being a finding — and its `disposition` and its `reason`, often several hundred words of measured argument, stop being read by anything at all. A change that lands thirteen new consumer specifications is therefore a change that can silently strand recorded omissions written when no consumer existed. The criterion is not a list of rows fixed here, because the readers do not exist yet to measure against: each group's `X.R` re-derives the disposition of **every** write row of the graph, not only the rows its own tasks created, and any recorded reason a landed consumer falsified is amended or moved in that same pass.

### D-25 — The second validation wave lands in this change, not in a new one

Four independent external reports (`docs/analise_gh105_{gemini3,gpt-5,grok-4.6,opus5}.*`, 27/08) were
adjudicated against the primary sources in seven read-only verification lots; the consolidated result is
`docs/20260827_relatorio_final_validacao_jca_android.md`. The findings are the **same kind of work this
change already owns** — repairs to existing specifications, predicate wiring, and truthful records — so
they land here rather than in a successor change (researcher decision, 28/08). Three consequences:

1. The verification is D-18 applied a second time: every item below was re-verified in the primary
   sources, and ~20 claims of the reports were **refuted or found already recorded** (the CCM registration,
   the RSA/ECB padding wart, `nextInt`, the MessageDigest negated-twin row, the AES-keysize deferral, the
   `RandomStringPassword` retirement). They are listed in the adjudication document so they are not
   re-adopted later.
2. Milestone M2 grows: G8 is added and its verification is folded into the single G7 pass, which now
   covers the enlarged surface. G7 does not run twice.
3. One report item was refuted **by this change's own earlier measurement**: the `LC_ALL=C` pinning
   recipe (task 6.3 withdrew it — measured, it breaks the hash it was meant to fix). Re-measured on 28/08:
   `C` and `C.UTF-8` both yield `6d92bc6d…` (codepoint collation), a language UTF-8 locale yields the
   registered `d7bcc019…`; the files are byte-identical either way, so a mismatch is a false alarm about
   content. The only residue is documentary (see 6.3).

### D-26 — The five behavioural repairs of the second wave (they change what is accused)

Stated here once, in the shape of D-20, because each changes what the instrument accuses. Every value
below comes from the pinned expert oracle; none introduces an algorithm, event or literal the oracle does
not name. **Each carries the researcher's ratification in its G8 task, and none is applied before it.** **Ratified 2026-08-28 (researcher): GO on all five items below, plus D-27.** Item 5 lands as task 8.1, which gained the `[RATIFY]` marker with this ratification — it had been the one item of this decision the task list left unmarked, and it does move what is accused.

1. **Event-alphabet completeness against the rule's anonymous position.** `getInstance(algorithm, _)`
   (`SecretKeyFactory.crysl:11`, `AlgorithmParameterGenerator`, `AlgorithmParameters`, `SecureRandom.crysl:20`)
   admits *any* second argument. Four specifications weave only the `(String)` and `(String, String)` forms,
   so the `(String, Provider)` route — declared by the API 30 `android.jar` — takes no event: no value accusation, and the
   next call draws a spurious ORDER. `SecureRandomSpec`'s accuser is narrower still (`args(alg)`, arity 1).
   The repair realizes the rule's `_`; the idiom already exists in ≥9 specifications of the set.
2. **A value clause realized only in `condition(...)` is defective (INV-INS-152), and `KeyPairGeneratorSpec`
   is the surviving instance.** `KeyPairGenerator.crysl:28` names five algorithms and the specification has
   no ALG code at all; a rejected `getInstance` is absorbed by the negated twin, and the misuse surfaces as
   `KEYPAIRGENERATOR-KEYSIZE-00` — a message asserting a clause the rule does not state for that algorithm —
   plus two spurious ORDER lines. Verified distinct from the Mac/Signature two-argument residue (gh105
   10.8(a)), where the accusation migrates to the init events instead of disappearing.

   **ADENDUM, ratified 2026-08-30 (researcher): the item closes at both arities, and 8.4 closed one.**
   What is written above is the `getInstance(String)` route, and task 8.4 repaired it there: `g3` accuses
   and the misuse draws `KEYPAIRGENERATOR-ALG-00`. The two-argument route is in a worse state than the
   one this item describes, and 8.4 made that visible rather than causing it. `g2` guards
   `getInstance(String, Object+)` with a **positive** `ConscryptAliasTable.matches(...)` and has no
   negated twin, so a rejected algorithm passed through it matches **no event at all** — the D-26.1
   family, registered for five other specifications in the `behavioural` row of `divergence_record.csv`
   that gh105 task 10.8 opened. It costs more here than in those five: `algorithm` is the field `init1`
   and `initError` both test for null, so the object goes on unbound and the whole specification stays
   silent for it — not even the key-size and ordering residues the one-argument route produces. Task 8.9
   gives it the arity-2 negated twin in the shape D-26.1 gave `SecureRandomSpec.g5`, and the twin binds
   `algorithm` as `g3` does, so that the two arities answer the same thing to the same misuse rather
   than trading one asymmetry for another. Register-only was the other option and was declined; the
   family row carries the decision.
3. **Alias semantics are not optional at a clause antecedent.** `AlgorithmParametersSpec` tests the
   antecedents of `AlgorithmParameters.crysl:35-40` with raw case-sensitive `contains`, three lines from a
   site that uses `ConscryptAliasTable.matches` and inside a block that elsewhere uses `equalsIgnoreCase`;
   `getInstance("dh")` therefore falls out of every branch and the REQUIRES read never happens — neither
   NOBS nor VIOLATED, silence. 55 of the set's 57 comparison sites already use `matches`.
4. **The PBE chain false positive is a reader defect, not an oracle wart** (INV-INS-153). Read together,
   the oracle is coherent: `SecretKeyFactory.crysl:31` ensures `generatedKey[key, algorithm]` over its own
   PBE/PBKDF2 list, `Cipher.crysl:134` requires `generatedKey[key, alg(transformation)]`, and for a PBE
   transformation those are **the same string** — `Cipher.crysl:94-105` treats the whole PBE name as the
   transformation's algorithm. The direct PBKDF2→`AES` route is closed by the oracle on purpose, and its
   conforming path is the re-wrap through `SecretKeySpec.crysl:27`. What accuses a conforming program is
   the reader: `keyAlgorithm` folds `AES_128`→`AES` (D-20.2, written for the alias/keysize route) and the
   fold spills into the PBE route, where the letter wants the PBE name the producer wrote. The repair
   compares against **both** readings — the letter and the family — and nothing else. In the same clause
   family, `KeyStoreSpec.mop:189` writes a concrete value where `KeyStore.crysl:60` leaves the position
   anonymous (`generatedKey[key, _]`), which is stricter than the rule. The correction the task proposed
   — drop that write to arity 1 — was **measured against the substrate and declined**. `PredicateStore`
   has no wildcard: `ensure(p, key)` records the EMPTY tuple, so the three arity-2 readers
   (`CipherSpec.mop:199`, `SecretKeySpec.mop:122`, `KeySpec.mop:79`) would find the entry, fail to find
   the tuple and answer VIOLATED — a `CIPHER-CONSTR-00` manufactured for every key-store key, and key
   material silently unstaged at the other two. An anonymous read is in fact served by `validateAny`,
   which already answers SATISFIED against the arity-2 write, so the change buys nothing and costs three
   sites. The write stays at arity 2 and the departure from `_` stays recorded, beside the Temurin
   measurement that first licensed it (divergence row `94be6e27a760`; researcher decision, 2026-08-28).
5. **`SecretKeySpec.crysl:26`'s `speccedKey` is transcribed.** The write was omitted on a recorded reason
   that is false — "its consumer is SecretKeyFactory, which has no specification in this set" — while three
   sites read `SPECCED_KEY` today (`SecretKeyFactorySpec.mop:90`, `KeyFactorySpec.mop:79`, `:105`). This is
   INV-INS-151's symmetric obligation read from the other end, and the ledger already says `wireable`.

A sixth item is **not** a specification change and is stated separately: the consolidation channel for
`-NOBS-` (D-27).

### D-27 — The `-NOBS-` channel is separated in consolidation, and the measurement stays in 7.3

All four reports converge on it and the measurement confirms it: the 64 `-NOBS-` codes and the 86
`-CONSTR-` codes share `ErrorType.UnsatisfiedConstraint`, the distinction lives only in the code substring,
and no consumer of the pipeline filters on it (measured: zero hits in `modules/`, `scripts/`). The
aggravating structure is measured too — 71 of the 76 `validate` sites read a predicate whose only route to
VIOLATED would be a `negate`, and the set holds exactly one — so upstream misuse reaches a downstream site
as NOT_OBSERVED and never as a violation.

The decision splits in two, deliberately. **What this change does**: give the consolidation a filter keyed
on `site_kind` (the column already exists in `codes.csv`) so that a `-NOBS-` line can never be summed as
conformance nor as violation. Nothing changes on the device; the same `addError` calls fire. **What this
change does not do**: measure the NOBS rate — that is task 7.3, already open (D-24) — nor decide whether
producers should `negate` when they accuse, which is a design question that belongs after the measurement.

**Ratified 2026-08-28 (researcher): GO**, and this one lands **first** of the six. It is the only repair of
the second wave that changes nothing on the device, and separating the channel is what makes 7.3's NOBS
rate readable at all: before it, a `-NOBS-` line was summed indistinguishably from a `-CONSTR-` one, so the
rate 7.3 reports is the first reading of this channel and is comparable to no earlier count.

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Verified by |
|---|---|---|
| Expert Oracle Coverage Parity / INV-INS-150 | coverage matrix artifact `data/jca_android/coverage_matrix.csv` (derived) + 24 new `.mop` | matrix derivation script check; `gh105_expert_ledger.py --check` |
| INV-INS-151 (producer gaps, both sides) | trivial+medium tier specs writing the six predicates **+ G1b opening the three unblocked reads** | ledger re-derivation: zero `unmonitored-producer` for writable rules; every predicate written by the set read at a consuming site or carrying a recorded impossibility |
| INV-INS-152 (accusing value clauses) | R1, R9 + new-spec template (accuser branch per constraint) | G-CONF + `codes.csv` bijection + trace pairs |
| INV-INS-153 (canonical predicate values) | R8 (`KeyGeneratorSpec:215`), normalizer splitter R6 | `ConscryptAliasTableTest` mirror + harness traces |
| INV-INS-154 (ceiling + jar evidence) | per-spec viability fiche in each G2–G4 task | G-SIG over enlarged set; generation artifact inspection |
| INV-INS-155 (platform-dead) | HMAC disposition rows (ledger #38/#80 reconciled) | ledger `--check` |
| Cipher tables MODIFIED | `CipherTransformationNormalizer` PBE branch + `alg` swap + AES_128 equivalence | monitor regen + diff harness checkpoint + `jca` freeze gate untouched |

Architecture, API Design, Data Flow, Error Handling and Testing Strategy sections are deliberately omitted (P1): the only new executable is `scripts/gh109_coverage_matrix.py`, whose data contract is the delta's Data Contracts entry and whose verification is its Mapping row above; everything else in this change is `.mop`/CSV work governed by the gh105 apparatus already documented in `docs/architecture/`.

## Goals / Non-Goals

**Goals**: coverage parity (INV-INS-150), the six producer gaps closed, the 9 verified repairs, Android adjudications recorded, records/censuses truthful, all gates green over the enlarged set.

**Non-Goals**: the NOBS *measurement* and the "should producers negate" design question (7.3 and after — D-27 separates them from the consolidation filter this change does add), junction buckets, the article, gate retirement (#107), AndroidKeyStore/`KeyGenParameterSpec` specs (no expert rule — issue #110), Network Security Config/cleartext (static analysis), upstream oracle edits, reopening D-15/11.6 adjudications.

**Weaver work stays out, and now names what it defers** (researcher decision, 28/08 — separate change): the second validation wave verified two defects in the dexlib2 weaver, and neither is repaired here. (i) `TypeResolver` builds no `$` for nested types, so `KeyStoreSpec`'s `ge1`/`se1` never weave under dexlib2 — a silent false negative plus a spurious `KEYSTORE-ORDER-00` on every `load`…`store`; the `.mop`-side workaround (`Object+`, the idiom `KeyStoreBuilderParametersSpec` already documents) is deliberately NOT applied here, because the root repair in the weaver fixes every specification at once. (ii) `AfterEmitter`'s javadoc promises `finally` semantics that neither the inline insertion nor the wrapper implements, so a plain `after()` advice does not run when the matched call throws — 58 of the set's 202 events are in that form, and ajc and dexlib2 therefore disagree on any trace that throws. Full analysis: `docs/20260827_divergencia_after_dexlib2_ajc.md`. What this change owes them is a record, not a repair (task 8.R).

## Risks / Trade-offs

- [KeyAgreement/SSLParameters complexity] → last group, after the template is proven on 14 trivial specs; oracle-defect rows land first (D-21).
- [Generator ceiling] → all new specs are ≤5 events; no risk. `CipherSpec` stays at 17/17 — no new Cipher events, ever (AEAD gap remains recorded). The price is named and paid in the open: `Cipher.crysl:136`'s `preparedAlg[params, …]` read cannot open, because `params` is bound only by the rule's `i5`/`i7` and the `.mop`'s fused `i2` carries `args(mode, key, ..)`. Recorded deferral, not silence (D-24).
- [False positives from the D-24 reads] → the three new read sites can answer NOT_OBSERVED for a program whose parameter spec or `ManagerFactoryParameters` was built outside the monitored set; that is the shape of the seventeen orphan accusers gh105 group 3 removed. Mitigation is measurement, not argument: each site gets its own `-NOBS-` code, and the NOBS rate over the APK corpus is read at harness checkpoint 2 before the NOBS branch is treated as final (task 7.3).
- [CI breakage from enumeration constants] → constants updated in the same commit as the first new spec of each milestone (D-23 owns the list).
- [`SecretKey+`/`Key+` subtype pointcuts on dexlib2] → verify the matcher accepts `+` in owner position on a woven exemplar before relying on it (task-level check in G1/R5).
- [Behavioral shift of the D-26/D-27 repairs] → ratified GO on 2026-08-28 and sequenced so the corpus is crossed **once**: `jca_android` carries no published number (the frozen `jca` answers for those) and the gh104 campaign had not run, so the six land before it rather than after. The price is named: 8.3 and 8.5 turn silence into `-NOBS-` lines and 8.7 changes how those are summed, so 7.3's NOBS rate is the first reading of that channel and no earlier count is comparable to it. D-26.4's measure-first alternative was declined because a corpus pass costs the same whatever it measures, and a second one would buy an answer the three rules already give when read together.
- [Behavioral shift of D-20 decisions] → all five stated in one design section, each with divergence-record rows; the campaign comparability caveat (populations named by oracle) is already the gh105 rule.
- [Two open changes touching the same capability (gh105 unarchived)] → gh109's delta only ADDs requirements plus one MODIFIED (`Cipher Transformation Tables`) that gh105's delta does not touch; archive order gh105 → gh109. The gh105 delta asserts two enumeration literals this change falsifies ("the successor set holds 24 specifications"; "25 are wireable — of which 24 are wired"): at gh109's sync they are re-derived during the manual `/opsx:sync` review (task 6.5) instead of surviving as stale literals.

## Open Questions

- `HMACParameterSpecSpec`: keep as documentation of untranslatability (default) vs. retire to `backup/` — researcher decision in G5; ledger rows reconcile either way.
- Sole-oracle gate vs. the conformance component (task 6.4): extending `gh105_sole_oracle_gate.py` to `rvsec-core` Java runs into `CalibrationTargets.java` / `StampedTable.java` / `SourceStamp.java`, which stamp `rvsec-cognicrypt` as the oracle they read — legitimately, because the component measures against upstream and the difference to the pinned expert copy is the two `CCM` lines of `Cipher.crysl`. Either the gate exempts the component by name, or 6.4's scope shrinks to the three stale api30 citations it was written for. Researcher decision; the answer decides whether 6.4 and the component's own tests can run unchanged.
