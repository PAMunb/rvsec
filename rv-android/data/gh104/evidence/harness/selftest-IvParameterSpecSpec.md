# IvParameterSpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-offset-unrandomised.txt` | unchanged | c4:?, c4:? | c4:?, c4:? |
| `IvParameterSpecSpec-offset.txt` | unchanged | — | — |
| `IvParameterSpecSpec-unrandomised.txt` | removed | c3:?, c3:? | — |
| `IvParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c4,type=UnsatisfiedConstraint,msg=unknown`
- `IvParameterSpecSpec-offset-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c4,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvParameterSpecSpec-offset-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c4,type=UnsatisfiedConstraint,msg=unknown`
- `IvParameterSpecSpec-offset-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c4,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=unknown`
- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
