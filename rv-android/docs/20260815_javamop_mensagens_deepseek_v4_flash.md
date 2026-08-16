# Independent validation of the JavaMOP messages plan and of its adversarial review

**Reviewer model:** `deepseek_v4_flash` (opencode)
**Date:** 2026-08-15
**Mode:** read-only, source-verified. Nothing implemented; no `.mop`, `jca/`, `ase-journal`, SDD spec or OpenSpec artifact edited. All measurement scripts live in `/tmp/opencode/jmval/` (outside the source tree).

---

## 1. Executive summary

**Verdict on the plan (`20260815_javamop_mensagens.md`):** the **diagnostic root cause is right**, and the **two-pillar mechanism holds** (verified in source). But the plan is **not executable as written**: it describes a pipeline the current branch no longer is, its headline numbers are partly non-reproducible, and a meaningful share of its specification-level workstreams are either already closed, frozen, or contradict the CrySL ground truth. It needs the review's corrections folded in and a target set named before any `.mop` edit is admissible.

**Verdict on the review (`20260815_javamop_mensagens_analise.md`):** **largely correct and well-evidenced.** Its central claims — the stale pipeline, the no-admissible-spec-target conclusion, the wrapper-collision/truncation explanation of the dataset volume, the CrySL-conformant reclassification of Cipher/KeyPair, the `condition()`-as-prologue correction, the `getState()`/`getLastEvent()` portability advice, the T0/T1 cut — all reproduce when I re-open the source. It has a handful of minor, mostly-parenthetical imprecisions (a 15-vs-16 O99 atomic count; an attribution-cleaning claim I could not re-reproduce) and tends to understate how *available* `getLastEvent()`/`getState()` are (they are on the base `IMonitor` interface for **both** shapes, not only synchronized).

**Three things I knocked down:**
1. The plan's headline attribution number **85.44%** — does not reproduce under the plan's own stated vendor list (I get **78.49%** for that list, **82.67%** for plan-list+okio). The review's own version ("85.44% only with okio added") also did not reproduce for me. No attribution/funnel-final number has an admitted definition; it ranges **30–59** actionable findings depending on the cut.
2. The plan's "largest identical group **3,098**" — the 10-column-identical maximum is **6** (confirmed by independent recount).
3. The plan's framing of the SSLContext row ("no `UnsafeProtocol` is emitted") and of the Cipher/KeyPair "false positives" — the former is emitted from `init`'s body and fan-out; the latter are **CrySL-conformant** (Cipher.crysl:84-85 and KeyPair.crysl:19 forbid them), so WS-2.5/2.6 are not translation defects.

**Three things I confirmed:**
1. The plan's pillar: the FSM sink + total transition completion (`JavaFSM.java:112,133-137,140-142,158`) and verbatim `@fail` inlining (`HandlerMethod.java:81-108`) — both exactly as the plan states (modulo the FSMMin-vs-JavaFSM citation, which the review corrected).
2. The review's central thesis: `jca` is **frozen** (gh101 gate, base `7e7acb69`) and is the set Study 03 uses (D1), `jca_android` is **NOT READY** (22/22 REPROVADA), the weaver repair is kept (D3) and `ExecutionContext` is reverted (D4, `e204e2a4`) — so today the plan has **no admissible specification-level target**.
3. The dataset-volume mechanisms the plan *under*-attributes: gh100's `eventsDropped: 9` / `errorEmittersDropped: 8` census and the pre-repair wrapper collision (three `(String)` wrappers → `g3`-wins) that produces the 1:1 twins and the 8,371 empty values; and the `SecureRandomSpec` `next2`-missing-from-`end` FP matching the 12,400-row stratum.

**Recommendation:** adopt the review's **T0/T1** cut. Do T0 (re-baseline on E3's first batches; sentinel for fabricated fields; message-content rule; escape-function fix; dedupe-identity decision) as one toolchain/parser change, and defer all specification-level work (plan WS-1/2/3/7) until the researcher rules on the audit's §7 list and names the post-E3 set — at which point fold the survivors into the audit's patch area (i) with the audit's provenance discipline, not as a parallel plan.

---

## 2. Method

I performed the verification directly (no sub-agents were needed; the tool set here is short), as independent passes each re-opening the source, plus standalone measurement scripts. Everything was re-opened at the cited `file:line`; nothing was taken from either document's citation list unverified.

- **Measurements (V2):** `/tmp/opencode/jmval/v2_measure.py`, `v2b.py`, `v2c.py`, `v2d.py`, `v2e.py`, `v2f.py` — stdlib-Python recounts of `ase-journal/dataset/results/errors.csv` (97,018 rows) under explicit definitions.
- **Execution-based checks (V6):** `uv run pytest --import-mode=importlib -o "addopts="` on the logcat parser (`38 passed`) and the header-contract test (`1 passed`).
- **Source re-opens (V1/V3/V4/V5/V7):** the generator (`JavaFSM`, `FSMMin`, `HandlerMethod`, `BaseMonitor`), runtime (`IMonitor`, `AbstractSynchronizedMonitor`, the two `ErrorCollector`s, `ErrorDescription`, `ErrorSummary`, `Property`), the three generated oracles (`gh99_jca_android_monitors`, `gh101_group8_jca_android`, `gh101_group8_jca_frozen_control` → `O99`/`O101`/`OFZ`), `javamop` (`RVDumpVisitor`, `EventDefinition`), the dexlib2 weaver (`PointcutMatcher`, pre/post `MonitorWrappers`), the `.mop` sets, the CrySL rules, `logcat_parser.py`, `log.py`, `result_processor.py` and the OpenSpec invariants/change dirs, the audit, and the Study 03 plan; plus `git log --oneline` for the seven provenance commits.

---

## 3. Verdicts per dimension

Evidence classes: **P** = PROVEN (executed), **M** = measured (own script), **O** = OBSERVED_IN_ARTIFACT, **I** = INFERRED, **NV** = NOT_VERIFIED.

### V1 — Cross-factual verification of both documents

The plan's decisive citations that I re-opened, all CONFIRMED (O/P):
- `ErrorDescription.java:34-36` mute `"unknown"`; two ctors `:34-44` (O, read).
- `JavaFSM.java:112,133-137,140-142,158` sink + completion + `fail condition` (O, read).
- `HandlerMethod.java:81-108` verbatim inline (O).
- `O99` `SSLContextSpecMonitor` `Prop_1_transition_*[]` at `:7345-7349` exactly as cited (O); `@fail` fires per event `:16020-16023,2280-2283` (O); fail body `:7480-7487` = mute 3-arg + `this.reset()` (O).
- `ErrorSummary.hashCode/equals` on `(spec,error,class,method,location)` — message excluded (O). `ErrorDescriptionTest.java:179-220` pins it (O).
- logcat `ErrorCollector.java:38-40` unescaped line, `:39` commented escape, `:44-51` buggy escape; JSE `:41-42,83-91` escapes only `expecting` (O).
- `logcat_parser.py:305-316,366-368` fabrication; Format-2 `parts[6:]` rejoin `:348`; Format-3 `:361` `dot_idx` (O, and `38 passed` tests).
- `result_processor.py:562-576` 11-column writer incl. `source`; `test_errors_csv_header_carries_source_after_method` `test_result_processor.py:248-262`; `INV-PLT-19` `platform/spec.md:192` (O).
- The three never-matching pointcuts `SignatureSpec.mop:99,106`, `TrustManagerFactory` gtm1 (O); `PointcutMatcher.java:361-367` exact-return gate (O).
- `Property.java` enum = **25** values, incl. `GENERATED_CIPHER`, `MACED` (O) — the review's "25, never 24" **CONFIRMED**.
- `generic_new` has **39** `Log.v` sites (M), not the plan's 44; `@severity` in a javadoc block `CharSequence_NotInSet.mop:17` (O); the two `[helper]` specs span two lines each (O).

The plan's *wrong* citations that the review corrected, all CONFIRMED:
- The "sink completion in `fsm/FSMMin.java:24-28,53-55`" — **W**. `FSMMin` is a Hopcroft minimiser (javadoc `FSMMin.java:...` "Minimizes the Finite State Machine"); completion is `JavaFSM.java:112-142`.
- The "`BaseMonitor.java:604-610` condition suppresses the event" — **misattributed**. `RVM_conditionFail` appears **0** times in all three oracles; the real mechanism is `javamop/.../RVDumpVisitor.java:47-51` (`if ( ! ( cond ) ) { return false; }`), verified in `O99:3648...` and `O101:3816...`.
- The review's atomic/synchronized counts: O101 **18/23 atomic** exact; **but O99 is 15/23, not 16/23** (M). New refinement (see V3): `getState()/getLastEvent()` exist in **both** shapes (base `IMonitor`).

### V2 — Evidence base (CSV), independent recounts (M)

All my numbers (scripts above):

| Item | Plan | Review | **My measure** |
|---|---|---|---|
| rows / messages | 97,018 / 19 | same | **97,018 / 19** (exact) |
| `unknown` = 72.93%, `⇔` InvSeq | C | C | **70,760 = 72.93%**, 0/0 counter-examples both ways |
| per-type distinct | 1/12/3/1/2 | same | **identical** |
| shadow pairing | 26,152 / 44,608 | pairing 26,152; co-location 32,411 | **26,152 (36.96% of InvSeq; 26.96% of CSV)** and **32,411 (33.42% of CSV)**; robust to `time` (26,103) and `timeout` (26,152) |
| event granularity | 46,330/20,507 | same | **46,330 / 20,507** |
| TMF identical sites | 1,733/1,748 | same | **1,733/1,748** |
| funnel | 661/207/136/28 | 661/207/136/24-53 | **661/207/136** (exact); final stage **30** (2-seg own) / **42** (11-prefix) / **59** (plan 7-prefix) |
| attribution 85.44%/88.01% | C | 85.44% only w/ okio | **85.44% not reproducible**: plan-list=78.49%, +okio=82.67%; 88.01% reproduces only under a **2-segment** own-package key (full-package = 89.82%); zero-own apps **78/113 (69.0%)** |
| largest 10-col-identical group | 3,098 | **6** | **6** |
| okhttp3 Platform | 36.93% | — | **35,828 = 36.93%** |
| apps in errors.csv | (163 implied) | 113 | **113** |
| distinct classes | — | 117 | **117** |

Conclusions: the review's corrections to the plan's numbers (largest group 6; funnel final stage; attribution definition-dependence; 113 vs 163; shadow-definition ambiguity; `time`-in-seconds) are **all confirmed**. New precision: even the review's stated "85.44% only with okio added" does not reproduce (I get 82.67% for that), so **neither document pins a publishable attribution definition**; and the plan's own-stated 7-prefix list gives 78.49%, below even the round 80%.

### V3 — Generator and runtime semantics

- Sink + total completion + `fail condition`: **C** (O, `JavaFSM.java` as above).
- `@fail` fires after every event while in the sink; fires once only because the `jca` handlers call `__RESET` immediately; **`KeyPairGeneratorSpec.mop:110-113` has no `__RESET`** (O) → re-reports on later events (D41, and the review's volume note).
- Event body runs before the transition/category (so the informative record precedes the mute twin): mechanism **C** (O).
- `__RESET` → `this.reset()` → `RVM_lastevent=-1; Prop_1_state=0` and does not clear spec variables: **C** (O, `O99:7494-7501`); **message must be composed before `__RESET`** — review's order correction CONFIRMED.
- **`getState()`/`getLastEvent()` are on the base `IMonitor` interface** (`rv-monitor-rt/.../IMonitor.java:19,25`) and are generated for **both** shapes: synchronized exposes `RVM_lastevent` (field, `AbstractSynchronizedMonitor.java:5`) / `Prop_N_state`; atomic packs `((lastEvent+1)<<3)|state` in an `AtomicInteger` and provides the same two accessors (`O99:3296-3309,3441-3454`). **Refinement over the review**: the review says the atomic shape has "neither field" and to "use getState()/getLastEvent()" — correct, but these accessors are present in atomic monitors too (via the packed value), so WS-1 can use `getLastEvent()`/`getState()` *regardless* of shape. This modestly **strengthens** the plan's WS-1 feasibility; the review is not wrong, just understated.
- **The pre-fail state is lost at `@fail`** (state = the sink): **C** (O, `O99:7494-7501`, and the transition tables at `:7345-7349` give no pre-fail state). WS-1.4's "expected one of" is **not derivable** there without a generator change (`RVM_prevState`) or per-event bookkeeping — review CONFIRMED.
- `condition()` as a prologue: **C** (O, `RVDumpVisitor.java:47-51`, generated `if ( ! (...)) return false;`); the monitor is created/looked up before the test; `BaseMonitor.java:604-610` `RVM_conditionFail` branch dead (0 occurrences) — review CONFIRMED, plan's L3 citation corrected.
- No end-of-trace hook: `terminateInternal` all bare returns (`O99`), `_END`/`@end` absent; JavaMOP `endObject/endProgram` exist but are absent from dexlib2 (grep 0) — review CONFIRMED; WS-4 radius is M+I.
- Parameterless events fan out to all live monitors and new monitors clone the root (`BaseMonitor` `super.clone()`): mechanism **C** (O) — supports the review's SSLContext fan-out correction and the "contamination" it adds over the plan.
- No `int → String` state/event table emitted (names degrade to comments): **C** (O, `O99:8703-8712` etc.).
- `static final String[]` hand-declaration viability: **I/NV** — I did not re-generate a monitor to prove it; both documents's reasoning (declarations block passes through as raw user Java, emitted once) is plausible and mutually corroborated, and rvsec already relies on the same path for its spec fields. Mark **I** (not executed).

### V4 — CrySL ↔ `.mop` fidelity

Confronted the contested "false positives" against `Crypto-API-Rules/JavaCryptographicArchitecture/src/` (the JSE set, correct ground truth for the frozen `jca`):
- **Cipher `doFinal()`/re-`init`:** `Cipher.crysl:84-85` `Get, Init+, AADUpdate*, WKB+ | (FINWOU | (Update+, DoFinal))+` with `DoFinal := FINWOU | f1 | f3` — `doFinal()`(f1) is legal only after `Update+`, and no re-Init follows a final → **not an FP**. Review's D05 = W CONFIRMED.
- **KeyPair ctor-keyed protocol:** `KeyPair.crysl:19` `Con, (GetPubl | GetPriv)*` → the plan's D06 is **not a translation defect**; observability depends on whether `new KeyPair` runs inside the APK's DEX. Review's D06 = I CONFIRMED.
- **SecureRandom `next2`:** `SecureRandom.crysl` `ORDER Ins, (Seed?, End*)*`, `Next := nB|nI|nIR` — repeated `nextBytes` is legal; the `.mop`'s `next2`-parity restriction is **invented**, not CrySL. The `end [ ... ]` block (`SecureRandomSpec.mop:155-161`) omits `next2` (**C**), so `nextBytes;nextBytes` is a genuine FP matching the 12,400-row site profile (nextBytes wrappers). Both docs agree D03 is real; the review's linkage to the site stratum via the audit (H-SRD-1 / `batchD/gama_report.md:240-256`) is the better evidence than the plan's orphan/collision reading for that stratum.
- **RANDOMIZED argument-poisoning:** `SecureRandomSpec.mop:110-116` marks the argument `randIntInRange`, with the TODO at `:110` (`//TODO randIntInRange eh RANDOMIZED...`) — **C** (D12).
- **Predicate graph:** `CipherSpec.mop:72` reads `GENERATED_PRIVATE_KEY` that is never written (D14, **C**); `KeyPairSpec.mop:38` writes the private key under `GENERATED_PUBLIC_KEY` (D13, **C**).
- **Message/condition contradictions:** `MessageDigestSpec.mop:70,92` hard-code `{SHA-256, SHA-384, SHA-512}` vs the 6-entry list at `:16` (D38, **C**); `PBEKeySpecSpec.mop:48-50` `condition(<10000)` vs message `>= 1000` (D18, **C**).
- The authors' `MessageDigestSpec.mop:48-52` comment (they already patched one instance of the sink-FP): **C**, verbatim.

### V5 — Weaver and localisation

- **Wrapper collision (pre-gh100):** `gh92_e2e2/monitors/mop/MonitorWrappers.java:588-616` — three wrappers with the same `(String)` signature → `g1Event`, `g2Event`, `g3Event`; last-write-wins → `g3` only ever fired. **C** (O). Explains the 643 `found X509` (g3 wrote X509 on root, cloned by `init`) and the 8,371 `found .` (g1 discarded). Not okhttp-specific.
- **Truncation:** gh100 `census_pre_repair.json` `eventsDropped: 9`, `errorEmittersDropped: 8`, `errorTypesDropped {UnsatisfiedConstraint:7, UnsafeAlgorithm:1}` — **C**.
- **Return-type matching (D07–D09 on Android):** `PointcutMatcher.java:361-367` exact-return gate — **C**; `SignatureSpec.mop:99` `byte` vs actual `byte[]`, `:106` `byte` vs `int`, TMF gtm1 `KeyManager[]`/`TrustManager[][]` vs `TrustManager[]` — **C**.
- I did **not** re-open `RegisterShifter.cloneInstructions` (L5c) in this pass — the review's mechanism claim (empty `MutableMethodImplementation(int)` ctor drops `DebugItem`) is `file:line`-cited but I mark the debug-item-`=0`/caller-impact part **NV**; the review itself lowers this to "real, cheap, unmeasured", which I concur with.

### V6 — Python pipeline, contracts, consumers

- Parser three formats + fabrication + `\n` → fabricated second record: **C** (O); tests pass (P).
- Writer 11 columns; `source` added by `cf234788`; `error_type` never a column (lives in `unique_msg`): **C**.
- `unique_msg` 5-way `:::` at `log.py:112`, `RvErrorLog` 6 fields: **C**.
- Changing the `errors.csv` header (WS-6.2/6.4) breaks **`INV-PLT-19`** (`platform/spec.md:192`) and **`test_errors_csv_header_carries_source_after_method`** — **C** (O, P: test passes today). gh103 `violations.py` hard-contract would raise — I did not re-open gh103's file (NV). 
- Re-enabling the logcat escape as-is would quote the whole line (always contains commas) and is **not a re-enable**: **C**. The escape function is buggy (newlines survive inside quotes; `null` `expecting` NPE): **C**.

### V7 — Real state of prior work

- All seven provenance commits exist with the review's quoted messages: `e204e2a4` (revert), `f322c5da` (audit), `48b57fc5` (wrapper merge), `233df18a`/`1217d6ff`/`a0f43833`/`2a36defa` (gh101), `7e7acb69` (freeze base), `cf234788` (source) — **C** (git).
- gh101 freeze: `tests/parity/test_gh101_specset_gates.py:46` `BASE_COMMIT="7e7acb69"`, `:67 test_frozen_paths_byte_identical_to_base_commit` — **C** (O).
- Audit: `global/juizglobal_relatorio.md` §3.1 (22/22 REPROVADA), §10.1 (NOT READY), §10.5 (patch areas), §7 (10 researcher decisions) — **C** (read in full).
- Study 03: `docs/20260810_plano_prontidao_estudo03.md` §2 **D1 `jca`**, **D3 weaver repair kept**, **D4 ExecutionContext reverted** — **C** (read). `P5`/`P6` confirm the `next2` FP ↔ 12,400-row stratum and the E3 comparability break.
- Both documents represent this correctly; the plan simply **omits** it entirely (its §3/§5/§6 are written against the pre-gh100 2026-07-06 dataset and treat `jca`/`jca_android` as editable). The review's representation is complete and accurate.

### V8 — Design and proportionality

- **Phase A "without touching shared infrastructure" is false**: WS-3.1 (new `ErrorType`) is radius C (`ErrorType` lives in `rvsec-core`); WS-3.5 is S/C. Review CONFIRMED.
- **WS-1 cheap-but-revised**: `getLastEvent()`(event id) + spec variables + object are in scope; message must be composed before `__RESET`; the pre-fail state is not recoverable without generator change. Review CONFIRMED. The identity-hash recommendation (plan WS-1.2) should be dropped (volume/dedupe interaction) — review §3.1 CONFIRMED.
- **WS-2**: 2.1–2.3 are done in `jca_android` (gh101); 2.4 (`next2`) is open and CrySL-backed; **2.5/2.6 contradict CrySL** (V4). Review CONFIRMED.
- **Sequencing**: the review's insertion of a *re-baseline first* (measured on E3's first batches, pre-commit, using the already-correct `jca`+repaired weaver) is the single highest-value missing move — **C**.
- **T0/T1 cut**: correct. T0 (no `.mop` edit, toolchain/parser/collector) is admissible today and is what Study 03's post-processing can use; T1 hangs on the researcher's audit-§7 rulings and the set decision. I found nothing superfluous in T0; the one item that deserves more emphasis is the message-content rule (T0.3) as a hard gate in front of any richer message.
- Risk neither covers in depth: the **shape flip** (synchronized↔atomic) is a word-edits-driven property that rescopes what fields a `.mop`-authored message may reference — a hand-written WS-1 that compiles against a synchronized monitor today can silently break when an unrelated spec edit flips it to atomic. Using `getState()/getLastEvent()` only avoids this.

### V9 — Audit of the review itself

- The review is well-cited and I re-opened its decisive claims; no conclusion was found resting on an un-opened source. Its self-consistency is good.
- **Imprecision found:** (1) `16/23` atomic in O99 is actually **15/23** (M); (2) its attribution "85.44% only with okio added" does not reproduce for me (82.67%); (3) it understates that `getState()/getLastEvent()` are available in atomic monitors too (base `IMonitor`), not merely the portable fallback for the synchronized shape.
- **No confirmation bias found** in the loaded sense: the review attacks the plan's own numbers as hard as its conclusions; its corrections are independently grounded.

---

## 4. Corrections needed

### To the **plan** (`20260815_javamop_mensagens.md`)
1. Add a "Prior work" section citing gh100, gh101, the revert `e204e2a4`, the `jca_android` audit and Study 03 D1/D3/D4; state the `jca` freeze, the NOT READY verdict, and which campaign "next" means (→ tier T0/T1). (§0/§1/§5/§6)
2. Fix §1/§2.3/§2.4 numbers: drop or define "73.4%"/"85.44%"/"28"/"3,465×"; the 10-column-identical max is **6** not 3,098; state the pairing-vs-co-location definition and that `time` is seconds; 113 vs 163 apps.
3. §3-L2: replace the `FSMMin` citation with `JavaFSM.java:112-142`; rewrite the SSLContext row (UnsafeProtocol is emitted, via fan-out/clone); reclassify Cipher/KeyPair rows as CrySL-conformant; add fan-out + root-clone contamination; add the gh100 census and wrapper collision as the dataset's dominant twin mechanism.
4. §3-L3: replace `BaseMonitor.java:604-610` with `RVDumpVisitor.java:47-51` + `EventDefinition.java:151-156`; note monitor creation precedes the test; correct the predicate matrix (25 `Property`; `GENERATED_PRIVATE_KEY` read-never-written; `KeyPairSpec.mop:38` write-slot).
5. §3-L7: add the escape-function bug, the `null`-`expecting` NPE, and the `\n`-fabrication path; `generic_new` has **39** `Log.v` sites.
6. §3-L8: `TrustManagerFactorySpec` gtm1 is beyond `:62` and carries a `TrustManager[][]` binding; source the `.aj` numbers correctly; note D07/D08 persist in `jca_android`; note the dexlib2 return-type gate.
7. §4: use `getState()/getLastEvent()` (both shapes); drop `RVM_lastevent`/`Prop_N_state` as "fields"; compose before `__RESET`; "seven handlers read spec variables" not the state/lastevent fields.
8. §5: WS-1 revised (names, pre-fail state, `__RESET` order, no identity hash); WS-2.1–2.3 marked already done, 2.5/2.6 removed; WS-3.1 radius C acknowledged and the Phase-A sentence fixed; WS-4 radius M+I; WS-6.6 rewritten ("not a re-enable"); WS-6.2/6.4 tied to `INV-PLT-19`/gh103 and the header test.
9. §6: D-1 is already decided for Study 03 (`jca`); D-2 is already made (gh100 kept by D3); the identity store is reverted (D4).
10. §7: criteria 2, 5, 6 reworded (empty-value is gh100+gh101's delivery, not WS-1; two of the six "FP" targets are actually CrySL violations; "one message per mode" needs WS-6.1 or cross-process).
11. §8 register: D02/D05/D06/D11/D34 reclassified; add the missing entries (fan-out, truncation/collision provenance, escape bug, `null` NPE, duplicate `c1`, untracked `.aj`, KPG `@fail`-without-`__RESET` volume).

### To the **review** (`20260815_javamop_mensagens_analise.md`)
1. O99 atomic count **15/23** (not 16/23).
2. Attribution: either pin the exact prefix list that yields "85.44%" or drop the round claim — I could not reproduce 85.44%, and "with okio" gives 82.67%.
3. Refine §4: state that `getState()/getLastEvent()` are generated for the atomic shape too (packed pairValue), so they are not only the "synchronized" portable path.
4. Minor: mark the `static final String[]` feasibility as **I** (not executed) rather than fully resolved-viable, and `RegisterShifter` L5c as NV in my pass (its own "unmeasured" caveat already stands).

---

## 5. New anomalies / bugs not listed by either document

1. **Shape-flip fragility for hand-written WS-1.** `SSLContextSpecMonitor` is synchronized in O99 (`:7324`) and atomic in O101 (`:7639`); a message that names fields (`Prop_1_state`, or the spec's own instance fields vs pack) would break on such a flip. Neither document draws the *portability* consequence strongly (the review says "the shape flips with spec edits" but keeps the recommendation as "portable accessors" — correct; this is a reinforcement, and a must-test).
2. **Attribution definitions are not pinned by either document** — my 30/42/59 funnel-final and 78.49/82.67/88.01 attribution spread means any "actionable count" or "% in libraries" published without a named definition is not reproducible — impacting the plan's whole §2.4/D-3 framing.
3. **The `unsafe_protocol`-type parameterless fan-out is a live contamination channel** on the *frozen* `jca` set that Study 03 runs: `getInstance("TLS")` writes `currentProtocol` on **every** live `SSLContext` monitor (root clone inheritance), so one app's sequence can corrupt another object's message. The review lists this; the plan does not; and it is active in the set E3 actually uses.

Provenance classes (audit convention): [jca] shape flip + fan-out (both in the frozen set Study 03 uses); [tool] attribution-definition, escape/`null` bugs; [oracle] none new.

---

## 6. Evolutionary / gradual plan with validation gates

Re-use the review's T0/T1 but state the gates crisply:

- **Rung 0 — Measure before touching (no code).** Gate: on E3's first batches (already `jca` + repaired weaver + reverted store), recount `unknown` share, InvSeq/value pairing and rows-per-site with the same scripts as V2 here (in `/tmp/opencode/jmval/`). Exit: a post-repair baseline, so the value of WS-1..3 is measured, not guessed.
- **Rung 1 — Message-content rule + collectors (no `.mop` edit).** Add a `rvsec-mop` test asserting message shape (no `\n`, no `:::`, last field) and a parser-side counter (not fabrication) for continuation lines; fix `escapeSpecialCharacters` (both collectors) and the `null`-`expecting` NPE **without** re-enabling the whole-line call. Gate: `uv run pytest --import-mode=importlib -o "addopts="` green; a golden-parse test unchanged.
- **Rung 2 — Sentinel + schema decision.** Emit an explicit sentinel for fabricated `error_type`/`source` in parser Formats 1/3; decide dedupe identity as the audit frames it (structured event/clause id preferred over free text; co-schedule the `ErrorSummary`/`ErrorDescriptionTest:179-220` delta and `INV-PLT-19`/gh103 deltas). Gate: header-contract test updated deliberately; gh103 `read_errors_csv` updated; no silent drop (INV-CAN-04).
- **Rung 3 — Spec tier only after §7 rulings + set decision.** Fold surviving WS-1/WS-7 into the audit's patch area (i) with provenance classes and regressive examples; set = repaired-`jca_android` or a successor, per the researcher. Gate: each spec's patch tied to a researcher ruling (audit §7) and to INV-INS-110 (no bound event with an all-`fail` row).
- **Rung 4 — Predicates.** Re-open `ExecutionContext` identity-vs-equality (the revert `e204e2a4` half-broke `jca_android`'s `generatedCipher` edge) before any `REQUIRES` work; fix the RANDOMIZED source + the `GENERATED_PRIVATE_KEY`/`GENERATED_PUBLIC_KEY` slot. Gate: predicate graph read-set annotation.
- **Rung 5 — Generator/runtime, only if measured.** `getState()`/`getLastEvent()` message composition is the safe path; `RVM_prevState`/event-name table in the generator (radius M) **only** if the T0.1 measurement shows the pre-fail state is worth the shared-infrastructure cost; debug-info preservation + regression test in the weaver (cheap, independent) stays.
- **Rung 6 — full correction + readiness.** Declare a set "ready" only via the audit's READY conjunction (`fase0/pre_registro.md` §7), not a new criterion.

**Formal validation** (mandated for every spec-touching rung): (a) language-equivalence/inclusion between the generated/minimised `.mop` automaton and the CrySL `ORDER` translated to an automaton; (b) `INV-INS-110` check (no bound event with an all-`fail` row); (c) minimal separating traces as executable counterexamples (the JVM-harness pattern the audit used, e.g. the `new SecureRandom(); nextBytes; nextBytes` two-FP trace); (d) a `condition()`-as-prologue vs pointcut audit per spec so WS-3.2 never creates a fresh orphan; (e) model/bounded-checking of the automaton × predicate product for the `REQUIRES`/`ENSURES` edges; (f) **message-level properties**: every violation names event+state, no message collides with a different meaning, and injectivity of message wrt failure mode; (g) a CogniCrypt-derived oracle over the same micro-APKs.

---

## 7. Brainstorming — ideas with cost / radius / risk

(Each grounded in something I opened.)

1. **Structured key=value/JSON message with the parser treating `message` as opaque** — cheaper than it sounds now that `ErrorType`, and (with a generator tweak) event-id, are first-class; cost S(21 .mop) or M; the current parser already treats `message` positionally, so a self-describing body removes the `\n`/`:::` fragility only if the body avoids both. Opened: `ErrorCollector.java:38-40`, `logcat_parser.py:319-349`.
2. **Emit event/state names from the generator (`HandlerMethod`/`BaseMonitor`) as `String[] eventNames` + a `RVM_prevState`**, instead of hand-written tables — radius M, one-time, benefits all sets, avoids the shape-flip fragility; the review measured `CipherSpec`'s alphabet re-budget yielding 53s/3.3GB→6s/1GB, so event-count is not free. Opened: `HandlerMethod.toString`, `BaseMonitor.java:106`, transition arrays.
3. **Trace-prefix recording (last N events per monitor) at `@fail`** — gives the *why* even when the pre-fail state is lost; cost M (a ring buffer in the generated monitor) but touches all consumers; prototype on one spec first. Depends on Rung 5. Opened: the sink + `getLastEvent()` schema.
4. **Static weave-site manifest + offline join with the dynamic frame** — the weaver already holds classDef/method/idx/`DebugItem` (L5e); a per-site manifest avoids the one-frame stack walk and the `new Exception()` per report; radius M+I; the precedent is `ThisJoinPointEmitter.java:9-12`. Opened: `DexWeaver`, `ViolationRecorder.getLineOfCode` (`:53-60`).
5. **CogniCrypt error categories as `ErrorType`** (`TypestateError`, `RequiredPredicateError`, `IncompleteOperationError`, `ConstraintError`) with CrySL remediation text — maps directly onto the five missing "answers" (Q1–Q5); radius C(for the enum) + the `.mop` call sites; would finally make the 72.93% mute bucket legible. Opened: `CryptoAnalysis/.../errors/*`, `ErrorType.java`.
6. **Escape/`null` hardening + a device-side aggregate counter of dropped/suppressed records** — turns the silent `HashSet`/activity-restart loss into a countable statistic; radius C; addresses both D28 and the missing "suppression logged" acceptance criterion. Opened: both `ErrorCollector`s.
7. **`--internalbehavior`-style diagnostics for calibration** — RV-Monitor already has it; a diagnostic mode would let one verify the message content at monitor level before any campaign cost. Opened: `BaseMonitor.java:1057-1061` (the only `int→String` emission, off by default).

**New anomalies to hunt next (each with the evidence I have):** (i) quantify the fan-out contamination *within* the frozen `jca` set on E3 micro-APKs (measurement, no code); (ii) confirm/refute the `RegisterShifter` debug-item claim directly (NV here) before WS-5.4 is scheduled; (iii) check gh103 `violations.py` against a WS-6.2 header change explicitly (I marked it NV).

---

## 8. Risks and threats to the validity of this review

- **Single-party verification.** I attempted independent recounts and re-opens but did not run the JavaMOP/RV-Monitor generator nor a Maven build; anything about *generation-time* behaviour (the `static final String[]` survival) is **I**, and the L5c debug-item mechanism is **NV**. Both are already flagged by the documents as open/uncertain.
- **No emulator/device, by design.** G6/G10 of the audit remain INCONCLUSIVE here too; all dynamic claims are JVM/oracle-level, not ART.
- **`getLastEvent()`-at-`@fail` semantic depth.** I confirmed the accessor exists and `reset()` clears it, but did not execute a monitor to observe the offending-event id at `@fail`; the "last event is the offending event" claim is **I**, though strongly implied by the dispatch order (event → transition → category → handler).
- **The definition-space of the funnel/attribution** is wide; my 30/42/59 and 78.49/82.67 are reproducible but their *exact* values are definition-sensitive — I report them as ranges, not absolutes.
- **NOT_VERIFIED in this pass:** gh103 `aperv-tool/analysis/violations.py` internals; `RegisterShifter.cloneInstructions` (L5c); actual monitor generation; `Session` dedupe counters on-device.

---

## 9. Documents and artifacts used

- Documents under review: `rv-android/docs/20260815_javamop_mensagens.md`; `.../20260815_javamop_mensagens_analise.md`; `.../20260815_javamop_mensagens_analise_handoff_prompt.md`; `.../20260815_javamop_mensagens_validacao_prompt.md`.
- Audit: `rv-android/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md`; `docs/20260808_validar_specs_jca_android.md`.
- Study 03: `rv-android/docs/20260810_plano_prontidao_estudo03.md` (§2 D1/D3/D4, §7 P3/P5/P6).
- Generator/runtime: `rv-monitor/.../JavaFSM.java`, `.../plugins_logicrepository/{ere,fsm}/FSMMin.java`, `output/monitor/{HandlerMethod,BaseMonitor}.java`, `rv-monitor-rt/.../tablebase/{IMonitor,AbstractSynchronizedMonitor}.java`, `ViolationRecorder.java`(NV), `javamop/.../{RVDumpVisitor,EventDefinition}.java`.
- `rvsec-core`: `mop/eh/{ErrorDescription,ErrorSummary,ErrorType}.java`, `mop/Property.java`, `ErrorDescriptionTest.java`.
- Collectors: `rvsec-logger-logcat/.../ErrorCollector.java`, `rvsec-logger-csv/.../ErrorCollector.java`.
- Weaver: `rvsec-instrumentation-dexlib2/.../{PointcutMatcher,DexWeaver}.java`; oracles `rv-android/results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java` (O99), `gh101_group8_jca_android/...` (O101), `gh101_group8_jca_frozen_control/...` (OFZ), `gh92_e2e2/monitors/mop/MonitorWrappers.java`.
- Specs: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/*.mop`.
- CrySL: `Crypto-API-Rules/JavaCryptographicArchitecture/src/{Cipher,KeyPair,SecureRandom,MessageDigest,...}.crysl`.
- Python: `modules/rv-coverage/.../logcat_parser.py`, `modules/rv-android-core/.../log.py`, `modules/rv-platform/.../result_processor.py`, and their tests.
- OpenSpec/invariants: `openspec/specs/platform/spec.md` (INV-PLT-19), `openspec/changes/gh100-weaver-emission-fidelity/` (census, tasks), `openspec/changes/gh101-jca-spec-conformance/`, `tests/parity/test_gh101_specset_gates.py`.
- Data: `ase-journal/dataset/results/errors.csv` (+ README); scripts `/tmp/opencode/jmval/*.py`.
