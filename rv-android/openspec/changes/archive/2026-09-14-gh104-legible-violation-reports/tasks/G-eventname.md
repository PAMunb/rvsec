# Group 3 — G: `__EVENTNAME` in the monitor generator

Tracked checkboxes: `tasks.md` §3. Wave 1 delivers 3.0-3.4, 3.6 and 3.7, in parallel with Groups 1, 2, 4, 5, 6. **Tasks 3.9, 3.5 and 3.8 are NOT wave-1 work**: in that order they form one between-waves orchestrator step, because regeneration needs the generator that 3.9's `mvn install` puts on the toolchain — the same shape as Group 4, which hands its re-weave to the same step. A subagent dispatched for this group in wave 1 stops after 3.7 and reports; it does not run `mvn install`. **Blocks Group 7** (E1 messages): no report site can compose `ev=` until this macro expands. Edits one submodule only — `rv-monitor/rv-monitor` (the *generator*). Group 5 edits `rv-monitor/rv-monitor-rt` (`ViolationRecorder`); the two are disjoint source sets. Git: one repository (`git rev-parse --show-toplevel` is `…/rvsec`); every `git status`/`git diff` carries a pathspec (`git status --short -- rv-monitor/rv-monitor`); this group does not commit — the orchestrator commits after the group's summary with explicit pathspecs, and this group's two commits are made separately from Group 5's (`rv-monitor/rv-monitor` vs `rv-monitor/rv-monitor-rt`). Environment: prefix every Java/Maven command line with `export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH` (shell state does not persist between tool calls; the default JDK is 25) and every generating line with `export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR` (`/tmp` and the session scratchpad are tmpfs). Two shared resources are serialised by the orchestrator, not by this group: the reactor `mvn install` of task 3.9 runs between waves (never while another group is editing Java; per-submodule `mvn -q test` may run inside the group), and monitor generation — tasks 3.5 and 3.8 are marked `[GEN]` below and the orchestrator dispatches at most one generating task at a time (3.0 generates nothing and is not `[GEN]`). `evidence/...` means `data/gh104/evidence/...`.

## Subagent brief

Read `design.md` D-4 (the decision and the superseded one, so you do not re-take it) and D-14, and the `instrumentation` delta requirements `Event-Name Emission by the Monitor Generator` (INV-INS-120) and `The Generated Dispatcher Releases Its Lock on Every Exit` (INV-INS-129). You are doing two things in one module: adding **one macro, one table and one per-class helper** (tasks 3.1-3.5, additive — no existing generated line changes shape) and **framing the dispatcher's guarded region** so the global lock is released on every exit (tasks 3.6-3.8 — the one existing emission this group does change, and only in its `try`/`finally` framing). The acceptance step proves both by regenerating the single control set, `jca`, and diffing it against its frozen control: the only admissible differences are the event-name table, the `RVM_eventName()` helper and the framing — no expanded macro appears, because the frozen `jca` writes no `__EVENTNAME`.

Do not touch any `.mop` file — including the successor set `jca_android`, which Group 2 builds in parallel with you and Group 7 fills with envelopes afterwards, and including the archived `jca_android_bug_predicate/`, which this group neither reads nor regenerates — it is edited, regenerated and replayed by no task of this change and is read only by the gh101 gate scripts and the identity checks (2.11, the E0 count). Do not touch `javamop` — it carries the Java block from `.mop` to `.rvm` verbatim, which is why `__LOC` traverses it today without javamop knowing what it is.

## The facts this group rests on (all verified 2026-08-17, file:line)

**The monitor already records the last event, in two shapes that coexist in one generated file — and the two shapes do not store the same number.** In the frozen control (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`) there are **15 classes of the atomic/table shape** and **8 of the non-atomic shape**:

| shape | condition | where the last event lives | what `this.getLastEvent()` returns | no-event value |
|---|---|---|---|---|
| atomic / table | `BaseMonitor.java:114-118` `isAtomicMoniorUsed()` (`pairValueField != null`) | packed into `pairValue` as `((lastEvent + 1) << numStateBits) \| state` — `calculatePairValue` stores `lastEvent + 1` (`BaseMonitor.java:1161-1166`; control `MultiSpec_1RuntimeMonitor.java:3305-3309`) | `pairValue >> numStateBits` with **no `-1`** (`getPairValueExtracter`, `BaseMonitor.java:1115-1140`) — i.e. `idnum + 1` | `0` (`calculatePairValue(-1, 0)`, control `:3292`) |
| non-atomic | otherwise | plain field `RVM_lastevent` (`BaseMonitor.java:106`; assigned inline at `:425-428`) — the field and its accessor are **inherited from the runtime**, `rv-monitor-rt` `AbstractSynchronizedMonitor.java:5` (`protected int RVM_lastevent = -1`) and `:21` (`public final int getLastEvent()`), declared on `IMonitor.java:19`; the generator declares neither | `idnum` itself (`BaseMonitor.java:427`, `AbstractSynchronizedMonitor.java:21`) | `-1` |

A lookup written identically for both shapes would therefore name the *next* event in the 15 atomic classes and the first event instead of `none` — exactly the mis-indexed name read as a fact that D-4 exists to eliminate. The generator branches between the two only where it emits *termination* code: `BaseMonitor.java:1044-1048` passes `"int lastEvent = this.getLastEvent();"` / `"lastEvent"` for the atomic shape and `null` otherwise, and `MonitorTermination.java:73` defaults the variable to `"RVM_lastevent"`. **Do not reuse that branch in `HandlerMethod`**: the `HandlerMethod` objects are constructed in `initialize` (`BaseMonitor.java:226`), before `checkIfAtomicMonitorCanBeEnabled()` runs (`:665`, at the top of `toString()`), so `isAtomicMoniorUsed()` throws `IllegalStateException` there (`:115`); and the raw field `RVM_lastevent` is undefined in the atomic shape. The shape **is** known inside `BaseMonitor.toString()`, after `:665` — so that is where the generator emits, per monitor class, a helper `RVM_eventName()` that reads `this.getLastEvent()`, subtracts one in the atomic shape, returns `"none"` for the no-event value (`-1` non-atomic / `0` atomic) and the table entry otherwise; `HandlerMethod` expands `__EVENTNAME` to a call of that helper, never to a direct table lookup. A non-outermost monitor (`isOutermost == false`, suffix mode; unused by `jca`) has neither shape — emit the literal `"none"` there and let the fail-closed check name the case.

**The generator already holds the names, and writes them as comments.** `MonitorTermination.java:131-133`:

```java
for (EventDefinition event : this.events) {
    ret += "case " + event.getIdNum() + ":\n";
    ret += "//" + event.getId() + "\n";      // index and name, paired, as a comment
```

**The `@fail` body is a method of the monitor class, and `__RESET` lands after the report.** `HandlerMethod.java:36-48` substitutes `__RESET` → `this.reset()` in the handler body; `reset()` sets the last event back to `-1`. In the `.mop` the `addError` call precedes `__RESET`, so the offending event is still recorded when the envelope is composed. `Prop_N_handler_fail()` is invoked right after the event method returns, on the same monitor instance (visible in the generated `event_g1` dispatch loop).

**An event that fails its guard cannot be reported.** The generated event method emits `if ( ! (condition) ) { return false; }` **before** the `.mop` body and before `handleEvent`, verified on `KeyManagerFactorySpec.Prop_1_event_g3`.

**Macro substitution is plain `replaceAll` on the body text, at three sites of the Java path:**

| site | what it substitutes | scope |
|---|---|---|
| `BaseMonitor.java:350-368` (`printEventMethod`) | `__RESET`, `__DEFAULT_MESSAGE`, `__LOC`, `__ACTIVITY`, `__SKIP` | event bodies |
| `HandlerMethod.java:36-48` (constructor) | `__RESET`, `__DEFAULT_MESSAGE`, `__LOC`, `__SKIP` | handler bodies, `@fail` among them |
| `RawMonitor.java:90-105` | same set | raw-monitor mode |

`SuffixMonitor` does not substitute (only a commented `has__LOC` at `:245`). `logicpluginshells/fsm/CFSM.java` (`:237`, `:429`), `tfsm/CTFSM.java` (`:225`, `:267`, `:459`) and `cfg/CCFG.java` (`:161`) also `replaceAll("__RESET", …)` but are the **C** output — they import `com.runtimeverification.rvmonitor.c.rvc.CSpecification` — and are off this path; none of the three is touched.

## Task 3.0 — the diff tool and the control it compares against, before the generator moves (NOT `[GEN]`: it generates nothing)

Tasks 3.5 and 3.8 regenerate ONE set — `jca` — and diff it against the control already in the tree, `results/gh101_group8_jca_frozen_control/monitors/`. One control is enough: the generator edit is global to all 191 `.mop` files, and `jca` exercises the same emitter paths as any set derived from it, so a second control buys no signal and costs a generation run, a directory, a manifest and a recipe. The archived `jca_android_bug_predicate` is regenerated by no task. 3.0 therefore only writes the tool and pins that one control, before a line of the generator changes:

1. Write `scripts/gh104_regen_diff.py`. It regenerates one set's monitors into scratch with the current toolchain, diffs them against a recorded control directory, classifies each difference, and exits non-zero on anything outside an `--expect` list. It is the only `gh104_*` script with no creating task before 2026-08-18.
2. Write `data/gh104/jca_frozen_control.sha256` for `results/gh101_group8_jca_frozen_control/monitors/`, which is unversioned today. The manifest covers the generation outputs under `monitors/` only — `MultiSpec_1RuntimeMonitor.java`, `MultiSpec_1MonitorAspect.aj` and the descriptor `MultiSpec_1MonitorAspect.json` (emitted by javamop `--emit-descriptor` in the same run, `runtime_verification_generator.py:212-213`) — and not `mop/MonitorWrappers.java`, which the instrumentation step produces, nor `Coverage.aj`, which is not a generator output: `runtime_verification_generator.py:227-230` copies it from the aspects directory into the control directory after generation, so the manifest names exactly the three generated files and excludes it. Nothing is generated here: the control already exists.
3. Write `data/gh104/README.md` with the regeneration recipe for the control, because `results/` is gitignored and the directory can be lost: the frozen `jca` control is the unmodified generator at the commit recorded there (the SHA of the tree before task 3.2 lands) over `rvsec-mop/src/main/resources/jca`. There is no second control to record.

**This group does not read the archived `jca_android_bug_predicate/` at all** — it is regenerated by no task and is not a control of this change. Nor does it read the successor `jca_android/`, which Group 2 builds in parallel. The only specification directory this group touches is the frozen `resources/jca`, and only to read it. Generation writes `.rvm` files into the source directory before moving them (`runtime_verification_generator.py:221-223`, `move_files_by_extension`), which is why the rename cannot overlap a generation. `tasks/E0-baseline.md` reads the same directory under the same name.

## File inventory

| file | edit |
|---|---|
| `rv-monitor/rv-monitor/src/main/java/.../output/monitor/BaseMonitor.java` | `:806-812` emit the event-name table; inside `toString()` after `checkIfAtomicMonitorCanBeEnabled()` (`:665`) emit the per-class helper `RVM_eventName()` (decodes `getLastEvent()` per shape: `-1` in the atomic shape; `none` for `0` atomic / `-1` non-atomic); `:350-368` expand `__EVENTNAME` to a literal |
| `.../output/monitor/HandlerMethod.java` | `:36-48` expand `__EVENTNAME` to the call `RVM_eventName()` (never a direct table lookup) |
| `.../output/monitor/RawMonitor.java` | `:90-105` mirror the event-body substitution |
| `rv-monitor/rv-monitor/src/main/java/.../rvj/RVMNameSpace.java` | `:24` area — reserve the table's name and `RVM_eventName` beside `RVM_lastevent` |
| `scripts/gh104_regen_diff.py` | NEW — task 3.0: regenerate a set into scratch, diff against a recorded control directory, classify each difference, exit non-zero on anything outside `--expect` |
| `data/gh104/jca_frozen_control.sha256` | NEW — task 3.0: the manifest of the one control (generated `monitors/` files only, each named). `results/` is gitignored, so the versioned manifest is the artefact: a check skips with a named reason when the control directory is absent, and FAILS when it exists but the manifest disagrees |
| `data/gh104/README.md` | NEW — task 3.0: regeneration recipe for the one control (generator commit, source set `resources/jca`, output directory), the manifest coverage and the `clear.sh` note |
| `rv-monitor/rv-monitor/src/test/java/.../EventNameMacroTest.java` | NEW — task 3.1's red test, one fixture per monitor shape (see Acceptance) |
| `.../output/combinedoutputcode/event/advice/Advice.java` | `:176-177` (acquire, `if (isSync) ret += this.globalLock.getAcquireCode();`) and `:254-256` (release, `if (!Main.useFineGrainedLock) { if (isSync) ret += this.globalLock.getReleaseCode(); }`) — emit `try {` after the acquisition and `} finally { <release> }` in place of the bare release (task 3.7). **Not** `GlobalLock.java:40-67`: its `getAcquireCode()`/`getReleaseCode()` are string fragments that `BaseMonitor.java:543,567,583,587` (`execEvent`), `StartThread.java`, `EndThread.java` and `ThreadStatusMonitor.java` also use, unbalanced by design (release → start thread → re-acquire); framing them there would break those callers |
| `rv-monitor/rv-monitor/src/test/java/.../DispatcherLockReleaseTest.java` | NEW — task 3.6's red test |
| `evidence/g_regeneration.md` | NEW — the `jca` regeneration diff (3.5 and 3.8 in one run) |

## Where the table goes, and why there

`BaseMonitor.toString()` `:806-812`:

```java
// state declaration
for (PropertyAndHandlers prop : props) {
    PropMonitor propMonitor = propMonitors.get(prop);
    ret += propMonitor.getStateDeclarationCode(this.isAtomicMoniorUsed());
}
ret += "\n";
```

This is where the `static final int Prop_N_transition_*[]` arrays land in the generated class, so the name table sits beside its structural siblings. Build it from `this.events` (`BaseMonitor.java:122`, populated at `:179` from `rvmSpec.getEvents()`) in `getIdNum()` order.

**One table per monitor class, not per property.** `getIdNum()` is spec-wide — it is the same index `handleEvent(idnum, …)` and `MonitorTermination`'s switch already use — while `Prop_N_transition_*` is per property. A per-property table would be indexed by a spec-wide number and would be wrong for any spec with more than one property.

**Emit the table and use the indices from the same iteration**, so a name and its index cannot disagree. That property is the whole reason this group exists instead of a hand-written array in each `.mop`'s `declarations` (design D-4).

## Expansion contract

- **event body** (`BaseMonitor.printEventMethod`, `RawMonitor`): `__EVENTNAME` → the string literal `"<event.getId()>"`. The `EventDefinition` is already in scope (`int idnum = event.getIdNum();` opens both methods). No field, no lookup, no runtime cost.
- **helper** (`BaseMonitor.toString()`, after `checkIfAtomicMonitorCanBeEnabled()` at `:665`, beside the table): one `RVM_eventName()` per monitor class. It reads `this.getLastEvent()`; in the atomic shape it subtracts one (the stored value is `idnum + 1`), in the non-atomic shape it uses the value as is; the no-event value (`0` atomic, `-1` non-atomic) returns the sentinel `"none"`, anything else returns the table entry. Never an out-of-range access. The shape decision is made here and only here, where `isAtomicMoniorUsed()` is legal.
- **handler body** (`HandlerMethod`): `__EVENTNAME` → the call `RVM_eventName()` — not a direct table lookup (the constructor runs before the shape is known and must not decode the index itself). Non-outermost monitor → literal `"none"`.
- **fail closed**: if the literal `__EVENTNAME` survives anywhere in the generated Java, generation aborts naming file and line. An unexpanded macro would otherwise reach `javac` as an undefined identifier — or, inside a string, be reported as text and read as a fact.

## The lock framing (tasks 3.6-3.8, INV-INS-129, design D-14)

**The measurement.** In the frozen control every one of the 134 dispatchers opens with `while (!MultiSpec_1_RVMLock.tryLock()) { Thread.yield(); }` and closes with `MultiSpec_1_RVMLock.unlock();` (`M:9163-9188` is one), and the file has **0** `finally` blocks; the lock is one `static final ReentrantLock` shared by every specification (`M:9005`). Conditions, event bodies and `@fail`/`@match` handlers all execute inside that region, and nothing in `MonitorWrappers.java` or the aspect catches. So an exception raised inside — the frozen set has a reachable one, `KeyPairGeneratorSpec`'s `switch(null)` — propagates into the application frame with the lock still held. Because the lock is reentrant, the throwing thread keeps entering; every *other* thread spins forever in the `yield` loop at its next monitored call.

**Task 3.6 — red test first.** Generate a small specification whose `@fail` handler throws; call the dispatcher once on thread A (the throw, caught by the test), then once **from thread B** with a bounded wait (`Future.get(2, SECONDS)` or equivalent); assert that B's call completes. It must be red today. Two calls on the **same** thread are not a test: `ReentrantLock.tryLock()` succeeds for the owner, so the second call passes with the lock still leaked. Record the red output under `evidence/`.

**Task 3.7 — emit the framing in `Advice.java`.** After the acquisition at `:176-177` emit `try {`; replace the bare release at `:254-256` by `} finally { <release> }`. The framing applies to the explicit `tryLock` form only — the one every generated dispatcher uses, because `GlobalLock.useImplicitLock` is hard-set `false` (`GlobalLock.java:18`; the `:44`/`:60` implicit branches emit nothing) — so there is no second form to frame. Nothing else: not which advices fire, not the lock's identity, not the spin loop, not `GlobalLock`'s fragments (see the file inventory). The exception still propagates to the application; only the release becomes unconditional. Also honour the `useFineGrainedLock` branch as it stands — the framing wraps whatever release that branch emits today.

**Task 3.8 `[GEN]` — regenerate and diff** in the same run as 3.5 `[GEN]`, in the between-waves step after 3.9's `mvn install`: `jca` against `results/gh101_group8_jca_frozen_control/monitors/`; the only admissible differences are the framing, the event-name table and the `RVM_eventName()` helper (no expanded macro — the frozen `jca` writes no `__EVENTNAME`); assert `grep -c tryLock == grep -c unlock == grep -c finally` on the regenerated monitor (134/134/134 for `jca`) and that every acquisition sits inside a `try`; record in `evidence/g_regeneration.md`. Note there that `rvsec-agent/pom.xml:94-111` regenerates the JSE agent's monitor from `resources/jca` at every build without `-DskipMopAgent=true` (task 3.9 diffs it once).

## Commands

```bash
# every Java/Maven line is prefixed (shell state does not persist between tool calls)
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
# from the reactor root (..)
mvn -q test -pl rv-monitor/rv-monitor
mvn -q install -DskipTests -DskipMopAgent=true          # ~12 min, task 3.9 — BETWEEN WAVES, by the orchestrator.
# Tasks 3.5 and 3.8 run immediately after it, in the same step: the regeneration needs this generator on the
# toolchain, so they cannot run inside wave 1. Wave 1 delivers 3.0-3.4, 3.6 and 3.7 only.

# regeneration diff [GEN] (RVSEC_HOME set; TMPDIR off tmpfs)
export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR
python3 scripts/gh104_regen_diff.py --specs-dir ../rvsec/rvsec-mop/src/main/resources/jca                       --control results/gh101_group8_jca_frozen_control/monitors/    --manifest data/gh104/jca_frozen_control.sha256 --expect table,helper,lock-framing
grep -rn "__EVENTNAME" <scratch>/monitors/            # must be empty
git status --short -- rv-monitor/rv-monitor rv-android/scripts/gh104_regen_diff.py rv-android/data/gh104   # from the repository root; pathspec always
```

## Acceptance

- `EventNameMacroTest` (task 3.1, red first) green on all three cases of INV-INS-120, with the handler case exercised on **one specification of each monitor shape** (`CipherSpec` or `SecretKeySpecSpec` for the atomic shape; `HMACParameterSpecSpec` or `TrustManagerFactorySpec` for the non-atomic one — `TrustManagerFactorySpecMonitor` extends `AbstractSynchronizedMonitor` in the frozen control, `:8778`). For each shape the test asserts two things: the handler of the **first** dispatched event sees that event's own name (not the next one — the atomic off-by-one), and a handler run before any event sees `none`.
- `DispatcherLockReleaseTest` red before task 3.7 (second thread blocked), green after; the framing is in `Advice.java`, `GlobalLock.java` untouched.
- Regenerating `jca` differs from the recorded control **only** by the new table, by the `RVM_eventName()` helper and by the `try`/`finally` framing of every dispatcher (no expanded macro: the frozen `jca` writes no `__EVENTNAME`) (acquisitions = releases = `finally` blocks) — no transition row, no state count, no other dispatch line changes. The diff is recorded in `evidence/g_regeneration.md`. One control is the whole control set: the generator edit is global to all 191 `.mop` files, so `jca` exercises the same emitter paths any set derived from it would; the archived `jca_android_bug_predicate` is edited, regenerated and replayed by no task.
- `grep -rn "__EVENTNAME"` over any generated monitor returns nothing.
- Reactor built (task 3.9, run by the orchestrator between waves); `lib/` jars refreshed (Group 4 task 4.6 also refreshes `instr-cli.jar` — the orchestrator runs the two installs in sequence; the last one wins and its sha256 is the one recorded). Task 3.9's diff of the JSE agent's regenerated monitor is against the frozen control (`rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` is gitignored; there is no committed source).
- Two commits, made by the orchestrator with explicit pathspecs and separately from Group 5's `rv-monitor-rt` commit: `feat(rv-monitor): macro __EVENTNAME, tabela de nomes de evento e helper RVM_eventName por monitor (refs #104)` and `fix(rv-monitor): libera o lock global do dispatcher em todo caminho de saída (refs #104)`.
