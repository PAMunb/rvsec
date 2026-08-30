# gh109 task 7.3 — harness checkpoint 2, every delta attributed

**2026-08-30** · A = `f2e83ad4`, the last gh105 commit and so the pre-gh109 preimage of the set
(24 `.mop`) · B = the working tree (48 `.mop`) · 231 traces · report files
`data/gh104/evidence/harness/gh109m2-*.md` (46 files; the prefix is `gh109m2` so that
checkpoint 1's committed `s-*.md` survive beside them).

```
unchanged 196 · moved 11 · introduced 23 · removed 1
```

Thirty-five deltas, all attributed below. An unattributed delta would be a defect, not a
result. No trace raised inside a monitor on either side, and one line of the corpus is
unresolved on both sides: `MessageDigestSpec-reset.txt`'s `md.reset()`, which is the frozen
set's one real orphan — neither snapshot declares a `reset` event, as that trace's own header
records — so it is unresolved by construction and not a blind spot.

> **These counts are not the ones a first pass produced.** The first pass read
> `unchanged 193 · moved 11 · introduced 24 · removed 1`, and the two extra deltas were the
> instrument, not the set: one call was emitting two letters (F7). Five further defects were
> found and repaired in this checkpoint, three of them in the instrument, one in a trace and
> one — F8 — in the set itself, found by a code review rather than by the harness. They are the
> substance of this session and they are written out below, because a checkpoint that only
> reports counts cannot be checked.
>
> The counts above are the **fourth** run. The third read `195/10/23/1` over 229 traces, and the
> difference is not a repair to the instrument: task 8.9 landed after it and added the trace pair
> over `KeyPairGenerator.getInstance(String, Object+)`. Its conforming half is `unchanged` and
> its violating half is `moved`, which is `+1 unchanged`, `+1 moved` and the whole of the
> difference. Every number in this file is from run 4, and each was read back off the 46 report
> files rather than copied forward.

## What the checkpoint is over

Task 7.3 as written enumerates the corpus as "the 178 traces + the trace pairs added by
1.R/2.R/3.R/4.3". That enumeration stopped at 4.3 because G7 was written before the second
wave (G8) was ratified on 2026-08-28, and 8.R closes with "No harness checkpoint of its own —
G7's checkpoint 2 (task 7.3) covers G8", a sentence that is true about the *checkpoint* and
silent about the *corpus*. Every other group's `.R` task carries an explicit trace obligation;
8.R carries none. The corpus is now 231 traces and it does include G8's — see F2 and F8.

## The 35 deltas, by group

Per group: **G1 8 · G1b 2 · G2 9 · G3 7 · G4 4 · G8 5 = 35**. The tally is the sum of the six
tables below, and the six tables are the 35 non-`unchanged` rows of the 46 report files with
nothing left over — which is the assertion the checkpoint actually makes.

### G1 — the nine repairs (8)

| task | trace | what B adds |
|---|---|---|
| 1.1 (R1) | `DHGenParameterSpecSpec-exponent-not-below-prime` | `c1:DHGENPARAMETERSPEC-CONSTR-00` |
| 1.3(a) (R3) | `MessageDigestSpec-{md5,sha1,d15-md5,d15-sha1,d15-sha1-alias}` | `d1:MESSAGEDIGEST-ALG-03` |
| 1.4 (R4) | `CipherOutputStreamSpec-flush-only` | `cl:CIPHEROUTPUTSTREAM-ORDER-00` |
| 1.9 (R9) | `IvParameterSpecSpec-zero-length` | `c2:IVPARAMETERSPEC-CONSTR-02` |

R1 and R9 are `introduced`: a `condition()` with no accusing body and a constraint that could
not be violated both measured as silence before, which is what made them repairs rather than
refinements. R3's five are `moved`, each adding one code at an event that was already accused
for the ordering — the shape D-15 recorded as the one a name-only comparison loses. R4 is
`moved` for the same reason: `c1:CIPHEROUTPUTSTREAM-NOBS-00` fires on both sides and the
repair shows up only as the `cl` ordering code that a `flush` no longer satisfies.

### G1b — the consumer reads D-24 opened (2)

| task | trace | what B adds |
|---|---|---|
| 1b.1 | `KeyPairGeneratorSpec-init3-unobserved-params` | `init3:KEYPAIRGENERATOR-NOBS-00` |
| 1b.1 | `KeyPairGeneratorSpec-init4-unobserved-params` | `init4:KEYPAIRGENERATOR-NOBS-01` |

1b.2 and 1b.3 opened `KEYMANAGERFACTORY-NOBS-01` and `TRUSTMANAGERFACTORY-NOBS-01`, and
neither has a delta here. The reason is in the read itself: both branches are guarded on
`arg instanceof ManagerFactoryParameters` (`KeyManagerFactorySpec.mop:146`), and every factory
trace of the inherited corpus calls `init(null, chars)` or `init(keyStore, chars)` — the
argument is a `KeyStore` or nothing, so the branch is never entered and the accusation is
unreachable from this corpus. Their evidence is the `codes.csv` row and the ledger, not a
replay. Reaching them would need a trace that first builds a `CertPathTrustManagerParameters`
(2.9) and then hands it to `TrustManagerFactory.init` — writable, and not written here.

### G2 — the producer specifications (9)

| task | trace | what B accuses |
|---|---|---|
| 2.1 | `RSAKeyGenParameterSpecSpec-keysize-and-exponent` | `c1:RSAKEYGENPARAMETERSPEC-CONSTR-00`, `c1:RSAKEYGENPARAMETERSPEC-KEYSIZE-00` |
| 2.2 | `ECGenParameterSpecSpec-weak-curve` | `c1:ECGENPARAMETERSPEC-ALG-00` |
| 2.4 | `DSAParameterSpecSpec-short-prime` | `c1:DSAPARAMETERSPEC-CONSTR-00` |
| 2.5 | `DHParameterSpecSpec-short-modulus` | `c1:DHPARAMETERSPEC-CONSTR-00` |
| 2.6 | `MGF1ParameterSpecSpec-sha1` | `c1:MGF1PARAMETERSPEC-ALG-00` |
| 2.9 | `CertPathTrustManagerParametersSpec-unobserved-params` | `c1:CERTPATHTRUSTMANAGERPARAMETERS-NOBS-00`, `c1:PKIXPARAMETERS-NOBS-00` |
| 2.10 | `PKIXParametersSpec-unobserved-truststore` | `c1:PKIXPARAMETERS-NOBS-00` |
| 2.11 | `PKIXBuilderParametersSpec-unobserved-truststore` | `c1:PKIXBUILDERPARAMETERS-NOBS-00` |
| 2.13 | `X509EncodedKeySpecSpec-unobserved-material` | `c1:X509ENCODEDKEYSPEC-NOBS-00` |

All nine are `introduced`, which is what a new specification produces by construction: side A
has no such file, so it can accuse nothing. The second code of the 2.9 row is 2.10's site
firing inside the same chain — a `PKIXParameters` built over an unobserved store, then handed
to a `CertPathTrustManagerParameters` — and it is counted once, on the trace.

The conforming halves of 2.1, 2.2, 2.4, 2.5, 2.6, 2.7 (`OAEPParameterSpecSpec`, which reads
the `preparedMGF1` 2.6 writes), 2.12 (`TrustAnchorSpec`) and 2.13 all replayed and drew
nothing, which is their result and not their absence. 2.3 (`ECParameterSpecSpec`) and 2.8
(`KeyStoreBuilderParametersSpec`) have no trace — see "not expressible" below.

### G3 — the medium producers (7)

| task | trace | what B accuses |
|---|---|---|
| 3.1 | `AlgorithmParametersSpec-unlisted` | `get:ALGORITHMPARAMETERS-ALG-00` |
| 3.2 | `AlgorithmParameterGeneratorSpec-badsize` | `initSize:ALGORITHMPARAMETERGENERATOR-KEYSIZE-00` |
| 3.3 | `SecretKeyFactorySpec-unobserved-spec` | `gen:SECRETKEYFACTORY-NOBS-00` |
| 3.4 | `KeyFactorySpec-unobserved-spec` | `genPublic:KEYFACTORY-NOBS-01` |
| 3.6 | `DigestInputStreamSpec-forbidden-on` | `on:DIGESTINPUTSTREAM-FORB-00` |
| 3.7 | `DigestOutputStreamSpec-forbidden-on` | `on:DIGESTOUTPUTSTREAM-FORB-00` |
| 3.7 | `DigestOutputStreamSpec-unobserved-digest` | `c1:DIGESTOUTPUTSTREAM-NOBS-00` |

3.6 and 3.7 read `generatedMessageDigest`, the predicate task 1.3(b) added because
`MessageDigest.crysl:46` ensures it and the file wrote only `DIGESTED`. The two `FORB` rows
are the evidence that the write carries: a `DigestInputStream.on(false)` reaches a forbidden
site that could not have been reached before. 3.5 (`CertificateFactorySpec`) has a conforming
trace and no violating twin, because `X.509` is the only type this platform registers and a
rejected name would make `getInstance` throw and the harness measure a different one.

### G4 — the complex adjudications (4)

| task | trace | what B adds |
|---|---|---|
| 4.1 | `SSLEngineSpec-suite-outside` | `ec1:SSLENGINE-ALG-01` |
| 4.2 | `SSLParametersSpec-tlsv1` | `c3:SSLPARAMETERS-PROTO-00` |
| 4.3 | `KeyAgreementSpec-forbidden-namedsecret` | `gs3:KEYAGREEMENT-FORB-00` |
| 4.3 | `KeyAgreementSpec-nodophase` | `gs1:KEYAGREEMENT-ORDER-00` |

The two `KeyAgreementSpec` rows are `moved`: both sides raise the `KEYPAIR-ORDER-00` rows that
the chain's key-pair half drags in, and only the `KeyAgreement` codes are new.

### G8 — the second wave (5)

| task | trace | A → B |
|---|---|---|
| 8.4 | `KeyPairGeneratorSpec-rejected-algorithm` | adds `g3:KEYPAIRGENERATOR-ALG-00` |
| 8.5 | `AlgorithmParametersSpec-dh-alias-unobserved` | `—` → `init:ALGORITHMPARAMETERS-NOBS-01` |
| 8.6 | `CipherSpec-pbkdf2-direct-aes` | `i2:CIPHER-NOBS-00` → `i2:CIPHER-CONSTR-00` |
| 8.6 | `CipherSpec-pbe-chain-conforming` | `i2:CIPHER-NOBS-00` → `—` |
| 8.9 | `KeyPairGeneratorSpec-rejected-algorithm-provider` | adds `g4:KEYPAIRGENERATOR-ALG-01`, `initError:KEYPAIRGENERATOR-KEYSIZE-00`, `initError:KEYPAIRGENERATOR-ORDER-00` |

The 8.9 row is the one to read against 8.4's, one line above it. Side B of the two now reads
alike — `g4:…ALG-01` where the one-argument spelling draws `g3:…ALG-00`, and behind it the same
two residues, the `KEYSIZE` and the `ORDER` code that an `init` on an unbound object drags in.
That is the whole content of the repair: before it, side B of the arity-2 trace was *side A*, a
lone `gen:KEYPAIRGENERATOR-ORDER-00`, because `algorithm` never got bound and the three tests for
its nullity all fell through. The conforming half of the pair,
`KeyPairGeneratorSpec-provider`, is silent on **both** sides and so does not appear here at all,
which is the evidence that `g4` accuses rather than blankets. Its provenance is F8.

The single `removed` of the whole checkpoint is the `CipherSpec-pbe-chain-conforming` row, and it is the good kind: side A
drew `i2:CIPHER-NOBS-00` because no producer of the predicate existed before gh109, and side B
is silent because the PBE chain now writes it. The 8.6 pair reads together: a conforming chain
stops being accused, and a key derived by PBKDF2 and then used under a direct AES
transformation is accused for the constraint rather than for the absence.

**A structural distinction this checkpoint cannot see past.** The G8 repairs split in two.
*Differentiable here*, because the file exists in snapshot A: 8.1 `SecretKeySpecSpec`, 8.2
`MacSpec`, 8.4 and 8.9 `KeyPairGeneratorSpec`, 8.6 `CipherSpec`/`KeyStoreSpec`, and the
`SecureRandomSpec` half of 8.3. *Not differentiable by construction*: 8.3 on the three fused
`get` specifications and 8.5 on `AlgorithmParametersSpec`, whose files gh109 created — side A
has nothing to compare, so a trace gives executable evidence that the site fires and nothing
more. Isolating those two repairs would need a pre-8.x versus post-8.x comparison, which this
checkpoint is not.

**8.2 is not testable by the harness, and that is measured rather than assumed.** The task
removes `PBEWITHHMACSHA` and `PBEWITHHMACSHA-256` from `MacSpec`'s admitted list. On the host
JVM (Temurin 25.0.3) `Mac.getInstance` throws `NoSuchAlgorithmException` for both names, so a
trace naming either would fall through `TraceRunner.instantiate`'s `FALLBACKS` array —
`{PKIX, SunX509, SHA-256, AES, RSA, SHA1PRNG, HmacSHA256, PKCS12, TLS, SHA256withRSA}` — and
silently measure a `Mac` of `HmacSHA256`. The name `PBEWithHmacSHA1`, which is a real JCA
name, does resolve, which is the contrast that makes the reading unambiguous. This corroborates
the mitigation 8.2 recorded for itself.

## Item 2 — no transitory disposition survived its reason

`predicate_graph.csv`: **153 rows, dispositions 136 empty / 16 `omission` / 1 `propagation`.**
Nothing transitory is standing. Fourteen rows still contain the word TRANSITORY, and in every
one of them it is inside the narrative that explains what the disposition *was* and on what
event it retired — the row itself carries an empty disposition cell, which is what an empty
cell means: the edge is wired. The three `MessageDigestSpec` write rows (`g1`/`g2`/`g3`) are
in that set, and their reason carries the "RE-DERIVED, gh109 task 3.6 and 3.7" addendum that
1.R promised them.

`predicate_ledger.csv`: **135 rows — `wireable` 54, `producible` 50, `unread` 22,
`unmonitored-producer-side` 5, `vacuous` 2, `unreachable-composition` 2.** Rows #17/#18/#103,
which 3.R owed, are `wireable`/`producible`. All 22 `unread` carry a recorded impossibility of
the form "no rule of the catalogue REQUIRES x". The 5 `unmonitored-producer-side` are the
structural N/A adjudications of task 4.4 plus the two propagator-written ones.
`unmonitored-producer` and `unmonitored-consumer` do not occur anywhere.

The negative half of the assertion — that no write row carries an `omission` whose recorded
reason a landed consumer has since falsified — is what `gh105_predicate_graph.py --check`
computes, and it reports **153 sites, 0 findings**.

**A name-level join raises two false positives, and they must not be re-opened.**
`KeyManagerFactorySpec.match1` and `TrustManagerFactorySpec.match1` carry `omission` while
`SSLContextSpec.init` reads a predicate of the same *name*. They are told apart by object
identity: the reads bind the `KeyManager[]` / `TrustManager[]` array (`SSLContext.crysl:32-33`),
and the omission records are about the factory-bound half, which has no reader anywhere. Both
records anticipate and refute this in their own text, and the adjudication of the external
reviews already recorded the claim as refuted.

## Item 3 — the coverage matrix is complete

```
uv run python scripts/gh109_coverage_matrix.py --check --require-complete
49 rule(s): 45 covered, 3 na-platform, 1 na-value; 8 carrying an oracle-defect row   (exit 0)
```

No rule is in two states and none is in zero. The four not covered are `Cookie`,
`DSAGenParameterSpec` and `HMACParameterSpec` (`na-platform`, each with its archive-scan
evidence) and `PasswordAuthentication` (`na-value`, INV-INS-156). The master question of the
change — is everything the expert oracle covers covered by MOP? — answers *yes, or
adjudicated*, over all 49.

## Item 4 — the NOBS census is deferred, by the researcher's decision of 2026-08-30

Task 7.3 item 4 asks for the NOT_OBSERVED rate of each read D-24 opened, measured over the APK
corpus, and makes the retirement of any NOBS branch depend on that number. **The corpus does
not exist yet.** `experimento-gh104/consolidado/` is empty, and the only recent `errors.csv`
under `results/` are the two gh105 probes: 12 and 10 lines, one APK (`cryptoapp.apk`), a
pre-gh109 specification set, and the only `-NOBS-` codes in them are `CIPHER-NOBS-00` and
`SECRETKEYSPEC-NOBS-00` — neither of which is a site D-24 opened.

The four sites at issue are `KEYPAIRGENERATOR-NOBS-00` and `-01` (task 1b.1),
`KEYMANAGERFACTORY-NOBS-01` (1b.2) and `TRUSTMANAGERFACTORY-NOBS-01` (1b.3); the `-NOBS-00` of
the two factories predates the change. Asked, the researcher chose **record as deferred**:
task 7.3 closes on items 1, 2, 3 and 5, and this is the debt.

**The consequence, stated so that it is not lost.** The NOBS branches of those four sites stay
**provisional**. Nothing in the set depends on their retirement — the codes exist, the reads
are three-valued, and `-NOBS-` lines are separated from constraint lines by `codes.csv`'s
`site_kind` (INV-INS-158, task 8.7) — but the question "does this read answer NOT_OBSERVED so
often in real applications that the branch is noise?" has no measured answer. The decision
moves to the first pass of the gh104 campaign, which is where an APK corpus first exists. Set
against the whole change the debt is small and bounded: it is one number about four of the 64
`-NOBS-` codes the set now carries, and it can only retire branches, never add accusations.

## The eight findings

Three were found and repaired by the previous session of this checkpoint; four were found by
this one; the eighth came from a code review of the group that had just closed, not from the
harness at all. Every one was settled on three oracles — the rule, the live `.mop`, and, where
the verdict depends on execution, a measurement on the JVM — because the first diagnosis was
wrong in more than one of them.

Seven of the eight are defects in the **instrument or the corpus**: the checkpoint was reading
the set wrongly. F8 alone is a defect in the **set**, and its interest is that a green
checkpoint is what hid it.

### F1 — the `BigInteger` blind spot (repaired)

Four traces naming `new RSAKeyGenParameterSpec(...)` were recorded unresolved on both sides, so
they measured as clean while never running. `RSAKeyGenParameterSpecSpec.mop:63-65` declares
`args(int, BigInteger)`; `TraceRunner.literal()` turns an integer token into an `Integer`;
`fitsPointcut` types arguments by `isInstance`, and `BigInteger.isInstance(Integer)` is false,
so `match()` returned empty and the line was skipped. Task 2.1 therefore had *zero* executable
evidence — its violating trace uses `(512, 3)`, both clauses wrong, and drew nothing — and
1b.1's satisfy/not-observed pair did not separate, because both halves drew NOBS for different
reasons.

The repair admits `Integer` at a `BigInteger` position in the three places that must agree:
`fitsPointcut` (which advice runs), `fits` (which reflective constructor is chosen) and
`coerce` (the value both receive). It unblocks five pointcuts: `RSAKeyGenParameterSpec.new`,
the two `DHParameterSpec` overloads, `DSAParameterSpec.new` and `ECParameterSpec.new`. Beside
it, `bits(n)` was added — a `BigInteger` of exactly n bits — because the conforming halves of
`DHParameterSpecSpec` and `DSAParameterSpecSpec` were otherwise inexpressible: the guards read
`p.bitLength() >= 2048`, and `BigInteger.valueOf(2048)` has a bit length of 12, so any integer
literal states the violating case.

### F2 — no trace exercised G8 (repaired for 8.4/8.5/8.6; 8.2 is impossible)

The first run of this checkpoint attributed its deltas to G1, G1b, G3 and G4, and **none to
G8**. The
root cause is the planning omission described under "What the checkpoint is over": 8.R owes no
trace and 7.3's corpus enumeration was written before G8 existed. Twenty-six traces were
written to close it and two that had never replayed were retired; a further two came later with
task 8.9 (F8). So the corpus moved from **205 tracked traces to 231** — 28 written by this
checkpoint, 2 retired — and coverage of the specifications gh109 created moved from 9 to 22 of
24. The 8.9 pair does not move that last fraction: `KeyPairGeneratorSpec` is inherited, not
created by gh109, which is exactly why F8's defect could hide behind a file that already had
traces.

### F3 — objects the platform could not produce (repaired)

`PKIXParametersSpec`'s two traces raised inside the generated monitor instead of running:
`MapOfMonitor.putNode(CachedWeakReference, IIndexingTreeValue)` threw a
`NullPointerException` because the monitored object was null. `PKIXParametersSpec.mop:40-42`
keys the monitor on the returned `PKIXParameters`; measured on the JVM, `ks.load(null)`
resolves to `load(LoadStoreParameter)` and succeeds, while `new PKIXParameters(emptyPKCS12)`
throws `InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty`;
`TraceRunner.instantiate` caught it, tried a `getInstance(String)` fallback that
`PKIXParameters` does not have, and returned null. The guard that exists to stop exactly this
covered only the receiver branch, and a `new` line binds into `produced`.

The repair gives the notation two tokens the certificate-path rules need and no literal can
spell: `truststore`, the platform's own `cacerts` (144 entries here), and `anchor`, one X509
certificate out of it — chosen over a committed fixture because there is then no binary to keep
current and no expiry to chase. A third token, `psource`, is `PSource.PSpecified.DEFAULT`, the
empty OAEP label, because the real `OAEPParameterSpec` constructor throws on a null one. The
two traces that had never replayed are retired to `backup/gh109/traces/` with their reason.

### F4 — a trace whose silence was "never ran" (repaired)

`KeySpec-unobserved-origin.txt` is the separating half of the interface rule (task 2.14), and
2.R owes a satisfy/not-observed pair for that shape. It built its public key through
`CertificateFactory.generateCertificate(stream)`, and `stream` is a token this notation cannot
produce, so the call answered null and **every line after it named a receiver the platform
never produced**. Measured: on side B the two lines that matter — `cert.getPublicKey()` and
`pub.getEncoded()` — were both recorded unresolved, so `KeySpec.ge1`'s guard, the one thing the
trace exists to exercise, never ran. The trace read "the guard refused"; the truth was "the
guard never ran", which is F1's family and the failure `TraceRunner`'s own class comment says
it exists to make impossible.

Three oracles: `Key.crysl` states no CONSTRAINTS, no FORBIDDEN and an ORDER of `GetEnc*` that
refuses no sequence, so this specification has no accusation site and the pair can only be
about a predicate write; `KeySpec.mop:75-85` guards the `preparedKeyMaterial` staging on
`generatedKey`, `generatedPubkey` or `generatedPrivkey` answering SATISFIED; and on the JVM the
`cacerts` anchor is an `X509CertImpl` whose `getPublicKey()` answers an `RSAPublicKeyImpl`
with a 294-byte encoding.

The trace now binds `anchor` and calls `getPublicKey` silently — no specification of the set
monitors that call — so the single monitored line is `pub.getEncoded()`. It resolves on side B,
the guard runs, the origin is NOT_OBSERVED, nothing is staged and nothing is drawn. The
separation the pair carries is downstream and is measured: an `X509EncodedKeySpec` built over
this material is accused by 2.13's read (`X509EncodedKeySpecSpec-unobserved-material` →
`c1:X509ENCODEDKEYSPEC-NOBS-00`) and one built over `KeySpec.txt`'s material is not.

### F5 — `public` is not the same as reachable (repaired, in the instrument)

Fixing F4 exposed the reason the fix did not work at first. `TraceRunner.produce` looks a
method up on the receiver's runtime class and then re-looks it up on a public owner, because
several JCA factories hand back a package-private delegate whose `Method` cannot be made
accessible. The test it used was `Modifier.isPublic(declaringClass)`. That sees one of the two
ways a class can be out of reach.

Measured on this JVM: `sun.security.x509.X509CertImpl` — what `KeyStore.getCertificate` hands
back, and so what the `anchor` token is — is declared **public** and lives in a package
`java.base` exports to nobody. The modifier test accepted it, `setAccessible` threw
`InaccessibleObjectException`, `produce`'s catch swallowed it, and the binding silently became
null. The same is true of `sun.security.rsa.RSAPublicKeyImpl` and `RSAPrivateCrtKeyImpl`;
`com.sun.crypto.provider.DESedeKey` is package-private and the old test already handled it.

`onPublicOwner` now asks both questions — public **and** in a package the module exports
unconditionally — through a `reachable(Class)` helper, and climbs to
`java.security.cert.Certificate.getPublicKey()`, whose virtual dispatch still runs the
override's body. The corpus exercised no other line of this shape, and re-running the whole
checkpoint after the repair produced identical counts, which is the evidence that the fix
changed this trace and nothing else.

### F6 — a conforming half that did not conform (repaired)

`SecretKeyFactorySpec.txt` is the conforming half of task 3.3's pair and its header claims
"nothing is drawn". Measured, it drew `c1:PBEKEYSPEC-NOBS-01` and `gen:SECRETKEYFACTORY-NOBS-00`
— and its twin drew `gen:SECRETKEYFACTORY-NOBS-00` too, so **the pair did not separate at the
site it is about**.

The cause is the one 8.6 recorded for the first PBE pair it wrote, unrepaired in this older
trace: the salt was spelled `bytes(16)` inline. `PBEKeySpec.crysl` wants a salt randomised
under observation, so an inline array clears `conforms` through `PBEKEYSPEC-NOBS-01`,
`speccedKey` is never written, and 3.3's read then answers NOT_OBSERVED for a reason that has
nothing to do with what the pair tests. Both halves now obtain a `SecureRandom` and call
`nextBytes` on the salt, so the only difference between them is the `bind` — whether the
constructor was observed. The conforming half is now silent on both sides and the twin draws
`gen:SECRETKEYFACTORY-NOBS-00` alone.

The lesson generalises and is worth stating once: **write a trace to the rule's conforming
values, not to what makes the JVM call succeed.** A platform that accepts a call says nothing
about whether the specification accepts it.

### F7 — one call, two letters (repaired, in the instrument)

`AlgorithmParameterGeneratorSpec.txt` replays the sequence the rule's ORDER states —
`get`, `init(2048)`, `generateParameters()` — and its header says nothing is drawn. Measured,
it drew `initSpec:ALGORITHMPARAMETERGENERATOR-ORDER-00` and
`gen:ALGORITHMPARAMETERGENERATOR-ORDER-00`, and its violating twin drew both of those beside
the `KEYSIZE` code its header predicted.

The specification is right: `init(int)` is `initSize`, `init(java.security.spec.AlgorithmParameterSpec)`
is `initSpec`, and the `ere` accepts `get initSize gen`. The instrument was wrong.
`TraceRunner.resolve` takes a *simple* name — it consults the generated monitor's import list,
then tries five packages — and a pointcut may spell its parameter type out in full, which
`jca_android` does ten times. A qualified name matched no import and no `java.security.` +
name candidate, so the type resolved to null, and `fitsPointcut` treats a type it cannot
resolve as admitting anything. `apg.init(2048)` therefore matched **both** `init` pointcuts:
one call emitted two letters, and the automaton refused a sequence the rule accepts.

`resolve` now tries a name containing a dot as it stands. The blast radius is exactly the
ambiguity that arity does not already separate: of the ten qualified positions, only
`AlgorithmParameterGenerator.init` has two same-arity overloads. After the repair the
conforming trace is silent and the violating one draws `initSize:KEYSIZE-00` alone — each
header's own claim, restored. This is the delta between the first pass's
`193/11/24/1` and the numbers at the top of this file.

Note the direction. F1 and F4 are false negatives: a line does not run and the trace reads as
clean. F7 is a false positive: an extra letter and an ORDER accusation the woven application
could never raise, because AspectJ types the call statically and the harness types it by value.
A differential harness can be wrong in both directions and only one of them looks like a bug.

### F8 — the arity the corpus never spelled (repaired, in the set)

The seven above were found by reading harness output. F8 was not, and that is the point of
recording it here: after this checkpoint had gone green over G8, `/rv-code-reviewer` was run over
the group (task 7.6) and found that task 8.4 had closed the clause of `KeyPairGenerator.crysl:28`
at **one arity only**. `g3`, the negated twin 8.4 added, has a one-argument pointcut; the
two-argument overload `getInstance(String, Object+)` is `g2`, whose `matches(...)` guard is
**positive**. So `getInstance("Ed25519", provider)` — a rejected algorithm named at the arity that
also names a provider — matched **no event at all**.

The cost is larger than one missing report, and this is why the fiche calls it a repair rather
than a register-only note. `algorithm` is the field `init1`, `init2`, `initError` and
`initError2` all test for null. An object that enters through the unmatched overload therefore
goes on **unbound**, and the specification stays silent for it *entirely* — where the
one-argument spelling of the same misuse draws three codes. The measurement is the G8 table
above: side A of `KeyPairGeneratorSpec-rejected-algorithm-provider` is a lone
`gen:KEYPAIRGENERATOR-ORDER-00`, and side B is 8.4's full shape.

**Why the harness could not have found it.** A differential harness compares two snapshots over
a fixed corpus; it is blind to a misuse the corpus does not spell. No trace of the 229 named the
two-argument overload with a rejected algorithm — `KeyPairGeneratorSpec-rejected-algorithm` uses
the one-argument form — so there was nothing for either side to answer differently about, and
checkpoint 2 was green over the gap for as long as the gap was unwritten. Writing the pair is
what turned the finding into a delta. The general form is worth keeping: **a differential
checkpoint measures the repairs, not the coverage of the corpus that measures them**, and the
`gh109_coverage_matrix.py` obligations plus a reading of the rules are what cover the second.

The repair, ratified by the researcher on 2026-08-30 (D-26.2 addendum), adds event `g4` in the
shape D-26.1 gave `SecureRandomSpec.g5`, binding `algorithm` exactly as `g3` does — so the two
arities answer alike and drag the same two residues — with the `ere` prefix becoming
`((g3 | g4)* g1 | (g3 | g4)* g2)`. It ripples into all five record families, which is finding 8
of the "Learnings" and is the reason five of the six reactor pins in the battery below were
already stale before 8.9 touched anything.

## What was deliberately left undone, with the measured reason

- **`ECParameterSpecSpec` (2.3) and `KeyStoreBuilderParametersSpec` (2.8)** — no trace. They
  need an `EllipticCurve` plus an `ECPoint`, and a `KeyStore.Builder`. Neither `c1` reads a
  predicate, so the whole content of either is the automaton and the `@match` write: high cost,
  no accusation to separate.
- **The conforming half of `PKIXParameters` / `PKIXBuilderParameters`** — not expressible. It
  needs a key store that both (a) holds a trusted entry, or the constructor throws, and (b) was
  observed being loaded, or `KeyStoreSpec` writes no `generatedKeyStore`. The notation cannot
  give both: `truststore` satisfies (a) but arrives without an observed `getInstance`, so its
  `load` falls outside the automaton and draws `KEYSTORE-ORDER-00`; and a store from an
  observed `getInstance` is empty, because **a trace line with no binding never reaches the
  platform** — only `-> name` and `bind` lines invoke the real API, so no trace can mutate real
  object state. The reason is written inside
  `PKIXBuilderParametersSpec-unobserved-truststore.txt`.
- **Task 8.2's repair** — untestable on this JVM; see the G8 section.
- **No JUnit test for the four `TraceRunner` extensions.** The suite's control monitor is the
  frozen `jca` (`TraceRunnerTest.DEFAULT_MONITOR_DIR`), and `jca` declares no `BigInteger`
  pointcut, no certificate-path pointcut and no qualified parameter type — a test over it would
  be permanently skipped, which is the same false green this whole checkpoint exists to kill.
  The evidence is the harness run. If a permanent guard is wanted, its shape is a gate over the
  `## Lines no pointcut resolved` sections of the reports, failing on any line unresolved on
  **both** sides that no record excuses.

## A limit of the instrument that remains

`fitsPointcut` admits any argument at a position whose declared type it cannot resolve. F7
removed the common cause of an unresolvable type; the permissive fallback itself is unchanged,
because making it strict would turn every genuinely unloadable type — an Android-only class,
say — into an unresolved line across the corpus, and that is a change to measure on its own
rather than to slip into a checkpoint. It is recorded here so that the next reader of a
surprising `moved` row asks this question early.

Two smaller things were fixed in the reporting itself while this was being read:
`gh104_diff_harness.py` now labels each unresolved line `(A)` or `(B)`, the way it already
labelled envelopes. A merged list read alike whether a line failed on one snapshot — the
ordinary case, when the specification exists only on one side — or on both, which is the only
shape that means "never replayed at all". Reading that distinction is what found F4.

## The battery, for the record

| instrument | result |
|---|---|
| `gh104_divergence_record.py --check` | 324 hunks, all recorded; 48 narrative entries |
| `gh104_message_gate.py` | `ok: true`, no skips |
| `gh105_predicate_graph.py --sets jca_android` | 48 files, 153 sites, 0 findings |
| `gh105_expert_ledger.py --check` | exit 0; 135 clauses |
| `gh105_expert_alphabet.py --check` | exit 0 |
| `gh105_sole_oracle_gate.py` | 75 files read, 0 findings, 12 skipped |
| `gh109_coverage_matrix.py --check --require-complete` | 49/49, exit 0 |
| `gh105_spec_gates.py --sets jca_android` | G-SIG 223/0 (3 skipped, 8 notes), G-FORB 5/0, G-BIND 204/0 (3 allow-listed) |
| `gh105_order_gate.py --sets jca_android` | 38 passed, 0 failed, 8 allow-listed, 2 skipped of 48 |
| `tests/parity` | 218 passed, 0 failed, 5m37s |
| reactor `rvsec-crysl` core/crysl/mop | 171 + 102 + 59, 0 failures (1 skipped, the CI-excluded tag) |
| generator ceiling (INV-INS-154) | 17 events at `CipherSpec`, which is the ceiling; the largest specification gh109 created is `KeyAgreementSpec` at 9 |

G-SIG and G-BIND each read one higher than they did at run 3 (222 and 203): `g4` is one more
signature to check and one more binding to check, and nothing else moved.

**The reactor row is not a formality, and it is the one that nearly went unread.** Six pins were
re-measured, and **five of them were stale before task 8.9 touched anything** — G8 had moved them
and no gh109 task after 7.1 runs the Maven tests, so `tests/parity` stayed green over the drift
for the whole second wave. Each pin carries its reason in the test file, in the convention those
tests already use ("the repair re-measures and re-pins here rather than the pin being loosened"):

| pin | move | cause |
|---|---|---|
| `MopLiftCorpusTest` aggregate events | 973 → 975 | 8.3's `g5`, then 8.9's `g4` |
| `MopLiftCorpusTest` provenance checks | 974 → 975 | the same census, second assertion |
| `MopLiftCorpusTest` overlap refusals | 57 → 58 | every negated twin costs one refusal |
| `M4PredicateCorpusTest` sites (×2 assertions) | 146 → 148 | 8.1's `speccedKey` write + 8.6's second probe |
| `M4PredicateCorpusTest` edges / absences | 105 → 107, 40 → 39 | the same two sites |
| `M4PredicateCorpusTest` rows / derived / fraction | 175 → 176, 145 → 146, 0.829 → 0.830 | +2 sites − 1 absence |

Only the first and third are 8.9's; the rest are G8 debt that running the tests is the only way
to find. One parity pin moved with 8.9 as well and was re-measured in place:
`test_an_absorbed_accuser_is_erased_from_both_languages` asserted `exempt == {"g3"}` and now
asserts `{"g3", "g4"}` — `g4` is erased for exactly `g3`'s reason, so the erased language does
not move and `(g1|g2)(inits)gen` still matches `Gets, Inits, Generators`. That is the fifth
record family a `.mop` edit ripples into, and it is the one no gate names.

`gh105_spec_gates.py` reads class presence from `android.jar`'s own zip entries and asks
`javap` only about members of classes the zip has already confirmed, which is the split
INV-INS-154 requires and the reason the gate does not greenlight `HMACParameterSpec`.
