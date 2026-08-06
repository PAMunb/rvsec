# MetaCrySL tier map and the derivation of the `jca_android` specification set

**Date**: 2026-08-06
**Change**: `openspec/changes/gh99-metacrysl-jca-android`
**GitHub Issue**: [#99](https://github.com/PAMunb/rvsec/issues/99)

This document records how the `jca_android` `.mop` set was derived rather than
translated by hand, what the derivation produced, and where it falls short. It is
the evidence behind the claim that the Android rules are *derived*, which is what
threat **W3** of the thesis asks for.

Paths outside `rv-android` are absolute, with `$WS` =
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`.

---

## 1. What MetaCrySL is, and what a tier means

MetaCrySL is a meta-specification layer over CrySL, written in Rascal. It takes a
set of **base specifications** (`$WS/MetaCrySL/samples/jca/base/`, 32 of them plus
the one authored here) and an ordered chain of **refinement tiers**
(`$WS/MetaCrySL/samples/jca/android/`, 19 of them plus the one authored here), and
emits plain `.cryptsl` rules. A tier declares the *delta* introduced at one API
level, never a total; composition is a set union over `define` values.

The upstream repository documents no rule for which tiers belong to a given
target. Reading the tier contents establishes one, and the platform documentation
confirms it:

- **`AABB` (four digits) is a closed availability window** — API `AA` through
  `BB`, for something that existed and was then removed.
- **`XXplus` is an open window** — API `XX` onward.

### 1.1 The rule, verified against the platform

Checked against the AOSP "Supported API Levels" tables. The `SSLContext` table
alone confirms both halves of the rule and every tier that touches it:

| Algorithm | Documented | Tier | |
|---|---|---|---|
| `TLS` | 1+ | `01plus` | ✓ |
| `Default`, `SSL`, `TLSv1` | 10+ | `10plus` | ✓ |
| `SSLv3` | **10-25** | `1025` | ✓ both digits |
| `TLSv1.1`, `TLSv1.2` | 16+ | `16plus` | ✓ |
| `TLSv1.3` | 29+ | *(none)* | gap — hence the authored `30plus` |

The four-digit tiers check out likewise: `0103` carries `MD2withRSA` (documented
1-3); `0108` carries `MD4withRSA`, `MD5withRSA/ISO9796-2`, `RSASSA-PSS`,
`SHA1withRSA/ISO9796-2` (all 1-8) and the keystore types `BCPKCS12`, `PKCS12-DEF`
(1-8); `1013` carries `RC4` (10-13); `1025` carries `SSLv3` (10-25).

`0119` does **not** check out. Its `Signature.ref` is a verbatim copy of
`0108/Signature.ref` — a 1-8 set. The algorithm whose window really is 1-19 is
`DSS`, and it is not there. See §4, defect D3.

### 1.2 Which tiers an API 30 target composes

Only the `XXplus` tiers with `XX ≤ 30`. Every four-digit window closes before 30,
so none of them qualifies — which is why `SSLv3` drops out of the API 30 rule on
its own, without anyone deciding to remove it.

```
01plus  10plus  11plus  14plus  16plus  17plus  18plus
19plus  20plus  22plus  23plus  24plus  26plus  28plus   +  30plus (authored)
```

`$WS/MetaCrySL/samples/jca/android/config/Android30.config` loads exactly these
fifteen over `load spec base/`.

Applying the same rule to the pre-existing `Android25plus.config` shows it wrongly
omits `17plus`, `19plus` and `23plus`, all of which are ≤ 25. That is recorded
here as evidence that the rule has diagnostic power. **It was not repaired** — this
work targets API 30, and the earlier targets do not feed it.

---

## 2. The tier map

| Tier | Kind | Specifications refined |
|---|---|---|
| `0103` | window 1-3 | Signature |
| `0108` | window 1-8 | AlgorithmParameters, KeyGenerator, KeyStore, Mac, MessageDigest, Signature |
| `0119` | window 1-19 | Signature *(contents wrong — see D3)* |
| `1013` | window 10-13 | KeyGenerator |
| `1025` | window 10-25 | SSLContext |
| `01plus` | 1+ | AlgorithmParameters, Cipher, KeyGenerator, KeyStore, Mac, MessageDigest, SSLContext, SecretKeyFactory, SecureRandom, Signature |
| `10plus` | 10+ | AlgorithmParameters, Cipher, KeyGenerator, SSLContext, SecretKeyFactory |
| `11plus` | 11+ | KeyGenerator, KeyPairGenerator, Signature |
| `14plus` | 14+ | KeyGenerator, KeyStore |
| `16plus` | 16+ | SSLContext |
| `17plus` | 17+ | Signature |
| `18plus` | 18+ | KeyStore |
| `19plus` | 19+ | SecretKeyFactory |
| `20plus` | 20+ | Signature |
| `22plus` | 22+ | KeyGenerator, Mac, MessageDigest |
| `23plus` | 23+ | Cipher, SecretKeyFactory, Signature |
| `24plus` | 24+ | AlgorithmParameters |
| `26plus` | 26+ | AlgorithmParameters, Cipher, Mac, SecretKeyFactory |
| `28plus` | 28+ | AlgorithmParameters, Cipher, KeyGenerator |
| `30plus` | 30+ | SSLContext **(authored here)** |

Tiers in bold-italic below the line are ours. Two files were authored:

- `$WS/MetaCrySL/samples/jca/base/TrustManagerFactory.cryptsl` — the base set had
  none, yet `base/SSLContext.cryptsl:32` requires the predicate
  `generatedTrustManager[tms]` that no specification produced. An orphan
  predicate is an upstream omission, not a deliberate exclusion. The rule is
  modelled on the CrySL 1.5.2 `TrustManagerFactory.crysl` for its objects, events
  and order, and on the sibling `base/KeyManagerFactory.cryptsl` for MetaCrySL's
  own conventions: MetaCrySL collapses CrySL's singular/plural predicate pair
  (`generatedTrustManager[this]` for the factory, `generatedTrustManagers[array]`
  for the array) into the singular name for both, and `SSLContext` requires the
  singular. Constrained to `algo in {"PKIX"}`, which is the *whole* of Android's
  `TrustManagerFactory` table. After this, no predicate required anywhere in the
  base set is left without a producer.
- `$WS/MetaCrySL/samples/jca/android/30plus/SSLContext.ref` — `TLSv1.3`, API 29.

**`TLSv1.3` is the only algorithm addition in the API 29-30 window** across every
class in the base set. Verified against the AOSP tables rather than assumed:
`XDH` (KeyPairGenerator) is 33+, `AESCMAC` (Mac) is 31+, `Ed25519` (Signature) is
33+. One further API-30 addition exists but is a *mode*, not an algorithm name —
see D6.

---

## 3. What the derivation produced

`Android30.config` generates **33 `.cryptsl` rules** into
`$WS/MetaCrySL/generated/api30/` (32 base + the authored `TrustManagerFactory`).

Confronting each generated rule against the platform's own table, filtered to the
entries whose documented range covers API 30, **six specifications agree with
Android element for element**: `SSLContext`, `KeyStore`, `Mac`, `MessageDigest`,
`KeyManagerFactory`, `TrustManagerFactory`.

`SSLContext` composes to exactly the seven protocols Android ships at API 30:

```
protocol in {"Default", "TLSv1.2", "TLSv1.1", "SSL", "TLSv1", "TLS", "TLSv1.3"}
```

### 3.1 Against the CrySL 1.5.2 rules

All 33 generated rules have a CrySL 1.5.2 counterpart in
`$WS/rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/`; 16 of 1.5.2's 49
rules have no MetaCrySL base specification (`KeyAgreement`, `KeyFactory`,
`SSLEngine`, `SSLParameters`, `CertificateFactory`, `Cookie`, `TrustAnchor`,
`ECGenParameterSpec`, `ECParameterSpec`, `DHParameterSpec`, `DSAParameterSpec`,
`MGF1ParameterSpec`, `OAEPParameterSpec`, `AlgorithmParameterGenerator`,
`PasswordAuthentication`, `X509EncodedKeySpec`). **No** allow-list is identical
between the two sets. The delta sorts into four classes.

**A — Java SE names replaced by Android names.** This is the adaptation the whole
exercise is for, and it lands exactly on the Layer 1 catalogue of
`docs/20260806_plano_specs_jca_android.md`:

| Spec | CrySL 1.5.2 | derived API 30 | item |
|---|---|---|---|
| `KeyStore` | `DKS`, `JCEKS`, `JKS`, `PKCS11` | `AndroidCAStore`, `AndroidKeyStore`, `BKS`, `BouncyCastle`, `PKCS12` | L1.1 |
| `SecureRandom` | `NativePRNG`, `NativePRNGBlocking`, `NativePRNGNonBlocking`, `PKCS11`, `Windows-PRNG`, `SHA1PRNG` | `SHA1PRNG` | L1.4 |
| `KeyManagerFactory` | `PKIX`, `SunX509` | `PKIX` | L1.3 |
| `TrustManagerFactory` | `PKIX`, `SunX509` | `PKIX` | L1.3 |
| `KeyPairGenerator`, `AlgorithmParameters` | `DiffieHellman` | `DH` | L1.3 |

**B — case normalisation.** `PBEWith…` becomes `PBEwith…` and `PBKDF2With…`
becomes `PBKDF2with…`, across `SecretKeyFactory` (twelve literals), `Mac` and
`AlgorithmParameters`. JCA resolves algorithm names case-insensitively at
`getInstance`; a `.mop` string comparison does not. Items L1.6/L1.8.

**C — availability broadening.** See §5.

**D — a constraint dropped.** 1.5.2 constrains `SecretKeySpec` to
`keyAlgorithm in {"AES","HmacSHA256","HmacSHA384","HmacSHA512"}`; the MetaCrySL
base specification carries no membership constraint, so the derived rule imposes
none.

---

## 4. Defects in the derived rules, adopted rather than repaired

The decision on this change was to **adopt the generated output as authored**, on
the grounds that MetaCrySL was written and recommended by members of the project.
Everything in this section is therefore recorded, not patched. Each was found by
confronting the generated rule against the platform table and verified against the
AOSP documentation.

| # | Spec | Defect | Direction |
|---|---|---|---|
| D1 | `Signature` | omits the whole ECDSA family — `ECDSA`, `ECDSAwithSHA1`, `NONEwithECDSA`, `SHA1withECDSA`, `SHA256withECDSA`, `SHA384withECDSA`, `SHA512withECDSA`, all documented 11+ | **false positive** |
| D2 | `KeyPairGenerator` | rejects `EC` outright while still carrying `alg in {"EC"} => keySize in {256}` | **false positive**, and internally unsatisfiable |
| D3 | `Signature` | admits `DSS`, documented 1-19 and removed at API 20 | false negative |
| D4 | `AlgorithmParameters` | literals `"DSADSA"` and `"PBEwithHmacSHA512AndAES_256PBEwithHmacSHA512AndAES_256"` — a `", "` missing in `01plus` and `26plus` | never match |
| D5 | `SecretKeyFactory` | literal `"PBEwithSHAANDTWOFISH-CBC\t"` carries a tab inside the string, from `10plus` | never matches |
| D6 | `Cipher` | no `GCM-SIV` mode, though `AES/GCM-SIV/NoPadding` is documented 30+ | false positive |

**D1 and D2 are the consequential pair.** Android's own cryptography guide names
`SHA256withECDSA` as the recommended `Signature` algorithm. The derived rule
rejects it, and the derived `KeyPairGenerator` rejects the `EC` key pairs that
would feed it. A campaign run with `jca_android` will therefore flag *correct*,
*recommended* elliptic-curve code as misuse.

**D2's root cause is not a missing tier.** `base/KeyPairGenerator.cryptsl` writes
its membership constraint as a literal, `alg in {"DH", "DSA", "RSA"}`, instead of
`alg in ${algorithm}`. Nothing consumes the meta-variable, so
`11plus/KeyPairGenerator.ref`'s `define algorithm = {"EC"};` is dead code — while
the same tier's `add constraint` and `add require` lines do take effect. The
generated rule ends up holding both `alg in {"DSA","DH","RSA"}` and
`alg in {"EC"} => keySize in {256}`, a conjunction no EC program can satisfy.
Repairing it would mean editing a base specification, not a tier.

**D3's root cause is a mis-tiered algorithm.** `DSS` is a closed 1-19 window but
`11plus/Signature.ref` declares it open. Since `11plus` is one of the fourteen
tiers an API-30 target loads, `DSS` leaks into the composition. This is the same
algorithm `0119` should have carried and does not (§1.1).

---

## 5. Threat to validity: the bias inverts, and not only for `SSLContext`

The `android` profile models which algorithms **exist** at an API level, not which
are **advisable**. Composed for API 30, the derived rules are markedly more
permissive than the CrySL 1.5.2 rules the current `jca` set was translated from:

| Spec | 1.5.2 | derived | admitted that 1.5.2 refused |
|---|---|---|---|
| `SSLContext` | 2 | 7 | `Default`, `SSL`, `TLS`, `TLSv1`, `TLSv1.1` |
| `MessageDigest` | 3 | 6 | `MD5`, `SHA-1`, `SHA-224` |
| `Signature` | 7 | 20 | incl. `MD5withRSA`, `SHA1withRSA`, `DSS` |
| `KeyGenerator` | 4 | 11 | incl. `ARC4`, `BLOWFISH`, `DESede`, `HmacMD5` |
| `SecretKeyFactory` | 12 | 44 | incl. the whole PBE-with-MD5 family |

**The bias therefore inverts direction.** The current `jca` set produces false
positives, by naming Java SE algorithms that Android does not have. The derived
`jca_android` trades some of those for **false negatives**: it will no longer flag
`SSLv3`-adjacent protocol choices such as `SSL` and `TLSv1`, nor `MD5`, nor
`MD5withRSA`. Plan §1.3 recorded this for `SSLContext`; measured across the set,
`MessageDigest` admitting `MD5` and `Signature` admitting `MD5withRSA` carry more
security weight than the protocol list does.

Any result obtained with `jca_android` must be read with this in mind. A drop in
reported violations relative to `jca` is **not** evidence of better code — it is
partly the specification becoming permissive by construction.

Two qualifications, both in favour of adopting the output as authored:

1. **The profile is availability minus deliberate exclusions.** `DES` is
   documented 1+ for `Cipher`, `KeyGenerator`, `SecretKeyFactory` and
   `AlgorithmParameters`, yet appears in no base specification and no tier. The
   omission is uniform, so it is deliberate: the profile already withholds an
   algorithm on security grounds rather than merely describing what exists.
2. **The `-cc` and `-bsi` profiles are not an alternative.** `android-bsi` is
   byte-identical to `android` for `SSLContext` and restricts nothing despite its
   name; `android-cc` defines `{"Insecure"}` at `01plus`, which is not a JCA
   protocol name.

---

## 6. Traceability of the `jca_android` `.mop` set

Destination: `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/` — **23
`.mop` files and no `.aj`**. `MultiSpec_1MonitorAspect.aj` was deliberately not
copied: §9.1 of `docs/20260806_plano_specs_jca_android.md` flags it as stale
residue carrying defect L2.7.

The governing principle: an allow-list changes only where a generated rule
contradicts it. Spelling variants that denote the same algorithm — case forms and
dashless aliases — are carried over from `jca` unchanged, because the `.mop`
compares strings where CrySL compares algorithm identity. Those are declared
translation artefacts, not derivations.

### 6.1 Adapted — ten files, each anchored to a generated rule

| `.mop` | Anchor | Change |
|---|---|---|
| `SSLContextSpec` | `SSLContext.cryptsl` | `{TLSV1.2, TLSV1.3}` → the seven derived protocols (held uppercase, since the spec compares `protocol.toUpperCase()`); hardcoded error message updated to match |
| `KeyStoreSpec` | `KeyStore.cryptsl` | `{JCEKS, JKS, DKS, PKCS11, PKCS12}` → `{AndroidCAStore, AndroidKeyStore, BKS, BouncyCastle, PKCS12}` (L1.1) |
| `TrustManagerFactorySpec` | `TrustManagerFactory.cryptsl` (authored) | `{PKIX, SunX509}` → `{PKIX}` (L1.3) |
| `KeyManagerFactorySpec` | `KeyManagerFactory.cryptsl` | `{PKIX, SunX509}` → `{PKIX}` (L1.3) |
| `SecureRandomSpec` | `SecureRandom.cryptsl` | six algorithms → `{SHA1PRNG}` (L1.4) |
| `MessageDigestSpec` | `MessageDigest.cryptsl` | adds `MD5`, `SHA-1`, `SHA-224`; the three dashless aliases already in `jca` are carried over (L1.7) |
| `SignatureSpec` | `Signature.cryptsl` | seven → the twenty derived; **loses the ECDSA family (D1), gains `DSS` (D3)** |
| `MacSpec` | `Mac.cryptsl` | `PBEWith…` → `PBEwith…`; `HmacPBESHA1` dropped (no counterpart); `HMAC-*` aliases carried over |
| `KeyGeneratorSpec` | `KeyGenerator.cryptsl` | four → the eleven derived; `HMAC-*` aliases carried over |
| `KeyPairGeneratorSpec` | `KeyPairGenerator.cryptsl` | `{RSA, EC, DSA, DiffieHellman, DH}` → `{DH, DSA, RSA}`; `case "DiffieHellman"` removed from the key-size switch; RSA sizes `{4096, 3072, 2048}` → `{4096, 2048}` per the derived constraint. **`case "EC"` is kept**, mirroring the derived rule's own unsatisfiable pair (D2) |

### 6.2 Verbatim — thirteen files

`CipherInputStreamSpec`, `CipherOutputStreamSpec`, `CipherSpec`,
`DHGenParameterSpecSpec`, `GCMParameterSpecSpec`, `HMACParameterSpecSpec`,
`IvParameterSpec`, `KeyPairSpec`, `PBEKeySpecSpec`, `PBEParameterSpecSpec`,
`RandomStringPassword`, `SecretKeySpec`, `SecretKeySpecSpec`.

Three of these deserve their reason stated:

- **`GCMParameterSpecSpec`** — kept verbatim because it already *agrees*: the
  derived rule gives `tLen in {96, 104, 112, 120, 128}`, exactly the `.mop` list.
- **`SecretKeySpecSpec`** — the derived rule imposes no membership constraint at
  all (§3.1 class D), so the `.mop` allow-list has no derived anchor either way.
  A rule that says nothing cannot contradict, so the list is left untouched and
  declared a hand translation.
- **`RandomStringPassword`** — has no MetaCrySL counterpart and is not a JCA
  specification. It propagates randomness taint through `String.valueOf` and
  `toCharArray` so that a password derived from `SecureRandom` is not accused by
  `PBEKeySpecSpec`. Copied verbatim and declared a hand translation.

### 6.3 `CipherSpec` could not be adapted — L1.5 remains open

`CipherSpec.mop` holds no allow-list. It delegates to `isValid(transformation)`,
imported from
`$WS/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java`,
where the mode and padding tables live as Java constants. That class is compiled
into `rvsec-core` and used at runtime by **both** specification sets.

Adapting Cipher's transformation constraints for Android therefore cannot be done
in the `.mop` file. It would require either editing shared Java — which would
change the behaviour of the existing `jca` set and invalidate every result already
measured against it — or introducing a parallel Android-specific utility, which is
new Java code and outside this change.

**Consequence: plan item L1.5 is not addressed by `jca_android`.** The Cipher
transformation rules in the Android set are byte-identical to the Java SE ones.
This is the largest single gap in the derivation and should be the first thing a
follow-up change takes on.

---

## 7. Generator defects recorded as debt

None of these were repaired. The **only** change made to
`$WS/MetaCrySL/src/` is the two-line fix in `PreProcessor.rsc` described below,
without which nothing generates at all.

**The fix.** `bindObjectDecl` (`PreProcessor.rsc:45`) and `bindLiteralSet` (`:81`)
compared `metaVariable(v) == var`. `MetaVariable` is declared
`data MetaVariable = metaVariable(str varName);` with no `location` or `comments`
field, but `implode` attaches both as **keyword parameters**, and keyword
parameters participate in equality. The node built in code therefore never equals
the node coming from the parse, so every generation failed with `invalid
definition for variable` and wrote zero files — on every Rascal obtainable, for
every input, including the most trivial refinement in the repository. This is the
historical Rascal migration from *annotations*, which `==` ignored, to *keyword
parameters*, which it does not. Both sites now compare `v == var.varName`.

Left as documented debt:

- **Constraints are duplicated in the output**, and the duplication grows with
  chain length: 0 duplicates in target `0108`, 7 in `0116`, 22 in `25plus`.
  Logically inert, since conjunction is idempotent, but it inflates diffs and
  human reading — and the API-30 chain is the longest yet composed.
- **`Loader.rsc` never resets** its module-level `specifications` and
  `refinements`, so two generations in one Rascal session contaminate the second.
  Every target must be generated in a **fresh session**.
- **`Main.rsc` swallows exceptions** (`catch e: println(e)`). The trailing `done`
  is the only signal that distinguishes success from failure.
- **Paths must be absolute.** `Loader.rsc` and `Main.rsc` both build locations as
  `|file:///| + fullPath`, so a relative path resolves against the filesystem root.
- **The `config <Name>` identifier is parsed but never read**, which is why the
  upstream copy-paste in `Android25plus.config` (it is named `Android0108`) is
  harmless.

Two parser constraints that bite silently, and apply to `.config`, `.cryptsl` and
`.ref` alike, because all three are parsed with `parse(#XDef, ...)` rather than
`parse(#start[X], ...)` — without `start`, Rascal permits no layout at the outer
edges:

- **No trailing newline.** A final `\n` after the closing token is a parse error.
  Every committed file in the repository ends at its last character.
- **Restricted path alphabet.** `lexical Path = [a-zA-Z0-9/\-]*` admits no `_`,
  `.` or `~`.

And one caveat when comparing generated output: `set[Literal]` has no stable
iteration order in Rascal, so two semantically identical runs may serialise the
elements inside `{...}` differently. Normalise the ordering before diffing.

---

## 8. Reproducing the generation

```bash
MC=$WS/MetaCrySL
J8=~/.sdkman/candidates/java/8.0.502-tem/bin/java
cd $MC   # required: META-INF/RASCAL.MF (Source: src) is what puts src/ on the search path

printf "import generator::Main;\nmain(|file://$MC/samples/jca/android/config/Android30.config|);\n:quit\n" \
 | timeout 900 $J8 -Xmx2G -Xss32m -jar rascal-0.19.6.jar 2>&1 \
 | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\r//g'
```

Rascal **0.19.6 with Java 8**. The current `rascal-shell-stable.jar` is Rascal
0.42.0, class file 55, so Java 8 cannot run it at all, and its REPL additionally
needs a pty with an explicit terminal width. 0.19.6 needs neither. Neither jar is
committed — `*.jar` is gitignored in the fork.

The gate for trusting any of this: `Android0108.config`, regenerated with the fix,
reproduces the committed `samples/jca/android/target/research/0108/` at **32/32
equivalent** — 21 byte-identical, 11 differing only in set-element ordering.

---

## 9. End-to-end validation of the set

The derived `.mop` files are only useful if the RVSEC pipeline can still turn them
into monitors. That was checked by consuming the set through the `custom`
specification path, with instrumentation, static analysis and execution all
switched off — so no emulator and no APK are involved, and the run exercises
monitor generation alone:

```bash
uv run rv-experiment run --tools monkey \
  --specification-set custom \
  --custom-specs-dir $WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android \
  --apks-dir ./apks_examples \
  --generate-monitors --skip-instrument --skip-static --skip-execution \
  --name gh99_jca_android_monitors
```

All 23 specifications produced `.rvm`, and JavaMOP plus RV-Monitor emitted
`MultiSpec_1RuntimeMonitor.java` (16 485 lines), `MultiSpec_1MonitorAspect.aj`
(705 lines) and `Coverage.aj` with zero errors. The derived literals reach the
monitor — `AndroidKeyStore`, `AndroidCAStore`, `BouncyCastle`, `PKIX`, `TLSV1.3`,
`SHA1PRNG`, `ChaCha20`, `PBEwithHmacSHA512` — and every Java SE leftover is gone:
`SunX509`, `JCEKS`, `DKS`, `NativePRNG`, `DiffieHellman`, `SHA256withECDSA`,
`PBEWithHmacSHA1` and `HmacPBESHA1` all occur zero times.

One detail costs time if rediscovered: the allow-lists live in
`MultiSpec_1RuntimeMonitor.java`, **not** in the aspect. Grepping the `.aj` for
algorithm names returns nothing and means nothing.

### 9.1 The instrumentation descriptor

`MultiSpec_1MonitorAspect.json` (86 597 bytes) was emitted alongside the aspect —
`emit_descriptor` defaults to `True` in
`modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:212`,
so no extra flag is needed. This descriptor is what the dexlib2 instrumenter reads
instead of parsing the `.aj`, which makes its coverage of the set the real test of
whether `jca_android` is usable downstream. It holds 115 advices, 134 monitor
calls, 49 imports, one `commonPointcut` and 12 `baseAspectExclusions`.

The descriptor was checked against the set and against the generated monitor:

| Check | Result |
|---|---|
| Distinct `specName` values across the 115 advices | 23 |
| Correspondence with the 23 `.mop` files | 1:1, no spec dropped and none extra |
| Advices with no `monitorCall` | 0 |
| `monitorCall.specName` disagreeing with its advice's `specName` | 0 |
| Monitor methods named by the 134 calls but absent from `MultiSpec_1RuntimeMonitor.java` | 0 |
| Distinct types targeted by the advice pointcuts | 23 |
| Imports naming a JSE-only provider class | 0 |

The 1:1 correspondence is not by filename — three specifications declare a name
that differs from their file (`IvParameterSpec.mop` declares `IvParameterSpecSpec`,
`RandomStringPassword.mop` declares `RandomStringPasswordSpec`, and
`SecretKeySpec.mop` and `SecretKeySpecSpec.mop` are two distinct specifications
whose names differ by one suffix). The check matched declared names, not files.

**No advice is `around`.** All 115 are `isAround: false` — 97 `after` and 18
`before` — and `grep` finds no `around` in the `jca_android` `.mop` files, in the
`jca` originals, or in the generated `.aj`. The derivation introduced none, which
is what had to be true: the dexlib2 weaver rejects `around` at
`EmitterDispatch.java:61-65` and merely increments `plansSkipped` in
`DexWeaver.java:419-424`, so an `around` advice would be silently dropped rather
than failing the weave. This matches the revision-4 finding of zero `around`
across the whole corpus.

### 9.2 The guard fixes from `jca` survived the derivation

`jca_android` was copied from `jca`, so any correction previously made to the
originals had to come across intact. Two are on record in the `rvsec` history and
both are present:

| Commit | Fix | State in `jca_android` |
|---|---|---|
| `9cec468b` | `KeyManagerFactorySpec` `init` guard negated, so `UnsafeAlgorithm` fires on unsafe algorithms rather than safe ones | present — `KeyManagerFactorySpec.mop:53` reads `if (!safeAlgorithms.contains(currentAlgorithmInstance))` |
| `2fa44ff5` | PBE error labels canonicalised to the block name | present — 6 occurrences of `"PBEKeySpecSpec"` and 2 of `"PBEParameterSpecSpec"`, zero of the old short labels |

More generally, a file-by-file diff of the two sets shows **ten files differing and
thirteen identical**, matching §6. Every one of the ten differs only in literal
lists — the algorithm/protocol/type allow-lists, the `SSLContext` error message
that enumerates them, and the `KeyPairGenerator` key-size table. No guard, no
`condition(...)`, no event, no advice position and no pointcut was touched. The
derivation changes *what counts as acceptable*, never *how the specification
decides*.

---

## 10. Related documents

| Document | Purpose |
|---|---|
| `docs/20260806_plano_specs_jca_android.md` | The governing plan; phase F2 is what this derivation satisfies |
| `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` | Revision-4 weaver investigation; its defects are a separate track |
| `openspec/changes/gh99-metacrysl-jca-android/plan.md` | The change plan behind this work |
