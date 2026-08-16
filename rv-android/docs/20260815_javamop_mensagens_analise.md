# Adversarial Review of "Making JavaMOP Violation Reports Legible"

**Date:** 2026-08-15
**Reviewed artifact:** `docs/20260815_javamop_mensagens.md` (the plan)
**Status:** analysis only. Nothing implemented; the plan was not edited.
**Method:** every `file:line` that carries a decision was re-opened in source by six independent
verifier passes (generator, `rvsec-core`/loggers, `.mop` sets, dexlib2 weaver, Python
parser/writer/consumers, `errors.csv` re-measurement), then the design was criticised against that
evidence. Claims below carry their own `file:line`; anything not re-read is marked **UNVERIFIED**.
Paths are relative to `workspace-rv/rvsec/` unless prefixed otherwise; `O99` = 
`rv-android/results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java`,
`O101` = `rv-android/results/gh101_group8_jca_android/monitors/MultiSpec_1RuntimeMonitor.java`,
`OFZ` = `rv-android/results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`.

**A note on the word "specification", because this repository uses it in two unrelated senses:**

- **SDD / OpenSpec specs** (`docs/SDD.md`, `openspec/specs/**`, `openspec/changes/gh<N>-*/`)
  are *development-process* artifacts: requirements, invariants (`INV-*`) and scenarios that
  document how the RV-Android software behaves and how a change is proposed and verified. When
  this review says "spec delta", "`INV-PLT-19`" or "OpenSpec change", it means these.
- **JavaMOP specifications** (`rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,
  generic_new}/*.mop`) are *runtime-verification* artifacts in the Monitoring-Oriented
  Programming paradigm (MOP: Chen & Roşu — [OOPSLA'07](https://dl.acm.org/doi/10.1145/1297105.1297069),
  [STTT 2011 overview](https://link.springer.com/article/10.1007/s10009-011-0198-6);
  JavaMOP: [ICSE'12](https://fsl.cs.illinois.edu/publications/jin-meredith-lee-rosu-2012-icse.pdf)).
  Each `.mop` declares events over an API (AspectJ-style pointcuts), a property over those events
  (`ere:`/`fsm:`/…), and handlers (`@fail`, `@match`) that run when the property is violated or
  validated; the RV-Monitor generator synthesises the monitor, and the weaver injects it into the
  APK. When this review says "the spec", "spec variable", "orphan event", "`@fail`", "the `jca`
  set is frozen", it means these. The plan under review is about the second kind; the process
  that would implement it is governed by the first kind.

---

## 0. Verdict in one page

**The pillar holds.** The two mechanical facts the whole plan rests on are true:

1. `@fail` is a *state* test on an implicit, unnamed sink that the generator appends to the
   automaton, and every `(state, event)` pair the specification does not write is completed into
   that sink. Verified in `rv-monitor/.../logicpluginshells/fsm/JavaFSM.java:112-142,158` and in
   the generated tables (`O99:7345-7349`, `OFZ:7349,5266,6369,6726,7906`).
2. The `@fail` body is inlined verbatim into an instance method of the monitor class
   (`rv-monitor/.../output/monitor/HandlerMethod.java:34-35,81-90,106`; `O99:7480-7487`), so Java
   written in the `.mop` reaches the monitor's fields without a generator change.

**But the plan describes a pipeline that no longer exists, and it does not know it.** Three
bodies of work on branch `modules` — two changes, one audit, and the researcher's decisions that
followed — are never mentioned:

- **gh101** (`openspec/changes/gh101-jca-spec-conformance/`; commits `2a36defa`, `1217d6ff`,
  `a0f43833`, `233df18a`, `1dd1f4c5`) rewrote `jca_android`: it repaired *all eighteen* orphan
  events there (WS-2.1–2.3 are done in that tree), fixed `KeyPairSpec:38` and the `gtm1` pointcut,
  reconnected the predicate graph, added `AndroidCipherTransformationUtil`, made `jca_android`
  selectable by name — and **froze `jca`**: "not one byte of `rvsec-mop/src/main/resources/jca`
  … changes" (`gh101/proposal.md`, D-S0; gate
  `tests/parity/test_gh101_specset_gates.py::test_frozen_paths_byte_identical_to_base_commit`,
  base `7e7acb69`). Its `tasks.md` reads 84/84 `[x]`, but **the change is open, not archived**,
  and its result was then audited and rejected (next bullet). One of its repairs was **reverted**:
  the identity-keyed `ExecutionContext` (`233df18a`) went back to equality in `e204e2a4`
  (2026-08-11, "revert(e3): the predicate store goes back to equality, and its test goes with
  it"), because the frozen `jca` set had inherited it without passing the freeze gate — 8 of its 27
  `condition(...)` reads answered differently. That revert breaks `jca_android`'s `generatedCipher`
  edge; gh101 records it and stays open. `Property.java` (`GENERATED_CIPHER`, `MACED`) and the
  weaver repair `48b57fc5` were kept.
- **The `jca_android` audit** (`docs/20260808_validar_specs_jca_android.md` protocol;
  `audit/20260808_validacao_jca_android/` — entry point `global/juizglobal_relatorio.md`, final
  decision §10, researcher decision list §7, patch areas §9; commit `f322c5da`) judged the derived
  set **NOT READY: 22/22 audited specs REPROVADA**, 10 gates FAIL, 2 INCONCLUSIVE
  (`RandomStringPassword` excluded by researcher decision). It also states that going back to `jca`
  "does not escape" the defects — it inherits almost all of them (`docs/20260810_plano_prontidao_
  estudo03.md:30`; provenance class `[jca]` in `juizglobal_relatorio.md` §5).
- **The researcher's decision for Study 03** (`docs/20260810_plano_prontidao_estudo03.md`,
  D1–D4; executed in `docs/20260812_comp162.md`, `docs/20260812_registro_execucao_prontidao_e3.md`):
  **Study 03 runs on the frozen `jca` set**; "`jca_android` will not be corrected nor used";
  `ExecutionContext` reverted (D4); the weaver repair kept (`:76` — it changes the `jca` arm's
  result relative to Study 02, towards *more* reports). All 348 E3 logs pass
  `.../resources/jca` (`:300`).
- **gh100** (`openspec/changes/gh100-weaver-emission-fidelity/`, 55/58, open) repaired two dexlib2
  weaver defects that explain part of the *dataset* volume the plan attributes to specification
  logic: (i) fused-advice truncation dropped **nine events from the DEX**, and those nine are
  exactly nine of the plan's eighteen "orphan events" (`gh100/evidence/census_pre_repair.json`:
  `IvParameterSpecSpec c3/c4`, `PBEKeySpecSpec err1/err2/err3`, `PBEParameterSpecSpec c3`,
  `SecretKeySpecSpec c3/c4`, `SecureRandomSpec c3`) — in the dataset those events emitted
  *nothing*, neither the informative record nor the mute twin; (ii) the wrapper registry was
  last-write-wins on `(class, name, params, return)` — "96 wrappers over 84 distinct keys, 10 keys
  bound more than once, 12 wrappers silently discarded, `SecureRandom.getInstance(String)` bound
  three times" (`gh100/tasks.md`, task 5.3) — so in ten of the eleven `jca` specifications that
  bind `getInstance(String)` twice, one of the two `getInstance` advices never fired at any site.
  That is the direct mechanism behind the 1:1 `UnsafeAlgorithm`/`InvalidSequenceOfMethodCalls`
  twins in `TrustManagerFactorySpec` and the 8,371 empty observed values ([inferred] #1) — the
  audit reached the same reading independently ("same-call pairing + delayed residue",
  "empty labels (creation-at-consume, H4 closed live)", `juizglobal_relatorio.md` §5 items 6 and
  the batch C consolidation). For `SecureRandomSpec`'s 12,400 value-less rows the audit's
  site profile points elsewhere: the sites are overwhelmingly `nextBytes` wrappers
  (`secureRandomBytes` 3,962, Ktor nonce loop 3,104, `randBytes` 1,532, …), which is the
  **`next2`-missing-from-`end` false positive** (D03; `FEN-SRD-NEXTBYTES-FP`, H-SRD-1 in
  `audit/.../batchD/gama_report.md:240-256`, replay G10-SRD-1 pending) — not the orphan pattern
  and not the wrapper collision.

**Consequence the plan cannot see: today its specification-level workstreams have no target
set.** `jca` is frozen (and, per the E3 decision, is the set the imminent campaign uses); the
derived `jca_android` is REPROVADA and, by researcher decision, "will not be corrected nor used"
for Study 03. Whether the plan's "next campaign" means Study 03 or the one after it changes what
is executable — see §6.

**Consequences for the plan as written:**

| Plan claim | Verdict |
|---|---|
| §1 "72.93% `unknown` ⇔ `InvalidSequenceOfMethodCalls`" | **Confirmed** (re-measured, exact). |
| §1/§3-L2 "18 orphan events → each violation emits two records" | **Imprecise.** True mechanism; wrong attribution for the dataset (9 never fired; the dominant twin producer is the wrapper collision). |
| §2.2 "27% of the CSV is shadow duplication" | **Reproducible only under a pairing definition** the text does not state; the co-location definition the prose describes gives 33.4%. |
| §1 "73.4% third-party" | **Not reproducible** under ~15 definitions; inconsistent with §2.4's own 85.44%/88.01%. |
| §2.3 "28 actionable findings, 3,465×" | **Not reproducible**; 24–53 depending on the vendor list. |
| §3-L2 SSLContext row "no `UnsafeProtocol` is emitted" | **Wrong.** It is emitted, via the root-monitor clone; plus two mute records; plus contamination of every live `SSLContext`. |
| §3-L2 Cipher and KeyPair rows as "false positives on correct code" | **Wrong against the plan's own ground truth.** `Cipher.crysl:84` forbids `doFinal()` without `update` and re-`init`; `KeyPair.crysl:19` keys the protocol on the constructor. These are CrySL semantics, not translation defects. |
| §3-L3 "a false `condition()` means the event is not generated" and `BaseMonitor.java:604-610` | **Imprecise / wrong citation.** JavaMOP strips `condition()` from the pointcut and inlines it as `if(!cond) return false;` in the monitor's event method; the monitor is created and looked up first. `:604-610` is dead code (`EventDefinition.condition` is never assigned). |
| §3-L2 "`fsm/FSMMin.java:24-28,53-55` completes missing entries" | **Wrong.** FSMMin is a Hopcroft minimiser; completion is in `JavaFSM.java:112-142`. |
| §4 "`Prop_N_state` and `RVM_lastevent` are in scope at `@fail`" | **Only in the synchronized monitor shape.** 16/23 (O99) and 18/23 (O101) monitors are *atomic* and have neither field. Use `getState()`/`getLastEvent()`. And at `@fail` the state is always the sink; the pre-fail state is lost. |
| §5 WS-1.4 "legal continuations derivable by indexing" | **Not derivable at `@fail`** without the pre-fail state. |
| §5 "Phase A … without touching a single line of shared infrastructure" | **Internally inconsistent** (WS-3.1 is radius C). |
| §5 WS-6.6 "re-enable escaping" | **Not a re-enable.** The commented call quotes the *whole line*; the function is buggy (`\R` replacement is discarded when a comma is present). |
| §5 WS-6.2/6.4 (new CSV columns) | **Break** `INV-PLT-19`, `test_errors_csv_header_carries_source_after_method`, and gh103's `read_errors_csv` (raises on any header change). |
| §9 [inferred] #2 (`static final String[]` survives) | **Resolved: viable.** |
| §9 [inferred] #4 (`RVM_loc` re-enable) | **Resolved: not a re-enable** — nothing ever assigned `loc`; needs rv-monitor + javamop + dexlib2. |
| §9 [inferred] #1 (empty observed value) | **Resolved, with an artifact:** pre-gh100 the wrapper registry was last-write-wins, and `gh92_e2e2/monitors/mop/MonitorWrappers.java:588-616` shows three `(String)` wrappers for `TrustManagerFactory.getInstance` of which the last (`g3`) won; `init` on an object with no `g1` clones the global-slice monitor (`""` → `found .`; `X509` → the 643 rows). Not a localisation gap; not okhttp-specific. For `jca` runs (Study 03) the PKIX case is closed by gh100's wrapper merge; the `g3`-binding half of the repair exists only in the shelved `jca_android`, so a non-allow-listed algorithm still yields `found .` under `jca` (`Prop_1_event_g1` assigns after the condition). |
| §3-L5c "highest-value single fix" | **Not established.** For the JCA descriptor no monitor-weaving route clones; only coverage spill on zero-local methods does, and JCA-calling methods usually hold a local. Real, cheap, unmeasured. |

**Recommendation in one sentence:** do not implement the plan as sequenced. Its specification
workstreams have no admissible target today (`jca` frozen and in use by Study 03; `jca_android`
REPROVADA and shelved), its evidence base predates gh100, and it duplicates — without citing —
the audit's §9 patch list (SIG/SSL return types, KPG NPE guard, SRD `next2` ORDER, KPR `co?`,
RANDOMIZED discipline, "specific `expecting` everywhere, stable dedupe keys", dedupe identity).
What survives is (a) the toolchain/parser items that do not touch a `.mop` (§6, tier T0), and
(b) a specification-level tier that becomes executable only when the researcher rules on the
audit's §7 list and a set (repaired `jca_android`, or a successor to `jca`) is unfrozen for the
post-E3 campaign — at which point WS-1/WS-7 should be folded into the audit's item (i), not run
as a parallel plan.

---

## 1. Section-by-section verdicts

Legend: **C** confirmed · **I** imprecise (right direction, wrong detail) · **W** wrong ·
**K** incomplete (misses something decisive).

### §1 The finding — C / I / W

- Numbers: C. 97,018 rows; 19 messages; 70,760 `unknown` = 72.93%; the equivalence
  `unknown ⇔ InvalidSequenceOfMethodCalls` holds in both directions (0 counter-examples either
  way; `unique_msg` consistent with the columns on every row).
- `ErrorDescription.java:34-36`: C. Exactly two constructors (`:34-44`); the literal goes into
  `expecting` (`:31,:42`); no getter/`toString` fallback also yields `"unknown"` (`:58-60,:143`).
  The only other fallback literal in the pipeline is `"(Unknown)"` from
  `ViolationRecorder.getLineOfCode()` for an empty stack — a *location*, not a message.
- "All 21 `@fail` in `jca/` and 21 in `jca_android/` use the 3-arg form": C
  (21 files carry `@fail` in each set; `RandomStringPassword.mop`, `SecretKeySpec.mop` have none).
- "Eighteen events … so each specific violation emits two records": I. See §2 below.
- "73.4% third-party": W (see §1-E4 of the re-measurement).
- "28 findings … 3,465×": W as a number; the funnel's first three stages (661 → 207 → 136)
  reproduce exactly, the last does not (24–53).

### §2 Evidence base — C with four corrections

Re-measured from `ase-journal/dataset/results/errors.csv` with stdlib Python (scripts in the
session scratchpad, not committed):

| Item | Plan | Measured | Note |
|---|---|---|---|
| Message/type distribution (§2.1) | as stated | identical | 12/3/1/2 distinct messages per type confirmed |
| Shadow / orphan (§2.2) | 26,152 / 44,608; 27.0% | **26,152 / 44,608 under min-pairing** Σ min(#InvSeq, #concrete) per `(apk,rep,tool,spec,class,method)`; **32,411 (33.4%)** under "co-located with any concrete row" | The prose describes co-location; the numbers are pairing. The per-spec table equals the pairing definition (SSL 8,798 ≈ 8,802 concrete rows; KS 2,005; Cipher 109). Robust to adding `time` (26,103) or `timeout` (26,152). |
| Event granularity (§2.2) | 46,330 / 20,507 / 32,232 | identical | but `time` is wall-clock **seconds** (17,174 rows at `time=0`); "event" overstates the resolution |
| TMF identical-count sites | 1,733/1,748 | identical (with or without `spec` in the key) | with `timeout` in the key: 4,587/4,602 |
| Funnel (§2.3) | 661/207/136/28 | 661/207/136/**53** with the 11 vendor prefixes named; 36 with `okio.`; 26 by 2-segment own-package; 24 by full package | the three example classes the plan lists among the 28 are own-package, so the 28 was probably an own-package cut, not a vendor cut |
| Attribution (§2.4) | 85.44% / 88.01% / 78 of 113 | 85.44% **only with `okio.` added** (4,050 rows) — not in the plan's list; 88.01% **only with a 2-segment package prefix** (full package: 89.82%, 81 zero-own apps) | one definition should be chosen and named |
| Amplification (§2.5) | 661/15,748/85,257; 11,761 (12.12%); largest identical group 3,098 | first four identical; **largest 10-column-identical group is 6 rows**, not 3,098 | 3,098 is a coarser key |
| Degenerate messages (§2.6) | all | all identical | `SHA-1`/`SHA1`/`SHA` = 1,915+424+1 |
| Empty observed value in TMF | 8,371 | 8,371 across 62 apps | **not only okhttp**: `Platform` 7,174; `TlsUtil` 584; `okhttp3.internal.Util` 324; Ktor 219; two own-package `AdvancedX509TrustManager` (owncloud/opencloud) 51; Conscrypt 19 |
| Apps | 163 | **113 in `errors.csv`**; 163 in `summary.csv`, 50 with zero errors | every per-app % in the plan silently conditions on having ≥1 error |

None of this reverses the direction of the finding; it weakens the rhetoric of §1 and §2.3.

### §3 Root cause — layer by layer

**L1 mute constructor — C.** Inventory correction: `jca/` has **51 textual `addError` lines, 50
live** — `jca/MessageDigestSpec.mop:57` is commented out — so §3/L1's "50 (25/25)" is right and
§3/L7's "51 (25/26)" counts the dead line. `jca_android/`: 75 textual, **74 live (25 mute / 49
with message)**; "24 additional 4-arg sites" is correct. The `Property` enum has **25** values
today (`rvsec-core/.../mop/Property.java:8-55`; 23 before `233df18a` added `GENERATED_CIPHER`,
`MACED`) — "24" was never true.

**L2 FSM sink — C mechanism, W two rows, K on the dataset.**
- Sink: `JavaFSM.java:112` `default_transition = countState`, `:136` fills each missing
  `(state,event)`, `:140-142` appends the sink column mapping to itself (non-accepting trap),
  `:158` `fail condition = $state$ == countState`. Both `ere:` and `fsm:` specs reach it
  (`LogicPluginFactory.java:296-309` → `EREPlugin.java:33-46` → `FSMPlugin.java:67-79` →
  JavaFSM). `ere/FSM.java:53-58` and `EREPlugin.java:21-27` as cited: C. `fsm/FSMMin.java`: **W**
  — it minimises (`:143,:206-218,:315-329`) and does not complete.
- Firing: `@fail` runs after every event while the flag is true (`O99:16020-16023`,
  `O99:2280-2283`); it fires once per violation only because the `jca` handlers call `__RESET`
  (`O99:7482-7486,7495-7499`). `KeyPairGeneratorSpec`'s `@fail` (`jca:110-113`) has no `__RESET`,
  so that monitor stays in the sink and re-reports on every later event.
- **Parameterless events fan out.** `unsafe_protocol` (`jca/SSLContextSpec.mop:46`, no
  `returning`) and `TrustManagerFactorySpec.g3` (`:44`, binds `k` not `mf`) are delivered to *all*
  live monitors of the spec (`O99:2316` `SSLContextSpecMonitor_Set.event_unsafe_protocol`) and
  to the root monitor; a monitor for a later-bound object is created by **cloning the root**
  (`BaseMonitor.java:760-769` `super.clone()`, `O99:15921-15938`), inheriting spec variables. This
  is why `getInstance("TLS")` produces **one `UnsafeProtocol` in `init`'s body plus two mute
  records** and overwrites `currentProtocol` on every live `SSLContext` — the plan's row "no
  `UnsafeProtocol` is emitted" is **W**, and the contamination is a defect the plan does not list.
- Orphan inventory: the 18 `jca` orphans are exactly right (independent script). `jca_android` has
  **zero** (gh101). Additional textual junk in both sets: `GCMParameterSpecSpec.mop:23,34` declare
  two `c1` and the ERE at `:48` names an undeclared `c2` (benign; the generated monitor has one
  `c1` table).
- False-positive table: (a) SecureRandom `next2` missing from `end` — **C**, and still open in
  `jca_android` (`end` block lists `next1, next3, ints`, no `next2`); CrySL `SecureRandom.crysl:38`
  `Ins, (Seed?, End*)*` allows repeated `nextBytes`. (b) SSLContext — **W** as above.
  (c) Cipher — **W as an FP claim**: `Cipher.crysl:75-76,84` `FINWOU := f2|f4|f5|f6|f7; ORDER Get,
  Init+, AADUpdate*, WKB+ | (FINWOU | (Update+, DoFinal))+` — `doFinal()` (`f1`) is legal only
  after `Update+`, and no re-`Init` follows a final. The spec is faithful. The *real* jca defect is
  that `f2 = doFinal(..)` also matches `doFinal()` (AspectJ `(..)` matches zero args; both advices
  on one join point, `OFZ`'s aspect), so one call fires two events; gh101 already made the
  `doFinal` candidates disjoint in `jca_android` (`design.md` D-S11). (d) MessageDigest `reset` —
  **C**, gh101 removed it. (e) KeyPair — **C on the fact, I on the reading**: `KeyPair.crysl:19`
  `Con, (GetPubl|GetPriv)*` keys the protocol on the constructor exactly as the spec does; whether
  `c1` is observed depends on whether `new KeyPair(...)` executes inside the APK's DEX (bundled
  BouncyCastle/SpongyCastle: yes — neither prefix is in the `notwithin` list; platform Conscrypt:
  no). Deviating here would move `jca_android` away from CrySL, against gh101's derivation
  discipline. (f) second `init` — same as (c).
- `MessageDigestSpec.mop:48-52` comment: C, literal.
- **K — the dataset.** The plan explains the volume by orphan events alone. Three mechanisms
  actually coexist, and the plan names one:
  1. orphan-event sink (spec logic) — real for the nine orphans that reached the DEX;
  2. fused-advice truncation — nine orphans **never reached the DEX** (`gh100/evidence/
     census_pre_repair.json`: `eventsDropped: 9`, `errorEmittersDropped: 8`); this is why
     `UnsatisfiedConstraint` has zero rows in §2.1 — a row the plan's table omits without asking
     why;
  3. wrapper-registry last-write-wins (`DexWeaver.java`, pre-gh100; today the guard at the
     registry write throws and `WrapperEmitter` merges) — ten `jca` specs bind
     `getInstance(String)` twice (`grep -c "getInstance(String)" jca/*.mop`), so one advice per
     pair was silently discarded at every site. With `g1` discarded, `init` runs on a fresh
     monitor: `UnsafeAlgorithm … but found .` from `init`'s body **and** `init` from `start` →
     sink → the mute twin, 1:1. gh100's own L3-b gate found "10 false positives … concentrated in
     `TrustManagerFactorySpec`" for exactly this reason (`gh100/evidence/l3_verdicts.md`).
  So "`TrustManagerFactorySpec` is the cleanest proof" (§2.2) is proof of mechanism 3, not 1. For
  `SecureRandomSpec`'s "100% mute; spec emits nothing else" the audit's site profile is the
  better evidence: the 12,400 rows sit overwhelmingly at `nextBytes` call sites
  (`secureRandomBytes` 3,962, Ktor nonce loop 3,104, `randBytes` 1,532, `secureRandomUuid` 1,229,
  SpongyCastle DRBG internals ~1,750 — `audit/20260808_validacao_jca_android/batchD/gama_report.md:
  240-256`, GAMA-SRD-02/H-SRD-1), i.e. the `next2`-missing-from-`end` false positive (D03), which
  the audit executed on a micro-trace (`new SecureRandom(); nextBytes×3` ⇒ two false
  `InvalidSequenceOfMethodCalls`, and `__RESET` re-arms at `start`, so every later `nextBytes`
  accuses too). Neither the orphan `c3/g4/setSeed3` (`c3` never reached the DEX) nor the discarded
  `getInstance` wrapper (`SecureRandom.getInstance(String)` bound three times) fits that profile;
  the audit left the attribution INCONCLUSIVE pending replay G10-SRD-1. The plan lists D03 but
  does not connect it to the 12,400 rows.

**L3 predicate failure — I / K.**
- Mechanism: **I.** JavaMOP removes `condition()` from the pointcut
  (`javamop/.../mopspec/EventDefinition.java:151-156`, `RemoveConditionVisitor`) — the generated
  aspect fires the advice unconditionally (`gh99 …/MultiSpec_1MonitorAspect.aj:662-674`; the
  `.json` descriptor `:2660-2727`) — and inlines the test as a prologue of the monitor's event
  method (`javamop/.../visitor/RVDumpVisitor.java:47-51` `if ( ! (cond) ) { return false; }`;
  `O99:7385-7388`). Effects the plan misses: the monitor **is created/looked up** before the test
  (a creation event with a false condition still leaves a monitor in `start`); the entry point's
  boolean is ignored and handlers re-run on the **stale flags** of the previous event
  (`O99:2280`); and `BaseMonitor.java:603-609`'s `RVM_conditionFail` branch is unreachable
  (`parser/ast/rvmspec/EventDefinition.java:30` has no setter; `RVMonitorExtender.java:256-259`
  passes no condition; zero occurrences in either oracle). Net trace effect equals a hole, so the
  conclusion survives; the cited mechanism does not.
- Predicate matrix for `jca/`: **C** (18 write-only; `GENERATED_PRIVATE_KEY` read at
  `CipherSpec.mop:72` and never written; `KeyPairSpec.mop:38` writes the private key under
  `GENERATED_PUBLIC_KEY`). **K:** in `jca_android` the graph is already reconnected by gh101 — 0
  read-never-written, 11 write-only, 14 both; `KeyPairSpec.mop:58` writes
  `GENERATED_PRIVATE_KEY`. WS-3.4 is done; WS-3.5's "18" is 11 there.
- `SecureRandomSpec.mop:110-116` marks the argument as `RANDOMIZED`: **C** (`TODO` present).
- Three specs that detect nothing: **C** as stated for `jca`. Note that in `jca_android` gh101 kept
  the `condition()`-guarded constructor shape but changed the reads (UNVERIFIED per file).
- API precision: `ExecutionContext` writes via `setProperty` (`:136-143`), reads via `validate`
  (`:152-154`); the deprecated `remove(Property)` that deletes a *whole* set is still called at
  `jca/MacSpec.mop:87`, `KeyManagerFactorySpec.mop:91`, `TrustManagerFactorySpec.mop:87-88`.

**L4 no end-of-trace check — C / K.** `terminateInternal` (`O99:7503-7527`) is all bare returns;
`MonitorTermination.java:104-188` only sets `RVM_terminated`. Grammar: any `@name` is accepted
(`RVParser.jj:288-312`) but fires only if the logic plugin defines `"<name> condition"`; JavaFSM
defines state names, aliases, `fail`, `nonfail` (`:153-159`) — an unknown name NPEs at
`BaseMonitor.java:334`. **K:** JavaMOP *does* have `endProgram()/endThread()/endObject()`
pointcuts (`javamop.jj:356-358`, `EndProgram.java:64` shutdown hook, `EndObject.java` via
`finalize`) — unused by rvsec and **absent from the dexlib2 weaver** (grep = 0). WS-4's radius is
therefore **M + I**, not "M or C".

**L5 localisation — see §4 below (dexlib2 pass).**

**L6 identity — C.** `ErrorSummary.java:73-83,85-120` on `(spec, error, classQualifiedName,
methodName, location)`; `ErrorDescription.java:108-116,136-139` delegates; javadoc at `:132-134`
as quoted. `location` **includes the line** (`ErrorSummary.java:26,89-106`, `FRAME_SUFFIX`).
`rvsec-core/src/test/java/br/unb/cic/mop/eh/ErrorDescriptionTest.java:179-220` asserts this
identity explicitly (`hashCodeMatchesEquals`, `deduplicationStaysLineGranular`) — WS-6.1 flips a
test on purpose; the plan should say so.

**L7 transport — C, with three additions.**
- Format: `ErrorSummary.toString()` (`:123-125`) + `","` + `expecting.trim()`
  (`rvsec-logger-logcat/.../ErrorCollector.java:36-42`); escaping call commented at `:39`; JSE
  sibling escapes only `expecting` (`rvsec-logger-csv/.../ErrorCollector.java:41-42`, header
  `:14`).
- **The escape function is buggy** (identical in `logcat:44-51` and `csv:83-91`): `\R` is replaced
  in `escapedData`, but when the text contains `,`, `"` or `'` the quoted result is built from the
  **original** `data`, so newlines survive inside the quotes. And the commented logcat call quotes
  the **whole line** (which always has commas) — re-enabling it as-is would break every
  positional parser.
- `err.getExpecting().trim()` NPEs on a `null` 4th argument (`logcat:38`, `csv:42`); the
  constructor does not normalise.
- Parser: `logcat_parser.py:305-316,348,361,366-368,371,397` all as cited (no drift). Format 2
  keeps `File.java:NN` in `source`, discards `parts[2]`. **The `\n` case is worse than "dropped
  with a warning":** the continuation line is parsed as an *independent* RVSEC message — ≥5 commas
  → a fabricated Format-2 record; `:::` → Format 3; otherwise the `:371` warning. No counter.
- Schema thesis: **C** — 11-column writer (`result_processor.py:562-576`, `cf234788`
  2026-07-28); `error_type` never a column; `unique_msg` at `log.py:112`; no Python-side
  deduplication anywhere (`coverage.py:574` appends every record).
- Four sets: **C**, except `generic_new` `Log.v` sites are **39**, not 44; the two `[helper]`
  emitters span two lines each (`ServerSocket_Backlog.mop:20-21`, `TreeMap_Comparable.mop:23-24`).

**L8 spec defects — C with drift.**
- Never-matching pointcuts: `SignatureSpec.mop:99,106` C; **`TrustManagerFactorySpec.mop:63`, not
  `:62`** — and `:62` carries a second reason (`returning(TrustManager[][] trustManager)`). The
  `.aj:979,984,1037` numbers belong to an **untracked** `rvsec-mop/src/main/resources/jca/
  MultiSpec_1MonitorAspect.aj`, not to the gh101 oracle (733 lines; `:672,:677,:728`, `gtm1`
  already `TrustManager[]`). `jca_android` still has `byte Signature.sign` at `:120,:127`
  (D07/D08 open in both sets); D09 is closed there (`:106`).
- **The dexlib2 matcher compares the return descriptor exactly**
  (`pointcut-engine/.../PointcutMatcher.java:361-363`, `TypeResolver.toDescriptor:87-106`), so
  D07–D09 are real on Android; only `*` is a wildcard.
- All other `file:line` in the register verified for `jca/`; open in `jca_android` too: D10
  (`:26-29`, `String algorithm;` unset), D11 (`MessageDigestSpec:56`, `KeyGeneratorSpec:59`),
  D18/D19 (`PBEKeySpecSpec:53-55`, `PBEParameterSpecSpec:46-50`), D20 (`:49`). D11 precision:
  the generated aspect groups `g1` before `g4` on the same advice (`OFZ` aspect `:459-465`), so
  `g1` has already written `currentAlgorithmInstance` when `g4`'s condition reads it — the
  defect is latent, not the live false negative the plan describes.
- `CipherTransformationUtil` is at `rvsec-core/.../mop/jca/util/`, lines as cited; extras:
  accepts `CCM` (`:33`) which `Cipher.crysl:97` does not list, and accepts empty padding for
  GCM/CTR where `Cipher.crysl:113` requires `NoPadding`. gh101's `AndroidCipherTransformationUtil`
  supersedes it for `jca_android` (`jca_android/CipherSpec.mop:15`).

### §4 What a report needs — C on the goal, I on the mechanics

- Q1–Q5 framing and the CogniCrypt comparison: **C** (not re-read: `TypestateError.java`,
  `RequiredPredicateError.java` — UNVERIFIED lines).
- "`Prop_N_state`, `RVM_lastevent` … all instance fields": **I.** These names exist only in the
  `AbstractSynchronizedMonitor` shape. `BaseMonitor.java:145-165` picks the *atomic* shape when
  `Main.useAtomicMonitor && isSimpleFSM && isOutermost && monitorInfo == null &&
  !isTimeTrackingNeeded`; there, state and last event are packed into an `AtomicInteger`
  (`O101:7667-7690`), and neither field exists. `SSLContextSpecMonitor` is synchronized in O99
  (`:7324`) and atomic in O101 (`:7639`) — **the shape flips with spec edits.** Portable
  accessors: `getState()`/`getLastEvent()` (`rv-monitor-rt/.../tablebase/IMonitor.java:19,25`;
  `AbstractSynchronizedMonitor.java:5,21-22`; `O101:7674-7679`).
- "the legal continuations from any state are derivable by indexing": **W at `@fail`.** By the
  time the handler runs, `getState()` is the sink; the pre-fail state is stored nowhere. Only the
  last event id survives — and `__RESET` sets it to −1 (`BaseMonitor.java:955`; `O99:7496`), so
  the message must be composed before `__RESET`. Recovering the pre-fail state needs either a
  generator change or a per-event bookkeeping line in every event body (the body runs before the
  transition, so `getState()` there is the pre-transition state).
- "`__RESET` does not clear specification variables": **C** (`monitorDeclaration` once at `:786`;
  `reset()` at `:950-968` re-emits only `localDeclaration`, which JavaFSM never sets). Corollary
  the plan does not draw: a "current" spec variable in a `@fail` message may be from a *previous*
  sequence on the same monitor.
- "Seven of the 21 `@fail` already read those fields": **I** — none reads `Prop_1_state`/
  `RVM_lastevent` (grep = 0 in both sets); seven read *spec variables* to clear `ExecutionContext`
  (eight in `jca_android`).
- No `int → String` table: **C** (`BaseMonitor.java:1057-1061`; `O99:7530-7536,8703-8712`;
  `--internalbehavior` trace is the only exception, off by default).
- Event ids follow declaration order (`terminateInternal` comments `case 0: //g1 … case 4:
  //engine`), which is what makes a hand-written event-name table feasible. State ids come from
  FSMMin's minimisation — it merges equivalent states (`O101:7661`: the spec's `start` and
  `unsafeProtocol` collapse) — so a hand-written *state*-name table is fragile and, at `@fail`,
  useless (the state is the sink).

### §5 The plan — per workstream (see also §3 of this review)

| WS | Verdict | Evidence |
|---|---|---|
| WS-1 | **needs redesign** (names, pre-fail state, `__RESET` order, identity coupling, volume) | §4 above; §3.1 below |
| WS-2 | **2.1–2.3 already done in `jca_android`** (gh101); 2.4 open and CrySL-backed; **2.5/2.6 contradict CrySL** | orphan grep; `Cipher.crysl:84`, `KeyPair.crysl:19` |
| WS-3 | 3.1 is radius **C** (contradicts Phase A's claim); 3.2 interacts with automata (a formerly-suppressed event now transitions — must be co-designed with WS-2 or it becomes a new orphan); 3.4 done; 3.5 is 11 not 18 in `jca_android` | `Property.java`, gh101 |
| WS-4 | radius **M + I**, not "M or C" | L4 |
| WS-5 | see §4 of this review | dexlib2 pass |
| WS-6 | 6.1 flips `ErrorDescriptionTest` and composes badly with WS-1.2/WS-2; 6.2/6.4 contradict `INV-PLT-19` and gh103's header contract; 6.5 fine; **6.6 is not a re-enable**; 6.7 fine | §3.5 below |
| WS-7 | item 1 half done (TMF closed, Signature open in both sets); items 2–5 open in `jca_android` (new line numbers); items 6–8 open; item 9/10 open | §3-L8 |
| WS-8 | 8.5 half done (`jca_android` selectable — `__main__.py:443`, `config.py:688-694`; `generic_new` still absent); 8.7 confirmed | Python pass |

### §6 Decisions — two were already taken elsewhere

- **D-1 has already been decided for Study 03, and the plan's framing of it is stale.** The plan
  weighs `jca` vs `jca_android` on allow-list bias alone. The record is: `jca` is frozen
  byte-for-byte (gh101 D-S0; `INV-INS-109 a`); `jca_android` was audited and judged NOT READY
  (22/22 REPROVADA — `audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` §10);
  and the researcher decided that **Study 03 uses `jca`** and that `jca_android` "will not be
  corrected nor used" (`docs/20260810_plano_prontidao_estudo03.md` §2, D1). If the plan's "next
  campaign" is Study 03, none of its `.mop` edits is admissible; if it is the campaign after, the
  choice is between repairing `jca_android` along the audit's §9 list (gated by the ten researcher
  rulings of §7) or unfreezing a successor to `jca` — and either way the plan's spec workstreams are
  a subset of the audit's patch area (i) and should be merged into it, with the audit's provenance
  discipline (`[jca]`/`[gh101]`/`[tool]`/`[oracle]`) and its regressive examples.
- **D-2 is already made.** gh100 (event set changes: 9 events restored, wrappers merged — kept for
  E3 by decision D3) breaks count-comparability of the `jca` arm with the published measurements
  in the direction of *more* reports (`docs/20260810_plano_prontidao_estudo03.md` "Consequência
  de D3"; `gh100/evidence/green_deltas.md:53-56`). The plan's break would be incremental; the
  re-baseline it recommends is unavoidable and should come **first**, not after implementation.
- The `ExecutionContext` identity store the plan's L3/WS-3 implicitly relies on for `jca_android`
  is **no longer in the tree** (`e204e2a4`); WS-3.4/3.6 in `jca_android` are half-broken by that
  revert (`generatedCipher` edge), which the plan cannot know.
- D-3 (scope): see §4 of this review.
- D-4/D-5/D-6/D-7/D-8: stand as decisions; D-7 note that `generic_new` is still not in the CLI
  (`click.Choice(["jca","jca_android","generic","custom"])`).

### §7 Acceptance criteria — three need rewording

1. Zero `unknown`: verifiable. **But** with the message outside identity, criterion 6 ("one distinct
   message per mode") cannot be met within one process for modes that occur at the same
   `(spec,type,class,method,line)` — the first record wins (`ErrorCollector.java:37`). Either 6
   is measured across separate processes/apps, or it depends on WS-6.1.
2. Zero empty observed values: **already delivered by gh100 (wrapper merge) + gh101 (`g3` binds
   `mf`)**, not by anything in the plan; keep as a regression check.
3. `error_type`/`source`/`is_library` columns: contradicts `INV-PLT-19` as written; needs a spec
   delta co-scheduled with gh103 (`aperv-tool/analysis/violations.py:60-72,243-247`).
5. "Zero violations on the six FP patterns": **wrong target for two of the six** — under CrySL,
   `init; doFinal()` and re-`init` are violations; the correct target there is *one violation with
   a message naming the missing `update`*, not zero.
7. Signature signing branch reaches `@match`: meaningful on Android (return type is matched
   exactly) — good criterion.
8. Line-number ratio before/after: verifiable offline (baksmali), no emulator needed — good.

### §8 Register — corrections

D01 C · D02 **I** (9 of the 18 never fired in the dataset; all 18 closed in `jca_android`) ·
D03 C (open in both) · D04 C (closed in `jca_android`) · **D05 W** (CrySL-conformant) · **D06 I**
(CrySL-conformant; observability depends on the DEX) · D07/D08 C (open in both) · D09 C (`:63`;
closed in `jca_android`) · D10 C · **D11 I** (latent) · D12 C · D13 C (closed in `jca_android`) ·
D14 C (closed in `jca_android`) · D15/D16 C (superseded for `jca_android`) · D17 C · D18–D20 C
(open in both) · D21–D24 see §4 · D25 C · D26 C · D27 C (+ escape bug) · D28 C · D29 C · D30 C ·
D31 C · D32 C · D33 C · **D34 I** (18 in `jca`, 11 in `jca_android`) · D35–D41 C · D42 C ·
D43 C · D44 UNVERIFIED (not re-read) · D45 C (lines) · D46 C · D47 C · D48–D50 see §4.
**Missing from the register:** parameterless-event fan-out and root-monitor cloning
(contamination); fused-advice truncation and wrapper collision (dataset provenance, closed by
gh100); the escape-function bug; `null` `expecting` NPE; `GCMParameterSpecSpec` duplicate `c1`
/ undeclared `c2`; the untracked `.aj` inside `jca/`; `KeyPairGeneratorSpec` `@fail` without
`__RESET` as a *volume* defect (monitor stuck in the sink re-reports on every event).

---

## 2. The four `[inferred]` claims — resolved

1. **Empty observed value (8,371 rows).** Resolved, high confidence, two cooperating mechanisms:
   (a) pre-gh100 the wrapper registry key was `(class#name(params)return)` and a second wrapper
   for the same key overwrote the first — the current guard's own comment records the old
   behaviour: "the last write would win and the earlier wrapper's monitor events would never fire
   at that site" (`dex-mutator/.../DexWeaver.java`, registry write); `TrustManagerFactorySpec`
   binds `getInstance(String)` in `g1` and `g3` (`jca:29,44`), so at every site one of them was
   discarded; (b) `init` on an object with no `g1` creates its monitor by cloning the root
   (`BaseMonitor.java:760-769`), whose `currentAlgorithmInstance` is `""` unless an unbound `g3`
   wrote it — which is exactly the 643 `but found X509` rows (`g3` won the key, wrote `X509` on
   the root, `init` inherited it). Consistent with all counts, with the 1:1 twin (`init` from
   `start` → sink), with the 14% of empty-value rows outside okhttp, and with gh100's L3-b
   finding. Which wrapper won is no longer inferred: the pre-fix artifact
   `rv-android/results/gh92_e2e2/monitors/mop/MonitorWrappers.java:588-616` holds three `(String)`
   wrappers for `getInstance` — `_getInstance` → `g1Event`, `_getInstance_1` → `g2Event`,
   `_getInstance_4` → `g3Event` — and the last registered (`g3`) won. For Study 03 (`jca`) the
   PKIX case is closed by gh100's merge (kept, D3); the `g3`-binding repair lives only in the
   shelved `jca_android`, so under `jca` a non-allow-listed algorithm still reports `found .`
   (assignment after the condition in `g1`). See §4 for the runtime trace.
2. **`static final String[]` in the declarations block.** Resolved: viable. rv-monitor keeps
   declarations as raw text (`RVParser.jj:253` → `JavaParserAdapter.java:173` → `UserJavaCode`
   → `BaseMonitor.java:786`); JavaMOP parses the block as a class body with modifiers
   (`javamop.jj:1276,1611-1623`) and re-prints modifiers (`DumpVisitor.java:814-826,207`);
   precedent `javamop/examples/ERE/SafeFileWriter/SafeFileWriter.mop:12` `static int counter`
   → `.rvm:11`. No rvsec spec uses it yet (UNVERIFIED in an rvsec oracle, but follows from the
   path).
3. **WS-4 volume on Android.** Still unmeasured; nothing in the tree measures it. Two facts bound
   the risk: JavaMOP's `endObject` is GC/`finalize`-driven and absent from dexlib2, so any
   implementation is new infrastructure; and parametric monitors are per object, so the count is
   "live monitors not in an accepting state at process death" — unbounded by construction on a
   platform that kills processes routinely. Prototype-first stands.
4. **`RVM_loc`.** Resolved: **not a re-enable.** The variable is threaded through `Monitoring(...)`
   signatures (`Monitor.java:131`, `MonitorSet.java:766`) but nothing ever assigns it; the
   generated entry points take only bound params (`O99:15717`), the descriptor's
   `monitorCalls.args` lists only advice params (`.json:2672-2677`), and dexlib2's
   `MonitorInvokeBuilder.java:163-169,237-248` builds the invoke strictly from those args. Turning
   it on = rv-monitor (new param) + javamop (`thisJoinPointStaticPart` into `.aj`/descriptor) +
   dexlib2 (constant arg). The one precedent for a weave-time constant argument is
   `ThisJoinPointEmitter.java:9-12` (used for `staticinit`), which is also the channel WS-5.9
   would need.

---

## 3. Design critique (handoff §3.1-C)

### 3.1 Phase A does touch shared infrastructure, and WS-1 is not as cheap as stated

- WS-3.1 (new `ErrorType`) is radius C; WS-3.5 is S/C. The sentence "without touching a single
  line of shared infrastructure" is false for Phase A as drawn.
- WS-1's "cheap" depends on three things the plan gets wrong (§1-§4 above): the field names, the
  availability of the pre-fail state, and the order relative to `__RESET`. A correct WS-1 is
  still spec-only, but it is: `getLastEvent()` + a hand-written event-name array + the spec
  variables + the object, composed **before** `__RESET` — and it answers Q1 and Q5, only part of
  Q2. "Expected one of" needs either one bookkeeping line per event body or a generator change.
- WS-1.2's "monitored object's identity hash" should be dropped: with WS-6.1 it makes every
  object a distinct record (volume unbounded); without WS-6.1 it is deduplicated away and adds
  nothing.

### 3.2 Sequencing

WS-7 → WS-2 → WS-1 → WS-3 is right in spirit, with two corrections:

- **A re-baseline comes before all of it, and Study 03 provides it for free.** The evidence base
  is the 2026-07-06 dataset, pre-gh100. E3 runs `jca` with the weaver repair (D3), so its first
  batches are the first post-repair measurement of `unknown` share and pairing. Until that is
  read, the value of WS-1..3 is unknown — and the specification tier is not admissible anyway
  (§6).
- **The plan's spec workstreams are a subset of the audit's patch list and must be merged into
  it.** `audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` §9/§10.5 already
  names SIG/SSL return types, KPG NPE guard, KPR `co?`, SRD `next2` ORDER, RANDOMIZED discipline,
  "diagnostic messages (specific `expecting` everywhere, stable dedupe keys)" and "dedupe identity
  (include `expecting` or a clause/constraint id)". Running the plan beside it would produce two
  competing repair programmes over the same 21 files, one of them without the audit's
  regressive examples and provenance classes.
- **WS-3.2 is not independent of WS-2.** Inverting `condition()` into the body makes a
  previously-suppressed event *transition*. If the automaton was written assuming the event only
  fires when the predicate holds, the new firing lands in the sink — a fresh orphan. WS-3.2 must
  be designed together with the automaton edit, spec by spec.

### 3.3 Remove vs. give a transition to the orphan events

Three options exist; the plan considered one. (A) keep the violating-branch event and add a
transition (Kleene prefix / explicit `unsafeAlg` state) — what gh101 did; (B) delete the event
and move the check into the body of the legitimate event with the condition dropped; (C) a
self-loop, equivalent to A. B is smaller (fewer events → fewer pointcuts, fewer wrappers, smaller
coenable strings — gh101 measured `CipherSpec` generation falling from 53 s / 3.3 GB to 6 s /
1 GB when its alphabet was re-budgeted, so event count is not free) but loses the ability to say
"after an unsafe instantiation" in the automaton, and is impossible where the violating branch is
a different overload. For `jca_android` the question is **moot**: A is done and INV-INS-110
(no bound event with an all-`fail` row) guards it. The plan should replace WS-2.1/2.2 with
"verify INV-INS-110 holds; nothing to do".

### 3.4 Hand-written tables vs. generator emission

The "×4 sets" maintenance argument is inflated: `generic`/`generic_new` have no `ErrorCollector`
`@fail` at all, and `jca` is frozen — so exactly **one** set (21 files) carries tables. A
hand-written **event**-name array per spec is cheap and stable (declaration order); a
**state**-name array is fragile (FSMMin renumbers/merges) and useless at `@fail`. Recommendation:
event names by hand now; if "expected one of" is wanted, prefer the generator emitting
`RVM_prevState` and `String[] eventNames` (radius M, small, one-time) over 170 bookkeeping lines
in event bodies.

### 3.5 WS-6.1 × WS-2 × WS-1.2 — the composition the plan does not do

- WS-2 (done by gh101 for `jca_android`) reduces mute records.
- WS-1 without WS-6.1: distinct informative messages at the same `(spec,type,class,method,line)`
  collapse to the first — WS-1's own verification criterion cannot be met in-process.
- WS-1 with WS-6.1: identity grows by the number of distinct message *values* per site; for specs
  whose message embeds an observed value (`… but found " + currentTransformation`) the bound is
  the number of distinct values, not sites; with an identity hash in the message, unbounded.
- **Middle option the plan does not consider:** add a *structured* field to identity — the
  offending event name (an int/short string) — instead of the free-text message. That
  distinguishes the modes WS-1 wants to distinguish without letting values or hashes multiply
  records. `ErrorDescriptionTest.java:179-220` flips either way; say so.

### 3.6 Acceptance criteria — see §1 (§7 subsection) above: three rewordings.

### 3.7 Missing workstreams

- **Performance**: `ViolationRecorder.getStack()` is `new Exception().getStackTrace()` (`:37-39`)
  per *report attempt* — evaluated as the `addError` argument, i.e. before the `HashSet` decides
  (`O99:9163-9185`, `MultiSpec_1_RVMLock` held, `enableFineGrainedLock(false)`). WS-5.8 mentions
  it in passing; it deserves its own line, with a measurement, because a richer message does not
  change it and a `@fail` without `__RESET` multiplies it.
- **Process restart**: covered by 6.7 (per-process `HashSet`), but the plan does not note that
  the `HashSet` and the singleton are unsynchronised (`ErrorCollector.java:10-22`) and are only
  serialised today by the monitor lock — any `addError` outside a handler races.
- **Message content rules**: no `\n` (parser splits and fabricates), no `:::` (`unique_msg`
  5-way split in `log.py:112`, `INV-CORE-25/41`, aperv-tool `_UNIQUE_FIELDS = 5`), and a
  documented position (last field). Cheap to enforce with a test over the `.mop` bodies in
  `rvsec-mop`; the plan has no such rule.
- **A synthetic-app suite** for §7.5–7.7 does not exist and needs an emulator run via
  `rv-experiment run` — it is a workstream, not a footnote.
- **The gh100/gh101/audit overlap** itself: the plan should cite all three, state what they
  closed and what was reverted (`e204e2a4`), and inherit gh101's divergence-record discipline
  (`INV-INS-109 b`) and the audit's provenance classes for every `jca_android` edit.
- **Toolchain findings of the audit that the plan does not list and that would corrupt the next
  campaign regardless of messages** (`juizglobal_relatorio.md` §5 items 2, 5, 7): first-call
  disjunct drop (CIS/COS/KPG) `[tool]`; declared-only member index killing inherited members (SRD
  `nextInt()`, `ints`) `[tool]`; varargs `args()` narrowing ignored under the production-default
  jar `[tool]`; nested-type descriptors unweavable (KST `getEntry/setEntry`) `[tool]`; generators
  exit 0 for uncompilable artifacts (KGN, masked by `-merge` import union), parse errors and
  undefined ERE symbols `[tool]`; the static path silently analysing `jca` for `jca_android` runs
  (G12 — `rv_experiment/config.py:942-951`, `rv_static_analysis/config.py:199-208`); wrapper-name
  instability and lexicographic-max `android.jar` selection (host 37.0, Docker 36, oracle 30).

---

## 4. Localisation (L5 / WS-5 / D-3) — dexlib2 pass

Module `M = rvsec/rvsec-android/rvsec-instrumentation-dexlib2`.

**L5a (one frame survives) — C.** `__LOC` → `Util.defaultLocation` (`BaseMonitor.java:361-362`,
`RawMonitor.java:104-105`, `HandlerMethod.java:45`, `output/Util.java:7-8`);
`ViolationRecorder.java:53-60` returns `relevantStack.get(0).toString()`; the exclusion in
`makeRelevantList` (`:87-105`) fires only when `fileName != null && className != null` **and** the
class starts with `com.runtimeverification.rvmonitor.`/`javamop.`/`mop.`/`rvm.` or the file
contains `.aj` — so a `mop.*` frame with a null `fileName` is kept (L5f, latent, C).

**L5b (scope) — C, and dexlib2 honours it.** `DescriptorWriter.java:68-70` and `:233-248` are the
twelve prefixes as listed. The weaver parses `commonPointcut` (`DexWeaver.java:317`), hoists it
when class-invariant (`:328,:750-759`) and gates **both** wrapper substitution and inline weaving
per class (`:367-374`, `continue` before pass 1); `PointcutMatcher.java:152-156,178-184` expands
`BaseAspect.notwithin()` (`BaseAspectExpander.java:37-49`). Unparseable `commonPointcut` now
fails the weave (`:885-895`, gh100). `PackageFilter.java:22-39,41-43` (coverage only,
`CoverageWeaver.java:116`) has 16 prefixes incl. `android/androidx/kotlin/kotlinx/com.google`,
no `okhttp3` — two divergent policies confirmed; e.g. Tink (`com.google.*`, 31 `MacSpec` rows) is
monitor-woven but not coverage-probed.

**L5c (debug info destroyed by cloning) — C on mechanism, I on impact.**
`RegisterShifter.cloneInstructions` (`:174-268`) builds `new MutableMethodImplementation(newCount)`
(`:176`) and copies instructions/labels/try-blocks only; grep for
`DebugItem|addDebugItem|getDebugItems|LineNumber` across the module = **0**. dexlib2's copying
ctor does copy debug items (`smali-dexlib2-3.0.9` `MutableMethodImplementation.java:184-191`),
which is what `DexFileMutator.forMethod` uses (`:129-130`), so un-cloned methods keep them.
`DexWriter.java:1155-1158` (not `:1156-1159`): `debug_info_off = 0` only if there are also no named
parameters; with parameter names the item exists but has no positions — same visible effect (no
line). Callers of the clone path: `CoverageWeaver.java:167` (`localCount < 1`, `:153-155`),
`DexWeaver.java:657` (staticinit prepend), `RegisterAllocator.java:44` (only when
`scratchCount() > 0`), `InstructionInjector.java:359` (after-throwing wrap). **For the JCA
descriptor none of the monitor routes fires**: `gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json`
has 115 advices — 97 `after` (wrapper-routed, `WrapperEmitter.java:161-163`), 18 `before`
(`RegisterRequest.NONE`), 0 throwing / `if` / staticinit. Wrapper substitution rebuilds only the
invoke (`DexWeaver.java:394-405` → `InstructionInjector.replaceInvoke`), no clone. So the only
live route is coverage spill on zero-local methods (advice weave first, coverage second, same
`DexFileMutator` cache — `BatchRunner.java:265,299,249,289` — so a zero-local JCA-calling method
loses its lines too). Methods that call JCA APIs typically hold a local (e.g. `Platform.
platformTrustManager` is reported *with* line 83), so the impact on **reported JCA frames** is
plausibly small; unmeasured (no spill counter — `CoverageWeaver.java:194-196`). WS-5.4/5.5 remain
correct and cheap, but "the highest-value single fix in this workstream" is not established.

**L5d (`RVM_loc`) — C lines; see [inferred] #4.** `MonitorSet.java` lives in `output/monitorset/`.

**L5e (site statically recoverable) — C.** `DexWeaver.java:359-555` loop, `SignatureFormatter.java:
27-40`, `CoverageWeaver.java:181-183`, `InstrumentationCli.java:39-115` (no scope option),
`:146-147` key with `:170-176` guard, `:861-869`/`:716-721` swallowed counters, `:978-1008`
`WeaveReport`, `BatchRunner.java:379-383` `ex.getMessage()` — all as cited (minor drift only).
The channel constraint (one wrapper per signature; extra register → clone) is real; the precedent
for a weave-time constant argument is `ThisJoinPointEmitter.java:9-12`.

**Return-type matching (D07–D09 on Android) — C.** Inline path `PointcutMatcher.matchCall`
(`:308-406`): owner exact or `+` via `InheritanceResolver` (`:334-343`), name (`:350-351`),
**return descriptor exact unless `*`** (`:361-364`), params exact/subtype (`:377-396`). Wrapper path
`WrapperEmitter.expandCallTarget` (`:396-397,444-453`) also rejects a mismatched return, arrays by
rank; the registry key includes the return descriptor (`DexWeaver.java:146-147,263-268`).

**D-3 (scope) — recommendation stands** (keep whole-APK, label origin, add an app frame), with one
correction to its cost: an `is_library` label can be computed **offline** from the class name and
the APK's own package (the analysis layer already derives the package key from `dataset.csv`, per
`INV-ANA-58`), which does not require WS-5.1/5.2. The app frame does.

**[inferred] #1 — established with an artifact.** The dataset predates the wrapper merge
(`errors.csv` README: 2026-07-06; merge commit `48b57fc5`, 2026-08-07). Pre-fix
`gh92_e2e2/monitors/mop/MonitorWrappers.java:588-616` has three wrappers with signature `(String)`
for `TrustManagerFactory.getInstance`: `_getInstance` → `g1Event`, `_getInstance_1` → `g2Event`
(`(String, ..)` expands to the 1-arg overload, `WrapperEmitter.java:383-384`), `_getInstance_4` →
`g3Event`; last write wins → **every `getInstance(String)` site fired only `g3`**. Then
`gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java:16327-16410`: `g3` binds `k` → global slice;
`initEvent(mf)` clones the global-slice monitor; `Prop_1_event_init` reports
`UnsafeAlgorithm … but found <global value>` and `start --init--> fail`. Predicts PKIX → `found .`
+ `unknown`; X509 → `found X509.` + `unknown` — matches 8,371 / 643 / 9,015 exactly. Not
okhttp-specific (`Platform.kt` 4.12.0 `:78-80`; `:83` in the CSV is a version offset). Residual
after the fix in the frozen `jca`: a non-allow-listed algorithm still yields `found .` because the
assignment sits after the condition (`Prop_1_event_g1`, `:8835-8843`); `jca_android` binds `g3` to
`mf` and adds `unsafeAlg`.

---

## 5. Risks the plan does not cover (handoff §3.1-D)

| Consumer / contract | Reads | Breaks under WS-1 (rich message) | under WS-6.2/6.4 (columns) | under WS-2 (counts) | Evidence |
|---|---|---|---|---|---|
| `logcat_parser.py` Format 2 | 7 comma fields, `parts[6:]` rejoined | commas fine; **`\n` → fabricated second record**; `:::` poisons `unique_msg` | n/a | n/a | `:319-349,371` |
| Device `HashSet` | `ErrorSummary` identity | richer text never re-emitted at the same site | n/a | source of counts | `ErrorCollector.java:37`, `ErrorDescription.java:131-133` |
| `RvErrorLog.unique_msg`, `summary.csv` `mop_errors_unique` | 5-way `:::` | more distinct keys per site; `:::` breaks split | — | changes | `log.py:112`, `coverage.py:575,627`, `result_processor.py:805-806` |
| `errors.csv` writer + test | exact 11-col header | csv-quoted, fine | **`test_errors_csv_header_carries_source_after_method` fails; `INV-PLT-19`** | rows change | `result_processor.py:562-576`, `test_result_processor.py:248-262` |
| gh103 `aperv-tool/analysis/violations.py` | `ERRORS_CSV_HEADER` exact tuple; `unique_msg` 5 parts; raw split bounded at 6 | commas fine; `:::` → `unique_msg_unparsed`; `\n` → extra violation with `shape_ok=False` (INV-CAN-04) | **`read_errors_csv` raises `ValueError`** | changes gate inputs (by design) | `:60-72,140,243-247,263-267` |
| `clock_logcat_join._parse_payload` | `split(",", 6)` | fine | n/a | per-step counts | `clock_logcat_join.py:455-462` |
| Campaign consolidators (`experimento-cal`, `-20260721`, `-comp162`) | regex `\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$` | `\n` continuation lines **not** counted (diverges from aperv-tool) | n/a | changes `mop_total` | frozen readers per `INV-APV-55`; not at risk, but their numbers are not comparable |
| `TraceComparator` (gh100) | 7-field payload, `EXPECTING_INDEX = 6` | tolerant | n/a | oracle matching | `TraceComparator.java:734-741` |
| OpenSpec invariants | — | `INV-CORE-25/41` (`unique_msg` formula), `INV-ANA-08` (format), `INV-ANA-46` (golden output) | `INV-PLT-19/24/25/26`, `core/spec.md:867-903` | `INV-CAN-04` (no silent drop) | `openspec/specs/*` |
| `jca` freeze | — | any `jca/*.mop` edit violates `INV-INS-109 a` | — | — | gh101; E3 D1 |
| Study 03 (comp162) | `jca` + gh100 weaver + reverted store | a message change mid-campaign would split the E3 record | same | same | `docs/20260810_plano_prontidao_estudo03.md`, `docs/20260812_comp162.md` |
| `jca_android` audit | 558 claims / 119 phenomena over the same 21 `@fail` files | any WS-1/WS-7 edit not entered in the audit's ledger and divergence record is untraceable to a verdict | — | — | `audit/20260808_validacao_jca_android/` (`claims/`, `global/`) |

No invariant mentions the literal `unknown` — removing it is spec-free.

---

## 6. Proportionality — minimal defensible cut (handoff §3.1-E)

Premises, all from the record: Study 03 runs on the frozen `jca` (`docs/20260810_plano_prontidao_
estudo03.md` D1); `jca_android` is REPROVADA and shelved (audit §10; D1); gh100's weaver repair
is kept (D3); the identity store is reverted (D4, `e204e2a4`); monitor generation is not
parallelisable; no emulator is managed by hand. Two tiers follow, by what is admissible **when**.

**Tier T0 — admissible now, without touching any `.mop`** (usable for Study 03's post-processing
and for any later campaign):

| # | Item | Radius | Why |
|---|---|---|---|
| T0.1 | **Re-baseline the message problem on the current branch**: on the E3 pilot / first batches (already `jca` + gh100 weaver), measure `unknown` share, InvSeq/value pairing and rows per site with the same scripts used for §2 of the plan | none | the plan's evidence is pre-gh100 (2026-07-06 dataset); the E3 outputs are the first post-repair measurement and cost nothing extra |
| T0.2 | WS-6.5 — explicit sentinel for fabricated `error_type`/`source` in parser Formats 1/3 | P | stops the analyst-facing lie; co-schedule with gh103 (`aperv-tool/analysis/violations.py` header/`unique_msg` contracts, `INV-CAN-04`) |
| T0.3 | Message-content rule and its test (no `\n`, no `:::`, last field) — as a `rvsec-mop` test over the `.mop` bodies **and** a parser-side guard that counts (not fabricates) continuation lines | S-test/P | prerequisite for any richer message; the audit lists "dedupe emission loss" and `\n` handling among the toolchain items (§9 (ii)) |
| T0.4 | Fix `escapeSpecialCharacters` (both collectors) and the `null`-`expecting` NPE — **without** re-enabling the whole-line call | C | the function is wrong today; fixing it is not a behaviour change while the call stays off |
| T0.5 | Decide WS-6.1 as the audit frames it — "dedupe identity (include `expecting` or a clause/constraint id)" (§9 (ii)) — preferring the structured id (event name / clause id) over the free text; write the spec delta for `ErrorSummary` identity and `ErrorDescriptionTest:179-220` | C | the audit measured the loss ("dedupe probe `3a658775…`", §10.3); the plan and the audit converge here |

**Tier T1 — specification-level, admissible only after the researcher rules on the audit's §7
list and names the set for the post-E3 campaign** (repaired `jca_android`, or an unfrozen
successor to `jca`). Everything here already appears in the audit's patch area (i); the plan adds
the *shape* of the message, nothing else:

| # | Item (plan) | Audit counterpart | Note |
|---|---|---|---|
| T1.1 | WS-7 items 1–5 (SIG return types; KPG NPE; PBE 1000/10000; `currentAlgorithmInstance` vs `alg`; wrong `ErrorType`) | §9 (i): "SIG sign return types; KPG NPE guard; …" | KPG NPE is also the E3 non-cancelling bias `FEN-KPG-NPE` |
| T1.2 | WS-2.4 (`next2` in `end`); **not** 2.5/2.6 | §9 (i): "SRD next2-repetition ORDER"; `FEN-SRD-NEXTBYTES-FP` | the 12,400-row stratum |
| T1.3 | WS-1.1 + revised 1.2/1.3 (4-arg constructor in the 21 `@fail`; message = event name from a hand array + spec variables + object class, composed **before** `__RESET`; no identity hash) | §9 (i): "diagnostic messages (specific `expecting` everywhere, stable dedupe keys)" | needs T0.3/T0.5 first |
| T1.4 | WS-1.4 ("expected one of") | — | needs the pre-fail state (generator `RVM_prevState` or per-event bookkeeping); decide after T0.1 |
| T1.5 | WS-3 (predicates) | §7 items 4, 6; §9 (i) "RANDOMIZED material-mark discipline; the extra-oracle clause family per the §7 researcher decisions" | blocked on the identity-store question reopened by `e204e2a4` and on D-4 |

Deferred entirely, with the reason: WS-4 (M+I, prototype); WS-5 (5.4/5.5 real but unmeasured and
belong with the weaver; 5.1/5.2/5.8/5.9 are cross-tool); WS-6.2/6.4 (need `INV-PLT-19` and gh103
deltas — decide after T0.1 shows what the analysis layer actually needs); WS-6.7 (D-6); WS-8
(D-7).

Revised sequencing: **T0.1 → T0.3/T0.4 → T0.2 → T0.5**, as one OpenSpec change on the Python/
collector side (or folded into gh103 where it already owns the contract). T1 opens only on the
researcher's §7 rulings and set decision, and then as part of the audit's repair patches
(§10.5), not as an independent change.

## 7. Proposed corrections to the plan (not applied)

1. Add a "Prior work" section citing gh100, gh101, the revert `e204e2a4`, the `jca_android`
   audit (`docs/20260808_validar_specs_jca_android.md`; `audit/20260808_validacao_jca_android/
   global/juizglobal_relatorio.md`) and the Study 03 decisions (`docs/20260810_plano_prontidao_
   estudo03.md` D1/D3/D4); state the `jca` freeze and the audit verdict; mark every WS-2/WS-3/WS-7
   item as closed-in-`jca_android` / open / audit-listed; state explicitly which campaign "next"
   means and therefore which tier (§6 T0/T1) is admissible.
2. §1: drop "73.4%"; either reproduce "28" with a published prefix list or replace it with the
   range; correct "largest identical group 3,098" (6 for the 10-column key).
3. §2.2: name the pairing definition; note `time` is seconds; note 113 vs 163.
4. §3-L2: replace the FSMMin citation with `JavaFSM.java:112-142`; rewrite the SSLContext row;
   reclassify the Cipher/KeyPair rows as CrySL-conformant; add fan-out/cloning; add the gh100
   census and the wrapper collision as the dataset's dominant twin mechanism.
5. §3-L3: replace `:604-610` with `RVDumpVisitor.java:47-51` + `EventDefinition.java:151-156`;
   note monitor creation precedes the test; correct the predicate matrix for `jca_android`.
6. §3-L7: add the escape-function bug and the `\n` fabrication path; `generic_new` 39 sites.
7. §3-L8: `TrustManagerFactorySpec.mop:63` (+`:62` double array); source the `.aj` lines
   correctly; note D07/D08 persist in `jca_android`; note the dexlib2 matcher compares return
   types.
8. §4: `getState()`/`getLastEvent()`; pre-fail state lost; compose before `__RESET`; atomic vs
   synchronized shape; "seven handlers read spec variables" not fields.
9. §5: WS-1 revised as in §3.1/§3.4 here; WS-2.1–2.3 marked done, 2.5/2.6 removed; WS-3.1 radius
   C acknowledged and Phase A sentence fixed; WS-4 radius M+I; WS-6.6 rewritten; WS-6.2/6.4 tied
   to `INV-PLT-19`/gh103; add the message-content rule and the synthetic-suite workstream.
10. §6: D-1 is already decided for Study 03 (`jca`) and depends on the audit's §7 rulings for the campaign after; D-2 already made (gh100 kept by D3); the identity store is reverted (D4).
11. §7: criteria 2, 5, 6 reworded as above.
12. §8: D02/D05/D06/D11/D34 reclassified; missing entries added.
13. §9: the four claims replaced by their resolutions.

---

## 8. Documents this review relies on

| Path | Role here |
|---|---|
| `rv-android/docs/20260815_javamop_mensagens.md` | the plan under review |
| `rv-android/docs/20260815_javamop_mensagens_analise_handoff_prompt.md` | the brief for this review |
| `rv-android/docs/SDD.md`, `docs/WORKFLOW.md`, `.claude/AGENTS.md` | process (SDD/OpenSpec) — the first sense of "spec" |
| `rv-android/openspec/changes/gh100-weaver-emission-fidelity/` (`proposal.md`, `design.md`, `tasks.md`, `evidence/census_pre_repair.json`, `evidence/l3_verdicts.md`, `evidence/green_deltas.md`) | weaver repairs; the nine truncated events; the wrapper collision; L3-b/L3-c |
| `rv-android/openspec/changes/gh101-jca-spec-conformance/` (`proposal.md`, `design.md`, `tasks.md`) and `rv-android/data/gh101/` (`frozen_set_debt.md`, `divergence_record.csv`, `predicate_*.csv`) | the `jca_android` rewrite; the `jca` freeze (D-S0); INV-INS-109/110/111/113 |
| `rv-android/docs/20260808_validar_specs_jca_android.md` | audit protocol |
| `rv-android/audit/20260808_validacao_jca_android/` — `global/juizglobal_relatorio.md` (§3 verdicts, §5 findings, §6 risks, §7 researcher decisions, §9 patch areas, §10 final decision), `fase0/estado_gh100_gh101.md`, `batchD/gama_report.md` (H-SRD-1), `HANDOFF_PROXIMA_SESSAO.md` | the NOT READY verdict and its evidence |
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` (§2 D1–D13), `docs/20260812_comp162.md`, `docs/20260812_registro_execucao_prontidao_e3.md` | Study 03 decisions: `jca`, weaver kept, `ExecutionContext` reverted |
| commits `e204e2a4` (revert), `f322c5da` (audit), `48b57fc5` (weaver merge), `233df18a`/`a0f43833`/`1217d6ff`/`2a36defa` (gh101), `7e7acb69` (freeze base) | provenance |
| `rv-android/openspec/changes/gh103-campaign-analysis-layer/` and `modules/aperv-tool/src/aperv_tool/analysis/violations.py` | the `errors.csv` / `unique_msg` contracts at risk |
| `rv-android/openspec/specs/{core,platform,analysis,instrumentation}/spec.md` | invariants cited (INV-CORE-25/41, INV-PLT-19/24-26, INV-ANA-08/46, INV-INS-109-115) |
| `ase-journal/dataset/results/errors.csv` (+ `dataset/results/README.md`) | the plan's evidence base, re-measured |
| `Crypto-API-Rules/JavaCryptographicArchitecture/src/*.crysl` | ground truth for the "false positive" claims |
| `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/` | the JavaMOP specifications — the second sense of "spec" |
| `rvsec/rvsec-core/.../mop/eh/*`, `.../mop/Property.java`, `.../mop/ExecutionContext.java`, `rvsec/rvsec-logger-csv`, `rvsec/rvsec-android/rvsec-logger-logcat` | reporting runtime |
| `rv-monitor/rv-monitor/.../output/monitor/*`, `.../logicpluginshells/fsm/JavaFSM.java`, `rv-monitor/plugins_logicrepository/{ere,fsm}/`, `rv-monitor/rv-monitor-rt/.../ViolationRecorder.java`, `javamop/src/main/java/javamop/{output/descriptor/DescriptorWriter.java,parser/ast/visitor/RVDumpVisitor.java,parser/ast/mopspec/EventDefinition.java}` | generator |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (`DexWeaver`, `RegisterShifter`, `PointcutMatcher`, `WrapperEmitter`, `CoverageWeaver`, `PackageFilter`, `InstrumentationCli`) | weaver |
| `rv-android/results/{gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control,gh92_e2e2,gh56-smoke}/monitors/` | generated oracles (`O99`, `O101`, `OFZ`, `MonitorWrappers.java`) |
| `rv-android/modules/rv-coverage/.../logcat_parser.py`, `rv-android-core/.../domain/log.py`, `rv-platform/.../result_processor.py`, `rv-experiment/.../__main__.py`, `config.py` | Python parser/writer/CLI |

