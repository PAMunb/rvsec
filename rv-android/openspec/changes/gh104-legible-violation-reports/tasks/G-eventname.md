# Group 3 — G: `__EVENTNAME` in the monitor generator

Tracked checkboxes: `tasks.md` §3. Wave 1, in parallel with Groups 1, 2, 4, 5, 6. **Blocks Group 7** (E1 messages): no report site can compose `ev=` until this macro expands. Edits one submodule only — `rv-monitor/rv-monitor` (the *generator*). Group 5 edits `rv-monitor/rv-monitor-rt` (`ViolationRecorder`); the two are disjoint and need no lock.

## Subagent brief

Read `design.md` D-4 (the decision and the superseded one, so you do not re-take it) and the `instrumentation` delta requirement `Event-Name Emission by the Monitor Generator` (INV-INS-120). You are adding **one macro and one table**; you are not changing any existing emission. Every edit is additive: no existing generated line may change shape, and the acceptance step proves it by regenerating two frozen sets and diffing.

Do not touch any `.mop` file. Do not touch `javamop` — it carries the Java block from `.mop` to `.rvm` verbatim, which is why `__LOC` traverses it today without javamop knowing what it is.

## The facts this group rests on (all verified 2026-08-17, file:line)

**The monitor already records the last event, in two shapes that coexist in one generated file.** In the frozen control (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`) there are **15 classes of the atomic/table shape** and **8 of the non-atomic shape**:

| shape | condition | where the last event lives | how to read it |
|---|---|---|---|
| atomic / table | `BaseMonitor.java:114-118` `isAtomicMoniorUsed()` (`pairValueField != null`) | packed into `pairValue` as `((lastEvent + 1) << numStateBits) \| state` (`BaseMonitor.java:1161-1166`) | `this.getLastEvent()` (emitted at `:1177-1179`) |
| non-atomic | otherwise | plain field `RVM_lastevent` (`BaseMonitor.java:106`), assigned inline in the event method | the field itself — **no accessor is generated** |

The generator already branches between the two for exactly this purpose: `BaseMonitor.java:1044-1048` passes `"int lastEvent = this.getLastEvent();"` / `"lastEvent"` for the atomic shape and `null` otherwise, and `MonitorTermination.java:73` defaults the variable to `"RVM_lastevent"`. **Reuse that branch; do not invent a second one.**

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

## File inventory

| file | edit |
|---|---|
| `rv-monitor/rv-monitor/src/main/java/.../output/monitor/BaseMonitor.java` | `:806-812` emit the event-name table; `:350-368` expand `__EVENTNAME` to a literal |
| `.../output/monitor/HandlerMethod.java` | `:36-48` expand `__EVENTNAME` to the shape-aware table lookup |
| `.../output/monitor/RawMonitor.java` | `:90-105` mirror the event-body substitution |
| `rv-monitor/rv-monitor/src/main/java/.../rvj/RVMNameSpace.java` | `:24` area — reserve the table's name beside `RVM_lastevent` |
| `rv-monitor/rv-monitor/src/test/java/.../EventNameMacroTest.java` | NEW |
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
- **handler body** (`HandlerMethod`): `__EVENTNAME` → a lookup of the table at the last-event index, using `this.getLastEvent()` when `isAtomicMoniorUsed()` and the `RVM_lastevent` field otherwise. Index `-1` (no event has transitioned the monitor) → the sentinel `none`. Never an out-of-range access.
- **fail closed**: if the literal `__EVENTNAME` survives anywhere in the generated Java, generation aborts naming file and line. An unexpanded macro would otherwise reach `javac` as an undefined identifier — or, inside a string, be reported as text and read as a fact.

## Commands

```bash
# from the reactor root (../rvsec)
mvn -q test -pl rv-monitor/rv-monitor
mvn -q install -DskipTests -DskipMopAgent=true          # ~12 min, needed before regeneration

# regeneration diff (RVSEC_HOME set, TMPDIR off tmpfs)
python3 scripts/gh104_regen_diff.py --set jca         --against results/gh101_group8_jca_frozen_control/monitors/
python3 scripts/gh104_regen_diff.py --set jca_android --against <its recorded control>
grep -rn "__EVENTNAME" <scratch>/monitors/            # must be empty
```

## Acceptance

- `EventNameMacroTest` green on all three cases of INV-INS-120, with the handler case exercised on **one specification of each monitor shape** (e.g. `TrustManagerFactorySpec` for the atomic shape, `HMACParameterSpecSpec` for the non-atomic one).
- Regenerating `jca` and `jca_android` differs from the recorded controls **only** by the new table and by expanded macros — no transition row, no state count, no dispatch line changes. Both diffs committed in `evidence/g_regeneration.md`.
- `grep -rn "__EVENTNAME"` over any generated monitor returns nothing.
- Reactor builds; `lib/` jars refreshed (Group 4 task 4.6 also refreshes them — coordinate so the last one wins and its sha256 is the one recorded).
- One commit: `feat(rv-monitor): macro __EVENTNAME e tabela de nomes de evento por monitor (refs #104)`.
