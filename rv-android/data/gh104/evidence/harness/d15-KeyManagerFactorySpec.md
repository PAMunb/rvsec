# KeyManagerFactorySpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyManagerFactorySpec-guard-on-field.txt` | unchanged | KeyManagerFactorySpec.init | KeyManagerFactorySpec.init |
| `KeyManagerFactorySpec-loaded-keystore.txt` | unchanged | — | — |
| `KeyManagerFactorySpec-managers-taken-twice.txt` | unchanged | KeyManagerFactorySpec.gkm1 | KeyManagerFactorySpec.gkm1 |
| `KeyManagerFactorySpec.txt` | unchanged | KeyManagerFactorySpec.init | KeyManagerFactorySpec.init |

## Envelopes

- `KeyManagerFactorySpec-guard-on-field.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
- `KeyManagerFactorySpec-guard-on-field.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (A) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=gkm1 obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec-managers-taken-twice.txt` (B) `spec=KeyManagerFactorySpec,ev=gkm1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYMANAGERFACTORY-ORDER-00 ev=gkm1 obj=KeyManagerFactory val='' exp='' msg='the observed call sequence is not one KeyManagerFactorySpec accepts'`
- `KeyManagerFactorySpec.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
- `KeyManagerFactorySpec.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=KEYMANAGERFACTORY-NOBS-00 ev=init obj=KeyManagerFactory val='PKIX' exp='a KeyStore this instrumentation observed being loaded' msg='no loading of the KeyStore given to KeyManagerFactory.init was observed'`
