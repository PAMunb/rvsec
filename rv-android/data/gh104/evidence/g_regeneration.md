# G — regeneration of the frozen `jca` against its control (tasks 3.5, 3.8, 3.9)

Run 2026-08-19, after task 3.9 installed the modified generator
(`mvn clean install -DskipMopAgent -DskipTests` at the reactor root, BUILD SUCCESS in 1m17s).

## Result

```
python3 scripts/gh104_regen_diff.py \
  --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" \
  --control results/gh101_group8_jca_frozen_control/monitors \
  --manifest data/gh104/jca_frozen_control.sha256 \
  --expect table,helper,lock-framing
→ RESULT: OK (exit 0)
```

| category | lines | meaning |
|---|---|---|
| `table` | 92 | the per-class event-name array |
| `helper` | 130 | the per-class `RVM_eventName()` |
| `lock-framing` | 402 | the `try`/`finally` around the guarded region |
| `other` | **0** | nothing else moved |
| indent-only | 6,010 | the framing adds a brace level and re-indents every dispatcher body |

`macro` = 0 and no unexpanded `__EVENTNAME` survives — expected, since the frozen `jca` writes
none. Lock accounting: **134 acquisitions, 134 releases, 134 `finally` blocks**, against the
control's 134 / 134 / **0**. `MultiSpec_1MonitorAspect.aj` and `.json` are byte-identical: javamop
is untouched.

## The control reproduces only under the JDK it was generated with

**This is a precondition of the run above and it is not in the plan.** The plan prefixes every
Java command line with JDK 21. Under JDK 21 this diff fails with 347 `other` differences, all of
them in the `Prop_N_transition_*` rows: the same 133 tables with the same event names, carrying
different state numbers.

### What is established, and how

**1. It is not this change.** Three-way comparison of the transition tables:

| generation | transition tables |
|---|---|
| control (2026-08-08) | reference |
| pre-change generator (`c069bc3b`), JDK 21 | **differ** from the control |
| post-change generator, JDK 21 | identical to pre-change, differ from the control |
| post-change generator, **JDK 25** | **identical to the control** |

The pre-change and post-change generators produce the same tables, so the change does not move a
transition row.

**2. It is deterministic within a JDK.** Three separate invocations per JDK: the 23 `.rvm` and the
generated `MultiSpec_1RuntimeMonitor.java` are byte-identical within each version. The variation is
across versions, not across runs.

**3. javamop is not implicated.** The 23 `.rvm` files are byte-identical between JDK 21 and JDK 25,
as are `MultiSpec_1MonitorAspect.aj` and `.json`.

**4. The divergence arises inside the ERE→FSM conversion of the logic repository.** `rv-monitor -v`
prints the exchange. The request (`== send to logic repository ==`, the `ere` formula and the event
list) is **byte-identical** across the two JDKs; the reply (`== result from logic repository ==`,
the `fsm` formula) **differs**, in the order of the states and of the transitions within a state.
Downstream, `JavaFSM.java:81-91` numbers states by the order of `fsmInput.getItems()`, so an order
difference in that reply becomes a state-number difference in the generated monitor.

**5. The automata are the same up to relabelling — no verdict moves.** Of the 23 monitor classes
that carry an automaton, 11 differ between the JDKs. For each of the 11 there is a bijection of
states that fixes the initial state 0 and satisfies `π(T_A[e][s]) = T_B[e][π(s)]` for every event
`e` and state `s`, and that carries the `fail` and `match` category sets onto their counterparts —
e.g. `SignatureSpecMonitor`, `π = {1↔2, 3→6, 5→7, 6→3, 7→5}`, `fail {8}→{8}`, `match {3,4}→{4,6}`.
The remaining 12 classes are byte-identical. A monitor generated under either JDK therefore accuses
exactly the same traces; only the integers labelling its states differ.

### What is NOT established

The exact data structure whose iteration order changes. The visible candidate is
`ERE.hashCode()` (`plugins_logicrepository/ere/.../ERE.java:98-106`), which falls back to
`super.hashCode()` — the JVM identity hash — for a leaf, and `Symbol` is a leaf; a hash-ordered
iteration keyed on such objects would be stable within a JVM version and vary across versions,
which is the observed pattern. **This was not confirmed.** Forcing the identity hash to a
version-independent scheme, which would prove it, destroys the subject: both
`-XX:hashCode=2` (constant) and `-XX:hashCode=3` (sequential) make the conversion fail with
`Logic Engine Error: null`. A second loose end: the FSM text in the reply is formatted `s0[` with
two-space indentation, while `FSM.print` in the running `ere.jar` emits `s0 [` with three, so the
formatter is some other code path, not chased here.

Only two JDKs were measured, 21.0.12 and 25.0.3. Nothing is claimed about the versions between them.

### Consequence

D-4 rests the reproducibility of published measurements on pinning the toolchain rather than
freezing the generator. This is that pin, and it was incomplete: **the JDK is part of the toolchain
a generated monitor is pinned to**, and the control was made under JDK 25. Anything that
regenerates a monitor for comparison against this control runs under
`$HOME/.sdkman/candidates/java/25.0.3-tem`; the reactor still *builds* under 21, which is what the
pom targets.

Because the difference is a relabelling and not a behavioural change, a monitor generated under
JDK 21 is as correct as one generated under 25 — what it is not is byte-comparable against an
artefact produced by the other. That is a constraint on *diffing*, not on running.

## Task 3.9 — the JSE agent's monitor

`rvsec-agent/pom.xml` runs `mop-gen` on every build that does not carry `-DskipMopAgent`,
regenerating `rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` from
`resources/jca`. That file is gitignored, so there is no committed source to diff against; it is
compared to the frozen control instead.

Re-emitted once with the new generator (`mvn install -DskipTests -pl rvsec/rvsec-agent`, JDK 25):

| | control | regenerated agent monitor |
|---|---|---|
| lines | 16,487 | 18,655 |
| `tryLock` / `unlock()` | 134 / 134 | 134 / 134 |
| `finally` | 0 | 157 |
| `RVM_eventName()` helpers | 0 | 23 — one per monitor class |
| unexpanded `__EVENTNAME` | 0 | 0 |

Table, helper and framing only; the acquisition and release counts are unchanged.

That build **fails afterwards**, at the `agent-gen` goal, with `aspectjrt.jar is missing from the
classpath. Halting.` The failure is pre-existing, unrelated to this change and downstream of the
regeneration — `mop-gen` has already run and written the monitor when it happens. It is why
`-DskipMopAgent` is the standard flag for building this reactor.

## Impact on this change, measured artefact by artefact

The question the pin raises is which of gh104's instruments read a state number. Four do not, one
does, and one now says so.

**The gates are invariant.** `scripts/gh104_gates.py` was run over the frozen `jca` monitor
generated under JDK 21 and over the control generated under JDK 25, same allow-list, same CrySL
oracle. Every gate returns the same hit set — same specifications, same events, same verdicts,
same counts: G-2 3, G-2a 1, G-2b′ 8, G-2c 1, G-2d 2, G-6′ 1, G-ERE 1, G-CONF 4, G-PRED 304. The
only textual difference in the whole report is that G-2b′ echoes the raw transition row in its
hit payload (`KeyStoreSpec.g2`, `[0,5,0,5,5,5]` against `[0,0,5,5,5,5]`) — a diagnostic field, not
a verdict. No test asserts on it.

**The gate allow-list is invariant.** `data/jca/gate_allowlist.csv` keys its 34 rows by event name
and `*`; not one row names a state number.

**The differential harness is invariant.** `gh104_diff_harness.py` generates both snapshots
through the same `generate()` in one run, so both sides carry the same labelling whatever the JDK,
and it classifies by which event accuses, never by a state number.

**Device runs and published measurements are unaffected.** A relabelled monitor accuses the same
traces, so nothing measured on a device or in the published corpus depends on this.

**Only the regeneration diff is sensitive**, because it is the one instrument that compares two
monitors byte for byte. It now names the cause instead of printing hundreds of rows: when every
substantive difference is a state label and the remainder is a pure reordering, it prints the
relabelling diagnosis with the JDK it is running under. Measured on the failing JDK-21 run: 347
unexpected differences = 300 state labels + 14 reordered declarations (a pure permutation, verified
by multiset) + 33 braces or blanks.

**One residue is documentary, not executable.** `design.md`, `tasks.md` and the conformance record
cite state numbers and transition rows read off the frozen control — `{4,4,4,4,4}` at
`MultiSpec_1RuntimeMonitor.java:6369`, `fail` = 4, `gtm1` = `{3,0,3,3}`, and the rows of task 8.12.
Those citations are true of the control, which is a JDK-25 artefact; read against a monitor
regenerated under another JDK they will not match, and the reader needs this section to know why.
