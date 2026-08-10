# Agent Beta report — Batch D (MAC, MDG, KPG, SRD, SIG)

Agent Beta (toolchain red team), 2026-08-09. FINAL batch. Scope: MacSpec (MAC),
MessageDigestSpec (MDG), KeyPairGeneratorSpec (KPG), SecureRandomSpec (SRD),
SignatureSpec (SIG) — the five heaviest of the round, per `batchD/generation_manifest.md`.
Round rules honored: D-piloto-1 (ORDER reading A), D-piloto-3 (effective automaton is
the evidence source — `beta_effective_automata.md`), D-piloto-4 (dimension at creation;
SET claims separate; FEN-* ids; six normative states), D-batchA-1 (raw weighted sum),
D-batchB-1 (every FAIL row carries a `fenomeno_id`), REF-B-01 (every decisive
harness/output copied here and hashed), REF-B-09 (executable two-object/interleaving
drives for all five). Sequential Thinking MCP not used (not required; §8 is the
published decomposition). Labels: PROVADO / MEDIDO / OBSERVADO_EM_ARTEFATO / INFERIDO /
NAO_VERIFICADO. Every material claim has an executable leg.

## 0. Inputs, freeze checks — MEDIDO

- 5 `.mop` + 5 `.cryptsl` sha256 match `fase0/manifest_hashes.md` and
  `batchD/generation_manifest.md` exactly (`beta_hashes.txt`); all five diverge from the
  frozen `jca` twins.
- 19/19 round-input artifacts (`.rvm`/`.aj`/`.json`/`RuntimeMonitor.java`) match the
  generation manifest hash-for-hash.
- Toolchain frozen and reverified: javamop jar `ab4e3765…`, rv-monitor jar `fab40319…`,
  android-30 jar `96ccfdc8…` (= batchA/beta), instr-cli.jar `356e8b70…`, rvsec-core
  `7b4d72aa…`, rv-monitor-rt `0fa65fbc…`, aspectjtools 1.9.25.1 `b07ce76c…`. Java Temurin
  25.0.3.
- javap trap neutralized: member tables from class files **extracted** from the frozen
  android-30 jar (`beta_member_tables.txt`, `beta/capture/cls`).
- ajc IS executable this host (`lib_tmp/aspectjtools.jar`, the Docker version) — both
  weave halves closed for capture. ART/device execution remains the only unexecuted half
  (BETA-SET-06).

## 1. Generability / budget (G2) — MEDIDO

Independent regeneration in scratch (`beta/gen`, frozen toolchain, `-d out -merge
--emit-descriptor` then `rv-monitor -d out -merge`), `/usr/bin/time -v`. **All 19
artifacts byte-identical to the round input** (generator determinism; REF-11: not
independent replication). `CoenableProbe` over the production `ere.jar`/`fsm.jar` on the
ORDER read from each `.rvm`:

| Spec | events | states (min) | coenable[fail] | n·(2ⁿ−1) | EXACT | coenable_chars | rv-monitor wall/RSS |
|---|---|---|---|---|---|---|---|
| MAC | 11 | 4 | 22517 | 11·2047 | ✔ | 619 683 | 1.58 s / 204.7 MB |
| MDG | 8 | 4 | 2040 | 8·255 | ✔ | 41 213 | 1.01 s / 98.9 MB |
| KPG | 9 | 4 | 4599 | 9·511 | ✔ | 138 409 | 1.08 s / 108.7 MB |
| SIG | 12 | 8 | 49140 | 12·4095 | ✔ | 1 377 409 | 2.20 s / 288.5 MB |
| **SRD** | **15** | **4** | **491505** | **15·32767** | ✔ | **24 084 738** | **12.57 s / 1610.9 MB** |

All ≤ 17-event ceiling. **SRD is the round's stress case** — 15 events, 491 505 saturated
coenable sets, a 24.08 MB coenable string, generated in 12.57 s / 1.61 GB RSS (3 reps
12.57/12.06/12.95 s; RuntimeMonitor byte-identical across reps and to the round input).
Every @fail set is EXACTLY n·(2ⁿ−1) — saturated: the failure category enumerates the full
power set of coenabled events, so cost grows as n·2ⁿ. **The 17-event ceiling reproduces
from THIS data point**: at 15 events RSS is already 1.6 GB; 17 would be 2 228 207 sets
(~4.5× the string) → multi-GB, the wall the ceiling encodes (BETA-SET-01/02, PASS). Full
23-spec `-merge` in scratch: javamop 0.70 s / 174.8 MB, rv-monitor 28.08 s / 1.74 GB; the
five per-spec `.rvm` are byte-identical to the merge outputs.

**One generation surprise (method note, not a defect claim)**: with `-merge` the JavaMOP
launcher writes `<Spec>.rvm` **next to the spec**, not into `-d out` — so a naive
`rv-monitor out/*.rvm` finds nothing (exit 0, "Target file doesn't exist", no monitor).
The pipeline moves the `.rvm` into `out/` before rv-monitor; the audit reproduces that.

## 2. Artifact chain (G6 static half) — MEDIDO / OBSERVADO_EM_ARTEFATO

- **Descriptor ↔ aspect 1:1** for all five (programmatic): MAC 10 advices/11 monitorCalls,
  MDG 7/8, KPG 7/9, SRD 13/15, SIG 11/12 — every count matches between `.json` and `.aj`.
- **Merged-advice shape** recurs where two events share a pointcut on a fixed order: MAC
  g1→g3, MDG g1→g4, KPG g1→g3 and init1→initError, SRD c2→c3 / setSeed2→setSeed3 /
  g1(safe)+g4(unsafe), SIG g1→g3. Benign where verified (MDG-c live: g1 sets the field
  before g4's condition reads it).
- **Advice kinds**: getInstance/doFinal/digest/generateKeyPair/sign?/verify are `after
  returning`; init/initSign/initVerify/update are `before`; SRD ctor/next are inline
  `after`. None `around`/`throwing`.
- **Standalone compile**: each of the five `RuntimeMonitor.java` compiles standalone
  against the production runtime (javac exit 0, 0 errors) — **none carries the KGN
  missing-import masking defect batch C found**; the merged `MultiSpec_1RuntimeMonitor`
  compiles clean too (57 classes) (BETA-SET-03, PASS).
- **Indexing** (BETA-SET-05, PASS): every spec has a process-global root `Tuple2`
  (`MacSpec__Map` `:9490`, etc.) AND per-object maps keyed by the monitored object weak
  ref (`MacSpec_m_Map`, dispatch `g1` `:11-22`). Two-object drives isolate A/B on the
  bound events in 4 specs. The exception is the **unbound** MAC f3 (§4.1), which uses only
  the global root.

## 3. Capture vs real android-30, both halves (G5) — MEDIDO

ajc 1.9.25.1 compile-time weave of `beta_BetaCaptureD.java` (one method per member, never
executed) against the merged 23-spec aspect, capture from `-showWeaveInfo`. Production
dexlib2 via `beta_BetaWeaveProbeB.java` (batch B/C harness verbatim) over a synthetic DEX
of 68 sites, DescriptorReader → TypeResolver → AndroidClassIndex(android-30) →
WrapperEmitter → DexWeaver — nothing reimplemented. Full matrix in
`beta_capture_matrix.txt`. Member tables from extracted class bytes.

Clean captures (both halves agree): MDG is faithful end to end (all 4 update overloads
incl. ByteBuffer, all 3 getInstance incl. Provider, all 3 digest; `reset()` correctly
UNMODELLED per D-S12). SRD c1/c2/c3, g1/g3, setSeed, genSeed, next1/next2 captured on
both. SIG initSign/initVerify/update/verify captured on both. MAC getInstance(String/
String,String)/init/update×3(incl. ByteBuffer)/doFinal()/doFinal(byte[]) captured on both.

**Capture defects (per spec, each with the executable leg):**

- **BETA-MAC-01 (critical, FEN-D-UNBOUND-EVENT)** — MAC f3 `doFinal(byte[],int)` declares
  `after(byte[] output, int outOffset)` **without a `Mac m` formal** yet uses `target(m)`.
  ajc emits `invalidAbsoluteTypeName` at `MonitorAspect.aj:479` and the site is UNCAPTURED
  (dead); dexlib2 emits `MacSpec_f3Event(output,outOffset)` dispatched through the
  **global root** `MacSpec__Map`. Live (dex drive, 3 reps): `DX-MAC-anon` fires
  InvalidSequenceOfMethodCalls with no live Mac monitor; `DX-MAC-bcast` puts an unrelated
  Mac B into accepting then InvalidSeq — a process-global broadcast. **The two halves
  disagree** (ajc dead / dexlib2 broadcast) and both are wrong. jca-inherited (the jca
  twin's f2 has the same missing `m`).

- **BETA-SIG-01 (critical, FEN-D-WRONG-RETURN)** — SIG s1/s2 declare `call(public byte
  Signature.sign()…)` but android-30 `sign()` returns `byte[]` and `sign(byte[],int,int)`
  returns `int` (member table). `sig_sign0`/`sig_sign3` UNCAPTURED on ajc AND no wrapper
  on dexlib2 (WrapperEmitter enumerated only getInstance×2 + verify×2). **The entire
  sign() family is dead on both halves**: SIGNED never written, the sign branch never
  accepts, and a legal `getInstance;initSign;update;sign;initSign` is reported
  InvalidSequenceOfMethodCalls because the monitor never saw s1 (drive SIG-b1/b2,
  DX-SIG-1/2, 3 reps). jca-inherited (same `byte` return in the twin).

- **BETA-SRD-01 (critical, FEN-SET-VARARGS-ARGS-IGNORED)** — SRD g2 is `call(getInstance
  (String,..)) && args(alg,*)`. `WrapperEmitter.expandCallTarget` reads only `call()` and
  ignores `args()` (`WrapperEmitter.java:326-400`), expanding the trailing `..` onto every
  overload incl. the 1-arg `getInstance(String)`. So the 1-arg wrapper fires g1,g2,g4
  (`beta_MonitorWrappers_multispec.java`). On the fsm: g1 (start→init) then g2 (init has
  no g2 → **fail**). **Every legal `getInstance("SHA1PRNG")` raises a spurious
  InvalidSequenceOfMethodCalls** on the dexlib2 path (drive DX-SRD-1, 3 reps). ajc fires
  only g1+g4 on the 1-arg site — the halves disagree. jca-inherited; recurs from batch C
  (KMF/TMF). **Critical FP on the correct call.**

- **BETA-KPG-02 (critical, FEN-SET-firstcall-disjunct)** — KPG gen is
  `call(generateKeyPair()) || call(genKeyPair())`. `WrapperEmitter.findFirstCall` takes
  only the first `call()` disjunct (`WrapperEmitter.java:507-524`); `kpg_gen` WRAPPED but
  `kpg_genkp` UNTOUCHED on dexlib2 (WeaveReport `plansSkippedAliasing=1`); ajc captures
  both. Live: `DX-KPG-2` — a KeyPair from `genKeyPair()` never marks GENERATED_KEY_PAIR,
  never accepts (3 reps). Halves disagree. jca-inherited. **Silent FN on production
  dexlib2.**

**Omissions (OMITIDA):**

- **BETA-{MAC,KPG,SIG}-02/04/02 (major, FEN-D-GETINSTANCE-PROVIDER)** — MAC/KPG/SIG model
  g2 as exact `getInstance(String,String)`, so the android-30 `getInstance(String,
  Provider)` overload is UNCAPTURED on both halves (`mac_gi2p`/`kpg_gi2p`/`sig_gi2p`). The
  CrySL g2 uses an anonymous `getInstance(alg,_)` that abstracts both overloads. MDG (g3
  explicit) and SRD (`..`) capture it; three of five specs drop it. A getInstance with a
  Provider object is invisible — FN.
- **BETA-KPG-05 (major)** — CrySL requires 4 conditional REQUIRES (DH/DSA/RSA/EC ⇒
  prepared*[params]); init3/init4 read only PREPARED_DH; the other three have no Property
  constant (spec comment, Group 5). init with an arbitrary parameter spec for DSA/RSA/EC
  raises nothing.

**Documented limitations (D-S13):**

- **BETA-MAC-03** — MAC uBuf `update(ByteBuffer)` has an empty body: captured on both
  halves but never marks MACED (rule models no ByteBuffer update; the event exists only to
  keep the automaton place). ByteBuffer-fed data is a documented FN.
- **BETA-MAC-04 / BETA-SRD-05 (FEN-D-BOXING)** — MAC uByte boxes `byte`→`Byte` (whole byte
  range is in the cache, so one MACed byte marks every equal literal); SRD next1 marks the
  boxed **bound** (not the return) and next3's non-cached boxed return is lost by the
  IdentityHashMap (drive SRD-f). FP (cached) and FN (non-cached) of the identity store.

## 4. Executable drives of the generated monitors — PROVADO / MEDIDO

Two drives, both 3 reps byte-identical (`beta_drive_run1.out` sha `44707e71…`,
`beta_dexdrive_run1.out` sha `8a30966c…`):

- **`beta_BetaDriveD.java`** — ajc-woven (compile-time) with the merged 23-spec aspect;
  every call reaches the monitors through the REAL AspectJ capture path with real JDK
  objects.
- **`beta_BetaDexPathDriveD.java`** — calls the EXACT `mop/MonitorWrappers.java`
  WrapperEmitter emitted for the merged descriptor over android-30 (hash `f01dc17d…`),
  i.e. byte-for-byte what a dexlib2-rewritten site executes; inline BEFORE/ctor events
  invoked as `MonitorInvokeBuilder` emits them; UNTOUCHED sites run as plain calls.

Highlights beyond §3's criticals:

1. **MDG is the clean spec** (BETA-MDG-01/02, positive) — legal update+digest clean and
   accepting; lowercase safe alg (folding) clean; ByteBuffer/Provider captured; the
   merged g1→g4 advice order is benign.
2. **KPG initError* repair VERIFIED** (BETA-KPG-01, positive) — `initialize(1024)` reports
   InvalidKeySize, then `initialize(2048)` corrects and reaches accepting with **no
   spurious InvalidSeq** on the correction route (drive KPG-c). The gh101 `initError*` is
   real.
3. **SRD producer side VERIFIED on ajc** (BETA-SRD-06, positive) — @match1 writes
   RANDOMIZED(sr); genSeed/next1/next2 write RANDOMIZED; two-object isolated (SRD-a). SRD
   is the writer of the set-wide RANDOMIZED edge. **But next3/ints are UNTOUCHED on
   dexlib2** (BETA-SRD-03, major, FEN-SET-DECLARED-ONLY): AndroidClassIndex is
   declared-only, so `nextInt()`/`ints(..)` get no wrapper — those RANDOMIZED producers
   are dead on the device path (DX-SRD-2), while `nextBytes`/`generateSeed` (declared,
   inline/wrapped) survive.
4. **SIG verify branch VERIFIED** (BETA-SIG-03, positive) — i3/i4/v1/v2 captured, VERIFIED
   written, two Signatures isolated (SIG-d). The verify half is faithful; the sign half is
   dead (BETA-SIG-01). SIG i1/i4 read GENERATED_PRIVATE/PUBLIC_KEY against writers in
   KeyStoreSpec/KeyPairSpec (cross-spec edge, BETA-SIG-04, reader faithful).
5. **Unsafe-route residue** (BETA-MAC-06, KPG-03, and SIG unsafe, major,
   FEN-D-UNSAFE-RESIDUE) — the `g3*`-prefix specs stack a spurious
   InvalidSequenceOfMethodCalls on top of the correct UnsafeAlgorithm when an init/verify
   follows an unsafe getInstance (drive MAC-c1, KPG-b1, SIG-c1). KPG's EC exposure is
   **gh101-introduced** (EC removed from the safe list, aligning with the CrySL alg
   constraint {DSA,DH,RSA}); the residue mechanism itself is jca-inherited.
6. **SRD constructor-seed asymmetry** (BETA-SRD-04, major) — a `new SecureRandom(seed)`
   with non-randomized bytes → c3 → unsafeInit, **silent** (drive SRD-e1), while the same
   condition via `setSeed(byte[])` → setSeed3 → UnsatisfiedConstraint (SRD-e2). The CrySL
   REQUIRES randomized[seed] is diagnosed on the setter but not the constructor.
7. **SRD 2-arg unsafe getInstance FN on ajc** (BETA-SRD-02, major, FEN-D-G4-ARITY) — g4's
   `args(alg)` is 1-arg only, so `getInstance("NativePRNG","SUN")` reports nothing on ajc
   (drive SRD-d1); dexlib2 catches it by the same over-expansion that makes SRD-01 wrong.
8. **MAC condition-suppression** (BETA-MAC-05, major, FEN-D-COND-SUPPRESS) — i1 keeps the
   GENERATED_KEY check in `condition()`, so an unmonitored key drops the i1 transition and
   the following doFinal becomes a spurious InvalidSeq (drive MAC-d1) — the exact trap the
   spec's own i2 comment warns against, still present on i1.

## 5. Fail-open probes — MEDIDO (`beta_probes_summary.txt`)

Three probes (BETA-SET-04, major). P1 (SRD fsm target `endX` undefined): javamop+rv-monitor
exit 0, stderr warns "states used but never defined", **no RuntimeMonitor** — silent
drop. P2 (SIG ere symbol `iX` undefined): both exit 0, RuntimeMonitor PRESENT with an
orphan `iX` row — unknown symbol accepted. P3 (MAC ere unbalanced paren): "Logic Engine
Error: null", exit 0, no RuntimeMonitor. Every probe exits 0; a pipeline gated on exit
codes catches none. Consistent with batches A/B/C.

## 6. Provenance (jca twin diff, per finding)

Verified against the jca twins directly. **jca-inherited** (defect present pre-gh101):
MAC f3 missing `m` (twin f2 identical); SIG `byte` sign() return (twin identical); SRD g2
`..`+args and c3 silent constructor (twin identical); KPG gen `||` disjunction (twin
identical); the getInstance(Provider) omissions; the unsafe-route residue shape.
**gh101-introduced**: KPG EC leaves the safe list (`{DH,DSA,RSA}` vs twin
`{RSA,EC,DSA,DiffieHellman,DH}`), exposing the residue for EC — but aligning the safe list
with the CrySL alg constraint. **Toolchain defects** (outside both spec sets, jar-
independent): FEN-SET-VARARGS-ARGS-IGNORED (WrapperEmitter ignores `args()`),
FEN-SET-firstcall-disjunct (findFirstCall drops later disjuncts), FEN-SET-DECLARED-ONLY
(AndroidClassIndex is declared-only). Provenance routes G11/G13 accountability; it excuses
nothing — the oracle is the api30 rule.

## 7. Scientific log (decomposition, protocol §2)

Per spec, one loop: (Q) does the chain realize the spec on the real platform, and what
breaks it? (H) hypotheses from reading (unbound events, wrong return types, `..`/args
over-/under-expansion, disjunct drop, declared-only index, boxing, condition suppression,
unsafe-route residue, cross-spec edges); (T) discriminating tests with an executable leg
(hash-compare regeneration; production dexlib2 weave + ajc weave over the same members;
monitor drive with real JDK objects incl. two-object interleavings; CoenableProbe;
fail-open probes; javap over extracted bytes); (E) evidence with file:line and outputs;
(R) claims in `beta_claims.csv`; (U) uncertainties: ART/device execution (BETA-SET-06),
android-37.0 production-default jar (BETA-SET-07). No unknown was converted to PASS.

## 8. Files

- `beta_effective_automata.md` — effective automata for the 5 (D-piloto-3); the 15-event
  SRD table is the round's common reference for Alfa's language work.
- `beta_claims.csv` — 30 claims (10 PASS, 18 FAIL, 2 INCONCLUSIVE; 4 critical, 11 major,
  6 minor).
- `beta_capture_matrix.txt` — both-halves capture matrix (68 sites incl. neighbors).
- `beta_hashes.txt` — sha256 of every input and decisive output.
- Harnesses/outputs: `beta_BetaWeaveProbeB.java`, `beta_weave_scenarios_D.tsv`,
  `beta_weave_all_D.out`, `beta_MonitorWrappers_multispec.java`, `beta_BetaCaptureD.java`,
  `beta_BetaDriveD.java`, `beta_drive_run1.out`, `beta_BetaDexPathDriveD.java`,
  `beta_dexdrive_run1.out`, `beta_coenable_summary.txt`, `beta_probes_summary.txt`,
  `beta_member_tables.txt`.
- Scratch (ephemeral, not the replication package): `<scratchpad>/batchD/beta/` — gen,
  merge, weave, ajc, drive, probes, capture.
