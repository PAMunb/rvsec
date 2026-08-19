# MacSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-guard-on-field.txt` | unchanged | MacSpec.i1 | MacSpec.i1 |
| `MacSpec-hmacpbesha1.txt` | introduced | — | MacSpec.i1 |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-guard-on-field.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
