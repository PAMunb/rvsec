# IvParameterSpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-offset-unrandomised.txt` | moved | IvParameterSpecSpec.c4 | IvParameterSpecSpec.c2 |
| `IvParameterSpecSpec-offset.txt` | introduced | — | IvParameterSpecSpec.c2 |
| `IvParameterSpecSpec-unrandomised.txt` | moved | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c1 |
| `IvParameterSpecSpec.txt` | introduced | — | IvParameterSpecSpec.c1 |

## Envelopes

- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c4,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-01 ev=c4 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[], int, int) was not observed to come from a randomized source'`
- `IvParameterSpecSpec-offset-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-01 ev=c2 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[], int, int) was observed'`
- `IvParameterSpecSpec-offset.txt` (B) `spec=IvParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-01 ev=c2 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[], int, int) was observed'`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvParameterSpecSpec-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvParameterSpecSpec.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
