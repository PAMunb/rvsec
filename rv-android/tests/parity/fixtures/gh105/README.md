# gh105 junction fixtures

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
