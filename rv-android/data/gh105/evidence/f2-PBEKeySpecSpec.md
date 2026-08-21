# PBEKeySpecSpec — the pass that finishes a clause it was not sent to wire (gh105 task 4.6)

Two reads, one write, one removal and one handler, in the file that carried five of the
seventeen orphan accusers. Like task 4.4, the placement census does not move: task 3.5 had
already brought both reads into `c1`'s body when it fused the three twins, and the write stays
where it is for a reason this task had to measure before it could record it. What moves is the
substrate, the truth value, the arity of the write, and the removal — brought forward from task
6.5 on purpose.

And one thing nobody asked for moved as well: with `SecureRandomSpec.next2` on the new store
since task 4.5, `randomized[salt]` now answers **SATISFIED** on the trace that randomises the
salt. Ledger clause #24 is wired end to end, half by 4.5 and half by 4.6, by a pair of file
passes that were never about the chain. Task 5.4 owns the consequence.

## What the rule says, and where each site landed

api30 `PBEKeySpec.cryptsl`:

```
FORBIDDEN  PBEKeySpec(char[]) => c1;  PBEKeySpec(char[], byte[], int) => c1;   :16,18
EVENTS     c1: PBEKeySpec(password, salt, iterationCount, keylength);          :23
           cP: clearPassword();                                               :25
ORDER      c1, cP                                                             :29
CONSTRAINTS iterationCount >= 10000;  neverTypeOf(password, java.lang.String); :33,35
REQUIRES   randomized[salt];                                                  :40
ENSURES    speccedKey[this, keylength] after c1;                              :45
NEGATES    speccedKey[this, _] after cP;                                      :50
```

| site | before | after | placed by |
|---|---|---|---|
| `c1` read of `randomized[password]` | `read:body`, boolean | `read:body`, three-valued | task 3.5 |
| `c1` read of `randomized[salt]` | `read:body`, boolean | `read:body`, three-valued | task 3.5 |
| `c1` write of `speccedKey` | `write:body`, arity 1 | `write:body`, arity 2, reason recorded | the seed |
| `c2` withdrawal of `speccedKey` | `remove:body` | `negate:body` | the rule (`after cP`) |
| `@match` bookkeeping | `bookkeeping:match` | deleted with the handler | INV-INS-147 |

Four codes where there were three: `PBEKEYSPEC-NOBS-00` and `-01` join the two `CONSTR` codes
the reads already had, because a code names a **site and a verdict**, and a site that cannot say
which of the two verdicts it saw is a site that reports less than it knows.

## The three decisions, and what measured each one

### 1. The removal comes forward from task 6.5

`clearPassword` is the one of the set's nine removals that translates a real `NEGATES` clause,
and task 6.5 owns it. But the write it withdraws is in this file and changes substrate in this
pass. Splitting the two would have left `speccedKey` ensured on the new store and withdrawn from
the old one between the two tasks — the withdrawal a no-op in between, an F2 window opened inside
a single file and avoidable by doing both at once. INV-INS-130 asks for the same thing from the
other side: a migrated file names no other substrate.

Measured before choosing. Leaving the line would have left the file with 2 mentions instead of 0
(the import and the call); the baseline is keyed `[set, file, subject]`, so the finding would have
survived without becoming a regression; and task 4.15, which requires import discipline green,
could not have closed before task 6.5 — the Group-4 closing task would have come to depend on a
Group-6 one. Chosen (researcher, 2026-08-21): **translate it here.** Task 6.5 keeps its other
deliverable, the `unclosable` record for `SecretKey generatedKey[this,_] after d`.

The translation carries a semantic difference, recorded rather than measured: the new store
**remembers** the withdrawal, so a later `validate` of a cleared spec answers `VIOLATED`, where
the old substrate forgot the entry and would have answered `NOT_OBSERVED`. That is what the clause
states. Nothing reads `SPECCED_KEY` in any of the five sets — measured: `jca` writes it twice,
`jca_android` twice, the reproved `jca_android_bug_predicate` three times, and **no set reads it
anywhere** — so the difference has no observer today.

### 2. The `ENSURES` write stays in the body, with the reason recorded

api30 qualifies the clause: `speccedKey[this, keylength] **after c1**`. The acceptance point is
therefore the state `c1` leads to, and this file states its automaton as an `ere`. Measured in the
generators: `alias` exists only in the FSM plugin's grammar (`rv-monitor/.../logicpluginshells/{fsm,tfsm}/parser/FSMParser.jj`),
and the ERE plugin emits exactly one alias of its own — `alias match = …` over the accepting
states (`rv-monitor/plugins_logicrepository/ere/.../FSM.java:85`). Here those are the states after
`c2`, which is where the rule **negates** the predicate rather than ensuring it. No file of the
64-file `ere` population in the universe carries an alias.

So the literal placement needs the `fsm` notation, and that path was measured before it was
declined. Restating the automaton and declaring `alias match1 = <post-c1>` makes the state
accepting, and G-ORDER derives the accepting set from the `match…` aliases: the specification
would then accept `c1` alone. Run through the gate's own DFA, the api30 ORDER answers otherwise —
`('c1',)` → False, `('c1','cP')` → True. That is a fifth G-ORDER divergence in a file that is
green today, and worse than a gate finding: the file would claim that a PBEKeySpec whose password
is never cleared is a complete accepted sequence.

Measured on the other side: **no constructible program makes this transition fail for the object
it binds.** The constructor returns a fresh object on every call, so a second `c1` for the same
monitor is impossible; `f1` and `f2` are Kleene loops; and `c2` can only follow. Body and
post-`c1` state coincide on every trace. INV-INS-134 admits a write kept elsewhere with a recorded
reason, and this is that case: the reason lives in `predicate_graph.csv` and in the file's own
comment block. Chosen (researcher, 2026-08-21): **body, with the reason recorded.**

A third option existed and is recorded because it may be the right one later: an `fsm` with a
named category that is *not* a `match` alias (`alias specced = …` + `@specced`) puts the write
after the transition without touching the accepting set, since the order gate reads only
`match…`. It costs an automaton restatement and either a widening of the graph gate's
`_ACCEPTANCE_HANDLERS` (`^@match\d*$`) or the same recorded reason, for a delta measured at zero.

The write does change in one way the invariant does require: it rises to the rule's arity.
`ensure(SPECCED_KEY, s, keyLength)` names the object **and** the key length, where the seed named
the object alone.

### 3. The clause-less read is three-valued too

`PBEKEYSPEC-CONSTR-01` tests `randomized[password]`, and api30 requires nothing of the password —
its only CONSTRAINTS clause about it is `neverTypeOf(password, java.lang.String)`, a different
claim. Task 3.5 measured that, kept the accusation and recorded it; this task does not repair it
either. What it decides is narrower: whether a read that translates no clause splits its code like
its sibling. Chosen (researcher, 2026-08-21): **split.** The site accuses the same constructions
with the same message, the message it already carried ("was not observed to come from a randomized
source") is the third value's, and a site that cannot name its verdict beside a sibling that can
would be the odd one out for no reason the rule gives. `PBEKEYSPEC-CONSTR-01` joins the codes with
no execution path — nothing in api30 withdraws `randomized` — for the same reason
`IVPARAMETERSPEC-CONSTR-00` did.

## What the harness measured

Cumulative against the pre-image over the 82-trace corpus: **58 unchanged, 17 moved, 2 introduced,
5 removed** — the same four numbers as after task 4.5. No trace changed class, and reading that as
"nothing happened" would be wrong twice over.

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `PBEKeySpecSpec-lowiter.txt` | `err1`, `err2`, `err3` | `c1` | moved |
| `PBEKeySpecSpec.txt` | `err2`, `err3`, `c2` | `c1` | moved |
| `PBEKeySpecSpec-salt-only.txt` | `err2`, `c2` | `c1` | moved |
| `PBEKeySpecSpec-forbidden{,3,-then-clear}.txt` | `f1`/`f2` (+`c2`) | same events | unchanged |

The three `moved` rows are task 3.5's fusion. What this task changed is inside the envelope, and
the harness records one envelope per dispatcher call: on all three the B-side report went from
`PBEKEYSPEC-CONSTR-02` to `PBEKEYSPEC-NOBS-00`.

**The `-salt-only` row is the one to read closely.** Before this task, the migrated side accused
the salt (`CONSTR-02`) on a trace that randomises it — because task 4.5 had moved `next2` to the
new store while this file still read the old one. That was the window of finding 11, invisible in
the class column because the file was already accusing for another reason. It closes here.

## Counting the whole `ErrorCollector`

The harness's table is a floor wherever one dispatcher call accuses more than once, which is every
call in this file. Counting the collector instead, over the two snapshots the harness generated:

| construction | A (pre-image) | B (migrated) |
|---|---|---|
| `PBEKeySpec(chars, salt, 1000, 256)`, nothing randomised | **6** — CONSTR-00 `err1`, CONSTR-01 `err2`, CONSTR-02 `err3`, and three ORDER-00 (one per orphan) | **3** — CONSTR-00, NOBS-00, NOBS-01, all at `c1` |
| `PBEKeySpec(chars, salt, 10000, 256)`, nothing randomised | **4** — CONSTR-01, CONSTR-02 and two ORDER-00 | **2** — NOBS-00, NOBS-01 |
| the same with the salt randomised through `nextBytes` | **2** — CONSTR-01 `err2` and its ORDER-00 | **1** — NOBS-00 |
| a conforming construction followed by `clearPassword()` | **5** — CONSTR-01, CONSTR-02, two orphan ORDER-00 and one ORDER-00 at `c2` | **2** — NOBS-00, NOBS-01 |

The third row is the measurement that matters: **one report, not two.** The salt read answers
`SATISFIED`, so what is left is the password read that stands behind no clause. The fourth row is
the `NEGATES` translation running: the withdrawal itself reports nothing, and the ordering report
the pre-image drew at `c2` — because its guarded `c1` had never moved the monitor off `start` — is
gone since task 3.5.

Reproducing (compile against `rvsec/rvsec-mop/target/gh104-classpath.txt`, run once per side with
that side's `work/classes/classes` from the harness scratch the JSON summary names):

```java
// every dispatcher a four-argument construction resolves to on this side:
// c1 alone after the fusion, c1 plus the three twins before it
static void construct(char[] pw, byte[] salt, int iterations, int keyLength, PBEKeySpec spec)
        throws Exception {
    for (Method m : rm.getDeclaredMethods()) {
        if (!m.getName().startsWith("PBEKeySpecSpec_")) continue;
        if (m.getParameterCount() != 5) continue;
        m.invoke(null, pw, salt, iterations, keyLength, spec);
    }
}

byte[] salt = new byte[16];
SecureRandom r = SecureRandom.getInstance("SHA1PRNG");
dispatcher("SecureRandomSpec_g1Event", 2).invoke(null, "SHA1PRNG", r);   // the trace's getInstance
r.nextBytes(salt);
dispatcher("SecureRandomSpec_next2Event", 2).invoke(null, r, salt);      // what marks it randomised
PBEKeySpec spec = new PBEKeySpec(chars, salt, 10000, 256);
construct(chars, salt, 10000, 256, spec);
// then read ErrorCollector.instance().getErrors().size()
```

## The clause this pass finished, and who owns the consequence

Ledger #24 (`PBEKeySpec randomized[salt]`) is dispositioned *wire* at task **5.4**. It is wired
now: the producer is `SecureRandomSpec.next2` writing `RANDOMIZED` at `@match2` (task 4.5), the
consumer is `c1` reading it in its body with an accuser and a code (this task), and the third row
of the count table is the satisfying half measured rather than argued. This is the second time a
pair of file passes closes an edge the plan routed through Group 5 — the first was #12 for task
5.1 — and the consequence is the same one: **task 5.4 must not add a second accuser for the
clause.** The design routes each clause to exactly one accuser. Either 5.4 records #24 as already
wired by mechanism A and moves on, or it re-routes it and takes the accuser out of `c1`.

The same file also holds the other half of a clause nobody can wire: `PBEKEYSPEC-CONSTR-01`/
`NOBS-00` read a `char[]` that only `RandomStringPasswordSpec` could mark, through a chain
(`String.valueOf(Object)` → `toCharArray()`) the harness cannot replay, because its resolver
matches declared parameter types rather than assignability. Task 3.5 measured that and wrote a
trace for it that was removed rather than committed with unresolved lines; nothing here changes it.

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 (`ExecutionContext` mentions) | 20 files | **19** |
| INV-INS-133 (`condition` reads) | 8 | 8 |
| INV-INS-134 (writes off acceptance, no reason) | 25 | **24** |
| accepting-state calls (INV-INS-147) | 22 | **21** |
| predicate sites in the graph | 87 | **86** |
| G-PRED2 findings | 26 | 26 |
| G-ORDER divergences | 4 | 4 |
| structural findings, all gates | 79 | **77** |

`gate_baseline.json` retires two rows (`PBEKeySpecSpec.mop / ExecutionContext` and
`c1/SPECCED_KEY`), and no finding appeared outside the baseline. The file's G-PRED2 row stays:
`SPECCED_KEY` is written and read by nothing, and its consuming rule (`SecretKeyFactory`) has no
`.mop` in the set — ledger #31 records it `unmonitored-consumer` at task 5.10, which is where that
row closes.

**Noticed while regenerating**: `data/jca_android/evidence/gate_baseline_report.md` in HEAD still
carried the counts of two tasks ago (89 sites, INV-INS-130 at 21, INV-INS-134 at 30). The baseline
JSON was current; only the human-readable report had not been rewritten since. It is regenerated
with this task, and the numbers above are the current ones.

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
