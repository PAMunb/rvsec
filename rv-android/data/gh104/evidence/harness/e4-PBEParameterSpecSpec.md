# PBEParameterSpecSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | unchanged | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c3 |
| `PBEParameterSpecSpec.txt` | unchanged | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c3 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='1000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='1000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='10000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=PBEPARAMETERSPEC-CONSTR-00 ev=c3 obj=PBEParameterSpec val='10000' exp='>= 10000 iterations and a randomized salt' msg='expecting at least 10000 iterations and a randomized salt'`
