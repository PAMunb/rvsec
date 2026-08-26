# KeyManagerFactorySpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-d15-sunx509.txt` | moved | init:KEYMANAGERFACTORY-ALG-00, init:KEYMANAGERFACTORY-ORDER-00 | init:KEYMANAGERFACTORY-NOBS-00, init:KEYMANAGERFACTORY-ORDER-00 |
| `KeyManagerFactorySpec-guard-on-field.txt` | moved | init:KEYMANAGERFACTORY-ORDER-00 | init:KEYMANAGERFACTORY-NOBS-00, init:KEYMANAGERFACTORY-ORDER-00 |
| `KeyManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `KeyManagerFactorySpec-managers-taken-twice.txt` | unchanged | gkm1:KEYMANAGERFACTORY-ORDER-00 | gkm1:KEYMANAGERFACTORY-ORDER-00 |
| `KeyManagerFactorySpec.txt` | introduced | — | init:KEYMANAGERFACTORY-NOBS-00 |

## Envelopes

- `KeyManagerFactorySpec-d15-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=v=1 code=KEYMANAGERFACTORY-ALG-00 ev=init obj=KeyManagerFactory val='SunX509' exp='PKIX' msg='expecting one of PKIX but found SunX509'`
- `KeyManagerFactorySpec-d15-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=init obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-d15-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='SunX509' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
- `KeyManagerFactorySpec-d15-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=init obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=init obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=init obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (A) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=gkm1 obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (B) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=gkm1 obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
