# KeyPairGeneratorSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 16

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-d15-diffiehellman.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-d15-rsa-3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-init3-no-clause-applies.txt` | unchanged | init3:KEYPAIRGENERATOR-ORDER-00 | init3:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-init3-prepared-rsa.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-init3-unobserved-params.txt` | introduced | — | init3:KEYPAIRGENERATOR-NOBS-00 |
| `KeyPairGeneratorSpec-init4-prepared-rsa.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-init4-unobserved-params.txt` | introduced | — | init4:KEYPAIRGENERATOR-NOBS-01 |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-provider.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` | moved | gen:KEYPAIRGENERATOR-ORDER-00 | g4:KEYPAIRGENERATOR-ALG-01, gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-rejected-algorithm.txt` | moved | gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 | g3:KEYPAIRGENERATOR-ALG-00, gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-rsa1024.txt` | unchanged | initError:KEYPAIRGENERATOR-KEYSIZE-00 | initError:KEYPAIRGENERATOR-KEYSIZE-00 |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-sticky-fail.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `KeyPairGeneratorSpec-init3-prepared-rsa.txt` (A) `new RSAKeyGenParameterSpec(2048, 65537) -> params`
- `KeyPairGeneratorSpec-init4-prepared-rsa.txt` (A) `new RSAKeyGenParameterSpec(2048, 65537) -> params`

## Envelopes

- `KeyPairGeneratorSpec-init3-no-clause-applies.txt` (A) `spec=KeyPairGeneratorSpec,ev=init3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=init3 obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-init3-no-clause-applies.txt` (B) `spec=KeyPairGeneratorSpec,ev=init3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=init3 obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-init3-unobserved-params.txt` (B) `spec=KeyPairGeneratorSpec,ev=init3,type=UnsatisfiedConstraint,msg=v=1 code=KEYPAIRGENERATOR-NOBS-00 ev=init3 obj=KeyPairGenerator val='RSA' exp='preparedRSA' msg='no preparation of the AlgorithmParameterSpec given to KeyPairGenerator.initialize was observed'`
- `KeyPairGeneratorSpec-init4-unobserved-params.txt` (B) `spec=KeyPairGeneratorSpec,ev=init4,type=UnsatisfiedConstraint,msg=v=1 code=KEYPAIRGENERATOR-NOBS-01 ev=init4 obj=KeyPairGenerator val='RSA' exp='preparedRSA' msg='no preparation of the AlgorithmParameterSpec given to KeyPairGenerator.initialize was observed'`
- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` (B) `spec=KeyPairGeneratorSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=KEYPAIRGENERATOR-ALG-01 ev=g4 obj=KeyPairGenerator val='Ed25519' exp='RSA,EC,DSA,DiffieHellman,DH' msg='expecting one of RSA,EC,DSA,DiffieHellman,DH but found Ed25519'`
- `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='256' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm-provider.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='256' exp='the key size the expert KeyPairGenerator.crysl declares for Ed25519' msg='invalid key size for algorithm Ed25519'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (B) `spec=KeyPairGeneratorSpec,ev=g3,type=UnsafeAlgorithm,msg=v=1 code=KEYPAIRGENERATOR-ALG-00 ev=g3 obj=KeyPairGenerator val='Ed25519' exp='RSA,EC,DSA,DiffieHellman,DH' msg='expecting one of RSA,EC,DSA,DiffieHellman,DH but found Ed25519'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='256' exp='the key size the expert KeyPairGenerator.crysl declares for Ed25519' msg='invalid key size for algorithm Ed25519'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rejected-algorithm.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa1024.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa1024.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
