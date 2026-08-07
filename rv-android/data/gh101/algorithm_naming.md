# Algorithm naming: what the specifications compare, and what the platform resolves

A JCA specification decides whether a call is a misuse by asking whether the
algorithm string the application passed is in a list of literals. The platform
decides whether the call *works* by asking its providers to resolve that string
to a service. The two questions are not the same, and the gap between them
produces false positives that no allow-list change reaches — because the
information needed to close it does not exist in any rule.

This record exists because the gap was measured while implementing gh101, from
two independent directions, and because only the smallest part of it is repaired
here. Everything else is recorded rather than fixed.

## What the platform actually does

`Provider.getService(type, algorithm)` matches on two things: the name a provider
registered the service under, and any **alias** it registered pointing at that
service. Both matches are **case-insensitive**. So all four of these reach the
same `Mac` implementation on Android:

```
HmacSHA256    HMACSHA256    hmacsha256    HMAC-SHA256  (if registered as an alias)
```

and `TrustManagerFactory.getInstance("X509")` returns the same factory as
`"PKIX"`, because Conscrypt registers `X509` as an alias of `PKIX`.

**Neither CrySL nor MetaCrySL models aliases.** A CrySL constraint is a set of
literal strings. MetaCrySL's platform table is built from the algorithm names the
Android documentation lists, which are the canonical ones. An alias is invisible
to the entire chain — upstream rule, generated rule, and `.mop` alike.

## What the specifications do today

Of the 12 `jca_android` specifications carrying an allow-list, **3 fold case** and
**9 compare exactly**:

| | specifications |
|---|---|
| folds (`alg.toUpperCase()` against an upper-case list) | `SSLContextSpec`, `MessageDigestSpec`, `SecretKeySpecSpec` |
| compares exactly (`list.contains(alg)`) | `MacSpec`, `KeyGeneratorSpec`, `SignatureSpec`, `KeyStoreSpec`, `KeyPairGeneratorSpec`, `KeyManagerFactorySpec`, `TrustManagerFactorySpec`, `SecureRandomSpec` |

Nothing normalises anywhere else in the pipeline. `MultiSpec_1MonitorAspect.aj`
binds the argument and passes it to the monitor untouched; the monitor runs
`safeAlgorithms.contains(alg)` on the raw string. The frozen
`CipherTransformationUtil` is half-folded: it upper-cases the padding
(`pad(transformation).toUpperCase()`) but compares the algorithm and mode
exactly.

The other half of the current workaround is in the data: the allow-lists carry
hand-added spellings — `HMAC-SHA256`, `HMAC/SHA256`, `SHA256` beside `SHA-256` —
which are the aliases someone saw in the wild, transcribed by hand. They are kept
(user decision, 2026-08-07) and declared as translation artefacts.

## How big the gap is

Measured twice, from opposite ends, and the two agree.

**Floor — what the campaign observed at runtime.** Of the 454 misuse tuples,
129 carry an observed algorithm value. **8 tuples in 8 apps** are rejected for
spelling alone: `MessageDigest("SHA1")` ×5, `Signature("SHA256WITHRSA")`,
`Signature("NONEWITHRSA")`, `Cipher("RSA/ECB/OAEPWithSHA1AndMGF1Padding")`.

**Ceiling — what the corpus sources contain.** Sweeping 348 app repositories for
`getInstance("…")` with a literal argument gives 376 call sites, 69 distinct:

| | sites |
|---|---:|
| accepted by the derived set as it stands | 269 |
| rejected on **case** alone — `KeyStore("pkcs12")` | 2 |
| rejected on **separator** alone — `MessageDigest("SHA1")` ×6, `Mac("HMAC-SHA-1")` | 7 |
| rejected for another reason | 23 |
| `Cipher` / `SecretKeyFactory`, which carry no inline list | 69 |
| not literals (`Mac.getInstance("Hmac" + algo)`) | 6 |

So the spelling gap is **9 call sites**, against a floor of 8 misuse tuples.
Small, and real.

One data point settles that folding works where it is applied:
`MessageDigest.getInstance("sha-1")`, `"sha-256"` and `"sha-384"` — 4 sites — are
accepted **only** because `MessageDigestSpec` calls `.toUpperCase()`.

## The larger finding the same sweep produced

Of the 23 sites rejected for another reason, 15 are defects in the **generated
rule**, not in the translation:

| observed | sites | apps | what it is |
|---|---:|---:|---|
| `Signature("SHA256withECDSA")` | 4 | | tier-map defect **D1** — the derived rule drops most of the ECDSA family. Adopted deliberately |
| `KeyPairGenerator("EC")` | 4 | | tier-map defect **D2** — the rule rejects `EC` while carrying `alg in {"EC"} => keySize in {256}`. Adopted deliberately |
| `TrustManagerFactory("X509")`, `KeyManagerFactory("X509")` | 6 | 6 | **not previously recorded** |
| `Cipher("RSA/NONE/NoPadding")` | 1 | 1 | **not previously recorded** |

The two new ones traced through every list in the chain:

| list | `(Trust\|Key)ManagerFactory` | `Cipher` RSA modes |
|---|---|---|
| CrySL 1.5.2 (upstream) | `{PKIX, SunX509}` | `{"", ECB}` |
| MetaCrySL base specification | `{PKIX}` — a literal, not `${algorithm}` | — |
| generated API 30 | `{PKIX}` | `{"", ECB}` |
| `jca` `.mop` (frozen) | `{PKIX, SunX509}` | delegates to `isValid` |
| `jca_android` `.mop` | `{PKIX}` | delegates to `isValid` |

`X509` is in none of them, not even upstream, and no `.ref` defines an algorithm
set for either ManagerFactory in any tier — so the base specification's literal is
all there is, which is the same root cause as D2. `RSA/NONE/NoPadding` is likewise
absent upstream, so that gap is inherited from CrySL rather than introduced by the
derivation.

Neither is repaired here. Adding `X509` to an allow-list would make it a
hand-maintained table diverging from its rule, which is what D-S4 and INV-INS-112
exist to prevent; and the MetaCrySL tree is not this change's to edit.

## What would actually close it, and why it is not in this change

A static list cannot express an alias without duplicating the platform's provider
table. But the monitor runs **inside the emulator**, where the table is available:

```java
static boolean admits(List<String> allowed, String type, String observed) {
    String canonical = resolveViaProviders(type, observed);   // Security.getProviders(),
                                                              // plus the Alg.Alias.<type>.<alias>
                                                              // entries each Provider exposes
    if (canonical == null) return false;                      // the platform does not offer it
    return allowed.stream().anyMatch(a -> a.equalsIgnoreCase(canonical));
}
```

Resolving the observed string to its canonical name *before* comparing collapses
three problems into one — case, spelling variant, and true alias — and it does
something the current design cannot: it separates "the platform does not offer
this algorithm" from "the platform offers it and the rule forbids it". Those are
different verdicts that today both surface as `UnsafeAlgorithm`.

It would also make the hand-added spellings unnecessary, since the provider
resolves them.

This is recorded as a design, not built. It touches all 12 specifications and
introduces a runtime dependency on the platform's provider set, which is a larger
decision than the 9 call sites it would recover.

## What gh101 does about it

Only one thing: `AndroidCipherTransformationUtil` folds case on the algorithm,
the mode and the padding. That is a repair rather than a transcription, and it is
there because the frozen class already folds the padding and one corpus call site
(`Cipher.getInstance("AES/CBC/PKCS5PADDING")`) depends on it — a literal
transcription of the rule would have regressed it.

The nine call sites in the other specifications stay as they are, recorded here.
