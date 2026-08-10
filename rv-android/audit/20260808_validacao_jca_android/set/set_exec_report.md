# SET-PHASE EXECUTOR report — executable half of the set-level verifications (protocol §19.5)

Date: 2026-08-09. Role: EXEC half of the set round — everything about the 23-spec
`jca_android` set measurable on this host. No verdicts are issued here; measured
evidence for the global judge. Claims: `set_exec_claims.csv` (30 rows:
22 FAIL / 8 PASS; 14 crítica / 7 major / 1 minor; every FAIL carries a
`fenomeno_id` per D-batchB-1). Hashes of every input and decisive output:
`set_exec_hashes.txt`. Deviations in force and applied: D-piloto-1..4,
D-batchA-1, D-batchB-1, D-batchC-1 (fail-open = crítica), D-batchD-1
(javap admissibility — §8 below).

Scratch (all generation and execution; never the spec tree):
`/tmp/claude-1000/-pedro-…-rv-android/d2ed0fb6-…/scratchpad/set/exec/`.
Freeze check first: the 23 `.mop` working-tree hashes match
`fase0/manifest_hashes.md` 23/23 (programmatic compare, 0 mismatches) — every
result below is about the frozen bytes.

Labels: **MEDIDO** = executed here with commands recorded; **PROVADO** = code
read at cited file:line; everything else labeled inline.

---

## 1. Full-set `-merge` generation (G2 set half) — EXEC-SET-01..03

Commands (production pipeline of `runtime_verification_generator.py:211,267`,
with `.rvm` kept for audit; `RH=$RVSEC_HOME`):

```bash
cp <specs>/*.mop specs/           # 23 frozen copies, scratch
/usr/bin/time -v $RH/javamop/bin/javamop -d out -merge --emit-descriptor specs/*.mop
mv specs/*.rvm out/               # javamop -d leaves .rvm beside the source
/usr/bin/time -v $RH/rv-monitor/bin/rv-monitor -d out -merge out/*.rvm
```

**MEDIDO** (two full runs; `set_exec_merge_times.txt`):

| Run | javamop wall/RSS | rv-monitor wall/RSS | exits | non-time stderr |
|---|---|---|---|---|
| run1 | 0.65 s / 163.2 MB | 28.42 s / 1.580 GB | 0 / 0 | empty |
| run2 | 0.70 s / 172.2 MB | 28.68 s / 1.584 GB | 0 / 0 | empty |

- Artifact inventory (26 files): `MultiSpec_1MonitorAspect.aj` (733 lines),
  `MultiSpec_1MonitorAspect.json`, `MultiSpec_1RuntimeMonitor.java` (16 900
  lines), plus the 23 per-spec `.rvm` (production deletes the `.rvm`; naming is
  `MultiSpec_1*` as the dexlib2 consumer expects).
- **Determinism**: run1 vs run2 — 26/26 artifacts byte-identical. The three
  `MultiSpec_1*` files are also byte-identical to the batch-D session's merge
  (`batchD/beta_hashes.txt`: `310fae06…` aj / `e91570ce…` json / `d6228eac…`
  java) — three independent generations, two sessions, one byte state.
- **Per-spec vs merge**: 23/23 per-spec `.rvm` byte-identical to the merge-run
  `.rvm`. All per-spec artifacts regenerated here hash-match the closed rounds'
  records: 80/80 (batches A–D generation manifests) + 8/8 (pilot
  `beta_hashes.txt` Cipher/GCM). `RandomStringPassword` (excluded from fidelity
  judgment by researcher decision, but part of the `-merge` set production
  generates) is recorded for the first time — 4 artifact hashes in
  `set_exec_hashes.txt`.
- Timing agrees with the batch-D record (0.70 s / 174.8 MB; 28.08 s / 1.74 GB);
  SRD remains the dominant rv-monitor cost, consistent with the closed
  generator-ceiling measurement.

**Which defects survive/change under `-merge`**: the `.rvm` identity plus the
descriptor identity in §2 mean the merge changes *packaging only* — every
per-spec defect the four rounds adjudicated survives verbatim (§§2–4 measure
this defect by defect). The one behavior that *changes* under merge is the KGN
compile masking (§3). No new masking and no collisions were found (§§2–3).

## 2. Descriptor lint over the merged set (G5/G6 set half) — EXEC-SET-04..13

Harness: `set_exec_descriptor_lint.py`; raw output
`set_exec_descriptor_lint_output.txt`. All **MEDIDO** on
`MultiSpec_1MonitorAspect.json` (`e91570ce…`).

- **Descriptor ↔ aspect 1:1**: 119 descriptor advices = 119 `.aj` advice
  headers; 119/119 descriptor expressions appear verbatim in the `.aj`.
- **monitorCalls ↔ monitor**: 140/140 monitorCalls resolve to
  `MultiSpec_1RuntimeMonitor` static methods with matching arity.
- **Per-spec counts**: 23 specs present. Advices/monitorCalls per spec: CIS 4/4,
  COS 5/5, CIP 13/14, DHG 1/1, GCM 2/2, HMC 1/1, IVP 2/4, KGN 8/9, KMF 5/6,
  KPG 7/9, KPR 3/3, KST 6/7, MAC 10/11, MDG 7/8, PBK 4/7, PBE 2/3, RSP 2/2,
  SSL 4/5, SKY 2/2, SKSS 2/4, SRD 13/15, SIG 11/12, TMF 5/6.
- **Merge = union, exactly**: for all 23 specs the per-spec descriptor's advice
  list is byte-equal to the merged block after normalizing the monitor-class
  prefix (`<Spec>RuntimeMonitor.` → `MultiSpec_1RuntimeMonitor.`). No advice is
  added, dropped, reordered, or fused by `-merge`. No wrapper-name collisions
  (83 unique wrapper names emitted by production `WrapperEmitter` on android-30).

**How each known per-spec defect manifests in the MERGED descriptor** (all
verbatim survivals; production consumes exactly these rows):

| Mechanism | Merged-descriptor row | Weave result (both jars) |
|---|---|---|
| MAC f3 unbound `target(m)` | `MacSpec_f3` params `[outOffset, output]`, expression ends `&& target(m)` | `mac_df_out` WRAPPED — fires with no Mac binding (broadcast path in monitor lines 6596–6615) |
| SIG sign return type | `SignatureSpec_s1/s2`: `call(public byte Signature.sign…)` (actual `byte[]`/`int`) | `sig_sign0`, `sig_sign3` UNTOUCHED (dead) |
| SSL createSSLEngine void | `SSLContextSpec_engine`: `call(public void SSLContext.createSSLEngine(..))` (actual returns `SSLEngine`) | `ssl_cse0`, `ssl_cse2` UNTOUCHED (dead) |
| KST nested types | `KeyStoreSpec_ge1/se1` use unqualified `Entry`/`ProtectionParameter` | `kst_getentry`, `kst_setentry` UNTOUCHED (dead) |
| First-disjunct drops | `CipherInputStreamSpec_r1` (`read()‖read(byte[])`), `CipherOutputStreamSpec_w1` (`write(int)‖write(byte[])`), `KeyPairGeneratorSpec_gen` (`generateKeyPair()‖genKeyPair()`) | first disjunct captured; `cis_readB`, `cos_writeB`, `kpg_genkp` UNTOUCHED |
| args() under trailing `..` | 10 rows (CIP g1/u1/u3/f2/f5, KMF g2, MAC uArr, SRD g2/g4, TMF g2) | present verbatim; SRD g2 is the row that reaches post-api30 members on the 37.0 jar (§5) |
| Declared-only index | `SecureRandomSpec_next3` (`nextInt()`), `_ints` (`ints(..)`) | UNTOUCHED (dead); `nextInt(int)` and `nextBytes` are captured (INLINE) |

This closes, with the merged descriptor, the batch-D routing item “descriptor
lint list for the set phase” — every mechanism is **silent at exit 0** and
visible only by artifact inspection (D-batchC-1's rationale re-confirmed).

## 3. Compile check (fail-open set half) — EXEC-SET-14

Classpath: `rv-monitor-rt.jar (0fa65fbc…)`, `rvsec-core.jar (7b4d72aa…)`,
`rvsec-logger-csv-0.9.3-SNAPSHOT.jar (6787f411…)`, `aspectjrt.jar (5765d5c8…)`;
javac Temurin 25. **MEDIDO** (`set_exec_standalone_compile.txt`):

- **Merged** `MultiSpec_1RuntimeMonitor.java`: compiles, exit 0 (2 unchecked
  warnings only).
- **Standalone, all 23** per-spec RuntimeMonitors: **22/23 compile; 1 fails** —
  `KeyGeneratorSpecRuntimeMonitor.java:259: error: cannot find symbol — Key
  generatedKey;`. Root cause: `KeyGeneratorSpec.mop` imports lack
  `java.security.Key` (its import block, `.mop` lines 3–10). Under `-merge`
  the imports union places `import java.security.Key;` at line 11 of the merged
  monitor — contributed by `CipherSpec.mop`/`KeyStoreSpec.mop` — masking the
  defect. This *verifies* FEN-KGN-NAOCOMPILA (batch C) and confirms the
  generator's fail-open (exit 0 for an uncompilable artifact) — crítica under
  D-batchC-1. **No new only-compiles-merged case exists** (the other 22 all
  compile standalone).

## 4. Fail-crash sweep over the 23 merged monitors — EXEC-SET-15

Harness: `set_exec_failcrash_sweep.py` (creation-initialized object fields →
dereference/switch sites → writers), output
`set_exec_failcrash_sweep_output.txt`; every flagged site then inspected
manually. **MEDIDO**:

- 13 dereference sites flagged in 6 monitor classes. **Exactly one is an
  unguarded throw-to-caller path**: `KeyPairGeneratorSpecMonitor.validate(int)`
  — `switch(algorithm)` at `MultiSpec_1RuntimeMonitor.java:5489`, with
  `algorithm` written only by creation events g1/g2/g3 (:5559/:5577/:5594) and
  the switch reachable from `Prop_1_event_init1/init2/initError`
  (:5607/:5626/:5670). This is FEN-KPG-NPE surviving `-merge` byte-for-byte.
- **Dynamic demonstration on the merged monitor** (composition drive S5):
  `KeyPairGeneratorSpec_init1Event` and `…_initErrorEvent` as first events on an
  unseen generator both **threw `java.lang.NullPointerException` to the
  caller** — in a woven APK the production advice calls these methods inline,
  so the app crashes (crash-to-app class).
- All 12 other flagged sites are guarded: the generator's `Ref_*` WeakReference
  reads are wrapped in `if (Ref_X != null)` (e.g. :6597–6600, :4575–4577);
  spec-authored helpers null-guard their operands — CipherSpec
  `reportUnrandomized`/`reportUnpreparedParams`/`reportMacedPlainText`
  (:3735–3757) and `isValid`/`modeOf` in
  `AndroidCipherTransformationUtil.java:168–171, 232–236`; KGN
  `reportUnrandomized` (:4875–4879); MAC `markAsMaced` (:6345–6353, null
  parameter explicitly tolerated). **The KPG NPE is the only member of its
  class in the whole set.**

## 5. BETA-SET-07 host-executable probe — android-37.0 (production default) vs android-30 (oracle) — EXEC-SET-11..13

Harness: `set_exec_WeaveProbe.java` — a rename-only copy of batch D's
`beta_BetaWeaveProbeB.java` (diff-verified) driving the **production dexlib2
pipeline** (`DescriptorReader → TypeResolver → AndroidClassIndex →
WrapperEmitter.generate → DexWeaver + expandWrapperReplacementsForApk →
weave`) from `instr-cli.jar (356e8b70…)`, over the **MERGED** descriptor, on a
synthetic DEX with one call site per scenario. Scenarios:
`set_exec_weave_scenarios.tsv` = union of the batch B/C/D scenario files plus
pilot-family rows (Cipher/GCM/IVP/DHG/PBE/SKSS) — **168 scenarios**. Runs: 2
reps per jar, byte-identical per jar. Outputs `set_exec_weave_android-30.out`,
`set_exec_weave_android-37.0.out`, delta `set_exec_weave_jar_diff.txt`.
**MEDIDO**:

- **Site capture: IDENTICAL across the two jars for all 168 scenarios** (50
  UNTOUCHED / 73 WRAPPED / 45 INLINE lines on both). `WeaveReport` identical:
  `matchesApplied=45, wrappersSubstituted=73, constructorInlineApplied=18,
  plansSkippedAliasing=10`, all other counters 0. Every divergence mechanism of
  §2 behaves the same under both jars — the five mechanisms are **jar-robust**,
  now measured with the merged descriptor. This is the host-executable half of
  BETA-SET-07 (REF-E-08) executed; the ART/device half remains the open G6/G10
  pendency.
- **Deltas, wrapper generation only**:
  1. android-37.0 emits **86 wrappers vs 83** — the 3 extras are
     `SecureRandom.getInstance(String, SecureRandomParameters[, String |
     Provider])`, reached by the SRD `g2` varargs row (`getInstance(String, ..)
     && args(alg, *)`). `SecureRandomParameters` exists in the frozen 37.0 jar
     (`unzip -l`: 1 class entry) and not in android-30 (0). Since production
     resolves the jar by lexicographic max (`ConfigResolver.java:111–127`,
     host = android-37.0; no rv-android call-site passes `--android-jar`),
     apps calling these API-33+ overloads get them woven and firing `g2` —
     members the api30 oracle does not model (extra-oracle capture, FP
     direction on API 33+ devices).
  2. **Wrapper-name permutation**: `java_security_MessageDigest_update_1/_2`
     swap members between jars (member-enumeration order). No capture effect
     (both overloads WRAPPED on both jars); artifact naming is
     jar-dependent — minor.

## 6. Cross-spec runtime composition probe (G7 set half) — EXEC-SET-16..26, 29

Harness: `set_exec_CompositionDrive.java` over the **compiled merged monitors**
(§3 classpath), real JDK objects, events emitted exactly as the merged
descriptor's advices do for production-captured calls (dead pointcuts emit
nothing); every error delta and the full `ExecutionContext` store dumped per
step. 3 reps from clean working dirs — **byte-identical**
(`sha256 8168d2a7…`; `set_exec_drive_rep1.out`). Supplementary probe
`set_exec_DedupeProbe.java`, 3 reps byte-identical (`3a658775…`). All
**MEDIDO**:

**S1 — SRD → RANDOMIZED → SKSS/PBK (the RANDOMIZED split, closed end to end)**
- Safe route: `new SecureRandom()` + `nextBytes` twice → RANDOMIZED written on
  the *object* (`r1`) **and** the *materials* (`salt`, `km1`); but the canonical
  sequence itself already emits `InvalidSequenceOfMethodCalls/SecureRandomSpec
  expecting=unknown` (the next2-repetition FP, batch D's D2 shape, now on the
  merged monitor — the shape H-SRD-1 matches).
- Rejected route: `getInstance("NativePRNG")` → `UnsafeAlgorithm … expecting one
  of SHA1PRNG` and `RANDOMIZED[r2]=false` (object-level sound), yet `next2`
  still writes `RANDOMIZED[km2]=true` (material from a rejected instance).
  **The real reader then accepts it**: `SecretKeySpecSpec c1/c3` over `km2` →
  0 errors, `SPECCED_KEY`+`GENERATED_KEY` written, monitor accepting —
  the executed FN direction, now writer→reader end to end.
- Negative control works: unmonitored material → `UnsatisfiedConstraint/
  SecretKeySpecSpec`, no marks.
- PBK: randomized salt suppresses the salt error (only the password-randomized
  demand remains); raw salt + weak params → 3 distinct errors (password, salt,
  `iterationCount >= 1000`).

**S2 — KGN → GENERATED_KEY → MAC / SKY**
- `KeyGenerator.generateKey` writes `GENERATED_KEY[skH]`; `Mac.init(skH)` is
  not suppressed; MAC run completes with 0 errors, accepting,
  `GENERATED_MAC`/`MACED` written (working edge).
- **Second writer measured live**: `SecretKeySpecSpec` c1/c3 *also* writes
  `GENERATED_KEY` (S1b store) — so MacSpec's (extra-oracle) key gate is opened
  by a non-KGN writer: `Mac.init(sks1)` not suppressed, 0 errors, accepting
  (FEN-SET-GENERATEDKEY-2A-CASA live at set level).
- **Second RANDOMIZED producer measured live**: `SecretKey.getEncoded` (SKY e1)
  marks the returned encodings `RANDOMIZED` (`enc1`, `enc2` in the store) —
  the `SecretKeySpec.mop:26` producer noted by batch D, executed.

**S3 — KPG → generatedKeyPair → KPR → SIG (the FP-toll edge)**
- Valid KPG sequence (RSA/2048): `GENERATED_KEY_PAIR[kp]` written, accepting.
- **The toll, measured**: each of `getPrivate`/`getPublic` emits
  `InvalidSequenceOfMethodCalls/KeyPairSpec expecting=unknown` *and still
  delivers* `GENERATED_PRIVATE_KEY[priv]` / `GENERATED_PUBLIC_KEY[pub]` —
  1 FP per access, no starvation; `Signature.initSign(priv)` passes with no
  requires error.
- **SIGNED starvation**: after a fully correct sign sequence, `sign()` emits
  no event (dead pointcut, §2) → `acc(sig)=false`, `SIGNED` never written,
  and **zero errors** — silent non-acceptance.
- **VERIFIED wrong slot**: real verification returns true; `v1` writes
  `VERIFIED` on the boxed `Boolean.TRUE`, not on the sign bytes
  (`VERIFIED[sigBytes]=false`).

**S4 — KST → GENERATED_KEY_STORE → KMF/TMF → SSL**
- KST: 1-arg `getInstance` fires g1+g2 (the double-emission measured in batch
  C) — automaton still accepts; `load` writes `GENERATED_KEY_STORE[ks]`
  (working edge).
- **KMF cascade**: JVM default algorithm SunX509 → `UnsafeAlgorithm (expecting
  PKIX)` + 2× `InvalidSequenceOfMethodCalls expecting=unknown`; `getKeyManagers`
  fires but `GENERATED_KEY_MANAGERS` is **not** written → SSL `init` then FPs
  (“requires key managers established by a monitored KeyManagerFactory
  sequence”) **and still writes `GENERATE_SSL_CONTEXT[ctx1]` and accepts** —
  error+mark+acceptance co-occur (fail-then-proceed). Threat declared: SunX509
  is the JDK default; Android's default is PKIX, so this specific cascade may
  not occur on-device — the durable finding is the co-occurrence pattern.
- TMF (PKIX): clean; `GENERATED_TRUST_MANAGER(S)` written (working edge).
- **SSL RANDOMIZED read is live** (dedupe probe X1): with km/tm marked and only
  the SecureRandom unmonitored, `init` emits `UnsatisfiedConstraint/…SecureRandom
  established by a monitored SecureRandom sequence` — the batch-C extra-oracle
  read, executed on the merged set. The event body
  (`Prop_1_event_init`) runs four independent checks — no short-circuit.
- `createSSLEngine()` executed: no event exists in the production weave (dead,
  §2) → `GENERATE_SSL_ENGINE` never written.

**Dedupe collapse (X2)** — with km AND random both unsatisfied at ONE call
site, exactly **one** record survives (key-managers; arrival order).
Mechanism at `ErrorDescription.java:109–139`: identity = `ErrorSummary`
(spec, type, class, method, loc) — `expecting` excluded by design comment;
`ErrorCollector.addError` drops the second (`ErrorCollector.java:40–44`,
logger-csv; the logcat collector shares the same `ErrorDescription` identity).
A detected violation is never recorded — emission loss at the collector,
crítica per §4's letter.

**Diagnostics census over the drive**: 14 error records total (S1a 1, S1c 1,
S1d 1, S1e 1, S1f 3, S3b 1, S3c 1, S4b 3, S4d 1, S4e 1); 5 carry
`expecting=unknown` (SRD S1a, KPR S3b/S3c, KMF S4b×2), and they accompany
exactly the executed FPs (G9 set half).

## 7. Config/selection checks (G12 set half) — EXEC-SET-27..28

**PROVADO** on current working-tree code (2026-08-09):

- `rv_experiment/config.py:688–693` — `jca_android` maps explicitly to
  `…/rvsec-mop/src/main/resources/jca_android`; unknown values and `custom`
  without a dir raise `ConfigurationError` (:695–712); `RVGeneratorConfig`
  receives `javamop_bin`/`rvmonitor_bin`/`mop_specs_dir` explicitly
  (:735–743). `DEFAULT_SPEC_SET = "jca"` remains a declared default
  (`constants.py:100`). Unchanged vs the fase-0 register
  (`toolchain_ambiente.md` §5): **no silent fallback in the monitor path**.
- Static path — **GAMA-SET-01/03 confirmed unchanged**:
  `rv_static_analysis/config.py:199–208` still defaults `mop_dir` to the
  literal `jca` directory when `targets_file` is unset; the android-jar probe
  list `["33","29","28","27","26"]` (:186) still lacks `"30"`; and
  `rv_experiment/config.py:892–953` (`get_static_analysis_config`) passes
  neither `mop_dir` nor `targets_file` nor `android_jar`, so both defaults
  apply to every `jca_android` run.

## 8. D-batchD-1 sweep of this phase's own outputs — EXEC-SET-30

No `javap` was executed in this phase; all platform-member evidence comes from
the production `AndroidClassIndex` reading the frozen jars' bytes. Trap-marker
sweep (`SecureRandomParameters|sun\.security|jdk\.internal`) over every
decisive output: **0 hits** in all android-30-labeled artifacts, the drive, the
dedupe probe, the lint and the sweep outputs; **3 hits** only in
`set_exec_weave_android-37.0.out`, where `SecureRandomParameters` is a genuine
member of the frozen android-37.0 jar (1 class entry by `unzip -l`; 0 in
android-30) — not host-JDK contamination.

## 9. Threats to validity (declared)

1. **JVM vs ART**: §§3–6 ran on Temurin 25; monitor/collector behavior on ART
   (dispatch, boxing caches, WeakReference timing, provider set) is the open
   BETA-SET-06 pendency. The KMF SunX509 cascade (S4b) is JVM-default-specific.
2. **Host vs Docker**: the weave probe used the host SDK jars (android-30 pin =
   oracle; android-37.0 = host production default). Docker resolves android-36 —
   a third capture surface not measured here (expected between the two by the
   same mechanism; not verified).
3. **ajc half**: the merged `.aj` was lint-checked, not compiled — `ajc` is
   absent from the host (Docker-only, per fase 0). The dexlib2 half is the
   production path measured.
4. **Scenario coverage**: capture equivalence across jars is asserted for the
   168 scenarios (union of all prior rounds' scenario files + pilot-family
   rows), not for every api30 member.
5. **Synthetic marks**: dedupe probe X1 marks km/tm via `setProperty` to
   isolate the random check; everything else in §6 uses only monitor-written
   marks.

## 10. Files written (all under `audit/…/set/`, `set_exec_` prefix)

`set_exec_report.md` (this file), `set_exec_claims.csv`, `set_exec_hashes.txt`,
`set_exec_merge_times.txt`, `set_exec_descriptor_lint.py` + `_output.txt`,
`set_exec_failcrash_sweep.py` + `_output.txt`, `set_exec_standalone_compile.txt`,
`set_exec_WeaveProbe.java`, `set_exec_weave_scenarios.tsv`,
`set_exec_weave_android-30.out`, `set_exec_weave_android-37.0.out`,
`set_exec_weave_jar_diff.txt`, `set_exec_CompositionDrive.java`,
`set_exec_drive_rep1.out` (reps 2–3 byte-identical, hashes recorded),
`set_exec_DedupeProbe.java`, `set_exec_dedupe_rep1.out` (idem).
