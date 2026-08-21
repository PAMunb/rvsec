# The 17 orphan accusers, one row each (gh105 Group 3, closed by task 3.7)

An orphan accuser is an event the generator weaves and dispatches but that the
specification's own automaton never names. The generator gives such an event a
transition row that sends every state to the fail state, so it fires the `@fail`
handler on a call the ordering does not judge: the set reports
`InvalidSequenceOfMethodCalls` about a sequence the rule accepts, and — where the
handler carries `__RESET` — leaves the monitor somewhere the *next* call is not
declared either, so the real accusation in that call's body is never reached.

`jca_android` carried 17 of them, over 9 of its 23 specifications. This is the
ledger of what happened to each, with the measurement beside it. Nothing here is
argued from the source alone: every row was replayed through both snapshots by
`gh104_diff_harness.py`, `--a backup/gh105-preimage/jca_android` against the
working set, and the rows whose two reports come from one dispatcher call were
counted again by reading the whole `ErrorCollector`, because the harness records
one accusing event per call and is therefore a floor.

## The ledger

| # | orphan | treatment | task | trace that exercises it | measured |
|---|---|---|---|---|---|
| 1 | `SecureRandomSpec.c3` | fused → `c2` | 3.1 | `-unrandomised-constructor` | `removed`: the twin accused nothing of its own |
| 2 | `SecureRandomSpec.setSeed3` | fused → `setSeed2` | 3.1 | `-unrandomised-seed` | `moved`: `setSeed3` → `setSeed2`, code kept |
| 3 | `SecureRandomSpec.g4` | absorbed (self-loops, ORDER-unmapped) | 3.1 | `-nativeprng` | `unchanged`: the algorithm report survives the absorption |
| 4 | `TrustManagerFactorySpec.g3` | fused → `g1` | 3.2 | `-sunx509` | 2 `ORDER-00` and no algorithm report → 1 `ALG-00 val='SunX509'` |
| 5 | `IvParameterSpec.c3` | fused → `c1` | 3.3 | `-unrandomised` | 2 → 1 by report count (`CONSTR-00` + `ORDER-00` → `CONSTR-00`) |
| 6 | `IvParameterSpec.c4` | fused → `c2` | 3.3 | `-offset-unrandomised` | 2 → 1 by report count |
| 7 | `SecretKeySpecSpec.c3` | fused → `c1` | 3.4 | `-badalg` | 2 → 1 by report count |
| 8 | `SecretKeySpecSpec.c4` | fused → `c2` | 3.4 | — | the clause is unreachable in `after ... returning`; declared and measured |
| 9 | `PBEKeySpecSpec.err1` | fused → `c1` (same arrow) | 3.5 | `-lowiter` | three constraint reports kept, one ordering report removed |
| 10 | `PBEKeySpecSpec.err2` | fused → `c1` (same arrow) | 3.5 | `-salt-only`, base | `moved`; the guarded `c1` had left the monitor at `start`, so `c2` fired too |
| 11 | `PBEKeySpecSpec.err3` | fused → `c1` (same arrow) | 3.5 | base trace | same |
| 12 | `PBEKeySpecSpec.f1` | absorbed (Kleene prefix, ORDER-unmapped) | 3.5 | `-forbidden` | 2 → 1: `FORB-00` kept, `ORDER-00` removed |
| 13 | `PBEKeySpecSpec.f2` | absorbed (Kleene prefix, ORDER-unmapped) | 3.5 | `-forbidden3` | same |
| 14 | `PBEParameterSpecSpec.c3` | fused → `c1` | 3.6 | `-lowiter`, base | 2 → 1 by report count |
| 15 | `SSLContextSpec.unsafe_protocol` | fused → `g1` | 3.6 | `-sslv3` | 2 `ORDER-00` and no protocol report → 1 `PROTO-00 val='SSLv3'` |
| 16 | `SignatureSpec.g3` | fused → `g1` | 3.6 | `-sha512withdsa` | **4** `ORDER-00` and no algorithm report → 1 `ALG-00 val='SHA512withDSA'` |
| 17 | `KeyPairGeneratorSpec.initError` | absorbed (`Inits` alternative, `mapped` to `i3`) | 3.6 | `-rsa3072` | 2 → 1: `KEYSIZE-00` kept, `ORDER-00` removed |

Partition: 12 negated twins fused on 11 arrows, plus `err1` riding the `PBEKeySpecSpec`
arrow as the thirteenth fused orphan, plus 4 absorbed. What separates the two treatments
is the orphan's **body**, not the shape of its guard — a body that carries an accusation
of its own is a report the set would lose, so the event stays; a body that only rebinds a
monitor field accuses nothing, and the only report it produces is the spurious ordering
one. That criterion corrected the census during task 3.2, which reclassified the three
`getInstance` accusers (#4, #15, #16) from absorptions to fusions.

## What the group found that the plan did not predict

**The orphan could suppress the finding, not only add to it.** Rows 4, 15 and 16 each
accused a wrong call sequence *and* prevented the constraint report the rule states, by
`__RESET`ting the monitor to a state where the following call is undeclared. Row 16 is the
extreme: one `Signature.getInstance("SHA512withDSA")` followed by an ordinary
sign sequence drew four ordering reports and never once said the algorithm was rejected.

**The harness verdict is a floor.** `TraceRunner.replay` records one accusing event and
one envelope per dispatcher call, so an orphan that accuses in its body *and* falls to
`@fail` in the same call shows up as one. Rows 5, 6, 7, 12, 13, 14 were counted by loading
`mop.MultiSpec_1RuntimeMonitor` from both snapshots and reading the whole collector
(`f1-IvParameterSpec-report-count.md`, `f1-PBEParameterSpecSpec-report-count.md`).

**Two accusations are unreachable, and are kept anyway.** `SECRETKEYSPEC-CONSTR-01`
(row 8) transcribes the rule's only CONSTRAINTS clause, and the JDK constructor throws
before the `after ... returning` advice can run, so no execution emits it
(`f1-SecretKeySpecSpec-unreachable-constraint.md`). `PBEKEYSPEC-CONSTR-01` is unreachable
for a different reason: the only producer chain that marks a `char[]` as randomised runs
through `String.valueOf(Object)`, which the harness's pointcut resolver does not match.
Both are recorded in `divergence_record.csv` and neither was repaired — repairing changes
what the set accuses.

**Absorption has two forms, and the rule picks.** Rows 3, 12 and 13 match calls the api30
rules turn down rather than sequence, so they self-loop and their mapping rows are
ORDER-unmapped. Row 17 matches `initialize(int)`, which api30 states as `i3` with the size
bound under CONSTRAINTS, so it enters at that position and its row is `mapped` to `i3`; a
self-loop there would have kept the ordering report, because a loop does not satisfy the
`Inits` the following `gen` needs (`f1-KeyPairGeneratorSpec-absorption.md`).

## Residue, recorded and deliberately not repaired

After the three `getInstance` fusions, a factory or context whose algorithm or protocol
the rule rejects and which is **never initialised** is accused by nothing: the accusation
lives in the `init` body. Measured, not assumed — `TrustManagerFactorySpec-sunx509-no-init`,
`SSLContextSpec-sslv3-no-init` and `SignatureSpec-sha512withdsa-no-init` all classify
`removed`. Moving the check up into the fused `g1` would close the hole but create a report
where none exists today, and would need deduplicating against the `init` one: a behavioural
change, deferred by the researcher's decision. `PBEKeySpecSpec`'s Kleene-prefix absorption
leaves an analogous residue, declared in that file's evidence.

The same suppression survives in the **two-argument `g2`** of `TrustManagerFactorySpec`,
`SSLContextSpec` and `SignatureSpec`, which still carries the guard its `g1` lost. `g2` is
inside the automaton, so G-ACC does not see it and no task of Groups 3-6 reaches it. It is
recorded in the body of each `.mop` and is not this group's to repair (decision of
2026-08-21, task 3.6).

## Where the gate stands

G-ACC reports nothing over `jca_android`, in both directions: no declared event is outside
its automaton, and no automaton names an event nothing declares. Task 3.7 retired the
gate's 17 baseline rows, so the pytest wrapper now compares against the empty set and the
next finding is a regression rather than an expectation
(`data/jca_android/gate_baseline.json`, key `retired`).

Harness over the 78 traces of the corpus, cumulative against the pre-image: **61 unchanged,
13 moved, 4 removed, 0 introduced.** Not one trace of the corpus is accused by the
successor and not by the pre-image.
