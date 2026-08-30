# KeyAgreementSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyAgreementSpec-forbidden-namedsecret.txt` | moved | gpr:KEYPAIR-ORDER-00, gpu:KEYPAIR-ORDER-00 | gpr:KEYPAIR-ORDER-00, gpu:KEYPAIR-ORDER-00, gs3:KEYAGREEMENT-FORB-00 |
| `KeyAgreementSpec-nodophase.txt` | moved | gpr:KEYPAIR-ORDER-00 | gpr:KEYPAIR-ORDER-00, gs1:KEYAGREEMENT-ORDER-00 |
| `KeyAgreementSpec.txt` | unchanged | gpr:KEYPAIR-ORDER-00, gpu:KEYPAIR-ORDER-00 | gpr:KEYPAIR-ORDER-00, gpu:KEYPAIR-ORDER-00 |

## Lines no pointcut resolved

- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `KeyAgreement.getInstance("DH") -> ka`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `ka.init(priv)`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `ka.doPhase(pub, true)`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `ka.generateSecret("AES")`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `ka.generateSecret()`
- `KeyAgreementSpec-nodophase.txt` (A) `KeyAgreement.getInstance("DH") -> ka`
- `KeyAgreementSpec-nodophase.txt` (A) `ka.init(priv)`
- `KeyAgreementSpec-nodophase.txt` (A) `ka.generateSecret()`
- `KeyAgreementSpec.txt` (A) `KeyAgreement.getInstance("DH") -> ka`
- `KeyAgreementSpec.txt` (A) `ka.init(priv)`
- `KeyAgreementSpec.txt` (A) `ka.doPhase(pub, true)`
- `KeyAgreementSpec.txt` (A) `ka.generateSecret()`

## Envelopes

- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-forbidden-namedsecret.txt` (B) `spec=KeyAgreementSpec,ev=gs3,type=ForbiddenMethod,msg=v=1 code=KEYAGREEMENT-FORB-00 ev=gs3 obj=KeyAgreement val='AES' exp='KeyAgreement.generateSecret() or KeyAgreement.generateSecret(byte[], int)' msg='the expert KeyAgreement.crysl forbids deriving a named secret key from an agreement'`
- `KeyAgreementSpec-nodophase.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-nodophase.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec-nodophase.txt` (B) `spec=KeyAgreementSpec,ev=gs1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYAGREEMENT-ORDER-00 ev=gs1 obj=KeyAgreement val='' exp='' msg='the observed call sequence is not one KeyAgreementSpec accepts'`
- `KeyAgreementSpec.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyAgreementSpec.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
