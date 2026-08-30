# CertPathTrustManagerParametersSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 1

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CertPathTrustManagerParametersSpec-unobserved-params.txt` | introduced | — | c1:CERTPATHTRUSTMANAGERPARAMETERS-NOBS-00, c1:PKIXPARAMETERS-NOBS-00 |

## Lines no pointcut resolved

- `CertPathTrustManagerParametersSpec-unobserved-params.txt` (A) `new PKIXParameters(ks) -> cpp`
- `CertPathTrustManagerParametersSpec-unobserved-params.txt` (A) `new CertPathTrustManagerParameters(cpp) -> params`

## Envelopes

- `CertPathTrustManagerParametersSpec-unobserved-params.txt` (B) `spec=PKIXParametersSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=PKIXPARAMETERS-NOBS-00 ev=c1 obj=PKIXParameters val='' exp='a key store the monitor observed being loaded' msg='no load of the key store was observed'`
- `CertPathTrustManagerParametersSpec-unobserved-params.txt` (B) `spec=CertPathTrustManagerParametersSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=CERTPATHTRUSTMANAGERPARAMETERS-NOBS-00 ev=c1 obj=CertPathTrustManagerParameters val='' exp='cert path parameters the monitor observed being built' msg='no construction of the cert path parameters was observed'`
