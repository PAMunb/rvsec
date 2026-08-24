# IvParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/f3df4e36-cdd1-4c58-a57b-9ec2804d6c42/scratchpad/before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-offset-unrandomised.txt` | unchanged | c2:IVPARAMETERSPEC-NOBS-01 | c2:IVPARAMETERSPEC-NOBS-01 |
| `IvParameterSpecSpec-offset.txt` | unchanged | — | — |
| `IvParameterSpecSpec-unrandomised.txt` | unchanged | c1:IVPARAMETERSPEC-NOBS-00 | c1:IVPARAMETERSPEC-NOBS-00 |
| `IvParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-01 ev=c2 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[], int, int) was observed'`
- `IvParameterSpecSpec-offset-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-01 ev=c2 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[], int, int) was observed'`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvParameterSpecSpec-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
