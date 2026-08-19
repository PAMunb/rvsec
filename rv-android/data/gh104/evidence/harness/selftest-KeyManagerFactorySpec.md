# KeyManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-guard-on-field.txt` | unchanged | KeyManagerFactorySpec.init | KeyManagerFactorySpec.init |
| `KeyManagerFactorySpec.txt` | unchanged | — | — |

## Envelopes

- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
