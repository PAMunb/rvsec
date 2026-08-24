# PBEKeySpecSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEKeySpecSpec-conforming.txt` | unchanged | err2:?, err2:? | err2:?, err2:? |
| `PBEKeySpecSpec-forbidden-then-clear.txt` | unchanged | f1:? | f1:? |
| `PBEKeySpecSpec-forbidden.txt` | unchanged | f1:? | f1:? |
| `PBEKeySpecSpec-forbidden3.txt` | unchanged | f2:? | f2:? |
| `PBEKeySpecSpec-lowiter.txt` | unchanged | err1:?, err1:? | err1:?, err1:? |
| `PBEKeySpecSpec-salt-only.txt` | unchanged | err2:?, err2:? | err2:?, err2:? |
| `PBEKeySpecSpec.txt` | unchanged | err2:?, err2:? | err2:?, err2:? |

## Envelopes

- `PBEKeySpecSpec-conforming.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec-conforming.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-conforming.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec-conforming.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-forbidden3.txt` (B) `spec=PBEKeySpecSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err1,type=UnsatisfiedConstraint,msg=third argument should be >= 1000`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=err1,type=UnsatisfiedConstraint,msg=third argument should be >= 1000`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=err1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-salt-only.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec-salt-only.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec-salt-only.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec-salt-only.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=first argument should have been randomized`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=unknown`
