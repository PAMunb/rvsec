# CipherSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `CipherSpec-keygen-key-mismatch.txt` | unchanged | — | — |
| `CipherSpec-keygen-key.txt` | unchanged | — | — |
| `CipherSpec-keystore-key.txt` | unchanged | — | — |
| `CipherSpec-nofinal-arg.txt` | unchanged | f1:? | f1:? |
| `CipherSpec-unsafe.txt` | unchanged | f2:? | f2:? |
| `CipherSpec-update-chain.txt` | unchanged | u1:? | u1:? |
| `CipherSpec.txt` | unchanged | f2:? | f2:? |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found .`
- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found .`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-nofinal-arg.txt` (A) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-nofinal-arg.txt` (B) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-update-chain.txt` (A) `spec=CipherSpec,ev=u1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec-update-chain.txt` (B) `spec=CipherSpec,ev=u1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `CipherSpec.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
