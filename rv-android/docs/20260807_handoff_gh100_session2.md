# Session handoff — gh100, continuing from Groups 1–3

> Paste this whole file as the first message of the new session.
> It supersedes `docs/20260807_handoff_gh100_weaver_emission.md` for everything
> it repeats, but that file is still the authoritative background on *why* the
> change exists. Read it after §3 below.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of
Pedro Costa, `phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

**Git branch is `modules`.** (The previous handoff said `rearch-counterparts`;
that was wrong and the user confirmed `modules` is correct.) The whole tree —
`rv-android` *and* the sibling Java reactor — is **one git repository** rooted at
`$WS/rvsec`. One commit can span both sides, and the commits below do.

`$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`
`$DEXLIB2` = `$WS/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2`

**Anything outside `rv-android` must be written with an absolute path** —
standing user instruction, applies to code, docs and prose.

**A parallel session is implementing gh101 on this same branch** and its commits
are interleaved with yours (see §2). Do not rebase, force-push or reorder. Stage
only paths this change owns. Nothing has been pushed.

---

## 1. What this session must produce

Continue implementing `openspec/changes/gh100-weaver-emission-fidelity/` —
GitHub issue [#100](https://github.com/PAMunb/rvsec/issues/100).

**Groups 1, 2 and 3 are complete (19/45 tasks).** Groups 4–7 remain, plus one
correction that must land first (§4).

Do **not** implement gh101. Do not edit its artefacts.

---

## 2. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md`. Then
`docs/WORKFLOW.md` — the authoritative process reference.

1. **Follow the OpenSpec workflow rigorously.** Anything under
   `openspec/changes/gh100-*/` goes through the **skills** invoked via the
   `Skill` tool: `openspec-apply-change`, `openspec-update-change`,
   `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change`
   (the `/opsx:*` aliases are the same skills). **Never** hand-write or hand-edit
   an OpenSpec artefact outside a skill that told you to. Implementation code is
   normal work — the rule is about the artefacts.
   *Caveat learned:* the `openspec-update-change` skill mandates confirming each
   edit with the user before writing. Batch the diffs into one `AskUserQuestion`
   rather than asking three times.
2. **NEVER start, stop or manage Android emulators.** No exceptions, including
   for validation. This is why L3-a is out of scope and why the acceptance
   criterion is V0/V2 on the Java side.
3. **Never add `Co-Authored-By`** or any co-author trailer.
4. **Language:** code, comments, commit messages, GitHub issues and OpenSpec
   artefacts in **English**; prose addressed to the user in **Brazilian
   Portuguese with correct accentuation**.
5. **P1–P4 principles** (`docs/WORKFLOW.md` §4): simplicity; narrative docs that
   explain *why*; no backward compatibility; current-state comments only.
6. **Terminology:** "MOP" = *monitored operations*, never "security operations".
7. **Read-only data.** `$WS/ase-journal/dataset/results`,
   `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/` and
   `$WS/rvsec-dataset/repos` are **read-only**. The L3-c derivation reads
   `$WS/ase-journal/dataset/results` and must never write there.
8. **Do not touch the MetaCrySL tree** (`$WS/MetaCrySL`).
9. Use the session scratchpad for temporary files, never `/tmp` directly.
10. **Commits**: `refs #100` during work, `closes #100` only in the final one.
11. **Ask before running anything heavy.** A campaign has been occupying this
    machine on and off. A reactor build is ~4 min; a single-APK instrumentation
    is ~90 s.

---

## 3. Read these, in this order

| # | path | what it is |
|---|---|---|
| 1 | `openspec/changes/gh100-weaver-emission-fidelity/proposal.md` | why the change exists |
| 2 | `.../specs/instrumentation/spec.md` | delta spec: 6 ADDED, 1 MODIFIED, INV-INS-104 to 108 |
| 3 | `.../design.md` | D-E1, D-A1/A2/A3, D-B1, D-O1/O2 |
| 4 | `.../tasks.md` | the 7 groups; 1–3 are checked off |
| 5 | `docs/20260807_handoff_gh100_weaver_emission.md` | the original handoff — the full story of the three defects |
| 6 | `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` | the closed investigation (~1400 lines). §3 wrapper collision, §4.8 inline truncation, §11 the control group, §12.4 where the counters die. **Do not re-derive it** |
| 7 | `docs/LIMITATIONS.md` | §"Known defects left unrepaired" — two defects found this session, deliberately not fixed |
| 8 | `docs/WORKFLOW.md` | §2 board protocol, §4 principles, §6 Full SDD |

---

## 4. FIRST TASK — a correction that must land before Group 4

**The L3-b and L3-c oracles were committed at the wrong granularity. Fix them
before anything else.**

### What happened

I keyed both derived oracles on `(spec, errorType)`, arguing that
`TraceComparator.matched()` is existential and ignores the oracle's `location`
field, and that class names diverge between variants under R8 so matching on
them "would measure the minifier".

The user rejected this and pointed at the paper (`$WS/ase-journal`). The user is
right. `results-rq1.tex:41` defines the canonical unit verbatim:

> A unique misuse is defined as a distinct **(app, class, method, specification)**
> tuple. The first three elements identify the location of the misuse within an
> application, whereas the specification identifies the particular JCA usage rule
> that was violated.

and the analysis code agrees: `data-analysis/repair_summary_outcome.py:53`
(`MISUSE_KEY = ("class", "method", "spec")`),
`data-analysis/analyze_intersection_rv_cc.py:39` ("The CANONICAL VENN is level 4
(apk_class_method_spec)").

So the key is **`(apk, class, method, spec)`** — location is *in*, and
`error_type` is *out*. My key was wrong in both directions. The argument I used
was about what a tool currently does, not about the right unit of analysis; if
`TraceComparator` ignores location, that is the comparator being misaligned with
the paper, not a licence to change the unit.

### The R8 objection was also wrong, and the real cause is known

The strings that made me think "obfuscation diverges between variants" look like:

```
okio.ByteString.digest$okio(r8-map-id-ffcc…:17).okio.ByteString.digest$okio(r8-map-id-ffcc…:17)
```

That is `class == method == the whole stack frame`. It is the **frame-form
defect** documented in `$WS/ase-journal/data-analysis/repair_frame_keys.py`: the
on-device summarizer (`ErrorDescription.java:9`) parses `pkg.Class.method(File.ext:NN)`
with a method group of `\w+`, which rejects `$`, `-` and space; Kotlin-mangled
names fall through and the fallback copies the entire frame into both columns.

Fixed at source in rv-android `cf234788`. **`out/run_jca_compare_consolidated/events_fair.csv`
predates the fix** (dated 4 May 2026) and carries **2,476 frame-form rows of
55,169**. The dataset sheets under `$WS/ase-journal/dataset/results` are already
repaired (`errors.csv`: 0 repaired), so L3-c's source is clean and only L3-b's
needs the repair applied at derivation time.

The repair rule, from that script: strip the suffix-anchored trailing
`(File.ext:NN)` group, then split the remainder at its **last** `.` into
`(class, method)`.

### The analysis is already done — do not redo it

With the repair applied and keyed on `(apk, class, method, spec)` over the 8
paired APKs:

```
ajc = 13   dexlib2 = 18   both = 12   only-ajc = 1   only-dexlib2 = 6
```

only in ajc (dexlib2 misses):
- `MessageDigestSpec | jh.h.c | gizz.tapes.foss_63.apk`

only in dexlib2 (fabricated — the wrapper-collision signature):
- `TrustManagerFactorySpec | n3.n.n | com.destructo.botox_43.apk`
- `TrustManagerFactorySpec | okhttp3.internal.platform.Platform.platformTrustManager | com.infomaniak.meet_28.apk`
- `TrustManagerFactorySpec | okhttp3.internal.platform.Platform.platformTrustManager | com.wirelessalien.android.moviedb_33.apk`
- `TrustManagerFactorySpec | okhttp3.internal.platform.c.q | gizz.tapes.foss_63.apk`
- `MessageDigestSpec | okio.ByteString.digest$okio(r8-map-id-…:17)… | com.wirelessalien.android.moviedb_33.apk`
- `MessageDigestSpec | okio.ByteString.digest$okio(r8-map-id-…:20)… | com.wirelessalien.android.moviedb_33.apk`

Note the last two are **still frame-form after my repair attempt** — the nested
paren inside `digest$okio(r8-map-id-…:17)` defeats a naive suffix strip. Read
`repair_frame_keys.py` and reuse its exact regex rather than re-inventing it; it
documents that two real backtick test names contain nested paren pairs, which is
why its guard is suffix-anchored with an unrestricted prefix.

### What to change

1. Rewrite `scripts/derive_l3b_oracle.py` and `scripts/derive_l3c_oracle.py` to
   key on `(apk, class, method, spec)`, applying the frame-form repair to the
   L3-b source and declaring it in the provenance block.
2. Regenerate both oracles and both reconstructed trace pairs.
3. Decide, and state in the change, what to do about `TraceComparator.matched()`
   ignoring `location` (`TraceComparator.java:486-495`). If the oracle keys on
   location and the comparator does not read it, the gate is weaker than the
   oracle. Either the comparator learns to match location, or the oracle records
   why it carries a key the comparator only partly uses. **Raise this with the
   user; do not decide it silently.**
4. Re-run the validator suite and re-commit.

---

## 5. What is already done — Groups 1, 2, 3

Twelve commits on `modules`, tip `2cb45998`. Base of the session was `7e7acb69`.
gh101's commits are interleaved; the gh100 ones are:

| commit | what |
|---|---|
| `bc2200bb` | task-zero: pin descriptor + monitors the red evidence rests on (new task 4.3) |
| `06cd13ae` | Group 1: `--results-json` on `instrument`, android.jar log, census script, Python consumer |
| `50341264` | artefact correction: 8-of-9 error emitters, V2 uses `jca_android` |
| `913d0383` | persist the CLI output; INV-INS-105 verified on a real cryptoapp run |
| `08b7a1dd` | rebase the INV-INS-105 baseline on the right platform jar |
| `844ad8db` | `LIMITATIONS.md`: two defects found and deliberately not repaired |
| `6fcb0e86` | Group 2: validator independence, N=3 fixtures, INV-INS-106 contract test |
| `49155a89` | Group 3: oracle admission by provenance |
| `2cb45998` | Group 3: the two derived oracles ← **granularity is wrong, see §4** |

### Group 1 — counters and observability (8/8)

- `--results-json` moved to the **root** command with `scope = INHERIT`; both
  `instrument` and `batch` write the same document shape, so the Python parser
  has one code path. `instrument` writes it whether the weave succeeded or
  failed (INV-INS-105).
- The weaver logs the resolved `android.jar` per APK at the top of
  `BatchRunner.runPipeline`.
- `scripts/census_truncated_advices.py` re-derives the truncation census (D-A3).
  **It reads the emission model out of the weaver sources** rather than assuming
  it, so the same script reports `INLINE PATH TRUNCATES` now and `ITERATES`
  after Group 5, with the descriptor unchanged. Pre-repair output committed at
  `openspec/changes/gh100-weaver-emission-fidelity/evidence/census_pre_repair.json`.
- Python side: the `apk_paths` loop names one results JSON per APK under
  `instrument_results.d/` and merges them into `instrument_results.json`;
  `InstrumentationResults` grew `weave_counts`.
- `_run_cli` now persists the CLI's stdout/stderr per APK. It did not before —
  `capture_output=True` and `proc.stdout` never read, so every diagnostic the
  weaver printed died with the call, and the silent-failure guard's message told
  the operator to "inspect cli stdout" that had already been discarded.

### Group 2 — validator independence (4/4)

- `BaksmaliDiffer.buildWrapperToSpec` collects **every** monitor call's spec;
  the map became `Map<String, Set<String>>` and `extractHooks`, `collectHooks`,
  `specOfInvoke` followed. In the current descriptor no advice's calls span more
  than one spec, so this changes no number today — it removes the premise.
- `EmitterTestFixtures.fused(advice, n)` — one combinator, not three builders.
- `MonitorCallsPremiseContractTest` — a **source scan**, not a list of line
  numbers, because inspection is what missed the five sites for fifteen months.
  It covers the validator only; **the half that scans `advice-emitter` lands
  with V0 in Group 4 as red evidence.** Confirmed to discriminate: the same
  patterns still match `EmitContext:52`, `MonitorInvokeBuilder:240`,
  `StaticInitializationEmitter:147` and match nothing in the validator.
- The N=3 fixtures assert **plan shape only**, never cardinality — asserting
  cardinality here would leave the suite red for all of Groups 2 and 3, and
  task 2.4 requires the opposite.

### Group 3 — derived oracles (7/7, but see §4)

- `OracleProvenance` + `OracleLoader` admit on provenance, not file count. Two
  admissible classes: `hand_validated` and `derived_from_independent_weaver`
  (must name weaver, source, source sha256, derivation script). A source weaver
  of `dexlib2` is rejected with a message naming the **circularity** — tested,
  including that the message does not say "malformed", because a reader told
  that would go and fix the YAML.
- `cryptoapp-oracle.yaml` declares `class: hand_validated`; its gh50 APE-RV run
  moved from `ground_truth_run` to `corroborating_run`.
- `hateitorrateit-oracle.yaml` is now **rejected, not deleted** — a named
  rejection documents the gap where a missing file would not. If you prefer P3
  deletion, that is a one-line change and the user has not been asked.
- `MINIMUM_ORACLES = 3` is met by the committed set, asserted by a test against
  the **real** `oracles/` directory, not a fixture.

---

## 6. Findings this session that the change now rests on

1. **The census corrected the prose: 8 of the 9 dropped events are error
   emitters, not 9.** `SecureRandomSpec_c3Event` raises nothing — it records the
   seed and advances the state machine, so dropping it suppresses a *later*
   violation. The delta-spec scenario used to demand an error from all 9, which
   would have failed V2 against a **correct** weave. Fixed in `50341264`.
   Breakdown of the 8: 7 `UnsatisfiedConstraint` + 1 `UnsafeAlgorithm`.
2. **L3-c corroborates the census from unrelated data.** The three specs whose
   `UnsatisfiedConstraint` is present in the JVM control group and absent from
   the dexlib2 campaign are `IvParameterSpecSpec`, `PBEKeySpecSpec`,
   `SecretKeySpecSpec` — exactly the specs the descriptor census flags as
   truncated, reached by a different method from a different source.
3. **L3-b shows the wrapper collision plainly.** On the paired APKs, dexlib2
   reports `TrustManagerFactorySpec` categories the independent weaver never
   does (3,348 events over 3 sites).
4. **Neither L3-b nor L3-c can flip red→green inside this change.**
   `TraceComparator.compare` needs `apkSubsetDir/<oracle>/{ajc,dexlib2}.logcat`
   — both sides. The only dexlib2 sides available are **frozen pre-repair**
   recordings. A verdict that flips needs a fresh dexlib2 run, i.e. an emulator
   (L3-a) or a corpus re-run (V4), both out of scope. **The user decided
   (2026-08-07) to derive and execute them as *characterization*, recording the
   verdict as documenting the defect rather than certifying the repair, and to
   amend the delta-spec scenario so the gate clause does not claim what frozen
   data cannot deliver.** That spec amendment is still **pending** — do it via
   `openspec-update-change` before Group 6.
5. **Two defects found and deliberately left unrepaired**, both recorded in
   `docs/LIMITATIONS.md` §"Known defects left unrepaired":
   - `ConfigResolver.resolveAndroidJarFromEnv` picks the platform jar by
     **lexicographic** max, so `android-4` beat `android-37` and the weaver was
     resolving Android 1.6. `latestUnder` has the same shape for build-tools.
     Mitigation on this machine: `platforms/android-4` was **moved** to
     `$ANDROID_HOME/android-4.disabled-by-lexicographic-resolver` (reversible
     with one `mv`). **Installing any single-digit platform brings it back.**
     Measured not to affect this change's baseline: weaving cryptoapp under both
     jars differs only in `wrappersGenerated` (90 vs 96), and those six extra
     wrappers are for targets cryptoapp never invokes — `wrappersSubstituted`
     (74), `matchesApplied` (32) and `constructorInlineApplied` (11) are
     identical. **User decision: leave it, just record it.**
   - A root reactor build fails in `rvsec-agent` at `mop-maven-plugin:agent-gen`
     with `aspectjrt.jar is missing from the classpath`. **User decision: do NOT
     touch this.** Use `-DskipMopAgent=true`; task 7.1 must be read with that.

---

## 7. Remaining work

### Group 4 — red evidence, the barrier

Nothing in Group 5 may be integrated before Group 4 is committed (INV-INS-108).

- **4.1 V0** — an advice with N monitor calls emits N invokes in descriptor
  order. Must **fail**. The fixtures exist (`EmitterTestFixtures.fused`); add
  the cardinality assertions and the `advice-emitter` half of
  `MonitorCallsPremiseContractTest` (reuse its `scan(Path)` helper).
- **4.2 V2** — weave one APK with the **`jca_android`** set (user decision),
  baksmali, count `invoke-static` for the 9 events; they must be absent.
- **4.3** — freeze and sha256 the descriptor and generated monitor sources V2
  weaves with, and reuse exactly those in 6.2. gh101 is editing the `.mop` sets
  in parallel; without the pin the red and green runs stop being comparable.
- **4.4** record which commit carries the red evidence. **4.5** confirm neither
  passes.

Evidence goes in `openspec/changes/gh100-weaver-emission-fidelity/evidence/`
(the convention established this session).

### Groups 5–7

Unchanged from `tasks.md`. Notes:
- **5.3 is what issue #101 waits on** — tell that session when it lands (7.7).
- 6.4 reads `plansSkippedHighRegister`; the pre-repair baseline is **0** for
  cryptoapp, recorded in `evidence/inv_ins_105_cryptoapp_results.json`.
- 7.1: a root build needs `-DskipMopAgent=true` (see §6).

---

## 8. Commands

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

openspec status --change gh100-weaver-emission-fidelity --json
openspec instructions apply --change gh100-weaver-emission-fidelity --json
openspec validate gh100-weaver-emission-fidelity --type change

# Python (CI contract — without these flags conftest isolation breaks)
uv run pytest modules/rv-instrumentation-dexlib2/tests modules/rv-instrumentation-core/tests \
    --import-mode=importlib -o "addopts="

# Java: build/test ONE module without installing (does not touch ~/.m2)
cd $WS/rvsec && mvn -q test \
    -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator -am -DskipMopAgent=true
# module names: cli, advice-emitter, validator, dex-mutator, pointcut-engine, …

# Java: full reactor install (needed to refresh instr-cli.jar in rv-android/lib)
cd $WS/rvsec && mvn -q install -DskipTests -DskipMopAgent=true    # ~4 min

# surefire summary (mvn -q hides it)
grep -h "<testsuite " <module>/target/surefire-reports/*.xml | \
  sed -E 's/.*name="([^"]*)".*tests="([0-9]*)".*errors="([0-9]*)".*skipped="([0-9]*)".*failures="([0-9]*)".*/\1: t=\2 e=\3 s=\4 f=\5/'

# the census, pre- and post-repair
python3 scripts/census_truncated_advices.py --json <out.json>

# the derived oracles (rewrite these first — §4)
python3 scripts/derive_l3b_oracle.py
python3 scripts/derive_l3c_oracle.py
```

**Real instrumentation without an emulator** (this is how INV-INS-105 was
verified; instrumentation is a build operation, no device needed). A driver is
in the previous session's scratchpad; re-create it as:
`DexlibInstrumentation(config).instrument_apks(apks_dir, results_dir, apk_paths=[...])`
with `monitor_output_dir=results/gh92_e2e2/monitors`,
`keystore_file=modules/rv-instrumentation/assets/keystore.jks`,
`keystore_password="password"`, `keystore_alias="server"`. ~90 s for cryptoapp.

---

## 9. Paths

Inside `rv-android` (relative):

| what | path |
|---|---|
| the change | `openspec/changes/gh100-weaver-emission-fidelity/` |
| evidence committed so far | `.../evidence/{census_pre_repair.json, inv_ins_105_cryptoapp_results.json, inv_ins_105_cryptoapp_cli.log}` |
| census script | `scripts/census_truncated_advices.py` |
| oracle derivations | `scripts/derive_l3b_oracle.py`, `scripts/derive_l3c_oracle.py` |
| known unrepaired defects | `docs/LIMITATIONS.md` |
| L3-b source (**carries the frame-form defect**) | `out/run_jca_compare_consolidated/events_fair.csv` |
| production descriptor (census input, `jca`, insulated) | `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` |
| Python consumer | `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` |
| results model | `modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py` |
| the parked driver (do not wire it up) | `scripts/drive_cryptoapp.py` |

Outside (absolute):

| what | path |
|---|---|
| DEX weaver | `$DEXLIB2` |
| CLI | `$DEXLIB2/cli/src/main/java/br/unb/cic/rv/cli/{InstrumentationCli,BatchRunner,ConfigResolver}.java` |
| emitters (Group 5 targets) | `$DEXLIB2/advice-emitter/src/main/java/br/unb/cic/rv/emitter/` |
| validator + oracles + traces | `$DEXLIB2/validator/{src,oracles,traces}` |
| specification sets | `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}` — **gh101 owns these; read only** |
| the paper (canonical misuse key) | `$WS/ase-journal` — `results-rq1.tex:41`, `data-analysis/repair_frame_keys.py` |
| control-group data — **read-only** | `$WS/ase-journal/dataset/results/{errors_unit_tests.csv,categoria_unit_tests.csv,errors.csv}` |

---

## 10. Learnings worth carrying

- **Check the paper before choosing a unit of analysis.** The `(app, class,
  method, specification)` key is defined in `results-rq1.tex:41` and implemented
  in `data-analysis/`. An argument from what a validator tool currently does is
  not a reason to deviate from it.
- **`mvn -q` hides the surefire summary.** Read the XML reports; a "quiet
  success" is not evidence tests ran.
- **Do not build the whole reactor when one module will do.** `mvn test -pl
  <module> -am` compiles only what is needed and never touches `~/.m2`.
  The user was rightly annoyed when I ran a full `install` for a single module.
  And read the docs first: `-DskipMopAgent=true` is documented in
  `$WS/rvsec/CLAUDE.md` via the `-Pcheck` profile.
- **The user rejects orchestration for its own sake.** Groups are linear on
  purpose. Do not fan them out.
- **Report findings, do not silently expand scope.** Two defects were found and
  the user chose to record rather than fix both. Ask.
- **`get(0)` may exist beyond the five known sites** — INV-INS-106 is enforced
  by a source scan, not by line numbers.
- Line numbers in the artefacts have already drifted (e.g.
  `MonitorInvokeBuilder` is `:240`, not `:238-241`). Re-check before editing.

---

## 11. Definition of done (unchanged)

- All 7 task groups checked off, with the red-evidence commit referenced from
  the repair commits.
- `openspec validate gh100-weaver-emission-fidelity --type change` passes.
- `/opsx:verify` run against the delta spec.
- L3-b and L3-c executed with recorded verdicts, each stating that L3-a did not
  run and that V0/V2 prove emission and arrival in the woven DEX, not arrival in
  logcat — **and, per §6.4, that both are characterization rather than
  certification.**
- Issue #100's acceptance criteria ticked one by one in the issue body **before**
  closing; any criterion not literally met gets an inline note
  (`- [x] ~~criterion~~ — superseded by …`), never a silent tick.
- Delta spec synced explicitly (`openspec-sync-specs`) **before** archiving, then
  `openspec archive gh100-weaver-emission-fidelity --skip-specs`.
- `openspec validate --specs` still passes.
- Final commit uses `closes #100`.

**Known board limitation:** the `gh` CLI token lacks the `project` scope, so
issue #100's card cannot be moved from here. Only the user can run
`gh auth refresh -s project`.
