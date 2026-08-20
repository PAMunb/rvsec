# KeyPairGeneratorSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | KeyPairGeneratorSpec.gen | KeyPairGeneratorSpec.gen |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | KeyPairGeneratorSpec.initError | KeyPairGeneratorSpec.initError |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=invalid key size for algorithm RSA.`
- `KeyPairGeneratorSpec-rsa3072.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='3072' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
