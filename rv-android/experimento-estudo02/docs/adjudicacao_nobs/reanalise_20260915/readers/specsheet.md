# Spec sheet — the 22 NOBS codes that occurred in the campaign (jca_android)

Read-only investigation, 2026-09-14. Every claim below cites a file:line in one of these sources.

Abbreviations: `R` = `rvsec/rvsec-mop/src/main/resources/jca_android/` (the spec set);
`S` = `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/` (the store package);
`G` = `rvsec-dataset/jca_android/instrument_results/instrument_00/instrument_00/monitors/` (the generated monitor the campaign ran).
All paths are under `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/`.

## 0. Provenance checks

- `G/specification_set.txt` = `jca_android`. `G/mop/` holds only `Coverage.java` and `MonitorWrappers.java` (the dexlib2 wrapper emitter output), not the `.mop` sources; so the campaign set was tied to `R` by content, not by diff:
  - all 22 codes occur exactly once in `G/MultiSpec_1RuntimeMonitor.java` (`grep -c "code=<CODE> "` = 1 for each) and zero times in the `.aj` (bodies live in the monitor class, the aspect only dispatches);
  - the generated bodies of `SecretKeySpecSpecMonitor` (`G/…RuntimeMonitor.java:15101-15175`) and `TrustManagerFactorySpecMonitor` (`:16452-16519`) are line-for-line the bodies of `R/SecretKeySpecSpec.mop:97-125,255-258` and `R/TrustManagerFactorySpec.mop:118-173,254-259`, with `__LOC` expanded to `ViolationRecorder.getLineOfCode()` and `__EVENTNAME` to the literal event name.
- `R/codes.csv` `file_line` points at the `ErrorCollector.instance().addError(` line; the `code=` string is on the next line. All 22 rows checked against the files (e.g. `CipherSpec.mop:231` → addError, `:232` → `code=CIPHER-NOBS-00`).
- Generated monitor timestamps: `.aj`/`.java` 2026-09-05; `.mop` sources last modified 2026-08-26..08-30; `codes.csv` 2026-08-30. Nothing in `R` postdates the monitor.

## 1. Store semantics (`S/PredicateStore.java`)

| Call | bound == null | entry absent | entry `negated` | tuples empty | tuple match |
|---|---|---|---|---|---|
| `validate(p, bound, values…)` `:342-362` | `NOT_OBSERVED` (:343-345) | `NOT_OBSERVED` (:348-350) | `VIOLATED` (:353-355) | `NOT_OBSERVED` (:356-358) | `SATISFIED` if the exact value tuple was recorded, else `VIOLATED` (:359-361) |
| `validateAny(p, bound)` `:395-412` | `NOT_OBSERVED` | `NOT_OBSERVED` | `VIOLATED` | `NOT_OBSERVED` | `SATISFIED` for any tuple (:409-411) |
| `validateAbsent(p, bound, …)` `:438-452` | `SATISFIED` | `SATISFIED` | `SATISFIED` | `SATISFIED` | `VIOLATED` — never `NOT_OBSERVED` |
| `ensure(p, bound, values…)` `:291-306` | no-op (:292-294) | creates entry, adds tuple (idempotent per (property, identity, values)) | reinstates (`withTuple` sets `negated=false`, :119-123) | — | — |
| `negate(p, bound)` `:320-329` | no-op | creates entry in `NEGATED` state | — | — | — |

Keying facts that matter for the codes below:
- Bound object is compared by **identity** through a weak key (`BoundKey`, :222-251). A fresh array/object with equal content is a different key. `getEncoded()` clones (`R/SecretKeySpec.mop:34-39`), `getKeyManagers()`/`getTrustManagers()` allocate a fresh array per call (`R/SSLContextSpec.mop:199-202`), `KeyStore.getKey` returns a fresh key object (`R/KeyStoreSpec.mop:180-184`).
- Value positions: `String` compared lower-cased, `Integer` by `toString`, everything else by identity (`ValueKey`, :162-213). A one-place `ensure` records the **empty** tuple; a two-place `validate` against it answers `VIOLATED`, not `NOT_OBSERVED` (`R/KeyStoreSpec.mop:169-178`).
- No wildcard on the write side: `ensure(p, key)` and `ensure(p, key, alg)` are two tuples; `validateAny` is the only reader that ignores values.
- `VIOLATED` is reachable only through `negate` (one live site: `R/PBEKeySpecSpec.mop:186`) or a value mismatch on a multi-place read. For every one of the 22 codes the `VIOLATED` sibling (`-CONSTR-`) is what fires instead of the NOBS when that happens; the NOBS is exclusively the "no entry / empty tuples / null bound" answer.

## 2. JavaMOP semantics relied on, verified in `G/MultiSpec_1RuntimeMonitor.java`

**(a) The event body runs before the transition is decided, in every state, and regardless of the outcome.** Generated `SecretKeySpecSpecMonitor.Prop_1_event_c1` (`G/…:15101-15127`):

```java
final boolean Prop_1_event_c1(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
    {   // <-- the .mop event body, verbatim
        boolean conforms = true;
        if (!ConscryptAliasTable.matches("SecretKeySpec", keyAlgorithm, algorithms)) { … SECRETKEYSPEC-ALG-00 …; conforms = false; }
        PredicateVerdict preparedMaterial = PredicateStore.instance().validate(Property.PREPARED_KEY_MATERIAL, keyMaterial);
        if (preparedMaterial == PredicateVerdict.VIOLATED) { … SECRETKEYSPEC-CONSTR-00 …; conforms = false; }
        else if (preparedMaterial == PredicateVerdict.NOT_OBSERVED) { … SECRETKEYSPEC-NOBS-00 …; conforms = false; }
        if (conforms) { spec = secretKeySpec; specAlgorithm = keyAlgorithm; }
    }
    int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;      // {1, 2, 2}: start->match, else fail
    this.SecretKeySpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
    this.SecretKeySpecSpecMonitor_Prop_1_Category_match = nextstate == 1;
    return true;
}
```

The only thing that runs *before* the body is a `condition(...)` clause, compiled as `if ( ! (guard) ) { return false; }` ahead of the body **and** of `handleEvent` (see `TrustManagerFactorySpecMonitor.Prop_1_event_g2`, `G/…:16435-16450`). None of the 22 NOBS reads sits behind a `condition`; all are in bodies.

**(b) A `@match`/`@fail` handler runs only after `handleEvent`, only when the category computed from `nextstate` holds, and in the same dispatcher call.** Static dispatcher `SecretKeySpecSpec_c1Event` (`G/…:26313-26320`):

```java
matchedEntry.Prop_1_event_c1(keyMaterial, keyAlgorithm, secretKeySpec);
if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail)  { matchedEntryfinalMonitor.Prop_1_handler_fail(); }
if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) { matchedEntryfinalMonitor.Prop_1_handler_match(); }
```

and for `TrustManagerFactorySpec_initEvent` (`G/…:28122-28131`) the same shape with `match2`, `fail`, `match1` in that order. The handler is a no-argument method that sees only monitor fields (`Prop_1_handler_match`, `G/…:15169-15175`: `ensure(GENERATED_KEY, spec, specAlgorithm); ensure(SPECCED_KEY, spec);`), which is why every acceptance-point producer stages its object in a field inside the body.

**(c) A monitor is created on first event, in state 0 (`start`), by `FindOrCreateEntry`** (`G/…:26295-26311`). An event whose transition row sends state 0 to `fail` still runs its body first (consequence of (a)); its `@fail` then runs, and every `@fail` of the set does `__RESET` (→ `this.reset()`, e.g. `G/…:15161-15167`), clearing staged fields.

**(d) Advice kind per emitting event** (from `G/MultiSpec_1MonitorAspect.aj`; matters for whether a NOBS is emitted when the JCA call itself throws):

| event | advice | consequence |
|---|---|---|
| `CipherSpec.i2` (`.aj:232`), `IvChainJunctionSpec.use` (`:227`), `MacSpec.i1` (`:157`), `SignatureSpec.i4` (`:127`), `KeyManagerFactorySpec.init` (`:182`), `TrustManagerFactorySpec.init` (`:117`), `SecureRandomSpec.next2` (`:147`) | `before` | body (and NOBS) runs even if the call then throws |
| `KeyAgreementSpec.dophase` (`:575`), `SSLContextSpec.init` (`:907`), `SecureRandomSpec.setSeed2` (`:1020`) | `after` (no `returning`) = after-finally under ajc (`R/MacSpec.mop:219-221`) | ajc: NOBS also on a throwing call; dexlib2: advice skipped when the call throws (memory note "Divergência after() dexlib2×ajc") |
| `GCMParameterSpecSpec.c1/c2`, `IvParameterSpecSpec.c1`, `PBEKeySpecSpec.c1`, `SecretKeySpecSpec.c1/c2`, `X509EncodedKeySpecSpec.c1`, `SecureRandomSpec.c2`, `KeyFactorySpec.genPublic`, `SecretKeyFactorySpec.gen` | `after … returning` | no body, no NOBS, when the constructor/call throws |

## 3. Producer table — every `ensure(`/`negate(` in the set, grouped by Property

Only the properties read by one of the 22 codes are expanded; the rest are listed at the end for completeness. "Guard" says under what condition the write actually happens, taking §2 into account.

### `PREPARED_KEY_MATERIAL` (read by SECRETKEYSPEC-NOBS-00/01, X509ENCODEDKEYSPEC-NOBS-00)
| site | event / placement | object marked | guard |
|---|---|---|---|
| `R/KeySpec.mop:105` | `@match` after `ge1` = `call(public byte[] Key+.getEncoded())` (`:75-77`); `ere : ge1*` never fails, so `@match` runs after every call | the **returned clone** (`stagedKeyMaterial = material`, `:83`) | staged only if `originObserved` (`:78-81`): `validate(GENERATED_KEY, k, k.getAlgorithm()) == SATISFIED` **or** `validate(GENERATED_PUBLIC_KEY, k) == SATISFIED` **or** `validate(GENERATED_PRIVATE_KEY, k) == SATISFIED`. Explicitly a MOP-more-restrictive divergence vs `Key.crysl` (`:51-69`). |
| `R/SecretKeySpec.mop:145` | `@match` after `e1` = `call(public byte[] SecretKey+.getEncoded())` (`:119-121`); `ere : e1*` | the returned clone | staged only if `validate(GENERATED_KEY, secretKey, secretKey.getAlgorithm()) == SATISFIED` (`:122-126`) — a two-place read, so the key must carry the tuple written by one of the three `GENERATED_KEY` producers with a value equal (case-insensitively) to `key.getAlgorithm()`. |
| `R/KeyAgreementSpec.mop:298` | body of `gs1` = `after(...) returning(byte[] sharedSecretBuffer)` on `generateSecret()` (`:294-296`) | the returned array | `if (conforms)` (`:297`): monitor field, `true` at construction, set `false` by any accusing read at `get`/`init1..4`/`dophase` and by `gs3`, reset only in `@fail` (`:385`). The body runs even when the automaton is in a state where `gs1` fails (§2a). |
| `R/KeyAgreementSpec.mop:315` | body of `gs2` on `generateSecret(byte[], int)` (`:311-313`) | the **argument** array | `if (conforms)` |

No other producer. In particular nothing marks `Cipher.unwrap` output, `KeyAgreement.generateSecret(String)` (forbidden, `gs3`), `Key.getEncoded()` on a key of unobserved origin, or any bytes read from storage/network.

### `RANDOMIZED` (read by IVPARAMETERSPEC-NOBS-00, GCMPARAMETERSPEC-NOBS-00/01, PBEKEYSPEC-NOBS-01, SECURERANDOM-NOBS-00/01, SSLCONTEXT-NOBS-02, and indirectly IVCHAINJUNCTION-NOBS-00/01)
| site | placement | object marked | guard |
|---|---|---|---|
| `R/SecureRandomSpec.mop:384` | `@match1` = alias of state `init` (`:365`) | field `sr` = the **SecureRandom object** | `sr` is bound by the bodies of `c1` (`:69`), `c2` (`:98`, **before** the seed read, so a badly seeded SR is still credited), `g1` (`:117`), `g2` (`:126`), `g3` (`:132`). `g1`/`g2` carry `condition(matches(alg, algorithms))` in the pointcut (`:116`, `:125`); an unsafe algorithm dispatches `g4`/`g5` instead, which bind nothing and self-loop at `start` (`:336-337`), so that SecureRandom is **never** `RANDOMIZED`. `ensure(null)` is a no-op. |
| `R/SecureRandomSpec.mop:394` | `@match2` = alias of `end` (`:368`) | `stagedGeneratedSeed` = array **returned** by `generateSeed(int)` (staged in `genSeed` body, `:250`) | the transition must be accepted (`init→end` or `end→end`); from `start` (`generateSeed` on an SR whose `Ins` was not observed) `@fail` clears the field (`:373`). |
| `R/SecureRandomSpec.mop:398` | `@match2` | `stagedNextBytes` = the **argument** array of `nextBytes(byte[])` (staged in `next2`'s `before` body, `:293`) | same: generated row `Prop_1_transition_next2[] = {3, 1, 1, 3}` (`G/…:15271`) with `fail = nextstate==3` → `nextBytes` on an SR at `start` fails, `@fail` sets `stagedNextBytes = null` (`:374`), array not marked (and SECURERANDOM-ORDER-00 is emitted). |

No `RANDOMIZED` producer marks an `int`, a `long`, a `char[]`, an `IntStream`, or any array not passed to `nextBytes`/returned by `generateSeed` of an **observed, admitted** SecureRandom.

### `PREPARED_IV` (read by IVCHAINJUNCTION-NOBS-00)
| `R/IvParameterSpec.mop:153` | `@match` (`ere : c1 | c2`, always accepted at the first event, `:135`) | field `spec` = the constructed `IvParameterSpec` | `spec` is bound **only** on the `else` branch of `c1` (`:77-79`: `RANDOMIZED[iv] == SATISFIED`) or, in `c2`, when `SATISFIED && len > 0 && offset >= 0 && iv.length >= offset+len` (`:126-132`). NOT_OBSERVED does not prepare (`:54-64`, decision recorded). |

### `PREPARED_GCM` (read by IVCHAINJUNCTION-NOBS-01)
| `R/GCMParameterSpecSpec.mop:180` | `@match` | field `spec` | bound only `if (conforms)` (`:82-84`, `:136-138`): `tagLen ∈ {96,104,112,120,128}` **and** `RANDOMIZED[src] == SATISFIED`. |

### `SPECCED_KEY` (read by KEYFACTORY-NOBS-01, SECRETKEYFACTORY-NOBS-00; all readers use `validateAny`)
| site | placement | object | guard |
|---|---|---|---|
| `R/PBEKeySpecSpec.mop:160` | body of `c1` (`after … returning`), arity 2 `(s, keyLength)` | the constructed `PBEKeySpec` | `if (conforms)` (`:159`): `iterationCount >= 10000` (`:121-125`) **and** `RANDOMIZED[salt] == SATISFIED` (`:148-158`). |
| `R/PBEKeySpecSpec.mop:186` | body of `c2` = `clearPassword()` | `negate(SPECCED_KEY, s)` | unconditional — the only `negate` in the set; a later read answers `VIOLATED`, i.e. the `-CONSTR-` sibling, not the NOBS. |
| `R/SecretKeySpecSpec.mop:257` | `@match` (arity 1) | the constructed `SecretKeySpec` | `spec` bound only `if (conforms)` (`:121-124`, `:187-190`): algorithm ∈ list **and** `PREPARED_KEY_MATERIAL[keyMaterial] == SATISFIED`. |
| `R/X509EncodedKeySpecSpec.mop:83` | `@match` (arity 1) | the constructed `X509EncodedKeySpec` | `spec` bound only on the `else` branch of `c1` (`:52-54`): `PREPARED_KEY_MATERIAL[encodedKey] == SATISFIED`. |

No spec exists for `PKCS8EncodedKeySpec`, `RSAPublicKeySpec`, `RSAPrivateKeySpec`, `ECPublicKeySpec`, `ECPrivateKeySpec`, `DHPublicKeySpec`, `DESKeySpec`, `DESedeKeySpec` (grep over `R/*.mop` for those names returns no `call(`).

### `GENERATED_KEY` (read by CIPHER-NOBS-00 via two two-place `validate`s, MAC-NOBS-00 via `validateAny`; also by the two `getEncoded` bridges above)
| site | placement | object / value | guard |
|---|---|---|---|
| `R/KeyGeneratorSpec.mop:223` | `@match` (only `gk1` reaches it, `:187-190`) | `generatedKey` = returned `SecretKey`; value `canonical("KeyGenerator", <string given to getInstance>)` | sequence accepted: `(g3* g1+ | g3* g2+) (init… gk1 | gk1)` (`:175`). `g1`/`g2` have `condition(matches(alg, safeAlgorithms))` (`:62`, `:69`); an unsafe algorithm only ever emits `g3`, after which `gk1` fails → key **not** marked (in addition to KEYGENERATOR-ALG-00 and -ORDER-00). A second `generateKey()` on the same generator fails → second key not marked (`:192-196`). |
| `R/KeyStoreSpec.mop:200` | `@match` | `generatedKey` = key returned by `getKey(String, char[])` (staged in `gk1` body, `:121`); value `generatedKey.getAlgorithm()` | sequence accepted: `(g2* (g1 | g3) load ((ge1 gk1 | gk1) | (se1 store))*)+` (`:124`). Needs an observed `getInstance(String[,…])` with an admitted type **and** an observed `load(..)`. The `File`-based `getInstance` overloads are not pointcut (`:76-79`). |
| `R/SecretKeyFactorySpec.mop:108` | body of `gen` (`after … returning`) | returned `SecretKey`; value `canonical("SecretKeyFactory", alg)` | `if (conforms)` (`:107`): `validateAny(SPECCED_KEY, keySpec)` neither `VIOLATED` nor `NOT_OBSERVED`. |
| `R/SecretKeyFactorySpec.mop:122` | body of `translate` | returned key; value canonical alg | unconditional. |
| `R/SecretKeySpecSpec.mop:256` | `@match` | the constructed `SecretKeySpec`; value `keyAlgorithm` as given to the constructor | `spec` bound only `if (conforms)` — see `SPECCED_KEY` row. |

### `GENERATED_PUBLIC_KEY` (read by KEYAGREEMENT-NOBS-08, SIGNATURE-NOBS-02, CIPHER-NOBS-00's composite)
| `R/KeyFactorySpec.mop:117` | body of `genPublic` (`after … returning`) | returned `PublicKey` | `if (conforms)` (`:116`): `validateAny(SPECCED_KEY, keySpec) == SATISFIED`. |
| `R/KeyPairSpec.mop:126` | body of `gpu` = `KeyPair.getPublic()` | returned `PublicKey` | **unconditional**; runs even when the pair's monitor is at `start` (pairs from `generateKeyPair()` never see `c1`), by design (`:105-119`). |

### `GENERATED_PRIVATE_KEY` (read by CIPHER-NOBS-00's composite; not by any of the 22 directly)
`R/KeyFactorySpec.mop:91` (body, `if (conforms)`), `R/KeyPairSpec.mop:146` (body, unconditional), `R/KeyStoreSpec.mop:202` (`@match`, `instanceof PrivateKey`).

### `GENERATED_KEY_STORE` (read by KEYMANAGERFACTORY-NOBS-00, TRUSTMANAGERFACTORY-NOBS-00)
| `R/KeyStoreSpec.mop:196` | `@match` | `loadedKeyStore` = the target of `load(..)` (staged in `load`'s `before` body, `:99`) | `load` must be accepted: preceded by `g1`/`g3` (admitted type) on the same object. `g2` (rejected type) → `load` fails → not marked. A `KeyStore` obtained by `getInstance(File, …)` or inside un-woven code → `load` from `start` → fail → not marked. |

### `GENERATED_KEY_MANAGERS` (read by SSLCONTEXT-NOBS-00)
| `R/KeyManagerFactorySpec.mop:176` | body of `gkm1` = `getKeyManagers()` | the **returned `KeyManager[]` array** (bound object, not spread) | **unconditional**; body runs before the transition, so it is marked even from `start` (row `{4,4,4,2,4}`, `:167`). |
| `R/KeyManagerFactorySpec.mop:220` | `@match1` (state `final`, after `init`) | the **factory** | `initialisedFactory != null`; read by no one (`:215-217`). |

### `GENERATED_TRUST_MANAGER` (read by SSLCONTEXT-NOBS-01)
| `R/TrustManagerFactorySpec.mop:218` | body of `gtm1` = `getTrustManagers()` (generated `G/…:16483-16486`) | the **returned `TrustManager[]` array** | unconditional; same reasoning. |
| `R/TrustManagerFactorySpec.mop:256` | `@match1` (state `final`) | the factory | read by no one. |

Note `Property.GENERATED_TRUST_MANAGERS` (plural, `S/Property.java:108`) has no live producer or consumer; the array edge runs through the singular constant (`S/Property.java:80-96`).

### Properties not read by any of the 22 (listed for completeness)
`ENCRYPTED` (`R/CipherSpec.mop:513,521`), `GENERATED_CIPHER` (`:533`), `MACED` (`R/MacSpec.mop:501,505`), `PREPARED_ALG` (3 sites), `PREPARED_DH/DSA/EC/MGF1/OAEP/PBE/HMAC/RSA`, `GENERATED_MANAGER_FACTORY_PARAMETERS` (`R/KeyStoreBuilderParametersSpec.mop:78`, `R/CertPathTrustManagerParametersSpec.mop:82`), `GENERATED_CERT_PATH_PARAMETERS`, `GENERATED_TRUST_ANCHOR`, `GENERATED_CERT`, `GENERATED_KEY_FACTORY`, `GENERATED_MESSAGE_DIGEST`, `DIGESTED*`, `GENERATED_KEY_PAIR` (`R/KeyPairGeneratorSpec.mop:397` — on the `KeyPair`, never on its halves), `GENERATE_SSL_CONTEXT/ENGINE`, `GENERATED_SSL_PARAMETERS`, `SIGNED`, `VERIFIED`.

## 4. Per-code sheet

Format: (1) emitting event + pointcut; (2) the read; (3) null behaviour; (4) producers (→ §3); (5) cascade; (6) notes.

### CIPHER-NOBS-00 — `R/CipherSpec.mop:231-232`, event `i2`
1. `event i2 before(int mode, Key key, Cipher c): call(public void Cipher.init(int, Key,..)) && args(mode, key, ..) && target(c)` (`:168-171`). Covers every `init` overload whose 2nd arg is a `Key` (2-, 3- and 4-argument), both modes.
2. Composite read (`:199-225`): `validate(GENERATED_KEY, key, CipherTransformationNormalizer.keyAlgorithm(c.getAlgorithm()))`, `validate(GENERATED_KEY, key, alg(c.getAlgorithm()))`, `validate(GENERATED_PUBLIC_KEY, key)`, `validate(GENERATED_PRIVATE_KEY, key)`. NOBS iff none is `SATISFIED` and none is `VIOLATED`. A `GENERATED_KEY` entry whose value equals neither the family nor the letter spelling gives `VIOLATED` → CIPHER-CONSTR-00, not NOBS.
3. `key == null` → all four `NOT_OBSERVED` → NOBS-00 is emitted, then the JCA throws `InvalidKeyException` (before advice). No spec-level null guard.
4. `GENERATED_KEY`: KeyGeneratorSpec `@match`, KeyStoreSpec `@match`, SecretKeyFactorySpec `gen`/`translate`, SecretKeySpecSpec `@match`. `GENERATED_PUBLIC_KEY`: KeyFactorySpec `genPublic`, KeyPairSpec `gpu`. `GENERATED_PRIVATE_KEY`: KeyFactorySpec `genPrivate`, KeyPairSpec `gpr`, KeyStoreSpec `@match`.
5. Upstream causes: SECRETKEYSPEC-NOBS-00/01 (spec not credited → no `GENERATED_KEY`); SECRETKEYFACTORY-NOBS-00 (`conforms=false` → no write at `:108`); KEYFACTORY-NOBS-00/01; KEYGENERATOR unsafe alg or double `generateKey()`; KeyStore chain not accepted; `Cipher.unwrap` output; key from un-woven code. Downstream: **none among the 22** — `initialisedCipher = c` is set unconditionally (`:238`), so `GENERATED_CIPHER` is still written at `@match3` and the stream specs are unaffected; the `ENCRYPTED` writes are unaffected. Co-occurs with IVCHAINJUNCTION-NOBS-00/01 on the same call when both key and params are unobserved.
6. i2 is `before`, so a `Cipher.init` that the platform rejects (`InvalidKeyException`) still draws the NOBS.

### GCMPARAMETERSPEC-NOBS-00 — `R/GCMParameterSpecSpec.mop:78-79`, event `c1`
1. `event c1 after(int tagLen, byte[] src) returning(GCMParameterSpec s): call(public GCMParameterSpec.new(int, byte[])) && args(tagLen, src)` (`:62-64`).
2. `validate(RANDOMIZED, src)` (`:71`), one place, on the **argument array**.
3. `src == null` → constructor throws `IllegalArgumentException` → `after returning` does not run → no report.
4. `RANDOMIZED` on arrays: only `SecureRandomSpec.@match2` (`nextBytes` argument / `generateSeed` return) of an observed, admitted, non-failed SecureRandom.
5. Upstream: SecureRandom unobserved / unsafe algorithm / `nextBytes` from `start`; IV received (decrypt), derived, copied (`Arrays.copyOf`, `System.arraycopy`, `ByteBuffer` slices), from `Cipher.getIV()`. Downstream: `conforms=false` → `spec` unbound → `PREPARED_GCM` never written → **IVCHAINJUNCTION-NOBS-01** at `Cipher.init` in **either** mode (§ IVCHAINJUNCTION-NOBS-01).
6. Runs regardless of the mode the spec will be used in; the constructor cannot know it.

### GCMPARAMETERSPEC-NOBS-01 — `R/GCMParameterSpecSpec.mop:132-133`, event `c2`
1. `event c2 after(int tagLen, byte[] src, int offset, int len) returning(GCMParameterSpec s): call(public GCMParameterSpec.new(int, byte[], int, int)) && args(tagLen, src, offset, len)` (`:116-118`).
2. `validate(RANDOMIZED, src)` (`:125`) on the whole argument array (not on the window).
3.–5. As NOBS-00. Note the rule's `len > 0` is reachable (`(128, iv, 0, 0)` returns, `:103-110`) and is deliberately not coded.

### IVCHAINJUNCTION-NOBS-00 — `R/IvChainJunction.mop:166-167`, event `use`
1. `event use before(int encmode, AlgorithmParameterSpec params, Cipher c): call(public void Cipher.init(int, Key, AlgorithmParameterSpec, ..)) && args(encmode, *, params, ..) && target(c)` (`:138-141`) — 3- and 4-argument `init` with a spec.
2. Guarded read (`:155-160`): `operationMode = CipherTransformationNormalizer.mode(c.getAlgorithm())`; `ivRequired = encmode == 1 && operationMode != null && ivModes.contains(operationMode)` with `ivModes = {CBC, CTS, CTR, CFB, PCBC, OFB}` (`:83`); then `validate(PREPARED_IV, params)`. Only ENCRYPT_MODE (1); DECRYPT (2), WRAP (3), UNWRAP (4) read nothing.
3. `params == null` → `NOT_OBSERVED` → NOBS-00 emitted (before advice, no null guard). `Cipher.init(ENCRYPT_MODE, key, (AlgorithmParameterSpec) null)` is legal and makes the provider generate the IV; it draws this NOBS.
4. `PREPARED_IV`: only `IvParameterSpec.@match`, bound only when the iv was `RANDOMIZED` (§3).
5. Upstream: IVPARAMETERSPEC-NOBS-00/01 (the same reach limit reported twice, acknowledged at `:127-137`); an `IvParameterSpec` constructed inside un-woven code; any non-`IvParameterSpec` parameter object for a CBC-family mode (e.g. `AlgorithmParameters`-derived specs are read under `PREPARED_IV` too, `R/AlgorithmParametersSpec.mop:148`, but the object handed to `init` must be the very `IvParameterSpec` the `@match` bound). Downstream: none (this spec writes nothing; `CipherSpec` stages independently).
6. The `ere` accepts everything (`:382`, rows `{0,1}` in `G/…`), so there is no ORDER code here.

### IVCHAINJUNCTION-NOBS-01 — `R/IvChainJunction.mop:200-201`, event `use`
1. Same event/pointcut as NOBS-00.
2. `gcmRequired = operationMode != null && "GCM".equals(operationMode)` (`:191-192`) — **no `encmode` conjunct** — then `validate(PREPARED_GCM, params)` (`:194`).
3. `params == null` → NOBS-01 (same as above; for GCM the provider would then generate a nonce on encrypt).
4. `PREPARED_GCM`: only `GCMParameterSpecSpec.@match`, bound only if tag length admitted **and** `src` `RANDOMIZED`.
5. Upstream: GCMPARAMETERSPEC-NOBS-00/01 and GCMPARAMETERSPEC-CONSTR-00/02 (an unadmitted tag length also unbinds `spec`, so a **tag-length CONSTR at construction turns into a NOBS here**). Fires on **decrypt too**, so a GCM decrypt with the received nonce draws GCMPARAMETERSPEC-NOBS-0x + IVCHAINJUNCTION-NOBS-01.

### IVPARAMETERSPEC-NOBS-00 — `R/IvParameterSpec.mop:74-75`, event `c1`
1. `event c1 after(byte[] iv) returning(IvParameterSpec s): call(public IvParameterSpec.new(byte[])) && args(iv)` (`:65-67`).
2. `validate(RANDOMIZED, iv)` (`:68`), one place, on the argument array; read unconditionally — the constructor has no mode.
3. `iv == null` → constructor throws NPE → no report.
4. `RANDOMIZED` on arrays: `SecureRandomSpec.@match2` only.
5. Upstream: SecureRandom reach limits (see SECURERANDOM section); IV received/parsed from ciphertext (**every decrypt**); `Cipher.getIV()` (no producer); copies. Downstream: `spec` unbound → no `PREPARED_IV` → IVCHAINJUNCTION-NOBS-00 when the spec reaches an ENCRYPT `init` with a CBC-family mode; nothing on DECRYPT.
6. The sibling NOBS-01 (`c2`, `:123-124`) did not occur in the campaign.

### KEYAGREEMENT-NOBS-08 — `R/KeyAgreementSpec.mop:270-271`, event `dophase`
1. `event dophase after(Key pubKey, boolean lastPhase, KeyAgreement ka): call(public java.security.Key KeyAgreement.doPhase(java.security.Key, boolean)) && args(pubKey, lastPhase) && target(ka)` (`:259-261`). `after` without `returning` (after-finally in ajc).
2. `validate(GENERATED_PUBLIC_KEY, pubKey)` (`:262`), one place.
3. `pubKey == null` → NOBS-08 under ajc (the call throws after/with the advice); under dexlib2 the advice is skipped on a throw.
4. `GENERATED_PUBLIC_KEY`: `KeyFactorySpec.genPublic` (only if the `KeySpec` was `SPECCED_KEY`), `KeyPairSpec.gpu` (unconditional).
5. Upstream: the peer's key is decoded from received bytes → `new X509EncodedKeySpec(bytes)` → X509ENCODEDKEYSPEC-NOBS-00 → `spec` unbound → `KeyFactory.generatePublic` → KEYFACTORY-NOBS-01 → `conforms=false` → key not marked → KEYAGREEMENT-NOBS-08. Also `Certificate.getPublicKey()` (no producer). Downstream: `conforms = false` (`:264`, `:269`) is a monitor field that stays false → `gs1`/`gs2` do **not** write `PREPARED_KEY_MATERIAL` on the shared secret → `new SecretKeySpec(sharedSecret, "AES")` → SECRETKEYSPEC-NOBS-00 → CIPHER-NOBS-00 / MAC-NOBS-00. A remote-peer ECDH therefore draws a five-link chain: X509 → KEYFACTORY → KEYAGREEMENT → SECRETKEYSPEC → CIPHER.
6. The local half (`init1..4` with `getPrivate()` of a generated pair) is credited through `KeyPairSpec.gpr`'s unconditional body write, so NOBS-00..07 need not accompany NOBS-08.

### KEYFACTORY-NOBS-01 — `R/KeyFactorySpec.mop:113-114`, event `genPublic`
1. `event genPublic after(KeySpec keySpec, KeyFactory f) returning(PublicKey publicKey): call(public PublicKey KeyFactory.generatePublic(KeySpec)) && args(keySpec) && target(f)` (`:101-103`).
2. `validateAny(SPECCED_KEY, keySpec)` (`:105`) — anonymous second place.
3. `keySpec == null` → `generatePublic(null)` throws → `after returning` does not run → no report.
4. `SPECCED_KEY`: `PBEKeySpecSpec.c1` (body, guarded), `SecretKeySpecSpec.@match` (guarded), `X509EncodedKeySpecSpec.@match` (guarded on `PREPARED_KEY_MATERIAL`). No producer for `RSAPublicKeySpec`, `ECPublicKeySpec`, `DHPublicKeySpec`, `PKCS8EncodedKeySpec` — a `generatePublic` over any of those is NOBS-01 with no possible producer.
5. Upstream: X509ENCODEDKEYSPEC-NOBS-00; an unspecified spec type. Downstream: `conforms=false` → no `GENERATED_PUBLIC_KEY` → KEYAGREEMENT-NOBS-08, SIGNATURE-NOBS-02, KEYPAIR-NOBS-01, TRUSTANCHOR reads, and CIPHER-NOBS-00 for RSA-encrypt with that key.

### KEYMANAGERFACTORY-NOBS-00 — `R/KeyManagerFactorySpec.mop:128-129`, event `init`
1. `event init before(Object arg, KeyManagerFactory k): ( call(public void KeyManagerFactory.init(KeyStore, char[])) || call(public void KeyManagerFactory.init(ManagerFactoryParameters)) ) && args(arg, ..) && target(k)` (`:113-116`).
2. Branch `if (arg == null || arg instanceof KeyStore)` (`:121`) → `validate(GENERATED_KEY_STORE, arg)` (`:122`).
3. `arg == null` is **read on purpose** (`:91-99`) → `NOT_OBSERVED` → NOBS-00. `init((ManagerFactoryParameters) null)` is also read as this branch (`:101-104`).
4. `GENERATED_KEY_STORE`: `KeyStoreSpec.@match` only, after an accepted `getInstance(String…)` + `load(..)` on that object.
5. Upstream: KeyStore built by `getInstance(File, …)` (not pointcut), or obtained/loaded inside un-woven code (e.g. a library that loads a PKCS12 from assets), or a store of a type outside the list. Downstream: **none** — `gkm1` marks the array unconditionally, so SSLCONTEXT-NOBS-00 does not follow from this code.

### MAC-NOBS-00 — `R/MacSpec.mop:185-186`, event `i1`
1. `event i1 before(java.security.Key key, Mac m): call(public void Mac.init(java.security.Key)) && args(key) && target(m)` (`:171-174`).
2. `validateAny(GENERATED_KEY, key)` (`:179`).
3. `key == null` → NOBS-00, then `init` throws (before advice).
4. `GENERATED_KEY`: the five sites in §3 (any value tuple satisfies `validateAny`).
5. Upstream: SECRETKEYSPEC-NOBS-00/01 (the usual `new SecretKeySpec(bytes, "HmacSHA256")` over stored/derived bytes), SECRETKEYFACTORY-NOBS-00 (PBKDF2 key whose `PBEKeySpec` was not specced), unobserved `KeyGenerator`. Downstream: none (`MACED` writes do not depend on it).

### PBEKEYSPEC-NOBS-01 — `R/PBEKeySpecSpec.mop:155-156`, event `c1`
1. `event c1 after(char[] password, byte[] salt, int iterationCount, int keyLength) returning(PBEKeySpec s): call(public PBEKeySpec.new(char[], byte[], int, int)) && args(password, salt, iterationCount, keyLength)` (`:117-119`).
2. `validate(RANDOMIZED, salt)` (`:148`) on the argument array.
3. `salt == null` → constructor throws NPE → no report.
4. `RANDOMIZED` on arrays: `SecureRandomSpec.@match2` only.
5. Upstream: a **stored** salt (the correct PBKDF2 idiom on every derivation after the first — the salt must be persisted and reused), a salt from un-woven code, a SecureRandom reach limit. Downstream: `conforms=false` (`:157`) → no `SPECCED_KEY` (`:159-161`) → SECRETKEYFACTORY-NOBS-00 → no `GENERATED_KEY` on the derived key → MAC-NOBS-00 / CIPHER-NOBS-00; and `SecretKeySpec.e1`/`KeySpec.ge1` stage nothing for that key → its `getEncoded()` bytes are not `PREPARED_KEY_MATERIAL` → the re-wrap `new SecretKeySpec(derived.getEncoded(), "AES")` (the very idiom `R/CipherSpec.mop:195-198` names as the conforming path) draws SECRETKEYSPEC-NOBS-00 → CIPHER-NOBS-00. One non-random salt is five reports.

### SECRETKEYFACTORY-NOBS-00 — `R/SecretKeyFactorySpec.mop:104-105`, event `gen`
1. `event gen after(KeySpec keySpec, SecretKeyFactory f) returning(SecretKey key): call(public SecretKey SecretKeyFactory.generateSecret(KeySpec)) && args(keySpec) && target(f)` (`:92-94`).
2. `validateAny(SPECCED_KEY, keySpec)` (`:96`).
3. `keySpec == null` → call throws → `after returning` does not run → no report.
4. `SPECCED_KEY`: PBEKeySpecSpec `c1` (guarded), SecretKeySpecSpec `@match` (guarded), X509EncodedKeySpecSpec `@match` (guarded). No producer for `DESKeySpec`/`DESedeKeySpec`/`PBEKeySpec(char[])` (forbidden, `f1`) / `PBEKeySpec(char[],byte[],int)` (forbidden, `f2` — the 3-arg constructor is accused with FORB-01 and additionally writes nothing, so its spec is NOBS here).
5. Upstream: PBEKEYSPEC-NOBS-01, PBEKEYSPEC-CONSTR-00 (iterations < 10000 also unbinds), PBEKEYSPEC-FORB-01, SECRETKEYSPEC-NOBS-00. Downstream: `conforms=false` → no `GENERATED_KEY` at `:108` → CIPHER-NOBS-00 / MAC-NOBS-00 / SECRETKEYSPEC-NOBS-00 via the `getEncoded` bridge.
6. A `ere : get (gen | translate)` (`:127`): a factory reused for a second `generateSecret` draws ORDER-00; the read and the write still happen (body runs first), so the second key **is** credited if the spec was.

### SECRETKEYSPEC-NOBS-00 — `R/SecretKeySpecSpec.mop:117-118`, event `c1`
1. `event c1 after(byte[] keyMaterial, String keyAlgorithm) returning(SecretKeySpec secretKeySpec): call(public SecretKeySpec.new(byte[], String)) && args(keyMaterial, keyAlgorithm)` (`:97-99`).
2. `validate(PREPARED_KEY_MATERIAL, keyMaterial)` (`:110`), one place, on the argument array.
3. `keyMaterial == null` → constructor throws `IllegalArgumentException` → no report.
4. `PREPARED_KEY_MATERIAL`: `KeySpec.@match` / `SecretKeySpec.@match` (the exact clone returned by a `getEncoded()` on a key whose origin was `SATISFIED`), `KeyAgreementSpec.gs1/gs2` (if `conforms`). Nothing else — not `SecureRandom.nextBytes` (that is `RANDOMIZED`, deliberately un-conflated, `:56-61`, `:73-91`), not hard-coded bytes, not `Base64.decode`, not PBKDF2 output unless the whole PBE chain conformed, not `Cipher.unwrap`, not `Key.getEncoded()` of an unobserved key.
5. Upstream (each is enough): bytes filled by SecureRandom (the corpus idiom, measured as 15 NOBS-00 in 126 traces, `:84-91`); stored/derived/received bytes; KEYAGREEMENT-NOBS-0x (any); SECRETKEYFACTORY-NOBS-00 / PBEKEYSPEC-NOBS-01 through the bridge; a first SecretKeySpec that itself drew NOBS-00 (laundering refusal, `R/KeySpec.mop:51-59`). Downstream: `conforms=false` → `spec` unbound → `@match` writes nothing → no `GENERATED_KEY`, no `SPECCED_KEY` → **CIPHER-NOBS-00** (measured 11 of 15, `:85-87`), **MAC-NOBS-00**, SECRETKEYFACTORY-NOBS-00 / KEYFACTORY-NOBS-0x if used as a `KeySpec`; and `SecretKeySpec.e1`/`KeySpec.ge1` stage nothing → its `getEncoded()` is not prepared → a second SecretKeySpec / X509EncodedKeySpec over it → SECRETKEYSPEC-NOBS-00 / X509ENCODEDKEYSPEC-NOBS-00.
6. The ALG check also unbinds `spec` (`:105-109`): SECRETKEYSPEC-ALG-00 alone (e.g. `"DES"`, `"Blowfish"`, `"HmacSHA1"`) with prepared material still yields CIPHER-NOBS-00 downstream — a NOBS whose cause is a value verdict, not a reach limit.

### SECRETKEYSPEC-NOBS-01 — `R/SecretKeySpecSpec.mop:183-184`, event `c2`
1. `event c2 after(byte[] keyMaterial, int offset, int len, String keyAlgorithm) returning(SecretKeySpec secretKeySpec): call(public SecretKeySpec.new(byte[], int, int, String)) && args(keyMaterial, offset, len, keyAlgorithm)` (`:159-161`).
2. `validate(PREPARED_KEY_MATERIAL, keyMaterial)` (`:176`) on the whole array (the window is not a separate object).
3.–6. As NOBS-00. `CONSTR-01` (`:171-175`) is unreachable (constructor throws first, `:150-158`).

### SECURERANDOM-NOBS-00 — `R/SecureRandomSpec.mop:236-237`, event `setSeed2`
1. `event setSeed2 after(byte[] seed, SecureRandom r): call(public void SecureRandom.setSeed(byte[])) && args(seed) && target(r)` (`:226-229`). `after` without `returning`.
2. `validate(RANDOMIZED, seed)` (`:230`) on the argument array.
3. `seed == null` → NOBS-00 under ajc (after-finally), then NPE; not under dexlib2.
4. `RANDOMIZED` on arrays: another (or the same) observed SecureRandom's `@match2` (`generateSeed` return / `nextBytes` argument).
5. Upstream: literal or stored seeds; seeds from un-woven code; a seed produced by an SR whose `Ins` was not observed. Downstream: none — `setSeed2` neither binds `sr` nor stages, and `sr` was bound at `Ins` regardless, so the SecureRandom object stays credited (`randomized[this] after Ins` is unconditional). `setSeed2` from `start` (unobserved SR) additionally draws SECURERANDOM-ORDER-00.
6. `setSeed(long)` (`setSeed1`, `:200-202`) reads nothing by decision (`:171-196`).

### SECURERANDOM-NOBS-01 — `R/SecureRandomSpec.mop:105-106`, event `c2`
1. `event c2 after(byte[] seed) returning(SecureRandom r): call(public SecureRandom.new(byte[])) && args(seed)` (`:95-97`).
2. `validate(RANDOMIZED, seed)` (`:99`).
3. `seed == null` → NPE in the constructor → no report.
4. As NOBS-00.
5. Upstream: as NOBS-00. Downstream: none — `sr = r` is assigned **before** the read (`:98`) and `c2 -> init` (`:332`), so `@match1` still marks the SecureRandom `RANDOMIZED`; every consumer of that SR (`Cipher.init(…, sr)`, `KeyGenerator.init(sr)`, `SSLContext.init(…, sr)`) answers `SATISFIED`, and its `nextBytes` arrays are marked. A constant-seeded SecureRandom is therefore a single NOBS-01 with nothing cascading.

### SIGNATURE-NOBS-02 — `R/SignatureSpec.mop:198-199`, event `i4`
1. `event i4 before(PublicKey key, Signature s): call(public void Signature.initVerify(PublicKey)) && args(key) && target(s)` (`:184-187`).
2. `validate(GENERATED_PUBLIC_KEY, key)` (`:192`), one place.
3. `key == null` → NOBS-02, then `InvalidKeyException` (before advice). The corpus traces pass `null` (`:132-135`).
4. `GENERATED_PUBLIC_KEY`: `KeyFactorySpec.genPublic` (guarded), `KeyPairSpec.gpu` (unconditional).
5. Upstream: `Certificate.getPublicKey()` / `X509Certificate` from a `CertificateFactory` or a `KeyStore.getCertificate` (no producer anywhere); X509ENCODEDKEYSPEC-NOBS-00 → KEYFACTORY-NOBS-01 → this. Downstream: none — `stagedVerified` is staged in `v1`/`v2` independently (`:262`, `:270`).
6. `i3` (`initVerify(Certificate)`, `:174-182`) reads nothing, so the same verification is silent when the certificate is passed and NOBS when its public key is extracted first.

### SSLCONTEXT-NOBS-00 — `R/SSLContextSpec.mop:228-229`, event `init`
1. `event init after(KeyManager[] kms, TrustManager[] tms, SecureRandom random, SSLContext ctx): call(public void SSLContext.init(KeyManager[], TrustManager[], SecureRandom)) && args(kms, tms, random) && target(ctx)` (`:214-217`). `after`, no `returning`.
2. `validate(GENERATED_KEY_MANAGERS, kms)` (`:222`) — the **array object** is the bound object (deliberately not spread, `:187-191`).
3. `kms == null` → `NOT_OBSERVED` → NOBS-00, by decision (`:204-208`). `init(null, tms, null)` is the canonical client idiom, so this code accompanies almost every conforming client `SSLContext`.
4. `GENERATED_KEY_MANAGERS` on arrays: `KeyManagerFactorySpec.gkm1` body, unconditional, on the array `getKeyManagers()` returned.
5. Upstream: null; an array built by hand (`new KeyManager[]{ km }`) or copied; `getKeyManagers()` called inside un-woven code (OkHttp/Retrofit/Conscrypt helpers). **Not** KEYMANAGERFACTORY-NOBS-00 (the array write is unconditional). Downstream: none (`GENERATE_SSL_CONTEXT` is written at `@match1` regardless, `:322`).

### SSLCONTEXT-NOBS-01 — `R/SSLContextSpec.mop:237-238`, event `init`
1. Same event.
2. `validate(GENERATED_TRUST_MANAGER, tms)` (`:231`) on the array object.
3. `tms == null` → NOBS-01 (default trust managers — a conforming program under every reading except the rule's, `:198-208`).
4. `GENERATED_TRUST_MANAGER` on arrays: `TrustManagerFactorySpec.gtm1` body, unconditional (`G/…:16483-16486`).
5. Upstream: null; a hand-built array — which is exactly the trust-all `new TrustManager[]{ new X509TrustManager(){…} }` the rule exists to catch (`:197-199`), so this code is where that misuse lands, under a "reach-limit" label; `getTrustManagers()` in un-woven code; a copy/filter of the returned array. **Not** TRUSTMANAGERFACTORY-NOBS-00.

### SSLCONTEXT-NOBS-02 — `R/SSLContextSpec.mop:246-247`, event `init`
1. Same event.
2. `validate(RANDOMIZED, random)` (`:240`) on the SecureRandom object.
3. `random == null` → NOBS-02 by decision (`:176-185`): "Every trace of the corpus that reaches this event passes null there, so every one of them gains a NOBS report."
4. `RANDOMIZED` on a SecureRandom object: `SecureRandomSpec.@match1` only.
5. Upstream: null (the documented default); an SR from un-woven code or from `getInstance` with an unadmitted algorithm.

### TRUSTMANAGERFACTORY-NOBS-00 — `R/TrustManagerFactorySpec.mop:153-154`, event `init`
1. `event init before(Object arg, TrustManagerFactory mf): ( call(public void TrustManagerFactory.init(KeyStore)) || call(public void TrustManagerFactory.init(ManagerFactoryParameters)) ) && args(arg) && target(mf)` (`:118-121`).
2. Branch `arg == null || arg instanceof KeyStore` (`:146`) → `validate(GENERATED_KEY_STORE, arg)` (`:147`).
3. `null` read on purpose (`:102-112`): `tmf.init((KeyStore) null)` — the documented default-truststore route and the canonical Android idiom — draws NOBS-00.
4. `GENERATED_KEY_STORE`: `KeyStoreSpec.@match` only (accepted `getInstance(String…)` + `load`).
5. Upstream: null; KeyStore loaded in un-woven code; `getInstance(File,…)`; unadmitted type; `tmf.init(unloadedStore)` runs on this platform (`:109-112`) and is NOBS. Downstream: none — `gtm1` marks the array unconditionally.
6. `initialisedFactory = mf` (`:172`) is set regardless, so the (unread) factory mark at `@match1` is unaffected.

### X509ENCODEDKEYSPEC-NOBS-00 — `R/X509EncodedKeySpecSpec.mop:49-50`, event `c1`
1. `event c1 after(byte[] encodedKey) returning(X509EncodedKeySpec s): call(public X509EncodedKeySpec.new(byte[])) && args(encodedKey)` (`:40-42`).
2. `validate(PREPARED_KEY_MATERIAL, encodedKey)` (`:43`) on the argument array.
3. `encodedKey == null` → NPE → no report.
4. `PREPARED_KEY_MATERIAL`: `KeySpec.@match` / `SecretKeySpec.@match` (only a `getEncoded()` clone of a key whose origin the store had), `KeyAgreementSpec.gs1/gs2` (only if `conforms`).
5. Upstream: any public key received from a peer, read from a file, from a certificate's `getPublicKey().getEncoded()` (the key is not `GENERATED_PUBLIC_KEY`, so `KeySpec.ge1` stages nothing), or from a `Base64` string. Only a **local round-trip** (`kp.getPublic().getEncoded()` → `new X509EncodedKeySpec(bytes)`) is `SATISFIED`. Downstream: `spec` unbound → no `SPECCED_KEY` → KEYFACTORY-NOBS-01 → (no `GENERATED_PUBLIC_KEY`) → KEYAGREEMENT-NOBS-08 / SIGNATURE-NOBS-02 / KEYPAIR-NOBS-01 / CIPHER-NOBS-00 (RSA encrypt).

## 5. Cascade graph (edges are "A's object not credited ⇒ B's read answers NOT_OBSERVED")

```
[SecureRandom unobserved | unsafe alg (g4/g5) | nextBytes/generateSeed from `start`]
   ├─> IVPARAMETERSPEC-NOBS-00 ──> (no PREPARED_IV)  ──> IVCHAINJUNCTION-NOBS-00   [ENCRYPT, CBC-family only]
   ├─> GCMPARAMETERSPEC-NOBS-00/01 ─> (no PREPARED_GCM) ─> IVCHAINJUNCTION-NOBS-01 [both modes]
   ├─> PBEKEYSPEC-NOBS-01 ──> (no SPECCED_KEY) ──> SECRETKEYFACTORY-NOBS-00 ──> (no GENERATED_KEY) ──┐
   ├─> SECURERANDOM-NOBS-00 / -01 (sinks)                                                             │
   └─> SSLCONTEXT-NOBS-02, IVCHAINJUNCTION-NOBS-02..05, KEYAGREEMENT-NOBS-05/07, KEYGENERATOR-NOBS-* │
                                                                                                      │
[bytes not from an observed getEncoded()/generateSecret]                                              │
   ├─> SECRETKEYSPEC-NOBS-00/01 ──> (no GENERATED_KEY, no SPECCED_KEY) ──┬──> CIPHER-NOBS-00 <───────┤
   │        ^                                                             ├──> MAC-NOBS-00    <───────┘
   │        │                                                             ├──> SECRETKEYFACTORY-NOBS-00 (spec used as KeySpec)
   │        │  (getEncoded bridge stages nothing)                         └──> SECRETKEYSPEC-NOBS-00 (re-wrap / laundering)
   │        └───────────────────────────────────────────────────────────────────────────────────────┘
   └─> X509ENCODEDKEYSPEC-NOBS-00 ──> (no SPECCED_KEY) ──> KEYFACTORY-NOBS-01 ──> (no GENERATED_PUBLIC_KEY)
                                                                 ├──> KEYAGREEMENT-NOBS-08 ──> conforms=false ──> (no PREPARED_KEY_MATERIAL on secret)
                                                                 │                                   └──> SECRETKEYSPEC-NOBS-00 ──> CIPHER-NOBS-00 / MAC-NOBS-00
                                                                 ├──> SIGNATURE-NOBS-02
                                                                 └──> CIPHER-NOBS-00 (RSA)

[KeyStore not loaded through an observed getInstance(String…)+load]
   ├─> KEYMANAGERFACTORY-NOBS-00   (sink: gkm1 marks the array anyway)
   ├─> TRUSTMANAGERFACTORY-NOBS-00 (sink: gtm1 marks the array anyway)
   └─> (no GENERATED_KEY via KeyStore.getKey) ──> CIPHER-NOBS-00 / MAC-NOBS-00 for keys taken from that store

[null arguments read on purpose]
   KEYMANAGERFACTORY-NOBS-00, TRUSTMANAGERFACTORY-NOBS-00, SSLCONTEXT-NOBS-00/01/02, IVCHAINJUNCTION-NOBS-00/01, CIPHER-NOBS-00,
   MAC-NOBS-00, SIGNATURE-NOBS-02, KEYAGREEMENT-NOBS-08 (ajc only), SECURERANDOM-NOBS-00 (ajc only)
   -- the constructor-site codes never fire on null (the constructor throws before `after returning`).
```

Value verdicts that also unbind the producer and therefore surface downstream as a NOBS (the NOBS is then not a reach limit): SECRETKEYSPEC-ALG-00/01 → CIPHER/MAC-NOBS; GCMPARAMETERSPEC-CONSTR-00/02 → IVCHAINJUNCTION-NOBS-01; PBEKEYSPEC-CONSTR-00 → SECRETKEYFACTORY-NOBS-00; KEYGENERATOR-ALG-00 (via `g3` then failed `gk1`) → CIPHER/MAC-NOBS; SECURERANDOM-ALG-00/01 → every consumer NOBS plus the IV chain; KEYAGREEMENT-ALG-00 / -FORB-00 → SECRETKEYSPEC-NOBS-00 on the shared secret; IVPARAMETERSPEC-CONSTR-02 (`len == 0`) → IVCHAINJUNCTION-NOBS-00.

Dedup: `ErrorCollector` (`rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java:26,51`) keeps a `HashSet<ErrorDescription>`, and `ErrorDescription.equals` compares only the `ErrorSummary` (`S/eh/ErrorDescription.java:166-172`), whose fields are `spec, error, classQualifiedName, methodName, location, code, event` (`S/eh/ErrorSummary.java:44-50`). So a cascade counts once per (code, call site), not once per object.

## 6. Observable JCA calls that produce key material / IVs / public keys with NO producer in the set

Grep basis: `/usr/bin/grep -n 'call(' R/*.mop` for the names below; only the listed hits exist.

| call | pointcut in set? | producer? | consequence |
|---|---|---|---|
| `Certificate.getPublicKey()` / `X509Certificate.getPublicKey()` | none | none (`GENERATED_PUBLIC_KEY` written only at `R/KeyFactorySpec.mop:117`, `R/KeyPairSpec.mop:126`) | SIGNATURE-NOBS-02, KEYAGREEMENT-NOBS-08, TRUSTANCHOR-NOBS, CIPHER-NOBS-00 for every certificate-derived key; `getPublicKey().getEncoded()` is not prepared either (`R/KeySpec.mop:78-81`), so re-spec'ing it → X509ENCODEDKEYSPEC-NOBS-00. |
| `KeyStore.getCertificate(String)` / `getCertificateChain` | none (`R/KeyStoreSpec.mop:186-193` records `generatedPubkey[key]` has no site) | none | as above |
| `KeyStore.getEntry(String, ProtectionParameter)` | `ge1 before(KeyStore k)` (`R/KeyStoreSpec.mop:106-108`) — binds nothing, ensures nothing | none | a `PrivateKeyEntry.getPrivateKey()` / `SecretKeyEntry.getSecretKey()` is never `GENERATED_*` → CIPHER/MAC/SIGNATURE NOBS. Only `getKey(String, char[])` (`gk1`) credits. |
| `Cipher.getIV()` | none | none (`RANDOMIZED` only from `SecureRandomSpec`) | the provider-generated IV read back and re-wrapped for decrypt → IVPARAMETERSPEC-NOBS-00 (and, if the same spec is later used to *encrypt*, IVCHAINJUNCTION-NOBS-00). |
| `Cipher.getParameters()` / `AlgorithmParameters.getParameterSpec(IvParameterSpec.class)` | `getParameters` none; `AlgorithmParameters.getEncoded` is pointcut (`R/AlgorithmParametersSpec.mop:184-185`, marks `PREPARED_ALG`) | no `RANDOMIZED`/`PREPARED_IV` producer | same as `getIV()` |
| `Cipher.init(ENCRYPT, key)` then implicit IV | n/a | n/a | fine for `CipherSpec`; but `init(ENCRYPT, key, (AlgorithmParameterSpec) null)` → IVCHAINJUNCTION-NOBS-00/01 (null read). |
| `Cipher.unwrap(byte[], String, int)` | none (`wkb1` covers `wrap` only, `R/CipherSpec.mop:295-298`) | none | unwrapped key → CIPHER/MAC-NOBS |
| `KeyAgreement.generateSecret(String)` | `gs3` (`R/KeyAgreementSpec.mop:337-343`) — FORB-00 | none, and sets `conforms=false` | the returned `SecretKey` → CIPHER/MAC-NOBS; and `gs1`/`gs2` afterwards write nothing |
| `SecretKeyFactory.generateSecret(KeySpec)` result | `gen` (`R/SecretKeyFactorySpec.mop:92-110`) | `GENERATED_KEY` **only if** `conforms` | see PBEKEYSPEC/SECRETKEYFACTORY cascade |
| `Key.getEncoded()` (any subtype), `SecretKey.getEncoded()` | `Key+.getEncoded()` (`R/KeySpec.mop:76`), `SecretKey+.getEncoded()` (`R/SecretKeySpec.mop:120`) | `PREPARED_KEY_MATERIAL` **only if** the key's origin is already in the store (`R/KeySpec.mop:78-84`, `R/SecretKeySpec.mop:122-126`) | not a producer for keys from certificates, `getEntry`, `unwrap`, libraries |
| `PKCS8EncodedKeySpec(byte[])` | no spec file | none | `KeyFactory.generatePrivate` → KEYFACTORY-NOBS-00 for every private key loaded from storage |
| `RSAPublicKeySpec`, `RSAPrivateKeySpec`, `ECPublicKeySpec`, `ECPrivateKeySpec`, `DHPublicKeySpec`, `DHPrivateKeySpec`, `DESKeySpec`, `DESedeKeySpec` | no spec file | none | KEYFACTORY-NOBS-00/01, SECRETKEYFACTORY-NOBS-00 with no satisfiable path |
| `KeyPairGenerator.generateKeyPair()` | `gen` (`R/KeyPairGeneratorSpec.mop:334-338`) | `GENERATED_KEY_PAIR` on the pair only (`:397`); the halves are credited later by `KeyPair.getPublic()/getPrivate()` bodies (`R/KeyPairSpec.mop:126,146`) | a pair whose halves are read inside un-woven code is never credited |
| `SecureRandom.nextInt()`, `nextInt(int)`, `nextLong`, `ints(..)`, `setSeed(long)` | `next1`, `next3`, `ints`, `setSeed1` — bodies empty | none (recorded decisions, `R/SecureRandomSpec.mop:253-270`, `:171-196`) | an IV/salt built from `nextInt` bytes → IVPARAMETERSPEC/PBEKEYSPEC-NOBS |
| `SecureRandom.getInstance(alg, provider, …)` 3-arg, `SecureRandom.getInstanceStrong()` | `g3` covers `getInstanceStrong` (`:130-133`); 3-arg overloads not pointcut (`:155-157`) | `g3` → `sr` bound → credited; 3-arg → nothing | 3-arg-obtained SR: every consumer NOBS + ORDER on its first `nextBytes` |
| `KeyStore.getInstance(File, char[])` / `(File, LoadStoreParameter)` | not pointcut (`R/KeyStoreSpec.mop:76-79`) | none | `load` from `start` → fail → no `GENERATED_KEY_STORE` → KMF/TMF-NOBS-00 |
| `KeyManagerFactory.getKeyManagers()` / `TrustManagerFactory.getTrustManagers()` **called in un-woven code** | pointcut exists but the call site is not in the app | none at runtime | SSLCONTEXT-NOBS-00/01 |
| `SecureRandom` constructed/obtained in un-woven code (libraries, `SecureRandom` held in a static of a library class) | n/a | none | the whole `RANDOMIZED` fan-out |

## 7. Things that look inconsistent in the specs (comment vs code, unreachable producers, mode/state issues)

1. **IV randomness is read on decrypt.** `R/IvParameterSpec.mop:65-80` reads `randomized[iv]` at construction unconditionally (transcribing `IvParameterSpec.crysl:22`), while the Cipher-side clause is gated on `encmode == 1` (`R/IvChainJunction.mop:156`, `Cipher.crysl:138`). A decrypt that rebuilds the received IV therefore always draws IVPARAMETERSPEC-NOBS-00, and the comment block at `IvChainJunction.mop:127-137` discusses the double report only for the encrypt path. The two rules disagree about whether a decrypt IV needs a random origin; the set follows each rule at its own site.
2. **GCM has no mode gate at all.** `R/IvChainJunction.mop:179-183,191-192` states the antecedent has "no `encmode` conjunct" so a GCM decrypt with the received nonce draws GCMPARAMETERSPEC-NOBS-0x at construction **and** IVCHAINJUNCTION-NOBS-01 at `init` — two reports for the one conforming decrypt, both labelled reach-limit.
3. **A tag-length CONSTR becomes a NOBS downstream.** `R/GCMParameterSpecSpec.mop:66-70,82-84`: an unadmitted `tagLen` clears `conforms`, so `spec` is never bound and `PREPARED_GCM` never written; `IvChainJunction.mop:194` then answers NOT_OBSERVED → IVCHAINJUNCTION-NOBS-01 whose message says "no preparation … was observed" although the preparation was observed and refused. The same pattern for SECRETKEYSPEC-ALG-00 → CIPHER-NOBS-00 (`R/SecretKeySpecSpec.mop:101-109`), PBEKEYSPEC-CONSTR-00 → SECRETKEYFACTORY-NOBS-00 (`R/PBEKeySpecSpec.mop:121-125`), KEYGENERATOR-ALG-00 → CIPHER-NOBS-00 (`g3` then failed `gk1`, `R/KeyGeneratorSpec.mop:175`), SECURERANDOM-ALG-00/01 → the whole IV chain (`R/SecureRandomSpec.mop:145-169,336-337`: `g4`/`g5` bind no `sr`). The NOBS code is documented as "reach limit, not a misuse" (`S/PredicateVerdict.java:29-34`); in these paths it is the echo of a misuse already reported.
4. **`SECRETKEYSPEC-NOBS-00`'s message is narrower than the code.** It says "not observed to have been prepared by a `Key.getEncoded()`" (`R/SecretKeySpecSpec.mop:118`), but `getEncoded()` prepares only if the key already carries a `GENERATED_*` mark (`R/KeySpec.mop:78-84`, `R/SecretKeySpec.mop:122-126`), and `KeyAgreement.generateSecret()` is a second producer (`R/KeyAgreementSpec.mop:298,315`). The comment at `SecretKeySpecSpec.mop:80-81` ("ENSURED by `Key.getEncoded()` and `SecretKey.getEncoded()` and by nothing else in the whole oracle") is stale relative to `KeyAgreement.crysl:51`, which `X509EncodedKeySpecSpec.mop:36-38` cites.
5. **`KeyAgreementSpec.conforms` never recovers.** Once any read at `get`/`init*`/`dophase` accuses (`:85,111,116,141,146,161,166,180,185,200,205,211,216,230,235,241,246,264,269`) or `gs3` fires (`:340`), the field stays `false` until a `@fail` (`:385`). The comment at `:57-60` records only the `gs3`-after-generate residue. Consequence: a remote-peer ECDH (peer key always NOT_OBSERVED, see §6) can never write `PREPARED_KEY_MATERIAL`, so `new SecretKeySpec(secret, "AES")` is SECRETKEYSPEC-NOBS-00 and the AES `Cipher.init` is CIPHER-NOBS-00 in every ECDH program — five NOBS from one structurally unavoidable unobserved object.
6. **`SecureRandom(byte[])` is credited before it is judged.** `R/SecureRandomSpec.mop:98` binds `sr = r` before the seed read, and `c2 -> init` (`:332`) reaches `@match1`, so a SecureRandom seeded with a constant is `RANDOMIZED` and its `nextBytes` arrays are too. Meanwhile a constant salt (`PBEKeySpecSpec.c1`) and a constant IV are not. Faithful to `SecureRandom.crysl:49` (`randomized[this] after Ins` unconditional), but it is the only producer in the set that writes on the non-conforming branch, and the `@match1` comment (`:378-382`) does not mention it.
7. **`nextBytes` on an unobserved SecureRandom silently un-randomises the array.** Row `Prop_1_transition_next2[] = {3,1,1,3}` (`G/…:15271`): from `start` the event fails, `@fail` clears `stagedNextBytes` (`R/SecureRandomSpec.mop:374`). The array is then NOT_OBSERVED at every consumer, and the program is *also* accused of SECURERANDOM-ORDER-00 for a sequence it did not perform (the `Ins` happened, unobserved). The spec's own comment defends staging over body-writing on the ground that "`getInstance("NativePRNG"); nextBytes(iv)` never reaches a state where `nextBytes` is legal" (`:56-61`) — that example is an *observed* unsafe `getInstance`; the same mechanism also fires for an *unobserved safe* one.
8. **Null is read at some sites and unreachable at others, and the resulting codes read alike.** Null is deliberately read at KMF/TMF `init` (`R/KeyManagerFactorySpec.mop:91-99`, `R/TrustManagerFactorySpec.mop:102-112`), at `SSLContext.init` for all three arguments (`R/SSLContextSpec.mop:176-185,204-208`), and by omission at `Cipher.init` (`R/CipherSpec.mop:168-233`), `Mac.init`, `Signature.initVerify`, `IvChainJunction.use` (`Cipher.init(ENCRYPT, key, (AlgorithmParameterSpec) null)` → IVCHAINJUNCTION-NOBS-00 although the provider generates the IV — nothing in `IvChainJunction.mop` discusses null). Constructor-site codes never see null (constructor throws first). So "NOBS on null" is a policy at four files and an accident at four others, with the same `-NOBS-` family and the same "reach limit" reading.
9. **`TRUSTMANAGERFACTORY-NOBS-00` / `SSLCONTEXT-NOBS-00/02` are the conforming idiom.** `tmf.init((KeyStore) null)` (`R/TrustManagerFactorySpec.mop:102-107`: "a conforming program under every reading except the rule's own") and `ctx.init(null, tms, null)` (`R/SSLContextSpec.mop:176-185`) are the platform-documented defaults; each draws the NOBS by recorded decision. The counts of these three codes therefore measure idiom frequency, not reach.
10. **`SSLCONTEXT-NOBS-01` is where the trust-all misuse lands.** `R/SSLContextSpec.mop:197-199` says `init(null, trustEverything, sr)` "is the trust-all manager this rule exists to catch"; a hand-built `TrustManager[]` has no `GENERATED_TRUST_MANAGER` entry and is NOT_OBSERVED, so the misuse the rule exists for is reported under the reach-limit code, indistinguishable from `getTrustManagers()` called in a library.
11. **`KEYMANAGERFACTORY-NOBS-00` / `TRUSTMANAGERFACTORY-NOBS-00` do not cascade, contrary to what the chain description suggests.** `gkm1`/`gtm1` mark the returned array unconditionally in the body (`R/KeyManagerFactorySpec.mop:176`, `R/TrustManagerFactorySpec.mop:218`; generated `G/…:16483-16486`), and the body runs before the transition (§2a). An unloaded/unobserved KeyStore therefore never reaches `SSLContext.init` as a NOBS. The `S/Property.java:59-78` comment describes the chain as if it were end-to-end.
12. **`SIGNATURE` asymmetry between `initVerify(Certificate)` and `initVerify(PublicKey)`.** `i3` reads nothing (`R/SignatureSpec.mop:112-116,174-182`); `i4` reads `GENERATED_PUBLIC_KEY`, which no certificate route produces (§6). The same verification is silent or NOBS depending on which overload the app picked. The comment attributes the asymmetry to the oracle but does not name the `getPublicKey()` route.
13. **`KEYFACTORY-NOBS-01` has an unsatisfiable producer for most key specs.** Only `X509EncodedKeySpec` has a spec, and its credit requires bytes from an observed local `getEncoded()` (`R/X509EncodedKeySpecSpec.mop:36-39`). `KeyFactorySpec.mop:67-69` says X509 "is the one a key factory actually sees, since a public or private key is decoded from encoded key material" — which is exactly the case that can never be credited when the material came from anywhere but a locally generated key.
14. **`PBEKEYSPEC-NOBS-01` accuses the correct persisted-salt idiom.** PBKDF2 requires the *same* salt on every derivation after the first; a stored salt is by construction NOT_OBSERVED at `R/PBEKeySpecSpec.mop:148`. The file's comment discusses only the removed `randomized[password]` read (`:126-147`), not that `randomized[salt]` is satisfiable only on the first derivation of a process that also generated the salt.
15. **The `getEncoded` bridge requires a two-place exact match.** `R/SecretKeySpec.mop:122-123` asks `validate(GENERATED_KEY, secretKey, secretKey.getAlgorithm())`; `SecretKeyFactorySpec.mop:108` writes `canonical("SecretKeyFactory", alg)` (e.g. `PBKDF2WithHmacSHA256`) and `KeyGeneratorSpec.mop:223` writes `canonical("KeyGenerator", <getInstance string>)`. If a provider's key reports a different `getAlgorithm()` string than the canonical service name (the comment at `:96-101` measured only the Blowfish case for KeyGenerator), the bridge answers VIOLATED, stages nothing, and the re-wrap `new SecretKeySpec(k.getEncoded(), "AES")` draws SECRETKEYSPEC-NOBS-00. `KeySpec.mop:79` has the same exposure. Not measured here; flagged as the one place where a spelling mismatch surfaces three files downstream as a NOBS.
16. **`Cipher.init` in DECRYPT/UNWRAP mode reads key origin exactly as ENCRYPT does** (`R/CipherSpec.mop:168-233`, no mode test). A key unwrapped/derived for decryption is CIPHER-NOBS-00 as often as for encryption; consistent with `Cipher.crysl:134`, just noting the code carries no mode information for the reader.
17. **`KEYAGREEMENT-NOBS-08` and `SSLCONTEXT-NOBS-0x` are `after` advices** (`G/MultiSpec_1MonitorAspect.aj:575,907`) — under dexlib2 a `doPhase`/`init` that throws yields no report while under ajc it does; the campaign ran dexlib2 (memory: "dexlib2 roda no host"), so these counts exclude throwing calls, whereas the `before`-advised codes (CIPHER, MAC, SIGNATURE, IVCHAINJUNCTION, KMF/TMF) include them.
18. **Minor:** `R/PBEKeySpecSpec.mop:43-47` and `:126-147` mention PBEKEYSPEC-NOBS-00 as removed; `codes.csv` indeed has only NOBS-01 — the campaign's `PBEKEYSPEC-NOBS-01` is the salt read, not a renumbered password read.
