# Session handoff — gh100, session 4: the repairs landed, the change is still open

> Paste this whole file as the first message of the new session.
> It supersedes `docs/20260807_handoff_gh100_session3.md` wherever the two
> disagree. Do not read session 3's handoff first — §6 below carries everything
> from it that is still true, and several of its numbers were wrong.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of
Pedro Costa, `phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

**Git branch is `modules`.** The whole tree — `rv-android` *and* the sibling
Java reactor — is **one git repository** rooted at `$WS/rvsec`. One commit can
span both sides.

- `$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`
- `$DEXLIB2` = `$WS/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2`
- **The Maven reactor root is `$WS/rvsec`**, not `$WS`. Session 3's handoff had
  this right; the first command of session 4 got it wrong and failed with
  "Could not find the selected project in the reactor".

**Anything outside `rv-android` must be written with an absolute path** —
standing user instruction, applies to code, docs and prose.

**A parallel session is implementing gh101 on this same branch** and its commits
interleave with yours. Do not rebase, force-push or reorder. Stage only paths
this change owns. Nothing has been pushed.

---

## 1. What happened in session 4, in one paragraph

The payload landed. The weaver is repaired, the reactor is rebuilt, and the new
`instr-cli.jar` is in `rv-android/lib/` — so **an experiment run from this tree
now runs against a fixed weaver**. Groups 4, 5, 6.1–6.4 and 7.1–7.4 are done and
committed, with V0 and V2 recorded failing before and passing after over
byte-identical inputs. **39 of 57 tasks.** What remains is Group 3b (the Layer-3
comparator work, entirely deferred), tasks 6.5–6.8, 7.5–7.7, one artefact
correction the implementation forced, and then sync + archive.

---

## 2. The commits, in order

| commit | what |
|---|---|
| `01dc0216` | docs: the artefact correction session 2 left uncommitted |
| `e29c3694` | **red evidence** — V0 and V2 failing against the unrepaired weaver |
| `48b57fc5` | **the repair** — every emission path emits every monitor call |
| `686f51c6` | **green evidence** — V0 and V2 passing over the same pinned bytes |

Nothing is pushed. `openspec validate gh100-weaver-emission-fidelity --type change`
passes.

---

## 3. The one thing that must happen early: D-B1 is now wrong

**`design.md`'s D-B1 prescribes a mechanism that cannot work, and the code
deliberately does something else.** This is the highest-value unfinished item,
because a reviewer reading the design and the code together will find them in
contradiction.

D-B1 says: *widen the wrapper registry key at `DexWeaver:145` so distinct
advices produce distinct keys.* The key is
`origClassDesc#method(params)return` — **the call site's own
`MethodReference`**, which is the only identity a call site carries. Any
component added to it is one the lookup cannot supply, so widening is not
available. The spec's own scenario allows the alternative ("either disambiguate
the key **or** fail loud"), but failing loud alone aborts the weave on the real
production descriptor, which has 10 colliding keys.

What was implemented instead, **confirmed with the user on 2026-08-07**:
`WrapperEmitter` **merges** — one wrapper per original call, whose body fires the
monitor calls of every advice bound to it. The registry becomes single-valued by
construction, and D-B1's fail-loud guard stays as the assertion that emitter and
registry still agree.

Measured on the production descriptor **before** the merge:

| | |
|---|---|
| wrappers generated | 96 |
| distinct registry keys | 84 |
| keys bound more than once | 10 |
| **wrappers silently discarded** | **12** |

`SecureRandom.getInstance(String)` alone was bound three times. After the merge:
`wrappersGenerated` 96 → 84, `wrappersSubstituted` unchanged at 74 — no call site
lost its wrapper.

**Task**: fold this into `design.md` D-B1 (and the "Open Questions" entry about
`BaksmaliDiffer`, which is now answered — see §4) **via the
`openspec-update-change` skill**, never by hand. That skill mandates confirming
each edit with the user; batch the diffs into one `AskUserQuestion`.

---

## 4. What the code actually does now (so you do not re-derive it)

### 4.1 Emission cardinality — `48b57fc5`

- `EmitContext.primaryMonitorCall()` → **`monitorCalls()`**, returning the list.
  `MonitorInvokeBuilder.primaryMonitorCall` and
  `StaticInitializationEmitter.primaryCall` are **deleted**. The INV-INS-106
  source scan now covers `advice-emitter` as well as `validator` and passes.
- `MonitorInvokeBuilder.buildInvoke(ctx)` iterates; `buildMethodReference` and
  `registersFor` take the `MonitorCallDescriptor` explicitly, because fused calls
  can declare different argument lists.
- **An unresolvable binding in any call skips the whole advice**, not just the
  offending call. Rationale in the javadoc: emitting a fused advice's first event
  without its second drives the monitor's state machine through a transition its
  accompanying event never accompanied. In the production descriptor every fused
  call shares an identical args list, so this changes nothing there — verified.
- **`TryCatchSpec.throwingOperandIndex` became `throwingOperandIndices`, a
  `List<Integer>` parallel to `toInsert`.** `InstructionInjector.installTryCatch`
  rewrites each invoke's own slot. A single index applied to all of them would
  rewrite an unrelated operand — a type-mismatched register the verifier rejects,
  which is a worse failure than the truncation.
- `StaticInitializationEmitter.eventMethodName` → **`eventMethodNames`** (list);
  `signatureDelivery` takes a list of events, emits the `ClassSignature`
  materialisation **once** and one invoke per event. `deliversSignature` requires
  **every** call to carry the token. Both `DexWeaver` call sites updated.

### 4.2 Fail-closed parsing

`DexWeaver.parseCommonPointcut` raised nothing and returned `null` on a parse
failure. That is not graceful degradation: the `commonPointcut` carries the
class-level exclusions (`BaseAspect.notwithin()`, `!within(...RVMObject+)`)
which appear in no advice's own expression, so dropping it weaves every site
they exist to exclude. It now raises `UnsupportedAspectConstructError` naming the
expression and the aspect. `UnsupportedAspectConstructError` gained a
`(message, cause)` constructor.

`DexWeaverDegradationTest.malformedCommonPointcutDegradesToAdviceOnlyMatching`
asserted the old behaviour. It was **inverted, not deleted**, and renamed
`malformedCommonPointcutFailsTheWeave`, so the record shows the contract changed
deliberately.

### 4.3 The Layer-1 gap the merge exposed — task 5.4, answered

`BaksmaliDiffer.specOfInvoke` looked wrapper names up **exactly**, while its own
javadoc claimed it registered a prefix form. It never did. The merge shifts the
emitter's `_<n>` overload numbering, which would have broken the lookup — but the
numbering was already unreproducible, because the descriptor-only derivation
never sees the android.jar overloads the emitter numbers.

`buildWrapperToSpec` now keys on the **base** name (`<fqClass>_<method>`, no
suffix) and **unions** the specs of every advice over it; `specOfInvoke` tries
the exact name first, then strips a trailing `_<digits>`.

---

## 5. State of the change — 39 of 57

| Group | | |
|---|---|---|
| 1. Counters and observability | 8/8 | done (session 1) |
| 2. Validator independence | 4/4 | done (session 2) |
| 3. Derived oracles | 7/7 | done, superseded by 3b |
| **3b. Oracle granularity + comparator fidelity** | **0/11** | **deferred twice — the big one left** |
| 4. Red evidence | 5/5 | done |
| 5. Emission repairs | 7/7 | done |
| 6. Green evidence and gates | 4/8 | 6.1–6.4 done; **6.5–6.8 depend on 3b** |
| 7. Integration and verification | 4/7 | 7.1–7.4 done; **7.5–7.7 open** |

### Test counts after the repair — this is your regression baseline

```
descriptor-reader 15 · pointcut-engine 157 · advice-emitter 95 · dex-mutator 86
validator 59 · cli 7 · grammar-tests 16/3/7 · 0 failures
Python: 36 passed (rv-instrumentation-dexlib2 + rv-instrumentation-core)
```

Session 3's baseline was `validator 58 · advice-emitter 85 · dex-mutator 83 ·
cli 7`. The deltas are: +1 validator (the emitter source scan), +10
advice-emitter (V0's 5, parity 2, wrapper merge 3), +3 dex-mutator (registry
guard).

---

## 6. What is left, in the order it should be done

### 6.1 Finish Group 7 (cheap, unblocks nothing else)

`/rv-verify` reported three **pre-existing** E501s in
`modules/rv-instrumentation-dexlib2/src/` (`config.py:73,78`,
`dexlib_instrumentation.py:88`), all inside description or message strings. They
predate gh100. Fix them or leave them, but do not report them as this change's.

- **7.5** `/rv-code-reviewer` via the Skill tool.
- **7.6** `/rv-docs-sync rv-instrumentation-dexlib2` if module docs need it.
- **7.7** Notify issue #101 that task 5.3 landed. **Its empirical verification of
  the two hot specs was blocked on this and is now unblocked** — the merged
  wrapper means both specs' monitor calls fire at a shared call site, which is
  the mechanism #101 needed. Say so explicitly in the notification.

### 6.2 The D-B1 artefact correction (§3) — via `openspec-update-change`

### 6.3 Group 3b — the Layer-3 comparator, 11 tasks

Entirely untouched. Its brief is in `tasks.md` §3b and in §6.2–6.5 of
`docs/20260807_handoff_gh100_session2.md`. The short version:

- `TraceComparator.parseObserved` reads a line format **nothing emits**
  (`[Spec] EType: msg`). The producer is `ErrorCollector.java:37`: seven
  comma-separated fields under a **padded** `RVSEC   :` tag,
  `spec,classQualifiedName,className,methodName,location,errorType,expecting`,
  with fields 6+ rejoined because the `expecting` text carries its own commas.
  `rv-android`'s `logcat_parser.py:319` is the reference implementation.
- `matched` ignores `location` although every oracle declares it.
- The derived oracles from Group 3 are keyed on `(spec, errorType)` and pooled
  one file per profile; they must be re-keyed on `(apk, class, method, spec)` and
  split one file per APK.
- Numbers already computed, do not re-derive: L3-b repaired gives
  `ajc=13, dexlib2=17, both=12, only-ajc=1, only-dexlib2=5` over 8 paired APKs.
  L3-c's `app_producao` filter keeps 138 of 298 control rows over 12 apps; the
  three control-only `UnsatisfiedConstraint` specs are `IvParameterSpecSpec` (9),
  `PBEKeySpecSpec` (5), `SecretKeySpecSpec` (16). The frame-form repair uses
  `ErrorDescription.FRAME_SUFFIX` and fixes 2,476 rows of `events_fair.csv` with
  zero residue; the article's `repair_frame_keys.py` fixes **0** of them.

### 6.4 Then 6.5–6.8 (they consume 3b's oracles), then sync + archive

`openspec-sync-specs`, then `openspec-archive-change`. The change stays open
until all of the above.

---

## 7. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md`, then
`docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under
   `openspec/changes/gh100-*/` goes through the **skills** invoked via the
   `Skill` tool: `openspec-apply-change`, `openspec-update-change`,
   `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change`
   (the `/opsx:*` aliases are the same skills). **Never** hand-write or hand-edit
   a planning artefact (proposal / design / specs / tasks) outside a skill that
   told you to. Implementation code and `evidence/*` outputs are normal work.
   *Caveat:* `openspec-update-change` mandates confirming each edit with the
   user. Batch the diffs into one `AskUserQuestion`, do not ask three times.
2. **VERIFY BEFORE YOU PROPOSE.** Read the producing code and a real artefact on
   disk *before* writing a recommendation, a spec sentence, or a question.
3. **NEVER start, stop or manage Android emulators.** No exceptions, including
   for validation. Instrumentation is a *build* operation and needs no device.
   Nothing in session 4 touched one.
4. **Never add `Co-Authored-By`** or any co-author trailer.
5. **Language:** code, comments, commit messages, GitHub issues and OpenSpec
   artefacts in **English**; prose addressed to the user in **Brazilian
   Portuguese with correct accentuation**.
6. **P1–P4 principles** (`docs/WORKFLOW.md` §4): simplicity; narrative docs that
   explain *why*; no backward compatibility; current-state comments only.
7. **Terminology:** "MOP" = *monitored operations*, never "security operations".
8. **Read-only data.** `$WS/ase-journal/dataset/results`,
   `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`,
   `$WS/rvsec-dataset/repos` and `rv-android/data/results` are **read-only**.
9. **Do not touch the MetaCrySL tree** (`$WS/MetaCrySL`).
10. Use the session scratchpad for temporary files, never `/tmp`.
11. **Commits**: `refs #100` during work, `closes #100` only in the final one.
12. **Ask before running anything heavy.** A campaign has been occupying this
    machine. See §8 for real timings — the numbers in earlier handoffs were
    optimistic.
13. **Do not fan out subagents or workflows.** The user has rejected
    orchestration for its own sake. Parallelism means a second *session*.

---

## 8. Commands — corrected against what actually ran

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

openspec status --change gh100-weaver-emission-fidelity --json
openspec instructions apply --change gh100-weaver-emission-fidelity --json
openspec validate gh100-weaver-emission-fidelity --type change

# Python (CI contract — without these flags conftest isolation breaks)
uv run pytest modules/rv-instrumentation-dexlib2/tests modules/rv-instrumentation-core/tests \
    --import-mode=importlib -o "addopts="
```

```bash
# Java: build/test modules WITHOUT installing. Note the reactor root.
cd $WS/rvsec && mvn test -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter \
    -am -DskipMopAgent=true
# module names: cli, advice-emitter, validator, dex-mutator, pointcut-engine, descriptor-reader
# several modules at once: comma-separate the -pl paths

# Single test class. The flag is -Dsurefire.failIfNoSpecifiedTests=false —
# -DfailIfNoSpecifiedTests=false is NOT read and the build fails on the first
# module of the -am chain that lacks the class.
... -Dtest=EmissionCardinalityTest -Dsurefire.failIfNoSpecifiedTests=false

# Full reactor install (task 7.1). ~4 min in earlier handoffs; it actually took
# 12m12s. Run it in the background and wait on the jar's mtime.
cd $WS/rvsec && mvn -q install -DskipTests -DskipMopAgent=true

# surefire summary — read the .txt reports, `mvn -q` hides everything
cat $DEXLIB2/<module>/target/surefire-reports/br.unb.cic.rv.*.<Class>.txt
```

### Weaving one APK, without an emulator

**Do not invoke `instr-cli.jar` by hand** — it needs `--classpath` pointing at
staged `rv-monitor-rt.jar` / `rvsec-core.jar` / `rvsec-logger-logcat.jar`, and
without them javac fails with ~2400 errors. Drive the production Python path:

```python
from rv_instrumentation_dexlib2 import DexlibInstrumentation
from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig

config = DexlibInstrumentationConfig(
    monitor_output_dir=RA / "results/gh99_jca_android_monitors/monitors",
    instrumented_dir=run / "instrumented",
    working_dir=run / "work",
    keystore_file=RA / "modules/rv-instrumentation/assets/keystore.jks",
    keystore_password="password", keystore_alias="server", key_password="password",
)
DexlibInstrumentation(config).instrument_apks(
    RA / "apks_examples", run / "instrumented",
    apk_paths=[str(RA / "apks_examples/cryptoapp.apk")])
```

**Do NOT call `prepare_instrumentation()` yourself.** `instrument_apks` calls it,
and it **appends** to `extra_classpath` — calling it twice passes every runtime
jar twice and d8 rejects the weave with `Type ... is defined multiple times`.
This cost session 4 one 85-second weave. (It is a real robustness smell; the user
was told, and it is **not** in gh100's scope.)

≈ 85 s for cryptoapp. A parked driver exists at `scripts/drive_cryptoapp.py` —
**do not wire it up**; it is the source of the bad `RVSEC_LINE` regex.

### The two evidence scripts

```bash
# descriptor-level census (tasks 1.4 / 6.3); defaults to the gh92 descriptor
python3 scripts/census_truncated_advices.py --json <out.json>

# end-to-end: do the truncated events reach the woven DEX? (tasks 4.2 / 6.2)
python3 scripts/v2_woven_dex_events.py --apk <WOVEN.apk> \
    --descriptor <MultiSpec_1MonitorAspect.json> \
    --monitor-src <MultiSpec_1RuntimeMonitor.java> --json <out.json>
```

`v2_woven_dex_events.py` recomputes the dropped-event set from the descriptor via
the census module, so the two can never disagree. It disassembles with the
baksmali bundled inside `instr-cli.jar` — no extra tool. Exit 1 on FAIL.

---

## 9. Learnings — the expensive ones from this session

- **The descriptor is the same for `jca` and `jca_android`.**
  `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` and
  `results/gh99_jca_android_monitors/monitors/MultiSpec_1MonitorAspect.json` have
  the **same sha256** (`e53f0af1…`); only the generated
  `MultiSpec_1RuntimeMonitor.java` differs. Task 1.4 assumed the two sets needed
  separate censuses. For the weaver they do not — the descriptor is what it
  reads. What differs between the sets lives in the monitor's state machines and
  `expecting` texts and never reaches an emission decision.
- **V2 over one APK covers 2 of the 9 events.** The other seven belong to advices
  whose pointcuts matched no site in `cryptoapp`. The script reports them `n/a`,
  never "absent", because a silent APK and a truncating weaver look identical
  there. Any claim about all nine is the census's, not V2's. Do not let a report
  blur the two.
- **A positive control is what makes an absence mean anything.** V2 counts the
  *kept* sibling of every dropped event. `dropped ×0` alone proves nothing;
  `kept ×5, dropped ×0` proves the advice wove and the second call was lost.
- **`mvn -q install` on the reactor is 12 minutes, not 4.** Run it in the
  background and poll the jar's mtime; the `-q` output file stays empty so
  tailing it tells you nothing.
- **`git status --cached` is not a flag.** Use `git diff --cached --name-status`.
- **`evidence/*.log` needs `git add -f`** — `rv-android/.gitignore:129` is `*.log`.
- **The weave writes into `--monitor-src-dir`**, adding `mop/MonitorWrappers.java`
  and `mop/Coverage.java`. The "pinned" monitor directory is not read-only in
  practice; the four pinned files themselves are untouched.
- **Report findings, do not silently expand scope.** Two defects were found this
  session (the non-idempotent `prepare_instrumentation`; the `BaksmaliDiffer`
  javadoc that claimed prefix matching the code never did). The second was in
  scope via task 5.4 and was fixed. The first was reported and left alone.
- **When the design prescribes a mechanism that cannot work, stop and ask.**
  D-B1's widening was impossible; the user chose merging. Implementing it
  silently would have left `design.md` contradicting the code with nobody
  knowing.

---

## 10. Paths

Inside `rv-android` (relative):

| what | path |
|---|---|
| the change | `openspec/changes/gh100-weaver-emission-fidelity/` |
| evidence | `.../evidence/` — `census_{pre,post}_repair.json`, `v0_red_emission_cardinality.txt`, `v2_{red,green}_cryptoapp.{json,txt}`, `v2_pinned_inputs.md`, `green_deltas.md`, `inv_ins_105_cryptoapp_*` |
| census script | `scripts/census_truncated_advices.py` |
| V2 script | `scripts/v2_woven_dex_events.py` |
| oracle derivations (Group 3b, to be rewritten) | `scripts/derive_l3b_oracle.py`, `scripts/derive_l3c_oracle.py` |
| known unrepaired defects | `docs/LIMITATIONS.md` |
| pinned V2 monitors (`jca_android`, frozen 2026-08-06) | `results/gh99_jca_android_monitors/monitors/` |
| census descriptor (`jca`, insulated) | `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` |
| recent real logcats (**read-only**) | `data/results/cmp163_*/` |
| Python consumer | `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` |
| phase-5 runner | `scripts/run_phase5_validators.sh` |

Outside (absolute):

| what | path |
|---|---|
| DEX weaver | `$DEXLIB2` |
| emitters (repaired) | `$DEXLIB2/advice-emitter/src/main/java/br/unb/cic/rv/emitter/` |
| weaver + wrapper registry | `$DEXLIB2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java` |
| validator + oracles + traces (Group 3b) | `$DEXLIB2/validator/{src,oracles,traces}` |
| on-device collector (format authority) | `$WS/rvsec/rvsec/rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java`, and `rvsec-core/.../mop/eh/{ErrorSummary,ErrorDescription}.java` |
| specification sets | `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}` — **gh101 owns these; read only** |
| the article | `$WS/ase-journal` — `results-rq1.tex:41`, `data-analysis/` |

---

## 11. Definition of done — for the NEXT session

Pick a scope and say which, explicitly, at the start:

- **Minimum**: 7.4–7.7 closed, and the D-B1 correction folded into `design.md`
  via `openspec-update-change`. That leaves the change coherent for a reader.
- **Full**: the above, plus Group 3b (11 tasks), plus 6.5–6.8, plus
  `openspec-sync-specs` and `openspec-archive-change`, plus `closes #100`.

Group 3b is large and independent of everything else — it touches
`$DEXLIB2/validator/**` and `rv-android/scripts/derive_l3*.py` and nothing the
repairs touched. It is the natural candidate for a session of its own.

**Known board limitation:** the `gh` CLI token lacks the `project` scope, so
issue #100's card cannot be moved from here. Only the user can run
`gh auth refresh -s project`.
