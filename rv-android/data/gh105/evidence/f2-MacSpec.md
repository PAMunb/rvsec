# MacSpec — the pass that leaves a file naming no predicate at all (gh105 task 4.9)

Two reads, two writes, one withdrawal and one bookkeeping handler went in. Nothing came out.
`MacSpec.mop` is the first file of the migration to leave `predicate_graph.csv` **entirely** —
the set's rows go 84 to 78 — and the first whose INV-INS-130 count reaches zero by subtraction
rather than by substitution. A reader who looks only at the placement census will see a task that
appears to have done nothing: no read moved to a body, no write moved to an acceptance point.
What it actually did is delete four sites that translate no clause of the rule, and in doing so
remove a false positive the file had been emitting for every program that used a key the
instrumentation never saw generated.

That last part is why the deletion is a repair rather than housekeeping, and it is the finding
this pass contributes: **a guard can invent an accusation, not only suppress one.**

## What the rule says, and where each site landed

api30 `Mac.cryptsl`:

```
ORDER        Gets, Inits, (Finals | (Updates+, Finals))                    :67
CONSTRAINTS  macAlg in {…12 values…}; offset < len;
             length(output1) > outOffset;                                  :71-75
REQUIRES     preparedHMAC[params];                                         :80
             !encrypted[output1, _];  !encrypted[output2, _];              :82-84
ENSURES      macced[output1, inp]; macced[output1, pre_input];
             macced[output2, input];                                       :89-93
```

`generatedKey` appears **nowhere** in the rule — not in REQUIRES, not in CONSTRAINTS.

| site | before | after | why |
|---|---|---|---|
| `i1` read of `generatedKey[key]` | `read:condition-guard` | **deleted** | translates no clause, feeds no write |
| `i2` read of `generatedKey[key]` | `read:condition-guard` | **deleted** | same |
| `f1` write of the one-place generated-MAC property | `write:body` | **deleted** | translates no clause; the rule's `macced` is two-place |
| `f2` write, same property | `write:body` | **deleted** | same |
| `@fail` withdrawal of that property | `remove:fail` | **deleted** | travels with the writes it undid (criterion of task 4.6) |
| `@match` accepting-state bookkeeping | `bookkeeping:match` | **deleted** | INV-INS-147; the handler had no other body |
| the `Mac mac` field | monitor field | **deleted** | the handler was its only reader |

The rule's three real REQUIRES arrive at this same file at tasks **5.2** (`preparedHMAC[params]`,
ledger #21) and **5.3** (the two `!encrypted`, ledger #22/#23), and its ENSURES at **5.7**
(ledger #8, the Cipher consumer `!macced[_, plainText]`).

## The corpus had none of the interesting configurations

Of the corpus's traces, three named this file before this pass — `MacSpec.txt` (a legitimate
HmacSHA256 over a generated key), `MacSpec-hmacpbesha1.txt` (a narrowed algorithm) and
`MacSpec-guard-on-field.txt` (a gh104 case about the message, not about the predicate). None of
them combines an algorithm judgement with a key origin, which is the whole of what the deleted
guard governed. Two traces were written before any measurement was taken (finding 18):

- `data/gh104/traces/MacSpec-unsafe-generated-key.txt` — `HmacPBESHA1` initialised with a key
  `KeyGenerator` produced. The only configuration in which the pre-image can report the unsafe
  algorithm at all.
- `data/gh104/traces/MacSpec-ungenerated-key.txt` — `HmacSHA256` initialised with a key bound
  silently (`bind key = new SecretKeySpec(...)`, learning 40, so no second specification's reports
  land in this one's envelope). A program that breaks **no clause** of the Mac rule.

## The three decisions, and what measured each one

### 1. The two `GENERATED_MAC` writes are deleted, and the `@fail` withdrawal goes with them

Two independent readings say the property translates nothing:

- **It is written and never read.** `grep -rn` over the five specification sets finds the write in
  three of them (`jca`, `jca_android`, `jca_android_bug_predicate`) and a read in **none**. The
  reproved set is among the hits and is named here as a *register*, never as a seed: it reads a
  different property, `MACED`, and its `CipherSpec.mop:98` says why in one line — *"MACED is the
  second place of CrySL's two-place macced[M, D]; GENERATED_MAC holds the …"*. That comment is the
  most informative documentation of this defect that exists anywhere in the tree, and it closed
  the decision. It was read, not copied.
- **The arity does not match the clause.** api30 states `macced[output1, inp]`,
  `macced[output1, pre_input]` and `macced[output2, input]` — two places, the tag and the data it
  authenticates. A one-place property over the tag alone cannot answer the only consumer there is,
  Cipher's `!macced[_, plainText]` (ledger #8), which asks about the *data*.

Chosen (researcher, 2026-08-21): **delete**. The real producer is ledger #8 at task **5.7**, which
writes at the acceptance point with the arity the clause states; migrating this write would have
given that one edge a **second** producer at an arity that cannot answer it. Precedents for
deleting rather than recording a clause-less write: `WRAPPED_KEY` (task 4.1) and the `ints` write
(task 4.5). The `remove()` in `@fail` travels with the write it undoes, by the criterion task 4.6
used for the `clearPassword` withdrawal — so task **6.4 performs seven** of INV-INS-142's eight,
and the invariant records the attribution rather than lowering its count (researcher, 2026-08-21;
see "The fourth decision" below).

### 2. The two `generatedKey` reads are deleted, not recorded as propagation

`tasks.md` called them *propagation* and instructed that they be recorded as such in the graph.
The measurement disagrees with the label, and the task text was corrected before the code was
touched.

Propagation is reading a predicate **and writing another**. `RandomStringPassword.vo` establishes
`RANDOMIZED` on the string it returns, `gb` on the char array, `SecretKeySpec.e1` on the key bytes
— each verdict travels. `MacSpec.i1`/`i2` write nothing: they compute a verdict and discard it.
Deleting them and moving them to a body without an accuser are **behaviourally the same program**;
what separates the two is dead code and two rows in `predicate_graph.csv`.

Chosen (researcher, 2026-08-21): **delete**, and the contract gains the criterion that separates
the two dispositions — a read that translates no clause **and feeds no write** is deleted; one that
feeds a write is recorded as `propagation` (`specs/instrumentation/spec.md`, the propagation-read
paragraph). The Mac rule's real REQUIRES reach this same event at tasks 5.2 and 5.3.

### 3. The `@match` handler and the `mac` field are deleted whole

The handler's entire body was the accepting-state bookkeeping call INV-INS-147 retires across the
set, and the field existed only to give that call an object. With the call gone the handler has no
body, and this file has no acceptance-point write to put in one. Task 5.7 recreates a handler when
it has the rule's ENSURES to write — at arity two over the tag and the data, not over the `Mac` —
so the field is not what that task needs either. Precedent: the `@match` deletion at task 4.6.

### The fourth decision: INV-INS-142 keeps its count and gains an attribution

The resumption prompt directed that "The eight `@fail` removals" become seven. Read against the
invariant, that weakens the contract: all eight still have to go, and if the invariant says seven,
**no invariant requires `MacSpec.mop:99` to be deleted** — the only artefact naming it would be a
task checkbox, which is not a contract. That is the failure mode of finding 25 and the reason
commit `946aad17` put its record in two artefacts.

Chosen (researcher, 2026-08-21): the invariant keeps **eight** and gains a sentence attributing one
of them to task 4.9 by the precedent of 4.6; `tasks.md` 6.4 goes to seven with its site list
**re-read from the tree**, which turned up a second staleness: Group 3 moved
`TrustManagerFactorySpec.mop:100,101` to `:124,125` and `KeyPairGeneratorSpec.mop:119` to `:133`.

### The fifth: the introduced accusation is recorded with the `g3*` finding, not repaired

See "Two findings about the automaton" below. Chosen (researcher, 2026-08-21): both belong to the
family the `CipherSpec` `unsafeAlg` sink opened (finding 1) and the `GCMParameterSpecSpec`
unreachable `@fail` continued (finding 21); they are recorded here and named as candidates for the
task finding 21 already asks for, without opening a 7.x artefact in the middle of Group 4.

## What the harness measured

91 traces, `--a backup/gh105-preimage/jca_android`, cumulative against the pre-image:

| | before this task | after |
|---|---|---|
| unchanged | 62 | **59** |
| moved | 17 | **18** |
| introduced | 7 | **8** |
| removed | 5 | **6** |

Every one of the three that changed class is a `MacSpec` trace, and each is a different thing:

| trace | A accuses | B accuses | class | what it is |
|---|---|---|---|---|
| `MacSpec.txt` | — | — | unchanged | the conforming program, silent on both sides |
| `MacSpec-ungenerated-key.txt` | `MAC-ORDER-00` @f1 | — | **removed** | the false positive of finding 32 |
| `MacSpec-hmacpbesha1.txt` | @f1 | @i1, @f1 | **moved** | the narrowed algorithm becomes accusable |
| `MacSpec-unsafe-generated-key.txt` | @i1, @f1 | @i1, @f1 | unchanged | the one configuration the pre-image could already accuse |
| `MacSpec-guard-on-field.txt` | — | @i1 | **introduced** | `Mac.init` observed, `Mac.getInstance` not |

The verdict is a **floor**, not a count (learning 3): on `-unsafe-generated-key` the harness shows
two accusing events where the collector holds three reports, because `TraceRunner.envelope()`
returns the first error of the `Set` per dispatcher call and this file emits the body report and
the transition report from the same call.

## Counting the whole `ErrorCollector`

Five configurations, both sides, one process per side, `reset()` between configurations
(learning 38). The prediction carried in the resumption prompt is beside the measurement:

| configuration | A | B predicted | B measured |
|---|---|---|---|
| 1. safe algorithm + generated key | 0 | 0 | **0** |
| 2. safe algorithm + **ungenerated key** | 1 — `MAC-ORDER-00` @f1 | 0 | **0** |
| 3. **unsafe algorithm** + generated key | 3 — ORDER @i1, **ALG-00 @i1**, ORDER @f1 | 3 | **3**, identical |
| 4. **unsafe algorithm + ungenerated key** | 1 — `MAC-ORDER-00` @f1 | 2 | **3** |
| 5. safe algorithm, `getInstance` unobserved | 1 — `MAC-ORDER-00` @f1 | — | **2** |

Rows 1 to 3 land exactly where the prediction put them. **Row 4 is off by one, and the prediction
is what was wrong**: it counted one `MAC-ORDER-00` where the program draws two, at `i1` and at
`f1`. The measured value is the coherent one — with the guard gone, the key origin decides nothing,
so **rows 3 and 4 of the B side must be identical, and they are**. That identity is the cleanest
statement of what this task did.

Row 5 is the configuration the prediction did not cover; it is discussed below.

The probe is audited (learning 27). On the B side a sibling site — `PBEParameterSpec(plain salt,
1000)`, migrated at task 4.7 — draws **2** reports in the same class loader, so a zero measured
there is a zero and not a probe that missed. On the A side that control is silent, because 4.7 has
not landed on the pre-image; the A side audits itself instead, since four of its five rows are
non-zero. The loader declares exactly the eight `MacSpec_*` dispatchers the file has events for.

## Two findings about the automaton, recorded and not repaired

Both are the shape finding 1 named: an **ordering accusation standing in for something that is not
ordering**. Neither is task 4.9's to fix — the repair is to the automaton, this pass moves no
symbol, and `MacSpec` is one of the thirteen files still absent from `order_alphabet_map.csv`, so
G-ORDER skips it in both directions (task 7.1 owns that).

**The `g3*` that leads nowhere.** `ere : (g3* g1 | g3* g2) (i1 | i2) …`. `g3` is the
unsafe-algorithm `getInstance`, and `g3*` must be followed by a **safe** `g1` or `g2`. A program
that only ever asks for an unsafe algorithm never leaves the prefix, so **every** such run ends in
`MAC-ORDER-00` whatever else it does correctly — visible in probe rows 3 and 4, where the ordering
report at `f1` accompanies the real accusation. Third member of the family after the `CipherSpec`
`unsafeAlg` sink (finding 1) and the `GCMParameterSpecSpec` unreachable `@fail` (finding 21).

**The unobserved prefix.** Probe row 5 and the `-guard-on-field` trace: `Mac.init` is observed and
`Mac.getInstance` is not, so the ORDER's `Gets` never happens and `Inits` arrives in the initial
state. The pre-image was silent on this program **by accident** — the key-origin guard suppressed
the transition before the automaton could judge it — and deleting the guard lets the automaton say
what it means. This is not an orphan accuser: `MacSpec.i1` is named by the `ere`, is absent from the
ledger of the seventeen, and draws no G-ACC finding. It is the reach limit of the instrumentation
arriving at an event that judges prefixes.

**This is finding 32's mirror, and the pair is the general statement**: a guard that decides an
automaton transition can *invent* an accusation (row 2 of the A side: a program that breaks no
clause of the rule, accused of `InvalidSequenceOfMethodCalls`) and can *mask* one (row 5: an
accusation the automaton would otherwise make). Both are wrong for the same reason, and neither is
visible in a placement census.

## Gate state after the task

| gate | before | after |
|---|---|---|
| G-PRED2 | 25 | **23** |
| INV-INS-130 | 17 | **16** |
| INV-INS-133 | 5 | **3** |
| INV-INS-134 | 24 | **22** |
| **total structural findings** | **71** | **64** |

`gh105_gate_baseline.py` reports seven `repaired` and **no finding outside the recorded baseline**;
the baseline was rewritten and its `retired` block (G-ACC, 17) is preserved. G-ORDER is unchanged:
the same four known divergences, `MacSpec` still skipped. `gh104_mop_lint.py` and
`gh104_message_gate.py` are green over the 23 files. `gh104_divergence_record.py --check`: 199
hunks, all recorded — 16 new rows for this file and 6 stale ones retired, their reasons absorbed.

Censuses: the set goes 18 reads to **16** (3 still guards), 38 writes to **36**, 19 accepting-state
calls to **18**, 9 removals to **8**; the graph goes 84 rows to **78**, the only file so far to
leave it entirely.

## Noticed and not repaired

`String currentAlgorithmInstance` is assigned by all three `getInstance` events and read by
**nothing** — here and in the frozen seed alike. It is not a predicate site, so it is outside this
pass, which owns the file's predicate machinery; deleting it is a separate repair and is recorded
rather than made. It is left with a comment saying so, beside the comment explaining why the
`Mac mac` field next to it *was* deleted (that one had a reader, and the reader left).

## Reproducing

```bash
cd .../rvsec/rv-android
export RVSEC_HOME=.../rvsec; SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# the rule
sed -n '60,95p' .../MetaCrySL/generated/api30/Mac.cryptsl

# written in three sets, read in none
grep -rn "GENERATED_MAC" --include=*.mop $SPECS

# the harness (~13 min; the JSON summary, scratch path included, is at the TOP of stdout)
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py --a backup/gh105-preimage/jca_android \
    --b $SPECS/jca_android --traces data/gh104/traces --out data/gh105/evidence/harness --group f2

# the probe: every configuration over the whole ErrorCollector, one process per side
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
javac -nowarn -cp "$CP" -d <dir> MacProbe.java
for side in a b; do java -cp "<dir>:<scratch>/$side/work/classes/classes:$CP" MacProbe $side; done
```

The probe's shape, which is what matters if it has to be rewritten: resolve
`mop.MultiSpec_1RuntimeMonitor` by name, call the dispatchers by `(name, parameter count)`, use a
**real** `Mac.getInstance("HmacPBESHA1")` for the unsafe rows — since gh104 task 8.16 the guard
reads `m.getAlgorithm()` on the bound object, not the monitor field, so passing an unsafe *string*
with a safe object measures nothing — establish `generatedKey` through
`KeyGeneratorSpec_g1Event`/`gk1Event` for the generated-key rows, and read the envelope from
`ErrorDescription.getExpecting()` (learning 39), resetting the collector between configurations.
