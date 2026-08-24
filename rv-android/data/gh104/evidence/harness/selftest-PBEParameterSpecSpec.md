# PBEParameterSpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEParameterSpecSpec-lowiter.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |
| `PBEParameterSpecSpec-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg-randomised.txt` | unchanged | — | — |
| `PBEParameterSpecSpec-threearg.txt` | unchanged | — | — |
| `PBEParameterSpecSpec.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |

## Envelopes

- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec-lowiter.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec-lowiter.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec.txt` (A) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=UnsafeAlgorithm,msg=expecting at least 1000 iterations and a randomized salt.`
- `PBEParameterSpecSpec.txt` (B) `spec=PBEParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
