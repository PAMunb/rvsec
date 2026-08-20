# TrustManagerFactorySpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `TrustManagerFactorySpec-guard-on-field.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-pkix-init.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-x509.txt` | unchanged | — | — |
| `TrustManagerFactorySpec.txt` | unchanged | TrustManagerFactorySpec.gtm1 | TrustManagerFactorySpec.gtm1 |

## Self-contradicting envelopes

- `TrustManagerFactorySpec-guard-on-field.txt` — b: self-contradicting envelope -- val ∈ exp: observed 'pkix' is listed in ['pkix']

## Envelopes

- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX but found .`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=v=1 code=TRUSTMANAGERFACTORY-ALG-00 ev=init obj=TrustManagerFactory val='PKIX' exp='PKIX' msg='expecting one of PKIX but found PKIX'`
- `TrustManagerFactorySpec.txt` (A) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `TrustManagerFactorySpec.txt` (B) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=gtm1 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
