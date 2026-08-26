# SecureRandomSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 11

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecureRandomSpec-d15-nativeprng.txt` | removed | g4:SECURERANDOM-ALG-00, g4:SECURERANDOM-ORDER-00, genSeed:SECURERANDOM-ORDER-00, setSeed2:SECURERANDOM-ORDER-00 | — |
| `SecureRandomSpec-d15-windowsprng.txt` | removed | g4:SECURERANDOM-ALG-00, g4:SECURERANDOM-ORDER-00, next2:SECURERANDOM-ORDER-00 | — |
| `SecureRandomSpec-genseed-rejected-algorithm.txt` | removed | g4:SECURERANDOM-ALG-00, g4:SECURERANDOM-ORDER-00, genSeed:SECURERANDOM-ORDER-00, setSeed2:SECURERANDOM-ORDER-00 | — |
| `SecureRandomSpec-genseed-to-setseed.txt` | unchanged | — | — |
| `SecureRandomSpec-nativeprng.txt` | removed | g4:SECURERANDOM-ALG-00, g4:SECURERANDOM-ORDER-00, next2:SECURERANDOM-ORDER-00 | — |
| `SecureRandomSpec-nextbytes-twice.txt` | removed | next2:SECURERANDOM-ORDER-00 | — |
| `SecureRandomSpec-randomised-seed.txt` | unchanged | — | — |
| `SecureRandomSpec-seeded-constructor.txt` | unchanged | — | — |
| `SecureRandomSpec-unrandomised-constructor.txt` | moved | c3:SECURERANDOM-ORDER-00 | c2:SECURERANDOM-NOBS-01 |
| `SecureRandomSpec-unrandomised-seed.txt` | moved | next2:SECURERANDOM-ORDER-00, setSeed3:SECURERANDOM-CONSTR-00, setSeed3:SECURERANDOM-ORDER-00 | setSeed2:SECURERANDOM-NOBS-00 |
| `SecureRandomSpec.txt` | unchanged | — | — |

## Envelopes

- `SecureRandomSpec-d15-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-d15-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=g4 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-d15-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=genSeed,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=genSeed obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-d15-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=setSeed2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-d15-windowsprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='Windows-PRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found Windows-PRNG'`
- `SecureRandomSpec-d15-windowsprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=g4 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-d15-windowsprng.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=g4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=g4 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=genSeed,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=genSeed obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-genseed-rejected-algorithm.txt` (A) `spec=SecureRandomSpec,ev=setSeed2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=setSeed2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=g4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=g4 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-nativeprng.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-nextbytes-twice.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-constructor.txt` (A) `spec=SecureRandomSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=c3 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-constructor.txt` (B) `spec=SecureRandomSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-01 ev=c2 obj=SecureRandom val='' exp='a randomized byte[]' msg='the constructor expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-CONSTR-00 ev=setSeed3 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=setSeed3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=setSeed3 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-seed.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `SecureRandomSpec-unrandomised-seed.txt` (B) `spec=SecureRandomSpec,ev=setSeed2,type=UnsatisfiedConstraint,msg=v=1 code=SECURERANDOM-NOBS-00 ev=setSeed2 obj=SecureRandom val='' exp='a randomized byte[]' msg='setSeed() expects a byte array observed to come from a randomized source'`
