# MessageDigestSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MessageDigestSpec-guard-on-field.txt` | unchanged | MessageDigestSpec.update | MessageDigestSpec.update |
| `MessageDigestSpec-md5-only.txt` | introduced | — | MessageDigestSpec.g4 |
| `MessageDigestSpec-md5.txt` | moved | MessageDigestSpec.update | MessageDigestSpec.g4, MessageDigestSpec.update |
| `MessageDigestSpec-reset.txt` | unchanged | MessageDigestSpec.reset | MessageDigestSpec.reset |
| `MessageDigestSpec-sha1.txt` | moved | MessageDigestSpec.update | MessageDigestSpec.g4, MessageDigestSpec.update |
| `MessageDigestSpec.txt` | unchanged | — | — |

## Envelopes

- `MessageDigestSpec-guard-on-field.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found .`
- `MessageDigestSpec-guard-on-field.txt` (B) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found .`
- `MessageDigestSpec-md5-only.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `MessageDigestSpec-md5.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `MessageDigestSpec-md5.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `MessageDigestSpec-md5.txt` (B) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `MessageDigestSpec-reset.txt` (A) `spec=MessageDigestSpec,ev=reset,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MessageDigestSpec-reset.txt` (B) `spec=MessageDigestSpec,ev=reset,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MessageDigestSpec-sha1.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1.`
- `MessageDigestSpec-sha1.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1.`
- `MessageDigestSpec-sha1.txt` (B) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1.`
