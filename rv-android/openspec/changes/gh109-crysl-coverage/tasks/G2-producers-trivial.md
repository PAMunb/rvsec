# G2 — Trivial producer specs (14 files, parallel per spec, after G0)

Every task: one new `.mop` in `SET/`, written from its expert rule alone, following the G0.2
conventions (accuser per value clause, predicate write on the conforming branch, canonical values,
codes rows appended by the task itself, `unzip -l` viability re-check). All classes were confirmed
present in the api30 jar this session; ORDER is `Con` for all but 2.14 (`GetEnc*`); constructor overloads are fused. Records
land once, in 2.R. Closing this group closes five of the six producer gaps (design D-19).

Fiches (from the verified viability census — re-confirm the CONSTRAINTS text against the rule before
writing; the rule is the source, this table is the map):

| Task | Rule | Constraints to transcribe | REQUIRES (read) | ENSURES (write) |
|---|---|---|---|---|
| 2.1 | RSAKeyGenParameterSpec | keysize ∈ {1024, 2048, 4096}; publicExponent ∈ {65537} | — | `preparedRSA[this]` |
| 2.2 | ECGenParameterSpec | stdName ∈ the rule's 23-curve list (transcribe literally) | — | `preparedEC[this]` |
| 2.3 | ECParameterSpec | none | — | `preparedEC[this]` |
| 2.4 | DSAParameterSpec | bit-length ≥ 2048 for `p`, `g` (D-20.4 semantics; divergence row from 0.1) | — | `preparedDSA[this]` |
| 2.5 | DHParameterSpec | bit-length ≥ 2048 (same) | — | `preparedDH[this]` |
| 2.6 | MGF1ParameterSpec | mdName ∈ {SHA-256, SHA-384, SHA-512} | — | `preparedMGF1[this, mdName]` |
| 2.7 | OAEPParameterSpec | mdName ∈ {SHA-256, SHA-384, SHA-512}; mgfName ∈ {MGF1} | `preparedMGF1[mgfSpec, mdName]` | `preparedOAEP[this]` |
| 2.8 | KeyStoreBuilderParameters | none | — | `generatedManagerFactoryParameters[this]` |
| 2.9 | CertPathTrustManagerParameters | none | `generatedCertPathParameters[params]` | `generatedManagerFactoryParameters[this]` |
| 2.10 | PKIXParameters | none | `generatedKeyStore[keyStore]` | `generatedCertPathParameters[this]` |
| 2.11 | PKIXBuilderParameters | none | `generatedKeyStore[keystore]` (`generatedTrustAnchor` is commented out in the rule — do not wire it) | `generatedCertPathParameters[this]` |
| 2.12 | TrustAnchor | none | `generatedPubkey[publicKey]` | `generatedTrustAnchor[this]` |
| 2.13 | X509EncodedKeySpec | none | `preparedKeyMaterial[encodedKey]` | `speccedKey[this, _]` |
| 2.14 | Key (file `KeySpec.mop`, add to `NON_PAIRING_FILES` mapping note if the stem clashes) | none; ORDER `GetEnc*` | — | `preparedKeyMaterial[keyMaterial]` after GetEnc |

Notes that survive from verification:

- **2.7 depends on 2.6** (its REQUIRES reads what 2.6 writes) — land 2.6 first or same batch; the
  oracle-side `preparedOAEP` consumer clause is vacuous (D-21), which lowers this pair's urgency but
  not its coverage obligation.
- **2.14** is the set's second interface-owned pointcut: `Key+.getEncoded()` — the R5 lesson applies;
  it must not shadow `SecretKeySpec.mop`'s own `getEncoded` bridge (one call, one transition per
  spec: check the two pointcuts stay disjoint by owner or document the deliberate double-monitor).
- **REQUIRES reads** follow the gh105 substrate: read in the event body with its accuser and a
  `codes.csv` code. Producers, verified: 2.9 reads what 2.10/2.11 write (`generatedCertPathParameters`);
  2.10 and 2.11 read `generatedKeyStore`, written by the existing `KeyStoreSpec.mop:189`; 2.12 reads
  `generatedPubkey`, written by the existing `KeyPairSpec.mop:126` (and later also by 3.4); 2.13 reads
  `preparedKeyMaterial`, written by 2.14 and already by `SecretKeySpec.mop:128`.
- Predicate parameters: `[this, value]` shapes map to `ensure(Property.X, obj, value)`; transcribe
  arity faithfully.

## 2.R — Group records pass

1. One `new-file` divergence row per spec (kind per the recorder's vocabulary; precedent
   `IvChainJunction`).
2. `gh105_predicate_graph.py --emit` + `gh105_expert_ledger.py` re-emit + `--check`: the ledger MUST
   show `preparedRSA`, `preparedEC`, `preparedDSA`, `preparedOAEP`, `generatedManagerFactoryParameters`
   and `preparedDH` moved off `unmonitored-producer` (INV-INS-151); `preparedAlg` remains open until
   G3, and `preparedKeyMaterial` (written by 2.14) closes fully with 4.3.
3. Alphabet mappings for the new specs (with 6.2) or declared skips — G-ORDER must not silently skip.
4. Coverage matrix re-derivation (0.4): 14 rules flip to `covered`.
5. **[GEN]** monitor regeneration (artifact inspection) + `tests/parity` + the 6.1 enumeration
   constants (same commit as the first spec of this group, per the dispatch rule).
6. One satisfy/violate trace pair per *shape*, not per file: one for a value-constrained producer
   (2.1), one for a REQUIRES-reading producer (2.10), one for the interface rule (2.14).
