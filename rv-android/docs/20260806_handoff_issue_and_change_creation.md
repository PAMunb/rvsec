# Session handoff — turn the Phase-0 ideation into GitHub issues and OpenSpec changes

> Paste this whole file as the first message of the new session.

---

## 0. Who you are and where you are

You are Claude Code working in the RVSEC / RV-Android research codebase (PhD work of Pedro Costa,
`phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch: `rearch-counterparts`. Main branch: `master`. Tip as of this handoff: `ceb87234`.

**Another session commits on this same branch.** Do not assume the tip is where you left it; do not
rebase, force-push, or reorder anything.

Sibling trees live under `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`
(abbreviated `$WS` below). **Anything outside `rv-android` must be written with an absolute path** —
standing user instruction, applies to code, docs and prose.

---

## 1. What this session must produce

**Phase 0 (ideation) is finished and committed.** Its output is
`docs/20260806_ideacao_consertos_instrumentador_e_specs.md` — a technical analysis document, *not* an
OpenSpec artefact (`docs/WORKFLOW.md` §1 explicitly allows this: such a document "serves as reference
material for the subsequent SDD phases").

**Your job is the next step: create the GitHub issue(s) and the OpenSpec change(s) that implement
that plan.** Concretely:

1. Settle the open decisions in §8 of the ideation document that gate change creation — above all
   **which changes to open now** (§6 below), because there is a board constraint that says "not yet".
2. Create the GitHub issue(s) from the right template.
3. Create the change director(ies) **through the OpenSpec skills**, never by hand.
4. Move the Kanban cards.

Do **not** start implementing. Creating the change artefacts is the deliverable; implementation is a
later session.

---

## 2. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/CLAUDE.md` first.
Then `docs/WORKFLOW.md` — it is the authoritative process reference and this session is pure process.

1. **Follow the OpenSpec workflow rigorously.** Anything under `openspec/changes/gh<N>-*/` goes
   through the **skills** invoked via the `Skill` tool: `openspec-new-change`,
   `openspec-continue-change`, `openspec-propose`, `openspec-ff-change`, `openspec-apply-change`,
   `openspec-verify-change`, `openspec-archive-change` (the `/opsx:*` aliases are the same skills).
   **Never** hand-write or hand-edit an OpenSpec artefact with `Write`/`Edit`. This rule is stated in
   `CLAUDE.md` as non-negotiable and overriding.
2. **A machine is busy.** An experiment is running on this host. Do **not** run heavy commands: no
   unbounded `find`/`grep` over the workspace, no `mvn`, no `uv sync`, no test suites, no builds, no
   `adb` — unless the user explicitly asks. Targeted `Read` by known path is fine. Bound every search
   with `-maxdepth` or a narrow subtree, and prefer reading a file you already know the path of.
3. **NEVER start, stop or manage Android emulators.** No `emulator`, no `adb emu kill`, no
   exceptions, including for validation. `rv-experiment` / `rv-platform` own the whole lifecycle.
   This rule is permanent and is *why* the plan looks the way it does (§4).
4. **Never add `Co-Authored-By`** or any co-author trailer. The user is the sole author.
5. **Language:** code, comments, commit messages, GitHub issues and OpenSpec artefacts in **English**;
   prose addressed to the user in **Brazilian Portuguese with correct accentuation**. The ideation
   document is in Portuguese — keep it that way if you touch it.
6. **P1–P4 principles** (`docs/WORKFLOW.md` §4, `CLAUDE.md`): simplicity; narrative docs that explain
   *why*; no backward compatibility (delete dead code, back it up under the gitignored `backup/`
   first); current-state comments only.
7. **Terminology:** "MOP" = *monitored operations*, never "security operations".
8. **Read-only data.** `$WS/ase-journal/dataset/results`,
   `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/` and `$WS/rvsec-dataset/repos` are
   **read-only**. Extract to the session scratchpad; never write into them.
9. Use the session scratchpad for temporary files, never `/tmp` directly.
10. **Do not touch the MetaCrySL tree.** It belongs to another session.
11. `git status` at session start shows ~20 files modified by other work. Before claiming anything
    about modified code, diff against the session-start snapshot.

---

## 3. Read these, in this order

| # | path | what it is |
|---|---|---|
| 1 | `docs/20260806_ideacao_consertos_instrumentador_e_specs.md` | **the Phase-0 output — start here.** §6.4/§6.5/§6.6 and §7/§8 are what this session acts on |
| 2 | `docs/WORKFLOW.md` | §1 Phase 0, §2 backlog/board protocol, §3 track selection, §4 principles, §6–§8 the three tracks |
| 3 | `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` | the investigation report (6 revisions, ~1400 lines) — background, do not re-derive |
| 4 | `docs/20260806_plano_specs_jca_android.md` | the spec-adaptation plan, phases F0–F7, decisions D1–D6 (**D1 and D4 matter here**) |
| 5 | `docs/20260423_plano_validacao.md` | the 6-layer validation framework and its pre-registered gates |
| 6 | `docs/20260426_dexlib2_validation_results.md` | what actually ran; §5.3 is where Layer 3 was declared N/A |
| 7 | `.claude/AGENTS.md` | skills and orchestrators reference |
| 8 | `docs/20260806_handoff_rv_platform_and_layer3_driver.md` | the previous handoff — superseded by this one, kept for the verified-facts tables in its §7 |

---

## 4. The story in one page

The dexlib2 DEX-native weaver has three silent defects that corrupt what RVSEC reports: a wrapper
collision that **fabricates** violations, an empty-slice binding problem that **mis-attributes** them,
and an inline truncation that **erases** an entire `ErrorType` category. The investigation is closed.
What is open is engineering: what to change in the weaver and in the JCA/Android specs, and how to
prove the fixes.

The validation question was answered twice, and the second answer is the one that stands:

- **First:** revive Layer 3 of the 6-layer validation framework — the pre-registered gate that
  compares event *sets* between the ajc and dexlib2 weavers against a YAML oracle. Decided 2026-08-06.
- **Then, the same day:** the strict per-APK instrument (**L3-a**) needs the deterministic UI driver
  `scripts/drive_cryptoapp.py` to run inside a booted emulator with the APK installed. The analysis of
  `rv-platform` confirmed that the only legal window is inside `TaskExecutor._run_emulator_session`,
  reachable only as an `AbstractTool` plugin — i.e. **new Python code in `rv-android`**. The user
  decided **not to open that front**. So **L3-a is parked**, and the acceptance criterion for the
  weaver fix migrated to the Java side: **V0** (an advice with N `monitorCalls` emits N invokes) and
  **V2** (the 9 events appear as `invoke-static` in the woven DEX). Weaker — it proves emission, not
  arrival in logcat — but still fails before the fix and passes after, which the 2026-05-06 substitute
  (`cov_rv_method`) did not.
- **L3-b and L3-c are unaffected** and stay in scope: neither needs a driver, an emulator, or a line
  of Python. L3-b derives oracles from `out/run_jca_compare_consolidated/events_fair.csv` (55,169
  paired ajc × dexlib2 events, 8 APKs under both variants) and targets defect 1. L3-c derives from
  `$RESULTS/errors_unit_tests.csv` (JVM `-javaagent` regime) and is the **only** regime where the
  erased `UnsatisfiedConstraint` category exists at all.

All of this is written up, with sites and line numbers, in the ideation document. **Do not re-derive
it. Do not re-open it.**

One late finding that belongs to change 2 if L3-a is ever unparked: **the driver is not
deterministic, and the source of the app is ours.** `CipherUtil.encrypt` builds an unseeded
`new Random()` per call (`examples/cryptoapp/app/src/main/java/br/unb/cic/cryptoapp/cipher/CipherUtil.java:16`)
and branches on `nextInt(10) > 6` (`:19`) — the 30% branch is `aes()`, which holds the `SecretKeySpec`
of oracle event 8 (`:40`), and the 70% branch is `des()` (events 3/4/5). The script's 30 clicks leave
P(no AES) = 0.7³⁰ ≈ 2.3·10⁻⁵ of losing the discriminant itself. Two answers, both written up in §6.5
of the ideation document: condition the verdict on an independent branch witness (the `RVSEC-COV` line
for `CipherUtil.aes`), which touches no APK; or remove the coin in the app, which costs re-dating the
oracle and desynchronises the versioned `apks_examples/cryptoapp.apk` from its source.

---

## 5. The changes to create

From §7 of the ideation document, already reconciled with the decisions above:

| # | change | scope | track | modules | depends on |
|---|---|---|---|---|---|
| 1 | weaver counters + observability | counters end to end; log the resolved `android.jar` | **FF SDD** | `$DEXLIB2/cli`, `rv-instrumentation-dexlib2`, `rv-instrumentation-core` | — |
| 2 | revive Layer 3 **without L3-a** | unblock the oracle gate with derived oracles, fix the §5.4 premises, run L3-b and L3-c | **Full SDD** | `$DEXLIB2/validator` | — (parallel to 1) |
| 3 | weaver emission fidelity | inline truncation + wrapper collision + fail-open `parseCommonPointcut` | **Full SDD** | `$DEXLIB2/{advice-emitter,dex-mutator,pointcut-engine}` | 1 and 2 |
| 4 | spec authoring fixes | binding + `fsm` + `gtm1`, in **both** spec sets | **FF SDD** | `$JCA`, `$JCA_ANDROID` | 3 |
| 5 | `CipherSpec` / `isValid` parameterised | the debt gh99 left open | **Full SDD** | `$CORE`, `$JCA`, `$JCA_ANDROID` | 4 |
| 6 | predicate-graph reconnection | 37 missing edges | **Full SDD** | `$JCA`, `$JCA_ANDROID`, `$CORE` | 4 |

Order: **1 and 2 in parallel → 3 → 4**, with 5 and 6 after. **2 before 3** is load-bearing: the
acceptance criterion of 3 is a test that must **fail before** the fix. Fixing first and validating
after is the exact failure mode that let defect 3 survive fifteen months.

Note that changes 1–3 and 5–6 touch the **sibling Java reactor**, not `rv-android`. Only their
`openspec/changes/` artefacts live in this repo. Change 1 also touches two `rv-android` Python
modules — flag that to the user before opening it, given the decision in §4.

---

## 6. Decisions to settle before creating anything

Ask the user. One at a time — they have asked for that pace explicitly, and they want a field to
write their own answer, so use `AskUserQuestion` (its "Other" option provides that field). Present
options **and a recommendation with its reason**, not a menu.

1. **Which changes to open now — and the board constraint that argues for "none yet".** There are
   **9 open change directories** (`gh-tbd-env-vars-architecture`, `gh48`, `gh69`, `gh77`, `gh78`,
   `gh79`, `gh95`, `gh97`, `gh98`), three of them nearly closed — **gh95 56/57, gh97 66/67, gh98
   45/48** — and `docs/20260806_plano_specs_jca_android.md` §14 **D4** says to close the open changes
   and submit before taking on this front. Opening changes 1 and 2 now competes with that. This must
   be put to the user explicitly, not decided silently.
2. **Do L3-b and L3-c go in one change or two?** (§8.3 of the ideation doc, reformulated now that
   L3-a is out: the question is no longer "with or without L3-a" but "together or apart".) L3-b is
   nearly free — the paired runs already exist on disk. L3-c needs a generator and a
   provenance-filter decision.
3. **Granularity** (§8.4): six changes, or merge 1+3 (one weaver change) and 4+5 (one spec change)?
4. **D-A3** (§8.5): does the "count before fixing" step become a task inside change 3, or does the
   fix go in directly?
5. **D-E1** (§8.6): unify on the `batch` subcommand (loses the explicit APK subset) or extend the
   `instrument` subcommand?

Already decided — **do not re-litigate**: the Layer-3 revival itself; the third oracle derived from
existing AspectJ executions; not touching `rv-android` (and therefore L3-a parked and the criterion
migrated to V0/V2); and plan §14 **D1**, which puts the layer-2 spec fixes in **both** spec sets with
the loss of exact reproduction of the published numbers recorded in the replication package.

---

## 7. The mechanics, exactly as `docs/WORKFLOW.md` §2 defines them

**Issues live in `PAMunb/rvsec` (the repo root), not in `rv-android`.** Templates:
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/.github/ISSUE_TEMPLATE/`
— five of them (Feature, Enhancement, Bug, Refactoring, Documentation), each pre-assigning type and
track labels. The issue's problem statement becomes the direct input to `openspec-new-change`.

**Naming and cross-referencing:**

- change directory `openspec/changes/gh<N>-<short-name>/` — lowercase, **no date prefix**
  (`openspec archive` adds the date)
- `proposal.md` header carries `GitHub Issue: #N` (Quick Path: `plan.md` header)
- commits use `refs #N` during work, `closes #N` in the final one
- PR body includes `Closes #N`

**Creating the change** (through the skills, never by hand):

- Full/FF SDD use the default `rv-sdd` schema — no flag
- Quick Path needs `--schema quick-path`
- the `.openspec.yaml` written into the change directory records the schema for later commands

**Board** — [GitHub Project #7](https://github.com/orgs/PAMunb/projects/7). Automation is unreliable:
new issues land in **"No Status"**, not Backlog, and closing an issue does **not** move its card. All
transitions are manual, via `gh project item-edit` (`~/.local/bin/gh`, authenticated, has `project`
scope):

```bash
# Project: PVT_kwDOAJRqj84BPHtv   Status field: PVTSSF_lADOAJRqj84BPHtvzg9n4kM
# Options: Backlog=efb2287e, In Progress=88b03dd2, In Review=eb8dfe26, Done=53305933
gh project item-list 7 --owner PAMunb --format json          # find ITEM_ID
gh project item-edit --project-id PVT_kwDOAJRqj84BPHtv --id <ITEM_ID> \
  --field-id PVTSSF_lADOAJRqj84BPHtvzg9n4kM --single-select-option-id efb2287e
```

Issue **state** (open/closed) goes through MCP `issue_write`; the **column** goes through the CLI
above. On creating work: card to **Backlog** on triage, then **In Progress** when the SDD phase
starts.

---

## 8. Facts already verified — do not re-derive, but do not trust blindly

All checked against source in earlier sessions. Line numbers exact as of `ceb87234`.

**The weaver defects**

| defect | sites |
|---|---|
| 1 — wrapper collision (fabricates) | key at `DexWeaver.java:145`, naked `put` at `:159`; the `containsKey` guard that is exactly what is needed already exists at `:208` |
| 2 — empty-slice binding | `$JCA/TrustManagerFactorySpec.mop:44` binds `k` instead of the spec parameter; state inherited via `sourceLeaf.clone()` at `$MONITOR:17952` |
| 3 — inline truncation (erases) | `EmitContext.java:51-52`, `MonitorInvokeBuilder.java:238-241` (used at `:50`, `:136`, `:217`), `StaticInitializationEmitter.java:145-148`, `AfterThrowingEmitter.java:72`; `WrapperEmitter.java:637` iterates correctly |

Root cause of 1/2 in javamop: fusion requires `advice.retVal.equals(event.getRetVal())`
(`$JAVAMOP/output/combinedaspect/event/EventManager.java:91`) while `MOPParameter.equals` compares
**type *and* name** (`$JAVAMOP/parser/ast/mopspec/MOPParameter.java:22-23`).

Defect 3 scope, re-derived independently: **7 advices truncated, 9 events dropped, all 7 the
constructor branch** — `WrapperEmitter.shouldWrap(a)` is just `"after".equals(a.getPosition())`
(`:138-140`) and every fused advice in the production descriptor is `after`, so the
`shouldWrap`-false branch contributes zero; what falls to inline is the explicit constructor
`continue` at `WrapperEmitter.java:215-219`. All 9 dropped are error emitters.

**The validation infrastructure**

| piece | path | state |
|---|---|---|
| trace comparator | `$DEXLIB2/validator/.../TraceComparator.java` | implemented; `analyze` and `batch` modes |
| CLI | same dir, `ValidationCli.java` — `layer3 --oracles --apks [--batch] [--mandatory]` | `--mandatory` (gh56 `INV-INS-73`) fails on any deviation, honoured in both modes (`:208-218`) |
| canonical oracle | `$DEXLIB2/validator/oracles/cryptoapp-oracle.yaml` | 8 events; **event 8** is `SecretKeySpecSpec`/`UnsatisfiedConstraint`, one of the 9 the truncation erases |
| oracle count gate | `OracleLoader.MINIMUM_ORACLES = 3` | the blocker — two files exist, one an empty template |
| static oracle | `BaksmaliDiffer.java` | **shares the defect's premise** at `:216` (`getMonitorCalls().get(0)`) — must be fixed before it can see the fix |
| tests that inherit the premise | `EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121` | build fixtures via `get(0)`; no advice with N>1 is exercised anywhere |

Comparator semantics that shape any gate built on it: `matched()` is **existential** and **ignores the
oracle's `location` field** (`TraceComparator.java:486-495`); `countFalsePositives()` counts **per
occurrence** (`:497-509`), so with F1 ≥ 0.98 over 1–2 oracle entries per spec **a single FP already
fails**. `batchAnalyze` consumes the `rv-platform` results tree verbatim
(`<results>/<apk>.apk/<apk>.apk__<rep>__<timeout>__<tool>.logcat`, `:83`/`:191`), while analyze mode
wants a hand-built `<apkSubsetDir>/<oracle>/{ajc,dexlib2}.logcat` layout (`:49-50`).

**Weaver counters never reach Python, and the reason is earlier than the parser:** `--results-json`
exists only on the `batch` subcommand (`InstrumentationCli.java:129-137`), and the production path
uses the single-APK `instrument` subcommand without it (`dexlib_instrumentation.py:245-252`).
Evidence: **289 `instrument_errors.json` and zero `instrument_results.json`** in the whole tree.
Fixing `_parse_results_json` and `InstrumentationResults` alone restores nothing.

**The spec fixes still pending after gh99** (archived; it changed **allow-lists only**, so the
authoring defects crossed into the new set on the same line numbers): `TrustManagerFactorySpec.mop:44`
binding; `SSLContextSpec.mop:46` missing `returning`; **the `fsm` part is mandatory** — neither `g3`
nor `unsafe_protocol` appears in its spec's `fsm`/`ere`, so the generator gives them `{3,3,3,3}` and
fixing the binding alone produces spurious `InvalidSequenceOfMethodCalls`; `gtm1` (`:62-65`) has a
wrong `Property` constant, a `TrustManager[][]` binding and a `KeyManager[]` return type that never
matches.

**The numbers:** 97,018 events (163-app analysis basis) / 165,999 (219-app executed basis);
`UnsatisfiedConstraint` = 0 under dexlib2 on both bases and **43** in the AspectJ unit-test control
group; `SSLContextSpec` 26,312 (27.1%); `TrustManagerFactorySpec` 18,029;
`InvalidSequenceOfMethodCalls` 70,760 (72.9%); production descriptor 115 advices, 17 with more than
one `monitorCall`.

---

## 9. Paths

Inside `rv-android` (relative):

| what | path |
|---|---|
| **Phase-0 ideation (the input)** | `docs/20260806_ideacao_consertos_instrumentador_e_specs.md` |
| investigation report | `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` |
| spec plan | `docs/20260806_plano_specs_jca_android.md` |
| validation framework / results | `docs/20260423_plano_validacao.md`, `docs/20260426_dexlib2_validation_results.md` |
| workflow (authoritative) | `docs/WORKFLOW.md` |
| skills & agents | `.claude/AGENTS.md` |
| env vars / docker / commands | `.claude/project-info.md` |
| open changes | `openspec/changes/` |
| schemas | `openspec/schemas/{rv-sdd,quick-path}/` |
| domain specs | `openspec/specs/README.md` |
| paired ajc × dexlib2 events (L3-b source) | `out/run_jca_compare_consolidated/events_fair.csv` |
| production descriptor | `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` |
| the parked driver | `scripts/drive_cryptoapp.py` |
| the app under test — **source, and it is ours** | `examples/cryptoapp` (Gradle project; `app/src/main/java/br/unb/cic/cryptoapp/cipher/CipherUtil.java`) |
| gh99, archived | `openspec/changes/archive/2026-08-06-gh99-metacrysl-jca-android/` |

Outside (absolute; `$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`):

| what | path |
|---|---|
| issue templates | `$WS/rvsec/.github/ISSUE_TEMPLATE/` |
| the 23 JCA `.mop` specs | `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca` |
| the 23 derived Android specs | `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android` |
| DEX weaver (`$DEXLIB2`) | `$WS/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2` |
| validator + oracles | `$DEXLIB2/validator` |
| javamop source | `$WS/rvsec/javamop/src/main/java/javamop` |
| `Property` / `ExecutionContext` / `CipherTransformationUtil` (`$CORE`) | `$WS/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop` |
| generated monitor (git-ignored, `$MONITOR`) | `$WS/rvsec/rvsec/rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` |
| campaign results, processed (`$RESULTS`) — **read-only** | `$WS/ase-journal/dataset/results` |
| campaign results, raw — **read-only** | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS` |
| corpus app sources — **read-only** | `$WS/rvsec-dataset/repos` |

---

## 10. Commands

Nothing here is heavy; keep it that way while the experiment runs.

```bash
# OpenSpec — prefer the Skill tool; these are the CLI equivalents the skills drive
openspec new change "gh<N>-short-name"                      # rv-sdd (Full/FF SDD)
openspec new change "gh<N>-short-name" --schema quick-path   # Quick Path
openspec status
openspec instructions <artifact> --change "gh<N>-short-name"

# GitHub
gh issue create --repo PAMunb/rvsec --template <template>.yml
gh project item-list 7 --owner PAMunb --format json

# Only if the user asks — these are NOT to be run casually while an experiment is up
pytest --import-mode=importlib -o "addopts="                 # the CI contract, always these flags
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec && mvn install
```

---

## 11. Method learnings — carry these over, do not rediscover

1. **The filesystem here is slow, and right now it is also busy.** An unbounded `find`/`grep` over
   `RV_ANDROID_NOVO_DATASET`, `rvsec-dataset` or the whole `rv-android` tree exceeds a 2-minute
   foreground timeout and steals I/O from the running experiment. A previous session made exactly
   this mistake and had to kill the job. Bound it, scope it, or do not run it.
2. **`git status` at session start is not yours.** ~20 files were already modified before this work
   began, six of them `.py`. Diff against the session-start snapshot before claiming anything.
3. **Disassemble per-DEX, never the whole APK.** `d2j-baksmali.sh <file.apk>` processes only
   `classes.dex` and silently misses the `mop/` package, which usually lives in the last DEX.
4. **The production descriptor is stable and datable.** 7 of 8 `MultiSpec_1MonitorAspect.json` files
   generated since June are byte-identical, so measuring `results/gh92_e2e2/monitors/…` measures the
   campaign's.
5. **Two bases ship side by side.** `errors.csv` = 163-app analysis basis (97,018 events);
   `errors_bck.csv` = 219-app frozen executed basis (165,999). State which one you are on, always.
6. **The dataset ships two AspectJ regimes, not one.** `errors_unit_tests.csv` is JVM `-javaagent`;
   `out/run_jca_compare_consolidated/events_fair.csv` is APK-on-emulator paired against dexlib2. They
   answer different questions, and confusing them was the one substantive error of an earlier session.
7. **A `COMPLETED` task is not by itself a valid one** (`modules/rv-platform/CLAUDE.md`): the state
   records that the tool returned without raising, not that the run did the work. Anything consuming
   `tasks.json` must decide admissibility from the artefacts, and must **count per identity, never per
   record**.
8. **Do not propose remediation for what the user has already decided.** When a list, a selection or a
   scope comes from the user, it is final — go straight to execution.

---

## 12. First message to the user

In Brazilian Portuguese. State in two or three sentences where things stand (Phase 0 closed and
committed at `ceb87234`; L3-a parked; the criterion now V0/V2), then put **decision 1 of §6** — which
changes to open now, against the board constraint of 9 open changes and plan §14 D4 — via
`AskUserQuestion`, with options, a recommendation, and the reason for it. One decision at a time.
Nothing gets created before that answer.
