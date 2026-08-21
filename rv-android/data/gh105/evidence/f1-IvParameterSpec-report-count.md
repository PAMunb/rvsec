# IvParameterSpec — how many reports each snapshot emits (gh105 task 3.3)

The differential harness classified both violating traces as `moved`: the accusation
changes event, `c3` → `c1` and `c4` → `c2`, and keeps its code. That is all it can
say, and it is less than the truth here.

`gh104_diff_harness.py` replays a trace by calling every dispatcher whose pointcut
matches the line, and records **one** accusing event and **one** envelope per
dispatcher call (`TraceRunner.replay`: `if (after.size() > before)` adds a single
entry, and `envelope(...)` returns the first error of that specification it finds in
a `HashSet`). A dispatcher call that adds *two* errors is therefore reported as one.
That is exactly what the pre-image does here: the orphan's own
`UnsatisfiedConstraint` and the `InvalidSequenceOfMethodCalls` its transition to the
fail state produces come from the same call to `IvParameterSpecSpec_c3Event`, and the
harness shows whichever the set iterated first.

Counting the whole `ErrorCollector` instead, against the two snapshots the harness had
already generated (`--a backup/gh105-preimage/jca_android`, `--b` the working set):

| construction | A (pre-image) | B (fused) |
|---|---|---|
| `new IvParameterSpec(iv)` with an unrandomised `iv` | **2** — `IVPARAMETERSPEC-CONSTR-00 ev=c3` and `IVPARAMETERSPEC-ORDER-00 ev=c3` | **1** — `IVPARAMETERSPEC-CONSTR-00 ev=c1` |
| `new IvParameterSpec(iv, 0, 16)` with an unrandomised `iv` | **2** — `IVPARAMETERSPEC-CONSTR-01 ev=c4` and `IVPARAMETERSPEC-ORDER-00 ev=c4` | **1** — `IVPARAMETERSPEC-CONSTR-01 ev=c2` |

So this file behaves like the `fsm`-based files of tasks 3.1 and 3.2 after all: the
orphan was drawing a second, spurious ordering report for a call sequence the rule
accepts, and the fusion removes it. It is visible in the generated monitor as well —
`Prop_1_transition_c3[] = {2, 2, 2}` sends every state to the fail state, and the
dispatcher runs `Prop_1_handler_fail()` whenever the event leaves the monitor there.

## Reproducing

Both snapshots live under the harness's scratch directory, which its JSON summary
names (`"scratch"`). Compile against the cached rvsec-mop test classpath
(`rvsec/rvsec-mop/target/gh104-classpath.txt`) and run the program below once per side
with the snapshot's `work/classes/classes` directory as the second argument. Swap the
constructor and the dispatcher arity (2 → 4 parameters, `iv, 0, 16, spec`) for the
three-argument row.

```java
String side = args[0];
URL classes = new java.io.File(args[1]).toURI().toURL();
URLClassLoader loader = new URLClassLoader(new URL[]{classes}, Probe.class.getClassLoader());
Class<?> rm = loader.loadClass("mop.MultiSpec_1RuntimeMonitor");

byte[] iv = new byte[16];                       // nothing randomises it
IvParameterSpec spec = new IvParameterSpec(iv);

for (Method m : rm.getDeclaredMethods()) {      // every dispatcher the call resolves to
    if (!m.getName().startsWith("IvParameterSpecSpec_c")) continue;
    if (m.getParameterCount() != 2) continue;
    m.invoke(null, iv, spec);
}
Class<?> ec = loader.loadClass("br.unb.cic.mop.eh.ErrorCollector");
Object collector = ec.getMethod("instance").invoke(null);
System.out.println(side + " errors="
    + ((java.util.Collection<?>) ec.getMethod("getErrors").invoke(collector)).size());
```

## What this says about the instrument

The harness's report is a floor on the number of accusations, not the number itself,
whenever one dispatcher call can accuse twice — which is the shape of every orphan
that both carries a report of its own and falls out of the automaton. Tasks 3.4 to 3.6
touch three more such files (`SecretKeySpecSpec.c3`/`c4`, `PBEKeySpecSpec.err1`-`err3`,
`PBEParameterSpecSpec.c3`), and a `moved` verdict there should be read the same way:
as "the accusation changed event", never as "the count did not change".
