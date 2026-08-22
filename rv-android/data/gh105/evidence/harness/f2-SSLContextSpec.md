# SSLContextSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-sslv3-no-init.txt` | removed | SSLContextSpec.unsafe_protocol | — |
| `SSLContextSpec-sslv3.txt` | moved | SSLContextSpec.unsafe_protocol, SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls-chain.txt` | unchanged | — | — |
| `SSLContextSpec-tls.txt` | introduced | — | SSLContextSpec.init |
| `SSLContextSpec.txt` | introduced | — | SSLContextSpec.init |

## Lines no pointcut resolved

- `SSLContextSpec-tls-chain.txt` — `tmf.getTrustManagers() -> tms`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3-no-init.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
