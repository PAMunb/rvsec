# CipherSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | unchanged | CipherSpec.i1 | CipherSpec.i1 |
| `CipherSpec-unsafe.txt` | unchanged | CipherSpec.i1 | CipherSpec.i1 |
| `CipherSpec.txt` | unchanged | — | — |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found .`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-00 ev=i1 obj=Cipher val='AES/CBC/PKCS5Padding' exp='a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl)' msg='expecting a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl) but found AES/CBC/PKCS5Padding'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found DES.`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-00 ev=i1 obj=Cipher val='DES' exp='a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl)' msg='expecting a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl) but found DES'`
