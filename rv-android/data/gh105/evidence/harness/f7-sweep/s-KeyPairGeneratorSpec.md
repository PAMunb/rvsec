# KeyPairGeneratorSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-d15-diffiehellman.txt` | removed | gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 | — |
| `KeyPairGeneratorSpec-d15-rsa-3072.txt` | removed | gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 | — |
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec-rsa1024.txt` | moved | gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 | initError:KEYPAIRGENERATOR-KEYSIZE-00 |
| `KeyPairGeneratorSpec-rsa3072.txt` | removed | gen:KEYPAIRGENERATOR-ORDER-00, initError:KEYPAIRGENERATOR-KEYSIZE-00, initError:KEYPAIRGENERATOR-ORDER-00 | — |
| `KeyPairGeneratorSpec-sticky-fail.txt` | unchanged | gen:KEYPAIRGENERATOR-ORDER-00 | gen:KEYPAIRGENERATOR-ORDER-00 |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairGeneratorSpec-d15-diffiehellman.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='2048' exp='the key size api30 KeyPairGenerator.cryptsl declares for DiffieHellman' msg='invalid key size for algorithm DiffieHellman'`
- `KeyPairGeneratorSpec-d15-diffiehellman.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-d15-diffiehellman.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-d15-rsa-3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='3072' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-d15-rsa-3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-d15-rsa-3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa1024.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa1024.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa1024.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa1024.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='1024' exp='the key size the expert KeyPairGenerator.crysl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='3072' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=initError obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
