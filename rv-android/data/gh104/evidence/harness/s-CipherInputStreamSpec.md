# CipherInputStreamSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherInputStreamSpec-initialised-cipher.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `CipherInputStreamSpec-two-streams.txt` | unchanged | c1:CIPHERINPUTSTREAM-NOBS-00 | c1:CIPHERINPUTSTREAM-NOBS-00 |
| `CipherInputStreamSpec-unclosed.txt` | unchanged | c1:CIPHERINPUTSTREAM-NOBS-00 | c1:CIPHERINPUTSTREAM-NOBS-00 |
| `CipherInputStreamSpec.txt` | unchanged | c1:CIPHERINPUTSTREAM-NOBS-00 | c1:CIPHERINPUTSTREAM-NOBS-00 |

## Envelopes

- `CipherInputStreamSpec-initialised-cipher.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherInputStreamSpec-initialised-cipher.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherInputStreamSpec-initialised-cipher.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherInputStreamSpec-initialised-cipher.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherInputStreamSpec-two-streams.txt` (A) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec-two-streams.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec-unclosed.txt` (A) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec-unclosed.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec.txt` (A) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
