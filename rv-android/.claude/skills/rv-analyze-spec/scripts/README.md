# The two harnesses

Both drive **production classes**, not re-implementations. That is the whole point: a model of
the generator agrees with whatever you already believed, and a harness over the shipped code
does not. See `../reference/triangulation.md` for why this angle outranks a model.

Run everything from a scratch directory. Never write into the specification tree.

---

## `CoenableProbe` — price a property before generating it

Reports states after minimisation, milliseconds per phase, the coenable set count per
category, the closed-form prediction beside it, and the size of the string rv-monitor will
have to parse. It stops before code generation, so it is roughly four times faster than a full
run and answers the only question that usually matters: *will this generate at all?*

**Compile**

```bash
RVM=$RVSEC_HOME/rv-monitor/target/release/rv-monitor/lib
CP="$RVM/plugins/fsm.jar:$RVM/plugins/ere.jar:$RVM/logicrepository.jar"
javac -nowarn -cp "$CP" -d $S/harness CoenableProbe.java
```

**Run** — the same language in both notations, which is the cheapest way to separate a
property of the language from a property of the notation:

```bash
EV="g1 g2 g3 i1 i2 u1 u2 u3 u4 u5 wkb1 f1 f2 f3 f5 f6 f7"

# body.fsm holds just the state block (and its alias line), copied out of the .mop or .rvm
java -Xss1g -cp "$CP:$S/harness" CoenableProbe fsm body.fsm "$EV" "fail match1"

# body.ere holds a single line: the regular expression
java -Xss1g -cp "$CP:$S/harness" CoenableProbe ere body.ere "$EV" "fail match"
```

The categories are the specification's handler names. Include `fail` — it is the one that
costs, and leaving it out is how a model once concluded "slow but tractable" about something
that could not be built at all.

Expected shape of the output:

```
events            = 17
states_after_min  = 5
enables_ms        = 948
coenables_ms      = 13214
coenable_sets[fail] = 2228207
coenable_sets[match1] = 354
coenable_sets_tot = 2228561
saturated_predict = 2228207
coenable_chars    = 82448990
```

When `coenable_sets[fail]` equals `saturated_predict`, the `fail` category is saturated and
the alphabet is the only thing that will change the cost. Over roughly 17 events the run will
not survive rv-monitor's regex; over roughly 23 the string cannot be built at all.

---

## `PointcutBudget` — find out what a pointcut really matches

Builds a synthetic DEX call site for every member of a real class and runs the production
`PointcutMatcher` against each candidate. Then reports overlaps and unmatched members, because
those are the two things that are easy to miss by eye and expensive to miss in a specification.

**Step 1 — get the real member table.** Never hand-write it.

```bash
python3 api_members.py $ANDROID_HOME/platforms/android-30/android.jar javax.crypto.Cipher \
  --only getInstance init update doFinal wrap getIV unwrap updateAAD > $S/cipher.tsv
```

Keep the neighbours (`unwrap`, `updateAAD`) in the table on purpose: they are how leakage
shows up. Then edit the first column so the tags carry the rule's event names — `i4`, `f2`,
`u3` — and the matrix reads directly against the oracle.

**Step 2 — write the candidates.** One per line, `label <TAB> pointcut`:

```
F1	call(public byte[] Cipher.doFinal())
F24	call(public byte[] Cipher.doFinal(byte[], ..))
F3	call(public int Cipher.doFinal(byte[], int))
F56	call(public int Cipher.doFinal(byte[], int, int, byte[], ..))
F7	call(public int Cipher.doFinal(ByteBuffer, ByteBuffer))
```

Include the *current* pointcuts alongside the proposed ones. Reading the two halves against
each other is what turns the matrix from a design into a diagnosis.

**Step 3 — compile and run.**

```bash
PE=$RVSEC_HOME/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine
cd $RVSEC_HOME && mvn -o -q -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine \
  dependency:build-classpath -Dmdep.outputFile=$S/pe-cp.txt
CP="$PE/target/classes:$(cat $S/pe-cp.txt)"

javac -nowarn -cp "$CP" -d $S/harness PointcutBudget.java
java -cp "$CP:$S/harness" PointcutBudget \
  $ANDROID_HOME/platforms/android-30/android.jar javax.crypto.Cipher \
  $S/cipher.tsv $S/pointcuts.txt
```

If `target/classes` is missing, build the module first with
`mvn -o -pl <module> -am -DskipTests package`. Check `pgrep -af mvn` before building — the
reactor and `~/.m2` are shared.

Output ends with the two checks that matter:

```
OVERLAP  f1   matched by [CURRENT f2, PROP F1]
DISJOINT  no member is matched by two candidates
UNMATCHED [iv]
```

`UNMATCHED` is not automatically a problem — an event the rule declares but the specification
deliberately omits will show up there. It is a problem when the member is one the rule
quantifies over.
