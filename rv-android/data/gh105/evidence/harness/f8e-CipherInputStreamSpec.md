# CipherInputStreamSpec — differential harness

- **A** `/home/pedro/tmp-gh104/f8-generated-cipher/A`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherInputStreamSpec-initialised-cipher.txt` | unchanged | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 | c1:SECRETKEYSPEC-NOBS-00, i2:CIPHER-NOBS-00 |
| `CipherInputStreamSpec-two-streams.txt` | introduced | — | c1:CIPHERINPUTSTREAM-NOBS-00 |
| `CipherInputStreamSpec-unclosed.txt` | introduced | — | c1:CIPHERINPUTSTREAM-NOBS-00 |
| `CipherInputStreamSpec.txt` | introduced | — | c1:CIPHERINPUTSTREAM-NOBS-00 |

## Envelopes

- `CipherInputStreamSpec-initialised-cipher.txt` (A) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherInputStreamSpec-initialised-cipher.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherInputStreamSpec-initialised-cipher.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `CipherInputStreamSpec-initialised-cipher.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherInputStreamSpec-two-streams.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec-unclosed.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
- `CipherInputStreamSpec.txt` (B) `spec=CipherInputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHERINPUTSTREAM-NOBS-00 ev=c1 obj=CipherInputStream val='' exp='a Cipher this instrumentation observed being initialised' msg='the Cipher given to the CipherInputStream constructor was not observed being initialised'`
