# SignatureSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec.txt` | unchanged | — | — |

## Envelopes

- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
