# SecretKeySpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | moved | c3:SECRETKEYSPEC-CONSTR-00, c3:SECRETKEYSPEC-ORDER-00 | c1:SECRETKEYSPEC-ALG-00, c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-cipher-chain.txt` | introduced | — | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `SecretKeySpecSpec-d15-aes.txt` | moved | c3:SECRETKEYSPEC-CONSTR-00, c3:SECRETKEYSPEC-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-d15-hmacsha256.txt` | moved | c3:SECRETKEYSPEC-CONSTR-00, c3:SECRETKEYSPEC-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-offset.txt` | introduced | — | c2:SECRETKEYSPEC-NOBS-01 |
| `SecretKeySpecSpec-prepared-material.txt` | unchanged | — | — |
| `SecretKeySpecSpec.txt` | introduced | — | c1:SECRETKEYSPEC-NOBS-00 |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECRETKEYSPEC-ORDER-00 ev=c3 obj=SecretKeySpec val='' exp='' msg='the observed call sequence is not one SecretKeySpecSpec accepts'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsafeAlgorithm,msg=v=1 code=SECRETKEYSPEC-ALG-00 ev=c1 obj=SecretKeySpec val='DES' exp='AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `SecretKeySpecSpec-d15-aes.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpecSpec-d15-aes.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECRETKEYSPEC-ORDER-00 ev=c3 obj=SecretKeySpec val='' exp='' msg='the observed call sequence is not one SecretKeySpecSpec accepts'`
- `SecretKeySpecSpec-d15-aes.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-d15-hmacsha256.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpecSpec-d15-hmacsha256.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECRETKEYSPEC-ORDER-00 ev=c3 obj=SecretKeySpec val='' exp='' msg='the observed call sequence is not one SecretKeySpecSpec accepts'`
- `SecretKeySpecSpec-d15-hmacsha256.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-offset.txt` (B) `spec=SecretKeySpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-01 ev=c2 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
