# SecretKeySpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |
| `SecretKeySpecSpec-cipher-chain.txt` | unchanged | — | — |
| `SecretKeySpecSpec-offset.txt` | unchanged | — | — |
| `SecretKeySpecSpec-prepared-material.txt` | unchanged | — | — |
| `SecretKeySpecSpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
