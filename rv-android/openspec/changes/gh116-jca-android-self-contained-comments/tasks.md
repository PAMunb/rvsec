<!-- Subagent dispatch hints:
     - Group 1 (Preconditions) must complete first. It requires #114 applied and committed.
     - Group 2 (Pilot) runs next and ends at the researcher's approval; Groups 3-10 read the approved pilot.
     - Groups 3-10 share no file and run in parallel, one subagent each (8 dispatches).
     - Group 11 (Consolidation) runs after all of 3-10; Group 12 (Close) runs last.
     - Critical path: 1 -> 2 -> {3..10} -> 11 -> 12.
     - This change touches 47 .mop + codes.csv + 9 Java classes + 1 guide + 1 script + 2 moved files.
     - Every rewrite worker receives: design.md (API Design and Decisions D1, D2, D8), the delta spec
       requirement "Documentation Convention of the `jca_android` Specification Set", the approved
       pilot files, the upstream commit `6d844ab402229aaefa4c5e45bf080987b787624b` with the `@see` URL of D4, and P1-P4.
     - By the researcher's decision no monitor is generated and no gate or test is run (only comments
       change). The schema's lint/verify/code-review tail is replaced by the acceptance reads of
       Group 11.
     - "Review the comments of X" means: keep every comment of X that already complies with the
       convention verbatim, rewrite the ones that do not, and give every event, predicate read and
       predicate write its own detailed comment (design D2a). -->

## 1. Preconditions

- [ ] 1.1 Confirm #114 is applied and committed; stop otherwise
- [ ] 1.2 Re-measure the set: `.mop` count, lines, comment lines, and the reference counts of design.md Context; record the numbers in this task's note
- [ ] 1.3 Check the citation of D4: the sha256 of `CROSSINGTUD/Crypto-API-Rules` `JavaCryptographicArchitecture/src/*.crysl` at commit `6d844ab402229aaefa4c5e45bf080987b787624b` matches `data/jca_android/oracle/expert_rules.sha256` in 48 of 49 rules, and `Cipher.crysl` differs only by `CCM` in the AES mode and AES `NoPadding` clauses; stop on any other difference

## 2. Pilot (sequential — researcher approval)

- [ ] 2.1 Review the comments of `jca_android/MGF1ParameterSpecSpec.mop` under the convention
- [ ] 2.2 Review the comments of `jca_android/CipherSpec.mop` under the convention
- [ ] 2.3 Present both diffs to the researcher and apply the corrections; resolve the Open Question of design.md (naming another specification of the set)

## 3. Cipher chain (parallel — subagent)

- [ ] 3.1 Review the comments of `IvChainJunction.mop` (name kept; header says why the file exists beside `CipherSpec`)
- [ ] 3.2 Review the comments of `CipherInputStreamSpec.mop` and `CipherOutputStreamSpec.mop`
- [ ] 3.3 Review the comments of `GCMParameterSpecSpec.mop` and `IvParameterSpec.mop`
- [ ] 3.4 Review the comments of `OAEPParameterSpecSpec.mop`

## 4. Mac and digest (parallel — subagent)

- [ ] 4.1 Review the comments of `MacSpec.mop`
- [ ] 4.2 Review the comments of `MessageDigestSpec.mop`, `DigestInputStreamSpec.mop` and `DigestOutputStreamSpec.mop`
- [ ] 4.3 Review the comments of `HMACParameterSpecSpec.mop`

## 5. Key generation, agreement, signature and randomness (parallel — subagent)

- [ ] 5.1 Review the comments of `KeyGeneratorSpec.mop` and `SecureRandomSpec.mop`
- [ ] 5.2 Review the comments of `KeyPairGeneratorSpec.mop` and `KeyPairSpec.mop`
- [ ] 5.3 Review the comments of `AlgorithmParameterGeneratorSpec.mop` and `AlgorithmParametersSpec.mop`
- [ ] 5.4 Review the comments of `KeyAgreementSpec.mop` and `SignatureSpec.mop`

## 6. Key material (parallel — subagent)

- [ ] 6.1 Review the comments of `SecretKeySpec.mop`, `SecretKeySpecSpec.mop` and `KeySpec.mop`
- [ ] 6.2 Review the comments of `PBEKeySpecSpec.mop` and `PBEParameterSpecSpec.mop`
- [ ] 6.3 Review the comments of `SecretKeyFactorySpec.mop`, `KeyFactorySpec.mop` and `X509EncodedKeySpecSpec.mop`

## 7. Algorithm parameter specifications (parallel — subagent)

- [ ] 7.1 Review the comments of `DHGenParameterSpecSpec.mop` and `DHParameterSpecSpec.mop`
- [ ] 7.2 Review the comments of `DSAParameterSpecSpec.mop`, `ECGenParameterSpecSpec.mop` and `ECParameterSpecSpec.mop`
- [ ] 7.3 Review the comments of `RSAKeyGenParameterSpecSpec.mop`

## 8. TLS, trust and key stores (parallel — subagent)

- [ ] 8.1 Review the comments of `SSLContextSpec.mop`, `SSLEngineSpec.mop` and `SSLParametersSpec.mop`
- [ ] 8.2 Review the comments of `TrustManagerFactorySpec.mop` and `KeyManagerFactorySpec.mop`
- [ ] 8.3 Review the comments of `KeyStoreSpec.mop` and `KeyStoreBuilderParametersSpec.mop`
- [ ] 8.4 Review the comments of `PKIXParametersSpec.mop`, `PKIXBuilderParametersSpec.mop`, `CertPathTrustManagerParametersSpec.mop`, `CertificateFactorySpec.mop` and `TrustAnchorSpec.mop`

## 9. Java helper classes (parallel — subagent)

- [ ] 9.1 Review the comments of `rvsec-core/src/main/java/br/unb/cic/mop/Property.java`, `PredicateStore.java` and `PredicateVerdict.java`
- [ ] 9.2 Review the comments of `jca/util/ConscryptAliasTable.java` and `jca/util/CipherTransformationNormalizer.java` (the normaliser stops naming `Api30CipherTransformationUtil`)
- [ ] 9.3 Review the comments of `eh/ErrorType.java`, `eh/ErrorDescription.java`, `eh/ErrorSummary.java` and `eh/Evidence.java`
- [ ] 9.4 Confirm `jca/util/CipherTransformationUtil.java` is not in the diff

## 10. Authoring guide and backup (parallel — subagent)

- [ ] 10.1 Rewrite `rv-android/data/jca_android/NEW_SPEC_CONVENTIONS.md`: add the comment convention; remove its own citations of invariants, decisions, tasks and `.mop` line numbers while keeping every authoring rule it states
- [ ] 10.2 Move `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/Api30CipherTransformationUtil.java` and `rvsec-core/src/test/java/br/unb/cic/mop/jca/util/Api30CipherTransformationUtilTest.java` to `backup/gh116/`, preserving their relative paths
- [ ] 10.3 Delete the two `EXEMPT_CORE` entries naming the moved files in `rv-android/scripts/gh105_sole_oracle_gate.py`, with the comment block above them that describes the class

## 11. Consolidation and acceptance reads

- [ ] 11.1 Read each producer/consumer pair across groups (e.g. `SecureRandomSpec` → `IvParameterSpec`, `MGF1ParameterSpecSpec` → `OAEPParameterSpecSpec`, `KeyGeneratorSpec`/`SecretKeySpecSpec`/`KeyStoreSpec` → `CipherSpec`, `TrustManagerFactorySpec` → `SSLContextSpec`) and align how the predicate is described
- [ ] 11.2 Update the `file_line` column of `jca_android/codes.csv` per D9
- [ ] 11.3 For every rewritten `.mop` and Java file, compare the token sequence with comments stripped against `HEAD`; restore any non-comment difference
- [ ] 11.4 Read the comments of every rewritten file for the patterns INV-INS-168 forbids (line numbers, `INV-`, `D-`, task, `gh`/`#` identifiers, dates, names of `data/jca_android/` records, counts, `jca` set, earlier-state narrative, promotional language); confirm every event, read and write has its own comment; fix what remains
- [ ] 11.5 Confirm every `.mop` header `@see` names `Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b`, and that only `CipherSpec.mop` states a difference from its cited rule (`CCM` for AES)
- [ ] 11.6 `git grep Api30CipherTransformationUtil` returns nothing outside `backup/`, `openspec/changes/archive/`, dated documents under `docs/` and `audit/`, and data records

## 12. Close

- [ ] 12.1 Run `/opsx:verify` for `gh116-jca-android-self-contained-comments`
- [ ] 12.2 Check off the acceptance criteria of issue #116
- [ ] 12.3 Commit by path (`git add -A -- <paths>` then `git commit --only -- <paths>`) with `closes #116`
- [ ] 12.4 Run `/opsx:archive`
