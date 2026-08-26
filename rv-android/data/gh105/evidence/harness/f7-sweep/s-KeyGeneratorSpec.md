# KeyGeneratorSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyGeneratorSpec-d15-arc4.txt` | unchanged | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 |
| `KeyGeneratorSpec-d15-desede.txt` | moved | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 | gk1:KEYGENERATOR-ALG-00, gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 |
| `KeyGeneratorSpec-d15-hmacmd5.txt` | moved | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 | gk1:KEYGENERATOR-ALG-00, gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 |
| `KeyGeneratorSpec-guard-on-field.txt` | unchanged | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 | gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 |
| `KeyGeneratorSpec-rangen-unobserved.txt` | removed | g4:SECURERANDOM-ALG-00, g4:SECURERANDOM-ORDER-00 | — |
| `KeyGeneratorSpec-rangen.txt` | unchanged | — | — |
| `KeyGeneratorSpec-unsafe.txt` | unchanged | gk1:KEYGENERATOR-ALG-00, gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 | gk1:KEYGENERATOR-ALG-00, gk1:KEYGENERATOR-ORDER-00, init:KEYGENERATOR-ORDER-00 |
| `KeyGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyGeneratorSpec-d15-arc4.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-arc4.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-arc4.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-arc4.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-desede.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-desede.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-desede.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-desede.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DESede' exp='AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DESede'`
- `KeyGeneratorSpec-d15-desede.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-hmacmd5.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-hmacmd5.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-hmacmd5.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-d15-hmacmd5.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='HmacMD5' exp='AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found HmacMD5'`
- `KeyGeneratorSpec-d15-hmacmd5.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-guard-on-field.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-rangen-unobserved.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `KeyGeneratorSpec-rangen-unobserved.txt` (A) `spec=SecureRandomSpec,ev=g4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=g4 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384' msg='expecting one of ChaCha20,ARC4,HmacSHA224,DESede,HmacSHA256,HmacMD5,HmacSHA1,HmacSHA512,AES,BLOWFISH,HmacSHA384 but found DES'`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=init obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=v=1 code=KEYGENERATOR-ALG-00 ev=gk1 obj=KeyGenerator val='DES' exp='AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES'`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYGENERATOR-ORDER-00 ev=gk1 obj=KeyGenerator val='' exp='' msg='the observed call sequence is not one KeyGeneratorSpec accepts'`
