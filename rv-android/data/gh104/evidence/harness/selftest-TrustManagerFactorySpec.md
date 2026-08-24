# TrustManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 10

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `TrustManagerFactorySpec-d15-sunx509.txt` | unchanged | init:?, init:? | init:?, init:? |
| `TrustManagerFactorySpec-guard-on-field.txt` | unchanged | init:?, init:? | init:?, init:? |
| `TrustManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-managers-taken-twice.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-pkix-init.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-sunx509-no-init.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-sunx509.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-unloaded-keystore.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-x509.txt` | moved | g3:?, init:? | init:?, init:? |
| `TrustManagerFactorySpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec.txt` — `tmf.getTrustManagers()`

## Envelopes

- `TrustManagerFactorySpec-d15-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-d15-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-d15-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-d15-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-x509.txt` (A) `spec=TrustManagerFactorySpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-x509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found X509.`
- `TrustManagerFactorySpec-x509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found X509.`
- `TrustManagerFactorySpec-x509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
