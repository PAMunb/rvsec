# SecretKeySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpec-encoded-iv.txt` | unchanged | — | — |
| `SecretKeySpec-hardcoded-iv.txt` | moved | c3:?, c3:?, c3:?, c3:? | c3:?, c3:? |
| `SecretKeySpec-keygen-iv.txt` | unchanged | — | — |
| `SecretKeySpec-laundered-material.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |
| `SecretKeySpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=unknown`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecretKeySpec-laundered-material.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpec-laundered-material.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecretKeySpec-laundered-material.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `SecretKeySpec-laundered-material.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
