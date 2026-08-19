# SSLContextSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls.txt` | unchanged | SSLContextSpec.unsafe_protocol, SSLContextSpec.init | SSLContextSpec.unsafe_protocol, SSLContextSpec.init |
| `SSLContextSpec.txt` | unchanged | — | — |

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found TLS.`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found TLS.`
