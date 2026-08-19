# KeyStoreSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | unchanged | KeyStoreSpec.load, KeyStoreSpec.gk1 | KeyStoreSpec.load, KeyStoreSpec.gk1 |
| `KeyStoreSpec-jks.txt` | unchanged | — | — |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=unknown`
