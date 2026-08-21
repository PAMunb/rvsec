# SSLContextSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls.txt` | unchanged | — | — |
| `SSLContextSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
