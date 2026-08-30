# PBEKeySpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEKeySpecSpec-conforming.txt` | unchanged | — | — |
| `PBEKeySpecSpec-forbidden-then-clear.txt` | unchanged | c2:PBEKEYSPEC-ORDER-00, f1:PBEKEYSPEC-FORB-00 | c2:PBEKEYSPEC-ORDER-00, f1:PBEKEYSPEC-FORB-00 |
| `PBEKeySpecSpec-forbidden.txt` | unchanged | f1:PBEKEYSPEC-FORB-00 | f1:PBEKEYSPEC-FORB-00 |
| `PBEKeySpecSpec-forbidden3.txt` | unchanged | f2:PBEKEYSPEC-FORB-01 | f2:PBEKEYSPEC-FORB-01 |
| `PBEKeySpecSpec-lowiter.txt` | unchanged | c1:PBEKEYSPEC-CONSTR-00, c1:PBEKEYSPEC-NOBS-01 | c1:PBEKEYSPEC-CONSTR-00, c1:PBEKEYSPEC-NOBS-01 |
| `PBEKeySpecSpec-salt-only.txt` | unchanged | — | — |
| `PBEKeySpecSpec.txt` | unchanged | c1:PBEKEYSPEC-NOBS-01 | c1:PBEKEYSPEC-NOBS-01 |

## Envelopes

- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-forbidden.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-forbidden3.txt` (B) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by the expert PBEKeySpec.crysl'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-00 ev=c1 obj=PBEKeySpec val='1000' exp='>= 10000' msg='the third argument should be >= 10000'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-00 ev=c1 obj=PBEKeySpec val='1000' exp='>= 10000' msg='the third argument should be >= 10000'`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
