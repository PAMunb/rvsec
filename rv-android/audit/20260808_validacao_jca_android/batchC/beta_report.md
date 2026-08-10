# Agent Beta report — Batch C (KGN, KMF, TMF, SSL, KST)

Agent Beta (toolchain red team), 2026-08-09. Scope: KeyGeneratorSpec (KGN),
KeyManagerFactorySpec (KMF), TrustManagerFactorySpec (TMF), SSLContextSpec (SSL),
KeyStoreSpec (KST), per `batchC/generation_manifest.md`. Round rules honored: D-piloto-1
(ORDER reading A), D-piloto-3 (effective automaton is the evidence source —
`beta_effective_automata.md`), D-piloto-4 (dimension at creation; SET claims separate;
FEN-* ids; six normative states), D-batchA-1 (raw weighted sum), D-batchB-1 (every FAIL
row carries a `fenomeno_id`), REF-B-01 (every decisive harness/output copied here and
hashed), REF-B-09 (executable two-object/interleaving drives for all five). Sequential
Thinking MCP not used (not required; §8 is the published decomposition). Labels: PROVADO /
MEDIDO / OBSERVADO_EM_ARTEFATO / INFERIDO / NAO_VERIFICADO. Every material claim has an
executable leg.

## 0. Inputs, freeze checks — MEDIDO

- 5 `.mop` + 5 `.cryptsl` sha256 match `fase0/manifest_hashes.md` and
  `batchC/generation_manifest.md` exactly (`beta_hashes.txt`).
- 20/20 round-input artifacts match the generation manifest hash-for-hash.
- Toolchain frozen: javamop jar `ab4e3765…`, rv-monitor jar `fab40319…`, android-30 jar
  `96ccfdc8…` (= batchA/beta), instr-cli.jar `356e8b70…`, rvsec-core `7b4d72aa…`,
  rv-monitor-rt `0fa65fbc…`, aspectjtools 1.9.25.1 `b07ce76c…`, rvsec-logger-csv
  `6787f411…`. Java Temurin 25.0.3.
- javap trap neutralized: member tables from class files **extracted** from the frozen
  android-30 jar (`beta_hashes.txt`, extraction under `beta/capture/cls`).
- **ajc IS executable this host** via `lib_tmp/aspectjtools.jar` (AspectJ 1.9.25.1, the
  Docker version) — so batch C closes the ajc capture half that batch B held pending. ART
  execution remains the only unexecuted half (G6/G10, BETA-SET-08).

## 1. Generability / budget (G2) — MEDIDO

Independent regeneration in scratch (`beta/gen/g_<Spec>`, frozen toolchain,
`-d out -merge --emit-descriptor` then `rv-monitor -d out -merge`), `/usr/bin/time -v`.
**All 20 artifacts byte-identical to the round input** (generator determinism; REF-11: not
independent replication). The `-merge` flag matters: without it, the RuntimeMonitor uses
unqualified event-method and category names (`i5Event` vs `KeyGeneratorSpec_i5Event`) and
diverges from the round input — production always passes `-merge`
(`runtime_verification_generator.py:211,267`).

| Spec | events | javamop wall/RSS | rv-monitor wall/RSS | CoenableProbe (production plugins) |
|---|---|---|---|---|
| KGN | 9 | 0.44 s / 88.9 MB | **1.08 s / 111.3 MB** | ere: fail=4599 = 9×(2⁹−1) saturado; match=0; **94595 chars** |
| KMF | 6 | 0.44 s / 87.2 MB | 0.92 s / 90.2 MB | fsm: fail=378 = 6×(2⁶−1) saturado; match1=0; 5864 chars |
| TMF | 6 | 0.44 s / 87.7 MB | 0.92 s / 90.7 MB | fsm: fail=378 = 6×(2⁶−1) saturado; match1=0; 5864 chars |
| SSL | 5 | 0.42 s / 87.8 MB | 0.92 s / 89.2 MB | fsm: fail=155 = 5×(2⁵−1) saturado; match1=2; 3584 chars |
| KST | 7 | 0.42 s / 87.7 MB | 0.97 s / 91.7 MB | ere: fail=889 = 7×(2⁷−1) saturado; match=4; 18065 chars |

All ≤ 17-event ceiling (max 9, KGN). **KGN confirmed the round's heaviest** — 4599 coenable
sets and a 94595-char string, yet rv-monitor generated it in 1.08 s / 111 MB (even higher
RSS than batch B's noted 108 MB; still tractable). All fail sets exactly `n×(2ⁿ−1)`
saturated (`beta_coenable_summary.txt`). Full 23-spec production `-merge` in scratch:
javamop 0.71 s / 179.9 MB; rv-monitor 28.98 s / 1.71 GB — consistent with batches A/B. The
five `.rvm` from the merge are byte-identical to the per-spec ones; the merged
`MultiSpec_1RuntimeMonitor.java` carries identical tables and indexing shapes
(`:9470` KGN per-object, `:9474` KMF per-object, `:9485` KST global Tuple2, `:9508` SSL
per-object, `:9528` TMF per-object) and **compiles clean** against the production runtime
(javac exit 0, 57 classes).

## 2. Artifact chain (G6 static half) — MEDIDO/OBSERVADO_EM_ARTEFATO

- **Descriptor ↔ aspect**: programmatic 1:1 comparison for all five — 28 advices, 33
  monitorCalls; every advice's pointcut expression, position, returning clause,
  monitorCall method list and argument list match between `.json` and `.aj` byte-for-byte.
  Merged-advice shape recurs where two events share a pointcut and fire in a fixed order:
  KGN g1→g3, KMF g1→g3, TMF g1→g3, SSL g1→unsafe_protocol, KST g1→g2 (aspect + descriptor
  agree on the order).
- **Advice kinds**: every advice is `after` or `before`; none `around`/`throwing`.
  getInstance/getKeyManagers/getTrustManagers/generateKey/getKey are `after returning`;
  init/load/store/getEntry/setEntry are `before`; SSL init/engine are plain `after`.
- **condition(...) prologue**: `return false` before the transition (suppression without
  transition) — KGN `:320`, KMF `:242`, KST `:289` — the pilot pattern.
- **Event body before transition**: ENSURES-style writes execute regardless of state —
  KST `Prop_1_event_load` writes GENERATED_KEY_STORE (`:325-337`) then transitions; proven
  live (KST-c writes the mark on the field, not the receiver).
- **__LOC**: present in every reporting body as `ViolationRecorder.getLineOfCode()`; the
  `mop.`-frame filter trap (batch B) does not bite the drives here — they sit outside
  package `mop` (errors carry `BetaDriveC.main(...)` locations, `beta_drive_run1.out`).
- **Stale category flags** (batch A/B): the merged-advice pattern recurs (KGN g1/g3,
  KMF/TMF g1/g3, KST g1/g2), and is BENIGN here — the two events sharing a pointcut are
  transition-compatible and their categories are recomputed after each `handleEvent`; no
  category state is left reachable between the two sibling calls (verified by the tables +
  drives; no double handler fired).

## 3. Capture vs real android-30, both halves (G5) — MEDIDO

Batch C closes both weave halves. **ajc 1.9.25.1** compile-time weave of `beta_BetaCaptureC.java`
(one method per call site, never executed) against the merged 23-spec
`MultiSpec_1MonitorAspect.aj`, capture read from `-showWeaveInfo` (`beta_capture_matrix.txt`).
**Production dexlib2** via `beta_BetaWeaveProbeB.java` (the batch B harness, reused
verbatim) over a synthetic DEX of 47 call sites (`beta_weave_scenarios.tsv`), driving
DescriptorReader → TypeResolver → AndroidClassIndex(android-30) → WrapperEmitter →
DexWeaver — nothing reimplemented (`beta_weave_all.out` per spec, `beta_weave_multi.out`
merged; identical behavior). Member tables from extracted class bytes (javap).

| Spec | Captured (both paths agree) | dexlib2-only DEFECT | Neighbors (0 hits) |
|---|---|---|---|
| KGN | 3 getInstance overloads (String; String,String; String,Provider via `Object+`); 5 init INLINE; generateKey WRAPPED | — (clean; `Object+` is exact-arity) | KeyPairGenerator, SecretKeyFactory, getAlgorithm |
| KMF | getInstance ×3 WRAPPED; init ×2 INLINE; getKeyManagers WRAPPED | **1-arg getInstance wrapper ALSO fires g2** (FEN-SET-VARARGS-ARGS-IGNORED) | getDefaultAlgorithm |
| TMF | getInstance ×3 WRAPPED; init ×2 INLINE; getTrustManagers WRAPPED | **1-arg getInstance wrapper ALSO fires g2** (same FEN) | getDefaultAlgorithm |
| SSL | getInstance ×2 WRAPPED; init WRAPPED | **createSSLEngine 0 wrappers (void-return pointcut)**; getInstance(String,Provider) UNTOUCHED | getDefault, getSocketFactory |
| KST | getInstance(String) WRAPPED; load/store INLINE; getKey WRAPPED | **getEntry/setEntry UNTOUCHED (nested-type descriptor)**; getInstance 2-arg UNTOUCHED | setCertificateEntry, setKeyEntry, aliases |

Three critical toolchain findings, each with the executable leg above plus the source
mechanism:

1. **FEN-SET-VARARGS-ARGS-IGNORED** (BETA-KMF-02, BETA-TMF-03, mechanism BETA-SET-02) —
   KMF/TMF g2 is `call(getInstance(String, ..)) && args(alg, *)`. `WrapperEmitter.generate`
   reads only the `call()` target (`firstCallTarget`) and never the `args()` clause;
   `expandCallTarget` expands the trailing `..` to every overload with arity ≥ fixedPrefix,
   **including the 1-arg `getInstance(String)`**. So g2 is grouped onto the 1-arg wrapper
   and the merged wrapper fires `g1Event, g3Event, g2Event` on `getInstance("PKIX")`
   (`beta_MonitorWrappers_multispec.java`). On the automaton: g1 (0→1 waitingInit) then g2
   (1→3 **fail**). **Every legal 1-arg `getInstance("PKIX")` raises a spurious
   `InvalidSequenceOfMethodCalls`** — the FP lands on the *correct* usage. Proven live,
   3 reps byte-identical (DX-1/DX-2, `beta_dexdrive_run1.out`). ajc suppresses g2 on the
   1-arg site because it honors `args(alg, *)` (≥2 args) — so ajc and dexlib2 **disagree**.
   KGN escapes (its g2 uses `Object+`, exact 2-arity, no `..`); SSL escapes (exact
   `getInstance(String,String)`); KST g1/g2 share the 1-arg pointcut by design (mutually
   exclusive `condition`s). Critical FP, jar-independent mechanism, spec shape jca-inherited.

2. **FEN-SET-NESTED-TYPE-DESCRIPTOR** (BETA-KST-04, mechanism BETA-SET-03) —
   KST ge1/se1 take nested-type params `KeyStore$Entry`/`KeyStore$ProtectionParameter`.
   `TypeResolver.toDescriptor` does `replace('.','/')` with no nested-type handling and
   produces `Ljava/security/KeyStore/ProtectionParameter;` (slash) where the DEX descriptor
   is `Ljava/security/KeyStore$ProtectionParameter;` (dollar) — PROVEN with `TR.java` over
   the production class. The BEFORE plan never matches → `getEntry`/`setEntry` are silently
   UNTOUCHED on the dexlib2 path, while ajc weaves both. Silent FN; the CrySL-legal
   `sE, Stores` route becomes a spurious fail (DX-5c). Critical, jar-independent.

3. **FEN-SSL-ENGINE-MORTO** (BETA-SSL-02) — `createSSLEngine()` returns `SSLEngine` on
   android-30, but the SSL `engine` pointcut declares `void` (`.mop:90`, aspect `:59`).
   ajc: 0 join points; dexlib2: 0 wrappers. GENERATE_SSL_ENGINE is never written, the
   Engine? tail of the ORDER is unobservable, and the engine-before-init violation is
   invisible. **Both halves blind** — a spec defect, not a capture divergence.

Two omissions in the same dimension: SSL g2 models only `getInstance(String,String)`, so
the CrySL `getInstance(protocol, _)` Provider overload is uncaptured (BETA-SSL-03); KST
models both g1 and g2 as 1-arg `getInstance(String)`, so the CrySL 2-arg
`getInstance(keyStoreAlg, _)` is uncaptured (BETA-KST-03) — a keystore created via
`getInstance(type, provider)` is invisible.

## 4. Executable drives of the generated monitors — PROVADO/MEDIDO

Two drives, both 3 reps byte-identical:
- **`beta_BetaDriveC.java`** — ajc-woven (compile-time) with the merged 23-spec aspect, so
  every call reaches the monitors through the REAL AspectJ capture path with real JDK
  objects (`beta_drive_run1.out`, sha `86ffc383…`, 3 reps identical).
- **`beta_BetaDexPathDriveC.java`** — calls the EXACT `mop/MonitorWrappers.java`
  WrapperEmitter emitted for the merged descriptor over android-30 (hash-verified), i.e.
  byte-for-byte what a dexlib2-rewritten site executes; inline BEFORE events invoked as
  `MonitorInvokeBuilder` emits them (`beta_dexdrive_run1.out`, sha `48b60aae…`, 3 reps).

Highlights (ids = output lines):

1. **TMF gh101 repair VERIFIED** (BETA-TMF-02, positive) — all four defects copied from
   KMF are corrected in the frozen artifact: gtm1 binds `target(mf)` and dispatches
   per-object (`:465`); return type `TrustManager[]` (not `[][]`); constant
   `GENERATED_TRUST_MANAGERS` (not KEY); g3 has a live row `{0,3,3,3}` (not all-fail). The
   2-arg `remove` isolation is proven: tmf2's `@fail` withdraws only its own array mark and
   preserves tmf1's (TMF-b3/b4). Probe pF1 reconstructs the pre-gh101 g3 all-fail row in
   the frozen toolchain (`beta_probes_summary.txt`) — the repair is real and measured.
2. **SSL unsafe_protocol repair VERIFIED** (BETA-SSL-04, positive) — the jca twin declares
   `unsafe_protocol` with no `returning` (empty slice); jca_android adds
   `returning(SSLContext ctx)` (`.mop:53`), so the event now dispatches per-object and the
   observed protocol reaches the label (SSL-e: two contexts isolated). SSL init reads the
   three predicates the jca twin ignored (task 3.2): GENERATED_KEY_MANAGERS,
   GENERATED_TRUST_MANAGERS, RANDOMIZED — all three readers fire (BETA-SSL-05, SSL-a).
3. **KST repair VERIFIED** (BETA-KST-05, positive) — gk1 now writes all three key
   constants (GENERATED_KEY + PRIVATE + PUBLIC; jca twin wrote only GENERATED_KEY), so a
   private key from a keystore carries what Signature.initSign REQUIRES.
4. **The dexlib2 1-arg-getInstance FP** (BETA-KMF-02/TMF-03, critical) — DX-1/DX-2 above.
5. **KST global-monitor FP + wrong-object identity** (BETA-KST-02/08, critical) — no event
   binds the spec parameter `ks` (all bind `k`); the tree is a process-global Tuple2
   (`:498`). Two legal keystores interleaved → 4 spurious InvalidSequence (KST-b). Under
   the uncaptured 2-arg getInstance, load writes GENERATED_KEY_STORE on the FIELD (= last
   g1), not the receiver: measured mark(ksE)=true (never loaded) / mark(ksF)=false (loaded),
   and the mislabel chains to a spurious `UnsatisfiedConstraint` in `KMF.init(ksF)` (KST-c/d).
   jca-inherited (twin binds `k` too).
6. **The unsafe-algorithm/protocol residue** (BETA-KGN-05, KMF-04, TMF-04, SSL-06, major) —
   the unsafe route stacks 1–2 spurious `InvalidSequenceOfMethodCalls` on top of the
   correct `UnsafeAlgorithm`/`UnsafeProtocol`. KGN is the sharpest (no unsafeAlg state → 2
   spurious + fail-then-reset); KMF/TMF/SSL have the unsafeAlg/unsafeProtocol state so the
   getInstance itself is clean, but the init that follows fails (0→fail). The gh101 binding
   repair on TMF *exposes* this residue that was inert in the empty slice.
7. **KGN capture is the multi-overload SUCCESS** (BETA-KGN-02, positive) — the three
   getInstance overloads (via `Object+`), the five init overloads and generateKey all
   captured on both paths; the 1-arg wrapper fires ONLY g1/g3 (no g2 over-expansion,
   because `Object+` is exact-arity). This is the correct counterpart to the KMF/TMF `..`
   defect and the discriminator between them.
8. **KGN keySize CONSTRAINT omitted** (BETA-KGN-06) — `alg=AES ⇒ keySize∈{128,192,256}`
   has no code; the JDK provider throws for AES before the spec checks anything (KGN-d).
9. **KST marks a null key** (BETA-KST-07) — getKey on a missing alias returns null and the
   body writes GENERATED_KEY(null); `validate(GENERATED_KEY, null)` then succeeds (KST-a3).

## 5. Fail-open probes — MEDIDO (`beta_probes_summary.txt`)

Six probes on these five specs (BETA-SET-04, major). **New shape**: p1 (KGN stray `)` in
the ere) makes the ERE plugin print `Logic Engine Error: null` on stderr with **exit 0 and
NO RuntimeMonitor** (batch A absorbed the stray paren byte-identically; here it kills
generation silently). p3 (KST undefined ERE symbol) orphans ge1 with an all-fail row
`{4,4,4,4,4}`. pF1 (TMF g3 removed from the fsm — the exact pre-gh101 shape) emits an
all-fail g3 row `{3,3,3,3}` with exit 0 and **empty stderr** — the defect family regresses
with zero diagnostics. pF2/pF3 (alias/transition to an undefined state) warn on stderr but
exit 0 and omit the RuntimeMonitor. p5 (missing input) prints `[Error]` and exits 0. Every
probe exits 0; a pipeline gated on exit codes catches none.

## 6. gh101 record consistency — OBSERVADO_EM_ARTEFATO

`data/gh101/predicate_edges.csv:85` marks TMF `generatedTrustManagers` as
`wrong-constant … never written`, but the FROZEN artifact writes GENERATED_TRUST_MANAGERS
(`.mop:109`, verified — BETA-TMF-02); rows 26/59/60/61/82 mark `missing` edges the
artifacts realize (the KMF/TMF/SSL readers executed in the drives). The records are stale
(pre-repair) — claims, not evidence (pre-registration §1) — BETA-SET-06. Registered
omissions that ARE consistent: GENERATE_SSL_CONTEXT/ENGINE write-no-read (terminal,
`predicate_omissions.csv:5-7`), generatedManagerFactoryParameters no-constant
(`:16`, D-S14).

## 7. Provenance (jca twin diff, per finding)

All five specs diverge from their `jca` twins. Repairs INTRODUCED by gh101 (verified
positive): TMF's four-defect fix + g3 unsafeAlg state; SSL's `returning(ctx)` on
unsafe_protocol + init reading the three predicates (task 3.2); KST's three-key write;
the 2-arg `remove(Property, obj)` on KMF/TMF/KST @fail. Defects INHERITED from `jca`
(pre-gh101, still failing their gates): KST global monitor (twin binds `k`); the
unsafe-alg/protocol residue (same ere/fsm shape in both twins); KGN g1+/g2+ permissive
repetition; KMF/TMF g2 `getInstance(String, ..)` shape that triggers the dexlib2 FP. Toolchain
defects (outside both spec sets): FEN-SET-VARARGS-ARGS-IGNORED, FEN-SET-NESTED-TYPE-DESCRIPTOR.
Provenance routes G11/G13 accountability; it excuses nothing — the oracle is the api30 rule.

## 8. Scientific log (decomposition, protocol §2)

Per spec, one loop: (Q) does the chain realize the spec on the real platform, and what
breaks it? (H) hypotheses from reading (global monitor, unbound parameter, `..` over-expansion,
nested-type descriptors, void-return pointcut, unsafe-route residue, extra-oracle gates);
(T) discriminating tests with an executable leg (hash-compare regeneration; production
dexlib2 weave + ajc weave over the same call sites; monitor drive with real JDK objects incl.
two-object interleavings; TypeResolver harness; CoenableProbe; fail-open mutation probes;
javap over extracted bytes); (E) evidence filed with file:line and outputs; (R) claims in
`beta_claims.csv`; (U) uncertainties: ART/device execution + after-finally-vs-wrapper on
exceptional returns (BETA-SET-08), android-37.0 production-default jar (BETA-SET-07, REF-C-03).
No unknown was converted to PASS.

## 9. Files

- `beta_effective_automata.md` — effective tables/scopes for the 5 specs (D-piloto-3).
- `beta_claims.csv` — 40 claims (18 PASS, 20 FAIL, 2 INCONCLUSIVE; 7 critical, 8 major,
  5 minor).
- `beta_hashes.txt` — sha256 of every input and decisive output.
- Harnesses/outputs: `beta_BetaWeaveProbeB.java`, `beta_weave_scenarios.tsv`,
  `beta_weave_all.out`, `beta_weave_multi.out`, `beta_MonitorWrappers_multispec.java`,
  `beta_BetaCaptureC.java`, `beta_capture_matrix.txt`, `beta_BetaDriveC.java`,
  `beta_drive_run1.out`, `beta_BetaDexPathDriveC.java`, `beta_dexdrive_run1.out`,
  `beta_probes_summary.txt`, `beta_coenable_summary.txt`.
- Scratch (ephemeral, not the replication package): `<scratchpad>/batchC/beta/` — gen,
  merge, weave, ajc, drive, probes, capture.
