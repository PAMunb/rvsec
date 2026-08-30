# G2 — Trivial producer specs (14 files, parallel per spec, after G0)

Every task: one new `.mop` in `SET/`, written from its expert rule alone, following the G0.2
conventions (accuser per value clause, predicate write on the conforming branch, canonical values,
codes rows appended by the task itself, `unzip -l` viability re-check). All classes and members were
confirmed in the API 30 `android.jar` this session; ORDER is `Con` for all but 2.14 (`GetEnc*`). Overloads
are **not** collapsed: a rule that labels them separately (`c1: …; c2: …; Con := c1 | c2`) gets one
event per label, which is what `GCMParameterSpecSpec`, `PBEParameterSpecSpec` and
`SecretKeySpecSpec` already do — "fusion" in this set names `IvParameterSpec`'s guard-twin fusion,
not the collapsing of constructors. The group is **18 events over 14 files**: two each for 2.5, 2.10
and 2.11, three for 2.12, one for the rest. Records land once, in 2.R. Closing this group closes
five of the six producer gaps (design D-19).

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
| 2.14 | Key (file `KeySpec.mop`; it pairs by the ordinary `<Rule>Spec.mop` convention and must **not** enter `NON_PAIRING_FILES` — a new file needing that exemption is a new file whose name is wrong) | none; ORDER `GetEnc*` | — | `preparedKeyMaterial[keyMaterial]` after GetEnc |

Notes that survive from verification:

- **2.7 depends on 2.6** (its REQUIRES reads what 2.6 writes) — land 2.6 first or same batch; the
  oracle-side `preparedOAEP` consumer clause is vacuous (D-21), which lowers this pair's urgency but
  not its coverage obligation.
- **2.14** is the set's second interface-owned pointcut, `Key+.getEncoded()`, and the shadowing
  question this fiche was written to raise has been measured and answered (researcher decision,
  2026-08-27). The two pointcuts are **not** disjoint and cannot be made so without narrowing the
  rule's own type: the API 30 `android.jar` has `SecretKeySpec implements SecretKey` and `SecretKey extends Key`, and
  the owner matcher keeps the `+` and walks interfaces (the R5 measurement,
  `PointcutMatcher:322-345`), so `Key+` subsumes every receiver `SecretKey+` reaches. The double
  monitoring is deliberate and free at the store — `ensure` is idempotent per (property, identity,
  values), so the second write of the same tuple adds nothing. What is not free is the *guard*.
  `SecretKeySpec.mop` stages only when the key's own origin was observed, and that is what refuses
  to launder key material through a copy (decision of 2026-08-22, measured by
  `SecretKeySpec-laundered-material.txt`); `Key.crysl` states no REQUIRES at all. Transcribed to the
  letter, 2.14 would prepare that material unconditionally through the Key monitor and cancel the
  refusal without a line of either specification changing. So the guard is mirrored here and
  generalised to `Key`'s shape — `generatedKey[k, k.getAlgorithm()]` **or** `generatedPubkey[k]`
  **or** `generatedPrivkey[k]` — as a MOP-MAIS-RESTRITIVO divergence row, the twin of the one
  `SecretKeySpec.mop` already carries against `SecretKey.crysl`. Two specifications watching one
  call have to agree about what it means, or the looser of them decides. Like its twin, the read
  governs a write and not a report: no accuser, no `codes.csv` row, and no `@fail` (the ORDER
  `GetEnc*` refuses no sequence).
- **2.8** carries a viability finding the census did not reach. The API 30 `android.jar` declares a second constructor
  the rule does not, `KeyStoreBuilderParameters(List<KeyStore.Builder>)`, and the pointcut cannot
  separate the two: `KeyStore.Builder` is a nested type, and the DEX matcher's
  `TypeResolver.toDescriptor` builds a descriptor by replacing every dot with a slash, so the nested
  name yields `Ljava/security/KeyStore/Builder;` where the platform's is
  `Ljava/security/KeyStore$Builder;` — a pointcut that matches nothing at all, the R5 failure mode
  again. The event is written over `Object+` (the `KeyStoreSpec.mop:90` form, which also keeps the
  trace harness's resolver walking declared types) and the rule's declared type is restored in the
  body with an `instanceof`, where it is ordinary Java and the nested name resolves. A construction
  through the List overload is not the rule's `c1`: it prepares nothing and accuses nothing, and
  what that costs downstream is a NOT_OBSERVED at 1b.2/1b.3 rather than a violation — the honest
  answer, and what the NOBS family exists for.
- **Report families**, stated here because the table above lists clauses and not families: 2.1's
  `keysize` is `KEYSIZE`/`InvalidKeySize` (the `KeyPairGeneratorSpec` precedent) and its
  `publicExponent` is `CONSTR`/`UnsatisfiedConstraint`; 2.4 and 2.5 report **both** bit-length
  clauses under `CONSTR`, because only one of the two quantities is a key size and the rule states
  the same thing about both — splitting the pair across two families would say the rule said two
  kinds of thing where it said one thing twice; 2.2, 2.6 and 2.7's name clauses are
  `ALG`/`UnsafeAlgorithm`; every predicate read is a `CONSTR` site plus a `NOBS` site.
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
