# Tasks: gh109-crysl-coverage

**What "complete" means here.** Milestone M1 (the essential half) closes when groups 0, 1, 2 and 1b are
green plus the M1 slices of groups 6 and 7: the 9 verified repairs applied, the 14 trivial producer specs
landed, five of the six producer predicate gaps closed **with the three unblocked reads opened at their
consuming sites** (D-24 — a written predicate nobody reads is not a closed gap), and the battery green
over the enlarged set.
Milestone M2 closes the remaining coverage (groups 3, 4, 5), **the second validation wave (G8)** and the
final verification. G8 folds in the findings the four external reports produced on 27/08 and that were
re-verified against the primary sources on 27-28/08 (D-25): five behavioural repairs the oracle's own
letter asks for (D-26), the consolidation channel for `-NOBS-` (D-27), and the records those two move.
G7 runs **once** over the enlarged surface — it is not repeated for G8. Every group
heading points to `tasks/G<N>-*.md` — the per-group execution file with the inventory, per-spec
fiches, commands and done-criteria. A subagent dispatched for a group reads ONLY its group file plus
the artifacts it cites; the orchestrator reads only this file and ticks boxes immediately on completion.

<!--
Subagent dispatch (docs/WORKFLOW.md §5) — lighter protocol than gh105 (design.md D-22):
- G0 is the critical path and is SHORT (one session): oracle-defect rows, the producer-spec template,
  conventions, the .rvm-preserving fixture. Nothing else starts before G0 lands.
- After G0: G1 ∥ G2 — fully parallel. Within G1 each repair touches one .mop (or one rvsec-core file);
  within G2 each spec is one new file. Disjoint by construction. Shared files are OWNED:
  codes.csv rows are appended per-task in file order (each task's rows named in its fiche);
  divergence_record/predicate_graph/ledger/alphabet are touched ONLY by the group's closing records
  task (X.R) in the parallel spec groups G1–G4, never by their individual spec tasks (the sequential
  G0 and G5 tasks own their record rows directly).
- G1b after G2: it opens reads whose producers G2 lands, so it cannot start earlier. Its three tasks
  touch three .mop files; one of them, KeyPairGeneratorSpec.mop, is also edited by 1.2 (R2), so G1b's
  1b.1 waits for 1.2 to land — the only ordering constraint between G1 and G1b.
- G3 after G2's template is proven (first records pass green). Within G3, 3.6 and 3.7 additionally
  wait for 1.3(b), which writes the `generatedMessageDigest` their reads consume — the second ordering
  constraint out of G1, and the only one that reaches G3. G4 after G3 (needs the oracle-defect
  rows of G0 and the confidence of two tiers). G5 anytime after G0. G6 has an M1 slice (enumeration
  constants — lands in the SAME commit as the first new spec) and an M2 slice (stale-record
  corrections — batched). G7 runs once per milestone.
- Java-side work runs in the sibling reactor with the JDK 21 prefix and /home/pedro/... paths
  (the /pedro/... alias does not resolve in the JVM). Build: `mvn clean install -DskipMopAgent
  -DskipTests` (~53 s). Monitor generation: inspect the artifact, never the exit code (INV-INS-145);
  at most one generating task at a time (orchestrator-serialized).
- Records cadence (D-22): ONE records pass per group (the X.R task), harness at TWO checkpoints
  (1.R after repairs; 7.3 final). New file = one `new-file` divergence row.
- Commit messages NEVER carry Co-Authored-By or any co-author trailer (CLAUDE.md) — repeated because
  subagents commit. Commit with explicit paths (`git commit -- <paths>`) — the repo is shared.
- G8 (second wave) after G0, and independent of G1-G5: its spec tasks touch six files none of those
  groups still own, so it is parallel per file inside itself. Three ordering facts, all real: both ends of
  the PBE chain edit the `CipherSpec.mop`/`KeyStoreSpec.mop` neighbourhoods, so they are ONE task (8.6)
  rather than two; 8.R (records) is the group's X.R and runs last, as in G1-G4; and 8.7 is Python-only
  (`rv-android` consolidation), shares no file with anything, and runs first by the ratified order.
- G8 tasks that change what is accused carry `[RATIFY]`: the researcher's go/no-go is recorded in the
  task line before the edit is made. A `[RATIFY]` task that has not been ratified is not started. All six
  (8.1, 8.3-8.7) were ratified GO on 2026-08-28 — see the group's preamble for the reason and the order.
- Checkpoint rule: tick each box immediately on completion, before starting the next task.
-->

## 0. G0 — Foundation (sequential, one session) — `tasks/G0-foundation.md`

- [x] 0.1 Record the D-21 narrative rows: the three oracle defects + the `OAEPParameterSpec.crysl:8` anomaly + the `1^2048` semantics note (D-20.4) — five rows
- [x] 0.2 Write the producer-spec template + conventions note (naming, codes, predicate placement, fiche format)
- [x] 0.3 Build the `.rvm`-preserving generation fixture procedure and refresh `results/gh51_e2e_test/monitors`
- [x] 0.4 Add the coverage-matrix derivation (`scripts/gh109_coverage_matrix.py` + parity test, INV-INS-150)
- [x] 0.5 Record the five D-20 value decisions as divergence narrative rows (they change what is accused)
- [x] 0.6 Run `/rv-doc-code scripts/gh109_coverage_matrix.py`
- [x] 0.7 Add the ~14 `Property` enum constants the new specifications write (`rvsec-core`), in one commit — the shared-file dependency of G2/G3/G4

## 1. G1 — Verified repairs to existing specs (parallel per file, after G0) — `tasks/G1-repairs.md`

- [x] 1.1 R1 `DHGenParameterSpecSpec`: condition → accusing body + `DHGENPARAMETERSPEC-CONSTR-00`
- [x] 1.2 R2 `KeyPairGeneratorSpec`: `initError2` twin for `initialize(int, SecureRandom)`
- [x] 1.3 R3 `MessageDigestSpec`, two halves: **(a)** value check on the `d1`/`d3` route; **(b)** the omitted `generatedMessageDigest` write in `g1`/`g2`/`g3` (`MessageDigest.crysl:46`) — not a repair, folded in here because R3 already edits the file and 3.6/3.7 cannot read a predicate nobody writes
- [x] 1.4 R4 `CipherOutputStreamSpec`: `ere` — `fl` no longer satisfies the `+`
- [x] 1.5 R5 `SecretKeySpec`: `SecretKey+.getEncoded()` (verify `+`-owner weaves on dexlib2 first)
- [x] 1.6 R6 `CipherSpec:177`: splitter → `CipherTransformationNormalizer.alg` + AES_128/AES_256 ≡ AES (D-20.2)
- [x] 1.7 R7 `CipherTransformationNormalizer.isValid`: admit the 8 expert PBE families (D-20.1)
- [x] 1.8 R8 `KeyGeneratorSpec:215`: write canonical predicate value (D-20.3)
- [x] 1.9 R9 `IvParameterSpec`: `len > 0` + accuser on the reachable violated branch
- [x] 1.10 Optional hygiene: delete the 8 write-only `current*` fields (P3)
- [x] 1.R Group records pass — including the predicate write of 1.3(b), which is not a repair and moves the graph: three `predicate_graph.csv` rows (`g1`/`g2`/`g3`) carrying the `after Get` reason that closes INV-INS-134 and the transitory `unmonitored-consumer` disposition that closes G-PRED2, plus the one-word extension of `RECORDED_WRITE_DISPOSITIONS` that admits it and the amendment of the `PBEKeySpecSpec` row the extension falsifies (D-24) — + trace pairs for R1/R4/R9 + **harness checkpoint 1** (diff vs pre-G1)

## 2. G2 — Trivial producer specs, 14 files (parallel per spec, after G0) — `tasks/G2-producers-trivial.md`

- [x] 2.1 `RSAKeyGenParameterSpecSpec.mop` (`preparedRSA`)
- [x] 2.2 `ECGenParameterSpecSpec.mop` (`preparedEC`, curve list)
- [x] 2.3 `ECParameterSpecSpec.mop` (`preparedEC`)
- [x] 2.4 `DSAParameterSpecSpec.mop` (`preparedDSA`, bit-length ≥ 2048 per D-20.4)
- [x] 2.5 `DHParameterSpecSpec.mop` (`preparedDH`, bit-length ≥ 2048)
- [x] 2.6 `MGF1ParameterSpecSpec.mop` (`preparedMGF1`)
- [x] 2.7 `OAEPParameterSpecSpec.mop` (`preparedOAEP`; REQUIRES `preparedMGF1` — wire after 2.6)
- [x] 2.8 `KeyStoreBuilderParametersSpec.mop` (`generatedManagerFactoryParameters`)
- [x] 2.9 `CertPathTrustManagerParametersSpec.mop` (`generatedManagerFactoryParameters`; reads `generatedCertPathParameters`)
- [x] 2.10 `PKIXParametersSpec.mop` (`generatedCertPathParameters`; reads `generatedKeyStore`)
- [x] 2.11 `PKIXBuilderParametersSpec.mop` (`generatedCertPathParameters`; reads `generatedKeyStore`)
- [x] 2.12 `TrustAnchorSpec.mop` (`generatedTrustAnchor`; reads `generatedPubkey`)
- [x] 2.13 `X509EncodedKeySpecSpec.mop` (`speccedKey`; reads `preparedKeyMaterial`)
- [x] 2.14 `KeySpec.mop` — interface rule `Key` (`Key+.getEncoded()`, writes `preparedKeyMaterial`)
- [x] 2.R Group records pass (new-file rows, graph, ledger — five of the six named producer gaps plus `preparedDH` must show closed) + [GEN] monitor + gates

## 1b. G1b — Consumer reads unblocked by the producers (after G2) — `tasks/G1b-consumer-reads.md`

- [x] 1b.1 `KeyPairGeneratorSpec`: the four guarded reads of `KeyPairGenerator.crysl:35-38` in `init3`/`init4` (after 1.2)
- [x] 1b.2 `KeyManagerFactorySpec`: `generatedManagerFactoryParameters` read on the bound `arg` (`:114`)
- [x] 1b.3 `TrustManagerFactorySpec`: the twin read (`:142`)
- [x] 1b.4 Record the deferred `Cipher.crysl:136` `preparedAlg` read (F7 form: ceiling 17/17 + `i2` binds no `params`)
- [x] 1b.R Group records pass + trace pairs (satisfy/violate/not-observed per site) + [GEN] monitor + gates

## 3. G3 — Medium specs, 7 files (parallel per spec, after G2 template proven) — `tasks/G3-medium.md`

- [x] 3.1 `AlgorithmParametersSpec.mop` (`preparedAlg`; 4 conditional REQUIRES implications)
- [x] 3.2 `AlgorithmParameterGeneratorSpec.mop` (`preparedAlg`; reads `randomized`)
- [x] 3.3 `SecretKeyFactorySpec.mop` (`generatedKey`; reads `speccedKey` — the password→key route)
- [x] 3.4 `KeyFactorySpec.mop` (`generatedPrivkey`/`generatedPubkey`; reads `speccedKey`)
- [x] 3.5 `CertificateFactorySpec.mop` (`generatedCert`)
- [x] 3.6 `DigestInputStreamSpec.mop` (reads `generatedMessageDigest`, written by 1.3(b) — **after 1.3**; FORBIDDEN `on(boolean)`)
- [x] 3.7 `DigestOutputStreamSpec.mop` (same family, same dependency on 1.3(b); apply the R4 lesson to its `ere`)
- [x] 3.R Group records pass (`preparedAlg` gap must show closed; ledger rows #17/#18/#103 leave `unmonitored-consumer`/`unmonitored-consumer-side` now that both ends are paired, and must land on wired rather than on `unmonitored-producer` — that is what 1.3 bought; the three `MessageDigestSpec` graph rows must **lose** the transitory `unmonitored-consumer` 1.R wrote, and every *other* write row of the graph is re-derived too — this group lands consumers for predicates written under `omission` when no consumer existed, and G-PRED2 stops raising a row the moment any specification reads its name, D-24) + [GEN] monitor + gates

## 4. G4 — Complex specs + adjudications (after G3) — `tasks/G4-complex-adjudications.md`

- [x] 4.1 `SSLEngineSpec.mop` (transcribe evident intent over the `cp1` defect row from 0.1)
- [x] 4.2 `SSLParametersSpec.mop` (3 constructor paths)
- [x] 4.3 `KeyAgreementSpec.mop` (5 events, `noCallTo[gs3]`, `gs2` defect row from 0.1)
- [x] 4.4 Adjudicate N/A: `Cookie` (no class), `DSAGenParameterSpec` (API 35+), `PasswordAuthentication` (D-19, ratified: recorded N/A-by-value)
- [x] 4.R Group records pass + [GEN] monitor + gates

## 5. G5 — Android ports (anytime after G0) — `tasks/G5-android-ports.md`

- [x] 5.1 `HMACParameterSpecSpec` platform-dead disposition (INV-INS-155; reconcile ledger rows #38/#80)
- [x] 5.2 The KeyStore alias gap recorded, not filled — **revised**: the pinned Conscrypt `OpenSSLProvider.java` registers no `KeyStore` alias at all (measured: 175 `Alg.Alias`, 175 rows, zero occurrences of the string), so a BC row would be the first with no provider line to cite (INV-INS-127); the four store names already enter through the closed `platform-value` set and `matches` resolves them by case folding; the corpus measures no other spelling. README declared-limit paragraph + divergence narrative row; no table row, no `ConscryptAliasTable` edit, no reactor build
- [x] 5.3 TLS-default-per-platform note + `getSocketFactory` non-addition recorded (D-20.5)
- [x] 5.4 Seed the AndroidKeyStore future issue (out-of-scope record with the 3 candidate accusations)

## 6. G6 — Records, censuses, enforcement constants — `tasks/G6-records.md`

- [x] 6.1 [M1, same commit as first new spec] CI/gate enumeration constants: `Corpora`, `MopLiftCorpusTest`, `CalibrationTargets`, G-PARAM count, G-ORDER skip set (D-23)
- [x] 6.2 [M1] Alphabet-map chain for new specs (`gh105_expert_alphabet.py --emit` + `--check`)
- [x] 6.3 [M2] Verified stale-record corrections: README site census 115→125 + sibling scalars (the "38" reads is 36 `validate(` + 5 `validateAbsent(`); `constraint_table.csv` verdict cells + seed-resolved pointers; `predicate_graph.csv` reasons — 69 of 76 rows, measured; ledger `SecretKeySpec` chain rows + `PREDICATE_ALIASES` unfusion. The `next1`/`next3` rows move to 6.2 (a mapping decision, not a repair); the `LC_ALL=C` recipe item is withdrawn — measured, it breaks the hash it was meant to fix. **Second wave (D-25) adds to this same task**: the false recorded reasons the verification found — `IvParameterSpec.mop:60-61` ("no specification reads `PREPARED_IV`" — two do), `PBEParameterSpecSpec.mop:144-146` ("`preparedPBE` required by no rule" — `AlgorithmParameters.crysl:37-39` requires it and `:141` reads it), `KeyFactorySpec.mop:67` (names a producer that does not write), ledger n.49/n.118-119 (`SecretKeySpec` writes `PREDICATE_KEY_MATERIAL` at `:145`), divergence rows 160/225/307/334 (reason copied from another spec, citing the withdrawn `KeyGenerator.cryptsl` as authority), row 13 (claims fold+alias already cover the six `HMAC-*` spellings of `SecretKeySpecSpec` — measured false: no `SecretKeySpec` service in the table, so the entries are load-bearing), row 23 (claims `SecureRandomSpec`'s `g4` "covers both arities" — `args(alg)` restricts it to one), `GCMParameterSpecSpec.mop:95-103` ("measured on all three, each throws" — false for `len > 0`: `(128, iv, 0, 0)` returns), the eight duplicated `(file,hunk)` keys plus the loader that would let a divergent duplicate win silently (`gh104_divergence_record.py:257-260`), the `oracle-wart` row the oracle's internal RSA disagreement still lacks (`RSAKeyGenParameterSpec.crysl:15` admits 1024, `KeyPairGenerator.crysl:29` requires ≥2048), the `Cipher.crysl:88/:90` `instanceOf` antecedents recorded under a `NAO-DERIVADO` that over-asserts, `coverage_matrix.csv:28` ("25 platform jars" — 26), the stale scalars in `rvsec-crysl/CLAUDE.md:61,:74` ("jca_android (24)" — 48; "215 files" — 239) and the seven javadocs carrying the same 215, and one sentence in `data/jca_android/README.md` recording that the pinning recipe assumes a language UTF-8 collation (`C`/`C.UTF-8` yield `6d92bc6d…` with the files unchanged) and that the order-free integrity check is `sha256sum -c oracle/expert_rules.sha256`
- [x] 6.4 [M2] Extend the sole-oracle gate to `rvsec-core` Java + amend the 3 stale api30 citations — the second wave names them and confirms two are load-bearing, not cosmetic: `ErrorType.java:16` justifies the `ForbiddenMethod` constants by citing `generated/api30/PBEKeySpec.cryptsl` (the clauses are in the pinned expert `PBEKeySpec.crysl`), and `Property.java:88-92` denies an ENSURES the oracle states (`Cipher.crysl:148` declares `wrappedKey[wrappedKeyBytes, wrappedKey]`) using the withdrawn catalogue's spelling — a false premise that is the recorded justification for deleting the write in gh105 4.1 (the operational conclusion survives: no rule of the 49 requires it). Still **blocked on a researcher decision**: the gate would also flag the conformance component's legitimate `rvsec-cognicrypt` stamps (design Open Questions)
- [ ] 6.5 [M2, at sync] Re-derive the two gh105-delta enumeration literals in the main spec during the manual `/opsx:sync` review (design Risks)

## 8. G8 — Second validation wave: repairs the oracle's letter asks for (parallel per file, after G0) — `tasks/G8-second-wave.md`

Every task below was re-verified against the primary sources before entering (D-25); the reports are
candidate generators only. Tasks marked `[RATIFY]` change what the instrument accuses (D-26/D-27) and
are not started before the researcher's go/no-go is written into the task line.

**Ratified 2026-08-28 (researcher): GO on all six** — 8.1, 8.3, 8.4, 8.5, 8.6 and 8.7, which is D-26.1
through D-26.5 plus D-27; for 8.6, the repair-now option and not the measure-first one. **A seventh was
ratified GO on 2026-08-30**, after task 7.6 measured what 8.4 had left standing: 8.9, the D-26.2
addendum, which lands after 8.4 and answers the same clause at the arity 8.4 did not reach. 8.1 carries the
marker from this ratification on: it was the one D-26 item the task list left unmarked, and it does move
what is accused — the `speccedKey` write makes three reading sites (`SecretKeyFactorySpec.mop:90`,
`KeyFactorySpec.mop:79`, `:105`) stop answering NOT_OBSERVED.

Two measured facts decided the timing. `jca_android` carries **no published number** — the frozen `jca` is
what the published measurements answer to — and the gh104 campaign **has not run**
(`experimento-gh104/consolidado/` is empty). This is therefore the cheapest moment this change will ever
have to move what the instrument accuses: once the campaign runs, each of the six costs either a second
pass over the 162 APKs or a comparability caveat on the results. The measure-first option for 8.6 was
declined on the same arithmetic — the cost of a corpus pass is fixed, and a second one would buy an
answer that reading `SecretKeyFactory.crysl:31`, `Cipher.crysl:134` and `:94-105` together already gives.

**Execution order inside the group**, decided with the ratification: **8.7 first** (the only one that
changes nothing on the device, and what makes 7.3's NOBS rate readable), then **8.3 and 8.5** (the letter
of the rule), then **8.4 and 8.6** (the two that move or remove an accusation), then **8.R**, then **7.3**.
The campaign runs once, after all of them. 8.2 and 8.8 carry no ratification and may land anywhere in the
group.

- [x] 8.1 [M2] [RATIFY · D-26.5 — GO, researcher, 2026-08-28] `SecretKeySpecSpec`: write `speccedKey` (`SecretKeySpec.crysl:26`) in the `@match`, and replace the two false recorded reasons — `:233-238` ("its consumer is SecretKeyFactory, which has no specification in this set") and the twin at `PBEKeySpecSpec.mop:172-180` — with the measured fact (three sites read `SPECCED_KEY`: `SecretKeyFactorySpec.mop:90`, `KeyFactorySpec.mop:79`, `:105`; ledger n.48/121 already say `wireable`/`producible`)
- [x] 8.2 [M2] `MacSpec`: remove `PBEWITHHMACSHA` and `PBEWITHHMACSHA-256` from the admitted list (`:40`) — neither is in `Mac.crysl:44` nor has a row in `alias_table.csv` for the `Mac` service; keep the six `HMAC-*`/`HMAC/*` spellings, which alias to admitted canonicals. Record the measured mitigation: under the pinned Conscrypt those two spellings throw in `getInstance`, so the after-returning event never fires and the departure only bites with a bundled BouncyCastle
- [x] 8.3 [M2] [RATIFY · D-26.1 — GO, researcher, 2026-08-28] Realize the rule's anonymous second argument (INV-INS-157) in the four sites that narrow it: `SecretKeyFactorySpec.mop:52-57`, `AlgorithmParameterGeneratorSpec.mop:45-54`, `AlgorithmParametersSpec.mop:63-78` gain the `(String, Provider)` overload the API 30 `android.jar` declares (and lose the "the two overloads api30 declares" comment, which is false); `SecureRandomSpec.mop:136-140` gains the arity-open twin (`args(alg, *)` with the negated condition) so a provider-route `getInstance` of a rejected PRNG is accused for its value instead of drawing a spurious ORDER at the next call. Idiom to copy: `KeyFactorySpec.mop:50-52`
- [x] 8.4 [M2] [RATIFY · D-26.2 — GO, researcher, 2026-08-28] `KeyPairGeneratorSpec`: give `KeyPairGenerator.crysl:28` an accusing branch (INV-INS-152) with its own `codes.csv` row — today the specification has no ALG code at all, `g3` absorbs the rejected `getInstance`, and the misuse surfaces as `KEYPAIRGENERATOR-KEYSIZE-00` asserting a clause the rule does not state for that algorithm, plus two spurious ORDER lines. Verified distinct from the Mac/Signature residue of gh105 10.8(a), where the accusation migrates rather than disappears
- [x] 8.5 [M2] [RATIFY · D-26.3 — GO, researcher, 2026-08-28] `AlgorithmParametersSpec:135,:139`: the antecedents of `AlgorithmParameters.crysl:35-40` resolve through `ConscryptAliasTable.matches` like the other 55 comparison sites of the set (and like the sibling `KeyAgreementSpec.mop:152,:156`), so `getInstance("dh")` reaches the `preparedDH` read instead of falling out of every branch in silence
- [x] 8.6 [M2] [RATIFY · D-26.4 — GO, researcher, 2026-08-28: option A (repair now), not the measure-first option] The PBE chain, both ends, in one task because both are the `generatedKey` clause family: the `CipherSpec.mop:180-181` read accepts the rule's own spelling **and** the folded family (the letter of `SecretKeyFactory.crysl:31` × `Cipher.crysl:134` for a PBE transformation is the same string; the D-20.2 fold was written for the alias/keysize route and spills into this one), and the `KeyStoreSpec.mop:189` half is discharged by measurement rather than by an edit: dropping that write to arity 1 does not realize the anonymous position of `KeyStore.crysl:60`, because `PredicateStore` has no wildcard and the empty tuple it would record makes three arity-2 readers (`CipherSpec.mop:199`, `SecretKeySpec.mop:122`, `KeySpec.mop:79`) answer VIOLATED, while `validateAny` already serves the anonymous read SATISFIED against the write as it stands — so the write stays at arity 2 and the departure stays recorded (divergence row `94be6e27a760`). Correct the comment at `CipherSpec.mop:173-177`, which claims the PBE name "matches no key any producer of this set ever wrote" — `SecretKeyFactorySpec.mop:102` writes exactly that name — and amend divergence row 289, whose reason ("with the canonical algorithm (D-20.3)") is empty for a service with no alias rows
- [x] 8.7 [M2] [RATIFY · D-27 — GO, researcher, 2026-08-28] Consolidation channel for `-NOBS-` (INV-INS-158): the results consumer separates on `codes.csv`'s `site_kind`, so a `-NOBS-` line is never summed as conformance nor as violation. Python-side only, with tests; nothing changes on the device. Does **not** measure the NOBS rate — that is 7.3 — and does not decide whether any producer should `negate`
- [x] 8.8 [M2] `Property.java`: javadoc for `GENERATED_TRUST_MANAGER` and `GENERATED_KEY_MANAGERS`, each of which carries two distinct oracle clauses (the array `generatedTrustManagers[trustManager]` and the factory `generatedTrustManager[this]`, `TrustManagerFactory.crysl:32-33`; the KMF analogue), told apart by object identity — no verdict moves, and today neither constant has a line while the dead sibling has an extensive one
- [x] 8.9 [M2] [RATIFY · D-26.2 addendum — GO, researcher, 2026-08-30] `KeyPairGeneratorSpec`: the arity-2 negated twin of `g3`, in the shape D-26.1 gave `SecureRandomSpec.g5` — today `getInstance(String, Object+)` with a rejected algorithm matches no event at all, because `g2`'s guard is positive and `g3`'s pointcut is one-argument, so 8.4 left the clause of `KeyPairGenerator.crysl:28` accusing at one arity and silent at the other. It costs more here than in the five specifications the F7 family row defers: `algorithm` is the field `init1` and `initError` both test for null, so the object goes on unbound and the specification stays silent for it entirely. Event `g4` binding `algorithm` as `g3` does + `KEYPAIRGENERATOR-ALG-01` in `codes.csv` + the `ere` prefix `(g3 | g4)*` + the `order-unmapped` row in `order_alphabet_map.csv` with the expert map and delta re-emitted + a trace pair over the two-argument overload + the amendment of the family row, which stops reading `register only` for this file
- [x] 8.R [M2] Group records pass: `new`/amended divergence rows for 8.1-8.6 (each behavioural repair gets its row, D-26), predicate-graph rows for the `speccedKey` write and the `generatedKey` arity change, ledger re-derivation, `codes.csv` rows for 8.3/8.4, and the **out-of-scope record of the two dexlib2 weaver defects** (nested-type `$` and `after()` without finally — the repair belongs to a separate change, and what this one owes is the row plus the pointer to `docs/20260827_divergencia_after_dexlib2_ajc.md`). No harness checkpoint of its own: G7's checkpoint 2 covers G8

## 7. G7 — Verification (once per milestone, single session) — `tasks/G7-verification.md`

- [x] 7.1 [M1] Full battery over the enlarged set: [GEN] monitor (artifact inspection), `tests/parity`, all record `--check`s, G-SIG/G-FORB/G-BIND, Maven gh106 tests
- [x] 7.2 [M1] Ledger assertion, both sides: the five named producer gaps plus `preparedDH` closed (`preparedAlg` after G3; `preparedKeyMaterial` fully after 4.3; `generatedMessageDigest` written by 1.3 and read from 3.6/3.7), and every predicate the set writes read at a consuming site or carrying a recorded impossibility (D-24) — transitory dispositions enumerated, each naming the task that owes its retirement, since G3 is M2 work and 1.R's `unmonitored-consumer` is legitimately still standing here; coverage matrix shows no rule without a terminal state among the landed tiers; run `/rv-verify` on the touched Python surface
- [x] 7.3 [M2] **Harness checkpoint 2** (final, covering G8 as well — the second wave gets no checkpoint of its own): differential classification attributed per group; battery green; coverage matrix complete — 49/49 terminal states over three values, `oracle_defect_row` filled by join; no transitory disposition survived its reason, in the graph or in the ledger; **NOBS rate of the G1b sites read over the APK corpus, for the researcher's decision on whether any NOBS branch retires** (D-24). This rate is the **first** reading of the channel 8.7 separates, and is comparable to no earlier count — before 8.7 a `-NOBS-` line was summed indistinguishably from a `-CONSTR-` one
- [x] 7.4 [M2] Run `/rv-qa-lint-fix scripts/ tests/parity/`
- [x] 7.5 [M2] Run `/rv-verify` on the same touched surface
- [x] 7.6 [M2] Run `/rv-code-reviewer` on the change surface
