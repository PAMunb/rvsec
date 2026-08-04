# Session Handoff Prompt — APE-RV Re-architecture: `rearch-03-decision-pipeline` **apply**, group 5

> Paste this whole file as the opening message of the next session.
> Run the session from `rv-android` (that is where the skills registry lives); the Java stage work
> happens in the `ape` worktree, which you reach by `cd`. **This stage touches only the `ape` repo.**

This prompt supersedes `20260804_prompt_rearch_stage3_group4_part5.md`. **Group 4 is complete and
committed** (4.5–4.8), the roadmap status log is written, and the worktree is **clean**. What
remains before the change can be verified and archived is **group 5** (`ScoringPipeline` real
injection, 7 tasks), **group 6** (the static-`Config` sweep, 6 tasks) and **groups 7–8**.

**Read §3 before you touch 5.2**: this session scouted group 5 and found that task 5.5a's premise
is wrong in a way that matters — the entry point 5.2 deletes has **five** call sites in `src/test`,
not one, and one of them is `OracleScaffold`, the merge gate's own harness. No task in the change
currently names it.

---

## 0. Where this session starts

Groups 1–4 are done. `rearch-03-decision-pipeline` stands at **27/53 tasks**, 4/4 artifacts,
8 groups. Group 5 is untouched.

Work group 5 in order (5.1, 5.1a, 5.2, 5.2a, 5.3, 5.4, 5.5, 5.5a). **Do not start group 6.** If
that is more than one session, stop at a task boundary with the suite green and a status-log entry
written.

---

## 1. Read this first, in this order

1. `ape/docs/plans/20260802_rearchitecture_roadmap.md` — **the coordinating instrument for both
   repositories**. Read the last entry (2026-08-04, "Stage 3 group 4 closed"), which records what
   the five LLM units own, the four corrections group 4 forced, and the note for group 6 about
   `ape.graphStableRestartThreshold`.
2. `ape/openspec/changes/rearch-03-decision-pipeline/tasks.md` — read **5.1 through 5.5a** word for
   word. 5.5a's "no other task names the file" clause **is known to be incomplete** — see §3.1.
3. `ape/openspec/changes/rearch-03-decision-pipeline/design.md` — **D8** (why the goldens cannot
   see a scoring-default change), **D1** (the `RUN_START` echo is write-only, level 0), and the
   risk-register entries for scoring-params injection and for `greedyPickLeastVisited`.
4. `ape/openspec/specs/scoring-pipeline/spec.md` — **INV-ARCH-02** (an empty pipeline is a strict
   no-op), **INV-ARCH-03** (the fixed pass order, frontier family contiguous), **INV-ARCH-04** (the
   single public entry point) and **INV-ARCH-11** (pass unit tests supply their own params). Read
   them in the original.
5. `ape/openspec/specs/parity-oracle/spec.md` — **INV-ORA-07 still binds** (goldens and scenario
   scripts SHALL NOT change; only the injection scaffold may adapt) and **INV-ORA-03** (no oracle
   path may reach the breaker or the wall clock).
6. `ape/docs/analise_fable-selecao.md` (rev. 3) — source of truth. **Do not reopen D1–D6.**

---

## 2. What landed in the last session

### Tasks 4.7 and 4.8 — committed, `598b00c8` and `076a7c4b`

`LlmRouter` is deleted with no facade: 996 LOC in `src/main` referenced by no other main file, plus
`LlmRouterTest` (32) and `LlmRouterToolSchemaTest` (4). `grep -rln "LlmRouter" src/main/java
src/test/java` returns nothing, comments and javadoc included.

Most of the 36 residual tests were **not migrated**, because migrating them would have duplicated
assertions that already exist where the code went. Of the 32: 3 guards moved to
`CoordinateMapperMappingTest`, 1 was retargeted, 3 merged into one assertion group in
`LlmTelemetryTest.summaryExposesLlmTapField`, 11 were already covered by the stage tests 4.6 wrote,
4 by `LlmClientTest`/`ToolCallParserTest`/`CoordinateMapperOffTreeTapTest`/`ConfigTest`, 6 were
vacuous, 2 were dropped deliberately, 2 were trivial.

Three of those are precedents rather than one-offs:

- **INV-RTR-09's check read `LlmRouter.java` off disk**, so deleting the file would have made it
  pass *vacuously at runtime* — not fail at compile time. It now lives in `LlmRandomStageTest` as
  `theNoSubstrateOverrideIsReadByNoDecisionOnThePath` and sweeps two whole directories
  (`agent/pipeline` + `llm`) rather than one named file.
- **`mapToModelAction_useSites_readConfigNotLiterals` asserted the source *contains* four `Config.`
  reads** — the opposite of what this change is for. It was deleted, not retargeted, because 6.5's
  grep-guard asserts zero and constructor injection realizes the intent structurally. **Group 5 and
  6 will meet more tests shaped like this.**
- **Six boundary tests passed an empty actions list**, so `map` returned null at the no-candidates
  branch whatever the boundary branch would have decided (learning 71). The top band, genuinely
  uncovered, got the honest form: a resolvable candidate left in place, so the null is attributable.

4.8 was an audit. The five llm units carry 1,479 lines with five symbols lacking javadoc, and all
five classify as skip under `sdd-doc-code`'s own table. Its honest output was three re-flows of
line wraps 4.7's own comment sweep had left ragged. **Nothing was manufactured to justify the task**
(learning 57).

### The `router` sweep

The word is gone from `src/main` and the `llm` tests (P4): it had become the name of a class that
no longer exists. `ScenarioScript`'s `routeRandom`/`routesRandom` **stays** — it names a step routed
to the LLM, which still happens, and the scenario format is frozen by INV-ORA-07.

### Gate at `c0f23d3c`

**1067 tests, 0 failures, 19 skipped**, BUILD SUCCESS. Parity gate 14/14.
`git status --short src/test/resources/goldens` empty. `openspec validate --strict` clean;
`--specs --strict` 21 passed; task count 53.

The fall from 1098 decomposes as **−32 −4 deletions +3 moved +1 retargeted +1 newly written**.
It is not a regression; report any future move the same way.

---

## 3. What this session scouted about group 5

Re-derive as you go (learning 59) — but start from these.

### 3.1 `fromConfig` has FIVE call sites in `src/test`, and 5.5a names one

Task 5.2 deletes `ScoringPipeline.fromConfig(Config, ScoringContext)`. Task 5.5a says
`PipelineParityTest` is the file that "no other task in any of the seven changes names". That is
true of `PipelineParityTest` specifically and **misleading about the blast radius**:

| File | Sites | Covered by a task? |
|---|---|---|
| `main/.../agent/StatefulAgent.java:198` | 1 | yes — 5.2 names it as "the sole caller" |
| `test/.../agent/PipelineParityTest.java` | `:129`, `:165` | yes — 5.5a |
| `test/.../agent/scoring/ScoringPipelineTest.java` | `:137`, `:152`, `:161` | arguably 5.5 ("pass/scorer unit tests") |
| `test/.../agent/BasePriorityCharacterizationTest.java:91` | 1 | **no task names it** |
| `test/.../oracle/OracleScaffold.java:553` | 1 | **no task names it — and it is the merge gate's own harness** |

**`OracleScaffold` is the one to think about before writing any code.** The parity gate builds the
agent through it, so 5.2 breaks the gate's compilation, and adapting the scaffold is exactly the
"injection profile" adaptation INV-ORA-07 permits — but it must be a deliberate, recorded
adaptation, not a compile-fix. Note 5.2 also calls `StatefulAgent:208` "the sole caller"; the read
site today is **`:198`**.

**Run `openspec-update-change` before 5.2** to fold these two files into the task text and correct
the line anchor. **Watch the task count — it must stay 53.** Sub-bullets are not tasks; if you
judge that `OracleScaffold` needs its own task, that is a real count change and must be stated as
one, not slipped in.

### 3.2 `fromConfig`'s `cfg` parameter is already decorative, and its javadoc says so

`ScoringPipeline.java:51` takes `Config cfg` and never reads it — the javadoc states "present for
signature fidelity with the spec; the pass gates read `Config`'s `public static final` fields
directly", and all five call sites pass `null`. So 5.2 is not changing where the values come from
for the *pipeline*; it is changing where they come from for the **passes**, which is 5.3. Sequence
accordingly: a `fromParams` that still lets each pass read static `Config` in `isEnabled()` would
compile, pass, and deliver nothing.

### 3.3 The eight keys, their features and their jar defaults

5.1a pins these as literals. Verified against `KeyOwnership.java` at `c0f23d3c`:

| Key | Feature | Default |
|---|---|---:|
| `ape.mopWeightDirect` | `MOP` | 500 |
| `ape.mopWeightTransitive` | `MOP` | 300 |
| `ape.mopWeightWtg` | `WTG` | 200 |
| `ape.mopWeightOpenMenu` | `MENU_GATEWAY` | 250 |
| `ape.frontierBoostWeight` | `FRONTIER` | 200 |
| `ape.mopFrontierWeight` | `MOP_FRONTIER` | 0 |
| `ape.coverageBoostWeight` | `COVERAGE_BOOST` | 100 |
| `ape.formCompletionEnabled` | `FORM_COMPLETION` | true (boolean) |

Note `mopFrontierWeight`'s default of **0**: `MopFrontierPass` is additive and disabled unless the
weight is positive, so a default-plan `ScoringParams` assembles **six** passes, not seven.

### 3.4 Where the static `Config` reads actually are

`grep -c "Config\." src/main/java/.../agent/scoring/` returns **6**, in four files: `WtgPass`,
`FrontierPass`, `FormCompletionPass`, `CoveragePass`. `MopScorer` — which 5.3 also names — is **not
in that package**: it lives at `src/main/java/com/android/commands/monkey/ape/utils/MopScorer.java`
and carries 6 more. 6.5's grep-guard covers "the scoring package"; `MopScorer`'s location means the
guard as worded would miss it. Raise that when you get to 6.5, not now.

### 3.5 The drift-guard argument in 5.1a is real, so do not weaken it

The goldens never execute scoring (`StatefulAgent.java:1475-1478`), the pass unit tests supply
their own params (INV-ARCH-11), the `RUN_START` echo is write-only (D1), and `rearch-01`'s
per-preset `Config` guard covers only the values the ladder reads. `ScoringParamsDefaultsTest` is
therefore the **only** thing standing between a mistyped default and a silently different
exploration. Write it with literals, not with references to the constants it is guarding — that is
the tautology 5.5a asks you to remove from `PipelineParityTest`
(`assertEquals(..., Config.mopWeightOpenMenu, menu.getMenuBoost())` compares the constant to itself
and passes under any value).

---

## 4. The work, in order

### 4.1 Re-establish the gate before trusting anything

```bash
WS=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
cd $WS/ape-rearch
git log --oneline -1                                     # expect c0f23d3c
git status --short                                       # expect EMPTY
git status --short src/test/resources/goldens            # MUST print nothing
grep -rn "fromConfig" src/main/java src/test/java        # expect the 5 files of §3.1
```

### 4.2 The artifact update group 5 is owed, BEFORE 5.2

Per §3.1: fold `OracleScaffold` and `BasePriorityCharacterizationTest` into the task text and fix
5.2's `StatefulAgent:208` → `:198`. Through **`openspec-update-change`**, never by hand.

### 4.3 Then the tasks, one commit each

`refs rearch-03`, no `Co-Authored-By`. Tick `- [ ]` → `- [x]` **through `openspec-apply-change`**,
never by hand (§6).

### 4.4 The gate after each task

```bash
# the scoring units
mvn -o test -Dtest='ScoringPipelineTest,PipelineParityTest,BasePriorityCharacterizationTest,MopScorerTest' 2>&1 | grep -E "Tests run:|BUILD"

# the parity gate — the merge gate of this change (INV-DP-09)
mvn -o test -Dtest='ParityOracleApervTest,ParityOracleMopTest,ParityOracleLlmTest,ParityOracleLlmMopTest,PreemptionGoldenTest' 2>&1 | grep -E "Tests run:|BUILD"
# expect 2 + 2 + 2 + 2 + 6 = 14 tests, 0 failures

# everything
mvn -o test 2>&1 | grep -E "Tests run:.*Skipped|BUILD"
git status --short src/test/resources/goldens            # must still print nothing
```

**Expect the total to RISE** as 5.1a and the injection-contrast test of 5.5 land. Report the delta
with its decomposition, not as a bare number.

---

## 5. Then the status log

Add an entry to `ape/docs/plans/20260802_rearchitecture_roadmap.md` in the established style. It
must carry:

- the gate numbers **with the skip decomposition** (never the bare total) at each commit;
- what `ScoringParams` owns and, specifically, that a default plan assembles **six** passes because
  `mopFrontierWeight` defaults to 0;
- how the `OracleScaffold` adaptation was made and why it is INV-ORA-07-permitted rather than a
  deviation;
- the candidate census of 5.2a: what `PIPELINE.candidates` carries and why there is no
  `disabledReason()` on the interface;
- anything the scouting of §3 turned out to be wrong about.

---

## 6. Workflow — non-negotiable

From `rv-android/CLAUDE.md`: **use the OpenSpec skills, never write artifacts manually.**

- `openspec-apply-change` for implementation and for ticking `- [ ]` → `- [x]`. Ticking a checkbox
  is the **only** artifact edit the apply skill owns. Run `openspec` commands from inside
  `$WS/ape-rearch`; the change resolves there under schema `sdd-full`.
- Any change to a task's *text*, or to `proposal`/`design`/`specs`, goes through
  `openspec-update-change`. **One is owed this session** (§4.2). **Watch the task count.**
- `openspec-verify-change` then `openspec-archive-change` **when the whole stage is done** — not
  after one group.
- The `ape` repo has its own `openspec-*` skills but **no `openspec-update-change`** — use
  rv-android's copy; it is repo-agnostic and resolves the nearest `openspec/` from the cwd.
- The `ape` repo's `sdd-*` skills are on disk at `ape-rearch/.claude/skills/` but **not** in the
  Skill tool's registry from an rv-android-rooted session. Read the `SKILL.md` and follow it
  manually, and say so in the commit.
- **`backup/` is gitignored in `ape-rearch`**; the convention `backup/<date>-<topic>/` is live and
  `backup/20260804-rearch-03-group4/deleted/` holds group 4's deletions. Put deletions there before
  deleting (P3).
- Portuguese in conversation with correct accentuation; English in artifacts, code comments and
  commit messages. P1–P4 are non-negotiable — especially **P3** (no adapter, shim, alias, wrapper or
  deprecation period; `fromConfig` dies with no delegating overload) and **P4** (comments describe
  the current state; no migration history, no promotional language).

### Scope discipline

**No golden may change. No scenario script may change. No Python may change. No `mvn install`.**
Group 6 owns the static-`Config` sweep outside the scoring package — do not start it early, and do
not "notice and fix" `SataAgent:22`'s unused static import of `graphStableRestartThreshold` (it is
recorded in the roadmap as a 6.4 note). The known `type_text` defect is reproduced, not fixed: a
`type_text` answer can execute a `MODEL_LONG_CLICK`, 28 of 1,233 LLM responses (2.3%);
`CoordinateMapper` reproduces it and names it in its javadoc.

---

## 7. Commands

```bash
WS=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
cd $WS/ape-rearch
export PATH="$ANDROID_HOME/build-tools/35.0.1:$PATH"   # only needed for `package`, not `test`

mvn -o test 2>&1 | grep -E "Tests run:.*Skipped|BUILD"
git status --short src/test/resources/goldens            # must print nothing

# per-class counts when the summary is hidden
cat target/surefire-reports/<class>.txt

# skip decomposition — record this, never the bare total
grep -l "Skipped: [1-9]" target/surefire-reports/*.txt | xargs grep -h "Tests run:"

# artifacts
openspec status --change "rearch-03-decision-pipeline" --json
openspec validate rearch-03-decision-pipeline --strict
openspec validate --specs --strict                       # 21 passed
grep -c "^- \[ \]\|^- \[x\]" openspec/changes/rearch-03-decision-pipeline/tasks.md   # must stay 53
```

`ape/openspec/config.yaml` has an invalid `references:` field — a harmless warning prints before the
JSON on every `--json` call. Find the first `{` before parsing; a plain `tail -n +2` is not always
enough. Left untouched deliberately.

**Always `cd` into the worktree before any `openspec` command** — OpenSpec 1.7 has no cross-repo
support and will silently resolve rv-android's otherwise.

**Never `mvn install`** — `copy-jar-to-aperv-tool` is bound to the `install` phase and overwrites the
deployed jar in `rv-android/modules/aperv-tool/.../ape-rv.jar`. `mvn package` stops one phase short.

**Never manage an Android emulator by hand** — no `emulator`, no `adb emu kill`, no manual boot-wait
or install, in any context. Permanent. Device work goes through `rv-experiment run` / `rv-platform
run`. Task 8.4 defers stage 3's on-device smoke to the next scheduled rebuild, consistent with the
owner's 2026-08-04 decision to hold one coordinated end-to-end smoke after every planned change on
both sides has landed.

---

## 8. The numbers to compare against

- **`rearch-03-decision-pipeline`: 27/53 tasks** (1.1–1.6, 2.1–2.9, 3.1–3.4, 4.1–4.8), 4/4
  artifacts, 8 groups.
- **Suite at `c0f23d3c`: 1067 tests, 0 failures, 19 skipped**, BUILD SUCCESS.
- The 19 skips decompose as **13 `@Ignore`** (`ImageProcessorIntegrationTest` 5, `ImageProcessorTest`
  4, `ApePinchOrZoomEventTest` 3, `GUITreeBuilderPasswordTest` 1) + **6 `Assume`** in
  `SglangLiveTest`, environment-dependent: with `SGLANG_URL` exported those six run and the total
  stops being 19. **Keep the environment constant across comparisons and record the decomposition,
  not the total.**
- The parity gate: `ParityOracle{Aperv,Mop,Llm,LlmMop}Test` 2 each + `PreemptionGoldenTest` 6 =
  **14 tests**. It has held at 14/14 after every task so far.
- `PipelineParityTest` has **5** `@Test`; `ScoringPipelineTest`'s assembly matrix is at `:124–:165`.
- `openspec validate rearch-03-decision-pipeline --strict` clean; `--specs --strict` 21 passed.

---

## 9. Key files

### The change in flight
- `ape/openspec/changes/rearch-03-decision-pipeline/tasks.md` — 53 tasks in 8 groups; 27 done
- `.../design.md` — **D8**, **D1**, D7, D9, plus the risk register
- `.../specs/scoring-pipeline/spec.md` (INV-ARCH-01..11), `.../specs/decision-pipeline/spec.md`
  (INV-DP-01..12)

### Group 5's targets
- `ape/src/main/java/.../ape/agent/scoring/` — `ScoringPipeline.java` (`fromConfig` at `:51`),
  `ScoringContext.java`, `ScoringPass.java`, and the seven passes
- `ape/src/main/java/.../ape/utils/MopScorer.java` — 6 static `Config` reads, **outside** the
  scoring package
- `ape/src/main/java/.../ape/agent/StatefulAgent.java:198` — the production call site
- `ape/src/main/java/.../ape/runtime/KeyOwnership.java` — the eight keys and their defaults

### Breaks on 5.2 (see §3.1)
- `ape/src/test/java/.../ape/agent/PipelineParityTest.java` (`:129`, `:165`)
- `ape/src/test/java/.../ape/agent/scoring/ScoringPipelineTest.java` (`:137`, `:152`, `:161`)
- `ape/src/test/java/.../ape/agent/BasePriorityCharacterizationTest.java:91`
- `ape/src/test/java/.../ape/oracle/OracleScaffold.java:553` — **the merge gate's own harness**

### The gate
- `ape/openspec/specs/parity-oracle/spec.md` — INV-ORA-01..07, notably **INV-ORA-03** and
  **INV-ORA-07**
- `ape/src/test/resources/goldens/` — **frozen** through stage 3

### Coordination
- `ape/docs/plans/20260802_rearchitecture_roadmap.md` — **the guide**; status log, gates,
  counterparts
- `ape/docs/20260803_procedimento_worktree_rearch.md` — `mvn install`, `d8` PATH, the stamp misreport
- `ape/docs/analise_fable-selecao.md` (rev. 3) — source of truth
- `rv-android/docs/20260804_prompt_rearch_stage3_group4.md` §11 — learnings 33–63 in full
- `rv-android/docs/20260804_prompt_rearch_stage3_group4_part2.md` §11 — learnings 64–69
- `rv-android/docs/20260804_prompt_rearch_stage3_group4_part3.md` §12 — learnings 70–73
- `rv-android/docs/20260804_prompt_rearch_stage3_group4_part4.md` §12 — learnings 74–76
- `rv-android/docs/20260804_prompt_rearch_stage3_group4_part5.md` §11 — learnings 77–79

---

## 10. On parallelising this

**Group 5 is a strict chain and cannot be parallelised.** Two agents editing `ape-rearch` would
collide on `target/` and on the index, and the parity gate — the merge gate — would run against a
tree neither of them fully owns. **Do not fan out edits.**

The reconnaissance §3 records has been run; do not re-run it — but **do** re-verify the specific
greps §4.1 lists, which cost seconds.

Note that this session's tool policy may say "do not call the Agent tool unless the user requested
it" — treat that as binding unless the owner says otherwise in this session.

---

## 11. Learnings to carry

Numbering continues; 33–63, 64–69, 70–73, 74–76 and 77–79 are all still live (see §9 for where they
are written out). The ones that bit hardest in the last session:

34. **When a test goes red, assert the true behaviour — never loosen the assertion.**
42. **An artifact promise is not self-executing.** Grep for a deleted mechanism's name across all
    specs and all comments.
57. **A doc pass over well-documented code is an audit, and its honest output may be two edits and
    a report.** Do not manufacture edits to justify the task.
59. **A handoff's pre-computed fact can be wrong in exactly the way its own learnings warn about.**
    §3.1 of this prompt is the instance to check first.
71. **A test that passes an empty input cannot prove which branch rejected it.**
72. **A structural test that greps a source file dies silently when the file moves** — at runtime,
    not at compile time.

New from this session (2026-08-04):

80. **A test that asserts a source file *contains* something is a bet against the next refactor,
    and the bet is usually wrong.** `mapToModelAction_useSites_readConfigNotLiterals` pinned the
    presence of four `Config.` reads to guard against hard-coded literals; the re-architecture's
    whole point is that those reads go away. Deleting it was right because constructor injection
    realizes the same intent structurally. **Before retargeting a structural test, ask whether the
    property it pins is still a property the design wants.**
81. **A structural invariant survives relocation only if it is asserted over a scope, not a file.**
    INV-RTR-09's check named `LlmRouter.java`; deleting the file would have made it pass vacuously.
    Sweeping two directories costs the same and cannot be defeated by a move.
82. **"No other task names this file" is a claim about the artifact, not about the code.** Task
    5.5a says exactly that of `PipelineParityTest`, and it is true — while four other files call
    the same entry point, one of them being the parity harness. **Grep the code for the symbol a
    task deletes; do not trust an artifact's account of the blast radius.**
83. **A parameter the javadoc admits is decorative is a warning about the task that removes it.**
    `fromConfig(Config cfg, ...)` never reads `cfg`, and every call site passes `null`. Replacing
    it with `fromParams` therefore changes nothing on its own — the behaviour lives in the passes'
    `isEnabled()`, which 5.3 parameterizes. A task that only swaps the signature would compile,
    pass, and deliver nothing.
