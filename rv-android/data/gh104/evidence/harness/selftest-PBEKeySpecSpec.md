# PBEKeySpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEKeySpecSpec-forbidden.txt` | unchanged | PBEKeySpecSpec.f1 | PBEKeySpecSpec.f1 |
| `PBEKeySpecSpec-forbidden3.txt` | unchanged | PBEKeySpecSpec.f2 | PBEKeySpecSpec.f2 |
| `PBEKeySpecSpec-lowiter.txt` | unchanged | PBEKeySpecSpec.err1 | PBEKeySpecSpec.err1 |
| `PBEKeySpecSpec.txt` | unchanged | PBEKeySpecSpec.err2 | PBEKeySpecSpec.err2 |

## Envelopes

- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden3.txt` (B) `spec=PBEKeySpecSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err1,type=UnsatisfiedConstraint,msg=third argument should be >= 1000`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=err1,type=UnsatisfiedConstraint,msg=third argument should be >= 1000`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
