# SecretKeySpecSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | unchanged | SecretKeySpecSpec.c3 | SecretKeySpecSpec.c3 |
| `SecretKeySpecSpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
