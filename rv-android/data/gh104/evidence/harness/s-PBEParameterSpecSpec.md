# PBEParameterSpecSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | unchanged | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c3 |
| `PBEParameterSpecSpec.txt` | unchanged | PBEParameterSpecSpec.c3 | PBEParameterSpecSpec.c3 |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
