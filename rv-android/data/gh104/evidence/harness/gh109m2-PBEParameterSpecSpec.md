# PBEParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | unchanged | c1:PBEPARAMETERSPEC-CONSTR-00, c1:PBEPARAMETERSPEC-NOBS-00 | c1:PBEPARAMETERSPEC-CONSTR-00, c1:PBEPARAMETERSPEC-NOBS-00 |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | unchanged | c2:PBEPARAMETERSPEC-CONSTR-02 | c2:PBEPARAMETERSPEC-CONSTR-02 |
| `PBEParameterSpecSpec-threearg-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg.txt` | unchanged | c2:PBEPARAMETERSPEC-NOBS-01 | c2:PBEPARAMETERSPEC-NOBS-01 |
| `PBEParameterSpecSpec.txt` | unchanged | c1:PBEPARAMETERSPEC-NOBS-00 | c1:PBEPARAMETERSPEC-NOBS-00 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c1 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c1 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-threearg-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-02 ev=c2 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-threearg-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-02 ev=c2 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-threearg.txt` (A) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-01 ev=c2 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-threearg.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-01 ev=c2 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
