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

The cause is not this change, and the evidence is a three-way comparison:

| generation | transition tables |
|---|---|
| control (2026-08-08) | reference |
| pre-change generator (`c069bc3b`), JDK 21 | **differ** from the control |
| post-change generator, JDK 21 | identical to pre-change, differ from the control |
| post-change generator, **JDK 25** | **identical to the control** |

So the change does not move a single transition row — the pre-change and post-change generators
produce the same tables — and the control is reproducible, but only under JDK 25. Two runs under
one JDK are byte-identical, so the generator is deterministic; what varies is the state numbering
across JDK versions, produced inside rv-monitor. javamop is not implicated: its descriptor
(`MultiSpec_1MonitorAspect.json`) is byte-identical to the control's under either JDK.

D-4 rests the reproducibility of published measurements on pinning the toolchain rather than
freezing the generator. This is that pin, and it was incomplete: **the JDK is part of the
toolchain a generated monitor is pinned to**, and the control was made under JDK 25. Anything that
regenerates a monitor for comparison against this control runs under
`$HOME/.sdkman/candidates/java/25.0.3-tem`; the reactor still *builds* under 21, which is what the
pom targets.

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
