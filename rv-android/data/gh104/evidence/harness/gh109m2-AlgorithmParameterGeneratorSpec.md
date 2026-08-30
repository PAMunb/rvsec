# AlgorithmParameterGeneratorSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `AlgorithmParameterGeneratorSpec-badsize.txt` | introduced | — | initSize:ALGORITHMPARAMETERGENERATOR-KEYSIZE-00 |
| `AlgorithmParameterGeneratorSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `AlgorithmParameterGeneratorSpec-badsize.txt` (A) `AlgorithmParameterGenerator.getInstance("DSA") -> apg`
- `AlgorithmParameterGeneratorSpec-badsize.txt` (A) `apg.init(1024)`
- `AlgorithmParameterGeneratorSpec-badsize.txt` (A) `apg.generateParameters()`
- `AlgorithmParameterGeneratorSpec.txt` (A) `AlgorithmParameterGenerator.getInstance("DSA") -> apg`
- `AlgorithmParameterGeneratorSpec.txt` (A) `apg.init(2048)`
- `AlgorithmParameterGeneratorSpec.txt` (A) `apg.generateParameters()`

## Envelopes

- `AlgorithmParameterGeneratorSpec-badsize.txt` (B) `spec=AlgorithmParameterGeneratorSpec,ev=initSize,type=InvalidKeySize,msg=v=1 code=ALGORITHMPARAMETERGENERATOR-KEYSIZE-00 ev=initSize obj=AlgorithmParameterGenerator val='1024' exp='[2048, 3072]' msg='the parameter size is not one the expert AlgorithmParameterGenerator.crysl admits'`
