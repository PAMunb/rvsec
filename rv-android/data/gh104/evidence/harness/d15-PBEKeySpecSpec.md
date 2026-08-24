# PBEKeySpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEKeySpecSpec-conforming.txt` | unchanged | — | — |
| `PBEKeySpecSpec-forbidden-then-clear.txt` | unchanged | PBEKeySpecSpec.f1, PBEKeySpecSpec.c2 | PBEKeySpecSpec.f1, PBEKeySpecSpec.c2 |
| `PBEKeySpecSpec-forbidden.txt` | unchanged | PBEKeySpecSpec.f1 | PBEKeySpecSpec.f1 |
| `PBEKeySpecSpec-forbidden3.txt` | unchanged | PBEKeySpecSpec.f2 | PBEKeySpecSpec.f2 |
| `PBEKeySpecSpec-lowiter.txt` | unchanged | PBEKeySpecSpec.c1 | PBEKeySpecSpec.c1 |
| `PBEKeySpecSpec-salt-only.txt` | unchanged | — | — |
| `PBEKeySpecSpec.txt` | unchanged | PBEKeySpecSpec.c1 | PBEKeySpecSpec.c1 |

## Envelopes

- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden3.txt` (B) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
