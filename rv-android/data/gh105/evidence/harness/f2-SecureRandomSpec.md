# SecureRandomSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | unchanged | SecureRandomSpec.g4, SecureRandomSpec.genSeed, SecureRandomSpec.setSeed2 | SecureRandomSpec.g4, SecureRandomSpec.genSeed, SecureRandomSpec.setSeed2 |
| `SecureRandomSpec-genseed-to-setseed.txt` | unchanged | — | — |
| `SecureRandomSpec-nativeprng.txt` | unchanged | SecureRandomSpec.g4, SecureRandomSpec.next2 | SecureRandomSpec.g4, SecureRandomSpec.next2 |
| `SecureRandomSpec-nextbytes-twice.txt` | removed | SecureRandomSpec.next2 | — |
| `SecureRandomSpec-randomised-seed.txt` | unchanged | — | — |
| `SecureRandomSpec-seeded-constructor.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-constructor.txt` | removed | SecureRandomSpec.c3 | — |
| `SecureRandomSpec-unrandomised-seed.txt` | moved | SecureRandomSpec.setSeed3, SecureRandomSpec.next2 | SecureRandomSpec.setSeed2 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=genSeed,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (B) `spec=SecureRandomSpec,ev=genSeed,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (B) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=next2,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nativeprng.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nativeprng.txt` (B) `spec=SecureRandomSpec,ev=next2,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nextbytes-twice.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-constructor.txt` (A) `spec=SecureRandomSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=c3 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-CONSTR-00 ev=setSeed3 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=next2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-CONSTR-00 ev=setSeed3 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
