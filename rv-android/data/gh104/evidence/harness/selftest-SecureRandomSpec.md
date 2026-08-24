# SecureRandomSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 11

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-d15-nativeprng.txt` | unchanged | — | — |
| `SecureRandomSpec-d15-windowsprng.txt` | unchanged | — | — |
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | unchanged | — | — |
| `SecureRandomSpec-genseed-to-setseed.txt` | unchanged | — | — |
| `SecureRandomSpec-nativeprng.txt` | unchanged | — | — |
| `SecureRandomSpec-nextbytes-twice.txt` | unchanged | next2:? | next2:? |
| `SecureRandomSpec-randomised-seed.txt` | unchanged | — | — |
| `SecureRandomSpec-seeded-constructor.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-constructor.txt` | unchanged | c3:? | c3:? |
| `SecureRandomSpec-unrandomised-seed.txt` | unchanged | setSeed3:?, setSeed3:? | setSeed3:?, setSeed3:? |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-nextbytes-twice.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-nextbytes-twice.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-constructor.txt` (A) `spec=SecureRandomSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-constructor.txt` (B) `spec=SecureRandomSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=UnsatisfiedConstraint,msg=setSeed() expects a randomized byte array.`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed3,type=UnsatisfiedConstraint,msg=setSeed() expects a randomized byte array.`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=unknown`
