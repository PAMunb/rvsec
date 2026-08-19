# TrustManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `TrustManagerFactorySpec-guard-on-field.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-pkix-init.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-x509.txt` | moved | TrustManagerFactorySpec.g3, TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec.txt` | unchanged | TrustManagerFactorySpec.gtm1 | TrustManagerFactorySpec.gtm1 |

## Envelopes

- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `TrustManagerFactorySpec-x509.txt` (A) `spec=TrustManagerFactorySpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec-x509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found X509.`
- `TrustManagerFactorySpec-x509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found X509.`
- `TrustManagerFactorySpec.txt` (A) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec.txt` (B) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=unknown`
