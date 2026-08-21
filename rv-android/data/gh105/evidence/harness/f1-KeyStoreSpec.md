# KeyStoreSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | unchanged | — | — |
| `KeyStoreSpec-guard-on-field.txt` | unchanged | KeyStoreSpec.load, KeyStoreSpec.gk1 | KeyStoreSpec.load, KeyStoreSpec.gk1 |
| `KeyStoreSpec-jks.txt` | unchanged | KeyStoreSpec.load, KeyStoreSpec.gk1 | KeyStoreSpec.load, KeyStoreSpec.gk1 |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=gk1 obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-jks.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-jks.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=v=1 code=KEYSTORE-KSTYPE-00 ev=gk1 obj=KeyStore val='JKS' exp='AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore' msg='expecting one of AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore but found JKS'`
- `KeyStoreSpec-jks.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYSTORE-ORDER-00 ev=load obj=KeyStore val='' exp='' msg='the observed call sequence is not one KeyStoreSpec accepts'`
- `KeyStoreSpec-jks.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=v=1 code=KEYSTORE-KSTYPE-00 ev=gk1 obj=KeyStore val='JKS' exp='AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore' msg='expecting one of AndroidKeyStore,PKCS12,BKS,BouncyCastle,AndroidCAStore but found JKS'`
