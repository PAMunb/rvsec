# GCMParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/b29940c9-85c0-4028-8d12-84e61ee6d388/scratchpad/preG1/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `GCMParameterSpecSpec-badtaglen.txt` | unchanged | c1:GCMPARAMETERSPEC-CONSTR-00 | c1:GCMPARAMETERSPEC-CONSTR-00 |
| `GCMParameterSpecSpec-second-overload-badtaglen.txt` | unchanged | c2:GCMPARAMETERSPEC-CONSTR-02 | c2:GCMPARAMETERSPEC-CONSTR-02 |
| `GCMParameterSpecSpec-second-overload-unrandomised.txt` | unchanged | c2:GCMPARAMETERSPEC-NOBS-01 | c2:GCMPARAMETERSPEC-NOBS-01 |
| `GCMParameterSpecSpec-second-overload.txt` | unchanged | — | — |
| `GCMParameterSpecSpec-unrandomised.txt` | unchanged | c1:GCMPARAMETERSPEC-NOBS-00 | c1:GCMPARAMETERSPEC-NOBS-00 |
| `GCMParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `GCMParameterSpecSpec-badtaglen.txt` (A) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-00 ev=c1 obj=GCMParameterSpec val='64' exp='a tag length the expert GCMParameterSpec.crysl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-badtaglen.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-00 ev=c1 obj=GCMParameterSpec val='64' exp='a tag length the expert GCMParameterSpec.crysl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-second-overload-badtaglen.txt` (A) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-02 ev=c2 obj=GCMParameterSpec val='64' exp='a tag length the expert GCMParameterSpec.crysl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-second-overload-badtaglen.txt` (B) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-CONSTR-02 ev=c2 obj=GCMParameterSpec val='64' exp='a tag length the expert GCMParameterSpec.crysl admits' msg='the authentication tag length is not one the rule admits'`
- `GCMParameterSpecSpec-second-overload-unrandomised.txt` (A) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-01 ev=c2 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `GCMParameterSpecSpec-second-overload-unrandomised.txt` (B) `spec=GCMParameterSpecSpec,ev=c2,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-01 ev=c2 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `GCMParameterSpecSpec-unrandomised.txt` (A) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-00 ev=c1 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `GCMParameterSpecSpec-unrandomised.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-00 ev=c1 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
