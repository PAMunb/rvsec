# RandomStringPassword — the pass that deletes a bridge for carrying the wrong thing (gh105 task 4.11)

Two reads, two writes, no calls. All four are **deleted**, which reverses the instruction the task
carried — it said to record the reads as `propagation`. What reversed it is a measurement taken
before the edit: the bridge does not carry the predicate it stamps.

This is the second file to leave `predicate_graph.csv` whole (`MacSpec` was the first, task 4.9),
and the two leave for different reasons. `MacSpec`'s reads went because they fed no write. These
feed one; they go because the *write* is unsound.

## What the file is

```java
RandomStringPasswordSpec(String str) {
    event vo after(Object obj) returning(String s):
       call(public static String String.valueOf(Object)) && args(obj) &&
       condition(ExecutionContext.instance().validate(Property.RANDOMIZED, obj)) {
          ExecutionContext.instance().setProperty(Property.RANDOMIZED, s);
    }
    event gb after(String s) returning(char[] chars):
      call(public char[] String.toCharArray()) && target(s) &&
      condition(ExecutionContext.instance().validate(Property.RANDOMIZED, s)) {
         ExecutionContext.instance().setProperty(Property.RANDOMIZED, chars);
    }
    ere : vo gb
    @match { }
}
```

Four facts about it, each checked rather than assumed:

- **It translates no rule.** There is no `RandomStringPassword.cryptsl` in api30; the only rule of
  that family is `SecureRandom.cryptsl`. `spec.md:818` already records that specifications with no
  rule are skipped declaredly by the message gate.
- **It accuses nothing, ever.** Zero `addError`, zero `@fail`, empty `@match`. It is the most
  extreme form of finding 17/29 seen so far — sharper than `GCMParameterSpecSpec`, which at least
  had a `@fail`, unreachable though it was.
- **It is the set's only dataflow bridge**, and it exists for one consumer. `PBEKeySpecSpec.c1`
  reads `randomized` over a `char[]`; every other reader of that predicate takes a `byte[]`
  (`IvParameterSpec.c1/c2`, `PBEParameterSpecSpec` ×2, `GCMParameterSpecSpec` ×2,
  `SecretKeySpecSpec.c1`, `PBEKeySpecSpec`'s salt read, `SecureRandomSpec.setSeed2`), and no
  producer in the set makes a randomised `char[]`. Without the bridge that read can never be
  satisfied.
- **It was byte-identical to the frozen `jca` seed.** Zero hunks in `divergence_record.csv`, zero
  lines in `codes.csv`. This pass writes the file's first four hunks.

## The measurement, taken before the edit (finding 47)

The corpus could not answer. The file's one committed trace passes a `String` literal, whose guard
is false, so no trace had ever exercised the propagation — the harness said `unchanged` without
having run the bridge once. Two traces were written first and the seed measured on the tree the
pass starts from, then the decisions were taken, then the file was touched.

### 1. What `String.valueOf(Object)` actually carries

`String.valueOf(Object)` calls `Object.toString()`. Measured over each of the three source types
the set can put into the bridge — the producers of `RANDOMIZED` are `byte[]`, boxed `int`, and the
`SecureRandom` instance itself (`SecureRandomSpec.@match1`):

| source | `String.valueOf(Object)` returns | carries randomness? |
|---|---|---|
| `byte[]` (`nextBytes`, `generateSeed`) | `[B@726f3b58` — the identity string | **no**: a heap identity hash |
| the `SecureRandom` itself | `SecureRandom` — a constant | **no**: the same text in every program |
| `Integer` (`nextInt`, `nextInt(int)`) | its own digits | **yes** |

### 2. Which of them survives the new store

`PredicateStore` keys a bound object by identity (`BoundKey`, `System.identityHashCode`). An `int`
is boxed at the `ensure` and boxed again at the read, and two boxes of one value are the same
object only inside the `Integer` cache. Measured on the store directly:

```
new store, same array object            -> SATISFIED
new store, equal Integer outside cache  -> NOT_OBSERVED
new store, equal Integer inside cache   -> SATISFIED
new store, equal but distinct String    -> NOT_OBSERVED
old store, equal Integer outside cache  -> true          <- the seed's semantics, by equals()
old store, equal but distinct String    -> true
```

So the one faithful conversion is also the one that dies. And inside the cache, the value
`SecureRandomSpec.next1` marks is the **bound argument** of `nextInt(int)`, not the random result —
a program constant.

**The two source types that propagate carry no randomness, and the one that carries randomness does
not propagate.**

### 3. The chain end to end, three trees, whole `ErrorCollector`

Probe over the real dispatchers, `SecureRandom` → `String.valueOf` → `toCharArray` → `PBEKeySpec`,
one process per tree. The third column runs the migrated bodies inline (`validate` →
`if SATISFIED then ensure`, both on `PredicateStore`) between the tree's own dispatchers, which is
what a faithful migration would have produced:

| configuration | pre-image | tree this pass starts from | faithful migration |
|---|---|---|---|
| `byte[]` route → `PBEKeySpec` | **0 — silent** | 1 — `PBEKEYSPEC-NOBS-00` | **0 — silent again** |
| `Integer` route, value outside the cache | 0 | 1 | 1 |
| `Integer` route, value inside the cache | 0 | 1 | 0 |
| control: hardcoded password | 0 | 1 | 1 |

Row 1 of the pre-image column is the finding. A `PBEKeySpec` whose password is the `char[]` of
`[B@6ae40994` — eleven characters of heap address — is accepted as randomised and draws nothing.
That is a false **negative**, it is live in the frozen seed, and a faithful migration restores it
on the new substrate.

### 4. Does the guard suppress anything visible?

No, and this is what separates the pass from 4.7/4.8/4.9. Read in the generated monitor rather than
inferred: the monitor class has `Prop_1_handler_match` and nothing else — there is no `@fail`
handler at all — and the handler's body is empty. State 3 is a sink no handler names. Measured on
the committed trace, where both guards are false: **0 reports**. So unlike `MacSpec` (finding 33) a
suppressed transition here cannot become an ordering accusation, and unlike `CipherSpec`
(finding 32) it cannot turn a conforming program into an accused one. The guard's only effect was
the write it gated.

## The decisions

### 1. All four sites are deleted, not migrated (researcher, 2026-08-21)

The reads translate no clause, so their whole justification was that they govern the writes; the
writes translate no clause, so their whole justification was that they feed `PBEKeySpecSpec.c1`.
The measurement removes the second: the write does not carry the predicate across. Recording the
pair as `propagation` would enter into `predicate_graph.csv` a claim the conversion does not
support.

`spec.md`'s propagation rule was amended in the same pass rather than bent around this file. It
said a read that translates no clause is propagation if it **feeds a write**; it now says the write
must also **carry the predicate across**, which leaves `SecretKeySpec.e1` as the only site meeting
both — `SecretKey.getEncoded()` returns the key's own bytes, so `RANDOMIZED` on the key really is
`RANDOMIZED` on what it returns.

What the deletion costs, stated plainly rather than minimised: `PBEKeySpecSpec.c1`'s password read
can now never be satisfied, so every four-argument `PBEKeySpec` construction draws
`PBEKEYSPEC-NOBS-00`. Three things bound that cost, and the first two are measurements:

- **Relative to the tree, nothing changes.** The bridge is already inert here — its reads sit on
  the old substrate while its producers moved at task 4.5 — so the accusation already fires on
  every construction (column 2 above, all four rows identical).
- **Relative to the faithful migration, only the `byte[]` row differs.** Compare columns 3 and 2:
  the migration would have recovered the false negative and nothing else, because the honest
  `Integer` route dies on the new store either way.
- **The accusation stands behind no clause.** api30 `PBEKeySpec.cryptsl` REQUIRES `randomized[salt]`
  and says nothing about the password; its clause about the password is
  `neverTypeOf(password, java.lang.String)`, which is not what `PBEKEYSPEC-CONSTR-01` tests. That
  is the standing allow-list finding against `err2`, recorded in `divergence_record.csv` against
  `PBEKeySpecSpec.mop`, where it lives. It is not repaired from here.

The third option — repairing the bridge with a type gate on the write (`obj instanceof Number ||
obj instanceof CharSequence`) — was declined. It kills both false negatives and preserves the
`Integer` route, but it invents a condition no rule states, inside a substrate migration
(decision 7), to feed a read that has no clause behind it either.

### 2. The empty `@match` stays — the option the grammar killed

Tasks 4.6 and 4.9 deleted `@match` handlers whose bodies had emptied. Here the handler is empty to
begin with, so deleting it looked like the same move. It is not available: measured, the JavaMOP
grammar requires at least one handler after the `ere`.

```
javamop.parser.main_parser.ParseException: Encountered "<EOF>" at line 27, column 1.
Was expecting:  "@" ...
    at javamop.parser.main_parser.RVParser.propertyHandler(RVParser.java:379)
✗ Monitor generation failed                                      (exit 1)
```

An empty handler is the only legal way to state an automaton with nothing to report.

### 3. And one that was not a decision: the two events stay

Deleting them would make the two calls **unmodelled** rather than unmarked, which is the opposite
of what the file records. Same disposition as `CipherSpec.wkb1` (task 4.1) and
`SecureRandomSpec.ints` (task 4.5).

## The harness repair this pass carried

The `Integer` trace was unreplayable when it was written. `TraceRunner.fitsPointcut` refused an
`Integer` against **every** declared reference type, so `String.valueOf(n) -> s` resolved to
nothing and the outcome read *not accused* where the truth was *not replayed* — the one reading
the class's own documentation says a differential harness must never make silently.

The rule's stated justification is separating `KeyPairGenerator.initialize(int)` from
`initialize(AlgorithmParameterSpec)`, and the assignability test on the line below it already
decides that: `AlgorithmParameterSpec` is not assignable from `Integer`. The blanket rule therefore
changed an outcome only where the declared type genuinely accepts an `Integer` — `Object`,
`Number`, `Integer`, `Comparable`, `Serializable`. Measured over the whole set: of the **112**
advices, **exactly one** pointcut declares such a type, `RandomStringPasswordSpec.vo`'s
`String.valueOf(Object)` — the one it blocked. (Two `Object+` pointcuts exist and leave earlier, by
the `endsWith("+")` branch.)

Measured inert before removal: **0 outcome changes over the 92 committed traces on both snapshots**
of the differential comparison, and `KeyPairGeneratorSpec-rsa3072.txt` — the docstring's own case —
still resolves to `initError` and not to `init3`/`init4`. A test pins both directions
(`anIntegerFitsAPointcutDeclaringObjectAndNotOneDeclaringAnUnrelatedType`); it fails against HEAD's
guard and passes with the repair.

Two `TraceRunnerTest` failures were already red at HEAD and are untouched by this pass, verified by
replaying the 92-trace corpus with HEAD's `TraceRunner` against the frozen control: the same eight
unresolved lines (`s.sign()` ×5, `ctx.createSSLEngine()`, `tmf.getTrustManagers()`, and
`KeyPairGeneratorSpec-sticky-fail`'s two NPEs), and `TrustManagerFactorySpec.txt` unaccused. They
belong to the return-type gate of `bdc027a6` and to gh104's 8.5, not here.

## What the harness measured

94 traces (the 92 committed plus the two this pass wrote), `--a backup/gh105-preimage/jca_android`,
cumulative against the pre-image:

| | before this task | after |
|---|---|---|
| unchanged | 61 | **61** |
| moved | 18 | 18 |
| introduced | 7 | **9** |
| removed | 6 | 6 |

| trace | A accuses | B accuses | class |
|---|---|---|---|
| `RandomStringPasswordSpec.txt` | — | — | unchanged |
| `RandomStringPasswordSpec-bytes-route.txt` | — | `c1` `PBEKEYSPEC-NOBS-00` | **introduced** |
| `RandomStringPasswordSpec-int-route.txt` | — | `c1` `PBEKEYSPEC-NOBS-00` | **introduced** |

**Every other specification's report is byte-identical** — the only file under
`data/gh105/evidence/harness/` that `git diff` touches is this one. That is the sharpest form of
"the deletion moved nothing else".

The two `introduced` rows are the two halves of the finding, and they are not the same kind of
thing. The `byte[]` row is a false negative removed: the pre-image accepted a heap-address password
and the migrated set does not. The `Integer` row is an honest program that the pre-image accepted
and the migrated set accuses — a cost, and one the faithful migration would have paid too, because
that route dies on the identity-keyed store regardless. Both are deliberate and both are recorded.
`introduced` reaches 9.

## Gate state after the task

| gate | before | after |
|---|---|---|
| G-PRED2 | 23 | 23 |
| INV-INS-130 | 15 | **14** |
| INV-INS-133 | 3 | **1** |
| INV-INS-134 | 22 | **20** |
| **total structural findings** | **63** | **58** |

Five findings repaired in one pass, the most of any Group 4 file, and all five are the same four
sites seen by four different gates. `gh105_gate_baseline.py` reports no finding outside the
recorded baseline; the baseline was rewritten and its `retired` block (G-ACC, 17) preserved.
G-ORDER is unchanged — the same four known divergences, this file still absent from
`order_alphabet_map.csv` and skipped in both directions. `gh104_mop_lint.py` is green over the 23
files and `gh104_message_gate.py` is `ok` with its one standing informative.
`gh104_divergence_record.py --check`: **206** hunks, all recorded — four new rows for this file,
its first, and no stale row to retire, because the file had none.

Censuses. The set's own: reads 16 → **14**, guard reads 3 → **1**, writes 36 → **34**;
accepting-state calls stay 17 and removals stay 8, because the `@match` stays. The graph: 77 rows →
**73**, `read:condition-guard` 3 → **1**, `write:body` 25 → **23**, everything else held. The
placement gate: `len(guards)` 3 → **1**, and the one left is `SecretKeySpec.e1`, which task 4.12
moves.

`codes.csv` is untouched: the file had no line in it and gains none, because a site with no accuser
never earns one.

## Reproducing

```bash
cd .../rvsec/rv-android
export RVSEC_HOME=.../rvsec; SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)

# there is no rule: this is the check, not an assumption
ls .../MetaCrySL/generated/api30/ | grep -i randomstring     # empty
cat .../MetaCrySL/generated/api30/PBEKeySpec.cryptsl          # REQUIRES randomized[salt] only

# the three conversions and the two stores (RspProbe: parts A and C)
javac -nowarn -cp "$CP" -d <dir> RspProbe.java
java -cp "<dir>:<scratch>/b/work/classes/classes:$CP" RspProbe starting-tree

# the same chain with the migrated bodies simulated, before the edit exists (RspPostProbe)
java -cp "<dir>:<scratch>/b/work/classes/classes:$CP" RspPostProbe starting-tree

# the pre-image side, which is where the false negative is live
java -cp "<dir>:<scratch>/a/work/classes/classes:$CP" RspProbe PRE-IMAGE

# no @fail handler, and the empty @match: read the monitor, do not infer it
grep -n "Prop_1_handler" <scratch>/b/monitors/MultiSpec_1RuntimeMonitor.java | grep RandomString -A2

# the grammar killing the @match deletion
cp -r $SPECS/jca_android <dir>/specs && <remove the @match block>
uv run rv-monitor-generator generate --specs-dir <dir>/specs --output <dir>/out   # exit 1

# the harness guard, measured inert before removal
git show HEAD:rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java > <dir>/TraceRunner.java
javac -nowarn -cp "$TC:$CP" -d <dir>/classes <dir>/TraceRunner.java
java -cp "<dir>/classes:$TC:$CP" br.unb.cic.mop.harness.TraceRunner <side>/monitors data/gh104/traces <work> <out>
# diff that against the same run without <dir>/classes on the path: 0 differences, both sides
```

**Write the traces before the edit.** This pass could state what the pre-image does, what the tree
does, and what the migration would have done, because all three were measured while all three were
still reachable. After the edit, the third column is unobtainable.
