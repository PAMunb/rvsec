# Layer-3 verdicts — L3-b and L3-c, executed against the derived oracles

Recorded 2026-08-08. Raw reports: `l3b_verdict.json`, `l3c_verdict.json`.
Tasks 6.5–6.8.

## What these verdicts are, and what they are not

**They are characterization, not certification.** Both sides of every derived
oracle are frozen pre-repair recordings: the ground-truth side was recorded from
the `ajc` weaver and the side under test from a `dexlib2` run that predates
`48b57fc5`. Neither can flip green when the repair lands, because neither is
re-executed by the repair. A *certifying* verdict would need a fresh `dexlib2`
run over the same APKs — the runtime arm L3-a, or V4 — and neither is in this
change's scope, because both need an emulator session.

**The runtime arm L3-a did not run.** No emulator was started for this change,
at any point. What did run, V0 and V2, proves that the repaired weaver emits
every monitor call and that the emitted calls arrive **in the woven DEX**. That
is not the same claim as arrival in logcat: nothing here observes an event
travelling from a woven instruction to the on-device collector. Any report
citing these verdicts alongside V0/V2 must keep the two claims apart.

So the question these two gates answer is not "is the weaver fixed?" It is
"does the defect these recordings contain show up as the oracles predict?" —
and the answer to that is yes, in both profiles.

## Execution

```
ValidationCli layer3 --oracles <profile>/oracles --apks <profile>/traces
```

The 20 derived oracles live in one directory (`validator/oracles/`) and were
split by their `profile:` field for execution, so that each verdict speaks for
one profile only. Every oracle was **admitted** — `rejectedOracles` is empty in
both reports — and no trace pair was missing.

## L3-b — paired execution, 8 APKs

`passed: false`, 4 of 8 oracles pass, 14 specs scored.

| | ajc | dexlib2 |
|---|---|---|
| TP | 18 | 16 |
| FP | 0 | **10** |
| FN | 0 | 2 |

Failing specs: `TrustManagerFactorySpec` (4 APKs), `MessageDigestSpec` (2).

This is the wrapper-collision signature. The 10 false positives are events
`dexlib2` reports that the independent weaver never reported for the same APK,
and they concentrate in `TrustManagerFactorySpec` — one of the two
specifications whose advices collide on a shared call site
(`TrustManagerFactory.getInstance(String)` was bound twice, `g1` and `g3`). The
2 false negatives are the `MessageDigestSpec` misuse at `jh.h.c` in
`gizz.tapes.foss`, which `ajc` reports and `dexlib2` does not.

At the article's unique-misuse key the same recording reads `ajc = 13,
dexlib2 = 17, both = 12, only-ajc = 1, only-dexlib2 = 5`.

## L3-c — control group, 12 apps

`passed: false`, 2 of 12 oracles pass, 47 specs scored.

| | ajc (`-javaagent`) | dexlib2 |
|---|---|---|
| TP | 108 | 21 |
| FP | 0 | 66 |
| FN | 0 | **87** |

**This is the gate that speaks to the erased category.** The control group is
the only recorded regime in which `ErrorType.UnsatisfiedConstraint` is
observable at all, and the oracles declare 30 such events across the three
specifications that carry it:

| spec | expected `UnsatisfiedConstraint` events | observed under dexlib2 |
|---|---|---|
| `SecretKeySpecSpec` | 16 | 0 |
| `IvParameterSpecSpec` | 9 | 0 |
| `PBEKeySpecSpec` | 5 | 0 |
| **total** | **30** | **0** |

Each of those 30 events is one unique misuse — no site in the control group
raised `UnsatisfiedConstraint` more than once.

Across all twelve dexlib2 traces there is not one `UnsatisfiedConstraint` event.
Total silence on the category, which is what the inline-truncation defect
predicts: the erased events are the second monitor call of a fused advice, and 7
of the 9 dropped events are error emitters raising exactly this type.

The caveat that keeps this honest: the two sides come from **different execution
regimes** — a project's own unit tests against GUI exploration of a shipped APK.
An event absent from the dexlib2 side may mean the site was never reached rather
than that the weaver dropped it. That is why only three apps (`photok`,
`aegis`, `org.cry.otp`) are gated: their silence was proved by joining the
campaign's coverage against the erased sites, so the method ran and emitted
nothing. The other nine apps' oracles are marked `gated: false` and their
verdicts are carried, not gating.

## A defect found and repaired while recording these

The first execution of both gates reported `dexFp = 0` for L3-b — impossible
next to five dexlib2-only unique misuses. `TraceComparator.scoreOracle` built
its list of specifications to score from the **oracle's** events alone, so a
specification appearing in a trace but not in that APK's oracle was never
iterated and its events were never counted.

That is precisely the blind spot a wrapper collision falls into: a call site
bound to the *wrong* specification surfaces under a specification the
independent weaver never reported for that APK — so the oracle has no entry for
it, and the profile written to discriminate the collision could not see it.
Measured before the fix: 10 of 26 dexlib2 events in L3-b and 45 of 87 in L3-c
were outside the scored set.

`scoreOracle` now iterates the union of the oracle's specifications and those
observed in either trace; a specification absent from the oracle gets an empty
expected-event list, so every event under it is a false positive. The numbers
above are post-fix. `TraceComparatorTest.specAbsentFromTheOracleIsStillScored`
holds the contract.

## Regression baseline

`$DEXLIB2` validator module: **66 tests, 0 failures** — 59 before this group,
+7 all in `TraceComparatorTest` (5 → 12). `TraceComparatorBatchTest` stays at 6:
its five fixtures were rewritten, not added to.
