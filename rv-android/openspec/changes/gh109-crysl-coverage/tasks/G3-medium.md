# G3 — Medium specs (7 files, parallel per spec, after G2's first records pass is green)

**Ordering, beyond G2**: 3.6 and 3.7 also wait on **1.3(b)**, which writes the
`generatedMessageDigest` they read. Landing them first would give the two reads a producer that
never fires — NOT_OBSERVED for every program, the form INV-INS-151 refuses.

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
| 3.6 | DigestInputStream | `Con, Read+, Close` | 3 array-bounds clauses (check reachability like R9 — the JDK may throw first; accuse only reachable branches, record the rest) | `generatedMessageDigest[digest]` — **written by 1.3(b)**, `g1`/`g2`/`g3` of `MessageDigestSpec` | `digestedInputStream[stream, digest]` | 3 + FORBIDDEN `on(boolean)` |
| 3.7 | DigestOutputStream | `Con, Write+, Close` | same family | `generatedMessageDigest[digest]` — same producer, same dependency | `digestedOutputStream[stream, digest]` | 3 + FORBIDDEN `on(boolean)` |

Notes:

- **3.3 and 3.4 are the high-value consumers**: they wire `speccedKey` (produced by
  `PBEKeySpecSpec`/`SecretKeySpecSpec`/2.13) and produce `generatedKey`/`generatedPrivkey`/
  `generatedPubkey` for existing readers (`CipherSpec`, `MacSpec`, `KeyPairSpec`, `SignatureSpec`,
  `TrustAnchorSpec`). Wire in topological order within the group.
- **3.6/3.7 `ere`**: apply the R4 lesson — no event outside the rule's alphabet inside the `+`.
- **3.6/3.7 and the producer that was not there.** `MessageDigest.crysl:46` ensures
  `generatedMessageDigest[this] after Get`, and `MessageDigestSpec.mop` did not write it — an
  omission this change caught only at G0.7, because the D-24 inventory enumerated producer gaps from
  the 27 *absent* rules and this producing rule is present and paired. Landing these two specs is
  what makes the omission visible: the three ledger rows that carry the predicate (#17, #18, #103)
  today read `unmonitored-consumer`/`unmonitored-consumer-side` on the sentence *none of which has a
  `.mop`*, and these two tasks falsify it. Task 1.3(b) supplies the write, so the disposition these
  tasks move lands on wired rather than on `unmonitored-producer`. Both reads get the full three
  branches, NOBS included with its own code, per D-24.
- **FORBIDDEN events** follow the set's existing FORBIDDEN form (`SSLContextSpec.getDefault`
  precedent) with their own codes.
- `generatedCert`, `digestedInputStream`, `digestedOutputStream` have no consumer among the 49 —
  write them anyway (coverage is the goal; the ledger will classify them unread, which is a fact
  about the oracle, not a defect).

## 3.R — Group records pass

Same shape as 2.R: `new-file` rows, graph + ledger re-emit (`preparedAlg` must show closed —
INV-INS-151 fully satisfied from here; and rows #17/#18/#103 must leave `unmonitored-consumer*` for
wired, never for `unmonitored-producer` — if they land there, 1.3(b) did not take, and the fix is in
`MessageDigestSpec.mop`, not here), alphabet mappings, coverage matrix re-derivation (7 rules
flip to `covered`), **[GEN]** monitor + `tests/parity`, one trace pair per shape (one ORDER-bearing
producer 3.2, one consumer chain 3.3, one FORBIDDEN 3.6).

**Two disposition retirements this group owes, and the second is not a list of rows.**

1. **The transitory disposition 1.R wrote must leave.** 1.R closed G-PRED2 over the three
   `MessageDigestSpec` write rows (`g1`/`g2`/`g3`) with `unmonitored-consumer`, a word added to
   `RECORDED_WRITE_DISPOSITIONS` for exactly this interval (D-24). 3.6 and 3.7 are the consumers it
   named. Once they land, the three rows must **lose** the disposition and stand as ordinary wired
   writes; their `reason` keeps the `after Get` half, which is INV-INS-134's and outlives G3. A
   transitory disposition that survives its own reason is a false record — the same rule that retired
   the `CipherOutputStreamSpec` allow-list line once R4 supplied the measurement it was waiting for.
   Task 7.3 asserts that none survived, so leaving one here fails the milestone, not this group.

2. **Every *other* write row of the graph is re-derived too.** G-PRED2 accumulates written and read
   predicate names over the whole set and judges each row against those two sets
   (`gh105_predicate_graph.py:1511-1553`). The moment any specification reads a name, every write row
   of that name stops being a finding — and its `disposition` and its `reason`, often several hundred
   words of measured argument, stop being read by anything. This group lands consumers for predicates
   that were written under `omission` *because no consumer existed*: check each write row of the
   graph, not only the rows these seven tasks created, and amend or move any recorded reason a landed
   consumer falsified. Do not pre-commit to a verdict per row here — the readers do not exist until
   the specs are written, and the point is to measure the graph after they are, not to predict it.
