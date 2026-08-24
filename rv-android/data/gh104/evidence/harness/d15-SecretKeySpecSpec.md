# SecretKeySpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | unchanged | SecretKeySpecSpec.c1 | SecretKeySpecSpec.c1 |
| `SecretKeySpecSpec-cipher-chain.txt` | unchanged | SecretKeySpecSpec.c1, CipherSpec.i2 | SecretKeySpecSpec.c1, CipherSpec.i2 |
| `SecretKeySpecSpec-offset.txt` | unchanged | SecretKeySpecSpec.c2 | SecretKeySpecSpec.c2 |
| `SecretKeySpecSpec-prepared-material.txt` | unchanged | — | — |
| `SecretKeySpecSpec.txt` | unchanged | SecretKeySpecSpec.c1 | SecretKeySpecSpec.c1 |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-cipher-chain.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `SecretKeySpecSpec-offset.txt` (A) `spec=SecretKeySpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-01 ev=c2 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec-offset.txt` (B) `spec=SecretKeySpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-01 ev=c2 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpecSpec.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
