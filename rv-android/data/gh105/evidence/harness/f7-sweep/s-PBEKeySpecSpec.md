# PBEKeySpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PBEKeySpecSpec-conforming.txt` | removed | c2:PBEKEYSPEC-ORDER-00, err2:PBEKEYSPEC-CONSTR-01, err2:PBEKEYSPEC-ORDER-00 | — |
| `PBEKeySpecSpec-forbidden-then-clear.txt` | moved | c2:PBEKEYSPEC-ORDER-00, f1:PBEKEYSPEC-FORB-00, f1:PBEKEYSPEC-ORDER-00 | c2:PBEKEYSPEC-ORDER-00, f1:PBEKEYSPEC-FORB-00 |
| `PBEKeySpecSpec-forbidden.txt` | moved | f1:PBEKEYSPEC-FORB-00, f1:PBEKEYSPEC-ORDER-00 | f1:PBEKEYSPEC-FORB-00 |
| `PBEKeySpecSpec-forbidden3.txt` | moved | f2:PBEKEYSPEC-FORB-01, f2:PBEKEYSPEC-ORDER-00 | f2:PBEKEYSPEC-FORB-01 |
| `PBEKeySpecSpec-lowiter.txt` | moved | err1:PBEKEYSPEC-CONSTR-00, err1:PBEKEYSPEC-ORDER-00, err2:PBEKEYSPEC-CONSTR-01, err2:PBEKEYSPEC-ORDER-00, err3:PBEKEYSPEC-CONSTR-02, err3:PBEKEYSPEC-ORDER-00 | c1:PBEKEYSPEC-CONSTR-00, c1:PBEKEYSPEC-NOBS-01 |
| `PBEKeySpecSpec-salt-only.txt` | removed | c2:PBEKEYSPEC-ORDER-00, err2:PBEKEYSPEC-CONSTR-01, err2:PBEKEYSPEC-ORDER-00 | — |
| `PBEKeySpecSpec.txt` | moved | c2:PBEKEYSPEC-ORDER-00, err2:PBEKEYSPEC-CONSTR-01, err2:PBEKEYSPEC-ORDER-00, err3:PBEKEYSPEC-CONSTR-02, err3:PBEKEYSPEC-ORDER-00 | c1:PBEKEYSPEC-NOBS-01 |

## Envelopes

- `PBEKeySpecSpec-conforming.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-01 ev=err2 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-conforming.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-conforming.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=f1 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden-then-clear.txt` (B) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden.txt` (A) `spec=PBEKeySpecSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=f1 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden.txt` (B) `spec=PBEKeySpecSpec,ev=f1,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-00 ev=f1 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[]) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-forbidden3.txt` (A) `spec=PBEKeySpecSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=f2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-forbidden3.txt` (B) `spec=PBEKeySpecSpec,ev=f2,type=ForbiddenMethod,msg=v=1 code=PBEKEYSPEC-FORB-01 ev=f2 obj=PBEKeySpec val='' exp='PBEKeySpec(char[], byte[], int, int)' msg='PBEKeySpec(char[], byte[], int) is forbidden by api30 PBEKeySpec.cryptsl'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-00 ev=err1 obj=PBEKeySpec val='1000' exp='>= 10000' msg='the third argument should be >= 10000'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err1 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-01 ev=err2 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err3,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-02 ev=err3 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-lowiter.txt` (A) `spec=PBEKeySpecSpec,ev=err3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err3 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-00 ev=c1 obj=PBEKeySpec val='1000' exp='>= 10000' msg='the third argument should be >= 10000'`
- `PBEKeySpecSpec-lowiter.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-salt-only.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-01 ev=err2 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec-salt-only.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec-salt-only.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-01 ev=err2 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err3,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-CONSTR-02 ev=err3 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=err3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=err3 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec.txt` (A) `spec=PBEKeySpecSpec,ev=c2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=PBEKEYSPEC-ORDER-00 ev=c2 obj=PBEKeySpec val='' exp='' msg='the observed call sequence is not one PBEKeySpecSpec accepts'`
- `PBEKeySpecSpec.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-01 ev=c1 obj=PBEKeySpec val='' exp='a randomized byte[]' msg='the second argument was not observed to come from a randomized source'`
