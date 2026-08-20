# KeyGeneratorSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyGeneratorSpec-guard-on-field.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec-unsafe.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec.txt` | unchanged | — | — |

## Self-contradicting envelopes

- `KeyGeneratorSpec-guard-on-field.txt` — b: self-contradicting envelope -- val ∈ exp: observed 'aes' is listed in ['aes', 'arc4', 'blowfish', 'chacha20', 'desede', 'hmacmd5', 'hmacsha1', 'hmacsha224', 'hmacsha256', 'hmacsha384', 'hmacsha512']

## Envelopes

- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found .`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='AES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found AES'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES.`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
