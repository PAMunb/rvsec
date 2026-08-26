# SecretKeySpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpec-encoded-iv.txt` | introduced | — | c1:IVPARAMETERSPEC-NOBS-00, c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpec-hardcoded-iv.txt` | moved | c3:IVPARAMETERSPEC-CONSTR-00, c3:IVPARAMETERSPEC-ORDER-00, c3:SECRETKEYSPEC-CONSTR-00, c3:SECRETKEYSPEC-ORDER-00 | c1:IVPARAMETERSPEC-NOBS-00, c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpec-keygen-iv.txt` | introduced | — | c1:IVPARAMETERSPEC-NOBS-00 |
| `SecretKeySpec-laundered-material.txt` | moved | c3:SECRETKEYSPEC-CONSTR-00, c3:SECRETKEYSPEC-ORDER-00 | c1:SECRETKEYSPEC-NOBS-00 |
| `SecretKeySpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpec-encoded-iv.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpec-encoded-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECRETKEYSPEC-ORDER-00 ev=c3 obj=SecretKeySpec val='' exp='' msg='the observed call sequence is not one SecretKeySpecSpec accepts'`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=IVPARAMETERSPEC-ORDER-00 ev=c3 obj=IvParameterSpec val='' exp='' msg='the observed call sequence is not one IvParameterSpecSpec accepts'`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `SecretKeySpec-keygen-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `SecretKeySpec-laundered-material.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpec-laundered-material.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECRETKEYSPEC-ORDER-00 ev=c3 obj=SecretKeySpec val='' exp='' msg='the observed call sequence is not one SecretKeySpecSpec accepts'`
- `SecretKeySpec-laundered-material.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='prepared key material' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()'`
