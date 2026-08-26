# CipherInputStreamSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherInputStreamSpec-two-streams.txt` | removed | c1:CIPHERINPUTSTREAM-ORDER-00, cl1:CIPHERINPUTSTREAM-ORDER-00, r1:CIPHERINPUTSTREAM-ORDER-00 | — |
| `CipherInputStreamSpec-unclosed.txt` | unchanged | — | — |
| `CipherInputStreamSpec.txt` | unchanged | — | — |

## Envelopes

- `CipherInputStreamSpec-two-streams.txt` (A) `spec=CipherInputStreamSpec,ev=c1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHERINPUTSTREAM-ORDER-00 ev=c1 obj=CipherInputStream val='' exp='' msg='the observed call sequence is not one CipherInputStreamSpec accepts'`
- `CipherInputStreamSpec-two-streams.txt` (A) `spec=CipherInputStreamSpec,ev=r1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHERINPUTSTREAM-ORDER-00 ev=r1 obj=CipherInputStream val='' exp='' msg='the observed call sequence is not one CipherInputStreamSpec accepts'`
- `CipherInputStreamSpec-two-streams.txt` (A) `spec=CipherInputStreamSpec,ev=cl1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHERINPUTSTREAM-ORDER-00 ev=cl1 obj=CipherInputStream val='' exp='' msg='the observed call sequence is not one CipherInputStreamSpec accepts'`
