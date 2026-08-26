# IvParameterSpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-offset-unrandomised.txt` | moved | c4:IVPARAMETERSPEC-CONSTR-01, c4:IVPARAMETERSPEC-ORDER-00 | c2:IVPARAMETERSPEC-NOBS-01 |
| `IvParameterSpecSpec-offset.txt` | unchanged | — | — |
| `IvParameterSpecSpec-unrandomised.txt` | moved | c3:IVPARAMETERSPEC-CONSTR-00, c3:IVPARAMETERSPEC-ORDER-00 | c1:IVPARAMETERSPEC-NOBS-00 |
| `IvParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c4,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-01 ev=c4 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[], int, int) was not observed to come from a randomized source'`
- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c4,type=InvalidSequenceOfMethodCalls,msg=v=1 code=IVPARAMETERSPEC-ORDER-00 ev=c4 obj=IvParameterSpec val='' exp='' msg='the observed call sequence is not one IvParameterSpecSpec accepts'`
- `IvParameterSpecSpec-offset-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-01 ev=c2 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[], int, int) was observed'`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=IVPARAMETERSPEC-ORDER-00 ev=c3 obj=IvParameterSpec val='' exp='' msg='the observed call sequence is not one IvParameterSpecSpec accepts'`
- `IvParameterSpecSpec-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
