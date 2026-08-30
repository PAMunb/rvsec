# SSLEngineSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLEngineSpec-suite-outside.txt` | introduced | — | ec1:SSLENGINE-ALG-01 |
| `SSLEngineSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SSLEngineSpec-suite-outside.txt` (A) `eng.setEnabledProtocols(strings("TLSv1.3"))`
- `SSLEngineSpec-suite-outside.txt` (A) `eng.setEnabledCipherSuites(strings("TLS_CHACHA20_POLY1305_SHA256"))`
- `SSLEngineSpec.txt` (A) `eng.setEnabledProtocols(strings("TLSv1.3"))`
- `SSLEngineSpec.txt` (A) `eng.setEnabledCipherSuites(strings("TLS_AES_128_GCM_SHA256"))`

## Envelopes

- `SSLEngineSpec-suite-outside.txt` (B) `spec=SSLEngineSpec,ev=ec1,type=UnsafeAlgorithm,msg=v=1 code=SSLENGINE-ALG-01 ev=ec1 obj=SSLEngine val='TLS_CHACHA20_POLY1305_SHA256' exp='a cipher suite the expert SSLEngine.crysl admits beside TLSv1.3' msg='the enabled cipher suites are not ones the expert SSLEngine.crysl admits beside that protocol'`
