# SecureRandomSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 11

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-d15-nativeprng.txt` | unchanged | — | — |
| `SecureRandomSpec-d15-windowsprng.txt` | unchanged | — | — |
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | unchanged | — | — |
| `SecureRandomSpec-genseed-to-setseed.txt` | unchanged | — | — |
| `SecureRandomSpec-nativeprng.txt` | unchanged | — | — |
| `SecureRandomSpec-nextbytes-twice.txt` | unchanged | — | — |
| `SecureRandomSpec-randomised-seed.txt` | unchanged | — | — |
| `SecureRandomSpec-seeded-constructor.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-constructor.txt` | unchanged | c2:SECURERANDOM-NOBS-01 | c2:SECURERANDOM-NOBS-01 |
| `SecureRandomSpec-unrandomised-seed.txt` | unchanged | setSeed2:SECURERANDOM-NOBS-00 | setSeed2:SECURERANDOM-NOBS-00 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-unrandomised-constructor.txt` (A) `spec=SecureRandomSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-01 ev=c2 obj=SecureRandom val='' exp='a randomized byte[]' msg='the constructor expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-constructor.txt` (B) `spec=SecureRandomSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-01 ev=c2 obj=SecureRandom val='' exp='a randomized byte[]' msg='the constructor expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
