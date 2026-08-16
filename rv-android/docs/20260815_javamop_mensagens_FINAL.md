# Legible JavaMOP Violation Reports — FINAL design document (Phase-0 input)

**Date:** 2026-08-15
**Status:** design / ideation output. **Nothing implemented.** This document is the input to the
OpenSpec workflow (`docs/WORKFLOW.md` §1 Phase 0 → §2 issue creation → §3 track selection):
each change proposed in §8 becomes one GitHub issue and one `openspec/changes/gh<N>-<name>/`
directory, created **only** through the OpenSpec skills.
**Supersedes for planning purposes:** `docs/20260815_javamop_mensagens.md` (the plan) — the plan
stays as the root-cause record; this document is what gets implemented.

**Lineage (read these; this document does not repeat them):**

| Path | Role |
|---|---|
| `docs/20260815_javamop_mensagens.md` | the plan (root cause L1–L8, WS-1..8, D-1..8, D01–D50) |
| `docs/20260815_javamop_mensagens_analise_handoff_prompt.md` | brief for the adversarial review |
| `docs/20260815_javamop_mensagens_analise.md` | adversarial review of the plan (§0 verdict, §6 T0/T1 cut, §8 sources) |
| `docs/20260815_javamop_mensagens_validacao_prompt.md` | brief given to four external LLMs |
| `docs/20260815_javamop_mensagens_claude_fable5.md` | external validation 1 (751 lines) |
| `docs/20260815_javamop_mensagens_deepseek_v4_flash.md` | external validation 2 (237 lines) |
| `docs/20260815_javamop_mensagens_gemini36flash.md` | external validation 3 (286 lines) |
| `docs/20260815_javamop_mensagens_gpt5_codex.md` | external validation 4 (480 lines) |

**How the four external validations were used.** They were not read as a whole by the author of
this document; each was reduced by an independent extraction pass to a list of candidate
corrections, anomalies and proposals (§4 reproduces those lists **without filtering**, with each
report's own evidence class). Every candidate that changed a decision was then re-verified in
source before entering §5–§9; §4 marks, per item, whether it was verified here (`V+`
confirmed / `V−` refuted / `V±` partial), was already verified in the review (`R`), or remains
unverified (`U`). **The consolidation should be redone against the four originals** by whoever
takes this to an issue: §4 gives the map from each original item to its status and to the section
of this document where it lands.

**Terminology.** "SDD/OpenSpec spec" = process artifact (`openspec/specs/**`, `INV-*`).
"JavaMOP specification" / `.mop` = runtime-verification artifact (Monitoring-Oriented Programming,
Chen & Roşu; JavaMOP → RV-Monitor → dexlib2 weaver). Both are used here; the object of the work is
the second, the process is the first.

---

## 1. Problem statement (one paragraph, for the issue)

RVSEC's violation reports are unreadable: in the reference dataset 72.93 % of the 97,018 records
carry the literal `unknown` (all and only `InvalidSequenceOfMethodCalls`), only 19 distinct
messages exist, and the post-repair Study 03 trial (`experimento-comp162`, 19,664 rows, `jca` +
gh100 weaver) is *worse*, 79.9 % `unknown` (15,714 rows). The message is a literal in
`ErrorDescription.java:34-36`; the volume comes from three mechanisms that must be treated
separately — specification automata that send legitimate or already-reported events into the FSM
sink, weaver defects (pre-gh100 wrapper collision/truncation; **post-gh100 `args()` arity ignored
in merged wrappers**, §5.1), and a reporting layer that drops the message from identity, fabricates
fields, and cannot carry structure. The goal is that the **next campaign after Study 03** produces
reports that name the specification, the offending event, the state/clause, the observed value and
the origin, with counts whose meaning is documented — and that every specification edit is
validated formally against its CrySL rule.

---

## 2. What is established (verified; the plan's evidence, corrected)

Verified in source by the review and re-verified by ≥2 external validations unless marked.

| # | Fact | Where |
|---|---|---|
| F1 | `@fail` is a state test on an implicit sink appended by `JavaFSM.java:112-142`; `fail condition = $state$ == countState` (`:158`); FSMMin only minimises. Every `(state,event)` not written goes to the sink; the sink is a trap; the handler re-fires on every event while there unless `__RESET`. | review §1-L2; ext. 1–4 |
| F2 | The `@fail` body is inlined verbatim into an instance method (`HandlerMethod.java:34-35,81-90,106`); substitutions: `__RESET`, `__DEFAULT_MESSAGE`, `__LOC`, `__SKIP`, `__ACTIVITY`. Declarations (incl. `static`) are emitted as text (`RVParser.jj:253`; javamop `javamop.jj:1276,1611-1623`, `DumpVisitor.java:814-826`). | review §2 [inferred] #2 |
| F3 | `Prop_N_state`/`RVM_lastevent` exist only in the *synchronized* shape; 15/23 (O99) – 18/23 (O101) monitors are *atomic*. Portable: `getState()`/`getLastEvent()` (`IMonitor.java:19,25`). **Atomic `getLastEvent()` returns `id+1`** (`calculatePairValue = ((lastEvent+1) << bits) \| state`, extractor is a bare shift — upstream off-by-one; `terminateInternal` likewise). At `@fail` `getState()` is the sink; pre-fail state is not stored; `__RESET` sets lastevent to −1/0. | review §1-§4; §5.2 here |
| F4 | `condition()` is stripped from the pointcut by JavaMOP (`javamop/.../mopspec/EventDefinition.java:150-156`) and inlined as `if(!(cond)) return false;` at the top of the monitor event method (`RVDumpVisitor.java:47-51`); the monitor is created/looked up first; callers ignore the boolean; rv-monitor's own `RVM_conditionFail` (`BaseMonitor.java:603-610`, `rvmspec/EventDefinition.java:30`) is dead (0 in oracles). Both statements are true — different classes. | review; ext. 1,2,4 (ext. 4 B1 resolved) |
| F5 | Parameterless events (`unsafe_protocol` no `returning`; `g3` binding `k`) go to the root slice, are dispatched to all live monitors, and new monitors are **clones of the root** (`BaseMonitor.java:760-769`), inheriting spec variables; the fan-out `__RESET` resets every live monitor. | review §1-L2; ext. 1,2,3 |
| F6 | `ErrorSummary` identity = `(spec,error,class,method,location incl. line)`; message excluded; pinned by `ErrorDescriptionTest.java:179-220`. Collector `HashSet` per process, unsynchronised, serialised only by the monitor's global lock; `new Exception()` per report attempt (`ViolationRecorder.java:37-39`). | review §1-L6/L7 |
| F7 | Logcat line = 7 comma fields, unescaped; escape function buggy (`\R` replacement discarded when a comma is present; commented call would quote the whole line); `null` `expecting` NPEs. JSE collector escapes only `expecting`. Parser Format 2 rejoins `parts[6:]`; `\n` → a **second fabricated record**; Formats 1/3 fabricate `error_type := spec`, `source := "Unknown Source:1"`; no drop counter. | review §1-L7; ext. 1–4 |
| F8 | `errors.csv` writer = 11 columns incl. `source` (`result_processor.py:562-576`); `error_type` only inside `unique_msg` (5-way `:::`); no Python-side dedup; `unique_msg` built in four places (`log.py:112`, `result_processor.py:631,999,1038`). Contracts: `INV-PLT-19`, `INV-CORE-25/41`, `INV-ANA-08/46`; gh103 `violations.py` raises on any header change and extracts `violation_type = parts[3]`. | review §5; ext. 1 |
| F9 | Dataset numbers: 72.93 %/19 messages exact; "shadow 27 %" is a min-pairing count (co-location gives 33.4 %); "73.4 %", "28 findings/3,465×", "3,098 largest group" not reproducible (largest 10-column group = 6; 113 apps with errors of 163; `time` is seconds). | review §1-§2; ext. 1–4 |
| F10 | Prior work the plan ignored: gh100 (weaver merge `48b57fc5`, nine truncated events restored), gh101 (`jca_android` rewritten; **`jca` frozen** at `7e7acb69`, `INV-INS-109 a`), the audit (`jca_android` NOT READY 22/22), Study 03 decisions (`jca`; weaver kept; `ExecutionContext` identity store **reverted** in `e204e2a4`; gh101 open, revert unrecorded in `data/gh101/README.md`). | review §0; ext. 1–4 |
| F11 | Pre-gh100 wrapper collision (last write wins) explains the TMF 1:1 twins, 8,371 `found .`, 643 `found X509` (`gh92_e2e2/monitors/mop/MonitorWrappers.java:588-616`); the SecureRandom 12,400 are better explained by the `next2` FP (audit H-SRD-1; site profile at `nextBytes`), attribution INFERRED pending replay. | review §1-L2/§4; ext. 1,4 (both keep INFERRED) |
| F12 | Never-matching pointcuts are real on Android (dexlib2 matches return descriptors exactly, `PointcutMatcher.java:361-364`): `SignatureSpec` `sign()` (both sets), `TrustManagerFactorySpec.mop:62-63` (jca), **`SSLContextSpec` `createSSLEngine` declared `void` (both sets)**. | review; §5.3 here |
| F13 | CrySL vs translation, decided against both oracles (original 1.5.2 and MetaCrySL api30): translation defects — `SecureRandom.end` lacks `next2`; **`CipherSpec` s3 has no `update` self-loop and s2/s3 no re-`init` (`Update+`, `Init+`) — both sets**; `PBEKeySpecSpec` demands `RANDOMIZED(password)` where the rule requires it on `salt` only; oracle choices — `KeyPair` ctor (`Con` in 1.5.2, `co?` in api30), `AndroidKeyStore`/BKS, MD5/SHA-1, SSL/TLSv1, PBEWithHmac catalogue; CrySL strictness — bare `doFinal()`/`doFinal(out,off)` without `update`. | §5.3 here |
| F14 | Generator hooks: event id = declaration order (`RVMonitorSpec.java:143-147`); no int→String tables (only `--internalbehavior`); `__DEFAULT_MESSAGE` = spec + line + URL only; `fsm:` per-state `default -> S` transitions are supported (`FSMParser.jj:93,149`, `JavaFSM.java:113-120`) and unused; undeclared ERE symbols vanish silently (`GCMParameterSpecSpec` `c2`); handlers see **no spec parameters**, only fields (`stripUnusedParameterInMonitor`), fields may be null; an exception in a handler escapes with the global lock held (no `finally`); no end-of-trace hook (`endObject`/`endProgram` absent from dexlib2). | §5.2 here |

---

## 3. Constraints and non-goals

- `jca` is frozen (gh101 D-S0; gate `tests/parity/test_gh101_specset_gates.py`); Study 03 runs on it
  (`docs/20260810_plano_prontidao_estudo03.md` D1/D3/D4). **No `.mop` edit lands in `jca`.**
- `jca_android` is REPROVADA (`audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md`
  §10) and shelved for Study 03. Any specification-level work needs the researcher's rulings on the
  audit's §7 list and a named target set (§6 D-A). The message work must not become a second repair
  programme beside the audit's §9 list; it is folded into it (lane C).
- No emulator is managed by hand; device validation only via `rv-experiment run` / `rv-platform run`.
- Monitor generation is not parallelisable; scratch directory; `TMPDIR` off tmpfs.
- The article (`ase-journal`) is evidence, not a target. No retroactive re-analysis.
- Non-goals: end-of-trace (`IncompleteOperationError`) detection (WS-4) and localisation frames
  (WS-5.1/5.2/5.8) are **not** in the staged plan; they are recorded as later options (§9 O-7/O-8).

---

## 4. Consolidated candidate table (unfiltered)

Every item extracted from the four external validations, keyed by report and the report's own ID
(`c` = claude_fable5, `d` = deepseek_v4_flash, `g` = gemini36flash, `x` = gpt5_codex; IDs are the
ones used inside each report's extraction: A = corrections to the plan, B = corrections to the
review, C = new anomalies, D = proposals). Status: `R` already verified in the review;
`V+`/`V−`/`V±` verified here (§5); `U` not verified; `—` not a factual claim (design/process).
"→" = where it lands in this document. Items agreeing with the review are kept, not dropped.

### 4.1 Corrections to the plan (A) and to the review (B)

| Item(s) | Claim (compressed) | Status | → |
|---|---|---|---|
| c-A1, d-A6, g-A11, x-A6 | FSMMin does not complete; sink completion in `JavaFSM.java:112-142,158` | R | F1 |
| c-A2, d-A10, g-A10, x-A7; x-B1 | `condition()` = prologue in monitor method; `BaseMonitor:604-610` dead; javamop `EventDefinition:150-156` does assign it (both true) | V+ | F4 |
| c-A3, c-A4, d-A14, d-A15, g-A6, g-A7, x-A8, x-A9, x-A10; d-B3 | fields only in synchronized shape; use accessors (present in both shapes); pre-fail state lost; compose before `__RESET` | V+ (+ off-by-one) | F3, §7.2 |
| c-A5, d-A1, g-A1, g-A2, g-A14, x-A1, x-A2, x-A16 | plan stale: gh100/gh101/audit/E3/revert; no admissible target set; name the campaign | R | F10, §6 |
| c-A6..A15, d-A2..A5, g-A5, g-A8, x-A3..A5, x-A26; g-B1, d-B2, c-B13, x-B2 | numbers: 73.4 %/28/3,098/163 not reproducible; shadow definitions; `okio.` needed for 85.44 %; funnel 24–59 by definition; scripts not durable | R (definitions differ per report — treat as "publish the classifier") | F9, §6 D-F |
| c-A16 | E3 breaks `unknown ⇔ InvSeq`: 419 `UnsatisfiedConstraint` rows are `unknown` (`jca/IvParameterSpec.mop:48,55` 3-arg ctor) | U (count) / R (sites) | §7.2 |
| c-A17, d-A7, g-A15, x-A14 | SSLContext row wrong; fan-out + root clone; contamination | R | F5 |
| c-A18, c-A19, c-A20, d-A8, g-A12, g-A13, x-A11..A13 | Cipher/KeyPair rows are CrySL semantics; KeyPair `co?` in api30; AndroidKeyStore is an oracle choice | V+ | F13, §6 D-B |
| c-A21, c-A22, x-A27; c-B13, d-B5 | L5c "highest-value" not established (n=1 census: 3.9 % methods, 0/693 woven; E3 100 % lines); `is_library` offline | V± (E3 lines U here) | §9 O-8 |
| c-A23, c-A24, d-A12, d-A20, g-C5, x-A22; x-B11 | escape bug; whole-line quoting; `null` NPE; JSE collector not canonical either | R | F7, C-1 |
| c-A25, c-A26, c-A27, c-A28, c-A29, d-A11, d-A13; c-B5, d-B1, c-B6, c-B7, c-B8, c-B11, c-B16 | small drift: `generic_new` 39; `Property` 25; 50 live sites; TMF `:63`+`:62`; `.aj` git-ignored; O99 atomic 15/23; clone at `O99:15992`; `coverage.py` path; `SecureRandom.crysl:39`; missing files in review §8 | R / V+ (15/23) | §10 errata |
| c-A30, d-A18, g-A9, x-A16 | Phase A touches `rvsec-core` (WS-3.1) | R | §8 C-2 |
| c-A31, d-A17, x-A17 | WS-2.1–2.3 done in `jca_android`; verify INV-INS-110; `default` transition alternative | V+ (default supported) | §7.4, §9 O-3 |
| c-A32 | WS-6.2/6.3 partly moot: gh103 already extracts `violation_type = parts[3]` and reads `source` | U (not re-opened here) | §7.3 |
| c-A33, x-A23 | `RVM_loc` never assigned; cross-tool | R | §9 O-8 |
| c-A34, x-A25 | event names by hand (declaration order) + generation-time length check; never state names | V+ | §7.2 |
| c-A35, d-B4 | `static final String[]` viability INFERRED (not regenerated) | R (grammar) / U (oracle) | §7.2 gate G-1 |
| c-A36, d-A22, x-A16 | D-1 decided for Study 03; D-2 made; identity store reverted | R | §6 |
| c-A37, d-A23, x-A21; c-B9 | acceptance criteria 2/5/6 reworded; 98 residual `found .` on E3 (MessageDigest 55, Signature 39, Mac 4) | V+ (E3 numbers) | §7.6 |
| c-A38, d-A24 | register reclassification D02/D05/D06/D11/D34; add fan-out, truncation, collision, escape, NPE, duplicate `c1`, KPG `@fail` without `__RESET` | R | §10 |
| c-A39 | `@fail` re-fires while in sink; KPG no `__RESET` → re-reports | R / V+ | F1 |
| c-A40, x-A16 | `jca_android` graph reconnected but `generatedCipher` broken by revert | R | F10 |
| c-A41, x-D3 | E3 re-baseline is step 0, computable now (E3 ran 2026-08-13) | V+ (comp162 results exist, 19,664 rows) | §8 C-0 |
| c-A42 | D-4 prerequisite: DH has a producer (`DHGenParameterSpecSpec.mop:36`), no PREPARED_EC/RSA/DSA | U | §9 O-5 |
| c-A43, d-A9, g-A4, x-A14 | TMF empty values = wrapper collision (artifact) | R | F11 |
| c-B1, c-C19 | gh101 does not record the revert (`data/gh101/README.md:255-300`) | U (not re-opened) | §8 C-0 task |
| **c-B2, c-C1** | **post-merge wrapper fires g1+g2 (+g3) on 1-arg `getInstance`; `args(alg,*)` arity ignored; TMF/KMF/SR post-instantiation state lacks g2 → mute records on every correct flow (E3: TMF 2,855, KMF 296)** | **V+ (three mutes per flow; dexlib2 only)** | **§5.1, §8 C-1** |
| c-B3 | `jca` CipherSpec not faithful on `Init+`/`Update+` | V+ | F13, §5.3 |
| c-B4 | review never opened api30 | V+ (opened here) | F13 |
| c-B10, x-B10 | E3 already ran; T0.1 offline now; ladder B0/T0/T1/T2 | V+ | §8 |
| c-B12, x-B4 | SRD 12,400: keep INFERRED (three candidate mechanisms) | R (kept INFERRED) | F11 |
| c-B14 | all 11 `getInstance(String)` specs collide pre-fix (SR three wrappers) | V+ (SR key owned by g4 pre-fix) | F11 |
| c-B15, x-B10 | third target-set option (successor of `jca`); T0.3 split; T0.4 bundle; `.mop` content-test home (`rvsec-mop` has no `src/test`) | — (design) | §6 D-A, §8 C-1/C-3 |
| c-B17, x-B2, x-B9 | review bias notes: numbers without durable scripts; causal claims graded unevenly | — (accepted: scripts become part of C-0) | §8 C-0 |
| c-B18 | closable items: D44 confirmed (50 `getLineOfCode`, 0 `record`); `MonitorBuilder` no `-g` | U (not re-opened) | §10 |
| c-B19, c-B20, c-B21 | `Platform.kt:83` provenance NV; `.aj` "git-ignored"; fan-out `__RESET` resets state | R / U | — |
| x-B3, x-B5, x-B6, x-B7, x-B8 | wrapper merge as *sole* cause too broad; V0/V2 prove DEX emission not logcat; "84/84" ≠ accepted; header contract changeable via delta; versioned transport before new columns | — (accepted) | §7.3 |
| g-B2, g-B3, g-B4 | FSMMin `null` default handling; "misclassifies CrySL items" (unspecified); T0/T1 correct | R / U | — |
| d-B6, d-B7 | attribution "cleaning" not reproducible; no confirmation bias found | — | — |

### 4.2 New anomalies claimed (C)

| Item(s) | Anomaly | Status | → |
|---|---|---|---|
| **c-C1** | merged wrapper + inert binding-form `args()` → g1+g2 both fire; TMF/KMF/SR mute on correct flows | **V+** | §5.1, C-1 |
| **c-C2, x-C13-adjacent** | CipherSpec s3 no `update` self-loop; s2/s3 no re-`init` (both sets) — streaming/multi-chunk = FP | **V+** | §5.3, C-4 |
| **c-C3** | `SSLContextSpec` `createSSLEngine` declared `void` (both sets) — dead Engine channel | **V+** | §5.3, C-4 |
| **c-C4** | `PBEKeySpecSpec` requires `RANDOMIZED(password)`; rule requires `salt` only — every typed password accused | **V+** | §5.3, C-4 |
| c-C5, c-C6 | api30 `KeyPair co?`; `KeyStore` list = oracle choice | V+ | F13, §6 D-B |
| c-C7 | user state named `fail` shadowed by `JavaFSM:158` | R (review §1-L2) | F1 |
| c-C8 | `fsm:` per-state `default` transitions supported, unused | V+ | §9 O-3 |
| c-C9 | entry point ignores boolean; stale flags; atomic double dispatch after CAS | V± (stale flags yes; concurrent double dispatch **refuted** under global lock) | F14 |
| c-C10, d-C3 | fan-out `__RESET` resets all live SSLContext monitors | R | F5 |
| c-C11 | `Ref_<param>` may be null in `@fail` | V− as stated (that path is dead); real hazard: fields null; **`jca_android/KeyPairSpec.mop:19-21` field shadows the spec parameter → `@match` passes null** | §5.2, C-4 |
| c-C12 | undefined ERE symbols pass silently (`GCMParameterSpecSpec` `c2`) | V+ | F14, C-3 gate |
| c-C13, c-C14, d-C8 | `__DEFAULT_MESSAGE` hook; `--internalbehavior` trace; no name tables | V+ (`__DEFAULT_MESSAGE` = spec+line+URL) | F14, §9 O-2 |
| c-C15, c-C20, d-C10, x-C4, x-C7, x-C11 | parser accepts any ≥6-comma text; Format 1 drops line number; no integrity counter; prose discriminator | R (mechanism) / U (≥6-comma acceptance not re-opened) | C-1 |
| c-C16 | `unique_msg` derived in four places | R | C-1 |
| c-C17, x-C8, x-C9, x-C10 | consolidator regex excludes continuation lines; `scripts/regenerate_results/regenerate_container.py:84,237-246` writes 10 columns; `gh91_compare_consolidation.py:85-90` legacy header; `rv_oracle_common.py:73-81` truncates `:::` | U (scripts not re-opened) | C-1 consumer matrix task |
| c-C18, c-C19, c-C25 | INV-INS-109..115 only in gh101 delta, INV-INS-110 untested; revert unrecorded; comp162 README stale | U | C-0 tasks |
| c-C21 | pre-fix SR `(String)` key owned by orphan `g4`; `next2Event` creates monitors (no `creation` keyword anywhere in `jca`) | V+ | F11 |
| c-C22 | audit's open toolchain items: first-disjunct, declared-only index, nested types | R (review §3.7) | §9 O-6 |
| c-C23 | `CoverageWeaver` counts spill failures not successes | U | §9 O-8 |
| c-C24 | JSE `escape(...).trim()` order | U (trivial) | C-1 |
| c-C26 | `f1`/`f2` both fire on `doFinal()` in `jca` | R | F13 |
| c-C27, x-C18-adjacent | no `ForbiddenMethod`/`RequiredPredicate`/`IncompleteOperation` `ErrorType` | R (six values) | §7.1 |
| c-C28, c-C29, c-C30 | `updateAAD` absent; wrap×doFinal mixing; SSL `Engine?`; CCM accepted; RANDOMIZED on argument | R/V+ (CCM absent from both oracles) | C-4 |
| c-C31, c-C32, c-C33 | `:::` → 6-part `unique_msg` (gh103 `unparsed`); `clock_logcat_join` split; `generic_new` absent from CLI; static path analyses `jca` for `jca_android` | R | C-1, C-0 |
| c-C34 | audit items cited by neither doc: 5/14 drive records `unknown`; KPG NPE annihilates records; 13 zero-emission specs; ~4,068-byte logcat bound | U | §9 O-6 |
| c-C35 | deprecated `remove(Property)` still called; collector unsynchronised; `HMACParameterSpec` absent; `@severity` in javadoc | R | C-4, C-2 |
| c-C36 | runtime frame has no callee → ambiguous site; unique only with event name | — (design) | §7.1 |
| c-C37 | unknown `@name` NPEs at `BaseMonitor:332-334` | R | — |
| d-C1, d-C2, d-C4..C10 | shape-flip fragility; unpinned definitions; KPG `@fail` no reset; escape; RANDOMIZED; D38/D18; no name tables; revert; parser | R | — |
| g-C1..C17 | restatements of D07–D09, D10, D11, escape, Format 1, D12, D15/16, D18, D20, D03, L5a/f, L5c, L7, L6, collision, shadow defs | R | — |
| x-C1..C6, x-C12..C17 | `EventDefinition` assign (resolved); null message NPE; escaper; no integrity counter; identity non-injective on raw location (`ErrorDescriptionTest:196-206`); root-slice inheritance; `getStack` per attempt; MD reset; KeyPair slot; SR next2; return-type match; persistent `@fail` | R / V+ | — |

### 4.3 Proposals (D) — all kept

| Item(s) | Proposal | Disposition | → |
|---|---|---|---|
| c-D1.0, d-D1.0, g-D1-R0, x-D1.0 | Rung 0 / B0: measure on E3 outputs; durable scripts; registered classifier | **Adopt** | C-0 |
| c-D1.1, d-D1.1, x-D1.2 | parser counts continuation lines; sentinels; content rule (no `\n`, `:::`, last field) in `INV-ANA-08` + test; fix escapers + NPE without whole-line re-enable | **Adopt** | C-1 |
| c-D1.2, d-D1.2, x-D1.2 | structured event/clause id in identity; rewrite `ErrorDescriptionTest:179-220`; touch four `unique_msg` sites; frozen-`jca` monitor byte-diff limited to collector call; JVM harness | **Adopt** (device-side → after Study 03 closes) | C-2 |
| c-D1.3, d-D1.3, x-D1.1 | message text only, in the nominated set: 4-arg ctor; event name from declaration-ordered array; spec vars; object class; before `__RESET`; gates INV-INS-115, array length == `getNumberOfEvents()`, micro-APK per mode, zero `unknown` | **Adopt** with F3 offset and null-field guard | C-3 |
| c-D1.4, g-D1-R3, x-D1.3 | automata/pointcuts with formal gates (INV-INS-110; ORDER↔DFA inclusion; separating traces; mutation; provenance entry) | **Adopt** | C-4 |
| c-D1.5, d-D1.4, g-D1-R5, x-D1.4 | predicates: identity vs equality first; `condition()` into body only with automaton co-edit; RequiredPredicate type; bounded automaton×predicates | **Adopt as later stage** | C-5 |
| c-D1.6, d-D1.5, x-D1.5 | generator only if measured; `__EVENTNAME`/`__PREVSTATE`; weave manifest; debug items | **Keep as option** | §9 O-1/O-2/O-8 |
| c-D1.7, d-D1.6, g-D1-R6, x-D1.6 | READY = audit conjunction + message properties | **Adopt** | §7.6 |
| c-D1.8, d-D1.F, g-D1-R3..R5, x-D1.3/1.4 | formal ideas: language inclusion; INV-INS-110; separating traces; bounded product; mutation; message properties (event+state named, no collision, injectivity); CogniCrypt oracle | **Adopt** | §7.5 |
| c-D2.1, d-D2.1, g-D2-1, x-D2 | `key=value` / JSON envelope, opaque `message`, versioned | **Adopt `key=value` v1** (JSON rejected: braces/commas/quotes in a positional line) | §7.1 |
| c-D2.2, x-D2 | error-code table per CrySL clause (`CIP-ORDER-03`) | **Adopt as the structured id** | §7.1 |
| c-D2.3, d-D2.2, x-D2 | generator emits `__EVENTNAME`/`__PREVSTATE`/name tables | option | O-1 |
| c-D2.4, d-D2.3 | trace-prefix ring buffer | option (calibration only) | O-2 |
| c-D2.5, d-D2.4, g-D2-2, x-D2 | static weave-site manifest + offline join | option | O-8 |
| c-D2.6, d-D1.2 | structured id in dedupe identity | adopt | C-2 |
| c-D2.7, d-D2.6, x-D2 | rate limit / aggregation with counters | option (needs D-6) | O-4 |
| c-D2.8, d-D2.5, x-D2 | CogniCrypt categories as `ErrorType` + remediation text | **Adopt partially** (add `RequiredPredicate`, `ForbiddenMethod` when C-5; keep existing six) | §7.1 |
| c-D2.9, g-D2-3, x-D2 | generate `.mop` from CrySL via MetaCrySL | option (long term) | O-9 |
| c-D2.10, d-D2.7 | diagnostic mode (`--internalbehavior`) | option | O-2 |
| c-D2.11 | `fsm:` `default` transitions | option, with caveat (swallows illegal events) | O-3 |
| c-D2.12 | alphabet reduction | option (gh101 method) | O-9 |
| **c-D2.13, c-D4.1** | **`args()` arity enforcement in the weaver; act mid-campaign or measure with/without** | **Adopt (C-1); researcher decision D-C** | §5.1, §6 |
| c-D3.*, d-D3.*, g-D3.*, x-D3 | B0→T0→T1→T2; T0.3 split; T0.4 bundle; identity change post-E3; co-schedule gh103; provenance tags; "more permissive ≠ more correct" | adopted in §8 | §8 |
| c-D4.*, d-D4.*, g-D4.*, x-D4 | researcher decisions: audit §7; target set; oracle choice; classifier; dedupe/count discontinuity; `RVM_prevState` worth; identity store; campaign identifier | consolidated in §6 | §6 |

---

## 5. New findings verified for this document (beyond the review)

### 5.1 The post-gh100 weaver fires `g2` on one-argument `getInstance` (K1) — **the largest post-repair mute source**

Mechanism (all `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`):
- `WrapperEmitter.java:334,379,383-384`: a trailing-`..` pattern (`getInstance(String, ..)`) is
  expanded to every overload with ≥ 1 leading param, **including `getInstance(String)`**.
- `WrapperEmitter.java:246-273,690-695` (gh100 merge): one wrapper per original call, body fires
  **every** advice bound to it. Post-fix artifact
  `results/gh101_group8_jca_frozen_control/monitors/mop/MonitorWrappers.java:538-543`:
  `TrustManagerFactory_getInstance(String)` → `g1Event`, `g2Event`, `g3Event`; same for
  `KeyManagerFactory` (`:215-219`) and `SecureRandom` (`:429-433`). Confirmed in the woven E3 DEX
  (`app.pachli_50.apk`, `classes24.dex`, `dexdump`).
- `ArgsPC.java:49-56` + `PointcutMatcher.java:268-271`: the binding form `args(alg, *)` has no type
  constraint → "always-match collector"; arity is never enforced; the wrapper path routes by
  `MethodReference` alone (`DexWeaver.java:270-280`). The descriptor JSON *does* carry the pattern.
- `jca/TrustManagerFactorySpec.mop:68-80`: `waitingInit [init -> final]` has no `g2` row → trace on
  a **correct** flow: `g1 → waitingInit; g2 → sink (mute #1, __RESET); init from start → sink
  (mute #2); getTrustManagers from start → sink (mute #3); never @match`. E3 evidence:
  `Platform.kt:78` 534, `:80` 1,179, `:83` 647; TMF 2,916 rows = 2,855 mute + 61 `X509`; KMF 296
  all mute (TlsUtil triplets). Same shape in `jca_android` (`:118-137`).
- Affected: TMF, KMF, SecureRandom (`(String, ..) && args(alg,*)` or `args(alg)`); not affected:
  MessageDigest, Cipher, Mac, Signature, KPG, SSLContext, KeyGenerator (exact 2-arity), KeyStore
  (both events on the 1-arg call by design). **dexlib2 only** — AspectJ enforces `args` arity.
- Share under E3: ≈ 16 % of all rows, ≈ 21 % of `InvalidSequenceOfMethodCalls`; SR share
  unquantified (most SR mutes are the `next2` FP at `nextBytes` sites).
- Minimal repair: enforce positional `args()` arity when grouping advices into a wrapper (one
  method in `WrapperEmitter` + unit test + INV delta); no spec change; needs re-instrumentation.
  Provenance `[tool]` (gh100 residue). It changes what the frozen `jca` **reports** (fewer mutes)
  without changing what it **says** — the same footing as gh100 itself (D3).

### 5.2 Generator facts that constrain a message composed at `@fail` (K6, K8–K12)

- `getLastEvent()` returns `id+1` in the atomic shape (`BaseMonitor.java:1151` vs `:1128-1131`;
  `O99:3626,3629`) and `RVM_lastevent` (= `id`) in the synchronized one; `−1`/`0` after reset.
  Any event-name array must apply the shape offset — or the design must avoid depending on the
  shape (§7.2 uses a spec-side `lastEventName` field written by each event body instead).
- Handlers take no parameters (`Main.stripUnusedParameterInMonitor = true`, `HandlerMethod:88-89`);
  the `Ref_*` restore path in handlers is dead (`RVMonitorSpec.java:47,69-70`); fields can be null.
  **Bug found:** `jca_android/KeyPairSpec.mop:19-21` declares a field with the same name as the
  spec parameter; `c1` writes the generated local, the field stays null, `@match`
  `setObjectAsInAcceptingState(keyPair)` passes null.
- Stale flags: a condition-failed event returns before flag assignment; the caller re-runs
  handlers on the previous flags — harmless where `@fail` calls `__RESET`, re-fires for
  `KeyPairGeneratorSpec` (no `__RESET`). Concurrent double dispatch is **not** possible: the global
  `ReentrantLock` surrounds lookup, event and handlers (`enableFineGrainedLock(false)`); but no
  `finally` — a handler exception leaves the lock held → any message code must be exception-safe.
- Undeclared ERE symbols vanish silently (`EREPlugin.java:25-33`, `FSM.java:53-58`;
  `GCMParameterSpecSpec` `c1 | c2` compiles to `c1`); duplicate declarations get `c1_1`, `c1_2`.
- `fsm:` per-state `default -> S` is supported and compiled as the state's replacement for the
  sink completion (`JavaFSM.java:113-120`); unused in rvsec.
- `__DEFAULT_MESSAGE` = `"Specification <name> has been violated on line " + __LOC + …URL` — no
  event; not a useful hook.

### 5.3 Specification defects confirmed against both oracles (K2–K5)

| Defect | Sets | Oracle 1.5.2 | api30 | Class |
|---|---|---|---|---|
| CipherSpec: no `u* -> s3` in s3; no `init` rows in s2/s3 (`jca:176-195`; `jca_android:302-317`) — multi-chunk `update` and re-`init` before final are FPs | both | `Update+`, `Init+` (`Cipher.crysl:84-85`) | same (`Cipher.cryptsl:117`) | translation defect (audit ALFA-CIP-01/02) |
| SSLContextSpec `createSSLEngine` declared `void` (`jca:63-64`; `jca_android:89-90`), `returning(SSLEngine)` in the same event | both | — | — | dead pointcut (audit FEN-SSL-ENGINE-VOID) |
| PBEKeySpecSpec `validate(RANDOMIZED, password)` (`jca:36-40,56-58`; `jca_android:41-45,61-63`) | both | `randomized[salt]` only (`PBEKeySpec.crysl:28-29`) | same (`:38-40`) | translation defect (audit FEN-PBK-SENHA-EXTRA) |
| SecureRandom `end` lacks `next2` (`jca:155-162`; `jca_android:169-177`) | both | `Ins, (Seed?, End*)*` (`:38-39`) | same | translation defect (D03) |
| KeyPair ctor mandatory (`c1 (gpu\|gpr)*`) | both | `Con, …` (`:19-20`) | `co?, (pu*, pr*)*` (`:26-27`) | **oracle choice** |
| KeyStore list (JCEKS/JKS/DKS/PKCS11/PKCS12 vs AndroidKeyStore/PKCS12/BKS/BouncyCastle/AndroidCAStore) | jca / jca_android | `:52` | `:89` | oracle choice |
| MessageDigest MD5/SHA-1; SSLContext SSL/TLSv1; PBEWithHmac catalogue | — | forbid / forbid / list | admit (`:63`) / admit (`:43`) / absent (`:121`) | oracle choice |
| bare `doFinal()` / `doFinal(out,off)` without `update` | — | `FINWOU` excludes f1/f3 (`:75,85`) | same | CrySL strictness (not a defect) |
| CCM | — | absent | absent | `CipherTransformationUtil:33` accepts it → deviation |

---

## 6. Decisions the researcher must take (each with the recommended default)

| ID | Decision | Default recommended here | Blocks |
|---|---|---|---|
| D-A | **Target set for the post-Study-03 campaign**: (i) repaired `jca_android` after the audit's §7 rulings; (ii) a successor set derived from the frozen `jca` (`jca_v2`), keeping `jca` byte-identical and inheriting gh101's divergence-record discipline; (iii) unfreeze `jca` (rejected: destroys reproducibility of E2/E3). | (ii) if the audit's §7 rulings are not imminent; (i) if they are — either way the same lane C work; the set name is a parameter of C-3/C-4 | C-3, C-4, C-5 |
| D-B | **Oracle**: original CrySL 1.5.2 vs MetaCrySL api30, per clause family (KeyPair `co?`, keystore list, MD5/SHA-1, SSL/TLSv1, Cipher catalogue). "More permissive ≠ more correct." | api30 for **availability** (keystore, catalogue), 1.5.2 for **recommendation** (digests, protocols) — recorded per spec in the conformance record; never mixed silently | C-4 |
| D-C | **`args()` arity repair in the weaver (§5.1)**: land now (changes what Study 03's `jca` reports, same footing as gh100/D3) or after Study 03 with a with/without measurement. | land now as C-1a if Study 03 has not started its final runs; otherwise C-1a immediately after, with the E3 trial re-measured with/without | C-1 |
| D-D | **Dedupe identity**: add a structured `code` (event/clause id) to `ErrorSummary` identity; free text and object hashes stay out; declare the count discontinuity. | yes (C-2) | C-2 |
| D-E | **Report suppression** (D-6 of the plan): per-process `HashSet` only, or a per-site counter/aggregation with a suppressed count first-class. | counter, not rate limit; decide after C-0 numbers | O-4 |
| D-F | **Published definitions**: the third-party classifier (prefix list + own-package rule) and the "shadow" definition (pairing vs co-location); registered before any number is published. | pairing + full-package own-code + explicit vendor list incl. `okio.`; the classifier ships in C-0 as code | C-0 |
| D-G | **Identity store** (`ExecutionContext` equality vs identity), reopened by `e204e2a4`. | equality until C-5; C-5 decides with a read-by-read enumeration (gh101 D-S10 method) | C-5 |
| D-H | The audit's §7 ten rulings (RandomStringPassword exclusion, HMC oracle bias, 1.5.2-vs-api30 anchor, extra-oracle clause family, Mac duplicate Gets, SecureRandom `ne`, folding/alias, reset/clone blind spots, declared-but-unordered events, MDG oracle shift). | — | C-4, C-5 |
| D-I | Campaign identifier: which campaign is "next" (name it) and its spec set, weaver commit, collector/parser versions. | recorded in the C-0 baseline record | all |

---

## 7. Target design

### 7.1 The report contract (what a violation record says)

One logcat line, still 7 comma-separated fields for the parser (INV-ANA-08 unchanged in shape),
message last; the **message becomes a versioned `key=value` envelope**, no `\n`, no `:::`, no `,`
inside values (values are quoted with `'` and escaped only if the C-1 property tests show it is
needed):

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<eventName> st=<stateOrClause> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<free text>'
```

- `code` is the **structured failure id** (stable, per spec × failure mode, e.g.
  `CIP-ORDER-03`, `SRD-CONSTR-01`, `TMF-ORDER-01`), defined in a table checked in with the set
  (`rvsec-mop/.../<set>/codes.csv`) and cross-checked at generation time; it is what enters the
  dedupe identity (D-D) and `unique_msg`; the free text never does.
- `ev` is the offending event name (spec-side, §7.2); `st` is the pre-fail state name where
  known (spec-side bookkeeping) or the CrySL clause for value violations; `val`/`exp` carry the
  observed and expected values (today's `expecting`); `obj` the monitored object's simple class,
  never a hash.
- `ErrorType` keeps its six values in C-1..C-4; `RequiredPredicate` and `ForbiddenMethod` are added
  in C-5 (CogniCrypt-aligned), each with a `code` prefix.
- Fabricated fields are replaced by explicit sentinels (`error_type=UNSPECIFIED`,
  `source=UNSPECIFIED:0`) and counted; continuation lines are counted, never parsed as records.
- `errors.csv` keeps its 11 columns until C-2's spec delta adds `code` (and, if D-F says so,
  `origin`), co-scheduled with gh103's `ERRORS_CSV_HEADER`; until then `code` rides inside
  `message` and consumers that need it split `key=value`.

### 7.2 How the `.mop` produces it without a generator change (C-3)

Per specification, in the declarations block: `static final String[] EVENT_NAMES = {…}` in
declaration order (viable per F2; gate G-1 regenerates and compiles); a `String lastEventName`
and `int stateBefore` field; each event body starts with `lastEventName = "<name>"; stateBefore
= getState();` (the body runs before the transition, so `getState()` is the pre-transition state
— this sidesteps both the atomic off-by-one and the lost pre-fail state); the `@fail` body composes
the envelope from those fields **before** `__RESET`, guards every field against null, wraps the
composition in `try/catch` (a handler exception would leave the global lock held), and calls the
4-argument constructor. The 21 `@fail` + 4 non-`@fail` mute sites are covered; the `codes.csv`
table lists one code per `@fail` (`<SPEC>-ORDER-00` = "sequence violation at event ev in state
st") plus one per value site.

### 7.3 Contracts and consumers (C-1/C-2)

`INV-ANA-08` (format: message grammar v1 added, sentinels), `INV-CORE-25/41` (`unique_msg` keeps
5 parts; `code` replaces the free text as part 5 **only in C-2**, with the discontinuity declared),
`INV-PLT-19` (unchanged in C-1; `code` column in C-2 via delta), gh103 `violations.py`
(`ERRORS_CSV_HEADER`, `_UNIQUE_FIELDS`, `read_errors_csv`), `aperv-tool/clock_logcat_join.py`,
`TraceComparator` (gh100), the campaign consolidators (frozen; documented as non-comparable), and
the scripts flagged by ext. 4 (`regenerate_container.py`, `gh91_compare_consolidation.py`,
`rv_oracle_common.py`) — a consumer matrix is a C-1 task, and every consumer either accepts the
grammar or is listed as frozen.

### 7.4 Automata and pointcuts (C-4)

Repairs only in the nominated set (D-A), only for **translation defects** (§5.3 rows 1–4 plus the
never-matching pointcuts, KPG NPE, D11, D18–D20, D35–D40, `remove(Property)`), each with a
divergence-record entry, a provenance class and a regressive example; oracle-choice items only
after D-B; CrySL-strictness items are **not** changed. Orphan events: INV-INS-110 must hold
(already true in `jca_android`; must be re-established in any successor set); the `fsm:` `default`
transition is available but not used by default (it swallows illegal events).

### 7.5 Formal validation (gates used by C-3/C-4/C-5)

| Gate | What | Tooling |
|---|---|---|
| G-1 generation | scratch generation of the set; compilation of `MultiSpec_1RuntimeMonitor.java`; `EVENT_NAMES.length == getNumberOfEvents()` per monitor; no undeclared/duplicate ERE symbol (fail-closed lint over `.mop` before generation) | `rv-monitor-generator` in scratch; small Java/py check |
| G-2 INV-INS-110 | no bound event with an all-`fail` row (both monitor shapes) | `scripts/gh101_monitor_transition_check.py` |
| G-3 language inclusion | `L(A_mop)` (minimised tables from the generated monitor) vs `L(A_crysl)` (CrySL `ORDER` → regex → DFA on the shared alphabet, event map declared per spec): report `L(mop) ⊆ L(crysl)` (no false accept), `L(crysl) ⊆ L(mop)` (no false reject); differences → minimal separating traces | small automata tool (py); alphabet map checked in |
| G-4 separating traces | each separating trace from G-3 becomes an executable JVM harness case (audit method) — expected verdict per oracle | JVM harness under `rvsec-mop` test tree (create `src/test`) |
| G-5 mutation | mutate `.mop` rows (drop a row, swap a state) — G-3/G-4 must catch it | py |
| G-6 message properties | over the generated monitor: every `@fail`/value site emits a non-empty `code`; codes are injective w.r.t. (spec, failure mode); no `\n`/`:::`/`,` can enter a value (property tests over the composition code) | py + JVM |
| G-7 predicates (C-5) | bounded checking of automaton × predicate store; every `REQUIRES` has a reachable producer in the set or is recorded as unclosable | py |
| G-8 device | micro-APK suite (one APK per failure mode of TMF/SSL/Cipher/SR/PBEKeySpec, plus correct flows) run via `rv-experiment run`; expected records per trace; CogniCrypt on the same APKs as an external oracle | rv-experiment; CogniCrypt |

### 7.6 Acceptance for the next campaign (rewrites the plan's §7)

1. Zero rows with `message = unknown`; every row carries a `code`.
2. Residual `found .`/empty observed values = 0 or explicitly coded (`*-NOOBS-*`).
3. Correct flows of TMF/KMF/SR (getInstance/init/getTrustManagers) produce **zero** records under
   the repaired weaver (G-8), and `@match` is reached.
4. Micro-APK per failure mode: exactly one record per violation, distinct `code` per mode; for
   CrySL-strict traces (bare `doFinal()` without update) exactly one **explanatory** record, not
   zero.
5. INV-INS-110 holds; G-3 reports no false reject for translation-defect rows repaired.
6. Signature signing branch reaches `@match`; SSL engine event fires.
7. `error_type`, `code`, `source` first-class in `errors.csv` (after C-2's delta) with the
   discontinuity declared; sentinels distinguishable; drop/suppression counters present.
8. READY for the set = the audit's conjunction (`fase0/pre_registro.md` §7) + G-6 properties.

---

## 8. Staged plan as OpenSpec changes, with parallel lanes

Lanes: **A** Python/contracts (`rv-coverage`, `rv-android-core`, `rv-platform`, `aperv-tool`,
`rv-experiment`) · **B** rvsec-core/collectors/weaver (Java) · **C** specifications (`.mop`, blocked
on D-A/D-B/D-H) · **V** validation infrastructure (formal tools, harness, micro-APKs). Radius
legend as in the plan (S/C/M/I/P). Track per `docs/WORKFLOW.md` §3.

```
C-0 (baseline, docs+scripts)  ──┬── C-1a weaver args arity [B]      ── needs D-C
                                ├── C-1  transport & parser [A,B]    ── parallel with C-1a
                                ├── C-V  validation infra [V]        ── parallel from day 1
                                └── (researcher: D-A, D-B, D-H)
C-1, C-V ── C-2 identity & schema [B,A]  (device-side; after Study 03 closes)
D-A ────── C-3 message text in the nominated set [C]  ── needs C-1 grammar, C-V G-1/G-6
D-A,D-B ── C-4 automata & pointcuts [C]                 ── needs C-V G-2..G-5; parallel with C-3 by file
D-G,D-H ── C-5 predicates [C,B]                         ── after C-4
options O-1..O-9 (generator/weaver/runtime)              ── only if C-0/C-3 measurements justify
```

| Change | One-sentence description (issue title) | Track / template | Modules | Radius | Depends on | Parallel with |
|---|---|---|---|---|---|---|
| **C-0** | Register the post-repair baseline of the message problem from the Study 03 trial and freeze the definitions (classifier, shadow, campaign identifier) as code | Quick Path / Documentation+scripts | `experimento-comp162/scripts`, `docs` | none | — | everything |
| **C-1a** | Enforce `args()` positional arity when the dexlib2 weaver groups advices into a merged wrapper, so `getInstance(String)` no longer fires the two-argument advice | FF SDD / Bug (`instrumentation`) | `rvsec-instrumentation-dexlib2` (`WrapperEmitter`), `rv-instrumentation-dexlib2` (results parse) | I | D-C | C-1, C-V |
| **C-1** | Make the violation transport honest: message grammar v1 (`key=value`, no `\n`/`:::`), sentinels instead of fabricated fields, continuation-line and drop counters, fixed escapers and `null` guard, consumer matrix | Full SDD / Enhancement (`analysis`, `core`, `platform`; `instrumentation` for collectors) | `rv-coverage`, `rv-android-core`, `rv-platform`, `aperv-tool` (gh103 co-schedule), `rvsec-core`, both `ErrorCollector`s | P + C | C-0 | C-1a, C-V |
| **C-V** | Build the formal validation toolkit for JavaMOP specifications: `.mop` lint (undeclared/duplicate symbols, array-length), INV-INS-110 gate as pytest, CrySL `ORDER`→DFA inclusion with separating traces, spec mutation, JVM harness home under `rvsec-mop`, micro-APK suite definition | Full SDD / Feature (`instrumentation`) | `rvsec-mop` (new `src/test`), `rv-android/tests/parity`, `scripts/`, `.claude/skills/rv-analyze-spec` | S-test + P | — | all |
| **C-2** | Put a structured failure `code` into the collector identity and into `unique_msg`, add `code`/`origin` columns to `errors.csv` by spec delta, and declare the count discontinuity | Full SDD / Enhancement (`core`, `platform`, `analysis`) | `rvsec-core` (`ErrorSummary`, test), `rv-android-core` (`log.py`), `rv-platform`, `aperv-tool` | C + P | C-1, C-V(G-6), D-D; **device-side → after Study 03's final runs** | C-3 design |
| **C-3** | Give every sequence and constraint report in the nominated set a message: event-name arrays, pre-fail state bookkeeping, envelope composed before `__RESET`, `codes.csv` per set | FF SDD / Enhancement (`instrumentation`) | `rvsec-mop/<set>/` (21 `@fail` + 4 sites) | S | D-A, C-1 (grammar), C-V (G-1, G-6) | C-4 (different hunks, same files → sequence per file) |
| **C-4** | Repair the translation defects of the nominated set against both CrySL oracles with formal gates: Cipher `Update+`/`Init+`, SSL `createSSLEngine`, PBEKeySpec `salt`, SecureRandom `next2`, Signature `sign()`, KPG NPE, D11/D18–D20/D35–D40, `remove(Property)`; oracle-choice items only per D-B | Full SDD / Bug (`instrumentation`) | `rvsec-mop/<set>/`, `data/<set>/` divergence record | S | D-A, D-B, C-V (G-2..G-5) | C-3 |
| **C-5** | Reconnect the predicate graph on a decided identity semantics: `RequiredPredicate`/`ForbiddenMethod` error types, `condition()` moved to bodies with automaton co-edit, RANDOMIZED discipline, missing producers | Full SDD / Feature (`instrumentation`, `core`) | `rvsec-core` (`ExecutionContext`, `ErrorType`), `rvsec-mop/<set>/` | C + S | D-G, D-H, C-4, C-V (G-7) | — |

Per-change outline (tasks are written by the OpenSpec skills; this is the content they need):

**C-0.** (1) commit the E3 measurement scripts (unknown share; pairing and co-location shadow;
per-spec; `found .`; source-with-line ratio; TMF/KMF triplet signature) next to
`experimento-comp162/scripts/`, with hashes and the exact inputs; (2) the classifier and shadow
definitions as code (D-F); (3) record the `e204e2a4` revert in `data/gh101/README.md` and the
comp162 README state; (4) baseline numbers table in a doc; (5) the campaign identifier record
(D-I). Gate: byte-identical rerun.

**C-1a.** (1) failing test: an advice with `args(a, *)` must not be grouped into the 1-arg
wrapper; (2) repair in `WrapperEmitter` grouping (drop an advice whose `args` list has no trailing
`..` and whose length ≠ `cc.paramFqns.size()`); (3) inline path check (`PointcutMatcher` binding
form) — same rule; (4) `WeaveReport` counter for advices excluded by arity; (5) delta spec:
INV on wrapper grouping; (6) re-weave the E3 trial's TMF/KMF micro-cases and record before/after.

**C-1.** (1) `INV-ANA-08` delta: grammar v1, sentinels, counters; (2) parser: continuation lines
counted; sentinel values; Format 1 keeps the line number; property tests (commas, quotes, `\n`,
`:::`, Unicode, truncation at the logcat bound); (3) collectors: fix `escapeSpecialCharacters` (both),
`null` guard, escape only `expecting`, keep the whole-line call off; (4) `unique_msg` construction
in one place; (5) consumer matrix (gh103, `clock_logcat_join`, `TraceComparator`, the three scripts
of ext. 4, consolidators listed as frozen); (6) `generic_new` in the CLI or explicitly out;
(7) static-path set mismatch (G12) at least documented, fixed if trivial.

**C-V.** (1) `.mop` lint; (2) INV-INS-110 as a pytest gate over generated tables (both shapes);
(3) `ORDER`→DFA inclusion tool with per-spec alphabet map, output = separating traces; (4) mutation
runner; (5) JVM harness home (`rvsec-mop/src/test`) with the audit's separating traces as first
cases; (6) micro-APK suite spec (sources under `apks_examples/`, built by the existing pipeline;
run only via `rv-experiment run`); (7) skill `rv-analyze-spec` gains dimensions from the audit's §18.

**C-2.** (1) `ErrorSummary` identity += `code`; `ErrorDescriptionTest:179-220` rewritten (the
message *text* stays out); (2) `unique_msg` part 5 = `code` (INV-CORE-25/41 delta with the
discontinuity declared); (3) `errors.csv` + `code`, + `origin` if D-F (INV-PLT-19 delta, gh103
header, `test_result_processor`); (4) collector suppressed-count (D-E); (5) frozen-`jca` monitor
byte-diff limited to the collector call. Device-side: needs re-instrumentation → after Study 03.

**C-3.** Per file: `EVENT_NAMES`, `lastEventName`/`stateBefore` bookkeeping, envelope in `@fail`
(before `__RESET`, null-guarded, exception-safe), 4-arg ctor at the 4 non-`@fail` sites,
`codes.csv`; gates G-1, G-6, G-8 (micro-APK per mode, zero `unknown`); divergence-record entries.

**C-4.** Per file, translation defects first (§5.3), then D-B items; each edit = row(s) + entry +
regressive example; gates G-2..G-5; `KeyPairSpec` shadow bug; `SignatureSpec` return types;
`createSSLEngine`; KPG NPE guard; `next2`; Cipher `u*`/`init` rows; PBEKeySpec `salt`.

**C-5.** D-G ruling → `ExecutionContext` semantics with read-by-read enumeration; new `ErrorType`s;
`condition()` → body with automaton rows (no new orphans, G-2); RANDOMIZED on return values;
producers for `SecretKeyFactory`/`*ParameterSpec` or recorded unclosable; G-7.

Parallelism in practice: C-0, C-1a, C-1, C-V start together (four people/agents, disjoint files);
C-2 and C-3 design can proceed while C-1 lands; C-3 and C-4 edit the same 21 files — sequence
**per file** (one owner per spec at a time), not per change; C-5 last.

---

## 9. Options kept open (not scheduled; each with what would trigger it)

| ID | Option | Radius | Trigger |
|---|---|---|---|
| O-1 | Generator emits `__EVENTNAME`/`__PREVSTATE` (or `RVM_prevState` + `String[] eventNames`) instead of spec-side bookkeeping | M (small, additive) | C-3 shows the bookkeeping is error-prone across 21 files or a second set appears |
| O-2 | Diagnostic mode: bounded trace-prefix ring buffer per monitor / `--internalbehavior` for calibration runs | M | calibration campaigns need trace context |
| O-3 | `fsm:` `default -> S` transitions for orphan absorption | S | a successor set is written from scratch (never in `ere:` specs; swallows illegal events) |
| O-4 | Per-site aggregation/rate limit with first-class suppressed count | C/P | C-0 shows restart-driven volume dominates |
| O-5 | Missing producers (`SecretKeyFactory`, `*ParameterSpec`) as new specs | S | C-5 |
| O-6 | Audit toolchain items: first-disjunct, declared-only index, varargs, nested types, fail-closed generation, `android.jar` pinning | I/M | any of them shown to affect messages in C-0/G-8 |
| O-7 | End-of-trace (`IncompleteOperationError`) via `endObject`-like hook in dexlib2 | M+I | prototype-and-measure only |
| O-8 | Localisation: debug-item preservation in `RegisterShifter` + spill counter; static weave-site manifest joined offline; app-frame | I / I+P / M | C-0 shows a real share of line-less frames (E3 trial: 100 % lines claimed by ext. 1, U here) |
| O-9 | Alphabet re-budgeting (gh101 method) / generating automata+messages from CrySL via MetaCrySL | S / high | successor set design |

---

## 10. Errata to carry into the plan and the review (do not edit; list for the issue)

Plan: FSMMin → JavaFSM; `:604-610` dead (javamop inlines the condition); accessors + shape
offset; pre-fail state; SSLContext row; Cipher/KeyPair rows reclassified (CrySL/oracle); TMF `:63`
+ `:62`; `.aj` source is git-ignored; D07/D08 persist in `jca_android`; `Property` 25; 50 live sites;
`generic_new` 39; numbers (73.4 %, 28, 3,098, 163) withdrawn or redefined; prior work (gh100, gh101,
audit, E3, revert); WS-2.1–2.3 done in `jca_android`; Phase A radius; WS-6.6 not a re-enable;
WS-6.2/6.4 contracts; D-1/D-2 decided; §7 criteria 2/5/6; register D02/D05/D06/D11/D34 + additions.
Review: O99 atomic 15/23; root clone at `O99:15992`; `coverage.py` lives in `rv-android-core`;
`SecureRandom.crysl:39`; "PKIX case closed by gh100" is **wrong** (the merge introduced §5.1);
"CipherSpec faithful" is wrong for `Update+`/`Init+`; api30 oracle was not opened; gh101 does not
record the revert; E3 already ran (T0.1 is offline now); scripts must be durable; SRD 12,400 stays
INFERRED; D44 confirmable.

---

## 11. References (absolute paths where outside `rv-android`)

- Repo root: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`
- Plan / review / handoff / prompt / four validations: `rv-android/docs/20260815_javamop_mensagens*.md`
- gh100/gh101: `rv-android/openspec/changes/gh10{0,1}-*/`, `rv-android/data/gh101/`
- Audit: `rv-android/docs/20260808_validar_specs_jca_android.md`, `rv-android/audit/20260808_validacao_jca_android/`
- Study 03: `rv-android/docs/20260810_plano_prontidao_estudo03.md`, `docs/20260812_comp162.md`, `docs/20260812_registro_execucao_prontidao_e3.md`, `rv-android/experimento-comp162/`
- Specs: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/`; CrySL: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/Crypto-API-Rules/JavaCryptographicArchitecture/src/`; api30: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/`
- Runtime/generator/weaver: `rvsec/rvsec-core/`, `rvsec/rvsec-logger-csv/`, `rvsec/rvsec-android/rvsec-logger-logcat/`, `rv-monitor/`, `javamop/`, `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`
- Oracles: `rv-android/results/{gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control,gh92_e2e2,gh56-smoke}/monitors/`; woven E3 corpus: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`
- Dataset: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`
- Process: `rv-android/docs/WORKFLOW.md`, `docs/SDD.md`, `.claude/AGENTS.md`, `CLAUDE.md`
