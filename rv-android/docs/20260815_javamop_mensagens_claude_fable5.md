# Independent validation of the JavaMOP messages plan and of its adversarial review

**Date:** 2026-08-15
**Reviewer:** Claude Fable 5 (`claude_fable5`), acting as external sceptical reviewer per
`docs/20260815_javamop_mensagens_validacao_prompt.md`.
**Artifacts under validation:** the plan (`docs/20260815_javamop_mensagens.md`, 982 lines) and the
adversarial review (`docs/20260815_javamop_mensagens_analise.md`, 797 lines). The handoff that
produced the review (`docs/20260815_javamop_mensagens_analise_handoff_prompt.md`) was read as context.
**Status:** analysis only. Nothing was implemented; no repository file other than this report was
written; no emulator was touched; no monitor was generated. All scripts and intermediate outputs live
in the session scratchpad (`/tmp/claude-1000/.../4c766db2-.../scratchpad/v1..v9/`, listed in §9).

Paths below are relative to `$RVSEC = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`;
`rv-android/` is `$RVA`. `O99`, `O101`, `OFZ` name the generated monitors under
`rv-android/results/{gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/MultiSpec_1RuntimeMonitor.java`.
`E3` = the Study 03 campaign output under `rv-android/experimento-comp162/results/comp162_00..07/`.

**On the word "spec".** This repository uses it in two unrelated senses and this report uses both:
*SDD/OpenSpec specs* (`openspec/specs/**`, `openspec/changes/gh<N>-*/`, invariants `INV-*`) are the
development-process artifacts; *JavaMOP specifications* (`rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/*.mop`)
are the runtime-verification artifacts. "The `jca` set is frozen" is about the second kind; "INV-INS-110"
is about the first.

Evidence classes used throughout: **PROVEN** (executed or disassembled by this review), **MEASURED**
(computed by this review's own scripts), **OBSERVED_IN_ARTIFACT** (source or generated file re-opened
and quoted), **INFERRED**, **NOT_VERIFIED**.

---

## 1. Executive summary

**Verdict on the plan.** The diagnosis is right and the pillar holds — `@fail` is a state test on an
implicit sink appended by `JavaFSM`, and the `@fail` body is inlined verbatim into an instance method of
the monitor class — but the plan is wrong on four mechanism details that its own workstreams depend on
(FSMMin does not complete the automaton; `BaseMonitor.java:604-610` is dead code and the live
`condition()` mechanism is a prologue in the monitor's event method that runs *after* the monitor has
been created; `Prop_N_state`/`RVM_lastevent` exist only in the 8-of-23 synchronized monitors; the
pre-fail state is lost at `@fail`), it is stale with respect to gh100/gh101/the audit/Study 03, three
of its headline numbers do not reproduce under any definition (73.4 %, 28 findings, 3,098-row group),
two of its "false positives" are CrySL semantics (D05, D06 against the 1.5.2 rules) and one of its
severity-A defects is an oracle choice, not a translation defect (D17). As sequenced it has no
admissible target set. **Not executable as written; the goal and roughly half of the register survive.**

**Verdict on the review.** Reliable on mechanism — every one of the 52 decision-carrying `file:line`
citations we re-opened for it is CONFIRMED or off by one line — and its re-measurements, which it left
untraceable, all reproduce (V2). It is right that the plan ignores prior work and that its specification
tier is not admissible today. But it carries **three material errors and one blind spot**: (i) it says
gh101 "records" the `e204e2a4` revert — nothing in gh101 does; (ii) it says the PKIX case in
`TrustManagerFactorySpec` "is closed by gh100's wrapper merge" for Study 03 — the merge removed the
`found .` symptom and replaced one informative + one mute record with **two mute records per correct
flow**, because the merged wrapper now fires `g1` *and* `g2` on every single-argument `getInstance`
(V5 item 11, PROVEN in an E3 DEX, MEASURED on the OFZ tables for 11 specs); (iii) it calls the `jca`
`CipherSpec` "faithful" to `Cipher.crysl` while `Init+` and `Update+` are not translated (audit
ALFA-CIP-01/02); and (iv) it never opens the api30 oracle that governs `jca_android`, under which
`KeyPair`'s constructor is optional (`co?`) and D06 flips. Its T0/T1 cut is sound in shape but stated as
the only path, and its premise "E3's first batches will provide the re-baseline" is already out of date:
**Study 03 ran on 2026-08-13** and its 19,664-row `errors.csv` set is on disk.

**Three things knocked down.**
1. *Plan:* "L5c is the highest-value single fix" — on the E3 output **100 % of reported frames carry a
   line number** (19,664/19,664, MEASURED); an offline `dexdump` census on one APK shows 3.9 % of
   methods lose line positions and **0 of 693 woven methods** do (V5). *Review:* "plausibly small" was
   right by luck; now measured.
2. *Review:* "for Study 03 the PKIX case is closed by the merge" — see (ii) above; the E3 output shows
   `TrustManagerFactorySpec` with 2,855 `InvalidSequenceOfMethodCalls`, 98 % twin-less, 0 `found .`,
   at both the `getInstance` and the `init` line of the same methods (V2b) — exactly what the mechanism
   predicts. The `unknown` share **rose** from 72.9 % to 79.9 % post-repair.
3. *Both:* "`unknown` ⇔ `InvalidSequenceOfMethodCalls`" — true on the 2026-07-06 dataset, false on E3:
   419 `UnsatisfiedConstraint` rows carry `unknown` (the 3-arg body sites `jca/IvParameterSpec.mop:48,55`
   that gh100 restored). And the review's "gh101 records the revert" — no gh101 artifact mentions
   `e204e2a4` (V7).

**Three things confirmed.** (a) The pillar (`JavaFSM.java:112-142,158`; `HandlerMethod.java:34-46,106`;
`O99:7480-7487`). (b) The review's corrections to the plan's mechanics (`condition()` prologue,
`:604-610` dead, atomic vs synchronized shape, `getState()/getLastEvent()` portable, compose before
`__RESET`, `TrustManagerFactorySpec.mop:63`, Property = 25, `generic_new` `Log.v` = 39). (c) The
wrapper-collision account of the 8,371 empty observed values (pre-fix `MonitorWrappers.java:588-616`;
E3: TMF `found .` 8,371 → 0).

**Recommendation.** Do not implement the plan as sequenced (agree with the review), but also do not
adopt the review's cut unchanged. Rung 0 is not "wait for E3" — it is *read E3 now* (this report gives
the headline numbers, §3-V2). **Surface the `g1+g2 → sink` finding to the researcher immediately**: it
is a `[tool]` defect (`args()` arity ignored) that the audit had already listed, but its consequence
under the merged wrapper — correct single-argument `getInstance` flows never reach an accepting state
in 11 of the 23 `jca` specs — bears on the validity of the Study 03 `jca` arm and only the researcher
can decide whether to act mid-campaign. Then follow the ladder of §6: toolchain syntax bans + sentinel;
identity decision (structured event/clause id, not free text); message text in whichever set the
researcher unfreezes/nominates after the audit's §7 rulings; automaton/pointcut repairs with formal
gates; predicates; generator only if the value measured on the earlier rungs justifies it.

---

## 2. Method

Nine subagents, one per dimension of the validation prompt §5, each with a self-contained prompt and
absolute paths, each instructed to re-open every `file:line` it judged and to return verbatim quotes;
plus one follow-up to V2 (re-measure on E3) and one to V5 (explain the E3 `TrustManagerFactorySpec`
residual). `sequential-thinking` was used at decomposition, at consolidation of contradictions between
subagents, and before the final opinion. Where two subagents disagreed (V1 vs review on the O99 atomic
count; V4 vs review on `CipherSpec` fidelity; V5 vs review on the PKIX residual) the disagreement was
resolved by the quote, never by majority.

| Dim. | What it opened (summary) | Scripts / outputs |
|---|---|---|
| V1 | 52 decision-carrying citations across generator, runtime, weaver, Python, `.mop`, oracles | `scratchpad/v1/v1_report.md` |
| V2 | `ase-journal/dataset/results/errors.csv` (+README, summary.csv); then E3 `comp162_0*/…/errors.csv` ×8 | `scratchpad/v2/v2_{a..e}.py|.out`, `v2b_e3.py|.out` |
| V3 | `JavaFSM`, `FSMMin`, `EREPlugin`/`FSM`, `FSMPlugin`, `LogicPluginFactory`, `BaseMonitor`, `HandlerMethod`, `RawMonitor`, `SuffixMonitor`, `MonitorSet`, `Monitor.java`, rv-monitor-rt `IMonitor`/`Abstract*Monitor`, javamop `EventDefinition`/`RVDumpVisitor`/`DumpVisitor`/`javamop.jj`/`RVParser.jj`, `EndProgram`/`EndObject`, O99/O101/OFZ, `gh56-smoke`, both `.mop` sets | `scratchpad/v3/` |
| V4 | `Crypto-API-Rules/.../src/*.crysl`, `MetaCrySL/generated/api30/*.cryptsl`, both `.mop` sets, `CryptoAnalysis/.../errors/*.java`, `rvsec-core` `ErrorType`/`Property`/`*CipherTransformationUtil`, audit `batchA..D/juiz_sintese_*.md`, `gama_report.md`, `pilot/` | `scratchpad/v4/v4_report.md` |
| V5 | dexlib2 module (all sub-modules), gh100 evidence, `48b57fc5` diff, pre/post-fix `MonitorWrappers.java`, `gh56-smoke` monitor, OFZ, one E3 DEX (`dexdump`) and one instrumented-vs-original APK census | `scratchpad/v5/{dbg.py,jca_in_lost.py,e3/}` |
| V6 | `logcat_parser.py` (executed on synthetic lines), `log.py`, `result_processor.py` (+ header test, run), `coverage.py`, gh103 `violations.py`, `clock_logcat_join.py`, campaign consolidators, `TraceComparator.java`, CLI/config, `openspec/specs/*` | `scratchpad/v6/parser_probe*.py|.out` |
| V7 | git log/show for the nine commits, gh100/gh101/gh102/gh103 `tasks.md`, `data/gh101/*`, freeze gate test (run), audit `global/`, `fase0/`, `set/`, `pilot/`, `plano_prontidao_estudo03.md`, `comp162.md`, `registro_execucao_prontidao_e3.md`, the E3 results tree | `scratchpad/v7/notes.txt` |
| V8 | design/proportionality; `ErrorType.java`, gh101 `design.md`/delta spec, `tests/parity/`, `rvsec-mop` tree, E3 results, `HandlerMethod` | `scratchpad/v8/e3_baseline.txt` |
| V9 | audit of the review: 13 review-only claims re-opened, bias patterns, misses | `scratchpad/v9/` |

Two facts about the validation prompt itself, found while executing it: its path for `JavaFSM.java`
(`.../java/rvj/logicpluginshells/fsm/`) is wrong — the file is at
`rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java`;
and its §6 rung 0 ("how to use the first outputs of Study 03") assumes those outputs are future — they
exist (E3 ran 2026-08-13; `experimento-comp162/README.md:182-193` "Estado" is stale and still says
"campanha não executada").

---

## 3. Verdicts per dimension

### V1 — Cross-factual verification (52 citations re-opened; OBSERVED_IN_ARTIFACT unless noted)

Tallies. **Plan** (45 rows): CONFIRMED 39 · IMPRECISE 3 · WRONG 2 · UNVERIFIED 1.
**Review** (52 rows): CONFIRMED 49 · IMPRECISE 2 · WRONG 0 · UNVERIFIED 1.

Disagreements between the two documents, decided:

| Topic | Winner | Evidence |
|---|---|---|
| FSMMin "completes missing entries" (plan) vs "minimises only" (review) | **Review** | `fsm/FSMMin.java:24-28` is the field/`static { fail = State.get("fail"); }` block; `:56-59` `this.events.add(null); minimize();` (Hopcroft, `:139-222`). Completion: `JavaFSM.java:112 int default_transition = countState;` `:136`, `:141`, `:158 setProperty("fail condition", "$state$ == " + countState)` |
| `BaseMonitor.java:604-610` live suppression (plan) vs dead (review) | **Review** | `rvj/parser/ast/rvmspec/EventDefinition.java:30 private String condition;` has no setter; `RVMonitorExtender.java:256-259` passes no condition; `RVM_conditionFail` in O99/O101/OFZ = 0. Live path: `javamop/.../mopspec/EventDefinition.java:151-156` (`RemoveConditionVisitor`) + `RVDumpVisitor.java:47-51` `if ( ! (cond) ) { return false; }` → `O99:7385-7388` |
| `Prop_N_state`/`RVM_lastevent` "instance fields, all alive" (plan) vs "synchronized shape only" (review) | **Review**, with a count correction | `BaseMonitor.java:158-163` atomic iff `useAtomicMonitor && simple && isOutermost && monitorInfo == null && !timeTracking`; `monitorInfo` set at `:248-250` when some event leaves a spec parameter unbound → an unbound-parameter event forces the synchronized shape (V3 N7). Counts by `extends`: **O99 15 atomic / 8 synchronized** (review said 16/23), OFZ 15/8, O101 18/5 |
| `TrustManagerFactorySpec.mop:62` (plan) vs `:63` (review) | **Review** | `:62 event gtm1 after(TrustManagerFactory k) returning(TrustManager[][] trustManager): :63 call(public KeyManager[] TrustManagerFactory.getTrustManagers())` — two defects, `:62` double array and `:63` return type |
| `Property` 24 (plan) vs 25 (review) | **Review** | `Property.java:8-55` 25 constants; `git show 233df18a` adds `GENERATED_CIPHER`, `MACED` |
| `jca` `addError` 50 (plan L1) / 51 (plan L7) vs 51 textual / 50 live (review) | **Review's framing** | `jca/MessageDigestSpec.mop:57` is `//` commented; grep 51 / 50; mute sites 25 (21 `@fail` + `PBEKeySpecSpec:24,30` + `IvParameterSpec.mop:48,55`) |
| `generic_new` `Log.v` 44 (plan) vs 39 (review) | **Review** | `grep -c "Log\.v" generic_new/*.mop` Σ = 39 |
| the `.aj:979,984,1037` oracle | both imprecise | it is `rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj`, **git-ignored** (`rvsec-mop/.gitignore:2 *.aj`, `git status --ignored` → `!!`), not "untracked" (review) and not a versioned oracle (plan) — the freeze gate cannot see it either way |
| `DexWriter.java:1156-1159` (plan) vs `:1155-1158` (review) | UNVERIFIED (external jar not opened; effect agreed) | — |
| review's `O99:15921-15938` for the root clone | review IMPRECISE | that range is the `unsafe_protocol` root dispatch; the clone is `O99:15992 (SSLContextSpecMonitor)sourceLeaf.clone()` inside `SSLContextSpec_initEvent` (`:15941`) |

Validation-prompt §4 lessons 1–10: all CONFIRMED in source (lesson 8's "second fabricated record" is
PROVEN by V6 for continuation lines with ≥5 commas, and only INFERRED for logcat's re-prefixing of
`\n` segments on-device).

### V2 — Evidence base (all MEASURED; scripts in `scratchpad/v2/`)

**2026-07-06 dataset** (97,018 rows; 113 apks with ≥1 error, 163 in `summary.csv`, 50 with none):

| Item | Plan | Review | This review | Definition | Plan | Review |
|---|---|---|---|---|---|---|
| Distribution / 19 messages / `unknown` ⇔ InvSeq | as stated | identical | identical, 0 counter-examples either way | `unique_msg.split(':::')[3]` | C | C |
| Shadow / orphan | 26,152 / 44,608 = 27.0 % | 26,152 pairing; 32,411 (33.4 %) co-location | 26,152 (26.96 %) under min-pairing Σ min(#InvSeq,#concrete) per (apk,rep,tool,spec,class,method); 32,411 (33.41 %) under co-location; +time 26,103 / 32,232 | as stated | I (prose says co-location, number is pairing) | C |
| Per-spec table | pairing values | pairing | identical under pairing; under co-location MessageDigest is 99 % shadow (10,035/10,135) and KeyStore 29 % — the definition changes the per-spec reading materially | pairing | C as pairing | C |
| TMF identical-count sites | 1,733/1,748 | + 4,587/4,602 with timeout | identical | — | C | C |
| Event granularity 46,330 / 20,507 / 32,232 | as stated | + `time` is seconds, 17,174 rows at time=0 | identical; `time` integer 0..294, monotone within run | (…,time,…) | C (numbers) / I ("event") | C |
| Funnel 661 → 207 → 136 | as stated | same | identical | — | C | C |
| Last stage "28" | 28 | 53/36/26/24 | **53** (9 vendor prefixes) / **36** (+`okio.`) / **26** (own 2-segment package) / **24** (3-segment/full). **No definition yields 28.** The three example classes the plan names are own-package, so 28 ≈ 26 + hand-adjustment | see left | **W** as a reproducible number | C |
| "73.4 % third-party" | 73.4 % | not reproducible | **not reproducible** under ~15 definitions (rows, non-unknown rows, sites, keys, classes; vendor/own/union/intersection). Nothing in 73.0–73.9 %. Note: per-tool `unknown` share is 71–74 % — possible confusion | — | **W** | C |
| 82,890 (85.44 %) / 85,384 (88.01 %) / 78 of 113 | as stated | only with `okio.` / only 2-segment | 85.44 % **only with `okio.` added** (4,050 rows) — not in the plan's list; 88.01 % **only with the 2-segment prefix** (full package 89.82 %, 81 zero-own) | — | I (definitions unstated) | C |
| Amplification keys 661 / 15,748 / 85,257; "11,761 rows (12.12 %) identical" | as stated | first four identical; largest group 6 | keys identical; 11,761 is the *excess* (N − distinct); rows belonging to a fully identical group are 20,323 (20.95 %) | 10-column key | I (wording) | C |
| Largest identical group | 3,098 (Ktor) | 6 | **6** on the 10-column key (dankchat, SecureRandomSpec, time=1); **3,098 is the 5-column key** (apk,spec,class,method,message) = dankchat / SecureRandomSpec / `io.ktor.util.NonceKt$nonceGeneratorJob$1.invokeSuspend` / `unknown`; 7-col 388, 8-col 230 | — | **W** (wrong key attached to the number) | C |
| "1,542-row group" | from `exp_00` | — | in *this* CSV the largest (apk,rep,tool,unique_msg) group is 388; 1,542 and "24 timestamps at Platform.kt:83" are other result dirs — the plan mixes sources without saying so | — | I | — |
| Degenerate messages (`but found .` 8,843/5; missing space 2,005; ellipsis 109; braced 9/14,959; unbraced 7/11,292; case-only 4; SHA-1/SHA1/SHA 2,340) | as stated | identical | identical (unbraced 9/11,299 if the two `invalid key size` messages are counted) | — | C | C |
| TMF empty observed value 8,371 | "okhttp" | 62 apps; class split | 8,371 across 62 apps: `Platform` 7,174; `TlsUtil` 584; `okhttp3.internal.Util` 324; Ktor 219; own-package `AdvancedX509TrustManager` 27+24; Conscrypt 19 → 96.5 % okhttp3, not 100 % | — | I | C |
| `found X509` 643; UnsatisfiedConstraint 0; UnsafeProtocol 3 msgs; InvalidKeySize 7 | — | — | identical | — | C | C |
| SecureRandomSpec 12,400 site profile | "100 % mute" | audit profile | `kotlin.uuid.UuidKt__UuidJVMKt.secureRandomBytes` 3,962; Ktor `NonceKt$nonceGeneratorJob$1.invokeSuspend` 3,104; Tink `Random.randBytes` 1,256 + 276 = 1,532; `secureRandomUuid` 1,229; gms 530 + 288; SpongyCastle DRBG chain ≈ 1,752 — the audit's profile is exact | (class,method) | — | C |

New (MEASURED): `unknown` share is flat across tools (71.2–74.0 %) and timeouts (72.5–73.1 %) —
a property of the specs/pipeline, not of the driver; volume is concentrated (top-5 apks 32 % of rows;
SSLContextSpec + TrustManagerFactorySpec = 45.7 % of the CSV); every `unique_msg` splits into exactly
5 parts — the dataset carries no `\n`/`:::` residue.

**E3 / Study 03 output (post-gh100, frozen `jca`, reverted store; 8 files, MEASURED)** — the
re-baseline both documents postpone:

| Item | 2026-07-06 | E3 (comp162) | Note |
|---|---|---|---|
| rows / apks with ≥1 error / tools | 97,018 / 113 of 163 / 11 | **19,664** / 112 of 162 / 3 (`ape` 7,133; `aperv:mop_off_llm_off` 6,023; `aperv:mop_on_llm_off` 6,508) | timeout 300 only |
| error types | InvSeq 72.93 · UnsafeAlg 15.92 · UnsafeProto 9.07 · InvKST 2.07 · InvKS 0.01 · **UnsatCons 0** | InvSeq **77.78** · UnsafeProto 7.46 · **UnsatCons 6.90 (1,357)** · UnsafeAlg 6.50 · InvKST 1.35 · InvKS 2 rows | the 9 restored events now emit |
| distinct messages | 19 | **16** | — |
| `unknown` share | 72.93 % | **79.91 %** (per tool 80.9 / 79.6 / 79.2) | **rose** |
| `unknown` ⇔ InvSeq | both ways | **broken one way**: 419 `unknown` rows are `UnsatisfiedConstraint`, all `IvParameterSpecSpec` (`jca/IvParameterSpec.mop:48,55`; e.g. Tink `AesSiv.encryptDeterministically` 242) | plan WS-1.5 sites |
| shadow (pairing) / co-location | 26.96 / 33.41 % | **22.21 / 28.08 %**; orphan mute rows still 55.6 % of the CSV | — |
| new 1:1 twin families | — | **SecretKeySpec 820/820, IvParameterSpec 419/419, PBEKeySpec 118/118** — restored orphans reaching the DEX and sinking (plan L2 mechanism 1, live) | — |
| TMF | 9,015 InvSeq; 1,733/1,748 identical sites; ratio 1.0001; `found .` 8,371 | **2,855 InvSeq; 21/543 identical sites; ratio 46.8; `found .` 0; `found X509` 61**; mute at both `getInstance` and `init` lines (`Platform.kt:80` and `:83`) | mechanism in V5 item 11 |
| `but found .` total | 8,843 | **98** (MD 55, Sig 39, Mac 4) | residue = non-allow-listed algorithm under frozen `jca` |
| funnel | 661 → 207 → 136 → 53/36/26 | **696 → 188 → 184 → 69/54/45** | same defs |
| third-party rows | 81.26 / 85.44 / 88.01 % | 80.04 / 84.81 / 87.34 %; 72/112 zero-own; `Platform` 30.4 % | unchanged |
| largest identical group | 10-col 6 | **11-col 2** (excess 0.05 %); 10-col w/o `source` 7; 5-col 1,152 (dankchat Ktor loop) | `source` separates lines |
| SecureRandomSpec | 12,400 (12.8 %) | **2,882 (14.7 %)**, same site profile (Ktor nonce 1,152; `secureRandomBytes` 731; …) | `next2` stratum untouched by gh100 |
| `source` column | absent | **100 % of rows carry `File:line`**; 0 `Unknown Source`; 85 of 164 sites have >1 distinct line | L5c has no measurable effect on reported frames here |

Review predictions that **hold** on E3: `UnsatisfiedConstraint` appears; TMF empty value gone; TMF 1:1
twin gone; SRD `next2` stratum persists. That **do not** hold: "PKIX case closed" (mute volume in TMF
persists at both lines); "empty observed value already delivered by gh100+gh101" (98 residual — minor).

### V3 — Generator and runtime semantics (OBSERVED_IN_ARTIFACT unless noted)

| # | Item | Plan | Review | Evidence |
|---|---|---|---|---|
| 1 | Sink: appended, self-looping, `fail condition = state == countState`; both `ere:` and `fsm:` reach it; FSMMin minimises | C mechanism / **W** citation | C | `JavaFSM.java:112,135-142,158`; `LogicPluginFactory.java:296-309` → `EREPlugin.java:33-46` → `FSMPlugin.java:67-79`; `ere/FSM.java:53-58`. New: `JavaFSM.java:154-158` — a user state literally named `fail` is silently shadowed by `:158` |
| 2 | `@fail` fires after **every** event while in the sink; once per violation only because handlers `__RESET`; KPG (`jca:109-112`) has none → re-reports on every later event; entry point ignores the event method's boolean and dispatches on possibly stale flags | I (silent on re-fire) | C | `O99:2270-2285`, `:7395-7396`, `:7480-7486`; OFZ `:5443-5455` (KPG, no `reset()`) |
| 3 | `__RESET` → `this.reset()` clears state, lastevent = −1, flags; spec variables survive | C | C | `HandlerMethod.java:39`; `O99:7496-7500`; `BaseMonitor.java:786` once, `:950-968` |
| 4 | Fan-out of unbound events; root cloning; `getInstance("TLS")` under `jca` = 1 `UnsafeProtocol` + 2 mute + contamination; **and** the `__RESET` in the fan-out knocks every live SSLContext monitor back to `start` (state loss, not just variable overwrite) | **W** ("no UnsafeProtocol is emitted") | C, incomplete | `O99:15921-15942`, `:15975-15981`, `:16005-16008`; `BaseMonitor.java:760-769`; `gh99/…MonitorAspect.aj:662-674`; `O99:7449` |
| 5 | Event ids = declaration order; state ids from FSMMin (merges `start`/`unsafeAlg` in CipherSpec — 6 columns for 7 named states; `start`/`unsafeProtocol` in O101 SSLContext) | I | C | `O99:7503-7527`; `JavaFSM.java:70-77`; OFZ `:3591-3604`; `O101:7659-7663` |
| 6 | Scope at `@fail`: shape decided by unbound params (`BaseMonitor.java:248-250`); O99 15/8, OFZ 15/8, O101 18/5; portable `getState()/getLastEvent()` (`IMonitor.java:19,25`); at `@fail` `getState()` is the sink; pre-fail state stored nowhere (local `oldstate` in atomic `handleEvent`, OFZ `:5295-5306`); event arguments not visible; bound object only if copied into a field, or via `Ref_<param>` weak ref (synchronized only) | **W** on names | C (count 16→15) | as cited |
| 7 | `static final String[]` in the declarations block: viable by grammar path (`javamop.jj:1276,1611-1623`; `DumpVisitor.java:207,814-826`; `RVParser.jj:253-254` raw text; precedent `examples/ERE/SafeFileWriter/SafeFileWriter.mop:12`); no rvsec `.mop` uses a static field; caveat: a declaration line matching `event <name>(` would trip the raw-text regex | [inferred]#2 → viable | C | INFERRED from grammar; NOT_VERIFIED in an rvsec oracle |
| 8 | `RVM_loc` never assigned; enabling = rv-monitor + javamop + dexlib2. **New:** `__DEFAULT_MESSAGE` is an existing generator keyword and `HandlerMethod.java:39-47` is a 4-line substitution table — the natural place for a `__EVENTNAME`/`__PREVSTATE` keyword | [inferred]#4 → not a re-enable | C | `SuffixMonitor.java:27`; `Monitor.java:38,76-81,131`; `MonitorSet.java:766`; O99 grep = 0 |
| 9 | `condition()` stripped from the pointcut and inlined as prologue; monitor created/looked up first; `:600-612` dead | **W** citation, I mechanism | C | see V1 |
| 10 | End of trace: `terminateInternal` bare returns; any `@name` parses, unknown name NPEs at `BaseMonitor.java:332-334`; JavaMOP `endProgram/endThread/endObject` exist (`javamop.jj:356-358`, `EndProgram.java:64`, `EndObject.java` `finalize`), unused by rvsec, absent from dexlib2 (grep 0) | C | C | as cited |
| 11 | `--internalbehavior` (`Main.java:414`; `BaseMonitor.java:410-413,1065-1085`): per-monitor `List<String> trace` of **event names**, cloned with the monitor, unbounded, off by default — a ready-made trace-prefix mechanism | — | mentioned | new detail |
| 12 | `f1 = doFinal()` and `f2 = doFinal(..)` both fire on one call (post-merge wrapper `WFZ:147-152`; dexlib2 `PointcutMatcher.java:367-370` "standalone `(..)` matches anything"); with the `jca` automaton the pair yields one mute record + spurious reset after `init` (a correct verdict under CrySL, badly reported) and nothing after `update` | not listed | C | as cited |
| 13 | `GCMParameterSpecSpec.mop:23,34` two `c1`, `:48` `ere : c1 \| c2`; undefined ERE symbols pass generation silently (`FSMPlugin.java:55-64` checks the FSM output, where `c2` no longer appears) | — | C | new: matches the audit's `[tool]` fail-open list |

Implications for a `@fail` message (V3): portable = `getState()`, `getLastEvent()`, spec fields,
`this.getClass()`; compose **before** `__RESET`; "expected one of" needs the pre-fail state — one
bookkeeping line per event body (`prevState = getState();`, ~170 lines in `jca_android`) or a
few-line generator change (`RVM_prevstate` + `static final String[] RVM_eventNames`, or a keyword next
to `__DEFAULT_MESSAGE`); hand-named **event** tables are stable (declaration order), hand-named
**state** tables are not (minimisation).

### V4 — CrySL ↔ `.mop` fidelity (original 1.5.2 `CR`, api30 `A30`, audit; OBSERVED_IN_ARTIFACT)

Verdict codes: (a) translation deviation · (b) CrySL is strict, spec faithful · (c) ambiguous/oracle-dependent.

| Item | Plan | Review | CrySL / api30 / audit | Verdict | Who is right |
|---|---|---|---|---|---|
| Cipher `doFinal()` right after `init` (D05) | FP | conformant | `CR/Cipher.crysl:75-76,85` `FINWOU := f2\|f4\|f5\|f6\|f7; DoFinal := FINWOU\|f1\|f3;` ORDER `…(FINWOU \| (Update+, DoFinal))+`; `A30/Cipher.cryptsl:107-117` same; pilot `alfa_cipher.md:68` "corretos contra o ORDER" | **(b)** | Review |
| Re-`init` after a final (`end` no `i1/i2`) | FP | conformant | `Init+` precedes the finals group | **(b)** | Review |
| **Re-`init` before any update/final** (`s2` no `i1/i2`, `J:176-187`; `JA:302-310`) | — | — ("spec is faithful") | `Init+` (`CR:85`), `Inits+` (`A30:117`); pilot ALFA-CIP-01 "re-init é uso comum e legal"; CIP REPROVADA G3 | **(a) [jca], persists [gh101]** | Neither; the audit. Review's "faithful" is **wrong for the ORDER as a whole** |
| **Multi-`update` before `doFinal`** (`s3` no self-loop, `J:188-195`; `JA:311-317`) | — | — | `Update+`; pilot ALFA-CIP-02 "streaming multi-chunk" | **(a) [jca], persists [gh101]** — realisable FP on the most common streaming pattern | Neither |
| wrap × doFinal mixing; `updateAAD` absent from both alphabets | — | — | `WKB+ \| (…)+` exclusive; `AADUpdate*`, `noCallTo[AADUpdate]` (`CR:66,85,118`) | **(a) FN** | Neither |
| SecureRandom `nextBytes` twice (D03) | FP | C, open in both | `CR/SecureRandom.crysl:36,39` `Ins, (Seed?, End*)*`; `A30:57` `Ins, Seeds?, Ends*`; GAMA-SRD-01 executed (`gama_report.md:236-246`) | **(a) [jca], persists [gh101]** | Both |
| 12,400 rows attribution | "spec emits nothing else" | `next2` FP | audit H-SRD-1 pending replay | INFERRED; V5 adds two more mechanisms (see V5) | Review better supported; label INFERRED |
| `KeyPair` keyed on constructor (D06) | FP | conformant (`KeyPair.crysl:19`) | `CR/KeyPair.crysl:19-20` `Con, (GetPubl \| GetPriv)*` — mandatory; **`A30/KeyPair.cryptsl:12-13` `co?, (pu*, pr*)*` — optional**; KPR G3 FAIL "`co?` made mandatory … executed, critical" (`juiz_sintese_batchB.md:376-385`); §9 "KPR `co?` restoration" | **(c) vs original / (a) vs api30** | Both half-right; neither cites api30's `co?`, decisive for `jca_android` |
| `MessageDigest.reset` (D04) | FP | C | no `reset` in `CR`/`A30`; removed in `jca_android` | **(a) [jca]**, closed | Both |
| TMF/KMF asymmetry; `:62-63`; Signature `byte` (D07/D08 open in both) | C | C | `CR/TrustManagerFactory.crysl:18,21-22`; `CR/Signature.crysl:36-37,44-45`; SIG G5 FAIL | **(a)** | Both |
| **`SSLContext.createSSLEngine` declared `void`** (`J/SSLContextSpec.mop:64`; `JA:90`) — real return `SSLEngine` | — | audit item only | `CR/SSLContext.crysl:21-22,25-26`; SSL G5 FAIL "Engine channel dead on BOTH weave halves" | **(a) [jca], persists [gh101]** — a fourth never-matching pointcut, missing from the plan's register | Neither |
| SSL `end [engine -> end]` vs `Engine?` | — | — | `CR:26` | **(a) FN** | Neither |
| PBE 1000 vs 10000 (D18/D19) | C | C | `CR/PBEKeySpec.crysl:24`, `CR/PBEParameterSpec.crysl:17` require ≥ 10000; `A30` same | conditions faithful; **message text (a)** | Both |
| **PBEKeySpec requires `RANDOMIZED(password)`** (`J/PBEKeySpecSpec.mop:37-40,55-59`; `JA:42-44,61`) | — | — | `CR/PBEKeySpec.crysl:28-29` REQUIRES only `randomized[salt]`; PBK G4 FAIL FEN-PBK-SENHA-EXTRA (`juiz_sintese_batchB.md:398-407`) | **(a) [jca], persists [gh101]** — every legitimate password-based PBEKeySpec is accused | Neither |
| PBEKeySpec FORBIDDEN ctors reported as `InvalidSequenceOfMethodCalls` (`J:20-30`) | sites only | — | `CR/PBEKeySpec.crysl:9-11` FORBIDDEN → CogniCrypt `ForbiddenMethodError` | wrong `ErrorType`; **no `ForbiddenMethod` type exists** | Neither names the category gap |
| `CipherTransformationUtil` rejects 8 `PBEWithHmacSHA*AndAES_*` (D15) | C | C | `CR:90-105` accepts; **`A30:121` catalogue lacks the PBE family** | **(a) vs original; (b) vs api30** | Both, api30 nuance missing |
| `CCM` accepted (`:33,42`); `AES/ECB` rejected; GCM/CTR empty padding | — | CCM, padding | `CR:97` no CCM (→ FN); `CR:97` no ECB (→ **rejecting is faithful**; `A30:129` admits ECB, JA util follows); `CR:113` `NoPadding` for GCM/CTR — depends on CogniCrypt's `pad()` on 2-part transformations | CCM (a) FN; ECB (b)/(a); padding **(c)** | Review's "extra" defensible, not established |
| **`AndroidKeyStore` flagged (D17, sev A)** | translation defect | C | `CR/KeyStore.crysl:52` `{JCEKS, JKS, DKS, PKCS11, PKCS12}` — `jca` is **byte-faithful**; `A30/KeyStore.cryptsl:89` `{AndroidKeyStore, PKCS12, BKS, BouncyCastle, AndroidCAStore}` | **(b) vs original — oracle choice**, (a) only vs api30 | Plan misclassifies; review does not correct |
| MD5/SHA-1, `SSL`/`TLSv1` (D-1) | bias note | §7 item 10 | `CR/MessageDigest.crysl:37`, `CR/SSLContext.crysl:29` faithful; `A30:31`, `A30:21` allow them; §7 item 10 "5,891/6,048 historical UnsafeAlgorithm lines name algorithms the raw api30 oracle does not forbid" | **(b) vs original; oracle shift vs api30** | Both |
| RANDOMIZED marks the argument (D12) | C | C | `CR/SecureRandom.crysl:33,53` `randomized[randIntInRange] after nIR` — the return value; `A30` has no `nextInt` events; SRD G7 FAIL "marks granted from violating/unsafe instances" | **(a) [jca], persists [gh101]**; audit's fail-path finding stronger than either states | Both |
| D-4 prerequisite (REQUIRES without producers) | claimed | not contested | `CR/Cipher.crysl:133-141`, `CR/KeyPairGenerator.crysl:34-38`; producers `SecretKeyFactory.crysl`, `ECGenParameterSpec.crysl:25`, `RSAKeyGenParameterSpec.crysl:19`, `DSAGenParameterSpec.crysl:25`, `DHParameterSpec.crysl:21` **and `DHGenParameterSpec.crysl:18`** | CONFIRMED with one correction: DH has a producer (`J/DHGenParameterSpecSpec.mop:36` writes `PREPARED_DH`); no `.mop` for the other four; `Property` has `PREPARED_DH`, no `PREPARED_EC/RSA/DSA` | Plan right in substance |
| CogniCrypt categories vs `ErrorType` | mapping | UNVERIFIED lines | `TypestateError.java:41-63`; `RequiredPredicateError.java:42-55`; `IncompleteOperationError.java:59-74`; `ConstraintError.java:58-119`; `ForbiddenMethodError.java:43-54`; `ErrorType.java:3-10` = 6 values | no `RequiredPredicate`, `IncompleteOperation`, `ForbiddenMethod`, `NeverTypeOf/HardCoded` | Plan's mapping stands; lines now verified |

Audit per-spec verdicts (all REPROVADA in covered scope) with headline reasons are tabulated in
`scratchpad/v4/v4_report.md`; the audit's "carrier FP" in almost every G3 is the plan's L2, reached
independently and executed.

### V5 — Weaver and localisation

| # | Item | Plan | Review | Evidence |
|---|---|---|---|---|
| 1 | Wrapper key `(class#name(params)return)`; pre-fix bare `put` (last write wins); today guard throws (`DexWeaver.java:170-176`) and `WrapperEmitter.java:246-273` merges by `registryKey`; pre-fix TMF `W92:588-616` `g1`/`g2`/`g3` on the `(String)` key, `g3` last; census 96/84/10/12 (`gh100/tasks.md:74`); **all 11** `getInstance(String)` specs collide (review's "ten of the eleven" is I: SecureRandom has 1 `(String)` + 2 `(String, ..)` → still 3 wrappers on one key; pre-fix winner was the orphan `g4`, `W92:439-489`) | K | C / I | OBSERVED + `git show 48b57fc5^:…DexWeaver.java:159` |
| 2 | Fused-advice truncation: 9 events / 8 emitters dropped (`census_pre_repair.json`), all nine in the plan's orphan table; mechanism `EmitContext.java:52 getMonitorCalls().get(0)` | K | C | OBSERVED |
| 3 | 8,371 / 643 / 9,015 (pre-gh100): `gh56-smoke:8835-8843` (`g1` tests before assigning), `:8877-8896` (`g3` writes then sinks), `:16327-16345` (root fan-out), `initEvent` clones root; consistent with all counts | [inferred]#1 | C | OBSERVED; INFERRED for registration order |
| 4 | 12,400 SRD rows: both hypotheses put the frame at a `nextBytes` site, so the profile cannot discriminate (review I on "does not fit that profile"); **new**: pre-fix the `(String)` key belonged to orphan `g4` → `getInstance("SHA1PRNG")` created the monitor and left it in `start` → first `nextBytes` accuses; and `next2Event` creates monitors (`gh56-smoke:14939`+31) → objects created outside the DEX accuse on first `nextBytes` — three coinciding mechanisms; CSV lacks object identity to split them | I | I | INFERRED |
| 5 | Return type exact unless `*` (`PointcutMatcher.java:361-364`), varargs `:370-373`; wrapper `expandCallTarget :383-395,444-453`; `doFinal(..)` also matches `doFinal()` (post-merge `WFZ:147-152` fires `f1` then `f2`; pre-merge `f2` won) | C | C | OBSERVED |
| 6 | Clone route: `RegisterShifter.java:174-176` empty ctor; `grep DebugItem` = 0; `DexFileMutator.forMethod:129-130` copying ctor; callers `CoverageWeaver.java:155-167`, `DexWeaver.java:657`, `RegisterAllocator.java:44` (only `AfterThrowingEmitter` requests scratch), `InstructionInjector.java:359`; descriptor: 115 advices = 64 after-returning + 33 after + 18 before, 0 throwing/if/staticinit → only coverage spill clones; no spill counter (`CoverageReport :194-196`). **MEASURED (n=1, `dexdump`, `com.owncloud.android_48000100` original vs `gh101_group8_jca_android/instrumented_apks/`)**: 136,982 common methods; 4,859 (3.9 %) lose all line positions, 0 gain; overwhelmingly `<init>` and one-liners; **0 of 693 methods invoking `mop.MonitorWrappers`/`MultiSpec_1RuntimeMonitor` lost lines**. Plus E3: 100 % of rows carry a line | I ("highest-value") | C ("plausibly small") | MEASURED |
| 7 | Scope: 12 vs 16 prefixes; per-class hoisting `DexWeaver.java:359-374`; no CLI scope option | C | C | OBSERVED |
| 8 | Site recoverability: loop has `classDef/method/idx/MethodReference`; `SignatureFormatter.java:27-40`; `CoverageWeaver.java:181-186`; `ThisJoinPointEmitter.java:5-16` weave-time constant channel; `MonitorInvokeBuilder.java:160-170,235-250`. Manifest join: runtime frame is `(class, method, file:line)` with no callee — ambiguous when one method holds two monitored calls (`getInstance` + `init` — the common case); unique only with the event name added to the report or the line | C | C | OBSERVED |
| 9 | `ViolationRecorder.java:37-39` `new Exception()` per report attempt, evaluated as the `addError` argument (before `errors.add`); `:53-60`; `:87-105`; `MonitorBuilder.java:86-101` no `-g`; D44 confirmed (50 `getLineOfCode`, 0 `record`) | C | C | OBSERVED |
| 10 | Audit toolchain items still open on `modules`: first-call disjunct (`WrapperEmitter.java:507-527` left-most `CallPC`); declared-only index (`AndroidClassIndex.java:111-127`); **varargs `args()` narrowing ignored (`ArgsPC.java:49-56`; `PointcutMatcher.java:269-271`; wrapper expansion `:383-384` accepts every overload with ≥ head params)**; nested types (`TypeResolver.toDescriptor` `KeyStore.Entry` → `Ljava/security/KeyStore/Entry;`); `android.jar` selection on the Python side (NOT_VERIFIED here) | — | listed | OBSERVED |
| **11** | **E3 residual in `TrustManagerFactorySpec` — mute at both lines, no twin, no `found .`.** Spec: `g1 :29-31 getInstance(String) && args(alg) && condition(algorithms.contains(alg))`; `g2 :37-39 getInstance(String, ..) && args(alg, *) && condition(algorithms.contains(alg))`; `g3 :45-47` binds `k`; automaton `:69-79` `start[g1,g2 → waitingInit] waitingInit[init → final] final[g1,g2 → waitingInit; gtm1 → start]` — **`waitingInit` has no `g2` row**. Tables `OFZ:8797-8801` `g1 = {2,2,3,3}`, `g2 = {2,2,3,3}`, `g3 = {3,3,3,3}`, `init = {3,3,1,3}`. Merged wrapper `WFZ:538-544` calls `g1Event`, `g2Event`, `g3Event` in sequence — **PROVEN** in the E3 corpus (`app.pachli_50.apk` `classes24.dex`, `Lmop/MonitorWrappers;.javax_net_ssl_TrustManagerFactory_getInstance` → `invoke-static …_g1Event`, `_g2Event`, `_g3Event`, `dexdump`), because dexlib2 expands `(String, ..)` to every overload with ≥1 param and never applies the `args(alg, *)` arity (audit `FEN-SET-VARARGS-ARGS-IGNORED`). Runtime for `getInstance("PKIX")` at line A, `init` at line B: `g1` → `0→2`; `g2` → `2→3` sink → `@fail` → **mute at A** + `__RESET`; `g3` → condition false; `init` on state 0 → `init[0] = 3` → **mute at B**; body silent (`PKIX` allowed) → no `UnsafeAlgorithm`, no `found .`. Predicts 2 `unknown` per correct flow, 0 twins, 0 `found .` — **matches V2b** (2,855, 98 % twin-less, 0 `found .`). MEASURED over OFZ: for CIP/KGN/KMF/KPG/KST/MAC/MDG/SSL/SRD/SIG/TMF, `transition_g2[transition_g1[0]]` is the sink → **under the merged wrapper, correct single-argument `getInstance` flows never reach `final`/`@match` in 11 of 23 `jca` specs**. Provenance: `[jca]` overlap of `(String)`/`(String, ..)` events + missing self-loops, exposed by the `[tool]` merge on top of the `[tool]` arity defect. `jca_android/TrustManagerFactorySpec.mop:44-47,129-133`: `g3` fixed (binds `mf` → `unsafeAlg`), the `g1+g2 → sink` overlap **not** | — | **W** ("PKIX case closed by the merge") | PROVEN (DEX) + MEASURED (tables) + INFERRED (runtime, no device replay) |

### V6 — Python pipeline, contracts, consumers (PROVEN where executed)

| Claim | Plan | Review | Verdict | Evidence |
|---|---|---|---|---|
| Format 1 suffix discriminator, no `else`; fabricates `error_type := spec`, `source` = file only (line parsed at `:391` and dropped) | C | C | CONFIRMED / PROVEN | `logcat_parser.py:305-316,386,391,397` |
| Format 2 7 fields, `parts[6:]` rejoined, `parts[2]` discarded; <6 parts falls through | C | C | PROVEN | `:322-349` |
| Format 3 needs `dot_idx`; `source := "Unknown Source:1"`; `[helper]` rows dropped (D32) | C | C | PROVEN | `:355-368`; probe → `None` + warning |
| `\n` in message | "orphan half dropped with a warning" | "fabricated second record" | **plan IMPRECISE, review CONFIRMED with one precision**: continuation with ≥5 commas → fabricated Format-2 record (spec = first token, `error_type` = sixth token — a bogus type enters `unique_msg`); with a `class.method(` prefix and `:::` → Format 3; otherwise `:371` warning, no counter. Bare `state=2:::event=g1` is **dropped**, not Format 3 | PROVEN by probe; logcat re-prefixing on device INFERRED |
| `:::` in message poisons `unique_msg` | — | C | PROVEN: 6 parts; gh103 `read_errors_csv:252-256` → `violation_type=""`, `unparsed += 1` (row kept) | — |
| `unique_msg` 5-way; no Python dedup; `unique_errors` set | C | C (file path I) | CONFIRMED — the file is `rv-android-core/.../domain/coverage.py:563-576`, not `rv-coverage/.../coverage.py`; `errors.csv` writes every row (`result_processor.py:614-651`) | — |
| 11-column header, INV-PLT-19 "MUST NOT be changed", exact test | C | C | PROVEN: `test_errors_csv_header_carries_source_after_method` **passes** on `modules` (2 passed); `platform/spec.md:192` | — |
| New columns break INV-PLT-19, the test, gh103 `read_errors_csv` (`ValueError`) | — | C | CONFIRMED (`violations.py:63-75,243-247`). **And**: gh103 already extracts `violation_type = parts[3]` (`:252-254`) and reads `source` as `location` (`:262`) — WS-6.2/6.3's motivation is stale for the analysis layer | — |
| `clock_logcat_join` `split(",", 6)` tolerant | — | C | CONFIRMED (`:455-462`); a `\n` continuation would inflate per-step counts by one | — |
| Consolidators regex `\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$`; frozen INV-APV-55 | — | C | CONFIRMED (`experimento-cal/scripts/consolidate_cal.py:75`, `verify_iteration.py:56`, `experimento-20260721/scripts/consolidate_compare.py:35`, **`experimento-comp162/scripts/consolidate.py:46`** — live, not in INV-APV-55's list); continuation lines and any spec not ending in `Spec` (`RandomStringPassword`) are excluded → E3 `mop_total` and aperv-tool's INV-CAN-04 count differ by construction | — |
| `TraceComparator` `EXPECTING_INDEX=6`, tolerant | — | C | CONFIRMED (`validator/.../TraceComparator.java:111,733-737`) | — |
| `generic_new` absent from CLI; static path silently analyses `jca` for `jca_android` | C | C | CONFIRMED (`__main__.py:443`; `rv_experiment/config.py:918-951`; `rv_static_analysis/config.py:199-208`) — still open | — |
| No invariant mentions the literal `unknown` | — | C | CONFIRMED (grep) | — |

Breakage table for every proposed change (V6): (a) rich comma-bearing message as last field — nothing
breaks in-band, but the "last positional field" rule is undocumented (add to INV-ANA-08); (b) `\n` —
fabrication/drop as above, consolidators undercount, aperv-tool overcounts; (b′) `:::` — 6-part
`unique_msg`, gh103 `unparsed`; (c) new columns — INV-PLT-19, the header test, gh103 raise; **or skip**
(gh103 already derives `violation_type`; `is_library` derivable offline from the campaign manifest,
INV-ANA-58); (d) sentinel — INV-ANA-46 golden output for fixtures with Formats 1/3; (e) message in
device identity — counts and `mop_errors_unique` rise, `ErrorDescriptionTest.java:179-220` flips;
(f) structured id — bounded; an 8th comma field before `message` breaks nothing only if comma-free, after
`message` it is swallowed by every consumer; (g) JSON message — fine positionally (PROVEN), same `\n`/`:::`
caveats; (h) error-code table — `unique_msg` cardinality drops, INV-CORE-41 comment stale.

### V7 — Real state of prior work (MEASURED from git/artifacts)

| Item | State today |
|---|---|
| gh100 | open, not archived; `tasks.md` **55 [x] / 3 [ ]** (7.4–7.6 verify/review/docs-sync); nothing open touches messages |
| gh101 | open, not archived; **84 [x] / 0 [ ]**; freeze gate `tests/parity/test_gh101_specset_gates.py` (5 tests) **passes today** (PROVEN); `git diff 7e7acb69 -- …/jca` empty; **the revert `e204e2a4` is recorded nowhere in gh101** (`tasks.md`, `proposal.md`, `design.md`, `data/gh101/README.md`, `frozen_set_debt.md` — `README.md:255-300` still documents the identity store as live); `divergence_record.csv` 106 rows, kinds `layer-2-repair` 51 / `predicate-graph` 42 / `allow-list` 12 / `cipher-import` 1 (gh101's vocabulary, not the audit's `[jca]/[gh101]/[tool]/[oracle]`) |
| INV-INS-109..115 | **exist only in the gh101 delta** (`openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md:43-57`); `openspec/specs/instrumentation/spec.md` tops out at INV-INS-103; INV-INS-110 ("an event in the event list MUST appear in `fsm`/`ere`") has **no test** in `tests/parity/` |
| Orphans | `jca` 18 (own script) · `jca_android` 0 |
| Audit | closed, NOT READY, 22/22 REPROVADA, gates 2 PASS / 2 INC / 10 FAIL; `HANDOFF_PROXIMA_SESSAO.md` is a stale mid-audit handoff |
| Study 03 / comp162 | **executed 2026-08-13** (8 containers; `errors.csv` 13:57–15:14; `consolidado/per_rep.csv` 1,455 rows = 162 × 3 × 3 minus 3); instrumented corpus `/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/` = 162 APKs; `experimento-comp162/README.md:182-193` "Estado" stale; E3 register open items P1–P3, P5, P6, P10–P12 (`registro_execucao_prontidao_e3.md:610-640`) |
| gh102 / gh103 | 28/28 open · 48/49 open; gh103 `design.md:54` names `errors.csv`/logcat as inputs; contract in `aperv-tool/analysis/violations.py` |

Audit findings relevant to messages/diagnostics **cited by neither document**: G9 FAIL evidence
EXEC-SET-25 ("5 of the 14 drive records carry `expecting=unknown`, exactly accompanying the executed
FPs", `juizglobal_relatorio.md:231`); §5 item 6 "KPG NPE annihilates records (only 16 historical
lines)" and "13 specs with zero historical emission never adjudicated" (`:395-401`); the G9 families
"displaced/false accusations", "missing channels", "10× message" (`set/set_cons_report.md:420`,
`batchD/juiz_sintese_batchD.md:379,498,531`); §6.1 risk 6 "diagnostic non-attribution … prevents
clause-level attribution" (`:445-447`); the pilot's serialisation chain incl. the **~4,068-byte logcat
payload truncation risk (NÃO_VERIFICADO)** (`pilot/gama_diagnostico.md:90-105`); ALFA-PBE-05 "no
forbidden-method `ErrorType`" (`batchA/alfa_report.md:191-193`). Cited by the review only: dedupe probe
`3a658775…` / EXEC-SET-24, §9 (i)/(ii), §7 items 4/6/10.

### V8 — Design and proportionality

- **Sequencing:** the re-baseline is not a future step; it is computable now and its headline is in
  V2 above. Older 11-column `errors.csv` under `results/` are toy (`gh90_smoke` 9 rows).
- **Phase A coherence:** `ErrorType.java:3-10` (six values) is in `rvsec-core`, shared by both sets and
  both loggers → WS-3.1 is radius C; and gh101's own rule for shared-runtime repairs
  (`gh101/specs/instrumentation/spec.md:99` "MUST apply identically to both sets … effect on the frozen
  set MUST be enumerated site by site") would bind it. Plan incoherent; review right.
- **WS-1 minimal body (illustration only, not applied):** 4-arg ctor, `getLastEvent()` indexed into a
  declaration-ordered event-name array, spec variables, object class, composed before `__RESET`. Carries
  Q1, part of Q2, Q5; cannot carry pre-fail state, legal continuations, event arguments; spec variables
  may be stale from a previous sequence on the same monitor. Drop the identity hash. A generation-time
  check "event count == array length" belongs with INV-INS-115.
- **WS-2 options:** gh101 chose A (Kleene prefix / `unsafeAlg`) for 15 orphans and B (remove) for
  `MessageDigestSpec.reset` (`gh101/design.md:166-190`, D-S9); recorded residue "the accusation reappears
  one call later" (audit §7 item 4). Generation cost is driven by event count only
  (`design.md:250`, `data/gh101/README.md:551`: 17 events 53 s / 3.3 GB, 18 → StackOverflow; CipherSpec
  re-budgeted 17 → 14, `tasks.md:111`) — A/C add none, B removes. **New spec-only alternative neither
  document weighs:** the `fsm:` grammar's per-state `default` transition (`FSMParser.jj:93,149`;
  `JavaFSM.java:113-120` replaces the sink for every unlisted event of that state); unused in either set
  (grep 0); not available to `ere:` specs; must be paired with an INV-INS-110-style check because it
  also swallows genuinely illegal events.
- **Volume model per site** (`(spec,type,class,method,line)`): (a) message outside identity → 1 record,
  arrival order picks the text (criterion 6 unmeasurable in-process); (b) message inside identity →
  ≤ distinct message values (bounded by allow-list size; unbounded with an object hash); (c) structured
  event id inside identity → ≤ |alphabet| ≤ 17, in practice 1–3. Recommend (c), which is what the audit's
  §9 (ii) "clause/constraint id" asks.
- **Acceptance criteria:** 1, 2, 3, 4, 8 verifiable offline; 5, 6 need `rv-experiment run` on a
  micro-APK; 5 is the wrong target for the Cipher rows (CrySL); 2 is not "already delivered" (98
  residual rows); 7 can be proven **statically** on Android (return type is matched exactly, so a weave
  census on a micro-APK proves the pointcut fix without running).
- **T0/T1 cut:** right in shape; premise "fold WS-1 into audit item (i)" presumes the post-E3 set is a
  repaired `jca_android` — a third option exists (a successor set derived from frozen `jca` with the
  minimal patches; compatible with INV-INS-109 as written, which freezes "the `jca` specification set …
  at this change's base commit", but colliding with INV-INS-112/113's derivation discipline and creating
  a third conformance ledger); researcher's decision, not surfaced as such by the review. Missing from
  T0: the E3 re-baseline script; **`rvsec-mop` has no `src/test`** (`ls rvsec/rvsec-mop` → `pom.xml src target`) —
  the "content rule test over `.mop` bodies" needs a home (precedent: `$RVA/tests/parity/`); a
  generation-time array/alphabet consistency check. Order: split T0.3 into T0.3a (syntax bans, now) and
  T0.3b (shape, after T0.5); bundle T0.4 with T0.3a (alone it is dead code by P3).
- **Proportionality:** T1.3 ≈ 21×3 + 21 array lines per set; WS-1.5 4 lines; WS-7 items 1–5 ≈ 10 lines
  in 7 files; WS-2.4 1 line; WS-3 ≈ 60 lines + automaton co-design per spec (27 `condition()` reads,
  `design.md:322`).

### V9 — Audit of the review itself

Thirteen review-only factual claims re-opened ((a)–(m) in the V9 brief): all CONFIRMED verbatim
(`jca/MessageDigestSpec.mop:57` commented; `Property` 25; `generic_new` 39; `ErrorDescriptionTest:180,197,210`;
no invariant names `unknown`; `RVParser.jj:303-312` + `BaseMonitor.java:332-334`; `EndProgram.java:64`,
`EndObject.java:17,70,76`, dexlib2 grep 0; deprecated `remove(Property)` at `ExecutionContext.java:52-53`
called at `MacSpec.mop:87`, `KeyManagerFactorySpec.mop:91`, `TrustManagerFactorySpec.mop:87-88`;
`CipherTransformationUtil.java:33,37-38`; `gh56-smoke:8835-8843`; `ErrorCollector.java:11-22`
unsynchronised; `O101:7659-7663`; `HMACParameterSpec` absent from `android-37/android.jar`;
`@severity` inside javadoc `generic_new/CharSequence_NotInSet.mop:17`). §8 omits many files the body
relies on (`javamop.jj`, `RVParser.jj`, `IMonitor`, dexlib2 helpers, `coverage.py`, `test_result_processor.py`, …)
and **never opens `MetaCrySL/generated/api30`** (0 mentions) — the one substantive gap.

Bias patterns: directional asymmetry (answers an unmeasured plan claim with an unmeasured counter-claim
— L5c "plausibly small"; now measured, it happened to be right); numbers without a replication path
(all now reproduced by V2, so the concern is resolved but the practice was wrong); selective firmness
(hedged in the body, firm in §0 — 12,400 rows "is" the `next2` FP; "matches exactly" for a mechanism
never replayed); single-oracle CrySL judgement; recommendation creep (T0/T1, "fold into audit (i)",
"structured id", "`is_library` offline" — the last needs the campaign manifest, not `errors.csv` alone).
Left open when closable: D44 (now confirmed), `TypestateError`/`RequiredPredicateError` lines (now
confirmed), `Platform.kt` provenance (still NOT_VERIFIED — okhttp source not in the workspace); never
re-checked the plan's `e3_decisiva_05`/`exp_00` figures nor L5f's zero-counts. Internal tension: T0.5
(identity in `ErrorSummary`) is a device-side behaviour change and therefore post-E3 only, which §5's
"do not split E3" row does not say. Format against the handoff §3.2: all deliverables present.

**Overall:** trustworthy on §1–§4 mechanism corrections; its §0 numbers are now MEASURED-confirmed; its
prior-work account is right except the revert record and the E3 timing; its CrySL verdicts are
incomplete (api30, `Init+`/`Update+`); its §6 cut is one admissible option.

---

## 4. Corrections needed

### 4.1 To the plan (kept separate; §-references are the plan's)

1. §0/§1/§5/§6 — add a "prior work" section: gh100 (weaver merge `48b57fc5`, 9 restored events; open
   55/58), gh101 (rewrite of `jca_android`, freeze of `jca` at `7e7acb69`, open 84/84, INV-INS-109..115
   in its delta spec only), the revert `e204e2a4` (unrecorded in gh101), the audit (NOT READY, 22/22;
   §7 ten rulings; §9 patch areas), Study 03 (D1 `jca`, D3 weaver kept, D4 store reverted; **executed
   2026-08-13**). State which campaign "next" means; today no `.mop` edit is admissible.
2. §1 — drop "73.4 %"; replace "28" by the range 24–53 with the definition per value; "3,465×"
   accordingly; "163 apps" → 113 with ≥1 error of 163; "perfect synonyms" holds only pre-gh100 (E3: 419
   `UnsatisfiedConstraint` `unknown` rows).
3. §2.2 — name the pairing definition (min-pairing) and note co-location gives 33.4 %; `time` is
   seconds; §2.4 — 85.44 % needs `okio.`, 88.01 % is the 2-segment prefix; §2.5 — 11,761 is the excess
   count; largest 10-column group is 6, 3,098 is the 5-column key; the 1,542/24-timestamp figures come
   from other result dirs.
4. §3-L2 — `fsm/FSMMin.java` → `JavaFSM.java:112-142,158`; SSLContext row: `UnsafeProtocol` **is**
   emitted, plus two mute records, plus fan-out that resets every live SSLContext monitor; Cipher rows:
   `doFinal()` after `init` and re-`init` after a final are CrySL semantics — but `init;init` and
   multi-`update` **are** translation defects (audit ALFA-CIP-01/02); KeyPair row: conformant to the 1.5.2
   rule, non-conformant to api30 (`co?`), unobservable on Android when `new KeyPair` runs in platform
   code; add fan-out/cloning, truncation and wrapper collision as dataset mechanisms; add the E3
   `g1+g2 → sink` mechanism (V5 item 11).
5. §3-L3 — replace `:604-610` with `RVDumpVisitor.java:47-51` + `EventDefinition.java:151-156`; the
   monitor is created before the test; `Property` = 25; the `jca_android` predicate graph is reconnected
   (11 write-only, 0 read-never-written) but `generatedCipher` is broken by the revert.
6. §3-L5 — L5c: real (3.9 % of methods on one APK) but 0 % of woven methods and 100 % line coverage on
   E3 → not "the highest-value single fix"; L5b: `is_library` is derivable offline from the campaign
   manifest without WS-5.1/5.2.
7. §3-L7 — the `\n` case fabricates (≥5 commas) or drops (≤4); the escape function is buggy and the
   commented call quotes the whole line; `generic_new` `Log.v` = 39; the JSE csv collector escapes then
   trims; `err.getExpecting().trim()` NPEs on `null`.
8. §3-L8 — `TrustManagerFactorySpec.mop:63` (+`:62` double array); add `SSLContextSpec.mop:64`
   (`createSSLEngine` declared `void`) to the never-matching set; D17 is an oracle choice (byte-faithful
   to `KeyStore.crysl:52`), reclassify; add PBEKeySpec's extra `RANDOMIZED(password)` requirement and
   the FORBIDDEN-as-InvSeq category defect; `.aj` lines come from a git-ignored generated file.
9. §4 — `getState()`/`getLastEvent()`; pre-fail state lost; compose before `__RESET`; atomic vs
   synchronized (15/8 in O99, 18/5 in O101); "seven handlers read spec variables", not the fields; the
   `Ref_<param>` weak ref may be null in the handler (V1 N2).
10. §5 — WS-1 as revised (§3-V3 implications; drop the hash; event names by hand, states never); WS-2.1–2.3
    done in `jca_android`, 2.5/2.6 removed, add "verify INV-INS-110" and the `default`-transition
    alternative for `fsm:` specs; WS-3.1 radius C and the Phase A sentence fixed; WS-3.2 co-designed with
    the automaton; WS-4 radius M+I; WS-6.2/6.3 partly moot (gh103 derives `violation_type` and reads
    `source`); WS-6.6 rewritten (fix, do not re-enable); WS-6.1 → structured id; add the message-content
    rule, the parser-side counter, the synthetic-suite workstream, and the E3 re-baseline as step 0.
11. §6 — D-1 decided for Study 03 (`jca`) and open for the campaign after (audit §7); D-2 already made
    (gh100 kept); D-3 cost corrected; add the researcher decision "repaired `jca_android` vs successor to
    `jca`".
12. §7 — criteria 2, 5, 6 reworded; 7 provable statically on Android.
13. §8 — D02 (9 never fired; all 18 closed in `jca_android`), D05 W, D06 I, D11 latent (`g1` grouped before
    `g4` on one advice, OFZ aspect `:459-465`), D17 oracle, D34 18/11; add: fan-out/cloning contamination,
    truncation, wrapper collision, escape bug, `null` `expecting` NPE, `GCMParameterSpecSpec` `c1`/`c2`,
    KPG `@fail` without `__RESET` as a volume defect, `createSSLEngine` `void`, PBEKeySpec
    `RANDOMIZED(password)`, `g1+g2 → sink` under the merged wrapper, `Init+`/`Update+` untranslated,
    `updateAAD` absent, SSL `engine*` vs `Engine?`.
14. §9 — the four inferred claims replaced by their resolutions (V3 items 7–8; V5 items 3–4; WS-4 still
    unmeasured).

### 4.2 To the review (§-references are the review's)

1. §0 — "gh101 records it [the revert] and stays open" → **nothing in gh101 records `e204e2a4`**;
   `data/gh101/README.md:255-300` still documents the identity store as live; the obligation to record it
   is in `plano_prontidao_estudo03.md` §2 ("deve registrar essa reversão") and in the revert's commit
   message, unfulfilled.
2. §0/§4 — "for `jca` runs (Study 03) the PKIX case is closed by gh100's wrapper merge" → **wrong**: the
   merge makes `g1` and `g2` both fire on every single-argument `getInstance`, `waitingInit` has no `g2`
   row, and the flow sinks twice (V5 item 11; E3: TMF 2,855 mute, 0 `found .`); this holds for 11 of the
   23 `jca` specs on the OFZ tables. Add it to §5's risk table as an E3-validity item.
3. §1-L2 (c)/(f) — "the spec is faithful" for `CipherSpec` → faithful on the `doFinal`-without-`update`
   row and on re-`init` after a final; **not** faithful on `Init+` (no re-`init` before a final) and
   `Update+` (no multi-`update`) — audit ALFA-CIP-01/02, `juiz_sintese.md:193`.
4. §1-L2 (e) and everywhere CrySL is invoked — cite the api30 oracle: `A30/KeyPair.cryptsl:13` `co?`
   makes D06 a deviation for `jca_android`; `A30/KeyStore.cryptsl:89`, `A30/MessageDigest.cryptsl:31`,
   `A30/SSLContext.cryptsl:21`, `A30/Cipher.cryptsl:121,129` bear on D17, D-1, D15 and the ECB/CCM points.
5. §0 table / §1 §4 — O99 is **15/23** atomic, not 16/23; the root clone is `O99:15992`, not
   `:15921-15938`; the review's `coverage.py` is `rv-android-core/.../domain/coverage.py:563-576`;
   `SecureRandom.crysl` ORDER expression is at `:39`.
6. §1 §7 criterion 2 — "already delivered by gh100 + gh101" → 98 residual `but found .` rows on E3;
   keep as a regression check, not as done.
7. §3.2 / §6 T0.1 — E3 has already run; T0.1 is executable now, offline; the "mid-campaign split" risk
   applies to future runs only; add that T0.5 is a device-side change (post-E3 only).
8. §3.7 — the untracked `.aj` is git-ignored; INV-INS-109..115 live only in the gh101 delta spec and
   INV-INS-110 has no test; add the E3 consolidator (`experimento-comp162/scripts/consolidate.py:46`) to the
   regex-consumer list; note the "13 zero-emission specs" and KPG-NPE evidence-annihilation findings of
   the audit; note the `~4,068-byte` logcat payload bound from the pilot.
9. §1-L2 K — "the discarded `getInstance` wrapper does not fit that profile" → both hypotheses put the
   frame at a `nextBytes` site; the pre-fix `(String)` key belonged to the orphan `g4` (`W92:487-489`),
   which leaves the monitor in `start`; and `next2Event` creates monitors for objects born outside the DEX
   — three coinciding mechanisms; keep the attribution INFERRED until G10-SRD-1.
10. §4 L5c — replace "plausibly small" by the measurement (3.9 % of methods, 0 % of woven, one APK; 100 %
    line coverage on E3).
11. §6 — surface the third target-set option (successor to `jca`) as a researcher decision; add the E3
    re-baseline script, the `.mop`-content-test home (`rvsec-mop` has no `src/test`), and the
    array/alphabet check; split T0.3; bundle T0.4.
12. §8 — list every file the body cites (V9 (m)); store the re-measurement scripts.

---

## 5. New anomalies and bugs (neither document lists them)

| # | Where (`file:line`) | Mechanism | Consequence | Class |
|---|---|---|---|---|
| A1 | `jca/TrustManagerFactorySpec.mop:29-39,69-79` + `WrapperEmitter.java:383-384` + `ArgsPC.java:49-56` + `PointcutMatcher.java:269-271`; PROVEN in E3 `app.pachli_50.apk` `classes24.dex` | merged wrapper fires `g1`+`g2` (+`g3`) on every 1-arg `getInstance`; `args(alg, *)` arity never applied; `waitingInit` has no `g2` row → `g1: 0→2`, `g2: 2→3` sink | two mute records per **correct** flow (at `getInstance` and `init`), no `@match` ever, in **11 of 23** `jca` specs (`transition_g2[transition_g1[0]]` = sink on OFZ for CIP/KGN/KMF/KPG/KST/MAC/MDG/SSL/SRD/SIG/TMF); explains E3 `unknown` rising to 79.9 %; bears on Study 03 validity | `[jca]`×`[tool]` |
| A2 | `jca/CipherSpec.mop:176-195`; `jca_android:302-317` vs `Cipher.crysl:85` `Init+`, `Update+` | `s2` has no `i1/i2`, `s3` has no `u*` self-loop | FP on `init;init;…` and on multi-chunk streaming `update;update;doFinal` — the most common Cipher pattern; persists in `jca_android` | `[jca]`, `[gh101]` |
| A3 | `jca/SSLContextSpec.mop:64`; `jca_android:90` | `call(public void SSLContext.createSSLEngine(..))` — real return `SSLEngine` | fourth never-matching pointcut (dexlib2 matches return exactly); Engine channel dead in both sets | `[jca]`, `[gh101]` |
| A4 | `jca/PBEKeySpecSpec.mop:37-40,55-59`; `jca_android:42-44,61` vs `PBEKeySpec.crysl:28-29` | requires `RANDOMIZED(password)`; CrySL requires only `randomized[salt]` | every legitimate password-based PBEKeySpec accused (`UnsatisfiedConstraint` + mute InvSeq at `clearPassword`) | `[jca]`, `[gh101]` |
| A5 | `MetaCrySL/generated/api30/KeyPair.cryptsl:13` `co?, (pu*, pr*)*` | constructor optional in the derived oracle | D06 is a hard deviation for `jca_android` (review judged only against 1.5.2) | `[oracle]`/`[gh101]` |
| A6 | `jca/KeyStoreSpec.mop:23` vs `KeyStore.crysl:52` | byte-faithful | D17 (`AndroidKeyStore`) is an oracle choice, not a translation defect; same for MD5/SHA-1 and `SSL`/`TLSv1` | `[oracle]` |
| A7 | `JavaFSM.java:154-158` | per-state `"<name> condition"` for a user state named `fail` is overwritten by `:158` | a `.mop` state literally named `fail` cannot fire `@fail` (mechanism of lesson 1) | `[tool]` |
| A8 | `FSMParser.jj:93,149`; `JavaFSM.java:113-120` | `fsm:` grammar supports per-state `default` transitions; unused in both sets | spec-only, generator-free way to keep an orphan event out of the sink (with INV-INS-110-style guard); not for `ere:` | `[tool]` (capability) |
| A9 | `O99:2270-2285`, `:7385-7388` | entry point ignores the event method's boolean; a condition-false event returns before recomputing flags → handlers dispatch on **stale** flags | inert while handlers `__RESET`; live for KPG's `@fail` and `@match` aliases; in the atomic shape the flag is a `volatile boolean` after a CAS → two threads can dispatch one violation twice (`O101:7690-7712`) | `[tool]` |
| A10 | `O99:15921-15942,15975-15981` + `jca/SSLContextSpec.mop:46` | `unsafe_protocol` fan-out + `__RESET` | every live SSLContext monitor is knocked back to `start` (state loss), not only its `currentProtocol` overwritten | `[jca]` |
| A11 | `HandlerMethod.java:96-101` | handler-visible spec params restored from `WeakReference.get()` | any `@fail` message dereferencing the monitored object can NPE; spec fields are safe | `[tool]` |
| A12 | `FSMPlugin.java:55-64` + `jca/GCMParameterSpecSpec.mop:48` | "used but undefined" check runs on the FSM output, where an undefined ERE symbol no longer appears | undefined ERE symbols pass generation silently | `[tool]` |
| A13 | `HandlerMethod.java:39-47`, `Monitor.java:38,76-81` | `__DEFAULT_MESSAGE` keyword exists; 4-line substitution table | precedent and place for a `__EVENTNAME`/`__PREVSTATE` keyword (radius M, tiny) | capability |
| A14 | `Main.java:414`; `BaseMonitor.java:410-413,1065-1085` | `--internalbehavior` keeps a per-monitor `List<String>` of event names, cloned with the monitor, unbounded, off | generator-native trace prefix, unused by rv-android | capability |
| A15 | `logcat_parser.py:322-349` (PROVEN) | any ≥6-comma text is accepted as a violation (even the JSE csv header line) | `\n` continuation with ≥5 commas → fabricated record with a bogus `error_type` in `unique_msg` | `[tool]` |
| A16 | `result_processor.py:631,999,1038` + `log.py:113` | `unique_msg` derived in four places | any identity change must touch four sites | `[tool]` |
| A17 | `experimento-comp162/scripts/consolidate.py:46` | `<Name>Spec,` regex | live E3 consolidator excludes continuation lines and any spec not ending in `Spec` (`RandomStringPassword`); `mop_total` ≠ aperv-tool INV-CAN-04 count by construction | `[tool]` |
| A18 | `openspec/specs/instrumentation/spec.md` (max INV-INS-103) vs `openspec/changes/gh101-.../specs/instrumentation/spec.md:43-57` | INV-INS-109..115 never synced; INV-INS-110 has no test | a change proposing WS-2 could ship without seeing them; both documents treat them as binding | process |
| A19 | `data/gh101/README.md:255-300`; gh101 `tasks.md`/`design.md` | revert `e204e2a4` unrecorded | gh101 documents a store that is not in the tree | process |
| A20 | `logcat_parser.py:391` vs `:309-315` | Format 1 parses `line_number` and drops it | the generic path loses the line even when it has it | `[tool]` |
| A21 | `results/gh92_e2e2/.../MonitorWrappers.java:487-489`; `gh56-smoke:14627,14939` | pre-fix SecureRandom `(String)` key belonged to orphan `g4`; `next2Event` creates monitors | two more mechanisms for the 12,400 SRD rows (monitor left in `start`; objects born outside the DEX accuse on first `nextBytes`) | `[tool]`, `[jca]` |
| A22 | `WrapperEmitter.java:507-527`; `AndroidClassIndex.java:111-127`; `TypeResolver.toDescriptor` | first-call left-most bias; declared-only member index; nested types | audit `[tool]` items — all still open on `modules` | `[tool]` |
| A23 | `CoverageWeaver.java:194-196` | `methodsSpillFailed` counted, successful spills not | L5c impact invisible in `WeaveReport` (measured 3.9 % / 0 woven, n=1) | `[tool]` |
| A24 | `rvsec-logger-csv/.../ErrorCollector.java:42` | `escape(...).trim()` order | once escaping is fixed the two collectors still disagree on trailing whitespace | `[tool]` |
| A25 | `experimento-comp162/README.md:182-193` | "Estado" says the campaign has not run | stale after 2026-08-13 | process |

---

## 6. Evolutionary plan with validation gates

Each rung names: what changes · target set and authorisation · gate · effect on counts. Nothing on a rung
that touches a `.mop` is admissible in frozen `jca`; T1 rungs presuppose the researcher's §7 rulings and
the nomination of the post-E3 set (repaired `jca_android`, or a successor derived from `jca` — see V8).

**Rung 0 — Measure before touching (executable now, no code change).**
- Commit the E3 re-baseline script next to `experimento-comp162/scripts/` (V2b's `v2b_e3.py` is a
  template): `unknown` share, pairing/co-location, per-spec table, `found .`, `source` line coverage,
  SRD site profile, largest groups. Gate: a second run reproduces the numbers byte-identically.
- Read the numbers already known: `unknown` 79.9 %; three new 1:1 twin families (SKS/IvP/PBK); TMF mute
  at both lines; SRD 14.7 %; 100 % lines. Effect: none.
- **Escalate A1 to the researcher** with the mechanism (V5 item 11) and a proposed discriminating test:
  a G10-style micro-APK (`getInstance("PKIX"); init(ks); getTrustManagers()`) run through
  `rv-experiment run` on the E3 jar, expecting two `unknown` rows and no `@match`. Only the researcher
  can decide whether the E3 `jca` arm is measured with or without the `args()` arity fix.

**Rung 1 — Toolchain hygiene (T0.2 + T0.3a + T0.4; radius P + C-logger; ordinary OpenSpec change,
co-scheduled with gh103).**
- Parser: count continuation lines instead of fabricating (INV-CAN-04 analogue in the analysis spec);
  sentinel for Formats 1/3 (`error_type`/`source`), golden output regenerated (INV-ANA-46); keep the
  `line_number` Format 1 already parses (A20); a spec-name sanity check on Format 2.
- Content rule: no `\n`, no `:::`, message is the last positional field — documented in INV-ANA-08 and
  enforced by a test over `.mop` bodies (home: `$RVA/tests/parity/`, since `rvsec-mop` has no tests).
- Fix `escapeSpecialCharacters` in both collectors and the `null`-`expecting` NPE, **without**
  re-enabling the whole-line call (bundle with the content test; alone it is dead code by P3).
- Gate: `uv run pytest --import-mode=importlib -o "addopts="` on rv-coverage/rv-platform/aperv-tool;
  the parser probes of V6 as regression tests. Effect on counts: none.

**Rung 2 — Identity decision (T0.5; radius C, shared runtime → gh101 rule "identical to both sets,
effect enumerated per site").**
- Add a structured id to `ErrorSummary` identity — the offending **event name** (or CrySL clause id) —
  not the free text, not an object hash (V8 volume model: ≤ |alphabet| per site).
- Rewrite `ErrorDescriptionTest.java:179-220` deliberately; touch the four `unique_msg` derivations
  (A16) or extract one helper. Spec deltas: INV-CORE-25/41 wording; INV-PLT-19 unchanged if the id rides
  inside `message` (V6 (f)).
- Gate: generation + compile of the frozen `jca` set unchanged in the monitor byte-diff except the
  collector call; unit tests; a JVM harness (audit style) firing two events at one site expects two
  records. Effect: rows per site may grow to the number of distinct events (1–3 in practice). Device-side
  → post-E3 builds only.

**Rung 3 — Message text only (T1.3 + WS-1.5; radius S; target set nominated by the researcher).**
- 4-arg constructor in the 21 `@fail`; message = event name from a declaration-ordered array +
  spec variables + object class, composed before `__RESET`; the 4 non-`@fail` mute sites report their
  parameters. No hash, no `\n`, no `:::`, no state names.
- Gate: generation of the whole set (INV-INS-115); array length == `getNumberOfEvents()` (a generation-time
  check); monitor compiles; `rvsec-core` tests; a micro-APK per failure mode via `rv-experiment run`;
  re-parse yields zero `unknown` and one distinct message per mode (measurable only with rung 2 or across
  processes). Effect: `unknown` → 0; row counts unchanged without rung 2.

**Rung 4 — Automaton and pointcuts (WS-7 items 1–5, WS-2.4, A2, A3, A4; not WS-2.5/2.6; radius S).**
- Gate (formal, mandatory): (i) INV-INS-110 asserted over the **generated** transition tables (no bound
  event with an all-sink row) — a script over `MultiSpec_1RuntimeMonitor.java`; (ii) language inclusion:
  translate the CrySL `ORDER` (original and api30, chosen per set) into a DFA and check that the
  generated minimised automaton accepts every ORDER-conformant trace over the common alphabet and
  rejects every non-conformant one up to a bound (bounded model checking on traces of length ≤ n; the
  audit's minimal separating traces become executable JVM counterexamples); (iii) spec mutation (drop a
  transition, swap an event) must be caught by (ii); (iv) provenance class and divergence record entry
  for every edit (`[jca]`/`[gh101]`/`[tool]`/`[oracle]`), merged with gh101's vocabulary.
- Effect: SRD stratum drops; SKS/IvP/PBK twins vanish; counts non-comparable (already the case since gh100).

**Rung 5 — Predicates (WS-3, after D-4 and the identity-store ruling reopened by `e204e2a4`).**
- `condition()` moved into the body only together with the automaton edit per spec (a formerly
  suppressed event now transitions); a `RequiredPredicate` error type; the RANDOMIZED discipline; the
  four missing producers or an explicit scope reduction.
- Gate: predicate-inventory parity test; a product check "automaton × predicates" — for each
  `REQUIRES`/`ENSURES` edge, a bounded exploration that no reachable trace grants a predicate from a
  violating path (audit GAMA-SRD-03) — plus the composition drive the audit already has.

**Rung 6 — Generator/runtime (only if rung 3 shows "expected one of" or localisation is needed).**
- `__EVENTNAME`/`__PREVSTATE` keywords next to `__DEFAULT_MESSAGE` (A13), or `RVM_prevstate` +
  `RVM_eventNames`; optionally `--internalbehavior`-style bounded trace prefix; debug-item preservation
  in `cloneInstructions` + spill counter (cheap, low value for JCA frames); an app-package constant via
  the `ThisJoinPointEmitter` channel for a first-application-frame; a `(class, method, callee, line)`
  weave manifest joined offline on `(class, method, event)`.
- Gate: byte-diff of the frozen-set monitor changes only in the added token; every rv-monitor consumer's
  tests; a `dexdump` before/after census (V5's script) as the L5c regression test.

**Rung 7 — READY** per `fase0/pre_registro.md §7` (23/23 APROVADA, all gates PASS, no
OMITIDA/INCORRETA/INCONCLUSIVA, no open counterexample, reproducible evidence) — not a new criterion.

Formal-validation ideas evaluated (validation prompt §6): language equivalence/inclusion — feasible
(the generated tables are already a DFA; ORDER regexes are regular); INV-INS-110 check — trivial over
tables; separating traces as JVM counterexamples — the audit's method, reuse it; bounded checking of
automaton × predicates — feasible for the small predicate graph (25 constants), tool to be chosen;
spec mutation — cheap and the only way to know whether the gates discriminate; message properties —
(1) every violation names event and state class, (2) no two failure modes share a message,
(3) injectivity per spec — checkable statically over the `.mop` text plus the event array; CogniCrypt as
an oracle over the same micro-APKs — the strongest external check, but the two tools use different
oracles (1.5.2 vs api30) and different granularities (static site vs `(class, method)`), so it validates
categories and counts, not messages.

---

## 7. Brainstorming — ideas with cost / radius / risk (each rooted in something opened)

1. **Structured `key=value` message with an opaque `message` field and first-class `event`.** Opened:
   `logcat_parser.py:348` (rejoin), V6 probe (JSON survives positionally), `violations.py:140`. Cost: S
   (message shape) + P (parser treats `message` as opaque; consumers split on `=`). Radius: no header
   change if the id rides inside `message`. Risk: `\n`/`:::` still forbidden; `unique_msg` cardinality
   grows if values are embedded. Recommended shape for rung 3.
2. **Error-code table per spec/CrySL clause (`CIP-ORDER-03`) with human text in the consumer.** Opened:
   `ErrorType.java:3-10` (six values), audit §9 (ii) "clause/constraint id", `unique_msg` 5-way. Cost: S
   + a table in the analysis layer (gh103). Radius: none on the device path. Risk: the table must be
   generated from the same source as the automaton or it drifts (rung 4's INV-INS-115 check applies).
3. **Generator emits event/state names (`__EVENTNAME`, `__PREVSTATE`).** Opened: `HandlerMethod.java:39-47`,
   `Monitor.java:38,76-81` (`__DEFAULT_MESSAGE`), `JavaFSM.java:70-77` (event ids declaration-ordered),
   OFZ atomic `handleEvent` `oldstate` (`:5299`). Cost: a few lines in rv-monitor. Radius: M (all consumers)
   but additive. Risk: state names are minimised ids; emit event names and the pre-fail state id, never
   spec state names.
4. **Trace prefix per monitor.** Opened: `--internalbehavior` (`BaseMonitor.java:1065-1085`, unbounded
   list, cloned). Cost: M for a bounded ring buffer (last N event ids). Risk: memory per live monitor;
   volume of the message. Use as a *calibration-campaign* mode, not the default.
5. **Static weave manifest joined offline.** Opened: `DexWeaver.java:359-405` (class/method/idx/callee),
   `SignatureFormatter.java:27-40`, `CoverageWeaver.java:181-186`, `ThisJoinPointEmitter.java:5-16`.
   Cost: I (emit JSON from the loop). Risk: the join key `(class, method)` is ambiguous without the event
   name or the line — pair with idea 1.
6. **Structured id in dedupe identity (event/clause), not text, not hash.** Opened: `ErrorSummary.java:73-120`,
   `ErrorDescriptionTest.java:179-220`, audit §9 (ii). Cost: C. Risk: bounded by alphabet (V8 model). Rung 2.
7. **Rate limiting / aggregation per site with a suppressed-count.** Opened: `ErrorCollector.java:10-22`
   (unsynchronised `HashSet`, per process), plan §2.5, E3 5-col group 1,152 rows. Cost: C. Risk: changes
   `mop_total` semantics; needs D-6.
8. **CogniCrypt categories as `ErrorType` with CrySL remediation text.** Opened: `TypestateError.java:41-63`,
   `RequiredPredicateError.java:42-55`, `IncompleteOperationError.java:59-74`, `ConstraintError.java:58-119`,
   `ForbiddenMethodError.java:43-54`; `ErrorType.java` has no `ForbiddenMethod`/`RequiredPredicate`/
   `IncompleteOperation`. Cost: C + S. Risk: comparability; but PBEKeySpec's FORBIDDEN ctors reported as
   `InvalidSequenceOfMethodCalls` (A4/V4) show the vocabulary gap is real.
9. **Generate the `.mop` (automata + messages) from CrySL via MetaCrySL.** Opened: `A30/*.cryptsl`,
   gh101 `divergence_record.csv` (106 hand hunks), audit §7 items 2/3/6 (api30 itself defective:
   `next(numB)` protected, no `nextInt`). Cost: high; radius: a new generator. Risk: the oracle's own
   defects propagate; and memory says the MetaCrySL generator is not to be touched yet. Long-term only.
10. **Diagnostic mode via `--internalbehavior` for calibration campaigns.** Opened: `Main.java:414`.
    Cost: build flag + parser branch. Risk: volume. Cheap to trial on the E3 micro-APKs.
11. **`fsm:` `default` transitions instead of enumerated self-loops.** Opened: `FSMParser.jj:93,149`,
    `JavaFSM.java:113-120`. Cost: S. Risk: swallows genuinely illegal events in that state — only with an
    explicit `unsafe` target and an INV-INS-110-style check; not for `ere:` specs.
12. **Alphabet reduction.** Opened: `gh101/design.md:250` (n×(2ⁿ−1)), `tasks.md:111` (17 → 14). Every
    orphan repair by removal (option B) or by folding the violating check into the legitimate event body
    reduces generation cost; A/C are cost-neutral. Risk: expressiveness ("after an unsafe instantiation").
13. **`args()` arity enforcement in both weave paths (A1).** Opened: `ArgsPC.java:49-56`,
    `PointcutMatcher.java:269-271`, `WrapperEmitter.java:383-384`. Cost: I, small. Risk: **flips Study 03
    semantics** — researcher decision; also removes the `g2` FP in 11 specs at once, which is more
    "message value" than any `.mop` edit on this list.

---

## 8. Risks and threats to the validity of this review; NOT_VERIFIED

- **Same class of agent.** This review was produced by the same class of agent as the plan and the
  review; the mitigation was subagents with re-open-and-quote discipline and cross-checks between them
  (V1↔V3 on the atomic count, V4↔V9 on api30, V5↔V2b on the TMF residual). Agreement is not proof; the
  quotes are.
- **E3 runtime consequence of A1 is INFERRED.** The wrapper (DEX, PROVEN) and the tables (OFZ, MEASURED)
  are established; that the runtime does exactly `g1: 0→2, g2: 2→3` on device was not replayed (no
  emulator; by rule). The E3 numbers match the prediction (2 mute per flow, 0 twins, 0 `found .`), which
  is strong but circumstantial. The G10-style micro-APK in rung 0 is the discriminating test.
- **L5c measurement is n = 1** (one APK, `dexdump`), plus the E3 100 %-line statistic (which conditions
  on frames that were reported at all).
- **12,400 SRD rows attribution** remains INFERRED (three coinciding mechanisms; CSV lacks object identity).
- **api30 judgements** rest on the rule text and gh101's documented reading; CogniCrypt's `pad()` on
  2-part transformations not checked.
- **`static final String[]` in the declarations block**: viable by grammar path; NOT_VERIFIED in an rvsec
  oracle (would require a monitor generation, deliberately not run).
- **logcat re-prefixing of `\n` segments** on device: INFERRED (the parser behaviour on the resulting
  lines is PROVEN).
- **`Platform.kt` line provenance** (review's ":83 is a version offset"): NOT_VERIFIED — okhttp source not
  in the workspace.
- **`DexWriter.java` line numbers** (external jar): NOT_VERIFIED, effect agreed.
- **`android.jar` selection** code path: NOT_VERIFIED (Python side).
- **Plan's in-tree figures** from `e3_decisiva_05` / `exp_00` (24 timestamps, 1,542 rows): NOT_VERIFIED.
- **Registration order of pre-fix wrappers**: INFERRED from artifact order.

---

## 9. Documents and artifacts used (absolute paths)

`$RVSEC = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`;
`$WS = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`;
`$SP = /tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4c766db2-76c7-4256-a969-597f7cac5045/scratchpad`.

- Under validation: `$RVSEC/rv-android/docs/20260815_javamop_mensagens.md`,
  `…/20260815_javamop_mensagens_analise.md`, `…/20260815_javamop_mensagens_analise_handoff_prompt.md`,
  `…/20260815_javamop_mensagens_validacao_prompt.md`.
- Prior work: `$RVSEC/rv-android/openspec/changes/gh100-weaver-emission-fidelity/` (`proposal.md`,
  `design.md`, `tasks.md`, `evidence/{census_pre_repair.json,l3_verdicts.md,green_deltas.md}`);
  `…/gh101-jca-spec-conformance/` (`proposal.md`, `design.md`, `tasks.md`, `specs/instrumentation/spec.md`);
  `$RVSEC/rv-android/data/gh101/{README.md,frozen_set_debt.md,divergence_record.csv,conformance_record.csv,algorithm_naming.md}`;
  `$RVSEC/rv-android/tests/parity/test_gh101_specset_gates.py`; `…/gh102-artifact-scoped-parse/`,
  `…/gh103-campaign-analysis-layer/`; `$RVSEC/rv-android/docs/20260808_validar_specs_jca_android.md`;
  `$RVSEC/rv-android/audit/20260808_validacao_jca_android/` (`global/juizglobal_relatorio.md`,
  `fase0/{estado_gh100_gh101.md,modelo_semantico.md,pre_registro.md,manifesto.md}`,
  `pilot/{alfa_cipher.md,juiz_sintese.md,gama_diagnostico.md}`, `batchA..D/juiz_sintese_*.md`,
  `batchA/alfa_report.md`, `batchB/alfa_report.md`, `batchD/gama_report.md`, `set/set_exec_report.md`,
  `set/set_cons_report.md`, `HANDOFF_PROXIMA_SESSAO.md`);
  `$RVSEC/rv-android/docs/{20260810_plano_prontidao_estudo03.md,20260812_comp162.md,20260812_registro_execucao_prontidao_e3.md}`;
  `$RVSEC/rv-android/experimento-comp162/{README.md,scripts/consolidate.py,results/comp162_0*/…/errors.csv,consolidado/*.csv}`;
  commits `e204e2a4 f322c5da 48b57fc5 233df18a a0f43833 1217d6ff 2a36defa 1dd1f4c5 7e7acb69 cf234788`.
- Evidence/oracles: `$WS/ase-journal/dataset/results/{errors.csv,summary.csv,README.md}`;
  `$WS/Crypto-API-Rules/JavaCryptographicArchitecture/src/*.crysl`; `$WS/MetaCrySL/generated/api30/*.cryptsl`;
  `$WS/CryptoAnalysis/CryptoAnalysis/src/main/java/crypto/analysis/errors/{TypestateError,RequiredPredicateError,IncompleteOperationError,ConstraintError,ForbiddenMethodError}.java`.
- JavaMOP specifications: `$RVSEC/rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/`
  (and the git-ignored `jca/MultiSpec_1MonitorAspect.aj`).
- Runtime/generator/weaver/Python: `$RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/{eh/*,Property.java,ExecutionContext.java,jca/util/*CipherTransformationUtil.java}` and `src/test/.../ErrorDescriptionTest.java`;
  `$RVSEC/rvsec/rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java`; `$RVSEC/rvsec/rvsec-logger-csv/.../ErrorCollector.java`;
  `$RVSEC/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/{java/rvj/output/monitor/*,java/rvj/output/monitorset/MonitorSet.java,java/rvj/output/Util.java,logicpluginshells/fsm/JavaFSM.java,java/rvj/parser/ast/rvmspec/EventDefinition.java,java/rvj/RVMonitorExtender.java,java/rvj/logicpluginshells/*}`,
  `$RVSEC/rv-monitor/rv-monitor/src/main/javacc/.../RVParser.jj`, `$RVSEC/rv-monitor/plugins_logicrepository/{ere,fsm}/`,
  `$RVSEC/rv-monitor/rv-monitor-rt/.../{ViolationRecorder.java,tablebase/*}`;
  `$RVSEC/javamop/src/main/java/javamop/{output/descriptor/DescriptorWriter.java,parser/ast/mopspec/EventDefinition.java,parser/ast/visitor/{RVDumpVisitor,DumpVisitor}.java,output/combinedaspect/event/{EndProgram,EndObject}.java}`,
  `$RVSEC/javamop/src/main/javacc/.../javamop.jj`, `$RVSEC/javamop/examples/ERE/SafeFileWriter/SafeFileWriter.mop`;
  `$RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/{dex-mutator,pointcut-engine,advice-emitter,coverage-weaver,cli,validator,monitor-builder}/…`;
  `$RVSEC/rv-android/modules/{rv-coverage/src/rv_coverage/parser/log/logcat_parser.py,rv-android-core/src/rv_android_core/domain/{log.py,coverage.py},rv-platform/src/rv_platform/components/result_processor.py,rv-platform/tests/components/test_result_processor.py,rv-experiment/src/rv_experiment/{__main__.py,config.py},rv-static-analysis/…/config.py,aperv-tool/src/aperv_tool/analysis/{violations.py,clock_logcat_join.py}}`;
  `$RVSEC/rv-android/experimento-cal/scripts/{consolidate_cal.py,verify_iteration.py}`, `$RVSEC/rv-android/experimento-20260721/scripts/consolidate_compare.py`;
  `$RVSEC/rv-android/openspec/specs/{core,platform,analysis,instrumentation,aperv,experiment}/spec.md`.
- Generated artifacts: `$RVSEC/rv-android/results/{gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control,gh92_e2e2,gh56-smoke}/monitors/…`,
  `$RVSEC/rv-android/results/gh101_group8_jca_android/instrumented_apks/`, `$WS/rvsec-dataset/head_apks/com.owncloud.android_48000100.apk` (census),
  `/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/app.pachli_50.apk` (dexdump).
- This review's scripts/outputs: `$SP/v1/v1_report.md`; `$SP/v2/v2_{a..e}.py|.out`, `$SP/v2/v2b_e3.py|.out`;
  `$SP/v3/`; `$SP/v4/v4_report.md`; `$SP/v5/{dbg.py,jca_in_lost.py,e3/}`; `$SP/v6/parser_probe*.py|.out`;
  `$SP/v7/notes.txt`; `$SP/v8/e3_baseline.txt`; `$SP/v9/`.
