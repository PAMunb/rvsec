# DigestInputStreamSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 1

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `DigestInputStreamSpec-forbidden-on.txt` | introduced | — | on:DIGESTINPUTSTREAM-FORB-00 |

## Lines no pointcut resolved

- `DigestInputStreamSpec-forbidden-on.txt` (A) `new DigestInputStream(null, md) -> dis`
- `DigestInputStreamSpec-forbidden-on.txt` (A) `dis.on(false)`
- `DigestInputStreamSpec-forbidden-on.txt` (A) `dis.read()`
- `DigestInputStreamSpec-forbidden-on.txt` (A) `dis.close()`

## Envelopes

- `DigestInputStreamSpec-forbidden-on.txt` (B) `spec=DigestInputStreamSpec,ev=on,type=ForbiddenMethod,msg=v=1 code=DIGESTINPUTSTREAM-FORB-00 ev=on obj=DigestInputStream val='false' exp='no call at all' msg='DigestInputStream.on(boolean) is forbidden by the expert DigestInputStream.crysl'`
