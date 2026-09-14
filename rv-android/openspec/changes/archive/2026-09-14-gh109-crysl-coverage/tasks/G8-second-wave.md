# G8 — Second validation wave (parallel per file, after G0)

Four external reports (`docs/analise_gh105_{gemini3,gpt-5,grok-4.6,opus5}.*`, 27/08) were adjudicated
against the primary sources in seven read-only verification lots on 27-28/08. The consolidated result is
`docs/20260827_relatorio_final_validacao_jca_android.md`; the per-claim table with vereditos is
`docs/20260827_adjudicacao_validacao_specs_jca_android.md`. **Those two documents are this group's
evidence base** — a subagent dispatched for a task reads its fiche below plus the anchors it cites, and
does not re-derive the adjudication.

Two rules govern the group, both inherited:

- **D-18 (verification before adoption).** Every fiche below cites the primary anchor that was read.
  ~20 claims of the reports were refuted or found already recorded and are listed in §"Not adopted" at
  the end — they must not re-enter later as "the reports said so".
- **D-26/D-27 (ratification before edit).** Tasks marked `[RATIFY]` change what the instrument accuses.
  The researcher's go/no-go goes into the task line in `tasks.md` before the file is touched. An
  unratified `[RATIFY]` task is not started. **All six were ratified GO on 2026-08-28** — 8.1 (D-26.5),
  8.3 (D-26.1), 8.4 (D-26.2), 8.5 (D-26.3), 8.6 (D-26.4, the repair-now option) and 8.7 (D-27). **8.9 was
  ratified GO on 2026-08-30**, on the D-26.2 addendum: task 7.6 measured that 8.4 had closed the clause
  at one arity only, and the two-argument route matches no event at all. 8.1 gained
  its marker with that ratification, having been the one D-26 item the list left unmarked. The reason and
  the execution order — 8.7, then 8.3/8.5, then 8.4/8.6, then 8.R, then 7.3, campaign once afterwards —
  are recorded in the group's preamble in `tasks.md`.

Records land once, in **8.R** — except each task's own `codes.csv` rows, which it appends itself, as in
G1–G4.

## The fiches

| Task | File(s) | What changes | Primary anchors read |
|---|---|---|---|
| 8.1 `[RATIFY · GO]` | `SecretKeySpecSpec.mop`, `PBEKeySpecSpec.mop` (comment only) | Write `ensure(Property.SPECCED_KEY, spec)` in the `@match` (the rule's ENSURES point), and replace the two false recorded reasons with the measured fact | rule `SecretKeySpec.crysl:26` (`speccedKey[this, _]`); omission + false reason at `SecretKeySpecSpec.mop:233-243`; twin false comment `PBEKeySpecSpec.mop:172-180`; the three readers `SecretKeyFactorySpec.mop:90`, `KeyFactorySpec.mop:79`, `:105`; ledger n.48 (`wireable`), n.121 (`producible, read by KeyFactory, SecretKeyFactory`) |
| 8.2 | `MacSpec.mop` | Remove `"PBEWITHHMACSHA"` and `"PBEWITHHMACSHA-256"` from `safeAlgorithms`; keep the six `HMAC-*`/`HMAC/*` spellings | rule `Mac.crysl:44` (nine algorithms; neither spelling present); `MacSpec.mop:40`; `alias_table.csv` service `Mac` (has `PBEWITHHMACSHA224/256/384/512`, no bare and no hyphenated form; the six `HMAC-*` rows alias to admitted canonicals) |
| 8.3 `[RATIFY · GO]` | `SecretKeyFactorySpec.mop`, `AlgorithmParameterGeneratorSpec.mop`, `AlgorithmParametersSpec.mop`, `SecureRandomSpec.mop` | Realize the rule's anonymous second position (INV-INS-157): add the `(String, Provider)` overload to the three fused `get` events and correct their "the two overloads api30 declares" comments; give `SecureRandomSpec`'s accuser an arity-open twin | rules `SecretKeyFactory.crysl:11`, `SecureRandom.crysl:20` (`getInstance(algorithm, _)`); pointcuts `SecretKeyFactorySpec.mop:52-57`, `AlgorithmParameterGeneratorSpec.mop:45-54`, `AlgorithmParametersSpec.mop:63-78`, `SecureRandomSpec.mop:136-140` (`args(alg)`, arity 1); `javap` over the API 30 `android.jar` (not the host JDK): three overloads; idiom `KeyFactorySpec.mop:50-52` |
| 8.4 `[RATIFY · GO]` | `KeyPairGeneratorSpec.mop` | Accusing branch for the algorithm clause + its `codes.csv` row (INV-INS-152) | rule `KeyPairGenerator.crysl:28`; `codes.csv:127-133` (no ALG code exists); `g3` absorbs the rejected `getInstance` at `:118-124`; the misleading `KEYPAIRGENERATOR-KEYSIZE-00` message at `:252-257`; contrast `codes.csv:119` (`KEYGENERATOR-ALG-00`) |
| 8.5 `[RATIFY · GO]` | `AlgorithmParametersSpec.mop` | `dhAlgorithms.contains(...)` / `pbeAlgorithms.contains(...)` → `ConscryptAliasTable.matches(...)` | rule `AlgorithmParameters.crysl:35-40`; raw sites `:135`, `:139`; the `matches` site three lines away at `:81`; `equalsIgnoreCase` in the same block at `:133`, `:143`; sibling done right `KeyAgreementSpec.mop:152,:156` |
| 8.6 `[RATIFY · GO — option A]` | `CipherSpec.mop`, `KeyStoreSpec.mop` | Reader accepts the rule's own spelling **and** the folded family; the KeyStore write **stays at arity 2** — the arity-1 correction was measured and declined, and is recorded instead; the false comment goes | rules `SecretKeyFactory.crysl:22-25,:31`, `Cipher.crysl:94-105,:134`, `KeyStore.crysl:60` (`generatedKey[key, _]`), `SecretKeySpec.crysl:27` (the re-wrap bridge); read site `CipherSpec.mop:180-181`; fold `CipherTransformationNormalizer.keyAlgorithm` (javadoc states the D-20.2 intent); raw writes `SecretKeyFactorySpec.mop:102`, `KeyStoreSpec.mop:189`; false comment `CipherSpec.mop:173-177` |
| 8.7 `[RATIFY · GO]` | `rv-android` consolidation (Python) + tests | Separate the `-NOBS-` channel on `site_kind` (INV-INS-158) | `codes.csv`: 64 `-NOBS-` + 86 `-CONSTR-`, all `UnsatisfiedConstraint`; measured: no consumer filters on the substring (zero hits in `modules/`, `scripts/`); 71 of 76 `validate` sites have a dead VIOLATED branch (the set holds one `negate`, `PBEKeySpecSpec.mop:188`) |
| 8.8 | `Property.java` (rvsec-core) | Javadoc on `GENERATED_TRUST_MANAGER` and `GENERATED_KEY_MANAGERS` | `TrustManagerFactory.crysl:32-33` (two clauses, one constant); sites `TrustManagerFactorySpec.mop:218,:256`, `KeyManagerFactorySpec.mop:176,:220`; `Property.java:59,61` (no javadoc; the dead sibling has one) |
| 8.9 `[RATIFY · GO]` | `KeyPairGeneratorSpec.mop` | The arity-2 negated twin `g4` (`KEYPAIRGENERATOR-ALG-01`), binding `algorithm` as `g3` does, plus the `ere` prefix `(g3 | g4)*` and the `order-unmapped` alphabet row | rule `KeyPairGenerator.crysl:28`; `g2`'s positive guard at `KeyPairGeneratorSpec.mop:110-115` and `g3`'s one-argument pointcut at `:137-144`; `algorithm != null` in `init1`/`initError`; the shape D-26.1 gave `SecureRandomSpec.mop` (`g5`, `SECURERANDOM-ALG-01`); the `behavioural` family row of `divergence_record.csv` (gh105 task 10.8) |
| 8.R | records | The group's records pass — see below | — |

## 8.6 — why this is one task and not two

Both ends belong to the same oracle clause family (`generatedKey`), and splitting them would let the set
sit, between two commits, in a state where the reader accepts two spellings while one producer still
writes a value the rule leaves anonymous. The letter, read across the three rules:

- For a **PBE transformation**, `SecretKeyFactory.crysl:31` ensures `generatedKey[key, algorithm]` with
  `algorithm` from its own list (`:22-25`), and `Cipher.crysl:134` requires
  `generatedKey[key, alg(transformation)]`. For that transformation the two are **the same string** —
  `Cipher.crysl:94-105` treats the whole PBE name as the transformation's algorithm. The oracle agrees
  with itself; the reader does not, because `keyAlgorithm` folds `AES_128`→`AES` (D-20.2, written for the
  alias/keysize route) and the fold spills here.
- The **direct** `PBKDF2WithHmacSHA*` → `Cipher("AES/...")` route does **not** match, and that is the
  oracle speaking, not a defect: the conforming path it provides is the re-wrap,
  `getEncoded()` → `new SecretKeySpec(bytes, "AES")` → `generatedKey[this, "AES"]`
  (`SecretKeySpec.crysl:27`). After this task that route stays accused, exactly as before.
- `KeyStore.crysl:60` writes the second position anonymous; `KeyStoreSpec.mop:189` writes
  `key.getAlgorithm()` raw, which is **stricter than the rule** — a store key whose spelling misses the
  reader's fold is accused where the rule says match. Dropping that write to arity 1 does **not** realize
  the `_`: `PredicateStore` has no wildcard, `ensure(p, key)` records the EMPTY tuple, and the three
  arity-2 readers (`CipherSpec.mop:199`, `SecretKeySpec.mop:122`, `KeySpec.mop:79`) would answer
  VIOLATED. `validateAny` — how an anonymous read is actually served — already answers SATISFIED against
  the write as it stands. The write stays at arity 2 and the departure is recorded, not repaired.

Done criterion for the pair: a trace of the conforming PBE chain draws no `CIPHER-CONSTR-00`, a trace of
the direct PBKDF2→AES route still draws it, and the keystore half is discharged by the record rather than
by an edit — the arity-1 write measured, declined and written down (divergence row `94be6e27a760`).

## 8.R — the records pass

1. One `divergence_record.csv` row per behavioural repair (8.3, 8.4, 8.5, 8.6, 8.7), each naming the
   oracle clause it restores and the D-26/D-27 item that ratified it; amend **row 289** (its reason,
   "with the canonical algorithm (D-20.3)", is empty for a service with no alias rows) and **row 23**
   (it asserts `SecureRandomSpec`'s `g4` "covers both arities"; `args(alg)` restricts it to one).
2. `predicate_graph.csv`: the new `speccedKey` write site (8.1) and the `generatedKey` arity change
   (8.6); re-derive the ledger.
3. `codes.csv` bijection after 8.3/8.4 append their rows, and after 8.9 appends `KEYPAIRGENERATOR-ALG-01`. 8.9 lands after this pass and carries its own records, the way G1-G4's tasks carry theirs: the alphabet rows, the trace pair and the amendment of the family row named in item 4, which stops reading `register only` for `KeyPairGeneratorSpec`.
4. The three negated-twin ORDER false positives that have no row of their own — `SecureRandomSpec`,
   `KeyGeneratorSpec`, `KeyPairGeneratorSpec` (`MessageDigestSpec` already has one, row 233; rows 23/24/26
   cover only the two-argument-silence family).
5. **The out-of-scope record of the two dexlib2 weaver defects.** The repair belongs to a separate change
   (researcher decision, 28/08); what this change owes is the row and the pointer:
   - nested types carry no `$` in `TypeResolver` (`:96-116`), so `KeyStoreSpec.mop:106-112`'s `ge1`/`se1`
     never weave under dexlib2 — silent false negative plus a spurious `KEYSTORE-ORDER-00` on every
     `load`…`store` (the `ere` at `:124` admits `store` only after `se1`). `KeyStoreBuilderParametersSpec.mop:29-46`
     documents the same mechanism and escapes it with `Object+`. **The `.mop`-side workaround is
     deliberately not applied here**: the root repair in the weaver fixes every specification at once,
     and applying the workaround would hide the defect from the change that must measure it.
   - `AfterEmitter`'s javadoc (`:9-13`) promises `finally` semantics that neither the inline insertion
     (`DexWeaver.java:921-927` → `InstructionInjector.insertAfter`) nor the wrapper
     (`WrapperEmitter.java:783-801`) implements; 58 of the set's 202 events are plain `after`, so ajc and
     dexlib2 disagree on any trace that throws. Full analysis:
     `docs/20260827_divergencia_after_dexlib2_ajc.md`.
6. No harness checkpoint of its own — G7's checkpoint 2 (task 7.3) covers G8.

## Not adopted (verified and refuted, or already recorded — do not re-enter)

| Claim of the reports | Why it is not a task |
|---|---|
| "The RSA/ECB padding admissions (`NoPadding`, `PKCS1Padding`, `OAEPWithMD5`) lack an oracle-wart row" | Row 8 already covers all three |
| "$ORACLE ≠ upstream (CCM) is unrecorded" | Row 11 and the README record it; the pinned copy is upstream + the two `CCM` lines of `Cipher.crysl:97,113` |
| "GCM without AAD passes mute" | `Cipher.crysl:118`'s `noCallTo[AADUpdate]` covers exactly the seven **non-AEAD** modes, and `AADUpdate*` in the ORDER is optional — GCM without AAD conforms |
| "`SecureRandom.nextInt` has no event" | `next1`/`next3` exist; the real gap (the `randomized` ENSURES) is decided and documented in place (task 11.5) |
| "Un-defer the KeyGenerator AES keysize" | Refuted three times on 25/08 (`init(64)` throws `InvalidParameterException`; no event binds the int). Residue accepted: the deferral lives in `constraint_table.csv:42` / `conformance_record.csv` line 10 |
| "Retire `RandomStringPassword.mop` to `backup/`" | Contradicts the disposition recorded in the file itself (modelling parity, the same disposition as `wkb1`/`ints`); record, do not execute |
| "MessageDigest's negated twin has no record" | Row 233 |
| "`Cipher` ENS#03 stages a null plaintext" | Deliberate and documented; no consumer reads the second position of `ENCRYPTED` (the only reader uses the first) — cost zero |
| "Arity projections of `MACED`/`DIGESTED`/`SIGNED` lose information" | Every reader uses the preserved position; recorded in `predicate_graph.csv` |
| "Add `LC_ALL=C` to the pinning recipe" | Withdrawn by task 6.3, measured; re-measured 28/08: `C` and `C.UTF-8` both give `6d92bc6d…`, a language UTF-8 locale gives the pinned `d7bcc019…`, and the files are byte-identical either way. The residue is one documentary sentence, folded into 6.3 |
| KMF/TMF double accusation, `SSLContext`'s `Engine*`, a rejected `getInstance` never `init`ed, `encmode`, `noCallTo[IWOIV]`, the `g3` sink, the empty padding, the `preparedKeyMaterial` origin gate, the orphan `generatedKeypair` | All recorded deferrals or decisions with a reason and an owner (rows 6, 23, 24, 26, 39, 179, 274; `gate_allowlist.csv:16-21,43-44`, each with the D-16 re-anchoring addendum). Reopening them without new evidence would violate the record |
| AndroidKeyStore / `KeyGenParameterSpec` / StrongBox / attestation | No expert rule — issue #110, whose first task is to pin an oracle |
