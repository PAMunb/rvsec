# Group 3 — G: `__EVENTNAME` in the monitor generator

Tracked checkboxes: `tasks.md` §3. Wave 1, in parallel with Groups 1, 2, 4, 5, 6. **Blocks Group 7** (E1 messages): no report site can compose `ev=` until this macro expands. Edits one submodule only — `rv-monitor/rv-monitor` (the *generator*). Group 5 edits `rv-monitor/rv-monitor-rt` (`ViolationRecorder`); the two are disjoint source sets. Shared resources are serialised per the `tasks.md` dispatch hints: `sdk use java 21.0.12-tem` in every shell; `export TMPDIR=<dir under /home>` before generating; the Maven lock for `mvn install` (3.9) and the generation lock for 3.0/3.5/3.8 (one monitor generation at a time across wave 1). `evidence/...` means `data/gh104/evidence/...`.

## Subagent brief

Read `design.md` D-4 (the decision and the superseded one, so you do not re-take it) and D-14, and the `instrumentation` delta requirements `Event-Name Emission by the Monitor Generator` (INV-INS-120) and `The Generated Dispatcher Releases Its Lock on Every Exit` (INV-INS-129). You are doing two things in one module: adding **one macro and one table** (tasks 3.1-3.5, additive — no existing generated line changes shape) and **framing the dispatcher's guarded region** so the global lock is released on every exit (tasks 3.6-3.8 — the one existing emission this group does change, and only in its `try`/`finally` framing). The acceptance step proves both by regenerating two frozen sets and diffing: the only admissible differences are the table, the expanded macros and the framing.

Do not touch any `.mop` file — including the successor set `jca_android`, which Group 2 builds in parallel with you and Group 7 fills with envelopes afterwards, and including the archived `jca_android_bug_predicate/`, which you only ever regenerate from. Do not touch `javamop` — it carries the Java block from `.mop` to `.rvm` verbatim, which is why `__LOC` traverses it today without javamop knowing what it is.

## The facts this group rests on (all verified 2026-08-17, file:line)

**The monitor already records the last event, in two shapes that coexist in one generated file.** In the frozen control (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`) there are **15 classes of the atomic/table shape** and **8 of the non-atomic shape**:

| shape | condition | where the last event lives | how to read it |
|---|---|---|---|
| atomic / table | `BaseMonitor.java:114-118` `isAtomicMoniorUsed()` (`pairValueField != null`) | packed into `pairValue` as `((lastEvent + 1) << numStateBits) \| state` (`BaseMonitor.java:1161-1166`) | `this.getLastEvent()` (emitted at `:1177-1179`) |
| non-atomic | otherwise | plain field `RVM_lastevent` (`BaseMonitor.java:106`; assigned inline at `:425-428`) — the field and its accessor are **inherited from the runtime**, `rv-monitor-rt` `AbstractSynchronizedMonitor.java:5` (`protected int RVM_lastevent = -1`) and `:21` (`public final int getLastEvent()`), declared on `IMonitor.java:19`; the generator declares neither | `this.getLastEvent()` — the same call as the atomic shape |

The generator branches between the two only where it emits *termination* code: `BaseMonitor.java:1044-1048` passes `"int lastEvent = this.getLastEvent();"` / `"lastEvent"` for the atomic shape and `null` otherwise, and `MonitorTermination.java:73` defaults the variable to `"RVM_lastevent"`. **Do not reuse that branch in `HandlerMethod`**: the `HandlerMethod` objects are constructed in `initialize` (`BaseMonitor.java:226`), before `checkIfAtomicMonitorCanBeEnabled()` runs (`:665`, at the top of `toString()`), so `isAtomicMoniorUsed()` throws `IllegalStateException` there (`:115`); and the raw field `RVM_lastevent` is undefined in the atomic shape. Since `getLastEvent()` exists in both shapes, the handler expansion is simply `this.getLastEvent()`. A non-outermost monitor (`isOutermost == false`, suffix mode; unused by `jca`) has neither — emit the literal `"none"` there and let the fail-closed check name the case.

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

`SuffixMonitor` does not substitute (only a commented `has__LOC` at `:245`). `logicpluginshells/fsm/CFSM.java` and `tfsm/CTFSM.java` also `replaceAll("__RESET", …)` but are the **C** output — they import `com.runtimeverification.rvmonitor.c.rvc.CSpecification` — and are off this path.

## Task 3.0 — the diff tool and the control it compares against, before the generator moves

Tasks 3.5 and 3.8 diff two regenerated sets against controls. `jca` has one in the tree — `results/gh101_group8_jca_frozen_control/monitors/`. The derived set has **none**, and no earlier artefact of this change creates it, so 3.0 does both jobs before a line of the generator changes:

1. Write `scripts/gh104_regen_diff.py`. It regenerates one set's monitors into scratch with the current toolchain, diffs them against a recorded control directory, classifies each difference, and exits non-zero on anything outside an `--expect` list. It is the only `gh104_*` script with no creating task before 2026-08-18.
2. Generate the derived set's control **with the generator still unmodified**, into `results/gh104_derived_pre_generator_control/monitors/`, and commit its sha256 manifest as `data/gh104/derived_pre_generator_control.sha256`; also commit `data/gh104/jca_frozen_control.sha256` for `results/gh101_group8_jca_frozen_control/monitors/`, which is unversioned today.

**Address the derived set by whichever name it currently carries** — `rvsec-mop/src/main/resources/jca_android/` before Group 2 task 2.1 renames it, `jca_android_bug_predicate/` after. The bytes are identical under both names, which is precisely why this group needs no dependency on Group 2. Write the name you measured under into `evidence/g_regeneration.md`; `tasks/E0-baseline.md` applies the same discipline to the same directory.

## File inventory

| file | edit |
|---|---|
| `rv-monitor/rv-monitor/src/main/java/.../output/monitor/BaseMonitor.java` | `:806-812` emit the event-name table; `:350-368` expand `__EVENTNAME` to a literal |
| `.../output/monitor/HandlerMethod.java` | `:36-48` expand `__EVENTNAME` to the shape-aware table lookup |
| `.../output/monitor/RawMonitor.java` | `:90-105` mirror the event-body substitution |
| `rv-monitor/rv-monitor/src/main/java/.../rvj/RVMNameSpace.java` | `:24` area — reserve the table's name beside `RVM_lastevent` |
| `scripts/gh104_regen_diff.py` | NEW — task 3.0: regenerate a set into scratch, diff against a recorded control directory, classify each difference, exit non-zero on anything outside `--expect` |
| `results/gh104_derived_pre_generator_control/monitors/` + `data/gh104/derived_pre_generator_control.sha256`, `data/gh104/jca_frozen_control.sha256` | NEW — task 3.0: the derived set's control, generated with the **unmodified** generator, and the manifests of both controls. `results/` is gitignored, so the committed manifests are the versioned artefacts and the check must fail with a named message when a directory is absent or disagrees with its manifest |
| `rv-monitor/rv-monitor/src/test/java/.../EventNameMacroTest.java` | NEW |
| `.../output/combinedoutputcode/event/advice/Advice.java` | `:176-177` (acquire, `if (isSync) ret += this.globalLock.getAcquireCode();`) and `:254-256` (release, `if (!Main.useFineGrainedLock) { if (isSync) ret += this.globalLock.getReleaseCode(); }`) — emit `try {` after the acquisition and `} finally { <release> }` in place of the bare release (task 3.7). **Not** `GlobalLock.java:40-67`: its `getAcquireCode()`/`getReleaseCode()` are string fragments that `BaseMonitor.java:543,567,583,587` (`execEvent`), `StartThread.java`, `EndThread.java` and `ThreadStatusMonitor.java` also use, unbalanced by design (release → start thread → re-acquire); framing them there would break those callers |
| `rv-monitor/rv-monitor/src/test/java/.../DispatcherLockReleaseTest.java` | NEW — task 3.6's red test |
| `evidence/g_regeneration.md` | NEW — the two regeneration diffs |

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
- **handler body** (`HandlerMethod`): `__EVENTNAME` → a lookup of the table at the last-event index, through `this.getLastEvent()` in **both** shapes (see the table above — no `isAtomicMoniorUsed()` call in the constructor, it throws there). Index `-1` (no event has transitioned the monitor) → the sentinel `none`. Never an out-of-range access. Non-outermost monitor → literal `"none"`.
- **fail closed**: if the literal `__EVENTNAME` survives anywhere in the generated Java, generation aborts naming file and line. An unexpanded macro would otherwise reach `javac` as an undefined identifier — or, inside a string, be reported as text and read as a fact.

## The lock framing (tasks 3.6-3.8, INV-INS-129, design D-14)

**The measurement.** In the frozen control every one of the 134 dispatchers opens with `while (!MultiSpec_1_RVMLock.tryLock()) { Thread.yield(); }` and closes with `MultiSpec_1_RVMLock.unlock();` (`M:9163-9188` is one), and the file has **0** `finally` blocks; the lock is one `static final ReentrantLock` shared by every specification (`M:9005`). Conditions, event bodies and `@fail`/`@match` handlers all execute inside that region, and nothing in `MonitorWrappers.java` or the aspect catches. So an exception raised inside — the frozen set has a reachable one, `KeyPairGeneratorSpec`'s `switch(null)` — propagates into the application frame with the lock still held. Because the lock is reentrant, the throwing thread keeps entering; every *other* thread spins forever in the `yield` loop at its next monitored call.

**Task 3.6 — red test first.** Generate a small specification whose `@fail` handler throws; call the dispatcher once on thread A (the throw, caught by the test), then once **from thread B** with a bounded wait (`Future.get(2, SECONDS)` or equivalent); assert that B's call completes. It must be red today. Two calls on the **same** thread are not a test: `ReentrantLock.tryLock()` succeeds for the owner, so the second call passes with the lock still leaked. Commit the red output under `evidence/`.

**Task 3.7 — emit the framing in `Advice.java`.** After the acquisition at `:176-177` emit `try {`; replace the bare release at `:254-256` by `} finally { <release> }`. Nothing else: not which advices fire, not the lock's identity, not the spin loop, not `GlobalLock`'s fragments (see the file inventory). The exception still propagates to the application; only the release becomes unconditional. Also honour the `useFineGrainedLock` branch as it stands — the framing wraps whatever release that branch emits today.

**Task 3.8 — regenerate and diff** in the same run as 3.5: `jca` against `results/gh101_group8_jca_frozen_control/monitors/` and the archived `jca_android_bug_predicate` against its recorded control; the only admissible differences are the framing, the event-name table and the expanded macros; assert `grep -c tryLock == grep -c unlock == grep -c finally` on each regenerated monitor (134/134/134 for `jca`) and that every acquisition sits inside a `try`; record in `evidence/g_regeneration.md`. Note there that `rvsec-agent/pom.xml:94-111` regenerates the JSE agent's monitor from `resources/jca` at every build without `-DskipMopAgent=true` (task 3.9 diffs it once).

## Commands

```bash
# from the reactor root (..)
mvn -q test -pl rv-monitor/rv-monitor
mvn -q install -DskipTests -DskipMopAgent=true          # ~12 min, needed before regeneration

# regeneration diff (RVSEC_HOME set, TMPDIR off tmpfs)
# $DERIVED is the derived set under whichever name it currently carries: `jca_android` before Group 2
# task 2.1 renames it, `jca_android_bug_predicate` after. Same bytes; task 3.0 recorded which one it used.
python3 scripts/gh104_regen_diff.py --specs-dir ../rvsec/rvsec-mop/src/main/resources/jca        --control results/gh101_group8_jca_frozen_control/monitors/    --manifest data/gh104/jca_frozen_control.sha256 --expect table,macro,lock-framing
python3 scripts/gh104_regen_diff.py --specs-dir ../rvsec/rvsec-mop/src/main/resources/"$DERIVED" --control results/gh104_derived_pre_generator_control/monitors/ --manifest data/gh104/derived_pre_generator_control.sha256 --expect table,macro,lock-framing
grep -rn "__EVENTNAME" <scratch>/monitors/            # must be empty
```

## Acceptance

- `EventNameMacroTest` green on all three cases of INV-INS-120, with the handler case exercised on **one specification of each monitor shape** (`CipherSpec` or `SecretKeySpecSpec` for the atomic shape; `HMACParameterSpecSpec` or `TrustManagerFactorySpec` for the non-atomic one — `TrustManagerFactorySpecMonitor` extends `AbstractSynchronizedMonitor` in the frozen control, `:8778`).
- `DispatcherLockReleaseTest` red before task 3.7 (second thread blocked), green after; the framing is in `Advice.java`, `GlobalLock.java` untouched.
- Regenerating `jca` and the archived `jca_android_bug_predicate` differs from the recorded controls **only** by the new table, by expanded macros and by the `try`/`finally` framing of every dispatcher (acquisitions = releases = `finally` blocks) — no transition row, no state count, no other dispatch line changes. Both diffs committed in `evidence/g_regeneration.md`. The successor `jca_android` is deliberately **not** a control for this group: it is being built by Group 2 in parallel and has no recorded control yet; Group 7 task 7.7 regenerates it once it is stable.
- `grep -rn "__EVENTNAME"` over any generated monitor returns nothing.
- Reactor builds under the Maven lock; `lib/` jars refreshed (Group 4 task 4.6 also refreshes `instr-cli.jar` — serialised by the same lock; the last one wins and its sha256 is the one recorded). Task 3.9's diff of the JSE agent's regenerated monitor is against the frozen control (`rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` is gitignored; there is no committed source).
- Two commits: `feat(rv-monitor): macro __EVENTNAME e tabela de nomes de evento por monitor (refs #104)` and `fix(rv-monitor): libera o lock global do dispatcher em todo caminho de saída (refs #104)`.
