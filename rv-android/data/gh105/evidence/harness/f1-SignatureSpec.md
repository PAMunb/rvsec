# SignatureSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-initsign-after-sign.txt` | unchanged | — | — |
| `SignatureSpec-sign-unobserved.txt` | unchanged | SignatureSpec.s1 | SignatureSpec.s1 |
| `SignatureSpec.txt` | unchanged | — | — |

## Envelopes

- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (B) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
