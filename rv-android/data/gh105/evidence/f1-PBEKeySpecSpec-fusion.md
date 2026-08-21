# PBEKeySpecSpec — the three twins, the two absorptions, the residue (gh105 task 3.5)

This file carried five of the seventeen orphan accusers, more than any other, and
they needed both treatments. What follows is what each one cost and what the repair
left behind.

## The three twins: four reports become one per violated clause

`err1`, `err2` and `err3` matched the same construction as `c1` and each negated one
conjunct of its three-part guard. They fused into `c1`'s body as three independent
tests, one report per violated clause.

Measured against the pre-image (`gh104_diff_harness.py`, group `f1`):

| trace | what it breaks | A (pre-image) | B (fused) |
|---|---|---|---|
| `PBEKeySpecSpec-lowiter.txt` | all three clauses | `err1`, `err2`, `err3` — three constraint reports, and each event's all-`fail` transition row adds an ordering report | `c1` — the same three constraint reports, no ordering report |
| `PBEKeySpecSpec.txt` | password and salt | `err2`, `err3`, and `c2` — the `clearPassword()` fires from `start`, because the guarded `c1` never moved the monitor | `c1` alone |
| `PBEKeySpecSpec-salt-only.txt` | password only | `err2`, then `c2` for the same reason | `c1` alone |

The last row is the one that shows the decomposition working: one clause broken, one
report, and the `clearPassword()` that follows is no longer accused of being out of
order — because `c1` now takes its transition whatever the arguments were.

## The two absorptions, and why they mattered more than the noise

`f1` and `f2` accuse constructors api30's FORBIDDEN clause turns down outright, so
they are absorbed, not fused (INV-INS-135). They enter the `ere` through Kleene
groups: `(f1 | f2)* c1 (f1 | f2)* c2 (f1 | f2)*`, the idiom the tree already uses
(`g3* g1 | g3* g2` in the seed's CipherSpec and MessageDigestSpec).

Neither event binds the specification parameter — `event f1 after(char[] password)`
names no `PBEKeySpec` — so the generator dispatches them to the whole monitor set
rather than to one instance:

```java
public static final void PBEKeySpecSpec_f1Event(char[] password) {
    ...
    PBEKeySpecSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1();
    stateTransitionedSet.event_f1(password);       // every live monitor, not one
}
```

Outside the automaton `f1` carried an all-`fail` transition row, so **one forbidden
construction anywhere in a program pushed every live PBEKeySpec monitor into `fail`**
— accusing objects that had done nothing wrong. That is the part the absorption fixes
that a per-instance reading of the same defect would have missed.

| trace | A (pre-image) | B (absorbed) |
|---|---|---|
| `PBEKeySpecSpec-forbidden.txt` | **2** reports — `PBEKEYSPEC-ORDER-00 ev=f1` beside `PBEKEYSPEC-FORB-00 ev=f1` | **1** — `PBEKEYSPEC-FORB-00 ev=f1` |

The counts come from the whole `ErrorCollector`, not from the harness table: the
harness records one envelope per dispatcher call and both of A's reports come from
the same call to `PBEKeySpecSpec_f1Event`, so it classifies this trace `unchanged`
and shows whichever report the set iterated first. The method and the program are in
`data/gh105/evidence/f1-IvParameterSpec-report-count.md`. The same caveat applies to
`PBEKeySpecSpec-forbidden-then-clear.txt` below, which the harness also calls
`unchanged` while the report at `f1` changes from an ordering complaint to the
FORBIDDEN accusation the rule states.

## The residue, declared

Absorbing a forbidden constructor by a Kleene group silences the ordering report at
the forbidden call. It does not silence the **obligatory call that must follow it**.
`PBEKeySpecSpec-forbidden-then-clear.txt` builds a PBEKeySpec with the forbidden
one-argument constructor and then calls `clearPassword()`:

| side | reports |
|---|---|
| A | `PBEKEYSPEC-ORDER-00 ev=f1` **and** `PBEKEYSPEC-ORDER-00 ev=c2` |
| B | `PBEKEYSPEC-FORB-00 ev=f1` **and** `PBEKEYSPEC-ORDER-00 ev=c2` |

The `c2` report survives, because `c2` still reaches the automaton from a state where
`c1` never happened — which is what the rule's `ORDER c1, cP` says. Silencing it
would mean modelling a forbidden constructor as an alternative opening of the
ordering, the opposite of what FORBIDDEN states. This is the `FEN-PBK-RESIDUO` case
the Phase-0 plan named and the delta's Kleene-prefix residue record.

## Two clauses nothing can satisfy, for different reasons

**`PBEKEYSPEC-CONSTR-01` stands behind no clause of the rule.** api30 REQUIRES
`randomized[salt]` and says nothing about the password; the CONSTRAINTS clause that
does mention it is `neverTypeOf(password, java.lang.String)`, a different claim. This
was the standing `gate_allowlist.csv` finding against `err2`. Deleting `err2` retires
the row — the finding was about an orphan and there is no orphan any more — but the
accusation itself survives inside `c1`, unrepaired: dropping it or moving it to the
salt changes what the set accuses, which this task does not do.

**No trace can satisfy it either.** The only chain in the set that marks a `char[]`
randomised is `RandomStringPasswordSpec`: `String.valueOf(obj)` on a randomised
object gives a randomised `String`, and `String.toCharArray()` on that gives a
randomised `char[]`. The harness cannot replay it — a trace line
`String.valueOf(n) -> pw` resolves against no pointcut, because the advice declares
`args(Object)` and the resolver matches declared parameter types rather than
assignability (the `Object`-idiom subtlety INV-INS-136(c) names from the other
direction). A trace attempting the full chain was written, measured, and removed
rather than committed with two unresolved lines; `PBEKeySpecSpec-salt-only.txt`
carries the satisfying half for the two clauses that *can* be satisfied —
`iterationCount >= 10000` and `randomized[salt]` — and isolates CONSTR-01 as the only
remaining report. That is the pair evidence INV-INS-144 asks for, with the third
clause's satisfying side declared impossible rather than assumed.
