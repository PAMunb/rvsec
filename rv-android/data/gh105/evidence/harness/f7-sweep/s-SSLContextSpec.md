# SSLContextSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 12

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SSLContextSpec-d15-ssl.txt` | moved | init:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-ORDER-00, init:SSLCONTEXT-PROTO-00 |
| `SSLContextSpec-d15-tlsv1.txt` | moved | init:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-ORDER-00, init:SSLCONTEXT-PROTO-00 |
| `SSLContextSpec-getdefault-engine.txt` | introduced | — | engine:SSLCONTEXT-ORDER-00, getDefault:SSLCONTEXT-FORB-00 |
| `SSLContextSpec-getdefault.txt` | introduced | — | getDefault:SSLCONTEXT-FORB-00 |
| `SSLContextSpec-guard-on-field.txt` | moved | init:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-ORDER-00 |
| `SSLContextSpec-provider-object.txt` | moved | init:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 |
| `SSLContextSpec-provider-sslv3.txt` | moved | init:SSLCONTEXT-ORDER-00, init:SSLCONTEXT-PROTO-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-PROTO-00 |
| `SSLContextSpec-sslv3-no-init.txt` | removed | unsafe_protocol:SSLCONTEXT-ORDER-00 | — |
| `SSLContextSpec-sslv3.txt` | moved | init:SSLCONTEXT-ORDER-00, init:SSLCONTEXT-PROTO-00, unsafe_protocol:SSLCONTEXT-ORDER-00 | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01, init:SSLCONTEXT-PROTO-00 |
| `SSLContextSpec-tls-chain.txt` | unchanged | — | — |
| `SSLContextSpec-tls.txt` | introduced | — | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 |
| `SSLContextSpec.txt` | introduced | — | init:SSLCONTEXT-NOBS-00, init:SSLCONTEXT-NOBS-01 |

## Lines no pointcut resolved

- `SSLContextSpec-getdefault-engine.txt` — `SSLContext.getDefault() -> ctx`
- `SSLContextSpec-getdefault-engine.txt` — `ctx.createSSLEngine()`
- `SSLContextSpec-getdefault.txt` — `SSLContext.getDefault() -> ctx`
- `SSLContextSpec-provider-object.txt` — `SSLContext.getInstance("TLSv1.2", p) -> ctx`
- `SSLContextSpec-tls-chain.txt` — `tmf.getTrustManagers() -> tms`
- `SSLContextSpec.txt` — `ctx.createSSLEngine()`

## Envelopes

- `SSLContextSpec-d15-ssl.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='SSL' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSL' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-d15-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSL' exp='TLSV1.2,TLSV1.3,TLS' msg='expecting one of TLSV1.2,TLSV1.3,TLS but found SSL'`
- `SSLContextSpec-d15-tlsv1.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-d15-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='TLSv1' exp='TLSV1.2,TLSV1.3,TLS' msg='expecting one of TLSV1.2,TLSV1.3,TLS but found TLSv1'`
- `SSLContextSpec-getdefault-engine.txt` (B) `spec=SSLContextSpec,ev=getDefault,type=ForbiddenMethod,msg=v=1 code=SSLCONTEXT-FORB-00 ev=getDefault obj=SSLContext val='' exp='SSLContext.getInstance(String)' msg='SSLContext.getDefault() is forbidden by api30 SSLContext.cryptsl'`
- `SSLContextSpec-getdefault-engine.txt` (B) `spec=SSLContextSpec,ev=engine,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=engine obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-getdefault.txt` (B) `spec=SSLContextSpec,ev=getDefault,type=ForbiddenMethod,msg=v=1 code=SSLCONTEXT-FORB-00 ev=getDefault obj=SSLContext val='' exp='SSLContext.getInstance(String)' msg='SSLContext.getDefault() is forbidden by api30 SSLContext.cryptsl'`
- `SSLContextSpec-guard-on-field.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-guard-on-field.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-provider-object.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-provider-object.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-provider-object.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-provider-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-provider-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3' msg='expecting one of Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3 but found SSLv3'`
- `SSLContextSpec-provider-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='SSLv3' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-provider-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-provider-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='TLSV1.2,TLSV1.3,TLS' msg='expecting one of TLSV1.2,TLSV1.3,TLS but found SSLv3'`
- `SSLContextSpec-sslv3-no-init.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=unsafe_protocol,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=unsafe_protocol obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SSLCONTEXT-ORDER-00 ev=init obj=SSLContext val='' exp='' msg='the observed call sequence is not one SSLContextSpec accepts'`
- `SSLContextSpec-sslv3.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3' msg='expecting one of Default,TLSv1.2,TLSv1.1,SSL,TLSv1,TLS,TLSv1.3 but found SSLv3'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='SSLv3' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='SSLv3' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec-sslv3.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=v=1 code=SSLCONTEXT-PROTO-00 ev=init obj=SSLContext val='SSLv3' exp='TLSV1.2,TLSV1.3,TLS' msg='expecting one of TLSV1.2,TLSV1.3,TLS but found SSLv3'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLS' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec-tls.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLS' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-00 ev=init obj=SSLContext val='TLSv1.2' exp='a KeyManager[] an observed KeyManagerFactory returned' msg='the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory'`
- `SSLContextSpec.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=SSLCONTEXT-NOBS-01 ev=init obj=SSLContext val='TLSv1.2' exp='a TrustManager[] an observed TrustManagerFactory returned' msg='the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory'`
