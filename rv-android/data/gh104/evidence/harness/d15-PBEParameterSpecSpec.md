# PBEParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | unchanged | PBEParameterSpecSpec.c1 | PBEParameterSpecSpec.c1 |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | unchanged | PBEParameterSpecSpec.c2 | PBEParameterSpecSpec.c2 |
| `PBEParameterSpecSpec-threearg-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg.txt` | unchanged | PBEParameterSpecSpec.c2 | PBEParameterSpecSpec.c2 |
| `PBEParameterSpecSpec.txt` | unchanged | PBEParameterSpecSpec.c1 | PBEParameterSpecSpec.c1 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-threearg-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-02 ev=c2 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-threearg-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-02 ev=c2 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-threearg.txt` (A) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-01 ev=c2 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-threearg.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-01 ev=c2 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
