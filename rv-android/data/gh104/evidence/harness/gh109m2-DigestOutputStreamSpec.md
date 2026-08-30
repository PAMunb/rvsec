# DigestOutputStreamSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `DigestOutputStreamSpec-forbidden-on.txt` | introduced | — | on:DIGESTOUTPUTSTREAM-FORB-00 |
| `DigestOutputStreamSpec-unobserved-digest.txt` | introduced | — | c1:DIGESTOUTPUTSTREAM-NOBS-00 |

## Lines no pointcut resolved

- `DigestOutputStreamSpec-forbidden-on.txt` (A) `new DigestOutputStream(null, md) -> dos`
- `DigestOutputStreamSpec-forbidden-on.txt` (A) `dos.on(false)`
- `DigestOutputStreamSpec-forbidden-on.txt` (A) `dos.write(0)`
- `DigestOutputStreamSpec-forbidden-on.txt` (A) `dos.close()`
- `DigestOutputStreamSpec-unobserved-digest.txt` (A) `new DigestOutputStream(null, md) -> dos`
- `DigestOutputStreamSpec-unobserved-digest.txt` (A) `dos.write(0)`
- `DigestOutputStreamSpec-unobserved-digest.txt` (A) `dos.close()`

## Envelopes

- `DigestOutputStreamSpec-forbidden-on.txt` (B) `spec=DigestOutputStreamSpec,ev=on,type=ForbiddenMethod,msg=v=1 code=DIGESTOUTPUTSTREAM-FORB-00 ev=on obj=DigestOutputStream val='false' exp='no call at all' msg='DigestOutputStream.on(boolean) is forbidden by the expert DigestOutputStream.crysl'`
- `DigestOutputStreamSpec-unobserved-digest.txt` (B) `spec=DigestOutputStreamSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=DIGESTOUTPUTSTREAM-NOBS-00 ev=c1 obj=DigestOutputStream val='' exp='a MessageDigest this instrumentation observed being obtained' msg='no obtaining of the message digest was observed'`
