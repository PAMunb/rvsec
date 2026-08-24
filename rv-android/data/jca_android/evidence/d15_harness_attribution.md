# D-15 differential harness — every delta attributed

**Task 11.9** · 2026-08-24 · A = the pre-D-15 snapshot of `jca_android`, B = the re-anchored set
· 159 traces (131 inherited + 28 written for this group) · report files
`data/gh104/evidence/harness/d15-*.md`

`unchanged 119 · moved 22 · removed 12 · introduced 6`. Every non-`unchanged` row is accounted
for below; an unattributed delta would be a defect, not a result.

> **These counts replace `unchanged 132 · moved 9 · removed 12 · introduced 6`, and the
> difference is the instrument, not the set.** Thirteen traces classed `unchanged` under a
> harness that could not see them. Neither snapshot moved: A and B are the same two directories
> that produced the first numbers, and the twelve `removed` and six `introduced` rows are
> unchanged. What changed is that the harness now compares **which accusation** each event
> raised and not merely **that** it raised one. The repair is described at the end of this file,
> because reading it first explains every row of the `moved` section that carries a `*-ALG-*`.

## introduced (6) — an accusation the re-anchoring restores

`MessageDigestSpec-d15-{md5,sha1,sha1-alias}` and the three inherited
`MessageDigestSpec-{md5,md5-only,sha1}`. Side A is silent, side B accuses. This is the
5,892-row family of the published corpus coming back, and `sha1-alias` shows it coming back
*through* the alias table: the observed `SHA1` resolves to `SHA-1`, which the expert list
rejects. Task 11.2 (`MessageDigestSpec`), acceptance measured in `d15_c5_replay.md`.

Each carries `g4:MESSAGEDIGEST-ALG-02`, and the five with a consuming call carry
`update:MESSAGEDIGEST-ALG-00` beside it, plus the ordering rows the rejected branch drags in.

## moved (22) — the accusation set changes at one or more events

### The value site starts firing (13)

Side A admitted the value, so only the ordering or a predicate complained; side B rejects it and
the `*-ALG-*` site fires at an event that was, in most of these, **already accused for another
reason**. That is why the first measurement could not see them.

- `CipherSpec-d15-{aes-ecb-pkcs5,aes-ecb-nopadding,desede-cbc,blowfish-ecb,chacha20}`: B adds
  `i1:CIPHER-ALG-00`, `i1:CIPHER-ORDER-00` and `i2:CIPHER-ALG-01`. Under the api30 tables these
  transformations were *admitted*, so `g1` fired and only the ordering complained; under the
  expert tables `getInstance` takes the `g3` branch and the value is accused at both value
  sites. This is the ECB detection returning (task 11.3), and it is why the case needed a trace:
  the corpus's 109 `CipherSpec` accusations are all the OAEP spelling, so no published number
  shows it.
- `SignatureSpec-d15-{md5withrsa,nonewithrsa,sha1withdsa}`: B adds `i1:SIGNATURE-ALG-00`.
  `i1` raises the value accusation and the predicate accusation from two independent `if`s, and
  `i1:SIGNATURE-NOBS-00` fires on both sides, so this is the exact shape the old harness lost.
- `SSLContextSpec-d15-{ssl,tlsv1}`: B adds `init:SSLCONTEXT-PROTO-00`, beside the
  `init:SSLCONTEXT-{NOBS-00,NOBS-01,ORDER-00}` that both sides raise. Task 11.2, and for `SSL`
  the `behavioural` row of task 11.4.
- `KeyGeneratorSpec-d15-{desede,hmacmd5}`: B adds `gk1:KEYGENERATOR-ALG-00`. `gk1`'s body
  checks the value unconditionally and the `@fail` handler raises `KEYGENERATOR-ORDER-00` at the
  same event, so again both sides accuse `gk1` and only the code differs.
- `SecretKeySpecSpec-badalg`: B adds `c1:SECRETKEYSPEC-ALG-00`. **This is the restored
  `SecretKeySpec` list** — the api30 rule declares no algorithm clause, so D-10 had dropped the
  list entirely and the site accused nothing. Task 11.2; the two `SECRETKEYSPEC-ALG-*` rows of
  `codes.csv` are this site.

### The value site stops firing (4) — a narrowing undone at an already-accused event

- `TrustManagerFactorySpec-sunx509`, `TrustManagerFactorySpec-d15-sunx509`: B drops
  `init:TRUSTMANAGERFACTORY-ALG-00`.
- `KeyManagerFactorySpec-d15-sunx509`: B drops `init:KEYMANAGERFACTORY-ALG-00`.
  `SunX509` is an expert entry, inert on Android but not removable — the "no narrowing by
  preference" decision of D-15, and here it is executed rather than described.
- `MacSpec-d15-hmacpbesha1`: B drops `i1:MAC-ALG-00`. `HmacPBESHA1` is named outright by
  `Mac.crysl:44`; the api30 list spelled it `PBEwithHmacSHA1` and so accused it. The
  re-anchoring **admits** this value. (The inherited `MacSpec-hmacpbesha1` says the same thing
  and classes `removed`, because there the value site was the only accusation.)

### Downstream of the Cipher change (4)

`IvChainJunctionSpec-rangen`, `IvChainJunctionSpec-rangen-unobserved`,
`MacSpec-mac-then-encrypt`, `MacSpec-update-then-encrypt`: each adds
`i2:CIPHER-ALG-01`, `i2:CIPHER-ORDER-00` and `f2:CIPHER-ORDER-00` — a transformation the tables
now reject reaches these chains in a different state. `IvChainJunctionSpec-rangen-unobserved`
also drops `g4:SECURERANDOM-ALG-00` and `useRandomKey:IVCHAINJUNCTION-NOBS-02`, both of which
are the `SecureRandom` list restoration of the `removed` section reaching the same chain.

### Platform-limited (1)

`CipherSpec-d15-arc4`: B adds `i1:CIPHER-ORDER-00` and no value code. See the note on ARC4
below — the branch changes because `g1`/`g3` read the transformation **string**, while the value
site reads `getAlgorithm()` off an object this JVM cannot produce.

## removed (12) — a narrowing undone, or its consequence

- `KeyPairGeneratorSpec-d15-rsa-3072`, `KeyPairGeneratorSpec-d15-diffiehellman`,
  `KeyPairGeneratorSpec-rsa3072`: RSA `3072` and `DiffieHellman` are expert entries; D-10 had
  dropped both. Task 11.2. (`KEYPAIRGENERATOR-KEYSIZE-00`, and for `diffiehellman` the ordering
  rows that followed it.)
- `KeyStoreSpec-d15-jks`, `KeyStoreSpec-jks`: `JKS` is an expert type, inert on Android but not
  removable. Task 11.2. (`KEYSTORE-KSTYPE-00` and its two ordering rows.)
- `SecureRandomSpec-d15-{nativeprng,windowsprng}`, `SecureRandomSpec-nativeprng`,
  `SecureRandomSpec-genseed-rejected-algorithm`: the api30 refinement had cut the list to
  `SHA1PRNG` alone; all six expert entries are back. Task 11.2. (`SECURERANDOM-ALG-00` and the
  ordering and predicate rows that followed it.)
- `MacSpec-hmacpbesha1`, `MacSpec-unsafe-generated-key`, `KeyGeneratorSpec-rangen-unobserved`:
  `HmacPBESHA1` is an expert entry the api30 list had dropped; the other two are its
  downstream chains.

Every one of these classes `removed` against the **pre-D-15 snapshot** because that snapshot
accused them. Against the **frozen `jca`** the same traces are `unchanged`, which is the
statement the design makes: the narrowings were undone, not merely described.

## What the first measurement could not see, and why

The first run of this group reported `unchanged 132 · moved 9`. Thirteen of those `unchanged`
rows were not unchanged. Two defects in the instrument, both now repaired, and both of the same
family as the lesson `data/jca_android/README.md` draws about green gates:

1. **`TraceRunner.envelope()` scanned instead of diffing.** `ErrorCollector` accumulates over a
   whole trace and hands back a `HashSet`; the method walked that set and returned the *first*
   error matching the specification. So an event that added a second accusation recorded only
   one of them, and — worse — the recorded envelope could belong to an event that had fired
   earlier. That is visible in the previous committed evidence: all four
   `MacSpec-hmacpbesha1` envelopes carry `ev=i1` inside the message while the outer `ev=` reads
   `update`, `updateBytes`, `f1`. The method now diffs the set against a snapshot taken before
   the advice and writes one envelope per accusation the event actually added, ordered by the
   message so that two snapshots stay comparable.

2. **`classify()` compared event names only.** Its docstring gave the reason — a message this
   change rewrote must not read as a behavioural difference — and the reason is right, but the
   remedy was too coarse. `SignatureSpec.i1` raises `SIGNATURE-ALG-00` and `SIGNATURE-NOBS-00`
   from two independent `if`s, so re-anchoring a value list adds an accusation at an event that
   was already accused, and a comparison over event names calls that `unchanged`. The comparison
   is now over `(event, code)` pairs: the code is the accusation's identity — `codes.csv` is
   what carries it — and the prose after it still counts for nothing.

The report tables now print `event:CODE` rather than the bare event, so a `moved` row can be
read without opening the envelopes underneath it.

Neither defect could be caught by the harness self-test as it stood: its three mutations each
move an accusation to an event that was previously silent, which is exactly the case a
name-only comparison still gets right. Re-run after the repair, the self-test still returns its
three designed verdicts — `moved` on `TrustManagerFactorySpec-x509`, `removed` on
`IvParameterSpecSpec-unrandomised`, `introduced` on `MessageDigestSpec-md5-only` — and now
classes nine further traces `moved`, for the same reason the main run does.

## A limit that is the platform's, not the traces'

One value in this group cannot be witnessed by execution on this JVM: **`ARC4`**.
`KeyGenerator.getInstance("ARC4")` and `Cipher.getInstance("ARC4")` both raise
`NoSuchAlgorithmException` here, so `TraceRunner` falls back to the first name in `FALLBACKS`
that the platform does answer — `AES` for both. The value sites of `KeyGeneratorSpec.gk1` and
`CipherSpec.i1` read `k.getAlgorithm()` / the transformation off the **object**, so they see
`AES`, and staying silent is the correct answer to the object they were given.
`KeyGeneratorSpec-d15-arc4` therefore classes `unchanged` and `CipherSpec-d15-arc4` moves only
at its ordering site, where the `g1`/`g3` split reads the string the trace named.

Lengthening either trace changes nothing; the object is what is missing, not the sequence. The
C5 replay (`d15_c5_replay.md`) checks `ARC4` against the lists directly and it is rejected, and
`Api30CipherTransformationUtil`'s superseding javadoc records `ARC4` among the transformations
measured as admitted by the withdrawn anchor and accused by the frozen one. The other seven
values of this family — `MD5`, `SHA-1`, `DESede`, `HmacMD5`, `NONEwithRSA`, `MD5withRSA`,
`SHA1withDSA`, `SSL`, `TLSv1` — are all producible here and all witnessed above.

**Superseded reading.** An earlier version of this file recorded eight traces as classing
`unchanged` because they were "too short to reach the `*-ALG-*` site", and named
`KeyGeneratorSpec-d15-hmacmd5` as the counter-example that proved the site worked. Measured, the
premise was wrong in three ways: seven of the eight do reach the value site and B does raise the
accusation; `hmacmd5` classed `unchanged` exactly like them; and `MacSpec-d15-hmacpbesha1` was
listed among values "the re-anchoring does reject" while the same file's `removed` section
already recorded `HmacPBESHA1` as an expert entry the re-anchoring **admits**. The instrument,
not the traces, was what could not see it.
