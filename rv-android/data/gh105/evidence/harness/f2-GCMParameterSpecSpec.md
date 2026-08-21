# GCMParameterSpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `GCMParameterSpecSpec-badtaglen.txt` | introduced | — | GCMParameterSpecSpec.c1 |
| `GCMParameterSpecSpec-second-overload-badtaglen.txt` | introduced | — | GCMParameterSpecSpec.c2 |
| `GCMParameterSpecSpec-second-overload-unrandomised.txt` | introduced | — | GCMParameterSpecSpec.c2 |
| `GCMParameterSpecSpec-second-overload.txt` | unchanged | — | — |
| `GCMParameterSpecSpec-unrandomised.txt` | introduced | — | GCMParameterSpecSpec.c1 |
| `GCMParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `GCMParameterSpecSpec-badtaglen.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-00 ev=c1 obj=GCMParameterSpec val='64' exp='a tag length api30 GCMParameterSpec.cryptsl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-second-overload-badtaglen.txt` (B) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-02 ev=c2 obj=GCMParameterSpec val='64' exp='a tag length api30 GCMParameterSpec.cryptsl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-second-overload-unrandomised.txt` (B) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-01 ev=c2 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `GCMParameterSpecSpec-unrandomised.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-00 ev=c1 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
