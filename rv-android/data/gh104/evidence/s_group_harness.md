# Group 2 (S) — differential harness, seed against successor (task 2.14)

**A** `rvsec-mop/src/main/resources/jca` (the frozen seed) · **B** `rvsec-mop/src/main/resources/jca_android`
(the successor after tasks 2.2–2.8) · 57 traces · JDK 21 · both snapshots generated in scratch by
`rv-monitor-generator` and replayed by `TraceRunner`.

| verdict | traces |
|---|---|
| unchanged | 48 |
| removed | 5 |
| introduced | 4 |
| **moved** | **0** |

## Why `moved` is zero, and why that is the result the group needed

`moved` is the verdict that fires when both snapshots accuse a trace at different events — the
signature of an accusation that changed hands rather than appeared or disappeared. It is what the
predicate removal would have produced in quantity, and what design D-11 withdrew the removal to
avoid. With the seed's 134 `ExecutionContext` lines carried over byte-for-byte, no event's guard
moved, so **every difference the harness sees is an allow-list difference** — which is precisely
the prediction task 2.14 made and the condition under which its two admissible classes cover the
whole result set.

## The nine differences, one line each

Every row is either a value the api30 rule admits and the seed rejected (the allow-list widened,
the accusation goes) or a value the seed admitted and the api30 rule does not (the list narrowed,
the accusation appears). No row falls outside those two classes, so nothing stops the group.

### Widenings — `removed`, reason `corrected verdict`

| trace | event(s) the seed accused at | api30 clause that admits the value |
|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | `load`, `gk1` | `KeyStore.cryptsl` `keyStoreAlg in {AndroidKeyStore, …}` — the single row that resolves the tier's 2,005-event `AndroidKeyStore` block |
| `MessageDigestSpec-md5.txt` | `update` | `MessageDigest.cryptsl:63` `digestAlg in {MD5, …}` |
| `MessageDigestSpec-sha1.txt` | `update` | `MessageDigest.cryptsl:63` `digestAlg in {…, SHA-1, …}` |
| `SSLContextSpec-tls.txt` | `unsafe_protocol`, `init` | `SSLContext.cryptsl` `protocol in {…, TLS, …}` — the tier's 8,648-event `TLS` block |
| `TrustManagerFactorySpec-x509.txt` | `g3`, `init` | `TrustManagerFactory.cryptsl` `algo in {PKIX}` reached through the alias rule of task 2.5: Conscrypt registers `X509` as an alias of `PKIX` |

The two `MessageDigestSpec` rows are the expensive half of the single-oracle rule and the cost is
already on record in `conformance_record.csv`: 5,892 of the published corpus's 6,048
`MessageDigestSpec/UnsafeAlgorithm` rows stop being reported. That is the researcher's decision
(design D-10), sized here rather than discovered later.

### Narrowings — `introduced`, reason `corrected verdict (narrowed by …)`

| trace | event the successor accuses at | api30 clause that omits the value |
|---|---|---|
| `KeyPairGeneratorSpec-rsa3072.txt` | `initError` | `KeyPairGenerator.cryptsl:51` `alg in {RSA} => keySize in {4096, 2048}` — no 3072 |
| `KeyStoreSpec-jks.txt` | `load`, `gk1` | `KeyStore.cryptsl` omits `JKS` (it does not exist on Android) |
| `MacSpec-hmacpbesha1.txt` | `i1` | `Mac.cryptsl:71` omits `HmacPBESHA1` |
| `SecureRandomSpec-nativeprng.txt` | `g4` | `SecureRandom.cryptsl` `randAlg in {SHA1PRNG}` only |

All four are on task 2.14's authorised narrowing list and each carries a `MOP-MAIS-PERMISSIVO`
row of `constraint_table.csv` plus a conformance note. The remaining authorised narrowings
(`DiffieHellman`, `SunX509`, `Windows-PRNG`, `PKCS11`, `JCEKS`/`DKS`, bare `RSA`/`RSA/ECB`) have
no trace in the set and are therefore unsized here, not unrecorded.

## Deferred constants: none promoted

Task 2.14's second half promotes a `deferred-constant` row of `conformance_record.csv` to a
transcribed check once the harness has sized the accusations that check would add. No trace of
the 57 exercises a clause the set does not implement, so the harness sized none of the 30 rows
and **all 30 stay deferred** (INV-INS-124). Promoting one on the strength of an unmeasured
clause is the move D-1 and D-6 already refused.

## Per-specification reports

`data/gh104/evidence/harness/s-<Spec>.md`, one per specification, 23 files.
