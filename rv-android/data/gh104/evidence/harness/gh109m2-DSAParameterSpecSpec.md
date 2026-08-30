# DSAParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `DSAParameterSpecSpec-short-prime.txt` | introduced | — | c1:DSAPARAMETERSPEC-CONSTR-00 |
| `DSAParameterSpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `DSAParameterSpecSpec-short-prime.txt` (A) `new DSAParameterSpec(bits(1024), bits(2048), bits(2048)) -> params`
- `DSAParameterSpecSpec.txt` (A) `new DSAParameterSpec(bits(2048), bits(2048), bits(2048)) -> params`

## Envelopes

- `DSAParameterSpecSpec-short-prime.txt` (B) `spec=DSAParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=DSAPARAMETERSPEC-CONSTR-00 ev=c1 obj=DSAParameterSpec val='1024' exp='a prime modulus of 2048 bits or more' msg='the dsa prime modulus is shorter than the rule intends'`
