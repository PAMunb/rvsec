# SecureRandomSpec — the file pass that closes two windows (gh105 task 4.5)

The file with the most `ExecutionContext` mentions in the set, the file that closes the
IV chain task 4.4 opened, and the file where a write relocation finally has a
behavioural delta to show. One read changes substrate and gains a third verdict, five
body writes become two acceptance-point writes plus two that stay with a recorded
reason and one that is deleted, one row is added to the `end` state, and a second
acceptance point is declared.

## What the rule says, and where each site landed

api30 `SecureRandom.cryptsl` states one `REQUIRES` clause and four `ENSURES`:

```
ORDER     Ins, Seeds?, Ends*                        :62
          Ins := Gets | Cons; Ends := gS | Nexts
REQUIRES  randomized[seed];                         :66
ENSURES   randomized[this] after Ins;               :71
          randomized[genSeed];                      :73
          randomized[next];                         :75
          randomized[numB];                         :77
```

Three of the four `ENSURES` clauses have a site in the file. The fourth is the one the
specification never settled, and it is treated below.

| site | before | after | clause |
|---|---|---|---|
| `setSeed2` read | `read:body`, boolean | `read:body`, three-valued, `PredicateStore` | `:66 randomized[seed]` |
| `genSeed` write | `write:body` | staged → `@match2` at `end` | `:73 randomized[genSeed]` |
| `next2` write | `write:body` | staged → `@match2` at `end` | `:75 randomized[next]` |
| `next1` write | `write:body` | `write:body`, with a recorded reason | — (see below) |
| `next3` write | `write:body` | `write:body`, with a recorded reason | — (see below) |
| `ints` write | `write:body` | **deleted** (the event stays) | — |
| `@match1` write | `write:acceptance` | `write:acceptance`, `PredicateStore` | `:71 randomized[this] after Ins` |
| `@match1` bookkeeping | `bookkeeping:match` | deleted | INV-INS-147 |
| `end` state | no `next2` row, not aliased | `next2 -> end`, `alias match2 = end` | `:62 Ends*` |

`randomized[this] after Ins` is an `after L` clause, so its acceptance point is the
state `Ins` leads to — `init`, which `alias match1` already named. The other two
clauses carry no qualification, so their acceptance point is the accepting state the
Ends reach, and that needed a second alias. This is the `CipherSpec` shape of task 4.1
seen from the other side: there the qualified clause needed the second alias
(`match2 = s3`) and the unqualified ones used `end`; here the unqualified ones need it.

## The three decisions this task had to make

### 1. The `randomized[numB]` stand-ins (`next1`, `next3`)

The file has carried the question since 2023, in a TODO of its own:

```java
//TODO randIntInRange eh RANDOMIZED ou eh o retorno do nextInt ???
```

The rule's fourth clause binds `numB` in `ne: next(numB)`. `next(int)` is **protected**
in `java.util.Random`, so no application calls it, and the file answered with two
stand-ins that cannot both be right: `next1` marks the *argument* of `nextInt(int)`,
`next3` marks the *return* of `nextInt()`. Task 2.8 had already decided the ORDER half
of the question — `order_alphabet_map.csv:79,81` record both ORDER-unmapped, because
pairing either with `ne` would be an inference INV-INS-138 forbids.

Measured before choosing:

* **No live specification reads `RANDOMIZED` over an `int`.** The only structural
  consumer is `RandomStringPassword.vo`, which reads it over the `Object` argument of
  `String.valueOf(Object)` — a propagation read with no accuser (task 4.11 records it
  as such), whose chain continues `toCharArray()` → `PBEKeySpec`. Sweeping the five
  sets for `validate(Property.RANDOMIZED` hits `jca`, `jca_android`,
  `jca_android_bug_predicate`, and no file of `generic`/`generic_new`; the hits in the
  archived set do not count, since it was failed 22/22 by the 2026-08-08 audit and is a
  record rather than a seed.
* **No trace of the corpus exercises that chain.** The one `RandomStringPassword`
  trace passes the literal `"secret"`.
* **The migration alone already narrows the writes, whatever their placement.**
  `PredicateStore` keys the bound object by identity (`BoundKey`,
  `System.identityHashCode`, `PredicateStore.java:177-207`) where the frozen substrate
  keyed it by `equals`, and an `int` autoboxes at the call. So a predicate over a boxed
  primitive only survives to a later read inside the `Integer` cache (−128..127), where
  equal small values genuinely are one object. This is the write-side unsoundness the
  delta's *inexpressible predicate* rule names.

Two precedents point in opposite directions here, which is why the choice went to the
researcher rather than being made in the edit. Task 4.1 deleted `WRAPPED_KEY` because a
write that translates no clause is deleted rather than recorded as an omission; task
5.5 names these two writes explicitly (*"drop the autoboxed argument writes"*) and owns
the clause they answer.

**Chosen (researcher, 2026-08-21): keep both writes in the body, migrated to the new
store, with the reason recorded in `predicate_graph.csv`.** INV-INS-134 admits a write
kept off the acceptance point when it carries a recorded reason, and that is the honest
state: an acceptance-point placement would claim a clause the file cannot point at.
Task 5.5 resolves the clause with the rest of the `randomized` hub and drops them, with
the whole oracle in front of it rather than half.

### 2. The `ints` write

`SecureRandom.ints(..)` returns an `IntStream`, and api30 declares **no stream event at
all** — `order_alphabet_map.csv:82` already recorded the site as ORDER-unmapped, noting
it "exists to mark the stream randomized, not to order anything". The write claimed
`randomized` over an object on the strength of a method name. Nothing in any of the
five sets reads `RANDOMIZED` over an `IntStream`.

**Chosen (researcher, 2026-08-21): delete the write, keep the event.** This is exactly
the disposition `CipherSpec.wkb1` received at task 4.1, where `wrap` is declared by the
rule and named in no `ENSURES` clause. The event stays because it is in the automaton:
removing it would make the call unmodelled rather than unmarked, and would reopen the
G-ACC the Group 3 just closed. `Property.RANDOMIZED` stays in the enum — INV-INS-132 is
append-only.

### 3. The `before` advice of `next2`

Left as the seed had it. An identity-keyed store does not care whether the array is
already filled — it is the same object on both sides of the call — so switching to
`after` would change when the predicate is written without changing what it says. A
substrate migration is not the place for that.

## What the harness measured

Cumulative against the pre-image over the corpus, now **82 traces** (79 plus the three
this task adds): **58 unchanged, 17 moved, 2 introduced, 5 removed** (before this task,
over 79: 56 / 17 / 2 / 4). Every one of the six moves is accounted for:

| trace | before 4.5 | after 4.5 | why |
|---|---|---|---|
| `IvParameterSpecSpec.txt` | introduced | **unchanged** | the F2 window of task 4.4 closes |
| `IvParameterSpecSpec-offset.txt` | introduced | **unchanged** | the same |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | **introduced** | a new F2 window opens |
| `SecretKeySpecSpec.txt` | unchanged | **introduced** | the same |
| `SecureRandomSpec-nextbytes-twice.txt` | (new) | **removed** | the `Ends*` repair |
| `SecureRandomSpec-genseed-*.txt` | (new) | unchanged | see the relocation below |

### The IV chain closes, exactly where task 4.4 said it would

`SecureRandomSpec.next2` marks the `byte[]` that `nextBytes(byte[])` fills. Task 4.4
migrated `IvParameterSpec`'s two reads to the new store while the producer still wrote
to the old one, so two conforming traces started answering `NOT_OBSERVED` and were
committed as `introduced` — the F2 window declared by design D-8. With the producer on
the same store, both traces are silent again:

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `IvParameterSpecSpec.txt` | — | — | unchanged |
| `IvParameterSpecSpec-offset.txt` | — | — | unchanged |

The two `introduced` verdicts of task 4.4 are retired. **Ledger edge #12
(`IvParameterSpec randomized[iv]`) is now realised by mechanism A**, the store, as a
side effect of two file passes that were never about the chain — which is the collision
task 5.1 has to resolve: `predicate_graph.csv` records `mechanism=store` for both reads
because that is what the artefact does, and 5.1 chooses between narrowing
`IvChainJunction.mop` to clause #9 or moving #12 into the junction and dropping the
reads' accusers. The design forbids one clause having two accusers.

### And two new windows open, on the same mechanism seen from the producer side

The set is mid-migration, so moving a producer to the new store dessatisfies every
consumer still reading the old one. INV-INS-130 forbids the alternative — a `.mop` of
this set may not name the frozen substrate at all — so a dual write to bridge the
window is not available, and the window is recorded instead:

| trace | B accuses | closed by |
|---|---|---|
| `PBEParameterSpecSpec-randomised.txt` | `PBEParameterSpecSpec.c1` | task 4.7 |
| `SecretKeySpecSpec.txt` | `SecretKeySpecSpec.c1` | task 4.10 |

Four other traces that randomise an array through `next2` and hand it to an unmigrated
consumer did **not** change, and the reason is worth recording because it is the
false-negative mechanism this change exists to remove: `GCMParameterSpecSpec.txt` and
`-second-overload.txt` are silent on both sides, because that file's reads are still
`condition(...)` guards (two of the eight INV-INS-133 findings that remain). A guard
that goes false suppresses the transition, so the constructor leaves the automaton and
nothing is reported at all — a broken producer link turns into silence rather than into
a report. Task 4.8 moves those reads into the body, and the same window will open there
as a report. `SecretKeySpecSpec-offset.txt` and `PBEKeySpecSpec-salt-only.txt` are
unchanged for their own reasons: the first is guarded the same way, the second was
already accusing through the task 3.5 fusion.

### The `Ends*` repair, in one row

`SecureRandomSpec-nextbytes-twice.txt` is the trace the delta has been citing since
INV-INS-138 was written:

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `SecureRandomSpec-nextbytes-twice.txt` | `SECURERANDOM-ORDER-00 ev=next2` | — | **removed** |

`Ins, Seeds?, Ends*` accepts `getInstance(); nextBytes(); nextBytes()`; the `end` state
omitted `next2` while carrying every other End, so the second call took the fail row.
12,400 events on the published campaign, 99.98 % of them inside libraries.

It took **two** changes, not one, and the second was not planned as a repair.
`test_the_securerandom_kleene_star_is_measured_and_not_argued` failed on the first pass
of this task's edit, because `end` still was not an *accepting* state: the file's only
alias was `match1 = init`, and G-ORDER derives the accepting set from the aliases. So
the automaton would have accepted the second `nextBytes` as a transition and still
rejected the word. Declaring `alias match2 = end` for the two unqualified `ENSURES`
clauses is what makes `end` accepting — the placement rule of INV-INS-134 and the
language repair of INV-INS-138 turn out to be the same edit, and the gate is what
showed it.

### The write relocation, which finally has a delta

Task 4.1 and task 4.4 could both only verify their write relocations structurally,
because nothing read the predicate yet. Here the producer and a consumer sit in the same
file, so the relocation is measurable:

| trace | A accusing events | B accusing events |
|---|---|---|
| `SecureRandomSpec-genseed-to-setseed.txt` | — | — |
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | `g4`, `genSeed`, **`setSeed2`** | `g4`, `genSeed`, **`setSeed2`** |

The second row classifies `unchanged` — the harness keys the class on the *set of
accusing events*, and the set is the same. The envelopes say otherwise, and the
identity of the accusing event is itself the proof:

* On **A**, the pre-image splits the call into `setSeed2` (guard
  `condition(validate(RANDOMIZED, seed))`, empty body) and `setSeed3` (the negated
  guard, carrying `SECURERANDOM-CONSTR-00`). The event that fired is **`setSeed2`** —
  the conforming twin — so the positive guard was **true**: the pre-image considered
  the seed randomised. It was, because `genSeed`'s body write ran unconditionally,
  even though the generator came from `getInstance("NativePRNG")`, an algorithm the
  rule's CONSTRAINTS reject and which the automaton never admits. The misuse was
  silent.
* On **B**, the write sits in `@match2` at `end`, a state this trace never reaches, so
  it never runs. `setSeed2` reads `NOT_OBSERVED` and emits
  `SECURERANDOM-NOBS-00`.

That is INV-INS-134 stated as a measurement rather than as a principle: *a write in an
event body establishes an `ENSURES` fact for a sequence the rule has not accepted, and
a consumer downstream validates against a predicate the producer never earned.* No
`ErrorCollector` count probe was needed — which twin fired on the pre-image answers the
question by itself.

### And the `setSeed2` read, moved and re-coded

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `SecureRandomSpec-unrandomised-seed.txt` | `SECURERANDOM-CONSTR-00 ev=setSeed3` | `SECURERANDOM-NOBS-00 ev=setSeed2` | moved |
| `SecureRandomSpec-randomised-seed.txt` | — | — | unchanged |

The `moved` row is task 3.1's fusion, unchanged by this task except in the code the
surviving event emits: *not observed* rather than *violated*, which is what the seed's
own message already said — "expects a byte array observed to come from a randomized
source". That wording travels to the `NOBS` site and `CONSTR` gets a wording of its own.

`SecureRandomSpec-randomised-seed.txt` is quiet on both sides, and it is the **first
`SATISFIED` verdict of this change to come from a producer and a consumer that both
sit on the new store**: `nextBytes(buf)` writes at `@match2`, `setSeed(buf)` reads by
identity, and the read answers `SATISFIED`. Half of ledger #33
(`SecureRandom randomized[seed]`) is therefore wired here; the other half is the
constructor's, `c2: SecureRandom(seed)`, which task 3.1 deliberately left accuser-less
and task 5.5 owns.

## What this task could not measure

* **`SECURERANDOM-CONSTR-00` has no execution path.** At arity 1 with no value
  positions a recorded tuple always matches, so `validate` can only answer `VIOLATED`
  through `negate`, and api30 has exactly two `NEGATES` clauses — `SecretKey:
  generatedKey[this,_] after d` and `PBEKeySpec: speccedKey[this,_] after cP`. Neither
  withdraws `randomized`. This is the same unreachability
  `IVPARAMETERSPEC-CONSTR-00`/`-01` carry, for the same reason, and it is written
  because INV-INS-133 requires the failed read and the not-observed read to carry
  distinct codes. There are now six such codes across three distinct reasons.
* **The `next1`/`next3` narrowing is not exercised.** No trace binds an `int` through
  `String.valueOf(Object)`, so the `Integer`-cache boundary is argued from the store's
  keying and not measured on a program. Task 5.5, which drops the writes, does not need
  it measured; a task that wanted to *keep* them would.
* **The `ints` deletion has no delta.** No trace calls `ints(..)`, and no set reads the
  mark. It is verified structurally: the site leaves `predicate_graph.csv`.

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 (`ExecutionContext` mentions) | 21 files | **20** |
| INV-INS-133 (`condition` reads) | 8 | 8 |
| INV-INS-134 (writes off acceptance, no reason) | 30 | **25** |
| accepting-state calls (INV-INS-147) | 23 | **22** |
| predicate sites in the graph | 89 | **87** |
| `write:body` / `write:acceptance` | 30 / 9 | **27 / 11** |
| G-PRED2 findings | 26 | 26 |
| G-ORDER divergences | 4 | 4 (witness still `c1 c1`) |
| structural findings, total | 85 | **79** |

`gate_baseline.json` retires six rows (the file's `ExecutionContext` mention and its
five `write:body` sites). G-PRED2 does not move: `RANDOMIZED` was already both written
and read in the set.

G-ORDER still reports `SecureRandomSpec` divergent, and the witness is unchanged —
`c1 c1`, the `init` self-loop over the constructor, which the rule's `Ins` does not
repeat. The `end` state also still admits Seeds after an End. Both are recorded and not
repaired here; task 7.1 owns them, and the count of known divergences is the same four
before and after.

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

The JSON summary is at the top of that output, not the bottom, and it names the scratch
directory holding both generated snapshots. The per-trace envelopes quoted above come
from `<scratch>/{a,b}/work/outcomes.json`, which records one envelope per dispatcher
call — the harness floor. Where a single call can accuse twice, that floor is not the
count; here it did not need to be, because the two sides accuse through *different
events* and the event name is the evidence.
