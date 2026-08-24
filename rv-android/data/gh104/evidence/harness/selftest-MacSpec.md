# MacSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 11

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-d15-hmacpbesha1.txt` | unchanged | update:? | update:? |
| `MacSpec-decrypt-buffer.txt` | unchanged | f2:?, next2:? | f2:?, next2:? |
| `MacSpec-encrypted-buffer.txt` | unchanged | f2:?, next2:? | f2:?, next2:? |
| `MacSpec-fresh-buffer.txt` | unchanged | f2:?, next2:? | f2:?, next2:? |
| `MacSpec-guard-on-field.txt` | unchanged | — | — |
| `MacSpec-hmacpbesha1.txt` | unchanged | f1:? | f1:? |
| `MacSpec-mac-then-encrypt.txt` | unchanged | i2:?, i2:? | i2:?, i2:? |
| `MacSpec-ungenerated-key.txt` | unchanged | f1:? | f1:? |
| `MacSpec-unsafe-generated-key.txt` | unchanged | — | — |
| `MacSpec-update-then-encrypt.txt` | unchanged | i2:?, i2:? | i2:?, i2:? |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-d15-hmacpbesha1.txt` (A) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-d15-hmacpbesha1.txt` (B) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-decrypt-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-decrypt-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-decrypt-buffer.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-decrypt-buffer.txt` (B) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-encrypted-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-encrypted-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-encrypted-buffer.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-encrypted-buffer.txt` (B) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-fresh-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-fresh-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-fresh-buffer.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-fresh-buffer.txt` (B) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-mac-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `MacSpec-mac-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `MacSpec-mac-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-ungenerated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-ungenerated-key.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-update-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `MacSpec-update-then-encrypt.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `MacSpec-update-then-encrypt.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
