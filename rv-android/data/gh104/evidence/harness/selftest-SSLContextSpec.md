# SSLContextSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-d15-ssl.txt` | unchanged | init:?, init:? | init:?, init:? |
| `SSLContextSpec-d15-tlsv1.txt` | unchanged | init:?, init:? | init:?, init:? |
| `SSLContextSpec-guard-on-field.txt` | unchanged | init:?, init:? | init:?, init:? |
| `SSLContextSpec-sslv3-no-init.txt` | unchanged | unsafe_protocol:? | unsafe_protocol:? |
| `SSLContextSpec-sslv3.txt` | unchanged | init:?, unsafe_protocol:? | init:?, unsafe_protocol:? |
| `SSLContextSpec-tls-chain.txt` | unchanged | — | — |
| `SSLContextSpec-tls.txt` | unchanged | init:?, unsafe_protocol:? | init:?, unsafe_protocol:? |
| `SSLContextSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SSLContextSpec-tls-chain.txt` — `tmf.getTrustManagers() -> tms`
- `SSLContextSpec-tls-chain.txt` — `tmf.getTrustManagers() -> tms`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-d15-ssl.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-d15-ssl.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-d15-tlsv1.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-d15-tlsv1.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-sslv3-no-init.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-sslv3-no-init.txt` (B) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found SSLv3.`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found SSLv3.`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found TLS.`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found TLS.`
