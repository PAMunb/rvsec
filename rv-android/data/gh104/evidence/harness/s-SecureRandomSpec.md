# SecureRandomSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-nativeprng.txt` | introduced | — | SecureRandomSpec.g4 |
| `SecureRandomSpec-unrandomised-seed.txt` | unchanged | SecureRandomSpec.setSeed3 | SecureRandomSpec.setSeed3 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-nativeprng.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of SHA1PRNG but found NativePRNG.`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
