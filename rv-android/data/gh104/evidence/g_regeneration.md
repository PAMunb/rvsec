# Tasks 3.9, 3.5 and 3.8 — the `jca` regeneration diff

**STUB — not yet run.** These three tasks are one between-waves step, in that
order, executed by the orchestrator after wave 1's generator edits have landed:
the regeneration needs the repaired generator on the toolchain, which is what
3.9's reactor install puts there. Wave 1 delivered 3.0-3.4, 3.6 and 3.7 only.

## The state the generator is in

`rv-monitor/rv-monitor` carries both halves of group G:

- **INV-INS-120** — `BaseMonitor` emits, into every monitor class, a
  `static final String[] RVM_eventNames` table and a `final String RVM_eventName()`
  decoder; `__EVENTNAME` expands to a string literal in event bodies
  (`BaseMonitor.printEventMethod`, `RawMonitor.doEvent`) and to `RVM_eventName()`
  in handler bodies (`HandlerMethod`); `Main.writeCombinedOutputFile` aborts if
  the literal survives.
- **INV-INS-129** — `Advice.enterGuardedRegion` emits `try {` after the lock
  acquisition and `Advice.leaveGuardedRegion` emits `} finally { <release> }` in
  place of the bare release. `GlobalLock.java` is untouched.

The table and the helper are emitted **unconditionally**, whether or not a
specification writes the macro. That is why the frozen `jca` — which writes no
`__EVENTNAME` — still differs from its control: by the table, by the helper and
by the framing, and by nothing else.

## Commands to run

```bash
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem
export PATH=$JAVA_HOME/bin:$PATH

# 3.9 — from the reactor root (~12 min)
mvn -q install -DskipTests -DskipMopAgent=true

# 3.5 + 3.8 — from rv-android, one run
export TMPDIR=$HOME/tmp-gh104 && mkdir -p "$TMPDIR"
python3 scripts/gh104_regen_diff.py \
    --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" \
    --control results/gh101_group8_jca_frozen_control/monitors \
    --manifest data/gh104/jca_frozen_control.sha256 \
    --expect table,helper,lock-framing
```

## What to expect

| check | expected |
|---|---|
| classified categories | only `table`, `helper`, `lock-framing` |
| `macro` category | 0 — the frozen `jca` writes no `__EVENTNAME` |
| `other` category | 0 |
| lock accounting on the regenerated monitor | 134 acquisitions / 134 releases / **134** `finally` blocks (it is 134 / 134 / **0** on the control) |
| every acquisition inside a `try` | yes |
| `indent-only` lines | non-zero and large: the framing adds one brace level to every dispatcher body and `Tool.changeIndentation` re-indents the file from its brace structure |
| `MultiSpec_1MonitorAspect.aj`, `…​.json` | byte-identical — javamop is untouched by this change |

The script's exit codes: 0 every difference expected, 1 an unexpected
difference, 2 the run could not be made.

## Also to record here

`rvsec/rvsec-agent/pom.xml` regenerates the JSE agent's monitor from
`resources/jca` at every build without `-DskipMopAgent=true`. Task 3.9 diffs
that regenerated monitor once against the frozen control;
`rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` is gitignored, so
there is no committed source to compare against.
