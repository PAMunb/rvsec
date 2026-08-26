# KeyStoreSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | unchanged | — | — |
| `KeyStoreSpec-d15-jks.txt` | removed | gk1:KEYSTORE-KSTYPE-00, gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 | — |
| `KeyStoreSpec-d15-pkcs12.txt` | unchanged | — | — |
| `KeyStoreSpec-getkey-iv.txt` | introduced | — | c1:IVPARAMETERSPEC-NOBS-00 |
| `KeyStoreSpec-guard-on-field.txt` | unchanged | gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 | gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 |
| `KeyStoreSpec-jks.txt` | removed | gk1:KEYSTORE-KSTYPE-00, gk1:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 | — |
| `KeyStoreSpec-provider-object.txt` | removed | load:KEYSTORE-ORDER-00 | — |
| `KeyStoreSpec-two-stores.txt` | removed | g2:KEYSTORE-ORDER-00, load:KEYSTORE-ORDER-00 | — |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `KeyStoreSpec-provider-object.txt` — `KeyStore.getInstance("JKS", p) -> ks`

## Envelopes

- `KeyStoreSpec-d15-jks.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-d15-jks.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=v=1 code=KEYSTORE-KSTYPE-00 ev=gk1 obj=KeyStore val='JKS' exp='AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore' msg='expecting one of AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore but found JKS'`
- `KeyStoreSpec-d15-jks.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-getkey-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-jks.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-jks.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=v=1 code=KEYSTORE-KSTYPE-00 ev=gk1 obj=KeyStore val='JKS' exp='AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore' msg='expecting one of AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore but found JKS'`
- `KeyStoreSpec-jks.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-provider-object.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-two-stores.txt` (A) `spec=KeyStoreSpec,ev=g2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=g2 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-two-stores.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
