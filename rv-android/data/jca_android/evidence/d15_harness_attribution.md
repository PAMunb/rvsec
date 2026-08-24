# D-15 differential harness — every delta attributed

**Task 11.9** · 2026-08-24 · A = the pre-D-15 snapshot of `jca_android`, B = the re-anchored set
· 159 traces (131 inherited + 28 written for this group) · report files
`data/gh104/evidence/harness/d15-*.md`

`unchanged 132 · moved 9 · removed 12 · introduced 6`. Every non-`unchanged` row is accounted
for below; an unattributed delta would be a defect, not a result.

## introduced (6) — an accusation the re-anchoring restores

`d15-MessageDigestSpec-{md5,sha1,sha1-alias}` and the three inherited
`MessageDigestSpec-{md5,md5-only,sha1}`. Side A is silent, side B accuses. This is the
5,892-row family of the published corpus coming back, and `sha1-alias` shows it coming back
*through* the alias table: the observed `SHA1` resolves to `SHA-1`, which the expert list
rejects. Task 11.2 (`MessageDigestSpec`), acceptance measured in `d15_c5_replay.md`.

## moved (9) — the accusation stays, its site changes

- `d15-CipherSpec-{aes-ecb-pkcs5,aes-ecb-nopadding,desede-cbc,blowfish-ecb,chacha20}`: side A
  accuses `i2`+`f2` (both `CIPHER-ORDER-00`, the automaton's sink), side B accuses `i1`+`i2`+`f2`
  — **`i1` is new, and `i1` is the value site**. Under the api30 tables these transformations
  were *admitted*, so `g1` fired and only the ordering complained; under the expert tables
  `getInstance` takes the `g3` branch and the value is accused where it should be. This is the
  ECB detection returning (task 11.3), and it is why the case needed a trace: the corpus's 109
  `CipherSpec` accusations are all the OAEP spelling, so no published number shows it.
- `IvChainJunctionSpec-rangen`, `IvChainJunctionSpec-rangen-unobserved`,
  `MacSpec-mac-then-encrypt`, `MacSpec-update-then-encrypt`: downstream of the same Cipher
  change — a transformation the tables now reject reaches these chains in a different state.

## removed (12) — a narrowing undone, or its consequence

- `d15-KeyPairGeneratorSpec-rsa-3072`, `d15-KeyPairGeneratorSpec-diffiehellman`,
  `KeyPairGeneratorSpec-rsa3072`: RSA `3072` and `DiffieHellman` are expert entries; D-10 had
  dropped both. Task 11.2.
- `d15-KeyStoreSpec-jks`, `KeyStoreSpec-jks`: `JKS` is an expert type, inert on Android but not
  removable. Task 11.2.
- `d15-SecureRandomSpec-{nativeprng,windowsprng}`, `SecureRandomSpec-nativeprng`,
  `SecureRandomSpec-genseed-rejected-algorithm`: the api30 refinement had cut the list to
  `SHA1PRNG` alone; all six expert entries are back. Task 11.2.
- `MacSpec-hmacpbesha1`, `MacSpec-unsafe-generated-key`, `KeyGeneratorSpec-rangen-unobserved`:
  `HmacPBESHA1` is an expert entry the api30 list had dropped; the other two are its
  downstream chains.

Every one of these classes `removed` against the **pre-D-15 snapshot** because that snapshot
accused them. Against the **frozen `jca`** the same traces are `unchanged`, which is the
statement the design makes: the narrowings were undone, not merely described.

## A limit of these traces, stated rather than left implicit

Eight traces class `unchanged` while carrying a value the re-anchoring *does* reject —
`d15-SSLContextSpec-{ssl,tlsv1}`, `d15-SignatureSpec-{md5withrsa,nonewithrsa,sha1withdsa}`,
`d15-KeyGeneratorSpec-{arc4,desede}`, `d15-MacSpec-hmacpbesha1`. Reading their envelopes shows
why: side B emits `SSLCONTEXT-NOBS-01`, `SIGNATURE-NOBS-00`, `KEYGENERATOR-ORDER-00`,
`MAC-ORDER-00` — a predicate or ordering site fires *before* the value site is reached, so the
trace is accused either way and the harness sees no change. The traces are too short to reach
the `*-ALG-*` site.

This is a limitation of the trace shapes, not of the specifications: the C5 replay
(`d15_c5_replay.md`) checks those same values against the lists directly and each is rejected.
`d15-KeyGeneratorSpec-hmacmd5` is the counter-example that proves the site works — it does emit
`KEYGENERATOR-ALG-00`. **Open work:** lengthen the eight traces so the value site is reached,
so that the harness and not only the replay witnesses them.
