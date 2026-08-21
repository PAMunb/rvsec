# SSLContextSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-sslv3-no-init.txt` | removed | SSLContextSpec.unsafe_protocol | — |
| `SSLContextSpec-sslv3.txt` | moved | SSLContextSpec.unsafe_protocol, SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls.txt` | unchanged | — | — |
| `SSLContextSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3-no-init.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3' msg='expecting one of Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3 but found SSLv3'`
