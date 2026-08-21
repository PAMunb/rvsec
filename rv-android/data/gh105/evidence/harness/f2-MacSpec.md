# MacSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-guard-on-field.txt` | introduced | — | MacSpec.i1 |
| `MacSpec-hmacpbesha1.txt` | moved | MacSpec.f1 | MacSpec.i1, MacSpec.f1 |
| `MacSpec-ungenerated-key.txt` | removed | MacSpec.f1 | — |
| `MacSpec-unsafe-generated-key.txt` | unchanged | MacSpec.i1, MacSpec.f1 | MacSpec.i1, MacSpec.f1 |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-ungenerated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
