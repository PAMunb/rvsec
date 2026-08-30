# DHParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `DHParameterSpecSpec-short-modulus.txt` | introduced | — | c1:DHPARAMETERSPEC-CONSTR-00 |
| `DHParameterSpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `DHParameterSpecSpec-short-modulus.txt` (A) `new DHParameterSpec(bits(1024), bits(2048)) -> params`
- `DHParameterSpecSpec.txt` (A) `new DHParameterSpec(bits(2048), bits(2048)) -> params`

## Envelopes

- `DHParameterSpecSpec-short-modulus.txt` (B) `spec=DHParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=DHPARAMETERSPEC-CONSTR-00 ev=c1 obj=DHParameterSpec val='1024' exp='a prime modulus of 2048 bits or more' msg='the diffie-hellman prime modulus is shorter than the rule intends'`
