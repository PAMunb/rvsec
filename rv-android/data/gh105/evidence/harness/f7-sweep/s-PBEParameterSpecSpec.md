# PBEParameterSpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | moved | c3:PBEPARAMETERSPEC-CONSTR-00, c3:PBEPARAMETERSPEC-ORDER-00 | c1:PBEPARAMETERSPEC-CONSTR-00, c1:PBEPARAMETERSPEC-NOBS-00 |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | introduced | — | c2:PBEPARAMETERSPEC-CONSTR-02 |
| `PBEParameterSpecSpec-threearg-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg.txt` | introduced | — | c2:PBEPARAMETERSPEC-NOBS-01 |
| `PBEParameterSpecSpec.txt` | moved | c3:PBEPARAMETERSPEC-CONSTR-00, c3:PBEPARAMETERSPEC-ORDER-00 | c1:PBEPARAMETERSPEC-NOBS-00 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='1000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEPARAMETERSPEC-ORDER-00 ev=c3 obj=PBEParameterSpec val='' exp='' msg='the observed call sequence is not one PBEParameterSpecSpec accepts'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c1 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec-threearg-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-02 ev=c2 obj=PBEParameterSpec val='1000' exp='>= 10000' msg='the iteration count should be >= 10000'`
- `PBEParameterSpecSpec-threearg.txt` (B) `spec=PBEParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-01 ev=c2 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='10000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEPARAMETERSPEC-ORDER-00 ev=c3 obj=PBEParameterSpec val='' exp='' msg='the observed call sequence is not one PBEParameterSpecSpec accepts'`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-NOBS-00 ev=c1 obj=PBEParameterSpec val='' exp='a randomized byte[]' msg='the salt was not observed to come from a randomized source'`
