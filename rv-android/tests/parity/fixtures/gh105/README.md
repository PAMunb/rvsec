# gh105 fixtures

## The junction rules

The four rules of INV-INS-136 exist because the IV-chain pilot measured each one
being broken. Three of them — (a), (b), (d) — are decidable from the `.mop`
source, so they are gated rather than reviewed; a rule enforced by a review that
runs once per chain is not protected against the edit that follows it.

Their negatives cannot come from the tree, because the tree holds no junction
specification yet: the first one lands in task 5.1. So the negatives live here,
one file per rule, each carrying the exact defect the pilot produced and nothing
else. `ConformingJunction.mop` is the same chain written correctly, and it is
what makes the other three mean something — a gate that only ever sees broken
input cannot demonstrate that it stays quiet on good input.

| File | Rule | What it does wrong |
|---|---|---|
| `CreationConsumerJunction.mop` | (a) | declares the consumer event `creation`, so a monitor starts at the consuming call and never saw the producer |
| `PartialLoopJunction.mop` | (b) | leaves a state without a transition for one event, so a disconnected join arriving there fails instead of staying silent |
| `HandlerParameterJunction.mop` | (d) | names a specification parameter inside `@match`, where only monitor fields are in scope |
| `ConformingJunction.mop` | — | none: the chain as it must be written |

## The two gates whose red side the tree no longer shows

Task 4.12 moved the last guard read of `jca_android` and task 4.14 took the last
`ExecutionContext` mention, so INV-INS-133 and INV-INS-130 both assert a literal
zero over the live set. A zero is only worth what the gate's ability to fire is
worth, and by task 8.7 nothing demonstrated that any more — a gate rewired to
return `[]` would have satisfied every assertion the suite made about either.
The absence was measured, not assumed: `grep "condition(" tests/parity/fixtures`
returned nothing and no fixture named `ExecutionContext`.

Each of these two carries one defect and no other, for the same reason the
junction four do: a fixture that tripped two gates could not say which one was
still working.

| File | Invariant | What it does wrong |
|---|---|---|
| `GuardedReadSpec.mop` | INV-INS-133 | reads `PREPARED_IV` inside `condition(...)`, so a false read suppresses the transition and the program is accused of a wrong call sequence instead of the constraint it broke |
| `LegacySubstrateSpec.mop` | INV-INS-130 | names `ExecutionContext` in all three forms the invariant's `-w` exists to catch — the import, a fully-qualified call, and a comment — which is 3 mentions, 2 in code and 1 in prose |
