# KeyManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-guard-on-field.txt` | unchanged | KeyManagerFactorySpec.init | KeyManagerFactorySpec.init |
| `KeyManagerFactorySpec.txt` | unchanged | — | — |

## Envelopes

- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=init obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
