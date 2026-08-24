# KeyManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-d15-sunx509.txt` | unchanged | init:?, init:? | init:?, init:? |
| `KeyManagerFactorySpec-guard-on-field.txt` | unchanged | init:?, init:? | init:?, init:? |
| `KeyManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `KeyManagerFactorySpec-managers-taken-twice.txt` | unchanged | gkm1:? | gkm1:? |
| `KeyManagerFactorySpec.txt` | unchanged | — | — |

## Envelopes

- `KeyManagerFactorySpec-d15-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `KeyManagerFactorySpec-d15-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-d15-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `KeyManagerFactorySpec-d15-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (A) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (B) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=unknown`
