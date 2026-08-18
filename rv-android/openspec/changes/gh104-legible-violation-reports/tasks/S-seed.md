# Group 2 — S: archive the reproved set, seed and shape the successor set `jca_android`

Tracked checkboxes: `tasks.md` §2. Wave 1. Dependencies: none for tasks 2.1–2.13 and 2.15; **task 2.14 waits for Group 6 task 6.9** (the harness) and Group 6 task 6.4 waits for this group's 2.15. Group 7 (E1) and Group 8 (E4) wait for this group's commit. This is the long pole of wave 1 — dispatch it first. Every generation shell: `sdk use java 21.0.12-tem`, `export TMPDIR=<dir under /home>`, and the generation lock of the `tasks.md` dispatch hints (one monitor generation at a time across wave 1); `evidence/...` means `data/gh104/evidence/...`.

## Subagent brief

**The name `jca_android` changes owner in this group.** Today it names the derived set the 2026-08-08 audit reproved 22/22 on its predicate machinery. Task 2.1 moves that set, unchanged, to `rvsec-mop/src/main/resources/jca_android_bug_predicate/`, where it stays as an archive that **nothing can select**. Only then does task 2.2 create a new `rvsec-mop/src/main/resources/jca_android/`, seeded from the **frozen `jca` (Java) set**. From that point on, in this change and in the code, `jca_android` means the successor set.

The successor differs from its seed in exactly three mechanical ways, applied in this order: the two pure predicate propagators are deleted (21 specifications remain), every use of `ExecutionContext` is removed, and every allow-list is re-transcribed from the CrySL rules already generated in `MetaCrySL/generated/api30/`.

The enumeration does **not** grow. `jca`, `jca_android`, `generic`, `custom` remain the four accepted values (`click.Choice`, `valid_spec_sets`); what changes is where `jca_android` resolves to. The archived directory has no value pointing at it and must be rejected like any other unknown string — that is task 2.9, and it is a *confirmation* task, not a registration task.

Read `design.md` D-1, D-10 and D-12, the `instrumentation` delta (`Requirement: Successor Specification Set`, INV-INS-09/112/118/125/127/128) and the `experiment` delta. **Do not edit anything under `jca/`, under the archived `jca_android_bug_predicate/`, under `MetaCrySL/`, nor `CipherTransformationUtil.java` or `AndroidCipherTransformationUtil.java`** — all five are read-only inputs (the archive is read-only from the moment the `git mv` lands; the `git mv` itself is the only write it ever receives). Do not repair automata, pointcuts or messages: Groups 7 and 8 do that. Every hunk against `jca/` gets a divergence-record entry.

Trees:
- rv-android (this one): `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`
- Java reactor: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`
- CrySL oracle (read-only): `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/`

## Files

Java side (git root `.../workspace-rv/rvsec`):
- `rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/` — the reproved derived set, moved here by task 2.1's `git mv`. 23 `.mop`, byte-identical. Read-only afterwards; not selectable.
- `rvsec/rvsec-mop/src/main/resources/jca_android/` — NEW. 23 `.mop` copied from `jca/` (1,912 lines total) minus the two deletions of task 2.2 → **21 `.mop`** + `codes.csv` (header `spec,code,error_type,site_kind,event,file_line`, no rows). `jca/` also holds `MultiSpec_1MonitorAspect.aj` (a generated artefact checked in); decide whether it travels and record the decision in the README either way.
- `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/<Api30CipherName>.java` — NEW (task 2.8), + its test.
- `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/<AliasTableName>.java` — NEW (task 2.5): the Conscrypt alias table as code, named by the `jca_android` specifications and by nothing under `jca/`. Its test asserts the in-code table equals `data/jca_android/alias_table.csv` row for row. Both new classes live under `rvsec/rvsec-core/src/test/java/br/unb/cic/mop/jca/util/` for tests.

Python side (`rv-android/`):
- `modules/rv-experiment/src/rv_experiment/constants.py` — `SPEC_SET_JCA_ANDROID = "jca_android"` already exists at `:97`. **No new constant.** The comment block above it (`:90-95`) and `config.py:248` still describe the value as "the same 23 specifications derived against generated CrySL rules"; that description now belongs to the archived set and must be rewritten to describe the successor.
- `modules/rv-experiment/src/rv_experiment/config.py` — `valid_spec_sets` (`:432-437`) and the JIT directory mapping (`:688-700`) are already correct in shape and stay as they are; the prose that needs rewriting is at `:248`, `:385`, `:429`, `:648`, `:678`.
- `modules/rv-experiment/src/rv_experiment/__main__.py` — `click.Choice(["jca", "jca_android", "generic", "custom"])` at `:443` **does not change**; the help text at `:368`, `:656` says "the JCA set derived for an Android API level" and must say what the successor set is (`:1193` is a docstring that only lists the four values and stays; `config.py:657` carries the same "derived for a declared Android API level" phrase and is rewritten with the others).
- `modules/rv-experiment/tests/test_config_jit.py` (`test_jca_android_spec_set_resolves_paths`, `:86-113`) and `tests/test_config_validation.py` (`test_jca_android_spec_set_valid` `:121`, `test_near_miss_spec_set_still_rejected` `:134`) already cover selection and rejection and stay green unchanged — that is the evidence the enumeration did not move. Add one test: `test_jca_android_bug_predicate_not_selectable`, asserting that the archived directory's name is refused exactly like `jca-android`. The invalid-value message keeps listing **four** sets.
- `data/jca_android/divergence_record.csv` (header as `data/gh101/divergence_record.csv`), `data/jca_android/conformance_record.csv` (header as `data/gh101/conformance_record.csv`), `data/jca_android/alias_table.csv` (imported in task 2.5; columns `service,alias,canonical,openssl_provider_line,in_api30_allowlist`), `data/jca_android/predicate_removal.csv` (`file,line,spec,event,class,lost_accusation,reason` — the 21 predicate-reading events plus the 9 `remove(...)` sites task 2.3 touches, 30 rows), `data/jca_android/constraint_table.csv` (`spec,cryptsl_line,mop_line,verdict` — task 2.15, the row-level table G-CONF reproduces), `data/jca_android/gate_allowlist.csv` (`set,gate,spec,event_or_state,reason,task`), `data/jca_android/README.md`. **There is no `predicate_omissions.csv`** — that record exists to justify a `Property` written and never read, and this set writes none (INV-INS-128). `predicate_removal.csv` is the record that does exist: it names what left, not what was left dangling.
- `scripts/gh104_divergence_record.py` — parametrised copy of `scripts/gh101_divergence_record.py` (169 lines): base directory `jca/`, target `jca_android/`, record `data/jca_android/divergence_record.csv`, `--check` exits non-zero on any hunk without an entry. It must tolerate a file present in the base and absent in the target (the two deletions).
- `tests/parity/test_gh104_specset_gates.py` — created here with `test_jca_android_hunks_all_recorded` and `test_jca_android_has_no_execution_context`; Group 6 writes its structural gates in a separate file (`test_gh104_structural_gates.py`) to avoid a merge.

## Task 2.1 — archive the reproved derived set

**Freeze the base of the rename before you move anything.** Record the Java tree's current `HEAD` SHA in `data/jca_android/README.md` as the freeze item `pre-rename-head`. Task 10.1 asserts the move is a pure rename **against that SHA**, not against `7e7acb69`: the freeze commit predates gh101's edits to this directory (19 files, 720 insertions, 122 deletions, measured 2026-08-18), so a rename diff taken against `7e7acb69` shows those hunks whatever this change does. `7e7acb69` remains the correct base for `jca/` and `CipherTransformationUtil.java`, which are byte-identical to it today and must stay so; `AndroidCipherTransformationUtil.java` does **not** exist at `7e7acb69` (gh101 added it, +262 lines), so its read-only base is `pre-rename-head` too.

```bash
cd ../rvsec/rvsec-mop/src/main/resources
git mv jca_android jca_android_bug_predicate
git status --short   # 23 lines, all `R  jca_android/X.mop -> jca_android_bug_predicate/X.mop`
```

Nothing else. No file content changes; `git diff --stat --find-renames` must show zero insertions and zero deletions. If any file shows a content hunk, the move was done wrong — undo and redo it with `git mv`.

**Why this name.** The set's defect is not "it is old" and not "v1": the 2026-08-08 audit reproved all 22 of its specifications on the predicate machinery (`audit/20260808_validacao_jca_android/`). The directory name says that, so a reader who finds it does not have to reconstruct why it is not in use. P4 applies to directory names as much as to identifiers: name the thing, not its lineage.

**Why it is not selectable.** Adding a fifth enumeration value would put a knowingly reproved instrument one flag away from an experiment. It has no value, and task 2.9 adds the test that proves the name is rejected. Anyone who needs to regenerate it points `--specification-set custom --custom-specs-dir <path to the archive>` at it deliberately, and that deliberateness is the point.

Record: the first `divergence_record.csv` entry (kind `set-archived`, reason `reproved 22/22 by the 2026-08-08 predicate audit; retained for reproduction of published measurements only`), plus a paragraph in `data/jca_android/README.md` naming the old path, the new path and the audit.

## Task 2.2 — the seed, and the two specifications that leave

`RandomStringPassword.mop` (29 lines, 2 events) and `SecretKeySpec.mop` (34 lines, 1 event) are **pure predicate propagators**: `grep -c "new ErrorDescription("` returns 0 for both and neither has a `@fail`. Their only job is to write `ExecutionContext` properties that other specifications read. With predicates gone they detect nothing, so they leave the set. Deleting them costs **zero report sites**. Record both deletions as divergence entries (kind `spec-removed`, reason `pure predicate propagator; no report site`) — they follow the `set-archived` entry of task 2.1.

The 21 that remain: `CipherInputStreamSpec, CipherOutputStreamSpec, CipherSpec, DHGenParameterSpecSpec, GCMParameterSpecSpec, HMACParameterSpecSpec, IvParameterSpec, KeyGeneratorSpec, KeyManagerFactorySpec, KeyPairGeneratorSpec, KeyPairSpec, KeyStoreSpec, MacSpec, MessageDigestSpec, PBEKeySpecSpec, PBEParameterSpecSpec, SecretKeySpecSpec, SecureRandomSpec, SignatureSpec, SSLContextSpec, TrustManagerFactorySpec`.

## Task 2.3 — the `ExecutionContext` inventory (21 events over 8 of the 21 files)

The frozen `jca` carries **134** `ExecutionContext` occurrences across the 23 files (126 in the 21 that stay). Of the 21 that stay, **21 events** read a predicate — all of them in their `condition()`, none in a body — over **8 files**: **10 as a guard only** (removing the predicate is a net gain — today an unmet predicate makes the event fail its guard, and the generated method returns before the body and before the transition, so the specification goes silent) and **11 as the basis of an accusation** (removing it is a declared loss of detection). The classification is by the generated monitor, not by the presence of a report site: an event whose transition row is all-`fail` accuses through `@fail` whatever its body says (`SecureRandomSpec.c3`), and an event whose row reaches `match` is a guard whatever its condition reads (`GCMParameterSpecSpec` 4-arg `c1`). Re-derive the table with `grep -n "ExecutionContext.instance().validate" jca/*.mop` and the `Prop_1_transition_*` rows before editing.

| spec | event | role | consequence of removal |
|---|---|---|---|
| GCMParameterSpecSpec | `c1` (`:23`, 2-arg ctor) | guarda | ctor accepted on `validLengths` alone |
| GCMParameterSpecSpec | `c1` (`:34`, 4-arg ctor — renamed `c2` in Group 8) | guarda | ctor accepted on `validLengths` + offset/len alone — its row is `{1,2,2}` (start → match), the same row as the 2-arg twin, so an unmet predicate never accused; the guard returned before any transition |
| IvParameterSpec | `c1`, `c2` | guarda ×2 | — |
| IvParameterSpec | `c3` (`:48`), `c4` (`:55`) | acusa ×2 | **the two three-argument report sites disappear entirely** (purely predicate-guarded) |
| MacSpec | `i1` (`:49-50`), `i2` (`:61-62`) | acusa ×2 | key-provenance (`GENERATED_KEY`) half lost; the allow-list half of each site survives |
| CipherSpec | `i2` (`:75-76`) | acusa | key-provenance half lost; the transformation half survives |
| PBEKeySpecSpec | `c1` | guarda | `iterationCount >= 10000` half stays |
| PBEKeySpecSpec | `err2` (`:57-58`), `err3` (`:65-66`) | acusa ×2 | **both four-argument report sites disappear entirely** |
| PBEParameterSpecSpec | `c1`, `c2` | guarda ×2 | — |
| PBEParameterSpecSpec | `c3` (`:49-50`) | acusa | `!validate(RANDOMIZED, salt)` half lost; `iterationCount < 10000` half survives |
| SecretKeySpecSpec | `c1` | guarda | — |
| SecretKeySpecSpec | `c3` (`:48-49`) | acusa | `!validate(RANDOMIZED, keyMaterial)` half lost — **and see task 2.4: the allow-list half has no base in api30, so this site loses both halves and disappears** (total loss) |
| SecureRandomSpec | `c2`, `setSeed2` | guarda ×2 | — |
| SecureRandomSpec | `c3` (`:43-48`) | acusa (via `@fail`) | its body only stores `sr = r;`, but its row is `{3,3,3,3}` against `fail = 3` (`MultiSpec_1RuntimeMonitor.java:7899`), so every firing accuses `InvalidSequenceOfMethodCalls`; with the predicate gone the event has no purpose and its **declaration is deleted** — kept with an empty condition it would accuse on every `new SecureRandom(byte[])` (total loss) |
| SecureRandomSpec | `setSeed3` (`:100-101`) | acusa | **the four-argument report site disappears entirely** (purely predicate-guarded) |

The four accusers that are **not** predicate-only keep their event and their report site: `PBEParameterSpecSpec.c3` (partial loss — strip the predicate conjunct, keep the iteration-count test), `CipherSpec.i2`, `MacSpec.i1/i2` (provenance — the `condition()` was the `GENERATED_KEY` read alone → drop the `condition()`, keep the event, its site and its row; the divergence entry says the provenance half is lost). Task 7.2's 45-site arithmetic assumes exactly this.

Plus, outside `condition()`: **the 9 `remove(...)` sites** — 4 of the deprecated one-argument `remove(Property)` (`MacSpec:87`, `TrustManagerFactorySpec:87,88`, `KeyManagerFactorySpec:91`) and 5 of the two-argument `remove(Property, Object)` (`KeyGeneratorSpec:75`, `KeyPairGeneratorSpec:112`, `KeyStoreSpec:79,80`, `PBEKeySpecSpec:72`) — all go, which also retires the deprecated one-argument API from this set. Context for the loss: the whole api30 corpus declares only **2** `NEGATES` blocks (`SecretKey.cryptsl`, `PBEKeySpec.cryptsl`), and exactly one of the nine sites encodes one of them — `PBEKeySpecSpec:72`, `remove(SPECCED_KEY, s)` inside `clearPassword()`, is `PBEKeySpec.cryptsl:48-50` `NEGATES speccedKey[this,_] after cP` — so eight removals were never asked for by a rule and the ninth leaves with the property it revokes.

And the `setProperty(...)` writes: every one of them — 46 sites in 19 of the 21 files (the two stream specifications only import `ExecutionContext`); 49 in the frozen `jca` — is deleted with its event body, one divergence entry per file, no row in `predicate_removal.csv`. **What happens to the declaration depends on the row, not on the body.** An event that stays in the `ere`/`fsm` keeps its declaration with an empty body (the generator needs no body). An event whose transition row is all-`fail` and whose only guard was the predicate — `IvParameterSpec.c3/c4`, `PBEKeySpecSpec.err2/err3`, `SecureRandomSpec.c3/setSeed3`, `SecretKeySpecSpec.c3` — has its **declaration deleted**: kept with an emptied `condition()` it would accuse on every legitimate call of its pointcut, and G-2 would clear it as `orphan-with-clause` through the rule's `REQUIRES` (design D-7 — on `jca_android` G-2 accepts `CONSTRAINTS`/`FORBIDDEN` only for exactly this reason). A guard whose `condition()` mixed a predicate with a real test (`GCMParameterSpecSpec` both `c1`, `PBEKeySpecSpec.c1`, `SecretKeySpecSpec.c1`) keeps the real test; a guard whose `condition()` was the predicate alone (`IvParameterSpec.c1/c2`, `PBEParameterSpecSpec.c1/c2`, `SecureRandomSpec.c2/setSeed2`) drops the `condition()` and fires unconditionally, which is the accepting transition the rule intends.

**Measured mitigation to record, not to argue with:** the three key-provenance detections lost (`CipherSpec.i2`, `MacSpec.i1/i2`) were already dead on Android — keys from `AndroidKeyStore`, Tink and `KeyGenParameterSpec` never carry `GENERATED_KEY` (11,620 events / 80 misuses / 25 apps, `ase-journal`). Put that sentence in the divergence entry for those three.

**The record.** Every one of the 21 events above, plus the 9 `remove(...)` sites, gets a row in `data/jca_android/predicate_removal.csv` (**30 rows**: 21 + 9, and the class totals below sum to the same 30): `file,line,spec,event,class,lost_accusation,reason`, where `class` is one of `guard` / `total-loss` / `partial-loss` / `provenance` / `remove`. Seven rows are `total-loss` (`IvParameterSpec c3/c4`, `PBEKeySpecSpec err2/err3`, `SecureRandomSpec c3/setSeed3`, `SecretKeySpecSpec c3`), one `partial-loss` (`PBEParameterSpecSpec c3`), three `provenance`, ten `guard`, nine `remove`; the `setProperty` deletions are divergence entries, not rows. The `lost_accusation` column carries the sentence the site used to raise, verbatim, so that reopening the predicate question later does not require re-deriving this inventory from the seed. This record is what INV-INS-128 leaves in place of a `predicate_omissions.csv`, which this set does not carry.

Verification command after the pass:

```bash
grep -rn "ExecutionContext\|Property\.\|ExecutionContext.instance().validate(\|setProperty(" ../rvsec/rvsec-mop/src/main/resources/jca_android/   # empty (NOT the bare `validate(` — KeyPairGeneratorSpec keeps its local `validate(int)`)
grep -c "ExecutionContext" ../rvsec/rvsec-mop/src/main/resources/jca/*.mop | awk -F: '{s+=$2} END{print s}'            # 134, the negative control
```

## Task 2.4 — literal transcription of the allow-lists

The seed declares **13** allow-lists. Each one is replaced by the corresponding `CONSTRAINTS` set of `MetaCrySL/generated/api30/<Rule>.cryptsl`, transcribed literally, with one `conformance_record.csv` row naming the `.cryptsl` file and the clause (design D-10: one anchor, the api30 rule; the availability/recommendation split of the derived set is withdrawn), and one `constraint_table.csv` row per clause (task 2.15).

| `.mop` (seed line) | today | api30 rule and clause | note |
|---|---|---|---|
| `MacSpec:12` `safeAlgorithms` | Hmac* list | `Mac.cryptsl` `macAlg in {12 entries}` | api30 adds `HmacMD5`, `HmacSHA1`, `HmacSHA224` and the `PBEwithHmac*` family |
| `MessageDigestSpec:16` `algorithms` | `SHA-256/384/512` + unhyphenated | `MessageDigest.cryptsl:63` `digestAlg in {MD5, SHA-224, SHA-256, SHA-1, SHA-512, SHA-384}` | api30 admits MD5 and SHA-1 → the spec accepts them; the measured cost is below |
| `KeyStoreSpec:23` `types` | `JCEKS, JKS, DKS, PKCS11, PKCS12` | `KeyStore.cryptsl` `keyStoreAlg in {AndroidKeyStore, PKCS12, BKS, BouncyCastle, AndroidCAStore}` | this single row resolves the 2,005-event / 12-misuse `AndroidKeyStore` block of the tier |
| `TrustManagerFactorySpec:23` `algorithms` | `PKIX, SunX509` | `TrustManagerFactory.cryptsl` `algo in {PKIX}` | more restrictive and correct (`SunX509` does not exist on Android); the 643 `X509` events need the alias rule of task 2.5, not this list |
| `GCMParameterSpecSpec:21` `validLengths` | `96,104,112,120,128` | `GCMParameterSpec.cryptsl` `tLen in {128,120,96,112,104}` | identical; record as IGUAL |
| `KeyGeneratorSpec:22` `safeAlgorithms` | AES + HMAC spellings | `KeyGenerator.cryptsl` `alg in {11 entries}` + `alg in {AES} => keySize in {128,192,256}` | api30 adds `ChaCha20`, `ARC4`, `DESede`, `BLOWFISH`, `HmacMD5`, `HmacSHA1` |
| `KeyManagerFactorySpec:22` `safeAlgorithms` | `PKIX, SunX509` | `KeyManagerFactory.cryptsl` `algo in {PKIX}` | as TMF |
| `SecretKeySpecSpec:19` `algorithms` | AES + HMACSHA* | `SecretKeySpec.cryptsl` `CONSTRAINTS` = `length(keyMaterial) >= off + len` **only** | the rule declares nothing about the algorithm → **the list has no base and is removed**; see the knock-on in task 7.2 |
| `KeyPairGeneratorSpec:22` `safeAlgorithms` | `RSA, EC, DSA, DiffieHellman, DH` | `KeyPairGenerator.cryptsl` `alg in {DSA, DH, RSA}` + four keySize implications | plus the `EC` decision of task 2.6 |
| `KeyPairGeneratorSpec:30` keySize per alg | `RSA: 4096,3072,2048` | `alg in {RSA} => keySize in {4096, 2048}`; `{DH}`/`{DSA} => {2048}`; `{EC} => {256}` | api30 drops 3072 |
| `SignatureSpec:23` `algorithms` | SHA256with* | `Signature.cryptsl:75` `alg in {20 entries}` | api30 admits `MD5withRSA`, `SHA1withRSA`, `SHA1withDSA` (accepted, see the rule below) and lists only `SHA224withECDSA` among the ECDSA algorithms (four are added back — task 2.7) |
| `SecureRandomSpec:23` `algorithms` | `SHA1PRNG, Windows-PRNG, NativePRNG, …` | `SecureRandom.cryptsl` `randAlg in {SHA1PRNG}` | more restrictive and correct on Android |
| `SSLContextSpec:23` `protocols` | `TLSV1.2, TLSV1.3` | `SSLContext.cryptsl` `protocol in {Default, TLSv1.2, TLSv1.1, SSL, TLSv1, TLS, TLSv1.3}` | this single row resolves the 8,648-event / 65-misuse `TLS` block of the tier |

**The rule is asymmetric, and both halves are already decided. Do not stop and ask.**

*api30 admits it → the specification accepts it.* One oracle, one anchor, no per-clause judgement. Where a value used to be rejected on a "recommendation" reading, the rejection goes. For `MessageDigestSpec` this is the expensive case and the number is on record: the published dataset carries **6,048** `MessageDigestSpec/UnsafeAlgorithm` rows, of which **3,552** are `MD5` and **2,340** are `SHA-1`/`SHA1`/`SHA`; those **5,892** rows stop being reported — 97.4 % of that specification's `UnsafeAlgorithm` reports (36.4 % of all its 16,183 reports) and 6.1 % of the 97,018-row corpus. That is a decision the researcher took, not a question for the executor: write the figure into `conformance_record.csv` as the declared cost of the single-oracle rule and move on. For `SignatureSpec` the same rule accepts `MD5withRSA`, `SHA1withRSA` and `SHA1withDSA`.

*api30 omits something the platform has → the set adds it, with a divergence entry.* This is not a licence to widen lists by taste: it applies only where a primary source proves the value exists on API 30 and the omission is traceable to a modelling defect or an incomplete transcription in MetaCrySL. Exactly two occurrences are authorised in this change, and both are written out: `EC` in `KeyPairGeneratorSpec` (task 2.6) and the four ECDSA signature algorithms (task 2.7). A third candidate found during execution is a question for the researcher, not a third entry.

The two halves are not in tension: the first says the oracle decides what is *safe*, the second says the oracle does not get to decide what *exists*.

`IvParameterSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`, `KeyPairSpec`, `CipherInputStreamSpec` and `CipherOutputStreamSpec` have no allow-list to transcribe (their api30 rules declare no `in {…}` clause; the two stream rules declare only `len > off`). Record them as `no-allow-list` rows so the conformance record covers all 21.

### The clauses the frozen `.mop` never tested — every one is born `deferred-constant` here

The api30 rules declare `CONSTRAINTS` clauses no `.mop` of the frozen `jca` tests (the pivot counted 30; the authoritative number is the count of `CRYSL-NAO-IMPLEMENTADO` rows in `constraint_table.csv`, task 2.15). They are **not** an open question and they are **not** Group 8's: design D-10/D-30 decides them here, in two passes that do not depend on each other's timing.

- **Pass 1 (this task, no dependency on EV):** every such clause gets a **`deferred-constant`** row of `data/jca_android/conformance_record.csv` naming the `.cryptsl` file and clause, the reason it is deferred, and the sentence that leaving it out adds no accusation. This is the third admissible departure from literal transcription and INV-INS-125 names it, which is what keeps G-CONF executable — the gate still fails on any difference with no row behind it.
- **Pass 2 (task 2.14, after the harness of 6.9 exists):** a row is **promoted** to a transcribed check when the harness has sized the accusations the new check adds; a transcribed clause is then an ordinary allow-list row and its `deferred-constant` row is removed. Rows the harness cannot size stay deferred.

Transcribing all of them without evidence would change what is accused with no before/after measurement, which is the same risk D-1 refused for the 94-hunk replay and D-6 for the arity filter. Also enter the OAEP case (`RSA/ECB/OAEPWithSHA1AndMGF1Padding`, 109 events; design D-10) in `divergence_record.csv` with its evidence labelled `behavioural` and no alias row. **No constant may be skipped in silence: a clause with neither an allow-list entry nor a `deferred-constant` row fails G-CONF.**

## Task 2.5 — the normalisation rule and the alias table

Literal transcription alone leaves roughly 3,000 events of the publishable tier unmatched, because the observed strings are Conscrypt aliases or differ only in case:

| observed | events | why a literal list misses it |
|---|---|---|
| `X509` (TrustManagerFactory) | 643 | Conscrypt alias of `PKIX`, not an algorithm; api30 lists `PKIX` only |
| `SHA256WITHRSA` (Signature) | 4 | api30 writes `SHA256withRSA` — case only |
| `RSA/ECB/OAEPWithSHA1AndMGF1Padding` (Cipher) | 109 | **not a row of this table** — no provider registers the observed spelling; see the paragraph below |
| `SHA1` / `SHA` / `SHA256` (MessageDigest) | 2,340 ev / 22 misuses fragmented over three spellings | Conscrypt aliases of `SHA-1` / `SHA-256` |

**The `OAEPWithSHA1AndMGF1Padding` case is not yours to normalise — do not add a row for it.** The observed value is `RSA/ECB/OAEPWithSHA1AndMGF1Padding`, without the hyphen in `SHA1` (218 occurrences in the CSV = 109 events, counted once in `message` and once in `unique_msg`). api30 declares `OAEPwithSHA-1andMGF1Padding`; Conscrypt registers `RSA/ECB/OAEPWithSHA-1AndMGF1Padding` (`OpenSSLProvider.java:338`) and the alias `RSA/None/OAEPWithSHA-1AndMGF1Padding` (`:339-340`) — both hyphenated, and the unhyphenated spelling appears in no registration of that file. There is therefore no provider line an alias row could cite, and writing a row without one would break the pointer requirement of INV-INS-127 for the sake of one value. What the evidence does establish is that the calls worked: `CipherSpec.g1` is an `after … returning(Cipher c)` advice, so it fires only when `getInstance` returns, and it fired 109 times. Some other platform provider accepts the spelling — the candidate is the Bouncy Castle build Android ships, outside this file. Record the case in `data/jca_android/divergence_record.csv` with its evidence labelled **behavioural**, and treat identifying that provider as part of executing that entry; leave `alias_table.csv` alone for it.

Rule to declare in `data/jca_android/README.md` and implement uniformly across the 21: **comparison is case-insensitive**, plus a **declared alias table** derived from Conscrypt branch `android11-release`, one pointer per entry. Today the seed is inconsistent — case-sensitive in `MacSpec`, `SignatureSpec`, `SecureRandomSpec`, `KeyGeneratorSpec`, `TrustManagerFactorySpec`, `KeyManagerFactorySpec` (and `KeyStoreSpec`, `KeyPairGeneratorSpec`), `.toUpperCase()` in `MessageDigestSpec`, `SSLContextSpec`, `SecretKeySpecSpec` — so one call to the alias class replaces both idioms everywhere.

### The table is already extracted — import it, do not redo the search

The ficha used to tell you to fetch `OpenSSLProvider.java` and, failing that, to mark the pointers unverified. **That is closed.** The file was fetched from `android.googlesource.com/platform/external/conscrypt`, branch `android11-release`, path `common/src/main/java/org/conscrypt/OpenSSLProvider.java` (607 lines), and the table was extracted from it. Both are in the workspace:

- `backup/gh104-analise/OpenSSLProvider.java` — the primary source, 175 `Alg.Alias.*` registrations.
- `backup/gh104-analise/alias_table_conscrypt_android11.csv` — **158 rows** (the aliases in services that have a specification), columns `service,alias,canonical,openssl_provider_line,in_api30_allowlist`; **114 rows** carry `in_api30_allowlist=yes`, i.e. their canonical target is an entry of an api30 allow-list.

The count is **114** rows with `in_api30_allowlist == "yes"` out of 158 in services the set monitors. An earlier revision of the prose summary said 115; it was corrected at source on 2026-08-18 and now carries the reason — `Cipher.GCM -> AES/GCM/NoPadding` matched spuriously, because `GCM` appears in the `Cipher` list as an operation *mode*, not as an algorithm, and the alias names a whole transformation. Write 114 into the README with that reason, so nobody re-derives the number later and thinks the table changed.

Copy that CSV to `data/jca_android/alias_table.csv` unchanged. Then **sample-check** roughly ten rows by opening `OpenSSLProvider.java` at the cited line — pick at least one per alias form (unhyphenated spelling, alternate separator, `Encryption` suffix, `andMGF1`, bare OID, `OID.` prefix, composite OID, historic name, `PBEWITHHMACSHA<n>`) — and write into the README which rows you checked and that they matched. Re-extracting the table from scratch is **out of scope**: it is a solved measurement, and redoing it risks a second set of numbers that disagrees with the one the change is written against.

Two pointers the pivot brief inherited from the ase-journal report are **wrong**, and the corrected values are the ones to carry into every artefact:

| alias | brief said | correct (verified in `OpenSSLProvider.java`) |
|---|---|---|
| `SHA1`/`SHA` → `SHA-1` | `:131-132,140` | **`:115-116`** — `:131-132` is `SHA-512`/`SHA512`, and `:140` is `KeyGenerator.ARC4`, which is not an alias at all |
| `X509` → `PKIX` | `:101-107` | **`:89-90`** (the CSV row already says `90`) — `:101-102` is `AlgorithmParameters` DESEDE/TDEA |

Two limits to state in the README, because a table that hides them invites false confidence: (i) `KeyStore` has **no** alias coverage here — `AndroidKeyStore` comes from `AndroidKeyStoreProvider` and `BKS`/`BouncyCastle` from Bouncy Castle, neither of which is this file; (ii) `SSLContext.SSL` and `SSLContext.TLS` at `:80-81` point at the same implementation class but are **not** `Alg.Alias` registrations, so they are behavioural equivalence, not table rows.

One incidental finding to act on: the seed's `KeyGeneratorSpec`, `MacSpec` and `SecretKeySpecSpec` already contain hand-written alias entries *inside* their allow-lists (`HMAC-SHA256`, `HMAC/SHA256`, `HMAC-SHA384`, `PBEWITHHMACSHA-256`; the real registrations are `:170-171` and `:481`). Task 2.4 removes them with the rest of the hand-written list; the alias table is where they belong.

### Where the table lives at run time

`data/jca_android/alias_table.csv` is the **auditable registry** — what a reviewer reads, what gate G-CONF (task 6.4) compares against. It is **not** read at run time: a monitor woven into an APK has no filesystem contract with this repository, and a spec that read a CSV at run time would make its verdict depend on a file nobody ships.

So: a **new utility class** under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` carries the table as code (a static map per service), and the 21 `.mop` files of `jca_android` **name that class** in the comparison they already perform. This is the shape INV-INS-112 requires — the specification names the utility it calls, and no runtime switch selects between tables. The consequence that matters: the frozen `jca` references the class nowhere, so nothing in this task can move a `jca` verdict, which is what keeps the published measurements reproducible.

Add one Java test asserting the in-code table is row-for-row equal to `data/jca_android/alias_table.csv` (same `(service, alias, canonical)` triples, same cardinality). That test is the only thing tying code and registry together, so it is not optional; without it the two drift and the registry stops being evidence. Name the class for what it holds, not for its lineage (P4) — e.g. `ConscryptAliasTable`.

## Task 2.6 — `EC` in `KeyPairGeneratorSpec`, with the divergence recorded

Literal api30 gives `alg in {"DSA", "DH", "RSA"}` and leaves the clause `alg in {"EC"} => keySize in {256}` unreachable, because CrySL `CONSTRAINTS` are conjunctive. Evidence that this is a MetaCrySL modelling defect and not intent:

- `MetaCrySL/samples/jca/android/11plus/KeyPairGenerator.ref:2` writes `define algorithm = {"EC"};` — the command that fills a `${algorithm}` hole.
- `MetaCrySL/samples/jca/base/KeyPairGenerator.cryptsl:27` writes the list as a **literal** (`alg in {"DH", "DSA", "RSA"};`) instead of `alg in ${algorithm}`, so the `define` is discarded in silence.
- The same tier uses the same idiom in `KeyGenerator.ref` and it works, because `samples/jca/base/KeyGenerator.cryptsl:27` does have the hole (`alg in ${algorithm};`).
- Only three base specifications fix the list literally (`KeyManagerFactory`, `KeyPairGenerator`, `TrustManagerFactory`) and only `KeyPairGenerator` has an Android `.ref` trying to extend it.

**Decision (D-c): `jca_android` includes `EC` with keySize 256.** One `divergence_record.csv` entry names the defect, points at the four lines above, states that the root fix is `alg in ${algorithm}` in the base specification, and states that it is **not executed here** because MetaCrySL is not modified by this change. Justification to carry in the entry: EC is the algorithm Android recommends for `AndroidKeyStore`, so a literal transcription would fabricate exactly the class of spec-artefact this change exists to remove.

## Task 2.7 — the four ECDSA signature algorithms, with the divergence recorded

Same `api30-omits` case as task 2.6, second and last occurrence.

`generated/api30/Signature.cryptsl:75` lists **twenty** algorithms and exactly one ECDSA among them, `SHA224withECDSA`. That cannot be right about the platform: Conscrypt on `android11-release` registers the whole family, and the registrations are in the same file as the alias table:

| algorithm | proof in `OpenSSLProvider.java` |
|---|---|
| `SHA1withECDSA` | `:270` (`Alg.Alias.Signature.ECDSA`), `:271` (`Alg.Alias.Signature.ECDSAwithSHA1`) |
| `SHA256withECDSA` | `:286` (`Alg.Alias.Signature.SHA256/ECDSA`) |
| `SHA384withECDSA` | `:293` (`Alg.Alias.Signature.SHA384/ECDSA`) |
| `SHA512withECDSA` | `:300` (`Alg.Alias.Signature.SHA512/ECDSA`) |

An alias can only point at an algorithm the provider actually registers, so each row is primary-source proof that the target exists on API 30. Add the four to the `SignatureSpec` allow-list, with one `divergence_record.csv` entry naming the four pointers and stating the same thing task 2.6's entry states: the omission is a MetaCrySL transcription gap, the root fix is in MetaCrySL, and it is **not executed here**. Justification to carry in the entry: ECDSA is the signature family Android pairs with `AndroidKeyStore` EC keys (task 2.6), so rejecting `SHA256withECDSA` while accepting `EC` key generation would report a violation on the platform's own recommended pairing.

## Task 2.8 — the Cipher allow-list stays in Java, in a new class

Decision D-b: the Cipher list does **not** migrate into the `.mop`. Consequence: this set needs a class of its own.

- `rvsec-core/.../jca/util/CipherTransformationUtil.java` (69 lines) belongs to the frozen `jca` and is covered by the gh101 freeze gate — untouchable.
- `rvsec-core/.../jca/util/AndroidCipherTransformationUtil.java` (262 lines) belongs to the reproved derived set, archived by task 2.1 as `jca_android_bug_predicate/` — untouchable, and it does **not** follow the name `jca_android` to the successor set.
- Create a third class in the same package, transcribing the lists of `generated/api30/Cipher.cryptsl` `CONSTRAINTS`: the algorithm set `part(0,"/",transformation) in {ChaCha20, AES_128, ARC4, RSA, DESede, AES, BLOWFISH, AES_256}` (8 entries, against the 2 families the frozen utility covers), the per-algorithm mode implications, and the per-algorithm/mode padding implications — including `part(0)="RSA" => part(2) in {OAEPwithSHA-512andMGF1Padding, OAEPwithSHA-224andMGF1Padding, PKCS1Padding, OAEPwithSHA-256andMGF1Padding, OAEPwithSHA-1andMGF1Padding, OAEPPadding, OAEPwithSHA-384andMGF1Padding, NoPadding}`, which is the clause the tier's 109-event `OAEPWithSHA1AndMGF1Padding` row would land on if the observed spelling matched. It does not: the observed string has no hyphen in `SHA1`, no provider registration in `OpenSSLProvider.java` carries that spelling, and task 2.5 therefore records it as a behavioural divergence instead of normalising it.
- Point `jca_android/CipherSpec.mop`'s static import at the new class; add a Java unit test mirroring `AndroidCipherTransformationUtilTest`.
- Gate G-CONF (Group 6, task 6.4) reads **this class** for the Cipher and the `.mop` files for the other 20.

Name it for what it is, not for its lineage (P4) — e.g. `Api30CipherTransformationUtil`. Do not name it `…V2`. It is the second new class this group adds to that package; the first is the alias table of task 2.5, and the two are separate because one answers "is this transformation allowed" and the other "what does this string denote".

## Task 2.9 — confirm the enumeration; do not extend it

There is **no new value to register**. The four accepted values already are `jca`, `jca_android`, `generic`, `custom`, and `SPEC_SET_JCA_ANDROID` already exists (`constants.py:97`). What this task does:

1. **Verify** that `click.Choice(["jca", "jca_android", "generic", "custom"])` (`__main__.py:443`), `valid_spec_sets` (`config.py:432-437`) and the mapping branch `SPEC_SET_JCA_ANDROID → os.path.join(mop_base_dir, SPEC_SET_JCA_ANDROID)` (`config.py:688-700`) are unchanged and now resolve to the successor set by construction — the mapping derives the directory from the value's own name, so re-pointing it required no code edit at all. Say so in the commit message; a reviewer who expects a diff here needs to know why there is none.
2. **Rewrite the prose that is now false.** Every one of these describes `jca_android` as the derived set: `constants.py:90-95` (comment block), `config.py:248`, `:385`, `:429`, `:648`, `:678`, `__main__.py:368`, `:656`, `:1193`. They must describe the successor set: 21 specifications, seeded from the frozen `jca`, allow-lists transcribed from api30 CrySL, no predicates.
3. **Add one test**, `test_jca_android_bug_predicate_not_selectable`, in `tests/test_config_validation.py` beside `test_near_miss_spec_set_still_rejected`: `specification_set="jca_android_bug_predicate"` must raise `ValueError` from `ExperimentConfig.validate.__wrapped__`. The existing `test_jca_android_spec_set_valid` (`:121`), `test_jca_android_spec_set_resolves_paths` (`test_config_jit.py:86`) and `test_near_miss_spec_set_still_rejected` (`:135`) stay **unchanged and green** — that is the evidence the enumeration did not move.

The invalid-value message keeps listing four values. If you find yourself editing it to list five, stop: something upstream went wrong.

## Task 2.13 — repoint the gh101 gate to the archive (immediately after 2.1)

Three scripts default to `resources/jca_android` and two tests call them with no path: `scripts/gh101_divergence_record.py:152` (`--derived` default), `scripts/gh101_predicate_pairing_check.py:156` (`--specs` default; `:157-161` `--inventory`), `scripts/gh101_conformance_check.py:269` (`--specs` default); `tests/parity/test_gh101_specset_gates.py:108` (`--check`) and `:122` (pairing) invoke the first two with no path. After 2.1/2.2 the divergence check reports every recorded hunk as stale and the pairing check a stale inventory (simulated read-only on 2026-08-18: 106 and 9 problems), so two of the five gates go red. Change the three defaults to `resources/jca_android_bug_predicate` (or the two test invocations), touch nothing in `data/gh101/`, and record in `data/jca_android/README.md` that the gh101 gate now guards the archive (INV-INS-118). Commit: `chore(gates): reaponta os gates gh101 para jca_android_bug_predicate (refs #104)`.

## Task 2.14 — harness before/after on this group's edits (waits for Group 6 task 6.9; before Group 8)

Replay `data/gh104/traces/<Spec>.txt` through the seed snapshot (post-2.2 commit) and the post-2.9 set for every touched file → `data/gh104/evidence/harness/s-<Spec>.md`. Admissible classes only: the 11 lost accusers → `removed`; every transcription difference → `removed` with reason `corrected verdict (<api30 file:line>)`; the 10 recovered guards → `introduced` (a guard that silenced the spec now lets it accuse — expected; cite the guard); anything else stops the group. Then run pass 2 of task 2.4: promote to transcribed checks the `deferred-constant` rows whose added accusations the harness sized. INV-INS-124: this group changes what is accused most and had no measurement of its own.

## Commands

```bash
# 2.1 — archive first, and only with git mv
cd ../rvsec/rvsec-mop/src/main/resources && git mv jca_android jca_android_bug_predicate
git status --short | grep -c '^R ' && git diff --cached --stat --find-renames   # 23 renames, 0 insertions, 0 deletions
# 2.2 — then seed
cp -r jca jca_android && rm jca_android/RandomStringPassword.mop jca_android/SecretKeySpec.mop && ls jca_android/*.mop | wc -l   # 21
cd -; uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh101_specset_gates.py -q   # 5 passed — only after task 2.13 repointed the three gh101 scripts to jca_android_bug_predicate; before it, 3 passed / 2 failed
uv run rv-experiment run --help | grep -A1 specification-set     # still exactly four choices; jca_android among them, jca_android_bug_predicate absent
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-experiment/tests -q
python3 scripts/gh104_divergence_record.py --check                # 0 unrecorded hunks
cd .. && mvn -q test -pl rvsec/rvsec-core                         # reactor root; the Cipher util's test AND the alias-table-equals-CSV test
```

## Acceptance

- `jca_android_bug_predicate/` holds the 23 `.mop` of the old derived set, byte-identical (`git log --follow` resolves each file across the rename, and `git diff --find-renames` shows zero content hunks); nothing selects it, and `test_jca_android_bug_predicate_not_selectable` proves the name is refused.
- `jca_android/` holds 21 `.mop` + `codes.csv`; `RandomStringPassword.mop` and `SecretKeySpec.mop` absent; `git diff` in the Java tree touches nothing under `jca/`, nothing inside `jca_android_bug_predicate/`, and neither `CipherTransformationUtil.java` nor `AndroidCipherTransformationUtil.java`; `MetaCrySL/` shows no modification at all.
- `grep -rn "ExecutionContext" jca_android/` returns nothing; the frozen `jca` still returns 134; `predicate_removal.csv` accounts for all 21 events plus the 9 `remove(...)` sites (30 rows); `constraint_table.csv` exists with one row per api30 clause and per clause-less `.mop` test.
- Every allow-list matches its api30 `CONSTRAINTS` clause modulo the declared normalisation, or has a conformance-record row saying why not — two `divergence_record.csv` entries are expected, the `EC` of task 2.6 and the four ECDSA algorithms of task 2.7; the MD5/SHA-1 cost of task 2.4 (5,892 of 6,048 rows) is recorded as a declared consequence, not as a divergence.
- Every `CRYSL-NAO-IMPLEMENTADO` clause of `constraint_table.csv` is either transcribed into an allow-list (promoted by 2.14) or carries a `deferred-constant` row in `conformance_record.csv`; none is left without one of the two, and G-CONF is green on the set.
- `data/jca_android/alias_table.csv` is byte-identical to `backup/gh104-analise/alias_table_conscrypt_android11.csv` (158 rows, 114 `yes`; 9 rows are `AlgorithmParameters`/`SecretKeyFactory`, services without a spec, kept with the flag); the sampled rows and their verification are named in the README; the two corrected pointers (`:115-116`, `:89-90`) appear nowhere in their old wrong form.
- The alias class exists in `rvsec-core`, is named by the 21 `.mop` of `jca_android` and by no file under `jca/`; its test asserts equality with the CSV and passes.
- `--specification-set jca_android` is accepted by the CLI and resolves to `.../resources/jca_android/` with no `custom_specs_dir`; an unknown value is rejected with a message listing exactly `jca, jca_android, generic, custom`.
- gh101's five gates still pass with their three scripts repointed to `jca_android_bug_predicate` (task 2.13; `data/gh101/` untouched); the harness evidence of task 2.14 exists for every touched file; `data/jca_android/` holds the six records (headers + this group's rows) and the README with the archive paragraph, the normalisation rule and the alias table's limits.
- Commits (one per pass keeps the divergence record readable): `chore(specs): arquiva o conjunto derivado reprovado como jca_android_bug_predicate (refs #104)`, `feat(specs): semeia o conjunto jca_android com 21 especificações a partir do jca congelado (refs #104)`, `refactor(specs): remove todo uso de ExecutionContext do jca_android (refs #104)`, `feat(specs): transcreve as allow-lists do jca_android a partir das regras CrySL api30 (refs #104)`, `feat(specs): resolução de alias Conscrypt android11-release no jca_android (refs #104)`.
