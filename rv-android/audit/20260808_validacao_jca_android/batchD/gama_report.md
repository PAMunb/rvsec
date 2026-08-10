# GAMA — Batch D report: diagnostics, experimental history, static synergy

Agent Gama · 2026-08-09 · adversarial posture. Round "batch D" — the FINAL batch —
of the `jca_android` audit. Scope: MacSpec (MAC), MessageDigestSpec (MDG),
KeyPairGeneratorSpec (KPG), SecureRandomSpec (SRD), SignatureSpec (SIG).

Governing rules applied without re-litigation: D-piloto-1/3/4, D-batchA-1,
D-batchB-1 (`fase0/desvios.md`); batch D generation manifest
(`batchD/generation_manifest.md`) plus all batch C round rules carried forward
(indexing-tree check, parameterless check, first-call-disjunct sweep,
REF-B-01/REF-B-09, fail-open probes, dexlib2 caveats, `ErrorSummary` drops
`expecting`, javap trap, provenance column). BINDING reading done:
`batchC/gama_report.md` (FEN-C-PAIRING-IMEDIATO, H4 "but found ." update),
`batchB/juiz_sintese_batchB.md` context via batch C's citations,
`pilot/gama_historico.md` H1–H7. No `batchD/alfa_*` or `beta_*` file was read.

Established SET registers cited, never re-derived — re-verified current this
round at the cited lines: GAMA-SET-01/03 (static jca-default `mop_dir` +
android_jar probe list without "30" — `rv_static_analysis/config.py:186-207`);
GAMA-SET-02/06 (dedupe identity excludes `expecting` —
`ErrorDescription.java:105-139`, comment names the consequence); 3-arg
`ErrorDescription` ⇒ `expecting="unknown"` (`ErrorDescription.java:34-36`);
logcat `ErrorCollector` escape commented out + in-JVM `Set.add` dedupe
(`rvsec-logger-logcat/.../ErrorCollector.java:36-42`); GAMA-SET-09 ctor `new`
blindness (measured live: SRD's 2 `new` rows, §4); GAMA-SET-18 (all `@fail` =
`unknown`); GAMA-SET-22 (two repair philosophies — confirmed from the SRD side,
§2.4); batch-A GAMA-SET-08 stale-flags (first *instantiated* this round, §2.3).

Method note (protocol §2): the Sequential Thinking MCP tool was listed as
deferred in this session and was not loaded; the same decomposition was applied
explicitly — every analysis follows question → hypothesis → discriminating test
→ evidence → result → uncertainty (scientific log §7). No chain-of-thought is
published.

## 0. Inputs, provenance, freeze checks (G0)

- Specs read from `.../rvsec-mop/src/main/resources/jca_android/`; `sha256sum`
  of all five equals `batchD/generation_manifest.md` and
  `fase0/manifest_hashes.md` (MAC `db8b0d12…`, MDG `03ff03db…`, KPG
  `9a262840…`, SRD `9e58c92c…`, SIG `68dd32a6…`) — freeze PASS.
- CrySL oracle `MetaCrySL/generated/api30/`: MAC `17245e0c…`, MDG `6bc3d2be…`,
  KPG `c820d2d0…`, SRD `69c55557…`, SIG `ce3b0317…` — all equal the manifest.
  Raw availability profile; bias recorded, never corrected.
- Round artifacts under `<scratch>/batchD/gen_<Spec>/out/`: all 20 sha256 equal
  the generation manifest (verified before any read). All language/automaton
  statements are made over these artifacts (D-piloto-3).
- Historical `ase-journal/dataset/results/errors.csv`: sha256 `78023def…`
  verified **inside** `gama_errors_batchD.py` (abort-on-mismatch) — PASS.
  PRE-GH100/GH101: hypothesis generator only.
- android.jar API 30: sha256 `96ccfdc8…` (= `fase0/toolchain_ambiente.md`);
  member facts from `javap` over `unzip`-extracted class bytes, never
  `javap -classpath` (batch A trap).
- Harness classpath: frozen `rv-android/lib_tmp/rv-monitor-rt.jar`
  (`0fa65fbc…` = toolchain manifest), `rvsec-core-0.9.3-SNAPSHOT.jar`,
  `rvsec-logger-csv-0.9.3-SNAPSHOT.jar` from the rvsec targets. **All five
  frozen monitors compile clean** — no batch-C KGN-01 recurrence.
- No emulator, no device, no DEX weaving (G10 pendencies named per claim).
  Specs, rules, production code, round artifacts untouched. JavaMOP/RV-Monitor
  never executed by me. Executions: `javac`+`java` over the round monitors in
  scratch; production `mop-extractor.jar` over **scratch copies** of the specs;
  one **ajc 1.9.25.1 source-compile probe** (`lib_tmp/aspectjtools.jar`,
  version = the Docker/pom pin) of the frozen `MacSpecMonitorAspect.aj` in
  scratch — a declared lane overlap with Beta, run because it decides
  GAMA-MAC-03's severity and costs nothing (no weaving, no emulator).

Evidence files of record (REF-B-01), all under `audit/.../batchD/`, sha256:

```
c402653abde3153b54d03b81c287f8dcb74563554569bfb4e73aa09c8a1fb58c  gama_errors_batchD.py
12e16fc1312da1654e66f63c88d3d3520c21ca7cc78ae4ae08846d9644e3a51f  gama_errors_batchD_output.txt
f788dca90a15a2edf27931708f1cfd0dc61f03531e9e5e7fe9b08b82f95353f2  gama_GamaBatchDDrive.java
55db8a3e3eb2ecedfd76902ea7de8fc21e97a018300a97e29d9554a7b9b47e66  gama_harness_output.txt
6457ea869489aea8a3cd837c54f312e48b130cab0666e2d78fae4b872457a394  gama_ajc_mac_probe.out
39e31b6669f5afff73a251f737de6f11e4afd14669f78d3a959ad16940ccc62c  gama_extractor_ja.csv
819569c603fe0590323f04712796d13504d6305e34c7143ac2a52c06a3fc77c0  gama_extractor_j.csv
d55aefb2d8409b911dc071b034381f51a8b552423f70ff86b75a42705606efb9  gama_claims.csv
```

Repetition policy: the 26-scenario harness ran 3×; the three outputs are
sha256-identical (`55db8a3e…`) — deterministic, no flaky marks.

## 1. Structural facts established once (cited per spec)

**1a. Indexing tree.** MAC, MDG, KPG, SRD, SIG all declare a parameter and all
events bind it **except MacSpec f3**: the event declares
`after(byte[] output, int outOffset)` without the Mac, and the generated
`MacSpec_f3Event` dispatches to the **empty parameter slice** (`matchedEntry =
MacSpec__Map`) and broadcasts over the whole monitor set — the batch-B KPR-c1
shape inside an otherwise per-object spec (§2.1, executed).

**1b. Effective transition tables** (from the frozen artifacts; state ids from
the `Category_` assignments):

- MAC (fail=4, match=3, start=0): `g1=g2={2,4,4,4,4}`, `g3={0,4,…}`,
  `i1=i2={4,4,1,4,4}`, `u*={4,1,4,4,4}`, `f*={4,3,4,4,4}` (artifact :344-354).
  Decisive: `i1[0]=4`, `f1[2]=4`.
- MDG (fail=4, match=1): `g1..g3={3,…}`, `g4={0,…}`, `update={4,2,2,2,4}`,
  `d1=d3={4,4,1,4,4}`, `d2={4,1,1,1,4}` (:235-242). Decisive: `update[0]=4`,
  `d2[0]=4`.
- KPG (fail=4, match=1): `g1=g2={2,…}`, `g3={0,…}`, `init*={4,4,3,4,4}`,
  `initError={4,4,2,3,4}`, `gen={4,4,4,1,4}` (:275-283). Decisive:
  `initError[0]=4`, `gen[2]=4`, and **no `__RESET`** in `@fail` — fail state
  absorbing.
- SRD (fail=4, match1=2): `c1={2,4,2,4,4}`, `c3=g4={1,…}` (unsafeInit=1),
  consuming events `{4,1,3,3,4}` **except `next2={4,1,3,4,4}`** (:393-407).
  Decisive: `next2[3]=4` — the missing end-row (§2.4).
- SIG (fail=8, match={4,6}): `g1=g2={5,…}`, `g3={0,…}`, `i1=i2[5]=1`,
  `i3=i4[5]=2`, `update`, `s1=s2[6..7]=6`, `v1=v2[2..4]=4` (:329-340).
  Decisive: `i1[0]=8`, `i4[0]=8`.

**1c. Body-before-handleEvent, creation, advice order.** Every event body runs
before the transition; every failing `condition` is `return false` **before**
the transition **and before the Category flags are updated** (KPG artifact
:441-456); every static dispatch does FindOrCreate — a consuming event on an
unseen object starts a monitor at state 0 with the algorithm field at its
initial value (`""` for MAC/MDG/SIG; **null for KPG** — §2.3). Merged
monitorCall order verified from the `.aj`/`.json`: g1-then-g3 (MAC/KPG/SIG),
g1-then-g4 (MDG), init1-then-initError (KPG), c2-then-c3 and
setSeed2-then-setSeed3 (SRD); SRD's g1 and g4 are separate advices in
declaration order g1-before-g4. All five `@fail` handlers use the 3-arg
`ErrorDescription` ⇒ every sequencing record is `expecting=unknown`.

**1d. First-call-disjunct sweep** (round rule): **one hit** — KPG's `gen`
pointcut is `(call(...generateKeyPair()) || call(...genKeyPair()))`
(`KeyPairGeneratorSpecMonitorAspect.aj:77`), the first `" || call("` since the
sweep began (GAMA-KPG-06).

## 2. Per-spec findings

Full rows: `gama_claims.csv` — **34 claims: 27 FAIL (12 critical), 6 PASS,
1 INCONCLUSIVE**. This section gives mechanisms and decisive evidence.

### 2.1 MAC — extra-oracle gate, unbound f3, pairing, live empty label

- **GAMA-MAC-02 (crítica).** i1/i2 are gated by
  `condition(validate(GENERATED_KEY, key))` — a REQUIRES the **frozen api30 Mac
  rule does not state** (its REQUIRES are preparedHMAC + two !encrypted).
  Executed (mac_b): safe algorithm + unmarked key ⇒ init suppressed, the
  following `doFinal` is accused `InvalidSequenceOfMethodCalls (unknown)` at
  the doFinal site — displaced FP on a rule-conformant trace, and the specific
  channel is silenced too. jca-inherited; and **the gh101 register asserts the
  clause exists** (`predicate_edges.csv:47` "generatedKey … present") — a
  register/oracle contradiction filed separately (GAMA-MAC-06). The upstream
  1.5.2 Mac rule does state generatedKey — recorded as oracle-anchor
  divergence, not corrected (the pre-registration fixes api30 as oracle).
- **GAMA-MAC-03 (crítica).** f3's pointcut carries `target(m)` with `m`
  undeclared in the formals (`.aj:88`, same text in the descriptor JSON).
  Executed ajc probe (1.9.25.1, the pinned version): exit 0 with
  `[warning] no match for this type name: m [Xlint:invalidAbsoluteTypeName]` —
  **f3 can never match under ajc**, silently (a new exit-0 fail-open shape:
  generation clean, aspect compiles, pointcut dead). And the runtime dispatch
  is an empty-slice **broadcast**: executed (mac_d), one f3 event produced a
  false InvalidSeq at its own site AND poisoned the sibling Mac, whose own
  conformant doFinal then failed. dexlib2 half named for Beta.
- **GAMA-MAC-01 / GAMA-MAC-04.** Same-call pairing executed (mac_a: g3("DES")
  then i1 ⇒ UnsafeAlgorithm + InvalidSeq, one `__LOC`); empty label executed
  (mac_c: i1 first event ⇒ `"but found ."` + InvalidSeq). Capture gaps feeding
  the first-event route: unsafe 2-arg (g3 is 1-arg) and
  `getInstance(String, Provider)` (no event; note the api30 Mac rule itself
  models only the 1-arg getInstance — g1/g2 are byte-duplicates, an oracle
  anomaly flagged for Alfa). Historical: MacSpec's 31 empty-label lines all sit
  at tink `Hkdf#computeHkdf`, a provider-parameterized creation wrapper.
- **PASS (GAMA-MAC-05).** preparedHMAC read, MACED/GENERATED_MAC writers,
  2-arg remove-on-fail: all verified in execution (mac_e, mac_b).

### 2.2 MDG — pairing cascade, live empty label, wrong-set message

- **GAMA-MDG-01 (crítica).** After an unsafe g4, **every** consuming call
  yields a pair (UnsafeAlgorithm + InvalidSeq): executed mdg_c — 6 records for
  one three-call trace, one pair per distinct site (post-`__RESET` re-arms at
  start where `update[0]=4`). Historical fingerprint: **2,780 of 2,871**
  execution×site cells carry both categories; 0 cells only-specific.
- **GAMA-MDG-02.** Empty label live: update-as-first-event executed (mdg_a).
  Invisible-creation routes: unsafe 2-arg/Provider (g4 is 1-arg only) and
  `MessageDigest.clone()` (no event; none in the rule either). The historical
  156 empty-label lines sit at a kmp-tor lambda and at guava
  `MessageDigestHashFunction$MessageDigestHasher#update` — guava's hasher is
  **clone()-based**, matching the route exactly.
- **GAMA-MDG-03 (latent, minor).** g4's condition tests the monitor field, not
  the argument (`mop:56`) — masked by g1-before-g4 order plus fresh-monitor
  `""` (mdg_b executed: 0 records on safe MD5). KGN-05 family.
- **GAMA-MDG-04 (minor).** The UnsafeAlgorithm message claims
  `{SHA-256, SHA-384, SHA-512}` while the enforced list admits MD5/SHA-1/
  SHA-224 + aliases — the report misstates the oracle.
- **GAMA-MDG-05 (oracle-shift warning, §3.10).** 5,891 of 6,048 historical
  UnsafeAlgorithm lines are MD5/SHA-1 — both SAFE under the api30 rule (and
  mdg_b shows the current artifact is silent on MD5). Any future drop is oracle
  change, not repair.

### 2.3 KPG — NPE crash, both pairing forms, absorbing fail, dead disjunct

- **GAMA-KPG-01 (crítica — the batch's sharpest edge).** `String algorithm;`
  is uninitialized and `validate(int)` switches on it. Executed (kpg_c):
  `initialize(int)` as the monitor's first event throws
  `java.lang.NullPointerException` **out of both `init1Event` and
  `initErrorEvent`** into the caller. Under weaving this crashes the app at
  `KeyPairGenerator.initialize(int)`. Reachable via the invisible
  `(String, Provider)` creation route (GAMA-KPG-02, the Cipher-repaired 2-arg
  class — rule g2 is `getInstance(alg, _)`, spec g2 is `(String,String)`
  only). jca-inherited; unregistered; no try/catch anywhere in the dispatch
  (artifact :441-456, :1039-1045). Fail-crash is worse than fail-open.
- **GAMA-KPG-03 (crítica — H2 closure for its named class).** Both forms
  executed: immediate (kpg_a — g3("EC") then init1(256): UnsafeAlgorithm +
  InvalidSeq, same call) and delayed (kpg_b — InvalidKeySize alone at
  initialize(1024), then InvalidSeq at `generateKeyPair`). Historical: 7/7
  cells both categories, 16 lines fully dumped — and the jca twin had
  initError **absent from its ere** (register `151e53aa8e1f`), i.e. the
  campaign-era form was same-call. **The gh101 repair converted the immediate
  pairing into the delayed one; it did not remove it.**
- **GAMA-KPG-04 (major).** No `__RESET` + absorbing fail state: every
  subsequent event re-accuses (kpg_b's second gen ⇒ third record). Plus the
  batch-A stale-flags phenomenon **first instantiated with a real record**:
  kpg_a's suppressed initError re-fired the fail handler at its own `__LOC`,
  because a failing condition returns before the flags are updated and the
  dispatch re-checks the stale `Category_fail` (PROVADO at :441-456 +
  :1039-1045). In-advice re-fires share `__LOC` and dedupe away; distinct-site
  events after any fail each add a record.
- **GAMA-KPG-05 (major).** initError covers `initialize(int)` only: an invalid
  size through `initialize(int, SecureRandom)` has **no InvalidKeySize
  channel** (executed kpg_f: 0 records at init2(1024), displaced InvalidSeq at
  gen). Unregistered.
- **GAMA-KPG-06 (major).** `gen`'s disjunctive pointcut: under dexlib2's
  `findFirstCall` (round register, `WrapperEmitter.java:507-524`) only
  `generateKeyPair()` is woven — `genKeyPair()` sites are invisible under the
  canonical variant, visible under ajc. Variant-divergent observability;
  execution of the dexlib2 half named for Beta (G10-KPG-2).
- **PASS (GAMA-KPG-07).** preparedDH read (specific alone, kpg_d), gen's
  GENERATED_KEY_PAIR write + remove-on-fail, and the registered
  writer-no-reader status of the KPG→KeyPairSpec `generatedKeypair` edge all
  verified — the edge is terminal by registered design; the pair-flow
  composition rides GENERATED_PRIVATE/PUBLIC_KEY (batch B context: KeyPairSpec
  itself was REPROVADA, which bounds what this writer can achieve end-to-end).

### 2.4 SRD — the missing next2 row, and the set-wide RANDOMIZED writer truth

- **GAMA-SRD-01 (crítica — the batch headline).** The spec's `end` state lists
  every consuming event **except `next2`** (`mop:169-177`); the effective
  table has `next2={4,1,3,4,4}` — from end(3), `nextBytes` FAILS, while the
  rule's ORDER is `Ins, Seeds?, Ends*` (nextBytes any number of times).
  Executed (srd_a): `new SecureRandom(); nextBytes; nextBytes; nextBytes` ⇒
  **two false InvalidSeq** (calls 2 and 3 — `__RESET` re-arms at start where
  `next2[0]=4`, so every later nextBytes accuses too). Control srd_a2:
  `nextInt`×3 clean — isolates the missing row. **jca-inherited** (the twin's
  `end` block, jca `mop:155-162`, also omits next2) — live during the whole
  campaign. Unregistered.
- **GAMA-SRD-02 (H-SRD-1, INCONCLUSIVE by design).** The 12,400 historical SRD
  lines are 100% InvalidSeq/`unknown`, zero specific, and their sites are
  overwhelmingly **nextBytes wrappers**: `secureRandomBytes` 3,962,
  ktor nonce-loop `invokeSuspend` 3,104 (33.7 lines/exec — H7 restart
  inflation), `randBytes` 1,532, `secureRandomUuid` 1,229, spongycastle
  DRBG entropy internals ~1,750. The pilot's H5 (all-fail violating branches)
  predicts creation sites — a small minority here. H-SRD-1: the dominant mass
  is the SRD-01 FP. Attribution deferred to the named replay (G10-SRD-1:
  micro-APK, `new SecureRandom()` + nextBytes×3, ajc AND dexlib2; predict
  records at calls ≥2).
- **GAMA-SRD-03 (major — the writer-side answer the round demanded for every
  RANDOMIZED edge).** Executed: (a) writes run body-before-handleEvent —
  RANDOMIZED is marked **on the fail path** (srd_a b2=true, srd_c) and
  (b) **from unsafeInit** (srd_b: an unsafe-algorithm SecureRandom's outputs
  are marked) — so every downstream `randomized[]` REQUIRES in the set
  (Cipher, PBEKeySpec, IvParameterSpec, GCM, SecretKeySpec(Spec),
  KeyGenerator, SSL) is satisfiable by non-conformant randomness. As
  implemented, RANDOMIZED means "came from any SecureRandom", not "conformant
  randomness" — an FN direction that touches every batch that read this
  predicate. The unsafeInit register (`029a4511565f`) says consuming calls "do
  not accuse"; it does not say their ENSURES writes still execute — searched,
  0 hits. (c) next1 marks the boxed **range argument** pre-call with
  Integer-cache identity (srd_d: box of 100 true, box of 1000 false) — but the
  raw rule itself states `randomized[numB]` over the argument, and its `ne` is
  the **protected** `next(int)` no app can call; nextInt()/ints are
  extra-oracle events (oracle ambiguity flagged, register endorses).
- **GAMA-SRD-06 (major).** Unsafe 2-arg getInstance matches nothing (g2
  condition-gated safe-only, g4 arity-bound to 1 arg) ⇒ srd_c executed: first
  consume = displaced InvalidSeq, no UnsafeAlgorithm ever. Safe-side contrast:
  SRD's `(String, ..)` g2 does cover the Provider overload — the only batch D
  spec that does.
- **PASS (GAMA-SRD-05).** `randomized[this] after Ins` via match1 (srd_e), and
  g4's specific-alone reporting (srd_b) — the registered unsafeInit philosophy
  works as registered; GAMA-SET-22 confirmed from the other side.

### 2.5 SIG — dead sign(), live empty label, invisible Provider creation

- **GAMA-SIG-01 (crítica).** The s1/s2 pointcuts declare return type `byte`
  (`aspect .aj:82-90`); android-30 declares `public final byte[] sign()` and
  `public final int sign(byte[], int, int)` (javap from class bytes). Neither
  pointcut can ever match — **`sign()` is invisible**: a fully conformant sign
  flow never reaches match (executed sig_b: accepting=false, SIGNED never
  written), and a sign-misuse (`sign()` with no update — the very case
  `frozen_set_debt.md:243` uses to argue against absorbing states) is
  unreportable **today**. Batch C SSL-03 dead-return-type class on a
  high-frequency API; jca-inherited; unregistered. SIGNED is registered
  terminal, so the predicate loss is bounded; the ORDER/diagnostic loss is not.
- **GAMA-SIG-02 (crítica — H4 closure for SIG) + GAMA-SIG-03 (crítica).**
  Executed sig_a: initSign as first event ⇒ **three records, three types, one
  `__LOC`** (UnsafeAlgorithm `"but found ."` + UnsatisfiedConstraint +
  InvalidSeq — all survive dedupe because types differ). Executed sig_d:
  unsafe-then-initVerify same-call pairing. The realizable production trigger
  is GAMA-SIG-03: `getInstance(String, Provider)` matches no event (rule g2 is
  `getInstance(alg, _)`; spec g2 is `(String,String)`). Historical H4: all 234
  SIG empty-label lines sit at **one site** — spongycastle
  `X509CertificateObject#checkSignature`, an initVerify wrapper whose Signature
  is created via provider-parameterized getInstance. The pilot's "unexplained
  residue" for SIG now has a live current-artifact mechanism; per-line
  historical attribution stays deferred (G10-SIG-1).
- **GAMA-SIG-04 (minor).** v1 marks VERIFIED over the boxed Boolean return —
  after one verify, `validate(VERIFIED, Boolean.TRUE)` is true process-wide
  (executed sig_c). Dormant (VERIFIED is registered terminal); D-S13 family.
- **PASS (GAMA-SIG-05).** generatedPrivkey/Pubkey reads and the g3* repair
  verified in execution (sig_e clean; sig_d silent at the getInstance line).

## 3. gh101 register audit (registered vs found)

Accurate, verified: MAC allow-list normalization (`23781ab3f0f1`), Mac split
update/doFinal + 2-arg remove (`dd4ea3afb352`, `4df0374c303e`), preparedHMAC
read comment (`72bb15348b36`); MDG allow-list widening (`35df505aa1ef`), reset
removal oracle-aligned with api30 (`ff425611fcba` — extractor confirms the
target disappears); KPG allow-list/keysize derivation rows, preparedDH reads,
initError layer-2 row (accurate for what it covers); SRD c3/g4/setSeed3
placements + unsafeInit (`389c0d571433`, `547f13f50890`, `8dd80ceaf10e`,
`029a4511565f`); SIG g3 repair + both key reads; the writer-no-reader rows for
DIGESTED, GENERATED_KEY_PAIR, GENERATED_MAC, SIGNED, VERIFIED
(`predicate_omissions.csv`) — all verified accurate.

Register absences/contradictions (exact greps over `data/gh101/` +
`openspec/changes/gh101-jca-spec-conformance/`, 0 hits each unless noted):
SIG s1/s2 dead return type; the `(String, Provider)` capture gap (SIG, KPG,
MAC); SRD next2 missing from `end`; MAC f3 unbound `target(m)`/broadcast; KPG
`switch(null)` NPE; KPG init2 without an initError twin; KPG gen disjunct ×
dexlib2; MDG g4 field-not-arg condition; the same-call pairing consequence
(3b.11b registers only the delayed shape — carried from batch C);
**contradiction**: `predicate_edges.csv:47` records Mac `REQUIRES generatedKey
… present` against a frozen api30 rule that does not state the clause
(GAMA-MAC-06).

## 4. Static synergy (protocol §13, measured)

Executed: production `mop-extractor.jar -t METHODS_PARAMS` over scratch copies
of the five jca_android specs and their jca twins.

- 49 target rows. Mappability per spec: MAC 11/11, MDG 7/7, KPG 8/8,
  SIG 11/11, SRD 10/12 (2 `SecureRandom,new` rows GATOR-blind — GAMA-SET-09;
  SRD's creation half is statically invisible). Batch D is METHOD-heavy as the
  round predicted.
- **GAMA-SET-23 (major).** Six rows are statically listed but dynamically dead
  or deformed: `Signature#sign` ×2 (dead pointcuts), `Mac#doFinal(byte[],int)`
  (ajc-dead + broadcast), `SecureRandom#nextInt` ×2 and `#ints` (inherited
  from `java.util.Random` — absent from SecureRandom's declared members,
  javap-measured; dexlib2's class index is declared-only per the round
  register). A statically flagged site on any of these can never obtain its
  dynamic witness — the batch C SET-20 breach class, now including two
  RANDOMIZED writers.
- **GAMA-SET-24.** jca vs jca_android diff at the GATOR key (`class#method`):
  exactly one delta — `MessageDigest#reset` present in jca only. Under the
  literal-`jca` default (re-verified current, `config.py:199-207`) the static
  view of a jca_android APK counts one member the derived monitors do not
  monitor; otherwise measured near-vacuous for batch D (Mac's update row split
  is invisible at key level). Probe list still lacks "30" (`config.py:186`).
- Per-clause: CONSTRAINTS/REQUIRES remain dynamic-only; RANDOMIZED is doubly
  invisible to the static view (predicate + two unweavable writers under the
  canonical variant).

## 5. History discipline summary (protocol §12)

Freeze verified in-script; global sanity equals the pilot exactly
(97,018 / 225 / 113 / 454 / 8,147). Four units per spec (output §B):
MAC 837/6/7/8 · MDG 16,183/65/38/55 · KPG 16/4/2/2 · SRD 12,400/15/43/53 ·
SIG 990/11/4/9. Pairing cells (§F): MAC 31 both / 166 only-generic / 0
only-specific; MDG 2,780/91/0; KPG 7/0/0; SRD 0/4,455/0; SIG 107/26/0.

- **H2 — closed.** Immediate form executed in MAC/MDG/KPG/SIG (the KPG and — 
  via the pilot's TMF naming — the H2-named classes included); delayed form
  executed in KPG (and MAC via the GENERATED_KEY gate); SRD alone decouples by
  design (executed). Historical zero-only-specific columns match the mechanism
  everywhere it exists.
- **H4 — closed.** The empty label is live in the current artifacts of exactly
  the three classes the pilot named (executed mac_c/mdg_a/sig_a), through
  creation-at-consume routes (Provider/2-arg/clone) that the task 8.1
  weaver-collision account never covered; the three historical residue sites
  match those routes by API shape (GAMA-SET-27). Per-line attribution deferred.
- **H5 — updated** to H-SRD-1 (§2.4): site profile contradicts the all-fail
  account as the dominant mass.
- **H1/H7** applied as method (zeros decomposed; cells, never raw lines).

**Named replay battery (G10 pendencies):**
1. **G10-SRD-1**: micro-APK `new SecureRandom()` + `nextBytes`×3, ajc AND
   dexlib2 — predicts InvalidSeq at calls ≥2 (decides H-SRD-1).
2. **G10-KPG-1**: micro-APK `KeyPairGenerator.getInstance("RSA", provider)`
   then `initialize(2048)` — predicts app crash (NPE) under weaving.
3. **G10-KPG-2**: dexlib2 weave of a `genKeyPair()` call site — decides
   GAMA-KPG-06's FN.
4. **G10-SIG-1**: micro-APK reproducing the spongycastle checkSignature shape
   (provider-created Signature + initVerify) — predicts the sig_a record
   triple; paired jca/jca_android replay attributes the 234 historical lines.
5. **G10-MAC-1**: micro-APK `Mac.getInstance(alg, provider)` + init + doFinal —
   predicts mac_c then displaced records.

## 6. Threats to validity

1. **Harness ≙ woven app**: events driven exactly as the verified advice
   bodies/order dictate, but no weaving/DEX ran — every executed FP/FN carries
   its named G10 pendency. The KPG NPE additionally assumes the advice frame
   propagates exceptions as plain Java does (it does — no catch exists in the
   generated code — but the woven frame was not executed).
2. **ajc probe scope**: source-compile of the per-spec aspect, not the
   production `-merge` MultiSpec aspect and not a weave over app code; the
   invalid-type-name behavior is version-pinned (1.9.25.1) and text-identical
   in the merged pointcut (INFERIDO for merge).
3. **Oracle anchor**: MAC-02/MAC-06 and SRD-04 verdicts are relative to the
   frozen api30 rules (raw availability profile); the 1.5.2 anchor differs on
   Mac generatedKey — recorded, not resolved.
4. **Historical data pre-repair**: hypothesis generation only;
   pseudoreplication controlled by units/cells; H-SRD-1 and the H4 site
   attributions are consistency arguments, not causal claims.
5. **Matcher halves**: dexlib2 behavior on `target(m)`, the gen disjunct, and
   inherited members is cited from round registers + measured member absence,
   not from executed weaves (Beta's lane, named).
6. **Extractor path**: exercises `JavamopFacade.listUsedMethods` as the GATOR
   client does, not a full GATOR run.

## 7. Scientific log

| # | Question | Hypothesis | Discriminating test | Evidence | Result | Uncertainty | Next decision |
|---|---|---|---|---|---|---|---|
| 1 | Do all events bind the spec parameter? | f3 does not | artifact dispatch read | §1a f3 empty-slice broadcast | PROVADO | none | mac_d execution |
| 2 | Does f3 even match under ajc? | No (`target(m)` unbound) | ajc 1.9.25.1 source probe | exit 0 + invalidAbsoluteTypeName warning | EXECUTADO | merge-aspect inferred | GAMA-MAC-03 crítica |
| 3 | Does the current artifact still pair specific+fail (H2)? | Yes, both forms | tables + harness mac_a/mdg_c/kpg_a/kpg_b/sig_d | pairs at one `__LOC`; delayed at gen | EXECUTADO 4/5 specs (SRD decouples) | G10 weave | H2 closed |
| 4 | Is the empty label dead post-GH100? | No — first-event route lives | mac_c/mdg_a/sig_a first-event drives | `"but found ."` ×3 executed | EXECUTADO | per-line history deferred | H4 closed (SET-27) |
| 5 | Is Mac's key gate in the api30 rule? | No | rule read + register grep + mac_b | REQUIRES lacks generatedKey; edges row says present | EXECUTADO + contradiction | 1.5.2 anchor | MAC-02/06 |
| 6 | Is nextBytes×2 conformant yet accused? | Yes (missing end row) | table + srd_a vs srd_a2 control | 2 false records; nextInt clean | EXECUTADO | G10-SRD-1 | SRD-01 crítica |
| 7 | Do the 12,400 SRD lines fit that mechanism? | Yes (wrapper sites) | 4-unit stratification + site profile | nextBytes wrappers dominate; 0 specific | MEDIDO (consistency) | pre-repair data | H-SRD-1 INCONCLUSIVE |
| 8 | Does initialize(int) on an unseen KPG crash? | Yes (switch(null)) | kpg_c try/catch drive | NPE from both event methods | EXECUTADO 3× | woven frame | KPG-01 crítica |
| 9 | Does RANDOMIZED mean conformant randomness? | No | srd_a/b/c/d marking probes | marked on fail path and from unsafeInit; cache identity | EXECUTADO | CrySL predicate semantics (Alfa) | SRD-03 set-wide |
| 10 | Can sign() ever fire? | No (return-type mismatch) | javap on extracted bytes + sig_b | no `byte sign()` member exists | MEDIDO + EXECUTADO consequence | none on the member fact | SIG-01 crítica |
| 11 | Are the found defects registered? | Partially | exact greps over data/gh101 | §3 absence list + one contradiction | OBSERVADO | register semantics | register claims |
| 12 | Can the static path map batch D? | Mostly, with dead targets | extractor both sets + diff + javap | 49 rows; 6 dead/deformed; diff = reset | MEDIDO | client-vs-extractor | SET-23/24 |

## 8. Commands (reproduction)

```
sha256sum <specs>/jca_android/{MacSpec,MessageDigestSpec,KeyPairGeneratorSpec,SecureRandomSpec,SignatureSpec}.mop
sha256sum $WS/MetaCrySL/generated/api30/{Mac,MessageDigest,KeyPairGenerator,SecureRandom,Signature}.cryptsl
sha256sum <scratch>/batchD/gen_*/out/*                                  # 20/20 = generation manifest
uv run python gama_errors_batchD.py > gama_errors_batchD_output.txt     # in-script freeze check
cd <scratch>/gama/api30 && unzip -oq .../android-30/android.jar javax/crypto/Mac.class java/security/{Signature,MessageDigest,KeyPairGenerator,SecureRandom}.class && javap -p <class>
javac -nowarn -cp rv-monitor-rt.jar:rvsec-core.jar:rvsec-logger-csv.jar -d classes gen_*/out/*RuntimeMonitor.java   # exit 0, all five
javac -cp <same>:classes -d classes GamaBatchDDrive.java
for rep in 1 2 3; do for sc in mac_a..sig_e (26); do java -cp classes:<same> gama.GamaBatchDDrive $sc; done > run_rep$rep.out; done   # sha-identical
java -cp lib_tmp/aspectjtools.jar org.aspectj.tools.ajc.Main -cp <same>:classes -d ajcout gen_MacSpec/out/MacSpecMonitorAspect.aj    # exit 0 + Xlint warning
java -jar mop-extractor.jar -d <scratch>/gama/specs_ja -o gama_extractor_ja.csv -t METHODS_PARAMS   # + specs_j twin
diff <specs>/jca/<S>.mop <specs>/jca_android/<S>.mop                    # provenance, all five
grep -rn "<term>" rv-android/data/gh101/                                # absence claims, §3
```
