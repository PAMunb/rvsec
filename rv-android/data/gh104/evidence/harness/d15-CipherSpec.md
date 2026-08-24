# CipherSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/f3df4e36-cdd1-4c58-a57b-9ec2804d6c42/scratchpad/before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | unchanged | i1:CIPHER-ORDER-00, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 | i1:CIPHER-ORDER-00, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 |
| `CipherSpec-keygen-key-mismatch.txt` | unchanged | i2:CIPHER-CONSTR-00 | i2:CIPHER-CONSTR-00 |
| `CipherSpec-keygen-key.txt` | unchanged | — | — |
| `CipherSpec-keystore-key.txt` | unchanged | — | — |
| `CipherSpec-nofinal-arg.txt` | unchanged | f1:CIPHER-ORDER-00, i2:CIPHER-NOBS-00 | f1:CIPHER-ORDER-00, i2:CIPHER-NOBS-00 |
| `CipherSpec-unsafe.txt` | unchanged | f2:CIPHER-ORDER-00, i2:CIPHER-ALG-01, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 | f2:CIPHER-ORDER-00, i2:CIPHER-ALG-01, i2:CIPHER-NOBS-00, i2:CIPHER-ORDER-00 |
| `CipherSpec-update-chain.txt` | unchanged | i2:CIPHER-NOBS-00 | i2:CIPHER-NOBS-00 |
| `CipherSpec.txt` | unchanged | i2:CIPHER-NOBS-00 | i2:CIPHER-NOBS-00 |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-keygen-key-mismatch.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-CONSTR-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='the key given to Cipher.init carries a key-origin predicate the rule does not admit'`
- `CipherSpec-keygen-key-mismatch.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-CONSTR-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='the key given to Cipher.init carries a key-origin predicate the rule does not admit'`
- `CipherSpec-nofinal-arg.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-nofinal-arg.txt` (A) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-nofinal-arg.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-nofinal-arg.txt` (B) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-01 ev=i2 obj=Cipher val='DES' exp='a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl)' msg='expecting a transformation admitted by Api30CipherTransformationUtil (api30 Cipher.cryptsl) but found DES'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=v=1 code=CIPHER-ALG-01 ev=i2 obj=Cipher val='DES' exp='a transformation admitted by CipherTransformationUtil (expert Cipher.crysl)' msg='expecting a transformation admitted by CipherTransformationUtil (expert Cipher.crysl) but found DES'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-update-chain.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-update-chain.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec.txt` (A) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
