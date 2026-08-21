# KeyPairGeneratorSpec — why `initError` was absorbed as an `Inits` alternative (gh105 task 3.6)

The ratified plan defined absorption one way: benign self-loops at every state where the
orphan's call is legal, plus an `order-unmapped` row so G-ORDER erases the event from both
languages before comparing. That form is right for `SecureRandomSpec.g4` and the two
`PBEKeySpecSpec` FORBIDDEN constructors, whose calls the api30 rules turn down rather than
sequence. It is wrong for `initError`, and the difference is measurable.

## What the rule says the call is

api30 `KeyPairGenerator.cryptsl` orders `Gets, Inits, Generators` and names the call
`initError` matches as `i3: initialize(keySize)`, one of the four alternatives of `Inits`.
The size bound lives under CONSTRAINTS — `alg in {"RSA"} => keySize in {4096, 2048}` and its
three siblings. So `initialize(3072)` on an RSA generator is an `Inits` event that violates a
constraint, exactly as `getInstance("SunX509")` is a `Gets` event that violates one. The size
may no more govern the transition than the algorithm may, which is the finding task 3.2
established for the three `getInstance` twins.

## Why a self-loop would not have done

A loop does not advance the automaton, so it does not satisfy the `Inits` the following `gen`
needs. Under `(g3* g1 | g3* g2) initError* (init1|init2|init3|init4) initError* gen`, the trace
`getInstance("RSA"); initialize(3072); generateKeyPair()` would still fail at `gen`, and the
rejected key size would still cost a `KEYPAIRGENERATOR-ORDER-00` about an ordering the rule
accepts — the co-emission this group exists to remove, moved rather than removed. Putting the
event in the `Inits` group instead is what makes the ordering report go away.

## What the exemption would have cost

Keeping `order-unmapped` while placing the event as an `Inits` alternative is not an option:
the erasure is an epsilon move (`gh105_order_gate.nfa_of_expression`), so
`(init1|init2|init3|init4|initError)` would erase to `(init1|init2|init3|init4|ε)` and make
`Inits` optional. The `.mop` would then accept `Gets Generators`, which the rule rejects, and
G-ORDER would gain a fifth divergence that is an artefact of the mapping rather than a fact
about the specification. Mapping the event to `i3` — the symbol its sibling `init1` already
carries — leaves the erased languages literally unchanged, and two events standing for one
symbol is the non-bijection `order_alphabet_map.csv` documents in its header.

## Measured

Differential harness, `--a backup/gh105-preimage/jca_android`, `--b` the working set, trace
`KeyPairGeneratorSpec-rsa3072.txt` (`harness/f1-KeyPairGeneratorSpec.md`):

| snapshot | reports |
|---|---|
| A (pre-image, orphan) | **2** — `KEYPAIRGENERATOR-KEYSIZE-00 ev=initError val='3072'` and `KEYPAIRGENERATOR-ORDER-00 ev=gen` |
| B (absorbed) | **1** — `KEYPAIRGENERATOR-KEYSIZE-00 ev=initError val='3072'` |

Here the harness's own report is enough: the two accusations of side A come from two different
dispatcher calls (`initError` and `gen`), so nothing is hidden by the one-entry-per-call limit
that made the probe of task 3.3 necessary. The other four traces of the file are `unchanged`,
`KeyPairGeneratorSpec-sticky-fail.txt` among them — the task-8.15 case, whose `bind` leaves
`algorithm` null so that neither `init1` nor `initError` is condition-true, is unaffected by
where `initError` sits in the `ere`.
