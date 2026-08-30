# MGF1ParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MGF1ParameterSpecSpec-sha1.txt` | introduced | — | c1:MGF1PARAMETERSPEC-ALG-00 |
| `MGF1ParameterSpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `MGF1ParameterSpecSpec-sha1.txt` (A) `new MGF1ParameterSpec("SHA-1") -> mgf`
- `MGF1ParameterSpecSpec.txt` (A) `new MGF1ParameterSpec("SHA-256") -> mgf`

## Envelopes

- `MGF1ParameterSpecSpec-sha1.txt` (B) `spec=MGF1ParameterSpecSpec,ev=c1,type=UnsafeAlgorithm,msg=v=1 code=MGF1PARAMETERSPEC-ALG-00 ev=c1 obj=MGF1ParameterSpec val='SHA-1' exp='SHA-256,SHA-384,SHA-512' msg='the mask generation function digest is not one the rule admits'`
