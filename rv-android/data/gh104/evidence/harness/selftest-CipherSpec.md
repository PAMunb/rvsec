# CipherSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | unchanged | CipherSpec.i1 | CipherSpec.i1 |
| `CipherSpec-unsafe.txt` | unchanged | CipherSpec.i1 | CipherSpec.i1 |
| `CipherSpec.txt` | unchanged | — | — |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found .`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found .`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found DES.`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found DES.`
