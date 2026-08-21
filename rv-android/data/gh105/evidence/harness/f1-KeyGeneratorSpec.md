# KeyGeneratorSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyGeneratorSpec-guard-on-field.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec-unsafe.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
