# KeyStoreSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyStoreSpec-androidkeystore.txt` | unchanged | gk1:?, load:? | gk1:?, load:? |
| `KeyStoreSpec-d15-jks.txt` | unchanged | — | — |
| `KeyStoreSpec-d15-pkcs12.txt` | unchanged | — | — |
| `KeyStoreSpec-getkey-iv.txt` | unchanged | — | — |
| `KeyStoreSpec-guard-on-field.txt` | unchanged | gk1:?, load:? | gk1:?, load:? |
| `KeyStoreSpec-jks.txt` | unchanged | — | — |
| `KeyStoreSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=expecting one ofJCEKS,JKS,DKS,PKCS11,PKCS12 but found AndroidKeyStore.`
- `KeyStoreSpec-androidkeystore.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-androidkeystore.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=expecting one ofJCEKS,JKS,DKS,PKCS11,PKCS12 but found AndroidKeyStore.`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-guard-on-field.txt` (A) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=expecting one ofJCEKS,JKS,DKS,PKCS11,PKCS12 but found .`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=load,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyStoreSpec-guard-on-field.txt` (B) `spec=KeyStoreSpec,ev=gk1,type=InvalidKeyStoreType,msg=expecting one ofJCEKS,JKS,DKS,PKCS11,PKCS12 but found .`
