# KeyManagerFactorySpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-guard-on-field.txt` | unchanged | KeyManagerFactorySpec.init | KeyManagerFactorySpec.init |
| `KeyManagerFactorySpec.txt` | unchanged | — | — |

## Envelopes

- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
