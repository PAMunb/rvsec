# PBEParameterSpecSpec — how many reports each snapshot emits (gh105 task 3.6)

The differential harness classified both violating traces as `moved`: the accusation
changes event, `c3` → `c1`, and keeps its code. As in task 3.3 that is a floor and not
the count. `gh104_diff_harness.py` records **one** accusing event and **one** envelope
per dispatcher call (`TraceRunner.replay`), and here the two reports come from the same
call to `PBEParameterSpecSpec_c3Event`: the orphan's own `UnsatisfiedConstraint` and
the `InvalidSequenceOfMethodCalls` its transition to the fail state produces. The
harness happened to show the ordering one, which is why the `A` column of
`harness/f1-PBEParameterSpecSpec.md` names a code the fusion is not about.

Counting the whole `ErrorCollector` instead, against the two snapshots the harness had
already generated (`--a backup/gh105-preimage/jca_android`, `--b` the working set):

| construction | A (pre-image) | B (fused) |
|---|---|---|
| `new PBEParameterSpec(salt, 1000)` with an unrandomised `salt` | **2** — `PBEPARAMETERSPEC-ORDER-00 ev=c3` and `PBEPARAMETERSPEC-CONSTR-00 ev=c3 val='1000'` | **1** — `PBEPARAMETERSPEC-CONSTR-00 ev=c1 val='1000'` |

So the file behaves like the other twin fusions of this group: the orphan was drawing a
second, spurious ordering report for a construction the rule's ORDER accepts — api30
PBEParameterSpec orders `Cons` with `Cons := c1 | c2`, and states the iteration count
under CONSTRAINTS and the salt under REQUIRES — and the fusion removes it.

## A trace of the corpus that was mislabelled

`PBEParameterSpecSpec.txt` carried the comment "legitimate: the iteration count the rule
requires". It is not legitimate: its salt is a plain `byte[]` that nothing randomises, so
`randomized[salt]` does not hold and the pre-image reaches the orphan through the salt
half of the disjunction, not the count half. Both snapshots accuse it; B's envelope says
`val='10000'`, which is the count being fine while the salt is not. The comment was
corrected in this task, and `PBEParameterSpecSpec-randomised.txt` was added as the trace
that actually satisfies `c1` whole — the salt comes from `SecureRandom.nextBytes`, the
one producer chain of this set that marks a `byte[]` as randomised.

## Reproducing

Both snapshots live under the harness's scratch directory, which its JSON summary names
(`"scratch"`). Compile against the cached rvsec-mop test classpath
(`rvsec/rvsec-mop/target/gh104-classpath.txt`) and run once per side with the snapshot's
`work/classes/classes` directory as the second argument.

```java
String side = args[0];
URL classes = new java.io.File(args[1]).toURI().toURL();
URLClassLoader loader = new URLClassLoader(new URL[]{classes}, Probe.class.getClassLoader());
Class<?> rm = loader.loadClass("mop.MultiSpec_1RuntimeMonitor");

byte[] salt = new byte[16];                     // nothing randomises it
int iterationCount = 1000;                      // and it is below the bound
PBEParameterSpec spec = new PBEParameterSpec(salt, iterationCount);

for (Method m : rm.getDeclaredMethods()) {      // every dispatcher the call resolves to
    if (!m.getName().startsWith("PBEParameterSpecSpec_c")) continue;
    if (m.getParameterCount() != 3) continue;
    m.invoke(null, salt, iterationCount, spec);
}
Class<?> ec = loader.loadClass("br.unb.cic.mop.eh.ErrorCollector");
Object collector = ec.getMethod("instance").invoke(null);
System.out.println(side + " errors="
    + ((java.util.Collection<?>) ec.getMethod("getErrors").invoke(collector)).size());
```
