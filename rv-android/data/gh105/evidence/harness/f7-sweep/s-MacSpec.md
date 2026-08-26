# MacSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 11

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-d15-hmacpbesha1.txt` | moved | f1:MAC-ORDER-00, update:MAC-ORDER-00 | f1:MAC-ORDER-00, i1:MAC-ORDER-00, update:MAC-ORDER-00, updateBytes:MAC-ORDER-00 |
| `MacSpec-decrypt-buffer.txt` | moved | f2:MAC-ORDER-00, next2:SECURERANDOM-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00, f2:MAC-CONSTR-00, i2:CIPHER-NOBS-00 |
| `MacSpec-encrypted-buffer.txt` | moved | f2:MAC-ORDER-00, next2:SECURERANDOM-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00, f2:MAC-CONSTR-00, i2:CIPHER-NOBS-00 |
| `MacSpec-fresh-buffer.txt` | moved | f2:MAC-ORDER-00, next2:SECURERANDOM-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `MacSpec-guard-on-field.txt` | introduced | — | i1:MAC-ORDER-00 |
| `MacSpec-hmacpbesha1.txt` | removed | f1:MAC-ORDER-00 | — |
| `MacSpec-mac-then-encrypt.txt` | introduced | — | c1:SECRETKEYSPEC-NOBS-00, f2:CIPHER-ORDER-00, finalInput:IVCHAINJUNCTION-CONSTR-06, i2:CIPHER-ALG-01, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 |
| `MacSpec-ungenerated-key.txt` | removed | f1:MAC-ORDER-00 | — |
| `MacSpec-unsafe-generated-key.txt` | removed | f1:MAC-ORDER-00, i1:MAC-ALG-00, i1:MAC-ORDER-00 | — |
| `MacSpec-update-then-encrypt.txt` | introduced | — | c1:SECRETKEYSPEC-NOBS-00, f2:CIPHER-ORDER-00, finalInput:IVCHAINJUNCTION-CONSTR-06, i2:CIPHER-ALG-01, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-d15-hmacpbesha1.txt` (A) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=update obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-d15-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-d15-hmacpbesha1.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-d15-hmacpbesha1.txt` (B) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=update obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-d15-hmacpbesha1.txt` (B) `spec=MacSpec,ev=updateBytes,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=updateBytes obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-d15-hmacpbesha1.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-decrypt-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-decrypt-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-fresh-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-fresh-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-fresh-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-fresh-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-01 ev=i2 obj=Cipher val='AES/ECB/PKCS5Padding' exp='a transformation admitted by CipherTransformationUtil (expert Cipher.crysl)' msg='expecting a transformation admitted by CipherTransformationUtil (expert Cipher.crysl) but found AES/ECB/PKCS5Padding'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
- `MacSpec-ungenerated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=MAC-ALG-00 ev=i1 obj=Mac val='HmacPBESHA1' exp='PBEwithHmacSHA256,PBEwithHmacSHA1,HmacSHA224,HmacSHA256,HmacMD5,HmacSHA512,PBEwithHmacSHA512,HmacSHA384,PBEwithHmacSHA384,PBEwithHmacSHA224,PBEwithHmacSHA,HmacSHA1' msg='expecting one of PBEwithHmacSHA256,PBEwithHmacSHA1,HmacSHA224,HmacSHA256,HmacMD5,HmacSHA512,PBEwithHmacSHA512,HmacSHA384,PBEwithHmacSHA384,PBEwithHmacSHA224,PBEwithHmacSHA,HmacSHA1 but found HmacPBESHA1'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-01 ev=i2 obj=Cipher val='AES/ECB/PKCS5Padding' exp='a transformation admitted by CipherTransformationUtil (expert Cipher.crysl)' msg='expecting a transformation admitted by CipherTransformationUtil (expert Cipher.crysl) but found AES/ECB/PKCS5Padding'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
