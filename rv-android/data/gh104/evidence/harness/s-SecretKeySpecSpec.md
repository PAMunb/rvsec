# SecretKeySpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | unchanged | c1:SECRETKEYSPEC-ALG-00, c1:SECRETKEYSPEC-NOBS-00 | c1:SECRETKEYSPEC-ALG-00, c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-cipher-chain.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `SecretKeySpecSpec-d15-aes.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-d15-hmacsha256.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpecSpec-offset.txt` | unchanged | c2:SECRETKEYSPEC-NOBS-01 | c2:SECRETKEYSPEC-NOBS-01 |
| `SecretKeySpecSpec-prepared-material.txt` | unchanged | — | — |
| `SecretKeySpecSpec.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00 |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsafeAlgorithm,msg=v=1 code=SECRETKEYSPEC-ALG-00 ev=c1 obj=SecretKeySpec val='DES' exp='AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES'`
- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsafeAlgorithm,msg=v=1 code=SECRETKEYSPEC-ALG-00 ev=c1 obj=SecretKeySpec val='DES' exp='AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512' msg='expecting one of AES,HMACSHA256,HMACSHA384,HMACSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `SecretKeySpecSpec-d15-aes.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-d15-aes.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-d15-hmacsha256.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-d15-hmacsha256.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-offset.txt` (A) `spec=SecretKeySpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-01 ev=c2 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-offset.txt` (B) `spec=SecretKeySpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-01 ev=c2 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
