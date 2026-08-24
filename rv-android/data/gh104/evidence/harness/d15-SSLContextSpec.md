# SSLContextSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/f3df4e36-cdd1-4c58-a57b-9ec2804d6c42/scratchpad/before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-guard-on-field.txt` | unchanged | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-ORDER-00 |
| `SSLContextSpec-sslv3-no-init.txt` | unchanged | — | — |
| `SSLContextSpec-sslv3.txt` | unchanged | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-PROTO-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-PROTO-00 |
| `SSLContextSpec-tls-chain.txt` | unchanged | — | — |
| `SSLContextSpec-tls.txt` | unchanged | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 |
| `SSLContextSpec.txt` | unchanged | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 |

## Lines no pointcut resolved

- `SSLContextSpec.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='SSLv3' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3' msg='expecting one of Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3 but found SSLv3'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='SSLv3' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='TLSV1.2,TLSV1.3,TLS' msg='expecting one of TLSV1.2,TLSV1.3,TLS but found SSLv3'`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLS' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-tls.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLS' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
