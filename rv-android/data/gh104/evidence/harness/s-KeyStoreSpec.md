# KeyStoreSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | unchanged | — | — |
| `KeyStoreSpec-d15-jks.txt` | unchanged | — | — |
| `KeyStoreSpec-d15-pkcs12.txt` | unchanged | — | — |
| `KeyStoreSpec-getkey-iv.txt` | unchanged | c1:IVPARAMETERSPEC-NOBS-00 | c1:IVPARAMETERSPEC-NOBS-00 |
| `KeyStoreSpec-guard-on-field.txt` | unchanged | gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 | gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 |
| `KeyStoreSpec-jks.txt` | unchanged | — | — |
| `KeyStoreSpec-provider-object.txt` | unchanged | — | — |
| `KeyStoreSpec-two-stores.txt` | unchanged | — | — |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyStoreSpec-getkey-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `KeyStoreSpec-getkey-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
