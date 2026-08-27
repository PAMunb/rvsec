# G3 — Medium specs (7 files, parallel per spec, after G2's first records pass is green)

Same conventions as G2 (G0.2 template, own codes rows, `unzip -l` viability re-check, records in
3.R). These rules have short non-trivial ORDERs — each fiche below carries the ORDER to realize.
Landing 3.1/3.2 closes the sixth producer gap (`preparedAlg`).

| Task | Rule | ORDER | Constraints | REQUIRES (read) | ENSURES (write) | Events |
|---|---|---|---|---|---|---|
| 3.1 | AlgorithmParameters | `Get, Init, GetEncoded?` | algorithm ∈ the rule's 12-value list | `preparedAlg[params, algorithm]` + 4 conditional implications (`preparedIV`/`preparedDH`/`preparedPBE`/`preparedOAEP` by algorithm family — guard in body before the read, per the gh105 guarded-clause form) | `preparedAlg[this, algorithm]` after Init; `preparedAlg[encParams, algorithm]` after GetEncoded | 3 |
| 3.2 | AlgorithmParameterGenerator | `Get, Init, GenParam` | algorithm ∈ {DH, DiffieHellman, DSA}; size ∈ {2048, 3072} | `randomized[random]` | `preparedAlg[algParams, algorithm]` after GenParam | 3 |
| 3.3 | SecretKeyFactory | `Get, Gen` | algorithm ∈ the rule's PBKDF2/PBE list (note: the rule lists `PBEWithHmacSHA384AndAES_128` twice — transcribe the set, note the duplicate in the task record) | `speccedKey[keySpec, _]` | `generatedKey[key, algorithm]` — canonical value (D-20.3) | 2 |
| 3.4 | KeyFactory | `Get, (GenPriv \| GenPubl)*` | algorithm ∈ {RSA, DiffieHellman, DH, DSA, EC} | `speccedKey[keySpec, _]` | `generatedKeyFactory[this, algorithm]` after Get; `generatedPrivkey`/`generatedPubkey` after Gen* | 3 |
| 3.5 | CertificateFactory | `Get, (GenCert \| GenCertPath \| GenCRL)+` | type ∈ {X509, X.509}; encoding ∈ {PKCS7, PkiPath} | — | `generatedCert[type]` | 4 |
| 3.6 | DigestInputStream | `Con, Read+, Close` | 3 array-bounds clauses (check reachability like R9 — the JDK may throw first; accuse only reachable branches, record the rest) | `generatedMessageDigest[digest]` | `digestedInputStream[stream, digest]` | 3 + FORBIDDEN `on(boolean)` |
| 3.7 | DigestOutputStream | `Con, Write+, Close` | same family | `generatedMessageDigest[digest]` | `digestedOutputStream[stream, digest]` | 3 + FORBIDDEN `on(boolean)` |

Notes:

- **3.3 and 3.4 are the high-value consumers**: they wire `speccedKey` (produced by
  `PBEKeySpecSpec`/`SecretKeySpecSpec`/2.13) and produce `generatedKey`/`generatedPrivkey`/
  `generatedPubkey` for existing readers (`CipherSpec`, `MacSpec`, `KeyPairSpec`, `SignatureSpec`,
  `TrustAnchorSpec`). Wire in topological order within the group.
- **3.6/3.7 `ere`**: apply the R4 lesson — no event outside the rule's alphabet inside the `+`.
- **FORBIDDEN events** follow the set's existing FORBIDDEN form (`SSLContextSpec.getDefault`
  precedent) with their own codes.
- `generatedCert`, `digestedInputStream`, `digestedOutputStream` have no consumer among the 49 —
  write them anyway (coverage is the goal; the ledger will classify them unread, which is a fact
  about the oracle, not a defect).

## 3.R — Group records pass

Same shape as 2.R: `new-file` rows, graph + ledger re-emit (`preparedAlg` must show closed —
INV-INS-151 fully satisfied from here), alphabet mappings, coverage matrix re-derivation (7 rules
flip to `covered`), **[GEN]** monitor + `tests/parity`, one trace pair per shape (one ORDER-bearing
producer 3.2, one consumer chain 3.3, one FORBIDDEN 3.6).
