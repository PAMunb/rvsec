# IvChainJunctionSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvChainJunctionSpec-decrypt.txt` | moved | IvParameterSpecSpec.c3 | SecretKeySpecSpec.c1, IvParameterSpecSpec.c1, CipherSpec.i2 |
| `IvChainJunctionSpec-gcm-unprepared.txt` | introduced | — | SecretKeySpecSpec.c1, GCMParameterSpecSpec.c1, CipherSpec.i2, IvChainJunctionSpec.use |
| `IvChainJunctionSpec-gcm.txt` | moved | SecureRandomSpec.next2 | SecretKeySpecSpec.c1, CipherSpec.i2 |
| `IvChainJunctionSpec-rangen-unobserved.txt` | moved | SecureRandomSpec.g4 | SecureRandomSpec.g4, SecretKeySpecSpec.c1, CipherSpec.i2, IvChainJunctionSpec.useRandomKey |
| `IvChainJunctionSpec-rangen.txt` | introduced | — | SecretKeySpecSpec.c1, CipherSpec.i2 |
| `IvChainJunctionSpec-unprepared.txt` | moved | IvParameterSpecSpec.c3 | SecretKeySpecSpec.c1, IvParameterSpecSpec.c1, CipherSpec.i2, IvChainJunctionSpec.use |
| `IvChainJunctionSpec.txt` | moved | SecureRandomSpec.next2 | SecretKeySpecSpec.c1, CipherSpec.i2 |

## Envelopes

- `IvChainJunctionSpec-decrypt.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-decrypt.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-decrypt.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-decrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-00 ev=c1 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=IvChainJunctionSpec,ev=use,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-01 ev=use obj=Cipher val='AES/GCM/NoPadding' exp='a GCMParameterSpec built over an observed randomized source' msg='no preparation of the AlgorithmParameterSpec given to Cipher.init was observed'`
- `IvChainJunctionSpec-gcm.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `IvChainJunctionSpec-gcm.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-gcm.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=IvChainJunctionSpec,ev=useRandomKey,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-02 ev=useRandomKey obj=Cipher val='AES/ECB/PKCS5Padding' exp='a SecureRandom this instrumentation observed being constructed' msg='the SecureRandom given to Cipher.init was not observed to come from an observed construction'`
- `IvChainJunctionSpec-rangen.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-rangen.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-unprepared.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvChainJunctionSpec,ev=use,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-00 ev=use obj=Cipher val='AES/CBC/PKCS5Padding' exp='an IvParameterSpec built over an observed randomized iv' msg='no preparation of the AlgorithmParameterSpec given to Cipher.init was observed'`
- `IvChainJunctionSpec.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `IvChainJunctionSpec.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `IvChainJunctionSpec.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
