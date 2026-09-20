<!-- Subagent dispatch hints (design D6). No step waits for a person.
     - WAVE 1 — groups 1-5 have no dependencies among them: dispatch 5 agents at once.
     - WAVE 2 — groups 6-14 share no file and depend only on group 5 (glossary): dispatch 9 agents as soon as
       group 5 ends, while the rest of wave 1 may still be running.
     - WAVE 3 — groups 15-18 review disjoint file sets and depend on all of wave 2 (and, for group 18, on
       groups 2-4): dispatch 4 reviewer agents at once. A reviewer is never the agent that wrote the files.
     - Group 19 runs in the main window after wave 3; group 20 closes.
     - Critical path: 5 -> slowest of 6-14 -> slowest of 15-18 -> 19 -> 20.
     - This change touches 47 .mop + codes.csv + 9 Java classes + 1 guide + 1 CLAUDE.md section + 1 script + 2 moved files.
     - Every .mop worker and reviewer receives: design.md (API Design, D1, D2, D2a, D2b, D4, D5, D8), the delta
       spec requirement "Documentation Convention of the `jca_android` Specification Set", the predicate
       glossary, the `@see` URL of D4, the difference list of group 1, and P1-P4 as amended by D2a.
     - Every Java worker and reviewer receives the eleven Java rules of the delta spec.
     - "Review the comments of X" means: keep every comment of X that already complies with the convention
       verbatim, rewrite the ones that do not, and give every event, predicate read and predicate write its own
       detailed comment (D2a). In Java, self-evident members get no Javadoc (D2c). A divergence whose technical
       cause is not known is stated as behaviour only.
     - "Self-check" means, for each file touched: (a) the token sequence with comments stripped equals the one
       at `HEAD`; (b) no comment contains a pattern INV-INS-168 forbids (line numbers, `INV-`, `D-`, task,
       `gh`/`#` identifiers, dates, names of `data/jca_android/` records, counts, the `jca` set, earlier-state
       narrative, promotional language); (c) for a `.mop`, the header `@see` is the URL of D4.
     - By the researcher's decision no monitor is generated and no gate or test is run (only comments change).
       The schema's lint/verify/code-review tail is replaced by the self-checks and the wave-3 reviewers. -->

## 1. Wave 1 — Citation check (parallel — subagent)

- [x] 1.1 Hash `JavaCryptographicArchitecture/src/*.crysl` of `CROSSINGTUD/Crypto-API-Rules` at commit `6d844ab402229aaefa4c5e45bf080987b787624b` and compare with `data/jca_android/oracle/expert_rules.sha256`: expect 48 of 49 identical and `Cipher.crysl` differing only by `CCM` in the AES mode and AES `NoPadding` clauses
- [x] 1.2 Write the difference list (rule, clause, expert text, upstream text) handed to wave 2; any difference beyond `CCM` is stated as behaviour in the header of the affected specification

## 2. Wave 1 — Java documentation convention (parallel — subagent)

- [x] 2.1 Write the "Documentation conventions" section of `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` with the eleven Java rules of the delta spec (design D2c), derived from the module's current Javadoc practice and the `rv-doc-code` mapping; change no existing comment of the module

## 3. Wave 1 — Java helper classes (parallel — subagent)

- [x] 3.1 Review the comments of `rvsec-core/src/main/java/br/unb/cic/mop/Property.java`, `PredicateStore.java` and `PredicateVerdict.java` against the Java rules; self-check
- [x] 3.2 Review the comments of `jca/util/ConscryptAliasTable.java` and `jca/util/CipherTransformationNormalizer.java` (the normaliser stops naming `Api30CipherTransformationUtil`); self-check
- [x] 3.3 Review the comments of `eh/ErrorType.java`, `eh/ErrorDescription.java`, `eh/ErrorSummary.java` and `eh/Evidence.java`; self-check
- [x] 3.4 Confirm `jca/util/CipherTransformationUtil.java` is not in the diff

## 4. Wave 1 — Backup and authoring guide (parallel — subagent)

- [x] 4.1 Move `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/Api30CipherTransformationUtil.java` and `rvsec-core/src/test/java/br/unb/cic/mop/jca/util/Api30CipherTransformationUtilTest.java` to `backup/gh116/`, preserving their relative paths
- [x] 4.2 Delete the two `EXEMPT_CORE` entries naming the moved files in `rv-android/scripts/gh105_sole_oracle_gate.py`, with the comment block above them that describes the class
- [x] 4.3 Rewrite `rv-android/data/jca_android/NEW_SPEC_CONVENTIONS.md`: add the comment convention; remove its own citations of invariants, decisions, tasks and `.mop` line numbers while keeping every authoring rule it states
- [x] 4.4 `git grep Api30CipherTransformationUtil` returns nothing outside `backup/`, `openspec/changes/archive/`, dated documents under `docs/` and `audit/`, and data records

## 5. Wave 1 — Predicate glossary (parallel — subagent; wave 2 starts when it ends)

- [x] 5.1 List every `Property` constant the 47 `.mop` files write or read
- [x] 5.2 Write one standard sentence per predicate stating what it asserts about its object and which rule clause produces it (design D5), as a working file handed to waves 2 and 3 and not committed

## 6. Wave 2 — MGF1 and Cipher (parallel — subagent, ~730 lines)

- [x] 6.1 Review the comments of `MGF1ParameterSpecSpec.mop`
- [x] 6.2 Review the comments of `CipherSpec.mop` (header states the `CCM` difference, D4)
- [x] 6.3 Self-check the two files

## 7. Wave 2 — Cipher chain (parallel — subagent, ~1,100 lines)

- [x] 7.1 Review the comments of `IvChainJunction.mop` (name kept; header says why the file exists beside `CipherSpec`)
- [x] 7.2 Review the comments of `CipherInputStreamSpec.mop` and `CipherOutputStreamSpec.mop`
- [x] 7.3 Review the comments of `GCMParameterSpecSpec.mop`, `IvParameterSpec.mop` and `OAEPParameterSpecSpec.mop`
- [x] 7.4 Self-check the six files

## 8. Wave 2 — Mac and digest (parallel — subagent, ~1,300 lines)

- [x] 8.1 Review the comments of `MacSpec.mop` and `HMACParameterSpecSpec.mop`
- [x] 8.2 Review the comments of `MessageDigestSpec.mop`, `DigestInputStreamSpec.mop` and `DigestOutputStreamSpec.mop`
- [x] 8.3 Self-check the five files

## 9. Wave 2 — Key generation and randomness (parallel — subagent, ~1,230 lines)

- [x] 9.1 Review the comments of `KeyGeneratorSpec.mop` and `SecureRandomSpec.mop`
- [x] 9.2 Review the comments of `KeyPairGeneratorSpec.mop` and `KeyPairSpec.mop`
- [x] 9.3 Self-check the four files

## 10. Wave 2 — Algorithm parameters, agreement and signature (parallel — subagent, ~1,130 lines)

- [x] 10.1 Review the comments of `AlgorithmParameterGeneratorSpec.mop` and `AlgorithmParametersSpec.mop`
- [x] 10.2 Review the comments of `KeyAgreementSpec.mop` and `SignatureSpec.mop`
- [x] 10.3 Self-check the four files

## 11. Wave 2 — Key material (parallel — subagent, ~1,500 lines)

- [x] 11.1 Review the comments of `SecretKeySpec.mop`, `SecretKeySpecSpec.mop` and `KeySpec.mop`
- [x] 11.2 Review the comments of `PBEKeySpecSpec.mop` and `PBEParameterSpecSpec.mop`
- [x] 11.3 Review the comments of `SecretKeyFactorySpec.mop`, `KeyFactorySpec.mop` and `X509EncodedKeySpecSpec.mop`
- [x] 11.4 Self-check the eight files

## 12. Wave 2 — Algorithm parameter specifications (parallel — subagent, ~630 lines)

- [x] 12.1 Review the comments of `DHGenParameterSpecSpec.mop`, `DHParameterSpecSpec.mop` and `DSAParameterSpecSpec.mop`
- [x] 12.2 Review the comments of `ECGenParameterSpecSpec.mop`, `ECParameterSpecSpec.mop` and `RSAKeyGenParameterSpecSpec.mop`
- [x] 12.3 Self-check the six files

## 13. Wave 2 — TLS contexts and certificates (parallel — subagent, ~1,090 lines)

- [x] 13.1 Review the comments of `SSLContextSpec.mop`, `SSLEngineSpec.mop` and `SSLParametersSpec.mop`
- [x] 13.2 Review the comments of `CertificateFactorySpec.mop` and `TrustAnchorSpec.mop`
- [x] 13.3 Self-check the five files

## 14. Wave 2 — Trust, key managers and key stores (parallel — subagent, ~1,070 lines)

- [x] 14.1 Review the comments of `TrustManagerFactorySpec.mop` and `KeyManagerFactorySpec.mop`
- [x] 14.2 Review the comments of `KeyStoreSpec.mop` and `KeyStoreBuilderParametersSpec.mop`
- [x] 14.3 Review the comments of `PKIXParametersSpec.mop`, `PKIXBuilderParametersSpec.mop` and `CertPathTrustManagerParametersSpec.mop`
- [x] 14.4 Self-check the seven files

## 15. Wave 3 — Review of groups 6, 7 and 8 (parallel — reviewer subagent, ~3,100 lines)

- [x] 15.1 Read every file of groups 6, 7 and 8 against the requirement and the glossary: clause quoted by text and matching the rule, mechanism explained, every event/read/write commented, divergences stated as behaviour, predicate descriptions matching the glossary; fix what departs
- [x] 15.2 Self-check every file changed in 15.1

## 16. Wave 3 — Review of groups 9, 10 and 12 (parallel — reviewer subagent, ~3,000 lines)

- [x] 16.1 Read every file of groups 9, 10 and 12 against the requirement and the glossary, as in 15.1; fix what departs
- [x] 16.2 Self-check every file changed in 16.1

## 17. Wave 3 — Review of groups 11 and 13 (parallel — reviewer subagent, ~2,600 lines)

- [x] 17.1 Read every file of groups 11 and 13 against the requirement and the glossary, as in 15.1; fix what departs
- [x] 17.2 Self-check every file changed in 17.1

## 18. Wave 3 — Review of group 14, the Java helpers and the guides (parallel — reviewer subagent, ~3,000 lines)

- [x] 18.1 Read every file of group 14 against the requirement and the glossary, as in 15.1; fix what departs
- [x] 18.2 Read the nine Java classes of group 3 against the eleven Java rules (no Javadoc on self-evident members, imperative method summaries, `@throws` with conditions, existing `{@link}` targets); fix what departs
- [x] 18.3 Read the dexlib2 "Documentation conventions" section and `NEW_SPEC_CONVENTIONS.md` against the requirement; fix what departs
- [x] 18.4 Self-check every file changed in 18.1–18.3

## 19. Anchors and headers (main window)

- [x] 19.1 Update the `file_line` column of `jca_android/codes.csv` per D9 over all 47 `.mop` files, and confirm every row names a line containing `code=<CODE> `
- [x] 19.2 Confirm every `.mop` header `@see` names `Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b`, and that only the headers named in the difference list of group 1 (`CipherSpec.mop` for `CCM`) state a difference from their cited rule

## 20. Commit and close (main window)

- [ ] 20.1 Commit by path (`git add -A -- <paths>` then `git commit --only -- <paths>`) with `closes #116`
- [ ] 20.2 Run `/opsx:verify` for `gh116-jca-android-self-contained-comments`
- [ ] 20.3 Check off the acceptance criteria of issue #116
- [ ] 20.4 Run `/opsx:archive`
