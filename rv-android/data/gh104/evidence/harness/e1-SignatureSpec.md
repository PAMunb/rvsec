# SignatureSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec.txt` | unchanged | — | — |

## Envelopes

- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
