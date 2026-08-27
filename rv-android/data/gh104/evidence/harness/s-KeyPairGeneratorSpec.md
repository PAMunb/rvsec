# KeyPairGeneratorSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-d15-diffiehellman.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-d15-rsa-3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-rsa1024.txt` | unchanged | initError:KEYPAIRGENERATOR-KEYSIZE-00 | initError:KEYPAIRGENERATOR-KEYSIZE-00 |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-sticky-fail.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa1024.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa1024.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
