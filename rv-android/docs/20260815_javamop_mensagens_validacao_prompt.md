# Prompt — independent validation of the JavaMOP messages plan and of its adversarial review

**Date:** 2026-08-15
**Your role:** you are an external, sceptical, meticulous reviewer. You will validate two documents
(a plan, and an adversarial review of that plan), trying to knock both down, and then propose an
evolutionary path and alternatives. **Do not implement anything.** Read-only mode in the
repository; write only your report and, if needed, temporary files in a scratch directory outside
the source tree.

**Mandatory output:** one complete report, **in English**, at:

`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260815_javamop_mensagens_<MODEL_NAME>.md`

where `<MODEL_NAME>` is the name of the model/agent you are (e.g. `gpt5`, `gemini25pro`,
`claude_opus`, `qwen3`), lower-case, no spaces.

---

## 1. How to work (mandatory)

- **Use several subagents** (or, if you have none, several independent passes with isolated
  context), one per verification dimension (§5). Each subagent gets a self-contained prompt with
  absolute paths, verifies **by opening the source**, and returns `file:line` with a quote. Never
  accept a `file:line` from a document without re-opening it. Mark as `UNVERIFIED` whatever you
  could not re-open.
- **Use the `sequential-thinking` MCP** at the start (to decompose the task), before each
  per-section verdict, when resolving contradictions between subagents, and before the final
  opinion. Do not publish raw chain-of-thought; publish only a concise scientific log (question →
  hypothesis → discriminating test → evidence → result → uncertainty → next decision).
- **Separate** `PROVEN` (executed/reproduced), `MEASURED`, `OBSERVED_IN_ARTIFACT`, `INFERRED`,
  `NOT_VERIFIED`. Agreement between agents is not proof; a round number is not proof.
- **The project's golden rule:** *a handoff, a subagent report and arithmetic are not
  verification; open the source and cite `file:line`.* Several reports produced earlier in this
  investigation carried strong claims that turned out imprecise — treat everything as hypothesis.
- You **are free** to explore dimensions not listed here. The protocol below is the floor, not the
  ceiling.

### Non-negotiable operational constraints

- **NEVER** start, stop or manage an Android emulator by hand (permanent rule of `CLAUDE.md`).
  Anything that needs a device goes through `rv-experiment run` / `rv-platform run` — and is most
  likely out of scope for this analysis session.
- **Do not edit** the `.mop` files, nor `jca/` (frozen), nor MetaCrySL, nor `ase-journal` (the
  article is evidence, not a target). Do not edit the two documents under review nor the handoff.
- **Monitor generation is not parallelisable** and JavaMOP writes `.rvm` next to the source: if
  you generate monitors, use a scratch directory, never the spec tree, and never two concurrent
  generations. `/tmp` is tmpfs (62 GiB in RAM) — export `TMPDIR` to a directory on disk.
- Python tests: always `uv run pytest --import-mode=importlib -o "addopts="`.
- Code and comments in English; the final report in English.

---

## 2. Context — what we are doing

**RVSEC / RV-Android** performs *runtime verification* of Android applications: JavaMOP
specifications (the *Monitoring-Oriented Programming* paradigm, Chen & Roşu) describe, over the
JCA (cryptography) API, events (AspectJ-style pointcuts), a property over the event sequence
(`ere:`/`fsm:`) and handlers (`@fail`, `@match`); RV-Monitor synthesises the Java monitor; a
DEX-native weaver (dexlib2) injects the calls into the APK; at run time, violations go to logcat
(`Log.v("RVSEC", …)`), are parsed in Python and become `errors.csv`.

**Beware of the word "spec"** — the repository uses it in two unrelated senses:
1. **SDD/OpenSpec specs** (`docs/SDD.md`, `openspec/specs/**`, `openspec/changes/gh<N>-*/`):
   development-process artifacts (requirements, `INV-*` invariants, scenarios).
2. **JavaMOP specifications** (`rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,
   generic_new}/*.mop`): runtime-verification artifacts, translated from CrySL rules
   (CogniCrypt). Both coexist and we use both; make this explicit in your report.

**The problem.** In the reference dataset (`ase-journal/dataset/results/errors.csv`, 97,018 rows),
72.93 % of the violation messages are the literal `unknown` (all and only the
`InvalidSequenceOfMethodCalls`), and there are only 19 distinct messages. A human cannot read the
report. We want the **next campaign** to produce legible, actionable reports.

**What has been done so far (in order):**
1. Root-cause investigation and **plan** (seven layers L1–L7, eight workstreams WS-1..WS-8, eight
   decisions D-1..D-8, nine acceptance criteria, 50 defects D01–D50, four `[inferred]` claims):
   `docs/20260815_javamop_mensagens.md`.
2. Handoff requesting an **adversarial review** of the plan:
   `docs/20260815_javamop_mensagens_analise_handoff_prompt.md`.
3. **Adversarial review** (six verification passes: generator, `rvsec-core`/loggers, `.mop`,
   dexlib2 weaver, Python parser/consumers, CSV re-measurement):
   `docs/20260815_javamop_mensagens_analise.md`. Its central conclusions — **which you must try to
   knock down just as hard as the plan**:
   - the plan's pillar (implicit FSM sink + `@fail` body inlined verbatim) holds;
   - the plan ignores three bodies of work: changes **gh100** (weaver repairs: 9 truncated events
     that never reached the DEX; wrapper-registry collision, last write wins) and **gh101**
     (rewrite of `jca_android`; **freeze of `jca`**), the **`jca_android` audit** (verdict NOT
     READY, 22/22 REPROVADA) and the **Study 03 decision** (uses `jca`; keeps the weaver repair;
     reverted the identity-keyed `ExecutionContext` in `e204e2a4`);
   - hence, today the plan's specification-level workstreams have no admissible target set, and
     they are a subset of the audit's patch list;
   - the plan's evidence is pre-gh100; the 1:1 twins in `TrustManagerFactorySpec` and the 8,371
     `but found .` are the wrapper collision; the 12,400 InvSeq of `SecureRandomSpec` are the
     `next2`-missing-from-`end` false positive;
   - at `@fail`: `Prop_N_state`/`RVM_lastevent` exist only in the *synchronized* monitor shape
     (use `getState()`/`getLastEvent()`); the pre-fail state is lost (WS-1.4's "expected one of"
     is not derivable there); compose the message before `__RESET`;
   - `condition()` is inlined as a prologue in the monitor's event method (the monitor is created
     before the test); `BaseMonitor.java:604-610` is dead code;
   - several numeric corrections to the CSV (the "27 %" is a pairing count; "73.4 %" and "28
     findings" do not reproduce; the largest identical group is 6, not 3,098);
   - a two-tier cut (T0 toolchain/parser executable now; T1 specification level only after the
     researcher's rulings in audit §7 and the choice of the post-E3 set).

**Scope rule:** the target is the next campaign, **not the article**; nothing in `ase-journal`
will be revised. Do not propose rectifying the article (it does not use `unique_msg`; the
published key is `(apk, class, method, spec)`).

---

## 3. Files and paths

Real git root: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`
(`git rev-parse --show-toplevel` prints `/pedro/desenvolvimento/...`, the same directory through a
symlink). Below, `$RVSEC` = that root; `$RVA` = `$RVSEC/rv-android`; `$WS` =
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`. Always use absolute
paths in your subagents' prompts.

### 3.1 The documents under validation (read them in full, first)
| Path | Role |
|---|---|
| `$RVA/docs/20260815_javamop_mensagens.md` | **the plan** (~980 lines, English) |
| `$RVA/docs/20260815_javamop_mensagens_analise.md` | **the adversarial review** of the plan (~800 lines, English); its §8 lists every document it used |
| `$RVA/docs/20260815_javamop_mensagens_analise_handoff_prompt.md` | the handoff that produced the review (axes A–E, lessons, useful commands; in Portuguese) |

### 3.2 Prior work both documents must respect
| Path | Role |
|---|---|
| `$RVA/openspec/changes/gh100-weaver-emission-fidelity/` (`proposal.md`, `design.md`, `tasks.md`, `evidence/census_pre_repair.json`, `evidence/l3_verdicts.md`, `evidence/green_deltas.md`) | dexlib2 weaver repairs; the 9 truncated events; the wrapper collision (task 5.3); L3-b/L3-c |
| `$RVA/openspec/changes/gh101-jca-spec-conformance/` (`proposal.md`, `design.md`, `tasks.md`, `specs/`) and `$RVA/data/gh101/` (`README.md`, `frozen_set_debt.md`, `divergence_record.csv`, `conformance_record.csv`, `predicate_*.csv`, `algorithm_naming.md`) | rewrite of `jca_android`; **freeze of `jca`** (D-S0, base `7e7acb69`); INV-INS-109..115 |
| `$RVA/docs/20260808_validar_specs_jca_android.md` | protocol of the adversarial `jca_android` audit (a good model of rigour — reuse its ideas) |
| `$RVA/audit/20260808_validacao_jca_android/` — `global/juizglobal_relatorio.md` (§3 verdicts, §5 findings, §6 risks, **§7 researcher decision list**, **§9 patch areas**, §10 final decision), `fase0/estado_gh100_gh101.md`, `fase0/modelo_semantico.md`, `batchA..D/`, `set/`, `claims/` | the NOT READY verdict and all its evidence (558 claims, 119 phenomena) |
| `$RVA/docs/20260810_plano_prontidao_estudo03.md` (§2 D1–D13), `$RVA/docs/20260812_comp162.md`, `$RVA/docs/20260812_registro_execucao_prontidao_e3.md` | Study 03 decisions: uses `jca`; keeps the weaver repair; reverts `ExecutionContext` |
| commits (in `$RVSEC`): `e204e2a4` (store revert), `f322c5da` (audit), `48b57fc5` (wrapper merge), `233df18a`/`a0f43833`/`1217d6ff`/`2a36defa` (gh101), `7e7acb69` (freeze base), `cf234788` (`source` column) | provenance |
| `$RVA/openspec/changes/gh103-campaign-analysis-layer/` and `$RVA/modules/aperv-tool/src/aperv_tool/analysis/violations.py` | `errors.csv`/`unique_msg` contracts that any message change affects |
| `$RVA/openspec/specs/{core,platform,analysis,instrumentation}/spec.md` | invariants cited (INV-CORE-25/41, INV-PLT-19/24-26, INV-ANA-08/46, INV-INS-109-115) |
| `$RVA/docs/SDD.md`, `$RVA/docs/WORKFLOW.md`, `$RVA/.claude/AGENTS.md`, `$RVA/CLAUDE.md`, `$RVSEC/CLAUDE.md` | process and project rules |
| `$RVA/.claude/skills/rv-analyze-spec/` (`SKILL.md`, `reference/`, `scripts/`) | `.mop` analysis skill (alphabet, automaton, pointcuts, generator cost) — may be used |

### 3.3 Evidence and oracles
| Path | Role |
|---|---|
| `$WS/ase-journal/dataset/results/errors.csv` (+ `README.md` in the same directory) | 97,018 rows; **read-only**; columns `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`; `error_type = unique_msg.split(':::')[3]` |
| `$WS/Crypto-API-Rules/JavaCryptographicArchitecture/src/*.crysl` | original CrySL rules — the translation's *ground truth* |
| `$WS/MetaCrySL/generated/api30/*.cryptsl` | rules derived for Android API 30 (the `jca_android` oracle; **read-only**) |
| `$WS/CryptoAnalysis/CryptoAnalysis/src/main/java/crypto/analysis/errors/` | CogniCrypt error categories (`TypestateError`, `RequiredPredicateError`, `IncompleteOperationError`, …) |

### 3.4 JavaMOP specifications (second sense of "spec")
| Path | Role |
|---|---|
| `$RVSEC/rvsec/rvsec-mop/src/main/resources/jca/` | 23 `.mop` — the experiment's and Study 03's set; **frozen** |
| `$RVSEC/rvsec/rvsec-mop/src/main/resources/jca_android/` | 23 `.mop` — derived, rewritten by gh101, **REPROVADA** in the audit |
| `$RVSEC/rvsec/rvsec-mop/src/main/resources/generic/` (118) and `generic_new/` (27) | generic sets (direct `Log.v`, no `ErrorCollector`) |

### 3.5 Runtime, generator, weaver, Python pipeline
| Path | Role |
|---|---|
| `$RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/` (`ErrorDescription`, `ErrorSummary`, `ErrorType`), `.../mop/Property.java`, `.../mop/ExecutionContext.java`, `.../mop/jca/util/{CipherTransformationUtil,AndroidCipherTransformationUtil}.java`; tests under `rvsec-core/src/test/java/...` | reporting runtime and predicate store |
| `$RVSEC/rvsec/rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java` (Android) and `$RVSEC/rvsec/rvsec-logger-csv/.../ErrorCollector.java` (JSE) | emitters (Android does not escape; JSE escapes only `expecting`) |
| `$RVSEC/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/` (`BaseMonitor`, `HandlerMethod`, `RawMonitor`, `SuffixMonitor`), `.../output/monitorset/MonitorSet.java`, `.../logicpluginshells/fsm/JavaFSM.java`; `$RVSEC/rv-monitor/plugins_logicrepository/{ere,fsm}/`; `$RVSEC/rv-monitor/rv-monitor-rt/.../ViolationRecorder.java`, `.../tablebase/{IMonitor,AbstractSynchronizedMonitor,AbstractAtomicMonitor}.java` | RV-Monitor generator and runtime |
| `$RVSEC/javamop/src/main/java/javamop/` (`output/descriptor/DescriptorWriter.java`, `parser/ast/visitor/RVDumpVisitor.java`, `parser/ast/mopspec/EventDefinition.java`, `parser/ast/visitor/DumpVisitor.java`) | JavaMOP (`condition()` becomes a prologue; `.mop` → `.rvm`/`.aj`/JSON descriptor) |
| `$RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (`dex-mutator/.../DexWeaver.java`, `RegisterShifter.java`, `pointcut-engine/.../PointcutMatcher.java`, `advice-emitter/.../WrapperEmitter.java`, `coverage-weaver/.../{CoverageWeaver,PackageFilter}.java`, `cli/.../InstrumentationCli.java`, `validator/`) | DEX-native weaver |
| `$RVA/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`, `$RVA/modules/rv-android-core/src/rv_android_core/domain/log.py`, `$RVA/modules/rv-platform/src/rv_platform/components/result_processor.py`, `$RVA/modules/rv-experiment/src/rv_experiment/{__main__.py,config.py}`, `$RVA/modules/rv-monitor-generator/` | three-format parser, `RvErrorLog`/`unique_msg`, `errors.csv` writer (11 columns), CLI, monitor generation |

### 3.6 Generated artifacts (oracles of what the generator/weaver emit)
| Path |
|---|
| `$RVA/results/gh99_jca_android_monitors/monitors/` (`MultiSpec_1RuntimeMonitor.java`, `MultiSpec_1MonitorAspect.{aj,json}`) |
| `$RVA/results/gh101_group8_jca_android/monitors/` and `$RVA/results/gh101_group8_jca_frozen_control/monitors/` |
| `$RVA/results/gh92_e2e2/monitors/` (includes `mop/MonitorWrappers.java` **pre-repair** — the wrapper-collision evidence) and `$RVA/results/gh56-smoke/monitors/` |

---

## 4. Lessons and pitfalls (do not repeat mistakes already made)

1. **`@fail` is not "an event with no transition": it is a state.** `Category_fail = (state ==
   sink)`, evaluated after every event; the sink is an extra, unnamed state that `JavaFSM` appends
   and into which it completes every missing `(state, event)`. A `.mop` state literally named
   `fail` does **not** fire `@fail`.
2. **`__RESET` does not clear specification variables** (only state, `lastevent`, flags). This
   was already a discarded hypothesis — do not redo it.
3. **The event body runs before the transition** — which is why an event that reports in its body
   and then falls into the sink produces two records, the informative one first.
4. **Events with no bound parameter** (`unsafe_protocol` without `returning`, `g3` binding `k`
   instead of `mf`) go to the root slice and are dispatched to **all** live monitors; a new monitor
   is created by **cloning** the root (it inherits spec variables). This contaminates, and explains
   empty/inherited observed values.
5. **The dataset is pre-gh100.** Twelve wrappers were silently discarded; nine events never
   reached the DEX. Do not attribute to "spec logic" what is a weaver defect, nor the reverse —
   and do not attribute causality from correlation in `errors.csv` alone (the audit's rule).
6. **`jca` is frozen; `jca_android` is REPROVADA.** No specification proposal is executable
   without first stating in which set (and under which authorisation) it lands.
7. **Granularity is `(class, method)`, never a signature** — the runtime uses `StackTraceElement`
   without a descriptor.
8. **The parser of the generic formats fabricates fields** (`error_type := spec`, `source :=
   "Unknown Source:1"`); a message containing `\n` yields a **second fabricated record**, not just
   a drop.
9. **`ErrorSummary.equals/hashCode` excludes the message** — at the same site the first record wins
   within the process; a test (`ErrorDescriptionTest:179-220`) pins this on purpose.
10. **The collectors' escape function is buggy** and the commented-out call would quote the whole
    line.

---

## 5. Minimum validation protocol (dimensions — at least one subagent each)

For **each** dimension: (a) verdict per claim/section — `CONFIRMED` / `IMPRECISE` / `WRONG` /
`INCOMPLETE` — with a re-opened `file:line`; (b) what the plan got wrong; (c) what the review got
wrong or missed; (d) new findings.

**V1 — Cross-factual verification of both documents.** Sample at least 40 `file:line` (prioritise
those carrying decisions: sink/`JavaFSM`; `@fail` inlining; `getState()`/`getLastEvent()` and the
atomic × synchronized shape; `condition()` as prologue; `ErrorSummary` identity; `ErrorCollector`
format/escape; `RegisterShifter`; `PointcutMatcher` return type; `DescriptorWriter` exclusions;
Python parser; CSV writer). Where the two documents disagree, decide with evidence.

**V2 — Evidence base (CSV).** Reproduce both documents' central numbers with your own scripts
(message distribution; "shadow" under both definitions — pairing and co-location; funnel
661→207→136→?; third-party attribution under explicit definitions; identical groups; empty
observed values). State which definitions yield which numbers.

**V3 — Generator and runtime semantics.** Confirm or refute, in source and in the generated
oracles: the sink; `@fail` firing per event while in the sink; `__RESET`; fan-out of
parameterless events and root-monitor cloning; event ids (declaration order) and state ids
(minimisation); what is and is not in scope at `@fail`; viability of `static` declarations in the
declarations block; `RVM_loc`; the absence of an end-of-trace hook; JavaMOP's
`endObject`/`endProgram` and their absence from dexlib2.

**V4 — CrySL ↔ `.mop` fidelity.** For every "false positive" and "defect" either document claims,
decide against the CrySL rules (original and api30): translation deviation, CrySL being strict, or
ambiguous? Consider `Cipher.crysl` (ORDER, `doFinal()` without `update`, re-`init`),
`SecureRandom.crysl` (`next2`), `KeyPair.crysl` (constructor), `MessageDigest.crysl` (`reset`).
Confront with the audit's per-spec verdicts (`batchA..D/juiz_sintese_*.md`).

**V5 — Weaver and localisation.** Wrapper collision (pre/post `48b57fc5`); truncation; return-type
matching; routes that clone and destroy debug info; scope policies; the mechanism of the 8,371
`but found .` and the 643 `found X509`; the `next2` hypothesis for `SecureRandomSpec`'s 12,400
(audit H-SRD-1) against the collision hypothesis.

**V6 — Python pipeline, contracts and consumers.** Parser (three formats; `\n`; `:::`),
`unique_msg`, 11-column writer, `INV-PLT-19`, `INV-CORE-25/41`, `INV-ANA-08`, gh103
(`violations.py`), `aperv-tool/clock_logcat_join.py`, campaign consolidators, `TraceComparator`
(gh100). For every change either document proposes (rich message; new columns; sentinel; dedupe
identity), state exactly what breaks and where.

**V7 — Real state of prior work.** Rebuild, from git and artifacts, what gh100/gh101 did, what
remained, what was reverted (`e204e2a4`), what the audit rejected and what Study 03 decided. Check
whether both documents represent this correctly and completely. List audit findings relevant to
messages/diagnostics that neither document cites.

**V8 — Design and proportionality.** Judge: sequencing; the plan's internal coherence (Phase A
"without shared infrastructure" vs WS-3.1); WS-1 (field names, pre-fail state, order relative to
`__RESET`, hand tables vs generator, identity hash); WS-2 (give a transition vs remove the event
vs fold into the legitimate event); WS-1 × WS-2 × WS-6.1 composition (volume); acceptance criteria
verifiable or not; the review's T0/T1 cut (is it the right cut? anything missing or superfluous?);
risks neither document covers.

**V9 — Audit of the review itself.** The review was written by the same class of agent that wrote
the plan; look for confirmation bias, claims without `file:line`, numbers not reproduced, sections
where it merely restates the plan, and conclusions it drew from subagent reports without
re-opening the source.

---

## 6. Evolutionary/gradual plan (mandatory to propose)

Propose an **incremental path**, from the smallest safe step to the full correction of the specs
and the Java, with a validation gate on every rung. Suggested ladder (adjust, cut, extend):

0. **Measure before touching**: how to use the first outputs of Study 03 (already `jca` + repaired
   weaver) as the post-repair *baseline* of the message problem, implementing nothing.
1. **Only the message text in the `.mop`** (the smallest step): switch the 3-argument constructor
   to the 4-argument one in the `@fail` handlers and compose the message from what is already in
   scope (`getLastEvent()` + event name + spec variables + object class), before `__RESET`, without
   `\n`/`:::`/identity hash. State **in which set** this can land today and under which
   authorisation; what changes in counts; how to validate (generation + monitor compilation +
   `rvsec-core` unit tests + micro-APK via `rv-experiment run` + re-parse).
2. **Content rules and contracts**: a test enforcing the message shape; a sentinel for fabricated
   fields; the dedupe-identity decision (free text × structured event/clause id); the escape fixed
   without re-enabling the whole-line call.
3. **Automaton and pointcuts** (what is a translation defect vs. CrySL strictness), with gh101's
   divergence record and the audit's provenance classes.
4. **Predicates (`ExecutionContext`)**: the identity × equality question reopened by the revert;
   `condition()` in the body instead of the pointcut and its coupling with the automaton.
5. **Generator/runtime** (`RVM_prevState`, name tables, localisation, end of trace), only if the
   value measured on the earlier rungs justifies touching shared infrastructure.
6. **Full correction** and the criteria for declaring a set "ready" — reusing the audit's READY
   (`fase0/pre_registro.md` §7) rather than inventing another.

**Formal validation, mandatory on every rung that touches a spec.** These are formal
specifications: propose how to verify them formally, not only by test. Ideas you must evaluate
(and extend): language equivalence/inclusion between the `.mop` automaton (the generated,
minimised one) and the CrySL `ORDER` (translated to an automaton); a check that no bound event has
an all-`fail` row (`INV-INS-110`); minimal separating traces as executable counterexamples (JVM
harness, as the audit did); model checking or bounded checking of the product "automaton ×
predicates" for the `REQUIRES`/`ENSURES` edges; spec mutation to measure whether tests/oracles
discriminate; properties over the **message** itself (every violation names event and state; no
message collides with one of different meaning; injectivity of the message with respect to the
failure mode); and a CogniCrypt-derived oracle over the same micro-APKs.

---

## 7. "Relaxed" brainstorming — out-of-the-box ideas (mandatory)

Here you are free, but every idea must come from careful investigation (cite what you opened) and
carry an estimated cost/radius/risk. Example directions — do not limit yourself to them:

- a structured message (JSON or key=value) instead of a sentence, with the parser treating
  `message` as opaque and a first-class `error_type`/`event`/`state`; or a table of error codes per
  spec/CrySL clause (`CIP-ORDER-03`) with the human text only in the consumer;
- emitting the message in the generator (`HandlerMethod`) with event/state names, or a new
  `__EVENTNAME`/`__PREVSTATE` keyword, instead of hand-written tables;
- recording the *trace prefix* (last N events per monitor) and printing it at `@fail`;
- storing the weave site statically (a per-site manifest in the weaver) and joining it offline
  with the dynamic frame, instead of recovering N frames at run time;
- dedupe identity with a structured id (event/clause) — neither free text nor object hash;
- rate limiting/aggregation per site in the collector, with a counter of what was suppressed;
- using CogniCrypt's categories (`TypestateError`, `RequiredPredicateError`,
  `IncompleteOperationError`, `ConstraintError`) as `ErrorType`, with CrySL's remediation text;
- generating the `.mop` (or at least the automata and messages) **automatically** from CrySL via
  MetaCrySL, removing manual translation as a source of defects;
- a "diagnostic mode" of the monitor (RV-Monitor's `--internalbehavior` already exists) for
  calibration campaigns;
- anything that reduces the event alphabet and the generation cost (gh101 measured `CipherSpec`
  falling from 53 s/3.3 GB to 6 s/1 GB when its alphabet was re-budgeted).

Also **hunt for new anomalies and bugs** — in the `.mop`, generator, weaver, collector, parser —
that neither document lists. Each with `file:line`, mechanism, consequence and provenance class
(`[jca]`, `[gh101]`, `[tool]`, `[oracle]`, as in the audit).

---

## 8. Minimum report structure

1. Executive summary (one page): verdict on the plan; verdict on the review; three things you
   knocked down; three you confirmed; the recommendation.
2. Method (subagents used, what each opened, where scripts/outputs live).
3. Verdicts per dimension V1–V9 (tables with `file:line`, evidence class).
4. Lists of corrections needed to the **plan** and to the **review**, kept separate.
5. New anomalies/bugs.
6. Evolutionary/gradual plan with validation gates (incl. formal validation).
7. Brainstorming — ideas with cost/radius/risk and what you opened to propose them.
8. Risks and threats to the validity of your own review; what remained `NOT_VERIFIED`.
9. Documents and artifacts you used (absolute paths).

Start by: reading the three documents of §3.1 in full; reading `global/juizglobal_relatorio.md`
§7/§9/§10 and `docs/20260810_plano_prontidao_estudo03.md` §2; then launching the §5 subagents in
parallel, each with a self-contained prompt and absolute paths; consolidating with
`sequential-thinking`; writing the report at the path given at the top.
