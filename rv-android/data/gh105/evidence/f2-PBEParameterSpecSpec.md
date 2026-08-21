# PBEParameterSpecSpec — the pass that made a silent overload speak (gh105 task 4.7)

Two reads, one write, one handler. It is the first file pass since task 4.1 to take a predicate
read out of `condition(...)` because the migration asked it to, and the last of this chain: with
it, the F2 window that task 4.5 opened on `PBEParameterSpecSpec-randomised.txt` closes, and ledger
clause **#25** is wired end to end — the second edge in two tasks that a Group-4 file pass finishes
on behalf of Group 5.

What the pass found on the way is bigger than the read it was sent to move. The three-argument
constructor — api30's `c2`, a full alternative of the rule's `ORDER` — **accused nothing at all**,
in every configuration, and the reason was the guard this task removes.

## What the rule says, and where each site landed

api30 `PBEParameterSpec.cryptsl`:

```
EVENTS      c1: PBEParameterSpec(salt, iterationCount);              :15
            c2: PBEParameterSpec(salt, iterationCount, paramSpec);   :17
            Cons := c1 | c2;                                         :19
ORDER       Cons                                                     :23
CONSTRAINTS iterationCount >= 10000;                                 :27
REQUIRES    randomized[salt];                                        :32
ENSURES     preparedPBE[this];                                       :37
```

| site | before | after | placed by |
|---|---|---|---|
| `c1` read of `randomized[salt]` | `read:body`, boolean, composite report | `read:body`, three-valued, one report per clause | task 3.6 |
| `c2` read of `randomized[salt]` | `read:condition-guard`, boolean | `read:body`, three-valued, **with the accuser it never had** | this task |
| `@match` write of `preparedPBE` | `write:acceptance`, old substrate | `write:acceptance`, new store, omission recorded | the seed |
| `@match` bookkeeping | `bookkeeping:match` | deleted | INV-INS-147 |

Six codes where there were two. A code names a **site**, not a clause (task 4.4): each event
carries a count report, a *violated* report and a *not observed* report of its own.

## The three decisions, and what measured each one

### 1. The composite report of `c1` decomposes per clause

Task 3.6's fusion wrote one report over `iterationCount < 10000 || !randomized(salt)` — the two
halves being clauses of two different sections of the rule. INV-INS-133 admits a composite site
only for probes of **one** clause (`CipherSpec.i2`'s key-origin trichotomy is the live case), and
with both halves broken there was no consistent code to file the report under: the message named
both and the reader could not tell which had failed. Chosen (researcher, 2026-08-21): **decompose**,
in the shape task 4.6 gave the sibling `PBEKeySpecSpec`, whose rule states the same two clauses.

Measured delta: one construction of the corpus changes count, `PBEParameterSpecSpec-lowiter.txt`,
from one report to two (see the count table below). Nothing else moves.

### 2. `c2`'s guard leaves whole — the CONSTRAINTS check with the read

The read leaves by mandate. The iteration-count check beside it did not have to: INV-INS-133 says
in as many words that `CONSTRAINTS` checks remain legitimate guard uses. It left anyway, and what
decided it was the artefact.

`c2` carried, until this pass, **the guard `c1` carried before the fusion — the same conjunction,
character for character**. Task 3.6 already ruled on that guard for `c1`; `c2` kept it only because
it had no negated twin to accuse in its place. In the generated monitor of the pre-change side:

```java
final boolean Prop_1_event_c2(byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec, PBEParameterSpec s) {
    if ( ! (iterationCount >= 10000 && <read>) ) {
        return false;                       // <- ahead of handleEvent
    }
    { spec = s; }
    int nextstate = this.handleEvent(1, Prop_1_transition_c2);
```

against `c1`, which runs its body and transitions unconditionally. So a three-argument construction
that broke either clause took no transition, reached no accepting state, and was accused of nothing.

That silence is measured, not argued. Three traces were written for this pass — a plain salt, a
count of 1000, and a randomised salt at the bound — and on the seed **all three produce zero
reports**. The corpus had no trace of the three-argument constructor at all: 0 of 82.

Chosen (researcher, 2026-08-21): **mirror `c1`.** The alternative — keeping the count as a guard —
was declined for two measured reasons. It would leave the read this pass takes out of the guard
sitting behind a second guard that suppresses the same transition, so the read would still not run
on a low-count construction; and it would leave the file accusing `PBEParameterSpec(bytes, 1000)`
while staying silent about `PBEParameterSpec(bytes, 1000, params)`, the identical defect under the
same CONSTRAINTS clause. On the 82-trace corpus the two options are indistinguishable; the trace
that separates them is `PBEParameterSpecSpec-threearg-lowiter.txt`, written here, and it separates
them by one report against zero.

A third option was considered and recorded rather than taken: pull the count out of the guard but
let it govern only the write, without a report. It makes the read reachable without adding an
accusation, at the cost of a file that evaluates a CONSTRAINTS clause and discards it in silence at
one event while accusing it at the other.

### 3. `preparedPBE` carries its deliberate-omission record here

Measured in the oracle: **`preparedPBE` appears exactly once in the whole api30 rule set** — as
this rule's own `ENSURES`. No rule requires it, so it is one of the nine `ENSURES`-only dead ends,
and INV-INS-137 asks for a recorded omission rather than a fabricated reader (a read invented on a
producer alone accuses every conforming use of a consumer nobody models). Measured in the sets:
`PREPARED_PBE` is written in three of the five (`jca`, `jca_android`, and the reproved
`jca_android_bug_predicate`, which a `grep` over the five sets hits and which is a record, never a
seed) and **read in none**.

Chosen (researcher, 2026-08-21): **here, in the F2 pass**, which is where the design already routes
the eleven dead-end sites. It closes one of the 26 G-PRED2 findings now, and it is the **first
`disposition` any of the graph's 86 rows has ever carried** — the precedent tasks 4.13 and 4.14
inherit for the other ten sites.

The write itself does not move, and the reason is worth stating beside task 4.6's opposite answer:
api30 states `preparedPBE[this]` with **no `after L` qualification**, so its acceptance point is the
accepting state itself, which in an `ere` is exactly what `@match` names. The sibling `PBEKeySpec`
clause says `after c1` — a state an `ere` has no way to address — which is why that write stayed in
a body with a recorded reason and this one does not have to. The monitor field stays for the same
reason task 4.6 deleted its own: a handler sees no event arguments, so the field is how the object
reaches the write, and it is bound only by the conforming branch of either constructor, which makes
`ensure` a no-op for a construction that broke a clause.

## What the harness measured

Cumulative against the pre-image over the 85-trace corpus: **60 unchanged, 17 moved, 3 introduced,
5 removed** (82 traces and 58/17/2/5 before this task added three).

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `PBEParameterSpecSpec.txt` | `c3` ORDER-00 | `c1` NOBS-00 | moved |
| `PBEParameterSpecSpec-lowiter.txt` | `c3` ORDER-00 | `c1` NOBS-00 | moved |
| `PBEParameterSpecSpec-randomised.txt` | — | — | **unchanged** (was `introduced`) |
| `PBEParameterSpecSpec-threearg.txt` | — | `c2` NOBS-01 | **introduced** |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | — | `c2` CONSTR-02 | **introduced** |
| `PBEParameterSpecSpec-threearg-randomised.txt` | — | — | unchanged |

Two rows to read closely.

**`-randomised.txt` leaves `introduced`.** It was one of the two live F2 windows: task 4.5 moved
`SecureRandomSpec.next2` to the new store and this file still read the old one, so the migrated side
accused the salt on a trace that randomises it. It closes here, and unlike task 4.6's window
(finding 16), this one *was* visible in the class column, because the file had nothing else to
accuse on that trace. **The one live window left is `SecretKeySpecSpec`, which closes at task 4.10.**

**The two `introduced` rows are the repair, not a regression.** They are the accusation the guard
suppressed: a three-argument construction with an unrandomised salt, and one below the iteration
bound. INV-INS-144's F2-window rule expects `NOT_OBSERVED` on a read whose producer has not landed;
here the producer *has* landed, so the pair is a real satisfy/violate pair rather than a window one.

## Counting the whole `ErrorCollector`

The harness records one envelope per dispatcher call, which is a floor wherever a call accuses more
than once. Counting the collector instead, over three snapshots — the seed, the tree before this
task, and the tree after it:

| construction | seed | before 4.7 | after 4.7 |
|---|---|---|---|
| 2-arg, plain salt, 10000 | 2 — CONSTR-00 at `c3`, ORDER-00 | 1 — CONSTR-00 | 1 — NOBS-00 |
| 2-arg, plain salt, 1000 | 2 — CONSTR-00, ORDER-00 | 1 — CONSTR-00 | **2 — CONSTR-00, NOBS-00** |
| 2-arg, randomised salt, 10000 | 0 | **1 — CONSTR-00** | **0** |
| 3-arg, plain salt, 10000 | **0** | **0** | 1 — NOBS-01 |
| 3-arg, randomised salt, 1000 | **0** | **0** | 1 — CONSTR-02 |
| 3-arg, randomised salt, 10000 | 0 | 0 | 0 |

Row 2 is decision 1: the composite becomes two reports, one per clause. Row 3 is the F2 window in
the raw — a randomised salt accused before this task and silent after, because producer and consumer
now speak to the same store. Rows 4 and 5 are decision 2: the seed and the pre-4.7 tree are silent
on every three-argument defect, and the middle column proves the silence was the guard's and not the
substrate's. Row 5 is the trace that separates the two dispositions the guard could receive.

The probe calls **every** `PBEParameterSpecSpec_*Event` of the right arity, which on the seed side is
two dispatchers for the two-argument constructor (`c1` and the twin `c3`) and one for the
three-argument one. A probe that called only the survivor would have measured 0 on the seed's
two-argument rows and reported a delta that is not there.

Reproducing (compile against `rvsec/rvsec-mop/target/gh104-classpath.txt`, run once per side with
that side's `work/classes/classes` from the harness scratch the JSON summary names):

```java
// every dispatcher the construction resolves to on this side
for (Method m : rm.getDeclaredMethods()) {
    if (!m.getName().startsWith("PBEParameterSpecSpec_")) continue;
    if (m.getParameterCount() != arity) continue;      // 3 for c1/c3, 4 for c2
    m.invoke(null, arguments);
}
// randomising the salt first, when the row asks for it:
call("SecureRandomSpec_g1Event", 2).invoke(null, "SHA1PRNG", r);
r.nextBytes(salt);
call("SecureRandomSpec_next2Event", 2).invoke(null, r, salt);
```

## The clause this pass finished, and who owns the consequence

Ledger **#25** (`PBEParameterSpec randomized[salt]`) is dispositioned *wire* at task **5.4**. It is
wired now: the producer is `SecureRandomSpec.next2` writing `RANDOMIZED` at `@match2` (task 4.5),
the consumer is `c1` and `c2` reading it in their bodies with accusers and codes (this task), and
the third row of the count table is the satisfying half measured rather than argued.

This is the **third** edge a pair of file passes has closed on Group 5's behalf — #12 for task 5.1
(tasks 4.4 + 4.5), #24 for task 5.4 (tasks 4.5 + 4.6), and now #25, also task 5.4's. The consequence
is the same one, and task 5.4 now carries it twice: **the design routes each clause to exactly one
accuser**, so 5.4 must not add a second accuser for either #24 or #25. Both are wired by mechanism A;
5.4 either records that and moves on, or re-routes and takes the accusers out of the event bodies.

Note the asymmetry the ledger does not show: #25's consumer has **two** read sites, because the rule
has two constructors and the specification binds them as two events. One clause, one accuser per
site — the code names the site (task 4.4), and the clause pointer in `predicate_graph.csv` is the
same for both rows.

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 (`ExecutionContext` mentions) | 19 files | **18** |
| INV-INS-133 (`condition` reads) | 8 | **7** |
| INV-INS-134 (writes off acceptance, no reason) | 24 | 24 |
| accepting-state calls (INV-INS-147) | 21 | **20** |
| predicate sites in the graph | 86 | **85** |
| G-PRED2 findings | 26 | **25** |
| G-ORDER divergences | 4 | 4 |
| structural findings, all gates | 77 | **74** |

`gate_baseline.json` retires three rows (`c2/RANDOMIZED`, `match/PREPARED_PBE`, and the file's
`ExecutionContext` row), and no finding appeared outside the baseline. G-ORDER is unchanged in both
directions, as it must be: the automaton, the alphabet and the two `order_alphabet_map.csv` rows are
untouched — this pass moved code inside two event bodies and one handler, and moved no symbol.

## Noticed and not repaired

The file's javadoc header names **`GCMParameterSpec`**, a copy-paste the seed carries too
(`jca/PBEParameterSpecSpec.mop:11`). Repairing it is a one-line hunk that the divergence recorder
has no kind for — none of its ten `KINDS` describes a documentation correction — and widening that
whitelist is collateral this task does not own. Recorded here; it is worth a line of whichever task
next touches the recorder.

## Reproducing

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android \
    --b $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f2
```

The JSON summary is at the top of that output, not the bottom.
