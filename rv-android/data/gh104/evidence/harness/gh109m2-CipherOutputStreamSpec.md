# CipherOutputStreamSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherOutputStreamSpec-flush-around-write.txt` | unchanged | c1:CIPHEROUTPUTSTREAM-NOBS-00 | c1:CIPHEROUTPUTSTREAM-NOBS-00 |
| `CipherOutputStreamSpec-flush-only.txt` | moved | c1:CIPHEROUTPUTSTREAM-NOBS-00 | c1:CIPHEROUTPUTSTREAM-NOBS-00, cl:CIPHEROUTPUTSTREAM-ORDER-00 |
| `CipherOutputStreamSpec-initialised-cipher.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `CipherOutputStreamSpec-unclosed.txt` | unchanged | c1:CIPHEROUTPUTSTREAM-NOBS-00 | c1:CIPHEROUTPUTSTREAM-NOBS-00 |
| `CipherOutputStreamSpec.txt` | unchanged | c1:CIPHEROUTPUTSTREAM-NOBS-00 | c1:CIPHEROUTPUTSTREAM-NOBS-00 |

## Envelopes

- `CipherOutputStreamSpec-flush-around-write.txt` (A) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec-flush-around-write.txt` (B) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec-flush-only.txt` (A) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec-flush-only.txt` (B) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec-flush-only.txt` (B) `spec=CipherOutputStreamSpec,ev=cl,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHEROUTPUTSTREAM-ORDER-00 ev=cl obj=CipherOutputStream val='' exp='' msg='the observed call sequence is not one CipherOutputStreamSpec accepts'`
- `CipherOutputStreamSpec-initialised-cipher.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherOutputStreamSpec-initialised-cipher.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherOutputStreamSpec-initialised-cipher.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherOutputStreamSpec-initialised-cipher.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherOutputStreamSpec-unclosed.txt` (A) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec-unclosed.txt` (B) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec.txt` (A) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
- `CipherOutputStreamSpec.txt` (B) `spec=CipherOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHEROUTPUTSTREAM-NOBS-00 ev=c1 obj=CipherOutputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherOutputStream constructor was not observed being initialised'`
