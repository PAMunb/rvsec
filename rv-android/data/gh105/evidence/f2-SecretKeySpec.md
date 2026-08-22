# F2 — `SecretKeySpec` (task 4.12): the last guard read, and a window that costs nothing

**Date**: 2026-08-21 · **Change**: gh105-predicate-wiring · **Task**: 4.12
**File**: `rvsec/rvsec-mop/src/main/resources/jca_android/SecretKeySpec.mop`
**Oracle**: `MetaCrySL/generated/api30/SecretKey.cryptsl`

The set's **last** read inside `condition(...)`. After this pass INV-INS-133 is zero and
INV-INS-130 counts thirteen files instead of fourteen.

## What the file is, and what the rule says

```java
SecretKeySpec(SecretKey secretKey) {
   event e1 after(SecretKey secretKey) returning(byte[] key):
      call(public byte[] SecretKey.getEncoded()) && target(secretKey) &&
      condition(ExecutionContext.instance().validate(Property.GENERATED_KEY, secretKey)) {
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, key);
   }
   ere : e1*
   @match { /* empty */ }
}
```

```
EVENTS     d: destroy();   ge: keyMaterial = getEncoded();
ORDER      ge*, d?
ENSURES    preparedKeyMaterial[keyMaterial] after ge;
NEGATES    generatedKey[this, _] after d;
```

One event, one read, one write, no accuser, no `codes.csv` line. The rule states an `ENSURES`
and **no `REQUIRES` section at all**, so nothing in this file translates a constraint — which is
what makes the read a `propagation` record rather than an accuser, and what made the disposition
of the read a real question rather than a transcription.

## The six trees, measured before the edit

Probe over the whole `ErrorCollector`, one process per configuration, both stores and the error
sink reset between them. Three trees are real (the pre-image, the starting tree, and — added
afterwards — the migrated tree); three are written inline between the starting tree's own
dispatchers, which is how a disposition that does not exist yet gets a column (learning 51).

| configuration | pre-image | starting tree | **guarded** | unguarded | deleted | guarded, after 4.14 | migrated tree (real) |
|---|---|---|---|---|---|---|---|
| **A** `KeyGenerator` → `getEncoded` → `IvParameterSpec` | 0 | 1 | **1** | 0 | 1 | **0** | 1 |
| **B** randomised material → `SecretKeySpec` → `getEncoded` → `IvParameterSpec` | 0 | 1 | **0** | 0 | 1 | 0 | 0 |
| **C** control: a `byte[]` of no observed origin | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| **D** control: hard-coded `SecretKeySpec` → `getEncoded` → `IvParameterSpec` | 4 | 2 | **2** | **1** | 2 | 2 | 2 |
| **E** the committed trace: `keygen` → `getEncoded`, no consumer | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The last column was measured after the edit and reproduces the simulation configuration by
configuration, which is the audit of the method as much as of the pass.

The probe is auditable in both directions the corollary of learning 27 asks for: **C** and **D**
accuse in every column, and **B** reaches zero in exactly one. The dispatchers it fired are
listed by the probe itself and correspond to the pointcuts of `KeyGeneratorSpec.g1/init/gk1`,
`SecureRandomSpec.g1/next2`, `SecretKeySpecSpec.c1` (and `c3` on the pre-image, where the twin
still exists), `SecretKeySpec.e1` and `IvParameterSpecSpec.c1` (`c3` likewise).

## The three decisions, and the number that decided each

### 1. The read stays, governing the write (researcher, 2026-08-21)

api30 states the `ENSURES` with no `REQUIRES`, so a literal translation deletes the read and
marks every encoding. Column *unguarded* is what that costs: **row D goes from 2 reports to 1**.
A key whose material is hard-coded is still accused at its construction, and the IV built from
its encoding is not accused at all — the set trades a report about a real defect for a chain it
closed one call earlier. Row A shows what it would have bought: the `KeyGenerator` chain closes
immediately instead of at 4.14.

The third option — delete both sites, as task 4.9 did to `MacSpec` and task 4.11 to
`RandomStringPassword` — is measured in column *deleted*: nothing closes. It does not apply here
for a reason the two earlier files make precise. `MacSpec`'s reads translated no clause **and fed
no write**; `RandomStringPassword`'s reads fed writes whose conversion **did not carry the
predicate**. This read translates no clause either, but the write it feeds does carry, and that is
the second condition of the delta's `propagation` rule.

That the write carries was measured rather than assumed, which is the whole lesson of 4.11:

```
first  = key.getEncoded();
second = key.getEncoded();
first == second        -> false        // a fresh clone on every call
first == the material  -> false
Arrays.equals          -> true
ensure(first), validate(second)  -> NOT_OBSERVED
```

`getEncoded()` copies. A store keyed on object identity therefore cannot see the material through
the copy, and no other site of the set writes about the returned array. This event is not a
convenience over the chain — it is the only thing in the set that bridges it.

### 2. The `NEGATES` with no site is recorded, not invented (researcher, 2026-08-21)

`generatedKey[this, _] after d` is the second of the oracle's two `NEGATES` clauses (INV-INS-142)
and the file declares no event for `destroy()`. Measured:

```
javax.crypto.spec.SecretKeySpec              -> threw javax.security.auth.DestroyFailedException
KeyGenerator.generateKey() (same class)      -> threw javax.security.auth.DestroyFailedException
```

Both `SecretKey` implementations this set can observe refuse to be destroyed, so an
`after ... returning` advice over `destroy()` would have **no execution path** even if the event
were declared — the position `SECRETKEYSPEC-CONSTR-01` is already in (task 4.10). Declaring it
would also add a symbol to an automaton whose `ORDER` mapping task 7.1 owns: `SecretKeySpec` is
one of the thirteen still unmapped, so G-ORDER skips it and would not have checked the addition.

The record itself belongs to **task 6.5**, which design D-3 already routes it to as `unclosable`.
This pass did not write it in two places; it wrote the measurement into 6.5's text so the next
session does not re-derive it (finding 25).

### 3. The `randomized` × `preparedKeyMaterial` conflation is recorded, not repaired

The rule names `preparedKeyMaterial` on both sides of the copy; the seed writes `randomized`.
That is ledger clause **#32**, recorded at the reading end by task 4.10 (`SecretKeySpecSpec.c1`)
and undone at task 5.10 together with 6.1. Renaming it here alone would leave this producer
writing a predicate none of the seven migrated readers of `randomized` over a `byte[]` asks for —
measured, column B would go back from 0 to 1, in the pass whose job is to close it.

Arity needs no exception, unlike task 4.10's write: the clause is one-place and the readers read
one-place.

## Where the write goes, and why both routes agree

INV-INS-134 admits two acceptance points: the `@match` handler, or the states of an `after L`
clause. This clause carries `after ge`, so the two could differ. Read off the generated monitor,
they do not:

```java
static final int Prop_1_transition_e1[] = {0, 1};
this.SecretKeySpecMonitor_Prop_1_Category_match = nextstate == 0;
```

From state 0 the event returns to state 0, the match category holds there, and state 1 is never
entered. The states after `ge` and the accepting states are the same single state, and `@match`
is both. The handler runs after **every** `e1`, which is what a clause over a per-call copy needs.

A handler sees no event parameter, so the bytes reach it through a staged field — the shape
`SecureRandomSpec.next2` already uses (task 4.5). The field is cleared when consumed, so a call
whose key origin was not observed leaves no marking behind for the next one.

## The window this pass opens, stated in full

The read is of `generatedKey`. Its three producers:

| producer | store, after this pass | task |
|---|---|---|
| `SecretKeySpecSpec.mop:153` | new | ✅ 4.10 |
| `KeyGeneratorSpec.mop:80` | **old** | 4.14 |
| `KeyStoreSpec.mop:83` | **old** | 4.14 |

Moving the read closes the first chain and opens a window against the other two, and the window
propagates: a key generated by `KeyGenerator` stops marking `randomized` on the bytes it returns,
and seven sites read `randomized` over a `byte[]`.

**Measured, the window changes no report.** Row A is 1 before and 1 after. The reason is not that
the window is small but that the write it suppresses was already dead: every reader of
`randomized` moved to the new store by task 4.8, so the old-store write at this site has had no
reader since task 4.4. Before the pass the read succeeded and wrote where nobody looks; after it,
the read fails and writes nothing. The same count, a different reason — and column *after 4.14*
shows the row going to 0 once the producers move.

This is finding 34 in a new shape. Neither side of the harness contains the window: on the
pre-image both ends are on the old store and the chain works; on the migrated tree the chain will
work again after 4.14. It exists only in the intermediate trees, and only a probe over the whole
`ErrorCollector` sees it.

## The harness

97 traces (94 committed plus the three this pass writes), against
`backup/gh105-preimage/jca_android`, cumulative:

```
unchanged 62 · moved 19 · introduced 10 · removed 6
```

`git diff --stat -- data/gh105/evidence/harness/` — **one report of the twenty-three changed**,
this file's own. Nothing else in the set moved.

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpec-encoded-iv.txt` | unchanged | — | — |
| `SecretKeySpec-hardcoded-iv.txt` | moved | `SecretKeySpecSpec.c3`, `IvParameterSpecSpec.c3` | `SecretKeySpecSpec.c1`, `IvParameterSpecSpec.c1` |
| `SecretKeySpec-keygen-iv.txt` | introduced | — | `IvParameterSpecSpec.c1` |
| `SecretKeySpec.txt` | unchanged | — | — |

Three things this table does not say, and the evidence has to.

`-encoded-iv` is classed **unchanged** and it is the trace that measures what the pass buys. It
is silent on the pre-image because both ends were on the old store there, and silent on the
migrated tree because both ends are on the new one; it was accused only on the **starting tree**,
which the harness does not contain. The closure is in column B of the probe table, not here.

`-keygen-iv` is the **tenth** `introduced` row of the change. The other nine are deliberate
repairs. This one is a window, and it closes at 4.14.

`-hardcoded-iv` is classed **moved** for a reason that belongs to Group 3, not to this pass: the
orphan twins `c3` were fused into `c1` at tasks 3.3 and 3.4, so the same two accusations arrive
under different event names and codes.

All three replay with `unresolved: []` on **three** snapshots — the harness's `a` and `b`, and
`results/gh101_group8_jca_frozen_control/monitors`, which is what `TraceRunnerTest` replays
against (learning 52).

## Gates

| gate | before | after |
|---|---|---|
| `read:condition-guard` (INV-INS-133) | 1 | **0** |
| `read:body` | 13 | 14 |
| `write:body` | 23 | 22 |
| `write:acceptance` | 11 | 12 |
| bookkeeping (INV-INS-147) | 17 | 17 |
| `remove:fail` / `negate:body` | 7 / 1 | 7 / 1 |
| INV-INS-130 files | 14 | **13** |
| gh105 structural findings | 58 | **55** (G-PRED2 23, INV-INS-130 13, INV-INS-134 19) |
| G-ORDER divergences | 4 | 4 (unchanged; `SecretKeySpec` is skipped, unmapped, owned by 7.1) |

`gh105_gate_baseline.py` reports three repairs and no finding outside the recorded baseline:
INV-INS-130, INV-INS-133 and INV-INS-134, all on this file. `gh104_mop_lint.py` and
`gh104_message_gate.py` green. `gh104_gates.py` over the generated monitor is byte-identical to
the starting tree's — `G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 · G-ERE 0 · G-CONF 0
· G-PRED 10` on both. `codes.csv` untouched: a propagation site never earns an accuser, and this
file has no code to move.

Six divergence hunks recorded, all new — this is the file's first divergence from the seed. The
94 assertions of the four gate suites pass.

## A finding this pass owes the record

**The migration narrows what counts as "the same key", and this file is where that could matter.**
The old substrate is a `HashSet` and matches with `equals`; `javax.crypto.spec.SecretKeySpec`
overrides `equals` to compare algorithm and bytes. The new store keys the binding on identity.

```
one.equals(two)                 -> true      // distinct objects, same material and algorithm
old store, equal-but-distinct   -> true
new store, equal-but-distinct   -> NOT_OBSERVED
```

So two `SecretKeySpec` built from the same material used to share `generatedKey` and no longer
do. This is finding 38's sibling — there it was `Integer` boxes and the narrowing killed a bridge;
here the narrowing is arguably the repair, since a predicate about one key object should not
attach to another that merely holds the same bytes. It changes nothing measured: the producer
ensures on the object the consumer reads. It is recorded because it is a property of the store
that every migrated file inherits silently, and this is the first file whose bound object is a
class with a value-based `equals`.

## What this pass did not touch

The two imports this file never used (`javax.crypto.KeyGenerator`,
`javax.crypto.spec.SecretKeySpec`) are left alone: they are the seed's, not this migration's, and
removing them would put a hunk with no measurement behind it inside a substrate pass.
`order_alphabet_map.csv` is unchanged — the automaton did not move, and `SecretKeySpec` is one of
the thirteen specifications task 7.1 still has to map.
