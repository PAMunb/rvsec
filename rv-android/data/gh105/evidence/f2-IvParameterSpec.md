# IvParameterSpec — the file pass that moves nothing (gh105 task 4.4)

Two reads and one write change substrate, and none of the three changes place. Task 3.3 had
already brought both reads into their event bodies when it fused the twins, and `preparedIV[this]`
is unqualified, so the rule's acceptance point is the accepting state and the write already sat in
`@match`. What is left for the F2 pass is the part the placement census cannot see: the boolean
becomes a three-valued verdict, the substrate becomes the one the monitors key like, and the
accepting-state bookkeeping goes.

This is worth recording precisely, because "no placement moved" reads at a glance like "nothing
happened", and the harness says otherwise: two traces that were silent on both sides now accuse.

## What the rule says, and where each site landed

api30 `IvParameterSpec.cryptsl` is one of the smallest rules in the set:

```
EVENTS    Cons := cons1 | cons2;                  :19
ORDER     Cons                                    :23
REQUIRES  randomized[iv];                         :28
ENSURES   preparedIV[this];                       :33
```

| site | before | after | placed by |
|---|---|---|---|
| `c1` read | `read:body`, boolean, `ExecutionContext` | `read:body`, three-valued, `PredicateStore` | task 3.3 |
| `c2` read | `read:body`, boolean, `ExecutionContext` | `read:body`, three-valued, `PredicateStore` | task 3.3 |
| `@match` write | `write:acceptance`, `ExecutionContext` | `write:acceptance`, `PredicateStore` | the seed |
| `@match` bookkeeping | `bookkeeping:match` | deleted | INV-INS-147 |

One clause, two constructors that bind it, two pairs of codes. A code names a site and not a
clause — `codes.csv` is keyed by event and file line — so the report has to say which constructor
it is about, and `IVPARAMETERSPEC-{CONSTR,NOBS}-00` belong to `c1`, `-01` to `c2`.

## What the harness measured

Cumulative against the pre-image over the 79-trace corpus: **56 unchanged, 17 moved, 2
introduced, 4 removed** (before this task: 58 / 17 / 0 / 4). Both new verdicts are this file's,
and `f2-IvParameterSpecSpec.md` is the only per-spec report the run rewrote.

| trace | A (pre-image) | B (migrated) | class |
|---|---|---|---|
| `IvParameterSpecSpec.txt` | — | `IVPARAMETERSPEC-NOBS-00 ev=c1` | **introduced** |
| `IvParameterSpecSpec-unrandomised.txt` | `IVPARAMETERSPEC-CONSTR-00 ev=c3` | `IVPARAMETERSPEC-NOBS-00 ev=c1` | moved |
| `IvParameterSpecSpec-offset.txt` | — | `IVPARAMETERSPEC-NOBS-01 ev=c2` | **introduced** |
| `IvParameterSpecSpec-offset-unrandomised.txt` | `IVPARAMETERSPEC-CONSTR-01 ev=c4` | `IVPARAMETERSPEC-NOBS-01 ev=c2` | moved |

The two `moved` rows are task 3.3's fusion, unchanged by this task except in the code the surviving
event emits: the violate half now says *not observed* rather than *violated*, which is what it
always meant. The seed's `CONSTR-00` message read "was not observed to come from a randomized
source" — the wording was already the third value; only the code was not.

**The two `introduced` rows are the F2 window, and they are the satisfy half of the pair.** Both
traces randomise the array through `SecureRandom.nextBytes(iv)` before the constructor, and on the
pre-image that satisfied the read because `SecureRandomSpec` writes `RANDOMIZED` to
`ExecutionContext`. The migrated `IvParameterSpec` reads `PredicateStore`, which no producer writes
to yet, so the conforming program is answered `NOT_OBSERVED`. Design D-8 declares exactly this:
inside the F2 window a read has no producer and the satisfy side is impossible, so an F2 pair
asserts `NOT_OBSERVED` on both halves. It is stated here as a measurement rather than assumed —
the pair is committed with the verdicts it actually produced.

## The window for this chain closes at 4.5, not at 5.1

`SecureRandomSpec.next2` (`SecureRandomSpec.mop:131-136`) marks the `byte[]` that
`nextBytes(byte[])` fills, and task 4.5 migrates that site to the new store. The traces above bind
the same array through both calls (`bind iv = bytes(16)`), and the store keys the binding by
identity, so from 4.5 onward `IvParameterSpecSpec.txt` and `-offset.txt` go silent again and the
two `introduced` verdicts retire. That is the whole of the F2 window for this chain: two tasks
wide, not a group wide.

**This has a consequence task 5.1 owns.** Ledger #12 (`IvParameterSpec randomized[iv]`) is
dispositioned *wire — junction (pilot chain)*, and #9 (`Cipher {CBC,…} && encmode==1 =>
preparedIV[params]`) with it. But the pair 4.4 + 4.5 wires #12 by mechanism A, the store, as a side
effect of two file passes that were never about the chain. If 5.1 then wires #12 inside
`IvChainJunction.mop` as well, one clause has two accusers, which the design forbids — the ledger
routes each clause to exactly one. The disposition is not settled here: `predicate_graph.csv`
records `mechanism=store` for both reads because that is what the artefact does, and 5.1 chooses
between keeping the store read and narrowing the junction to #9, or moving #12 into the junction
and dropping the reads' accusers (researcher decision, 2026-08-21: the graph describes the
artefact, not the plan).

## The decision this task had to make

**What `NOT_OBSERVED` does with the `ENSURES` write.** The seed bound `spec` only in the `else` of
a boolean, so the constructor left `preparedIV` behind only when the read succeeded. With three
values that branch splits, and the third value could reasonably go either way:

* **preserve the boolean literally** — only `SATISFIED` prepares; or
* **degrade to silence** — `SATISFIED` and `NOT_OBSERVED` prepare, only `VIOLATED` does not, so an
  unobserved randomisation costs one report here instead of cascading into a second one at the
  consumer. Design D-4 argues that shape for the static oracle's analogue: an analysis that cannot
  see a value must not accuse on it.

Measured before choosing: **the two are indistinguishable on this set today.** `PREPARED_IV` is
written in three of the five sets (`jca/IvParameterSpec.mop:66`,
`jca_android/IvParameterSpec.mop:138`, `jca_android_bug_predicate/IvParameterSpec.mop:74`) and read
in exactly one place in any of them — `jca_android_bug_predicate/CipherSpec.mop:84`, in the set the
2026-08-08 audit failed 22/22 and which is archived as a record, not a seed. No live specification
reads it, and the planned reader is a junction, which consults the parametric monitor and not the
store. The cascade the second option exists to prevent has nothing to cascade through.

Chosen (researcher, 2026-08-21): **preserve the boolean literally.** A behavioural change with no
measurement able to decide it does not belong in a substrate migration; the alternative is recorded
in the `.mop` comment and in `divergence_record.csv` for whoever gives `PREPARED_IV` a store
reader.

## What this task could not measure

* **`IVPARAMETERSPEC-CONSTR-00` and `-01` have no execution path, and will not get one from this
  oracle.** `VIOLATED` requires positive evidence, which at arity 1 with no value positions can
  only come from `negate` — and api30 has exactly two `NEGATES` clauses,
  `SecretKey: generatedKey[this,_] after d` and `PBEKeySpec: speccedKey[this,_] after cP`. Neither
  withdraws `randomized`. The codes are written because INV-INS-133 requires the failed read and
  the not-observed read to carry distinct codes, and a two-valued site would be a site that cannot
  say which of the two it means. This is a stronger unreachability than `CIPHER-CONSTR-00`'s, which
  task 5.6 makes reachable by raising that read to the rule's arity 2; there is no arity here to
  raise. They join `PBEKEYSPEC-CONSTR-01` and `SECRETKEYSPEC-CONSTR-01` as codes with no execution
  path, for a third distinct reason.
* **The write relocation has no behavioural delta, because there was no relocation.** The write
  was already at the acceptance point, and nothing reads `PREPARED_IV`. It is verified structurally
  — `predicate_graph.csv` files it `write:acceptance` with its clause pointer — and not by an
  accusation.
* **The offset/length half of `c2` is still unreachable.** Task 3.3 measured it: the advice is
  `after … returning` and the constructor throws on each of the three conditions before it can
  return (JDK 21 `java.base/javax/crypto/spec/IvParameterSpec.java:75-91`), with the ART/libcore
  caveat that audit ALFA-IVP-02 recorded. This task did not re-measure it and did not change it.

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 (`ExecutionContext` mentions) | 22 files | **21** |
| INV-INS-133 (`condition` reads) | 8 | 8 |
| INV-INS-134 (writes off acceptance) | 30 | 30 |
| accepting-state calls (INV-INS-147) | 24 | **23** |
| predicate sites in the graph | 90 | **89** |
| G-PRED2 findings | 26 | 26 |
| G-ORDER divergences | 4 | 4 |

`gate_baseline.json` retires one row (`IvParameterSpec.mop / ExecutionContext`). The file's
G-PRED2 row stays: `PREPARED_IV` is written and read by nothing until its clause is wired.

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

The JSON summary is at the top of that output, not the bottom. No `ErrorCollector` count probe was
needed here: each constructor emits at most one report (`VIOLATED` exclusive-or `NOT_OBSERVED`),
and both events are in the `ere`, so no `@fail` fires alongside — the harness's one-envelope-per-
dispatcher-call floor is the exact count for this file.
