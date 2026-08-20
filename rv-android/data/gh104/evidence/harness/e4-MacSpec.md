# MacSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-guard-on-field.txt` | unchanged | MacSpec.i1 | MacSpec.i1 |
| `MacSpec-hmacpbesha1.txt` | unchanged | MacSpec.i1 | MacSpec.i1 |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-guard-on-field.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
