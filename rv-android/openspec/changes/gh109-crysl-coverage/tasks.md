# Tasks: gh109-crysl-coverage

**What "complete" means here.** Milestone M1 (the essential half) closes when groups 0, 1, 2 and 1b are
green plus the M1 slices of groups 6 and 7: the 9 verified repairs applied, the 14 trivial producer specs
landed, five of the six producer predicate gaps closed **with the three unblocked reads opened at their
consuming sites** (D-24 — a written predicate nobody reads is not a closed gap), and the battery green
over the enlarged set.
Milestone M2 closes the remaining coverage (groups 3, 4, 5) and the final verification. Every group
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
- [ ] 4.R Group records pass + [GEN] monitor + gates

## 5. G5 — Android ports (anytime after G0) — `tasks/G5-android-ports.md`

- [ ] 5.1 `HMACParameterSpecSpec` platform-dead disposition (INV-INS-155; reconcile ledger rows #38/#80)
- [ ] 5.2 BouncyCastle alias rows for the KeyStore service family (table + `ConscryptAliasTable` mirror)
- [ ] 5.3 TLS-default-per-platform note + `getSocketFactory` non-addition recorded (D-20.5)
- [ ] 5.4 Seed the AndroidKeyStore future issue (out-of-scope record with the 3 candidate accusations)

## 6. G6 — Records, censuses, enforcement constants — `tasks/G6-records.md`

- [x] 6.1 [M1, same commit as first new spec] CI/gate enumeration constants: `Corpora`, `MopLiftCorpusTest`, `CalibrationTargets`, G-PARAM count, G-ORDER skip set (D-23)
- [ ] 6.2 [M1] Alphabet-map chain for new specs (`gh105_expert_alphabet.py --emit` + `--check`)
- [ ] 6.3 [M2] Verified stale-record corrections: README site census 115→125 + sibling scalars (the "38" reads is 36 `validate(` + 5 `validateAbsent(`); `constraint_table.csv` verdict cells + seed-resolved pointers; `predicate_graph.csv` reasons — 69 of 76 rows, measured; ledger `SecretKeySpec` chain rows + `PREDICATE_ALIASES` unfusion. The `next1`/`next3` rows move to 6.2 (a mapping decision, not a repair); the `LC_ALL=C` recipe item is withdrawn — measured, it breaks the hash it was meant to fix
- [ ] 6.4 [M2] Extend the sole-oracle gate to `rvsec-core` Java + amend the 3 stale api30 citations — **blocked on a researcher decision**: the gate would also flag the conformance component's legitimate `rvsec-cognicrypt` stamps (design Open Questions)
- [ ] 6.5 [M2, at sync] Re-derive the two gh105-delta enumeration literals in the main spec during the manual `/opsx:sync` review (design Risks)

## 7. G7 — Verification (once per milestone, single session) — `tasks/G7-verification.md`

- [ ] 7.1 [M1] Full battery over the enlarged set: [GEN] monitor (artifact inspection), `tests/parity`, all record `--check`s, G-SIG/G-FORB/G-BIND, Maven gh106 tests
- [ ] 7.2 [M1] Ledger assertion, both sides: the five named producer gaps plus `preparedDH` closed (`preparedAlg` after G3; `preparedKeyMaterial` fully after 4.3; `generatedMessageDigest` written by 1.3 and read from 3.6/3.7), and every predicate the set writes read at a consuming site or carrying a recorded impossibility (D-24) — transitory dispositions enumerated, each naming the task that owes its retirement, since G3 is M2 work and 1.R's `unmonitored-consumer` is legitimately still standing here; coverage matrix shows no rule without a terminal state among the landed tiers; run `/rv-verify` on the touched Python surface
- [ ] 7.3 [M2] **Harness checkpoint 2** (final): differential classification attributed per group; battery green; coverage matrix complete — 49/49 terminal states over three values, `oracle_defect_row` filled by join; no transitory disposition survived its reason, in the graph or in the ledger; **NOBS rate of the G1b sites read over the APK corpus, for the researcher's decision on whether any NOBS branch retires** (D-24)
- [ ] 7.4 [M2] Run `/rv-qa-lint-fix scripts/ tests/parity/`
- [ ] 7.5 [M2] Run `/rv-verify` on the same touched surface
- [ ] 7.6 [M2] Run `/rv-code-reviewer` on the change surface
