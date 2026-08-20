# SSLContextSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/backup/gh104-group7-pre-e1`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls.txt` | unchanged | — | — |
| `SSLContextSpec.txt` | unchanged | — | — |

## Self-contradicting envelopes

- `SSLContextSpec-guard-on-field.txt` — b: self-contradicting envelope -- val ∈ exp: observed 'tlsv1.2' is listed in ['default', 'ssl', 'tls', 'tlsv1', 'tlsv1.1', 'tlsv1.2', 'tlsv1.3']

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='TLSv1.2' exp='Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3' msg='expecting one of Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3 but found TLSv1.2'`
