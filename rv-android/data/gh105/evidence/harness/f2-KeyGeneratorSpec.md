# KeyGeneratorSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyGeneratorSpec-guard-on-field.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec-rangen-unobserved.txt` | moved | SecureRandomSpec.g4 | SecureRandomSpec.g4, KeyGeneratorSpec.initRandomSize |
| `KeyGeneratorSpec-rangen.txt` | unchanged | — | — |
| `KeyGeneratorSpec-unsafe.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-rangen-unobserved.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `KeyGeneratorSpec-rangen-unobserved.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `KeyGeneratorSpec-rangen-unobserved.txt` (B) `spec=KeyGeneratorSpec,ev=initRandomSize,type=UnsatisfiedConstraint,msg=v=1 code=KEYGENERATOR-NOBS-01 ev=initRandomSize obj=KeyGenerator val='AES' exp='a SecureRandom this instrumentation observed being constructed' msg='init() expects a SecureRandom observed to come from an observed construction'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
