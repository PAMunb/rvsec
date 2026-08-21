# RandomStringPasswordSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `RandomStringPasswordSpec-bytes-route.txt` | introduced | — | PBEKeySpecSpec.c1 |
| `RandomStringPasswordSpec-int-route.txt` | introduced | — | PBEKeySpecSpec.c1 |
| `RandomStringPasswordSpec.txt` | unchanged | — | — |

## Envelopes

- `RandomStringPasswordSpec-bytes-route.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-00 ev=c1 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
- `RandomStringPasswordSpec-int-route.txt` (B) `spec=PBEKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PBEKEYSPEC-NOBS-00 ev=c1 obj=PBEKeySpec val='' exp='a randomized char[]' msg='the first argument was not observed to come from a randomized source'`
