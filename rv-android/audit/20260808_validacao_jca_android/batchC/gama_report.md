# GAMA — Batch C report: diagnostics, experimental history, static synergy

Agent Gama · 2026-08-09 · adversarial posture. Round "batch C" of the `jca_android`
audit. Scope: KeyGeneratorSpec (KGN), KeyManagerFactorySpec (KMF),
TrustManagerFactorySpec (TMF), SSLContextSpec (SSL), KeyStoreSpec (KST).

Governing rules applied without re-litigation: D-piloto-1/3/4, D-batchA-1,
D-batchB-1 (`fase0/desvios.md`); batch C generation manifest round rules
(`batchC/generation_manifest.md`), including the standard indexing-tree check
("declares a parameter AND every event binds it"), the extra-oracle-gate sweep,
the first-call-disjunct sweep, and REF-B-01/REF-B-09. BINDING reading done:
`batchB/juiz_sintese_batchB.md` §6/§8, `batchB/gama_report.md`,
`pilot/gama_historico.md` (H1–H7, with the batch B H2 update). No `batchC/alfa_*`
or `beta_*` file was read.

Established SET registers cited, never re-derived — all re-verified current this
round at the cited lines: GAMA-SET-01/03 (static path defaults to literal `jca`
mop_dir and an android_jar probe list `["33","29","28","27","26"]` without "30" —
`rv_static_analysis/config.py:180-207`); GAMA-SET-02/06 (dedupe identity excludes
`expecting` — `ErrorDescription.java:108-139`, the code comment itself names the
consequence); 3-arg `ErrorDescription` ⇒ `expecting="unknown"`
(`ErrorDescription.java:34-37`); logcat `ErrorCollector` escape commented out and
in-JVM `Set.add` dedupe (`rvsec-logger-logcat/.../ErrorCollector.java:36-42`);
GAMA-SET-09 (static ctor blindness — no ctor events exist in batch C, measured
moot, §4); stale-flags re-execution (checked: `reset()` clears both category
flags in all five artifacts — no batch C instantiation).

Method note (protocol §2): the Sequential Thinking MCP tool was listed as
deferred in this session and was not loaded; the same decomposition was applied
explicitly — every analysis below follows question → hypothesis → discriminating
test → evidence → result → uncertainty (scientific log §7). No chain-of-thought
is published.

## 0. Inputs, provenance, freeze checks (G0)

- Specs read from `.../rvsec-mop/src/main/resources/jca_android/`; `sha256sum` of
  all five equals `batchC/generation_manifest.md` and `fase0/manifest_hashes.md`
  (KGN `3788c3d8…`, KMF `a7fb68fb…`, TMF `a4691fd4…`, SSL `42760be5…`,
  KST `3392a11d…`) — freeze PASS.
- CrySL oracle `MetaCrySL/generated/api30/`: KGN `30779a3a…`, KMF `ebd1639e…`,
  TMF `ae2a9d8f…`, SSL `610bbcdb…`, KST `083b171f…` — all equal the manifest.
  Raw availability profile; bias recorded, never corrected.
- Round artifacts under `<scratch>/batchC/gen_<Spec>/out/`: all 20 sha256 equal
  the generation manifest (verified before any read). All language/automaton
  statements are made over these artifacts (D-piloto-3).
- Historical `ase-journal/dataset/results/errors.csv`: sha256 `78023def…`
  verified **inside** `gama_errors_batchC.py` (abort-on-mismatch) — PASS.
  PRE-GH100/GH101: hypothesis generator only.
- android.jar API 30: sha256 `96ccfdc8…` (= `fase0/toolchain_ambiente.md`);
  member facts taken from extracted class bytes (`javap` over `unzip`-extracted
  `.class`), never `javap -classpath` (batch A trap).
- Harness classpath: frozen `rv-android/lib_tmp/rv-monitor-rt.jar`
  (`0fa65fbc…` = toolchain manifest), `rvsec-core-0.9.3-SNAPSHOT.jar`,
  `rvsec-logger-csv-0.9.3-SNAPSHOT.jar` from the rvsec tree targets.
- No emulator, no device, no weaving (G6/G10 pendencies named per claim). Specs,
  rules, production code, and round artifacts untouched — with one documented
  exception: the KGN monitor **does not compile as generated** (§2.5, GAMA-KGN-01),
  so the harness ran against a scratch copy whose only delta is one added
  `import java.security.Key;` line (copy sha256 `4e24e1bf…`; original
  `de9e5205…`; `diff` = 1 line, preserved in the scratch `patched/` dir).
  JavaMOP/RV-Monitor never executed by me; the only executions were
  `javac`+`java` over the round monitors in scratch and the production
  `mop-extractor.jar` over **scratch copies** of the specs.

Evidence files of record (REF-B-01), all under `audit/.../batchC/`, sha256:

```
cee27df10749228ea5f2b32e18237824f988d82fa648a5af11dc512675dd2b90  gama_errors_batchC.py
b2808006fc07ab1c837eac7b6fbbeb4538d2e776835e22a3182fc7251f392620  gama_errors_batchC_output.txt
3556a725340b875a0f2082a70eafca26544799f781e410a01b896e6e6ab9872e  gama_GamaBatchCDrive.java
f72ec03b171028ad5c158c24dbb5bb0003422f33564b75b9a74bfef0fae43e70  gama_harness_output.txt
0d92fcf19c3cdf51ec6bd963718138b36ad6465de5cc7fa86ffb4d1f719ba97b  gama_kgn_compile_error.txt
e637fa41f538e6fb2c00b48f22dca9c6f300a92874aca5fef4709b49783fe327  gama_extractor_ja.csv
00b51c1f738b17cd10330045c51ffbf5e070fd001e1b18bc5162aa37aca4664a  gama_extractor_j.csv
8b1555adb91eba2834797dacd57b7bb2d954310e87a7dbf945da770f7ffdd776  gama_claims.csv
```

Repetition policy: the 18-scenario harness ran 3×; the three outputs are
sha256-identical (`f72ec03b…`) — deterministic, no flaky marks.

## 1. Structural facts established once (cited per spec)

**1a. Indexing-tree standard check** (round manifest, both halves): KGN, KMF,
TMF, SSL declare a parameter and every event binds it — per-object
`MapOfMonitor` keyed on the parameter (`KeyGeneratorSpec_k_Map` artifact `:596`,
KMF `:464`, TMF `_mf_Map:465`, SSL `_ctx_Map:420`). **KST FAILS the second
half**: the spec declares `KeyStoreSpec(KeyStore ks)` (`.mop:21`) but **every
one of its 7 events binds `k`, not `ks`** — the generated monitor has **zero**
`MapOfMonitor` and only the empty-binding
`Tuple2<KeyStoreSpecMonitor_Set,…> KeyStoreSpec__Map` broadcast (`:498`, Set
class `:27`): one process-global automaton over ALL KeyStore objects
(FEN-KST-GLOBAL; the FEN-STREAMS-MONITOR-GLOBAL / KPR-c1 family in a **new
sub-shape: parameter declared, never bound** — invisible to gh101's
`AbstractSynchronizedMonitor` census signature, since KST *is*
`AbstractSynchronizedMonitor:221` yet global).

**1b. Effective transition tables** (extracted from the frozen artifacts;
fail/match state ids from the `Category_` assignments):

- KGN (`:267-275`; fail=5, match=1, start=0): `g1={4,5,5,5,4,5}`,
  `g2={3,5,5,3,5,5}`, `g3={0,5,5,5,5,5}`, `i1..i5={5,5,5,2,2,5}`,
  `gk1={5,5,1,1,1,5}`.
- KMF/TMF (`:192-197`/`:193-198`; fail=3, match1=2, start=0):
  `g1=g2={1,3,1,3}`, `g3={0,3,3,3}`, `i1=i2={3,2,3,3}`, `gkm1/gtm1={3,3,0,3}`.
- SSL (`:170-174`; fail=3, match1=1, start=0): `g1=g2={2,3,3,3}`,
  `unsafe_protocol={0,3,3,3}`, `init={3,3,1,3}`, `engine={3,1,3,3}`.
- KST (`:242-248`; fail=5, match=1, start=0): `g1={4,4,5,5,5,5}`,
  `g2={0,0,5,5,5,5}`, `load={5,5,5,5,1,5}`, `store={5,5,1,5,5,5}`,
  `ge1={5,3,5,5,5,5}`, `se1={5,2,5,5,5,5}`, `gk1={5,1,5,1,5,5}`.

Decisive rows: `i1[0]=fail` (KMF/TMF), `init[0]=fail` (SSL), `load[0]=fail` and
`gk1[0]=fail` (KST), `i*[0]=fail` and `gk1[0]=fail` (KGN) — the *consuming*
event after an allow-list-only violation is a sequence violation, although each
rule keeps the algorithm/protocol/type in CONSTRAINTS, not ORDER.

**1c. Body-before-handleEvent, suppression, creation.** Every event body
(including all specific-error reports) runs **before** the transition
(`Prop_1_event_*`, e.g. KGN `:317-445`); a failing `condition(...)` is
`return false` **before** any transition (no fail); **every** static dispatch
does `FindOrCreateEntry` — every event is a creation event (KGN `:632-648`),
so a consuming event on an object whose creation was not captured starts a
monitor at state 0. `__LOC` is `ViolationRecorder.getLineOfCode()` threaded
per call site.

**1d. Advice merge and order.** The shared `getInstance(String)` joinpoint
carries two monitorCalls in one advice, in JSON order **g1 then
g3/g2/unsafe_protocol** (all five `*MonitorAspect.json`); no `" || call("`
disjunctive pointcut exists anywhere in the five `.aj` (first-call-disjunct
sweep: clean). All five `@fail` handlers use the 3-arg `ErrorDescription` ⇒
every sequencing record is `expecting=unknown` (GAMA-SET-18).

## 2. Per-spec findings (G9 diagnostics, history, synergy)

Full claim rows: `gama_claims.csv` (36 claims: 26 FAIL, 6 PASS, 4 INCONCLUSIVE;
9 critical FAILs).
This section gives the mechanism and the decisive evidence.

### 2.1 The batch-wide headline — FEN-C-PAIRING-IMEDIATO (5/5 specs, executed)

The pilot-H2 priority test. In **all five** specs, the allow-list violation is
reported by the **consuming** event's body, and the same consuming event takes
the fail transition, so the specific error and a spurious
`InvalidSequenceOfMethodCalls (unknown)` land on the **same call, same `__LOC`**
(they survive dedupe jointly only because their types differ). Executed:

| Scenario | Trace | Records |
|---|---|---|
| tmf_a | g3("X509"), i1, gtm1 (marked ks) | UnsafeAlgorithm "but found X509." + InvalidSeq at i1 **+ InvalidSeq at gtm1** (post-`__RESET` delayed residue at the rule's own optional event — FEN-C-DELAYED) |
| kmf_a | g3("SunX509"), i1, gkm1 | same 3-record shape |
| ssl_a | unsafe_protocol("SSLv3"), init (marked km/tm/sr) | UnsafeProtocol + InvalidSeq at init |
| kst_b | g2("JKS"), load, getKey | InvalidSeq at load + InvalidKeyStoreType + InvalidSeq at getKey |
| kgn_a | g3("DES"), generateKey | InvalidSeq + UnsafeAlgorithm at gk1 |

Every one of these traces **satisfies the rule's ORDER** (`Gets, Init, gtm?` /
`Gets, Loads, …` / `Gets, Inits?, gk` — the algorithm/protocol/type is a
CONSTRAINT); the correct diagnosis is the specific error alone. This is the
pre-registered G9 FAIL criterion verbatim ("`@fail` espúrio junto a erro
específico").

**Registration status (decisive nuance):** `frozen_set_debt.md:220-250`
(task 3b.11b) registers the *delayed accusation* ("the accusation moves from
the violating call to the next one") and the D-S9 grounds for keeping it. It
does **not** state that the next call is also where the specific report lands —
the same-call pairing, which is what the historical H2 signature measures, is
unstated; and no researcher scope reduction is on file (pre_registro §7).
Moreover, one of the two recorded grounds for rejecting the absorbing-state
repair — "it would leave the set with two repair philosophies" — is **factually
already the case**: SecureRandomSpec's `unsafeInit` admits ALL consuming events
(`SecureRandomSpec.mop` fsm; register row `029a4511565f` says so explicitly)
while KMF/TMF `unsafeAlg` and SSL `unsafeProtocol` admit none (GAMA-SET-22,
artifact-proven).

**Pilot H2 update (recorded per round instructions):** batch B found the pairing
returning in *delayed* form at PBK's `clearPassword`. Batch C shows it was never
gone in *immediate* form: the current TMF/KMF/SSL/KST/KGN artifacts produce
specific+spurious-`@fail` on the same call, executed. H2's decoupling prediction
is refuted for the entire batch.

### 2.2 History: TMF is the mechanism's fingerprint (freeze-checked, 4 units)

| Spec | lines | unique_msg | APKs | sites | pairing cells (both / only-generic / only-specific) |
|---|---:|---:|---:|---:|---|
| TrustManagerFactorySpec | 18,029 | 22 | 64 | 70 | **4,599 / 0 / 3** (of 4,602) |
| SSLContextSpec | 26,312 | 30 | 62 | 125 | 4,507 / 3,967 / 1 (of 8,475) |
| KeyStoreSpec | 10,660 | 35 | 22 | 52 | 927 / 2,771 / 0 (of 3,698) |
| KeyGeneratorSpec | 0 | 0 | 0 | 0 | — |
| KeyManagerFactorySpec | 0 | 0 | 0 | 0 | — |

TMF: exactly two UnsafeAlgorithm literals in the whole campaign — "but found ."
(8,371 lines) and "but found X509." (643); 50.0%/50.0% category split;
zero cells with InvalidSeq alone. This is precisely what creation-at-`i1` plus a
lost `g1` produces, and gh101's own task 8.1 measurement
(`frozen_set_debt.md:160-215`) already attributes the labels to the pre-GH100
**wrapper collision** (one wrapper per call site; whichever of g1/g3 survived
decides the label — their table covers the whole distribution "with nothing left
over", including SSL's 8,648 "TLS" / 103 "SSL" / 51 empty). My stratification
independently reproduces every number that account predicts. Causal attribution
for the historical lines stays deferred (GAMA-TMF-05/SSL-07/KST-07
INCONCLUSIVE, replay battery below) — but the **current-artifact half of H2 is
not historical**: it is executed (§2.1).

Oracle-alignment warning (protocol §3.10): SSL's 8,648 "TLS" lines and KST's
2,005 "AndroidKeyStore" lines are artifacts of the `jca` allow-lists
(`{TLSV1.2,TLSV1.3}`; desktop store types). `jca_android` realigns both lists to
the api30 rules, so those categories will collapse in any future campaign **by
oracle change, not by repair** — that drop must never be read as improvement.

KGN/KMF zeros: token search over all fields of all 97,018 lines finds
`KeyGenerator`/`KeyManagerFactory` **nowhere** (output §G). Zero ≠ conformance;
decomposition open (GAMA-SET-21, INCONCLUSIVE). The KGN non-compiling monitor
(§2.5) is *not* the campaign explanation — production `-merge` masks it.

**Empty-label residue (pilot H4) — updated.** Task 8.1 corrected the empty-label
attribution to the weaver and measured 0 empty labels post-GH100 in both arms.
Batch C shows the current artifact retains **live routes** to "but found .":
any consuming event that becomes the monitor's first event (creation-at-consume)
reports with the never-written state field. Executed: tmf_c
(`i1` first ⇒ "expecting one of PKIX but found ." + InvalidSeq) and ssl_c
(`init` first ⇒ UnsafeProtocol "but found ." + InvalidSeq). The realizable
production trigger is FEN-C-UNSAFE-2ARG (§2.3).

### 2.3 FEN-C-UNSAFE-2ARG — the Cipher-repaired capture class, live in 4 specs

`divergence_record.csv` row `b532e439f79a` registers, for CipherSpec, exactly
this defect — "getInstance(transformation, provider) over an unsafe algorithm
matched only the conforming event, whose condition then rejected it: nothing
fired … the init that followed was reported as InvalidSequenceOfMethodCalls
instead of as UnsafeAlgorithm" — repaired there by widening the invalid event to
`(String, ..)`. The same class is **unrepaired and unregistered** in:

- **TMF/KMF**: `g3` is 1-arg; unsafe algorithm via `getInstance(String, ..)` ⇒
  nothing fires ⇒ first-event `i1` pairing + empty label (executed tmf_c).
- **KGN**: `g3` is 1-arg, `g2` conforming-only ⇒ first-event `gk1` pairing +
  empty label (table `gk1[0]=5`).
- **SSL (worst)**: `g2`'s pointcut is `(String, String)` **only**, while the
  frozen android-30 declares `getInstance(String)`, `(String,String)`,
  `(String,Provider)` (measured from class bytes). The rule's `g2:
  getInstance(protocol, _)` covers the Provider overload; the spec makes a
  **fully conformant** creation route invisible, and its `init` is then accused
  from state 0 with the empty label — executed ssl_c with all three REQUIRES
  pre-marked: 2 records on a rule-conformant trace (GAMA-SSL-02, critical).
- **KST**: the rule's `g2` **is** the 2-arg getInstance (`KeyStore.cryptsl:47`);
  the spec reuses the name for the unsafe-*type* 1-arg twin and has **no** 2-arg
  event at all (GAMA-KST-04). Additional side effect: on 2-arg-created stores,
  `load`'s body runs `setProperty(GENERATED_KEY_STORE, keyStore=null)` — the
  real store is never marked, null is — so conformant downstream KMF/TMF `init`
  reads fail (displaced FP).

### 2.4 KST — global monitor, executed (GAMA-KST-01/02/03)

- **kst_a**: two *individually conformant* interleaved keystores ⇒ **3 spurious
  InvalidSeq** (the outer `+` saves sequential lifecycles; interleaving does
  not). Executed FP of the unbound-parameter broadcast.
- **kst_c (cross-object erasure chain)**: A completes `Gets, Loads`
  (`validate(GENERATED_KEY_STORE, ksA)=true`); B's bogus `store()` fails the
  global monitor and its `@fail` removes the mark of the **field's** current
  value — A's (`validate=false` measured); a fully conformant TMF flow over A
  then emits `UnsatisfiedConstraint` (record shown). The wholesale-erasure
  defect class gh101 repaired for KMF/TMF (2-arg removes, rows
  `d2f6d5180a06`/`c48992bd2264`) resurfaces through the shared field.
- **kst_b**: the unsafe-type pairing (§2.1) — the rule's ORDER is satisfied;
  2 of its 3 records are spurious.
- Register search for any of this: 0 hits (`parameterless`, `slice`, `global`,
  `Tuple`, `bind` against KeyStoreSpec rows).
- PASS side (kst_d): conformant lifecycle clean; the three-predicate key marking
  (`GENERATED_KEY`/`GENERATED_PRIVATE_KEY`/`GENERATED_PUBLIC_KEY`, row
  `40cf6d2335e1`) executes true — repair holds.
- OMITIDA: `scE`/`skE1`/`skE2` (setCertificateEntry, both setKeyEntry) declared
  by the rule, no events, no register row; an app's `load → setKeyEntry → store`
  is accused at `store` (displaced site/event, `unknown`) — with a recorded
  oracle ambiguity (Entries declared but absent from ORDER) flagged for Alfa.

### 2.5 KGN — non-compilable artifact + two executed FNs

- **GAMA-KGN-01**: the frozen round artifact `KeyGeneratorSpecRuntimeMonitor.java`
  **does not compile** — `Key generatedKey` (`mop:28`) with no
  `java.security.Key` import (`javac` exit 1, `gama_kgn_compile_error.txt`).
  Inherited byte-for-byte from the `jca` twin. Production is masked **only** by
  `-merge` (`runtime_verification_generator.py:211,269`): the merged monitor's
  import union gets `java.security.Key` from `KeyStoreSpec.mop`. A custom set
  without a Key-importing spec, or any move to per-spec generation, breaks the
  build. Unregistered. (This also caveats the batch A/B "exit 0 ≠ success"
  rule with a new shape: **generation clean, artifact non-compilable**.)
- **GAMA-KGN-03 (executed FN)**: kgn_c — `g1("HMAC-SHA256")` accepted,
  `generateKey` ⇒ 0 records. The api30 rule admits exactly 11 algorithms; the 6
  `HMAC-`/`HMAC/` spellings are extra-oracle. *Registered* (row `53b2fdc6652b`:
  "translation artefacts carried over unchanged"; conformance row 9 groups them
  as aliases) — registered ≠ approved; blocks vs the raw oracle until a formal
  scope reduction or the D-piloto-2 folding test proves alias equivalence
  (Alfa's lane).
- **GAMA-KGN-04 (executed FN, unregistered)**: kgn_d — `AES` with
  `init(64)` ⇒ 0 records; the rule's `alg in {"AES"} => keySize in
  {128,192,256}` is transcribed nowhere (contrast KeyPairGeneratorSpec's
  `initError`, row `151e53aa8e1f`, which repaired the identical shape).
- **GAMA-KGN-05 (latent, minor)**: `g3`'s condition tests
  `currentAlgorithmInstance` (monitor state) where every sibling spec tests the
  **argument**; masked by per-object indexing + the verified g1-before-g3
  monitorCall order (kgn_b executed benign: 0 records, `GENERATED_KEY` marked).
- PASS side (kgn_e): unrandomized `SecureRandom` at `init` ⇒ **exactly one**
  `UnsatisfiedConstraint` and **no** spurious fail — the registered
  body-read-not-guard design (rows `017696e9c911`/`b65be4f34f8c`) works; per-site
  `__LOC` threading verified in the artifact.

### 2.6 SSL — dead Engine pointcut and the 3-clause collapse

- **GAMA-SSL-03**: the engine pointcut declares
  `call(public void SSLContext.createSSLEngine(..))` (`.aj:60`; identical in the
  descriptor JSON); the frozen android-30 declares `public final SSLEngine
  createSSLEngine()` / `(String,int)` — a return-type mismatch of exactly the
  class the register itself documents as repaired for TMF `gtm1` ("the
  KeyManager[] return declared in the pointcut, which getTrustManagers() never
  has", row `038a616babd0`). Engine can never fire: the Engine-position ORDER
  violations are unobservable (FN) and the `GENERATE_SSL_ENGINE` writer is dead
  (harmless to the predicate graph only because the predicate is registered
  terminal — `predicate_omissions.csv:7`). Inherited from `jca`; unregistered.
  Matcher-half execution (ajc `adviceDidNotMatch` / dexlib2 resolution) is
  Beta's lane — named, not assumed.
- **GAMA-SSL-04 / GAMA-SET-17 (executed)**: ssl_b — all three REQUIRES violated
  at one `init` ⇒ **1 record** (the key-managers clause; advice-text order
  decides the survivor). Three distinct rule clauses share
  (type, spec, `__LOC`); two are structurally unreportable per site. Batch B
  FEN-SET-DEDUPE, now in its worst (3-clause) instance. By contrast TMF/KMF
  i1's two reports survive together only because their **types** differ.
- **GAMA-SSL-06**: `FORBIDDEN getDefault() => Gets` has no event and no register
  row (0 hits) — OMITIDA.
- **GAMA-SSL-05 (minor)**: `engine` loops `end→end` while the rule admits
  `Engine?` at most once (ssl_d: second engine silent) — FN direction, currently
  masked by SSL-03.
- PASS side (ssl_d): conformant TLS flow with marked predicates ⇒ 0 records;
  the three per-object REQUIRES reads (gh101 task 3.2) work in isolation.

### 2.7 Synergy table (protocol §13, set level — measured)

Executed: production `mop-extractor.jar -t METHODS_PARAMS` over scratch copies
of the five jca_android specs and their five `jca` twins.

- **GAMA-SET-19 (MEDIDO, PASS)**: 28 target rows, **0** rows with method `new`
  (batch B had 6/20 blind) — batch C is the audit's first fully name-mappable
  batch for the static path. The `jca` vs `jca_android` diff is **one row
  differing only in the signature column** (gtm1 `KeyManager[]`→`TrustManager[]`);
  at the GATOR-client key (`class#method`) the two sets are **identical** — the
  GAMA-SET-01 literal-`jca` default is measured *vacuous* for batch C targets
  (contrast batch B, where it lost `destroy`).
- **GAMA-SET-20 (FAIL)**: the static target list contains
  `SSLContext#createSSLEngine`, a member the production pointcut can never
  capture (SSL-03) — a statically flagged site can never obtain its dynamic
  witness (§13 breach); static `cov_mop` denominators silently include an
  unobservable member.
- Both-views-blind (REF-C-04 shape): no 2-arg `getInstance` row exists in the
  static view either, so the FEN-C-UNSAFE-2ARG creation routes are invisible to
  **both** analyses — a third state, not a contradiction.

Per-clause mappability: KGN 9/9 rows, KMF 5/5, TMF 5/5, SSL 4/5 (the 5th —
`createSSLEngine` — is listed but dynamically dead), KST 6/6 listed but the
rule's 2-arg `g2` member and the three Entries events are absent from both
views. Constraint/REQUIRES clauses (allow-lists, predicate reads) remain
dynamic-only, as in prior batches.

## 3. gh101 register audit (Gama lane: registered vs found)

Accurate registers, verified: allow-list realignments (KGN/KMF/TMF/SSL/KST
`gh99` rows; conformance rows 9/10/13/19/24 match the spec literals);
KMF/TMF layer-2 remove repairs; SSL unsafe_protocol binding + row repair
(`8fee071a456e` — verified against the artifact table); KST three-predicate
write; `GENERATED_TRUST_MANAGER` factory-constant write-no-read
(`predicate_omissions.csv:5`); `GENERATE_SSL_CONTEXT`/`GENERATE_SSL_ENGINE`
terminal (`:6-7`); task 8.1's wrapper-collision account (independently
consistent with my stratification); task 3b.11b's residue register (partial —
see §2.1).

Register absences (searched `data/gh101/*.csv`, `*.md`, exact greps preserved
in the scientific log; **0 hits each**): KST unbound spec parameter / global
broadcast; KST 2-arg getInstance omission; KST setKeyEntry/setCertificateEntry
omissions; SSL `(String,Provider)` capture gap; SSL `createSSLEngine` dead
return type; SSL FORBIDDEN getDefault; KGN AES-keySize constraint; KGN missing
`java.security.Key` import; the same-call pairing consequence of 3b.11b; the
2-arg unsafe-getInstance class for KGN/KMF/TMF (Cipher-only repair).

## 4. History discipline summary (protocol §12)

Freeze verified in-script before read; global sanity equals the pilot exactly
(97,018 / 225 / 113 / 454 / 8,147). Units never mixed; pairing analysis done at
the execution×site **cell** level (pseudoreplication controlled — H7 applied as
a design constraint). Pilot hypotheses on batch C classes:

- **H2 — refuted in immediate form** for TMF/KMF/SSL/KST/KGN: the current
  artifact pairs specific+spurious-`@fail` on the same call (executed §2.1).
  Historical TMF fingerprint (4,599/0/3) consistent; attribution deferred.
- **H4 — mechanism updated**: gh101 task 8.1's weaver attribution verified read;
  the current artifact keeps live empty-label routes (tmf_c/ssl_c executed);
  H4's "unexplained residue" for Signature/MD/Mac remains outside my batch.
- **H1/H7** applied as method (zeros decomposed per spec; cells not raw lines).

**Named replay battery** (G10 pendencies, for the judge's discriminating tests):

1. **G10-TMF-1**: micro-APK calling
   `TrustManagerFactory.getInstance("X509"); init(ks); getTrustManagers()` woven
   by ajc AND dexlib2 — expect the 3-record shape of tmf_a (2 spurious) with
   "but found X509."; the historical arm predicts the same cell signature.
2. **G10-SSL-2**: micro-APK using `SSLContext.getInstance("TLS",
   someProvider)` + `init` — expect ssl_c's 2 false records on a conformant
   trace (decides GAMA-SSL-02 end-to-end).
3. **G10-KST-1**: micro-APK with two interleaved keystores (tink + okhttp
   pattern, the dominant historical sites) — expect kst_a/kst_c contamination;
   paired jca/jca_android replay at `AndroidKeystoreKmsClient.<init>` decides
   how much of the 2,771 only-generic cells the global monitor explains.
4. **G10-KGN-1**: per-spec (non-merge) generation build attempt in the
   production pipeline — decides whether GAMA-KGN-01 is reachable outside the
   audit pipeline.

## 5. Threats to validity

1. **Harness ≙ woven app**: the harness invokes the generated static event
   methods in the advice order verified from the descriptors, but no weaving/DEX
   execution happened — every executed FP/FN carries its named G10 pendency.
2. **KGN patched copy**: all KGN runtime findings run on a 1-line-import scratch
   copy (delta documented, §0); the non-compilability claim itself runs on the
   frozen artifact.
3. **Oracle bias recorded**: api30 rules model availability; the KGN whitelist
   extras may be provider aliases (D-piloto-2 test pending, Alfa); SSL's
   `toUpperCase` matching vs the rule's mixed-case literals is registered
   (conformance row 19) and its equivalence is Alfa's folding test.
4. **Historical data pre-repair/pre-GH100**: hypothesis generation only; the
   task 8.1 register is itself a gh101 artifact — I verified its numbers against
   the raw CSV but its causal story is corroborated, not proven, by my strata.
5. **Matcher halves inferred**: SSL-03/SSL-02/KST-04 capture claims cite
   artifact+API measurements; ajc/dexlib2 matcher execution is Beta's lane.
6. **Extractor path**: exercises `JavamopFacade.listUsedMethods` as the GATOR
   client does, not a full GATOR invocation.

## 6. Verdict inputs per spec (Gama's lane only; dimension-assigned at creation)

- **TMF / KMF**: same-call pairing + delayed residue, executed; unsafe-2-arg
  gap; every sequencing record `unknown` — REPROVADA-supporting; conformant-path
  predicate repairs hold (2 PASS).
- **SSL**: pairing executed; conformant `(String,Provider)` route accused
  (executed); dead Engine pointcut; 3-clause dedupe collapse (executed);
  FORBIDDEN omitted — REPROVADA-supporting; predicate reads themselves work.
- **KST**: globally broadcast monitor (executed interleaving FP + cross-object
  predicate erasure chain), rule-g2/Entries omissions, pairing — the batch's
  most defective spec in my lane.
- **KGN**: artifact non-compilable per-spec (production-masked); two executed
  FNs (whitelist extras — registered; AES keySize — unregistered); pairing;
  REQUIRES read + no-spurious-fail verified PASS.

## 7. Scientific log

| # | Question | Hypothesis | Discriminating test | Evidence | Result | Uncertainty | Next decision |
|---|---|---|---|---|---|---|---|
| 1 | Is the indexing tree per-object in all five? | No for one | artifact indexing decl grep | §1a: KST Tuple2-only, `ks` unbound | KST global (PROVADO) | none | executable FP → kst_a/c |
| 2 | Does the current artifact still pair specific+fail (H2 priority)? | Yes, at the consuming event | tables + 5 harness scenarios | §2.1, i1[0]/init[0]/load[0]/gk1[0]=fail | EXECUTADO 5/5 | G10 weave | FEN-C-PAIRING claims crítica |
| 3 | Does the pairing match TMF's historical fingerprint? | Yes | cell-level stratification, 4 units | 4,599/0/3; two literals only | consistent (MEDIDO) | pre-repair data | GAMA-TMF-05 INC + G10-TMF-1 |
| 4 | Is the empty label dead post-GH100? | No — creation-at-consume route lives | tmf_c/ssl_c first-event drive | "but found ." executed twice | EXECUTADO | realizability via 2-arg routes | FEN-C-EMPTY-LABEL folded into capture claims |
| 5 | Is the Cipher 2-arg repair class present in batch C? | Unrepaired in 4 specs | pointcut arity vs android-30 bytes | §2.3; SSL misses a conforming overload | ssl_c EXECUTADO | matcher half (Beta) | GAMA-SSL-02 crítica |
| 6 | Do same-site multi-clause reads survive dedupe? | No (3-clause worst case) | ssl_b 3-violation drive | 1 of 3 records | EXECUTADO | survivor order under dexlib2 | GAMA-SET-17/SSL-04 |
| 7 | Does KST's @fail contaminate other objects' predicates? | Yes via shared field | kst_c chain probe | validate A true→false; TMF FP record | EXECUTADO | G10 | GAMA-KST-02 crítica |
| 8 | Does the KGN artifact build? | No (missing import) | javac over frozen artifact | exit 1 | EXECUTADO | production `-merge` masks | GAMA-KGN-01 major + G10-KGN-1 |
| 9 | Are the rule's KGN constraints enforceable? | Whitelist FN + keySize omitted | kgn_c/kgn_d drives | 0 records both | FN EXECUTADO ×2 | alias folding (Alfa) | KGN-03/04 |
| 10 | Can the static path map batch C? | Fully, first time | extractor over both sets + diff | 28 rows, 0 blind; key-level diff empty | MEDIDO | client-vs-extractor path | SET-19 PASS / SET-20 FAIL |
| 11 | Is the D-S9 "two philosophies" ground true? | False — set already split | SecureRandom fsm vs KMF/TMF/SSL rows | §2.1 register quote + artifacts | PROVADO | none | GAMA-SET-22 |
| 12 | Are the found defects registered? | Partially | exact greps over data/gh101 | §3 absence list, 0 hits each | OBSERVADO | register semantics (README baseline) | register-absence claims |

## 8. Commands (reproduction)

```
sha256sum <specs>/jca_android/{KeyGeneratorSpec,KeyManagerFactorySpec,TrustManagerFactorySpec,SSLContextSpec,KeyStoreSpec}.mop
sha256sum $WS/MetaCrySL/generated/api30/{KeyGenerator,KeyManagerFactory,TrustManagerFactory,SSLContext,KeyStore}.cryptsl
sha256sum <scratch>/batchC/gen_*/out/*                                   # 20/20 = generation manifest
python3 gama_errors_batchC.py > gama_errors_batchC_output.txt            # in-script freeze check
unzip -o android-30/android.jar javax/net/ssl/SSLContext.class ... && javap -p <class>   # member facts from bytes
javac -nowarn -cp rv-monitor-rt.jar:rvsec-core.jar:rvsec-logger-csv.jar gen_KeyGeneratorSpec/out/KeyGeneratorSpecRuntimeMonitor.java  # exit 1 (GAMA-KGN-01)
javac ... patched/KeyGeneratorSpecRuntimeMonitor.java <other 4 monitors> GamaBatchCDrive.java
for s in tmf_a tmf_b tmf_c kmf_a kmf_b ssl_a ssl_b ssl_c ssl_d kst_a kst_b kst_c kst_d kgn_a kgn_b kgn_c kgn_d kgn_e; do java -cp classes:... gama.GamaBatchCDrive $s; done   # 3 reps, sha-identical
java -jar mop-extractor.jar -d <scratch>/specs_ja -o gama_extractor_ja.csv -t METHODS_PARAMS   # + specs_j twin run
grep -rn "<term>" rv-android/data/gh101/                                 # absence claims, §3
```
