# SecureRandomSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-nativeprng.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-seed.txt` | unchanged | SecureRandomSpec.setSeed3 | SecureRandomSpec.setSeed3 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
