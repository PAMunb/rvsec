# SecureRandomSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | removed | SecureRandomSpec.g4, SecureRandomSpec.genSeed, SecureRandomSpec.setSeed2 | — |
| `SecureRandomSpec-genseed-to-setseed.txt` | unchanged | — | — |
| `SecureRandomSpec-nativeprng.txt` | removed | SecureRandomSpec.g4, SecureRandomSpec.next2 | — |
| `SecureRandomSpec-nextbytes-twice.txt` | unchanged | — | — |
| `SecureRandomSpec-randomised-seed.txt` | unchanged | — | — |
| `SecureRandomSpec-seeded-constructor.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-constructor.txt` | unchanged | SecureRandomSpec.c2 | SecureRandomSpec.c2 |
| `SecureRandomSpec-unrandomised-seed.txt` | unchanged | SecureRandomSpec.setSeed2 | SecureRandomSpec.setSeed2 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=genSeed,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=next2,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-unrandomised-constructor.txt` (A) `spec=SecureRandomSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-01 ev=c2 obj=SecureRandom val='' exp='a randomized byte[]' msg='the constructor expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-constructor.txt` (B) `spec=SecureRandomSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-01 ev=c2 obj=SecureRandom val='' exp='a randomized byte[]' msg='the constructor expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
