# MacSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 10

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-decrypt-buffer.txt` | unchanged | SecretKeySpecSpec.c1, CipherSpec.i2, MacSpec.f2 | SecretKeySpecSpec.c1, CipherSpec.i2, MacSpec.f2 |
| `MacSpec-encrypted-buffer.txt` | unchanged | SecretKeySpecSpec.c1, CipherSpec.i2, MacSpec.f2 | SecretKeySpecSpec.c1, CipherSpec.i2, MacSpec.f2 |
| `MacSpec-fresh-buffer.txt` | unchanged | SecretKeySpecSpec.c1, CipherSpec.i2 | SecretKeySpecSpec.c1, CipherSpec.i2 |
| `MacSpec-guard-on-field.txt` | unchanged | MacSpec.i1 | MacSpec.i1 |
| `MacSpec-hmacpbesha1.txt` | removed | MacSpec.i1, MacSpec.f1Input | — |
| `MacSpec-mac-then-encrypt.txt` | moved | SecretKeySpecSpec.c1, CipherSpec.i2, IvChainJunctionSpec.finalInput | SecretKeySpecSpec.c1, CipherSpec.i2, CipherSpec.f2, IvChainJunctionSpec.finalInput |
| `MacSpec-ungenerated-key.txt` | unchanged | — | — |
| `MacSpec-unsafe-generated-key.txt` | removed | MacSpec.i1, MacSpec.f1Input | — |
| `MacSpec-update-then-encrypt.txt` | moved | SecretKeySpecSpec.c1, CipherSpec.i2, IvChainJunctionSpec.finalInput | SecretKeySpecSpec.c1, CipherSpec.i2, CipherSpec.f2, IvChainJunctionSpec.finalInput |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-decrypt-buffer.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-decrypt-buffer.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-decrypt-buffer.txt` (A) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-fresh-buffer.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-fresh-buffer.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-fresh-buffer.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-fresh-buffer.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-guard-on-field.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1Input,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-mac-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-mac-then-encrypt.txt` (A) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=f1Input,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-update-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `MacSpec-update-then-encrypt.txt` (A) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `MacSpec-update-then-encrypt.txt` (B) `spec=IvChainJunctionSpec,ev=finalInput,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-CONSTR-06 ev=finalInput obj=Cipher val='AES/ECB/PKCS5Padding' exp='a plaintext no observed Mac has authenticated' msg='the plaintext given to Cipher.doFinal was already authenticated by a Mac'`
