# PBEParameterSpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
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
