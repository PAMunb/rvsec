# TrustManagerFactorySpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `TrustManagerFactorySpec-guard-on-field.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-managers-taken-twice.txt` | introduced | — | TrustManagerFactorySpec.gtm1 |
| `TrustManagerFactorySpec-pkix-init.txt` | introduced | — | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-sunx509-no-init.txt` | removed | TrustManagerFactorySpec.g3 | — |
| `TrustManagerFactorySpec-sunx509.txt` | moved | TrustManagerFactorySpec.g3, TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-unloaded-keystore.txt` | introduced | — | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-x509.txt` | introduced | — | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec.txt` | introduced | — | TrustManagerFactorySpec.init |

## Lines no pointcut resolved

- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec-managers-taken-twice.txt` — `tmf.getTrustManagers()`
- `TrustManagerFactorySpec.txt` — `tmf.getTrustManagers()`

## Envelopes

- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-managers-taken-twice.txt` (B) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=gtm1 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-pkix-init.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-sunx509-no-init.txt` (A) `spec=TrustManagerFactorySpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=g3 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=g3 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=v=1 code=TRUSTMANAGERFACTORY-ALG-00 ev=init obj=TrustManagerFactory val='SunX509' exp='PKIX' msg='expecting one of PKIX but found SunX509'`
- `TrustManagerFactorySpec-unloaded-keystore.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-x509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='X509' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
