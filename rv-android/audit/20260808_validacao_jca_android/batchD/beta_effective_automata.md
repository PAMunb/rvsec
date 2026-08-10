# Agent Beta — Batch D effective automata (MAC, MDG, KPG, SRD, SIG)

Source: the ORDER expression **read from the generated `.rvm`** (D-piloto-3: the
effective artifact, not the `.mop` syntax) plus the minimized state count from the
production `CoenableProbe` walk over `ere.jar`/`fsm.jar` (`beta/probes`,
`beta_coenable_summary.txt`). Alphabet and event→call mapping cross-checked against
the `RuntimeMonitor.java` event entry points and the android-30 member tables
(`beta/capture/member_tables.txt`). Category `fail`/`match` handlers from the `.mop`.
All five `.rvm` are byte-identical to the round input (`beta_hashes.txt`).

Convention: `α` maps a real android-30 call → CrySL event → MOP event. Fusions
(many calls → one MOP event) and splits (one CrySL event → many MOP events) are
noted. "dead" = the pointcut cannot match a real member (wrong return type / unbound
`target`) so the event never fires on either weave path. "unbound" = the MOP event
omits the spec parameter, so it dispatches through the process-global root monitor.

---

## MAC — `MacSpec(Mac m)`, ere, 11 events, 4 states after minimization

```
ere: (g3* g1 | g3* g2) (i1 | i2) ((uArr | uByte | uBuf)* (f1 | f2 | f3))
```

| MOP event | android-30 member | CrySL | binding | note |
|---|---|---|---|---|
| g1 | `getInstance(String)` safe | g1 | returning m (per-obj) | merged advice with g3 on the 1-arg pointcut |
| g2 | `getInstance(String,String)` safe | g2 | returning m | |
| g3 | `getInstance(String)` unsafe | (g1 unsafe complement) | returning m | `g3*` prefix, no advance |
| i1 | `init(Key)` | i1 | target m + GENERATED_KEY guard | |
| i2 | `init(Key,AlgorithmParameterSpec)` | i2 | target m | reads PREPARED_HMAC in body |
| uArr | `update(byte[])`, `update(byte[],int,int)` | u2,u3 | target m | fusion 2→1 |
| uByte | `update(byte)` | u1 | target m | boxes byte → Byte-cache over-mark (D-S13) |
| uBuf | `update(ByteBuffer)` | — (not in rule) | target m | body empty: documented FN (ByteBuffer data never MACED) |
| f1 | `doFinal()` | f1 | target m (per-obj) | |
| f2 | `doFinal(byte[])` | f2 | args+target m (per-obj) | |
| **f3** | **`doFinal(byte[],int)`** | f3 | **args only — NO `Mac m` formal** | **UNBOUND: dispatches to the global root `MacSpec__Map`; ajc leaves it dead (invalidAbsoluteTypeName on `target(m)`)** |

Effective language (module α, per-object m): `Gets Inits (Updates* Final)`, accepting
after any of `f1|f2`. **f3 is not per-object**: on the dexlib2 path it advances a
process-global Mac monitor (any `doFinal(byte[],int)` anywhere), on ajc it never fires
(dead pointcut). So the per-object effective automaton that the two-object drive
exercises omits f3 entirely, and the third finalization overload is realized by
neither faithfully (critical, BETA-MAC-01; jca-inherited — the jca twin's f2 has the
same missing `m`).

Root monitor `MacSpec__Map` is a single process-global `Tuple2` (`RuntimeMonitor
:9490`); per-object events index `MacSpec_m_Map` by the `Mac` weak ref.

---

## MDG — `MessageDigestSpec(MessageDigest digest)`, ere, 8 events, 4 states

```
ere: (g4* g1 | g4* g2 | g4* g3) (d2 | (update+ (d1 | d2 | d3)))+
```

| MOP event | android-30 member | CrySL | note |
|---|---|---|---|
| g1 | `getInstance(String)` safe (toUpperCase) | g1 | merged advice with g4 |
| g2 | `getInstance(String,String)` safe | g2 | |
| g3 | `getInstance(String,Provider)` safe | (Provider overload; rule folds into g2 `_`) | modeled explicitly |
| g4 | `getInstance(String)` unsafe complement | — | `g4*` prefix |
| update | `update(..)` — byte, byte[], byte[]/int/int, ByteBuffer | u1..u4 | fusion 4→1; ByteBuffer captured (unlike MAC) |
| d1 | `digest()` | d1 | writes DIGESTED(out) |
| d2 | `digest(byte[])` | d2 | direct-digest branch (DWOU); UnsafeAlgorithm in body |
| d3 | `digest(byte[],int,int)` | d3 | writes DIGESTED(out) |

Effective language: `Gets (d2 | update+ (d1|d2|d3))+`. Accepting after any digest;
loops for streamed digesting. No dead/unbound events; every update overload (incl.
ByteBuffer) is captured. `reset()` (android-30 member) is deliberately not modeled
(CrySL has no reset — D-S12), correctly UNCAPTURED on both paths. Merged advice g1→g4
is benign (g1 sets `currentAlgorithmInstance` before g4's condition reads it;
verified by MDG-c live). Global root `MessageDigestSpec__Map`; per-object by `digest`.

---

## KPG — `KeyPairGeneratorSpec(KeyPairGenerator k)`, ere, 9 events, 4 states

```
ere: (g3* g1 | g3* g2) initError* (init1 | init2 | init3 | init4) initError* gen
```

| MOP event | android-30 member | CrySL | note |
|---|---|---|---|
| g1 | `getInstance(String)` safe {DH,DSA,RSA} | g1 | merged advice with g3 |
| g2 | `getInstance(String,String)` safe | g2 | |
| g3 | `getInstance(String)` unsafe complement | — | **now flags EC** (gh101 removed EC from the safe list) |
| init1 | `initialize(int)` valid keysize | i3 | UnsafeAlgorithm in body |
| init2 | `initialize(int,SecureRandom)` valid | i4 | |
| init3 | `initialize(AlgorithmParameterSpec)` | i1 | reads PREPARED_DH in body |
| init4 | `initialize(AlgorithmParameterSpec,SecureRandom)` | i2 | reads PREPARED_DH |
| initError | `initialize(int)` invalid keysize | — (violating branch of i3) | InvalidKeySize; admitted `initError*` both sides of the init |
| gen | `generateKeyPair()` **or** `genKeyPair()` | k1,k2 | writes GENERATED_KEY_PAIR(kp) |

Effective language: `Gets initError* Init initError* gen`. Accepting after `gen`.
The `initError*` around the init is the gh101 repair (initError was all-fail before).
**gen is a disjunctive pointcut** `generateKeyPair() || genKeyPair()`: on dexlib2 only
the first disjunct (`generateKeyPair`) gets a wrapper — `genKeyPair()` is UNTOUCHED
(FEN-SET-firstcall-disjunct, BETA-KPG-02, silent FN on dexlib2; ajc captures both).
Unsafe route (EC): g3 then init1 → the automaton has only seen g3, so init1 is a
sequence violation → UnsafeAlgorithm (correct) + InvalidSequenceOfMethodCalls
(spurious residue), BETA-KPG-03. Global root `KeyPairGeneratorSpec__Map`; per-object
by `k`.

---

## SRD — `SecureRandomSpec(SecureRandom r)`, fsm, 15 events, 4 states — ROUND REFERENCE

Effective transition table (from the generated `.rvm` fsm, the authoritative artifact;
`match1 = init`, i.e. `init` is the only accepting state):

```
start [ c1->init  c2->init  c3->unsafeInit  g1->init  g2->init  g3->init  g4->unsafeInit ]
init  [ c1->init  genSeed->end  setSeed1->end  setSeed2->end  setSeed3->end
        next1->end  next2->end  next3->end  ints->end ]
end   [ genSeed->end  setSeed1->end  setSeed2->end  setSeed3->end
        next1->end  next3->end  ints->end ]            # note: next2 absent from `end`
unsafeInit [ genSeed->unsafeInit  setSeed1->unsafeInit  setSeed2->unsafeInit
             setSeed3->unsafeInit  next1->unsafeInit  next2->unsafeInit
             next3->unsafeInit  ints->unsafeInit ]
alias match1 = init
```

15 events → 4 minimized states. `Ins Seeds? Ends*` from CrySL, split into three
creation targets: `init` (accepting, `c1/c2/g1/g2/g3`), `unsafeInit`
(non-accepting sink, `c3/g4` — the object exists and downstream calls are admitted so
they do not accuse, but no path returns to `init`), and `end` (post-consume,
non-accepting but not fail). Any symbol not in a state's row → `fail`.

| MOP event | android-30 member | CrySL | binding/writer | note |
|---|---|---|---|---|
| c1 | `new SecureRandom()` | c1 | ctor inline-AFTER | writes RANDOMIZED(sr) via @match1 |
| c2 | `new SecureRandom(byte[])` randomized seed | c2 | ctor, RANDOMIZED guard | |
| c3 | `new SecureRandom(byte[])` non-rand seed | c2 (violating) | → unsafeInit, **silent** | REQUIRES randomized[seed] on ctor NOT diagnosed (FN, jca-inherited, BETA-SRD-04) |
| g1 | `getInstance(String)` SHA1PRNG | g1 | merged advice with g2,g4 | |
| g2 | `getInstance(String,..)` args(alg,\*) safe | g2 | — | **`..`+args(alg,\*)**: dexlib2 groups g2 onto the 1-arg wrapper (FEN-SET-VARARGS-ARGS-IGNORED, BETA-SRD-01) |
| g3 | `getInstanceStrong()` | gI | | |
| g4 | `getInstance(String,..)` args(alg) unsafe | — | → unsafeInit, UnsafeAlgorithm | args(alg)=1-arg only ⇒ 2-arg unsafe getInstance is a **silent FN on ajc** (BETA-SRD-02) |
| setSeed1 | `setSeed(long)` | s2 | | |
| setSeed2 | `setSeed(byte[])` randomized | s1 | RANDOMIZED guard | |
| setSeed3 | `setSeed(byte[])` non-rand | s1 (violating) | UnsatisfiedConstraint | the ctor path (c3) has no such report — asymmetry |
| genSeed | `generateSeed(int)` | gS | writes RANDOMIZED(ret) | producer of the set-wide RANDOMIZED edge |
| next1 | `nextInt(int)` | (ne) | writes RANDOMIZED(**boxed bound**) | marks the argument, not the return (TODO in spec) |
| next2 | `nextBytes(byte[])` | nB | writes RANDOMIZED(bytes) | producer |
| next3 | `nextInt()` | — (not in rule) | writes RANDOMIZED(boxed ret) | non-cached box lost by the identity store (BETA-SRD-05) |
| ints | `ints(..)` | — (not in rule) | writes RANDOMIZED(stream) | all four `ints` overloads captured on ajc |

**SRD is the WRITER of RANDOMIZED consumed across the whole set** (c2/setSeed2 readers
in SRD itself; SecureRandom feeds KeyPair/KeyStore/Cipher elsewhere). Producers
genSeed/next1/next2/next3/ints all fire and write on the ajc path (SRD-a live). But
`nextInt()`/`ints(..)` are **UNTOUCHED on dexlib2** (no declared wrapper hit;
inherited/non-declared members) so those RANDOMIZED writes are dead on the device
path (DX-SRD-2), while `nextBytes`/`generateSeed` (declared, inline/wrapped) survive.

Global root `SecureRandomSpec__Map`; per-object by `r`. All events bind `r` (target or
returning), so no unbound-event defect here — SRD's problems are capture-side
(`..`+args over/under-expansion) and the identity store's boxing, not binding.

---

## SIG — `SignatureSpec(Signature s)`, ere, 12 events, 8 states

```
ere: (g3* g1 | g3* g2) ( ((i1|i2)+ (update+ (s1|s2)+)+)+ | ((i3|i4)+ (update* (v1|v2)+)+)+ )
```

| MOP event | android-30 member | CrySL | note |
|---|---|---|---|
| g1 | `getInstance(String)` safe | g1 | merged advice with g3 |
| g2 | `getInstance(String,String)` safe | g2 | |
| g3 | `getInstance(String)` unsafe complement | — | `g3*` prefix |
| i1 | `initSign(PrivateKey)` | i1 | reads GENERATED_PRIVATE_KEY (writer: KeyStore/KeyPair spec) |
| i2 | `initSign(PrivateKey,SecureRandom)` | i2 | reads GENERATED_PRIVATE_KEY |
| i3 | `initVerify(Certificate)` | i3 | |
| i4 | `initVerify(PublicKey)` | i4 | reads GENERATED_PUBLIC_KEY |
| update | `update(..)` — byte/byte[]/byte[]int int/ByteBuffer | u1..u4 | fusion 4→1; ByteBuffer captured |
| **s1** | `sign()` → **`byte[]`** | s1 | **pointcut declares return `byte` — dead: `sign()` never matches** (BETA-SIG-01) |
| **s2** | `sign(byte[],int,int)` → **`int`** | s2 | **pointcut declares return `byte` — dead** |
| v1 | `verify(byte[])` | v1 | writes VERIFIED |
| v2 | `verify(byte[],int,int)` | v2 | writes VERIFIED |

Two branches (sign vs verify) → 8 minimized states. **The entire sign() family (s1,s2)
is dead**: both pointcuts declare return type `byte`, but android-30 `sign()` returns
`byte[]` and `sign(byte[],int,int)` returns `int`. UNCAPTURED on ajc (capture matrix)
and no wrapper on dexlib2 (WrapperEmitter enumerated only getInstance×2 + verify×2).
Consequences: SIGNED is never written; the sign branch never reaches acceptance; a
legal `getInstance; initSign; update; sign; initSign` trace is reported as
InvalidSequenceOfMethodCalls because the monitor never advanced past the dead s1
(BETA-SIG-01, critical, jca-inherited — same `byte` return in the jca twin). The
verify branch is faithful (v1/v2 captured, VERIFIED written, two-object isolated —
SIG-a/SIG-d live). Global root `SignatureSpec__Map`; per-object by `s`.
