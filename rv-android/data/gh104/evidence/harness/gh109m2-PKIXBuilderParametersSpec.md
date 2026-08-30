# PKIXBuilderParametersSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 1

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `PKIXBuilderParametersSpec-unobserved-truststore.txt` | introduced | — | c1:PKIXBUILDERPARAMETERS-NOBS-00 |

## Lines no pointcut resolved

- `PKIXBuilderParametersSpec-unobserved-truststore.txt` (A) `new PKIXBuilderParameters(ks, null) -> params`

## Envelopes

- `PKIXBuilderParametersSpec-unobserved-truststore.txt` (B) `spec=PKIXBuilderParametersSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PKIXBUILDERPARAMETERS-NOBS-00 ev=c1 obj=PKIXBuilderParameters val='' exp='a key store the monitor observed being loaded' msg='no load of the key store was observed'`
