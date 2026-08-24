# SSLContextSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-sslv3-no-init.txt` | unchanged | — | — |
| `SSLContextSpec-sslv3.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec-tls-chain.txt` | unchanged | — | — |
| `SSLContextSpec-tls.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |
| `SSLContextSpec.txt` | unchanged | SSLContextSpec.init | SSLContextSpec.init |

## Lines no pointcut resolved

- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
