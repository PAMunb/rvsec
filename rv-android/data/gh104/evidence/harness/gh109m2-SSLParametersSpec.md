# SSLParametersSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLParametersSpec-tlsv1.txt` | introduced | — | c3:SSLPARAMETERS-PROTO-00 |
| `SSLParametersSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SSLParametersSpec-tlsv1.txt` (A) `new SSLParameters(strings("TLS_AES_128_GCM_SHA256"), strings("TLSv1")) -> params`
- `SSLParametersSpec.txt` (A) `new SSLParameters(strings("TLS_AES_128_GCM_SHA256"), strings("TLSv1.3")) -> params`

## Envelopes

- `SSLParametersSpec-tlsv1.txt` (B) `spec=SSLParametersSpec,ev=c3,type=UnsafeProtocol,msg=v=1 code=SSLPARAMETERS-PROTO-00 ev=c3 obj=SSLParameters val='TLSv1' exp='TLSv1.2,TLSv1.3' msg='expecting one of TLSv1.2,TLSv1.3 but found TLSv1'`
