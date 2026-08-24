# TrustManagerFactorySpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `TrustManagerFactorySpec-guard-on-field.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-managers-taken-twice.txt` | unchanged | TrustManagerFactorySpec.gtm1 | TrustManagerFactorySpec.gtm1 |
| `TrustManagerFactorySpec-pkix-init.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-sunx509-no-init.txt` | unchanged | — | — |
| `TrustManagerFactorySpec-sunx509.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-unloaded-keystore.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec-x509.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |
| `TrustManagerFactorySpec.txt` | unchanged | TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |

## Envelopes

- `TrustManagerFactorySpec-guard-on-field.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-guard-on-field.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-managers-taken-twice.txt` (A) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=gtm1 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-managers-taken-twice.txt` (B) `spec=TrustManagerFactorySpec,ev=gtm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=TRUSTMANAGERFACTORY-ORDER-00 ev=gtm1 obj=TrustManagerFactory val='' exp='' msg='the observed call sequence is not one TrustManagerFactorySpec accepts'`
- `TrustManagerFactorySpec-pkix-init.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-pkix-init.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=v=1 code=TRUSTMANAGERFACTORY-ALG-00 ev=init obj=TrustManagerFactory val='SunX509' exp='PKIX' msg='expecting one of PKIX but found SunX509'`
- `TrustManagerFactorySpec-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='SunX509' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-unloaded-keystore.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-unloaded-keystore.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-x509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='X509' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec-x509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='X509' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
- `TrustManagerFactorySpec.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=TRUSTMANAGERFACTORY-NOBS-00 ev=init obj=TrustManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to TrustManagerFactory.init was observed'`
