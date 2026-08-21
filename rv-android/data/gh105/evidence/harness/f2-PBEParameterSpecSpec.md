# PBEParameterSpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | moved | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c1 |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec.txt` | moved | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c1 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEPARAMETERSPEC-ORDER-00 ev=c3 obj=PBEParameterSpec val='' exp='' msg='the observed call sequence is not one PBEParameterSpecSpec accepts'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c1 obj=PBEParameterSpec val='1000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEPARAMETERSPEC-ORDER-00 ev=c3 obj=PBEParameterSpec val='' exp='' msg='the observed call sequence is not one PBEParameterSpecSpec accepts'`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c1 obj=PBEParameterSpec val='10000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
