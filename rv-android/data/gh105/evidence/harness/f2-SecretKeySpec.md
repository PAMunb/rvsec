# SecretKeySpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpec-encoded-iv.txt` | unchanged | — | — |
| `SecretKeySpec-hardcoded-iv.txt` | moved | SecretKeySpecSpec.c3, IvParameterSpecSpec.c3 | SecretKeySpecSpec.c1, IvParameterSpecSpec.c1 |
| `SecretKeySpec-keygen-iv.txt` | introduced | — | IvParameterSpecSpec.c1 |
| `SecretKeySpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpec-hardcoded-iv.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpec-hardcoded-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `SecretKeySpec-keygen-iv.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
