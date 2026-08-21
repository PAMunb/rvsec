# GCMParameterSpecSpec — the pass that ended a mute specification (gh105 task 4.8)

Two reads, one write, one handler, and the file's whole census fit on one line. What the pass
found before it edited anything does not: task 4.7 discovered that a guard can silence an
*event*; this file is the case where two guards and an unreachable handler silenced the
**specification**. Measured on eight constructions over the whole `ErrorCollector`, on all six
of its corpus traces on both snapshots, and against the published gh104 corpus:
`GCMParameterSpecSpec` accused **nothing, ever**.

With the two reads in their bodies the file speaks, and ledger clause **#11** is wired end to
end — the fourth edge a Group-4 file pass has closed on Group 5's behalf, and the **third** that
lands on task 5.4.

## What the rule says, and where each site landed

api30 `GCMParameterSpec.cryptsl`:

```
EVENTS      c1: GCMParameterSpec(tLen, src);                 :17
            c2: GCMParameterSpec(tLen, src, offset, len);    :19
            Cons := c1 | c2;                                 :21
ORDER       Cons                                             :25
CONSTRAINTS tLen in {128, 120, 96, 112, 104};                :29
REQUIRES    randomized[src];                                 :34
ENSURES     preparedGCM[this];                               :39
```

| site | before | after | placed by |
|---|---|---|---|
| `c1` read of `randomized[src]` | `read:condition-guard`, boolean | `read:body`, three-valued, with the accuser it never had | this task |
| `c2` read of `randomized[src]` | `read:condition-guard`, boolean | `read:body`, three-valued, with the accuser it never had | this task |
| `c1`/`c2` check of `tLen` | inside the same `condition(...)` | `if` in each body, one code each | this task |
| `c2`'s three range conjuncts | inside the same `condition(...)` | **deleted** | this task |
| `@match` write of `preparedGCM` | `write:acceptance`, old substrate | `write:acceptance`, new store, no omission record | the seed |
| `@match` bookkeeping | `bookkeeping:match` | deleted | INV-INS-147 |

Seven codes where there was one. A code names a **site**, not a clause (task 4.4): each event
carries a constraint report, a *violated* report and a *not observed* report of its own.

## The measurement that came before the edit

The `.mop` had two `condition(...)` guards, each conjoining the rule's one CONSTRAINTS clause
with the read of its one REQUIRES predicate. `condition(...)` compiles into the monitor's
`Prop_1_event_X` as `if (!(guard)) return false;` **ahead of** `handleEvent`, so a construction
that broke either clause took no transition. In the pre-image's generated monitor:

```java
final boolean Prop_1_event_c1(int tagLen, byte[] src, GCMParameterSpec s) {
    if ( ! (validLengths.contains(tagLen) && <read>) ) { return false; }   // before handleEvent
    { spec = s; }
    int nextstate = this.handleEvent(0, Prop_1_transition_c1);
```

and `Prop_1_event_c2` the same, with three more conjuncts. Unlike task 4.7's file, **no event
here had an unguarded sibling**: both were guarded, so the guard was the file's only path to a
report — and the `@fail` handler cannot make up for a suppressed transition, because it is
unreachable by construction. Both transition rows are `{1, 2, 2}`, and the monitor is keyed on
the constructed object (`GCMParameterSpecSpec(GCMParameterSpec s)`), so a monitor of this
specification receives **at most one event** and state 2 is never entered. That last fact was
already asserted, in the reason of the gh104 hunk `4e26843171eb`, together with the corpus
figure: **0 of the published corpus's 97,018 rows** are attributed to this specification.

So the prediction was total silence, and the measurement is total silence — three independent
readings of it:

| reading | result |
|---|---|
| the six corpus traces, both snapshots, differential harness | `unchanged`, `—` accused on both sides |
| eight constructions, whole `ErrorCollector`, on `a/work/classes/classes` | 0, 0, 0, 0, 0, 0, 0, 0 |
| the published gh104 corpus | 0 of 97,018 rows |

The corpus half had to be written first: of the 85 traces, the two that named this file
(`GCMParameterSpecSpec.txt`, `-second-overload.txt`) both **conform whole**, so the corpus could
not have separated any option here (finding 18). Four traces were added — an unrandomised source
and an unadmitted tag length, at each overload.

The probe is audited rather than asserted (learning 27): on the same class loader, with the same
collector, a sibling construction (`PBEParameterSpec(salt, 1000)` over a plain salt) draws **2**
reports, and the loader declares exactly the two dispatchers the probe calls,
`GCMParameterSpecSpec_c1Event/3` and `_c2Event/5`. Zero here is zero, not a probe that missed.

## The three decisions, and what measured each one

### 1. The three range conjuncts of `c2` are deleted, not moved

`offset >= 0 && len >= 0 && src.length >= offset + len` stood beside the read in `c2`'s guard.
They translate **no clause**: api30 states one CONSTRAINTS clause, over the tag length, and says
nothing about the offset or the length. And they are **false-unreachable where they stood**. The
constructor's documented contract —

```
 * @throws IllegalArgumentException if {@code tLen} is negative,
 * {@code src} is null, {@code len} or {@code offset} is negative,
 * or the sum of {@code offset} and {@code len} is greater than the
 * length of the {@code src} byte array.            GCMParameterSpec.java:102-105
```

— is exactly their complement, and an `after ... returning` advice runs only on a normal return.
Measured on all three shapes: `(128, src, 8, 16)`, `(128, src, -1, 16)` and `(128, src, 0, -1)`
each throw `IllegalArgumentException: Invalid buffer arguments` before any advice.

Chosen (researcher, 2026-08-21): **delete**. Moving them to the body was the alternative and
would have written two more codes with no execution path — a **fourth** reason distinct from the
three already recorded (finding 8) — accusing a program the platform itself forbids. Keeping them
as guard was the third option, declined because it leaves a `condition(...)` that reads as a
filter in the one event this pass is emptying.

**The measurement that separates the options cannot be written.** There is no trace, because
there is no program: the JVM rejects it. That is a statement about the *program*, not about the
corpus — the distinction finding 19 asks for, and here it falls on the strong side.

### 2. The tag-length check leaves the guard with the read

INV-INS-133 says in as many words that `CONSTRAINTS` checks remain legitimate guard uses. It left
anyway, on task 4.7's precedent (decision 15) and on this file's own measurement.

Chosen (researcher, 2026-08-21): **to the body, with a code at each event.** Keeping it as a
guard would leave the read this pass takes out of the guard sitting behind a second guard that
suppresses the same transition, so the read would still not run on a construction with an
unadmitted tag length — and the file would stay mute about `GCMParameterSpec(64, iv)`, which is
the very silence the pass was sent to end.

Measured delta: the two `-badtaglen` traces go from **0 reports to 1** each. Unlike task 4.7's
version of this decision, this is a statement about the program as well as the corpus: *every*
construction with a tag length outside `{96, 104, 112, 120, 128}` is accused after this pass and
was accused of nothing before it.

The message names the rule rather than listing the five lengths. The set lives in the monitor
field `validLengths`, and `gh104_message_gate.py` reads a message's integer literals against the
guard's: spelling the numbers out asserted five literals the guard does not carry, ten findings.
The form used instead — `exp='a tag length api30 GCMParameterSpec.cryptsl admits'` — is the one
`KeyPairGeneratorSpec`'s key-size site already uses for the same reason.

### 3. The unreachable `@fail` is recorded, not repaired

The handler and its `GCMPARAMETERSPEC-ORDER-00` cannot fire, for the reason measured above. It
is a pre-existing condition, not one this pass creates.

Chosen (researcher, 2026-08-21): **record here, repair nowhere yet** — the treatment finding 1
gave the `CipherSpec` `unsafeAlg` sink. The repair is to the automaton, and this pass moves no
symbol: `GCMParameterSpecSpec` is one of the thirteen specifications still absent from
`order_alphabet_map.csv`, which task 7.1 owns, so G-ORDER skips it in both directions and the
four known divergences are untouched.

**It is worth a task of its own.** The `ere` `c1 | c2` gives a per-object monitor exactly one
usable event, so every `@fail` of a construction-only specification in this set is in the same
position. This file is the one where it was measured.

### And one that was not a decision: `preparedGCM` carries no omission record

Task 4.7 gave `preparedPBE` the change's first `disposition`, because the oracle requires it
nowhere. Measured here, `preparedGCM` is **not** a dead end: it appears twice in api30 — as this
rule's `ENSURES` and as `Cipher.cryptsl:184`,
`part(1,"/",transformation) in {"GCM"} => preparedGCM[params]` — which is **ledger clause #10**,
dispositioned *wire* at task **5.8**. The G-PRED2 finding on this write closes there, by a read,
not here by a record, and G-PRED2 therefore stays at 25.

Measured in the sets: `PREPARED_GCM` is written in three of the five (`jca`, `jca_android`, and
the reproved `jca_android_bug_predicate`, which the grep hits and which is a record, never a
seed) and **read in one — that same reproved set**, at `jca_android_bug_predicate/CipherSpec.mop:89`.
The shape task 5.8 needs already exists there, in the one place it must not be copied from.

## What the harness measured

Cumulative against the pre-image over the 89-trace corpus: **60 unchanged, 17 moved, 7
introduced, 5 removed**. Before this task, with the same 89 traces: 64 / 17 / 3 / 5. Exactly the
four new traces move, and all four move from `unchanged` to `introduced`.

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `GCMParameterSpecSpec.txt` | — | — | unchanged |
| `GCMParameterSpecSpec-unrandomised.txt` | — | `c1` NOBS-00 | **introduced** |
| `GCMParameterSpecSpec-badtaglen.txt` | — | `c1` CONSTR-00 | **introduced** |
| `GCMParameterSpecSpec-second-overload.txt` | — | — | unchanged |
| `GCMParameterSpecSpec-second-overload-unrandomised.txt` | — | `c2` NOBS-01 | **introduced** |
| `GCMParameterSpecSpec-second-overload-badtaglen.txt` | — | `c2` CONSTR-02 | **introduced** |

The two `unchanged` rows are the ones to read closely: **no F2 window opens here**. A migrated
consumer whose producer has not migrated accuses a conforming trace (INV-INS-144's window rule);
this consumer's producer landed at task 4.5, so a randomised source is `SATISFIED` on the new
store and the file stays silent about it. That silence is the satisfying half of the pair,
measured rather than argued.

## Counting the whole `ErrorCollector`

The harness records one envelope per dispatcher call, a floor wherever a call accuses more than
once. Counting the collector instead, over the pre-image and the migrated set — the two columns
are the whole story here, because `GCMParameterSpecSpec.mop` is **byte-identical** in
`backup/gh105-preimage/jca_android` and at HEAD before this task, so the "seed" and "before"
columns of the usual three-column probe coincide:

| construction | pre-image = before 4.8 | after 4.8 |
|---|---|---|
| 2-arg, `tLen=128`, plain src | **0** | 1 — NOBS-00 |
| 2-arg, `tLen=64`, plain src | **0** | **2 — NOBS-00, CONSTR-00** |
| 2-arg, `tLen=128`, randomised src | 0 | 0 |
| 2-arg, `tLen=64`, randomised src | **0** | 1 — CONSTR-00 |
| 4-arg, `tLen=128`, plain src | **0** | 1 — NOBS-01 |
| 4-arg, `tLen=64`, plain src | **0** | **2 — NOBS-01, CONSTR-02** |
| 4-arg, `tLen=128`, randomised src | 0 | 0 |
| 4-arg, `tLen=64`, randomised src | **0** | 1 — CONSTR-02 |

Six of the eight rows were silent and are not. Rows 3 and 7 are the satisfying half — the two
constructions that break no clause — and they are silent on both sides, which is what a closed
chain looks like. Rows 2 and 6 are why the report decomposes per clause: two clauses of two
different sections of the rule, broken together, produce two reports under two codes, where a
composite site would have had to choose one.

Reproducing (compile against `rvsec/rvsec-mop/target/gh104-classpath.txt`, run once per side
with that side's `work/classes/classes` from the harness scratch the JSON summary names):

```java
// every dispatcher of the right arity, on both sides
for (Method m : rm.getDeclaredMethods()) {
    if (!m.getName().startsWith("GCMParameterSpecSpec_")) continue;
    if (m.getParameterCount() != arity) continue;      // 3 for c1, 5 for c2
    m.invoke(null, arguments);
}
// randomising the source first, when the row asks for it:
call("SecureRandomSpec_g1Event", 2).invoke(null, "SHA1PRNG", r);
r.nextBytes(src);
call("SecureRandomSpec_next2Event", 2).invoke(null, r, src);
```

## The gate that read the specification the old way

The migration broke **G-CONF** with two failures, and both were artefacts of the reader:

```
GCMParameterSpecSpec CRYSL-NAO-IMPLEMENTADO  tLen in {128, 120, 96, 112, 104}
GCMParameterSpecSpec MOP-SEM-BASE            `validLengths` guards calls no CONSTRAINTS clause reaches
```

One clause, reported twice, from each side: the rule's clause "reaches no guard", and the set's
list "backs no clause". The cause is `_list_guarding` (`scripts/gh104_gates.py:783`), which
requires `event.condition` and searches only inside it. The **sibling branch of the same
function** — the numeric-bound matcher in `derive_constraint_rows` — was already repaired for
exactly this, inside this change, at task 3.4, and its comment says so in as many words: *"a
matcher that read only the guard would call a migrated numeric bound unbacked … when the clause
is still stated, one line further in."* The set-membership branch was left behind because no
migrated file had moved a list membership out of a guard until now.

Chosen (researcher, 2026-08-21): **repair here**, the same repair the sibling branch already
carries. Measured: `jca_android` G-CONF 2 → 0 failures; the four suites go to 94/94; the frozen
`jca` set changes no verdict — its G-CONF reproduction of the committed `constraint_table.csv`
was green before the patch and is green after it.

This is finding 24's shape a second time, and worth stating as a rule rather than an incident:
**when a migration makes a gate complain, ask first whether the gate reads the post-migration
form.** Two of this change's gate surprises now have that answer.

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 (`ExecutionContext` mentions) | 18 files | **17** |
| INV-INS-133 (`condition` reads) | 7 | **5** |
| INV-INS-134 (writes off acceptance, no reason) | 24 | 24 |
| accepting-state calls (INV-INS-147) | 20 | **19** |
| predicate sites in the graph | 85 | **84** |
| G-PRED2 findings | 25 | 25 |
| G-ORDER divergences | 4 | 4 |
| structural findings, all gates | 74 | **71** |
| assertions in the four suites | 94 | **94** |

`gate_baseline.json` retires three rows (`c1/RANDOMIZED`, `c2/RANDOMIZED` and the file's
`ExecutionContext` row), and no finding appeared outside the baseline. G-ORDER is unchanged in
both directions and in its skip list: this pass moved code inside two event bodies and one
handler, moved no symbol, and this file has no `order_alphabet_map.csv` row to move — task 7.1
owns it, with the twelve others.

## Noticed and not repaired

**`gh104_mop_lint.py` reads a comment between `ere` and the first handler as the formula.**
`parse_mop` takes the formula text from `ere :` to the next line starting with `@` or `alias`
(`gh104_gates.py:320`), so a comment block attached to `@fail` — the natural place for the note
about that handler — is parsed as event symbols, one `undeclared-symbol` finding per word: 67 of
them here. The note was moved above the `ere` instead, where it is anyway about the automaton,
and the linter is left alone. It is a one-line fix (stop at a comment line as well) and it
belongs to whichever task next owns that script; recording it here so the next file pass that
wants to annotate a handler does not rediscover it as a mystery.

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
