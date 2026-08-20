# KeyPairGeneratorSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | KeyPairGeneratorSpec.gen | KeyPairGeneratorSpec.gen |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | KeyPairGeneratorSpec.initError | KeyPairGeneratorSpec.initError |
| `KeyPairGeneratorSpec-sticky-fail.txt` | unchanged | KeyPairGeneratorSpec.gen | KeyPairGeneratorSpec.gen |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.init1 raised java.lang.NullPointerException: Cannot invoke "String.toUpperCase()" because the return value of "br.unb.cic.mop.jca.util.ConscryptAliasTable.canonical(String, String)" is null)`
- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.initError raised java.lang.NullPointerException: Cannot invoke "String.toUpperCase()" because the return value of "br.unb.cic.mop.jca.util.ConscryptAliasTable.canonical(String, String)" is null)`

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-rsa3072.txt` (A) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='3072' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-rsa3072.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=v=1 code=KEYPAIRGENERATOR-KEYSIZE-00 ev=initError obj=KeyPairGenerator val='3072' exp='the key size api30 KeyPairGenerator.cryptsl declares for RSA' msg='invalid key size for algorithm RSA'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
- `KeyPairGeneratorSpec-sticky-fail.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIRGENERATOR-ORDER-00 ev=gen obj=KeyPairGenerator val='' exp='' msg='the observed call sequence is not one KeyPairGeneratorSpec accepts'`
