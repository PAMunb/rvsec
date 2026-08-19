# KeyStoreSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | removed | KeyStoreSpec.load, KeyStoreSpec.gk1 | — |
| `KeyStoreSpec-jks.txt` | introduced | — | KeyStoreSpec.load, KeyStoreSpec.gk1 |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-jks.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-jks.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=unknown`
