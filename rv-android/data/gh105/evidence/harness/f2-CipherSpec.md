# CipherSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | moved | CipherSpec.i1 | CipherSpec.i1, CipherSpec.i2 |
| `CipherSpec-keygen-key-mismatch.txt` | introduced | — | CipherSpec.i2 |
| `CipherSpec-keygen-key.txt` | unchanged | — | — |
| `CipherSpec-keystore-key.txt` | unchanged | — | — |
| `CipherSpec-nofinal-arg.txt` | moved | CipherSpec.f1, CipherSpec.f2 | CipherSpec.i2, CipherSpec.f1 |
| `CipherSpec-unsafe.txt` | moved | CipherSpec.f2 | CipherSpec.i2, CipherSpec.f2 |
| `CipherSpec-update-chain.txt` | moved | CipherSpec.u1, CipherSpec.f1, CipherSpec.f2 | CipherSpec.i2 |
| `CipherSpec.txt` | moved | CipherSpec.f2 | CipherSpec.i2 |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-keygen-key-mismatch.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-CONSTR-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='the key given to Cipher.init carries a key-origin predicate the rule does not admit'`
- `CipherSpec-nofinal-arg.txt` (A) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-nofinal-arg.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-nofinal-arg.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-nofinal-arg.txt` (B) `spec=CipherSpec,ev=f1,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-update-chain.txt` (A) `spec=CipherSpec,ev=u1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=u1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-update-chain.txt` (A) `spec=CipherSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=u1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-update-chain.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-update-chain.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
- `CipherSpec.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=f2 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec.txt` (B) `spec=CipherSpec,ev=i2,type=UnsatisfiedConstraint,msg=v=1 code=CIPHER-NOBS-00 ev=i2 obj=Cipher val='' exp='a key produced by one of the generators the rule names' msg='no generator of the key given to Cipher.init was observed'`
