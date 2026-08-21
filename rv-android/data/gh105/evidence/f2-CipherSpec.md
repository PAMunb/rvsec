# CipherSpec — the first migrated file (gh105 tasks 4.1 and 4.2)

Three reads leave `condition(...)` for the event body, eleven `ENCRYPTED` writes move to the
two acceptance points the rule names, a twelfth write is deleted, and the accepting-state
bookkeeping goes. This records what each of those did, measured rather than argued, and the two
things the measurement turned up that the plan did not predict.

## What the rule says, and where each site landed

api30 `Cipher.cryptsl` states one key-origin clause and three `encrypted` clauses:

```
REQUIRES  generatedKey[key, part(0,"/",transformation)];              :174
ENSURES   encrypted[pre_ciphertext, pre_plaintext] after updates;     :189
          encrypted[cipherText, plainText];                           :191
          encrypted[cipherBuffer, plainBuffer];                       :193
```

INV-INS-134 names two acceptance points — the `@match` handler, and the states of an `after L`
clause. This automaton's `updates` lead to `s3`, so the file now carries two: `alias match1 =
end` for the two unqualified clauses and `alias match2 = s3` for the `after updates` one. Every
`u*`/`f*` body stages its pair in monitor fields and the handler that runs immediately after the
transition writes it and clears the field; `@fail` clears all four, because a refused transition
means no handler ran and a stale pair must not survive into the next accepted event.

Eleven write sites became two. That is the shape the rule has — three clauses over two
acceptance points — and the per-event rows the `predicate_graph.csv` loses were eleven copies
of one clause, fired before the automaton had accepted anything.

### Two facts measured in the generated monitor, not assumed

Both were checked in the artefact (`MultiSpec_1RuntimeMonitor.java`) before the edit was
written, because the plan's cost estimate for this shape rested on the second one being false:

* **An event body runs before the transition is decided.** `Prop_1_event_u1` executes the body,
  *then* calls `handleEvent`. A write in a body therefore marks a ciphertext for a sequence the
  automaton is about to reject — which is the whole reason INV-INS-134 exists.
* **A state handler fires on every event that lands in its state, not once.**
  `Category_matchN = nextstate == N` is recomputed after every event and the dispatcher calls
  the handler whenever it holds. So `u1; u2` runs the handler twice, each time with the pair its
  own body had just staged, and the "the last pair wins" cost the plan attributed to this shape
  does not exist.

A third fact settled the arity question: `PredicateStore.validateAbsent` is name-only
(`PredicateStore.java:339`), so the `!encrypted[output1, _]` read that task 5.3 wires asks about
position 0 alone. The three `doFinal` overloads that bind no plaintext (`f1`, `f2`, `f3`)
therefore stage the pair with position 1 null rather than being narrowed to arity 1, which would
file one predicate under two shapes.

## What the harness measured

The differential harness records **one** accusing event and **one** envelope per dispatcher
call, so its table is a floor and not a count (the same limitation task 3.6 hit). The counts
below come from reading the whole `ErrorCollector` on both snapshots.

| trace | A (pre-image) | B (migrated) |
|---|---|---|
| `CipherSpec.txt` | **1** — `CIPHER-ORDER-00 ev=f2` | **1** — `CIPHER-NOBS-00 ev=i2` |
| `CipherSpec-update-chain.txt` | **3** — `CIPHER-ORDER-00` at `u1`, `f1`, `f2` | **1** — `CIPHER-NOBS-00 ev=i2` |
| `CipherSpec-unsafe.txt` | **1** — `CIPHER-ORDER-00 ev=f2` | **4** — `CIPHER-ALG-01 ev=i2 val='DES'`, `CIPHER-NOBS-00 ev=i2`, and `CIPHER-ORDER-00` at `i2` and `f2` |

The first two rows are the repair stated in one number. A guard read compiles to
`if (!(guard)) return false;` ahead of both the body and `handleEvent`, so a key whose producer
the monitor never saw dropped the `init` out of the automaton and every later call in the
program was accused of a wrong call sequence — three such reports on a five-call program. With
the read in the body the sequence is accepted and the one report is about what was actually
observed: no generator of this key.

Set-wide, against the pre-image over the whole 79-trace corpus: **58 unchanged, 17 moved, 4
removed, 0 introduced**.

## Finding: the `unsafeAlg` sink, recorded and not repaired

The third row is the one where the migrated set reports more, and the cause is older than this
task. `g3` — `getInstance` with a transformation the table rejects — moves the automaton to
`unsafeAlg`, a state whose only outgoing transitions are more `getInstance` calls. So *any*
subsequent legitimate call draws `CIPHER-ORDER-00`. api30 orders `Gets, Inits+, …` with
`Gets := g1 | g2` and states the transformation under CONSTRAINTS, so `getInstance("DES");
init(1, key)` is an ordering the rule **accepts**: this is the same defect task 3.2 established
for the three `getInstance` twins, where an algorithm was made to govern a transition it has no
business governing.

Two of `-unsafe`'s four B-side reports are that sink. What this task changed is only that the
sink is now reachable: the predicate guard used to suppress `i2` before `handleEvent`, so the
init never took a transition and never failed. The other two reports are true and were being
suppressed with it — `CIPHER-ALG-01 val='DES'` is the accusation the file exists to make, and it
was silent on the pre-image for exactly the reason task 3.2 measured on
`TrustManagerFactorySpec`: an event that leaves the automaton takes the `@fail` path instead of
the body that carries the check.

`CipherSpec.g3` is not an orphan — it is in the `fsm` — so G-ACC never saw it and no task of
Groups 3 to 6 reaches it. Repairing it means fusing it into `g1` and deleting `unsafeAlg`, which
changes what the set accuses rather than where it accuses from. **Decision: record it here and
leave it**, the same disposition the `g2` guards of `TrustManagerFactorySpec`, `SignatureSpec`
and `SSLContextSpec` received. It deserves a task of its own whenever someone decides to move
it, and G-ORDER already reports `CipherSpec` as divergent (on a different witness, `f2` alone).

## Finding: three corpus traces named a program that does not compile

`CipherSpec.txt`, `CipherSpec-unsafe.txt` and `CipherSpec-guard-on-field.txt` all wrote
`c.init(1, null)`. That line does not compile:

```
error: reference to init is ambiguous
    c.init(1, null);
  both method init(int,Key) in Cipher and method init(int,Certificate) in Cipher match
```

The harness matches a pointcut against the argument's runtime type and a `null` fits any
reference parameter, so it dispatched to `i1` **and** `i2`. The pre-image hid the second
dispatch because `i2`'s guard returned false before `handleEvent`; with the read in the body the
second dispatch became visible, and on `CipherSpec.txt` it produced an accusation the pre-image
did not have — the harness's only `introduced` verdict in this group.

That verdict was about the trace, not about the specification: in a woven program the call
site's resolved signature picks exactly one overload, which is why both weavers gate the
signature exactly. `CipherSpec.txt` and `CipherSpec-unsafe.txt` now bind a key and name the
`init(int, Key)` overload; both are about the transformation and the key was incidental.
`CipherSpec-guard-on-field.txt` is left alone: it is gh104's cited evidence for `i1`, and the
trace grammar has no way to name the `Certificate` overload — its arguments are literals,
integers, `null` and bound names, and a `Certificate` cannot be constructed from those. Its
extra `i2` ordering report is the sink above, seen through the same ambiguity, and is recorded
rather than repaired for the same reason.

## What this task could not measure

* **The write relocation has no behavioural delta yet.** `ENCRYPTED` is read by no specification
  of any of the five sets until task 5.3 wires `Mac`'s two `!encrypted` clauses, so the eleven
  relocated writes are verified structurally — `predicate_graph.csv` files both sites as
  `write:acceptance`, and the generated handlers were read in the artefact — and not by an
  accusation. This is expected: it is the F2 side of the F2→F3 window.
* **`CIPHER-CONSTR-00` is unreachable today.** At arity 1 with no value positions a recorded
  tuple always matches, so `validate` can only answer `VIOLATED` through `negate`, and nothing
  negates a key-origin predicate. Task 5.6 raises this read to the rule's arity 2
  (`generatedKey[key, part(0,"/",transformation)]`), at which point a key generated for one
  transformation and used with another is a mismatch and the code fires. It is written now
  because INV-INS-133 requires the failed read and the not-observed read to be separate codes,
  and a two-valued site would have to be rewritten at 5.6 anyway. It joins
  `PBEKEYSPEC-CONSTR-01` and `SECRETKEYSPEC-CONSTR-01` as a code with no execution path today,
  for a different reason from either.
* **The satisfy side of the pair does not exist inside the window.** No producer writes to the
  new store until Group 5, so every trace answers `NOT_OBSERVED`. The pairs of INV-INS-144 that
  assert `SATISFIED`/`VIOLATED` land per chain in Group 5, as design D-8 declares.

## The *not observed* code family (task 4.2)

`CIPHER-NOBS-00` is the first member of a family of its own: `codes.csv` files it under
`site_kind = NOBS`, distinct from the `CONSTR` violations. `ErrorType` stays
`UnsatisfiedConstraint` for both — the enum's own javadoc records why a second name for one
condition would split the vocabulary — so what tells them apart downstream is the code, which is
what `errors.csv` carries.

`gh104_message_gate.py` gained a fifth property to hold the mapping in both directions: a report
site admitted by an equality test on `PredicateVerdict.NOT_OBSERVED` must carry a code of the
`NOBS` family, and one admitted by a `VIOLATED` test must not. Only the equality form is read —
`v != PredicateVerdict.SATISFIED` names a verdict without saying which branch the site is, and a
gate that guessed there would report a finding the reader has to dismiss. A set with no
three-valued read reports the property as skipped, with the reason, rather than green by vacuity.

## Reproducing

```bash
export RVSEC_HOME=.../rvsec
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android \
    --b $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f2
```

The JSON summary at the top of that output names a `scratch` directory holding both generated
snapshots. The count probe compiles against the cached test classpath
(`rvsec/rvsec-mop/target/gh104-classpath.txt`) and runs once per side with that side's
`work/classes/classes` as its second argument: it loads `mop.MultiSpec_1RuntimeMonitor` through
a fresh loader, calls the `CipherSpec_<event>Event` dispatchers in the order the trace names
them — firing every advice a line matches, as the harness does, so `c.doFinal()` calls both `f1`
and `f2` — and prints the whole `ErrorCollector` between traces instead of one envelope per
call.
