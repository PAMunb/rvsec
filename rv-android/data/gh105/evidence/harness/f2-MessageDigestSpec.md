# MessageDigestSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MessageDigestSpec-guard-on-field.txt` | unchanged | MessageDigestSpec.update, MessageDigestSpec.d1 | MessageDigestSpec.update, MessageDigestSpec.d1 |
| `MessageDigestSpec-md5-only.txt` | unchanged | — | — |
| `MessageDigestSpec-md5.txt` | unchanged | — | — |
| `MessageDigestSpec-reset.txt` | unchanged | — | — |
| `MessageDigestSpec-sha1.txt` | unchanged | — | — |
| `MessageDigestSpec-unlisted-only.txt` | unchanged | MessageDigestSpec.g4 | MessageDigestSpec.g4 |
| `MessageDigestSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `MessageDigestSpec-reset.txt` — `md.reset()`
- `MessageDigestSpec-reset.txt` — `md.reset()`

## Envelopes

- `MessageDigestSpec-guard-on-field.txt` (A) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MESSAGEDIGEST-ORDER-00 ev=update obj=MessageDigest val='' exp='' msg='the observed call sequence is not one MessageDigestSpec accepts'`
- `MessageDigestSpec-guard-on-field.txt` (A) `spec=MessageDigestSpec,ev=d1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MESSAGEDIGEST-ORDER-00 ev=update obj=MessageDigest val='' exp='' msg='the observed call sequence is not one MessageDigestSpec accepts'`
- `MessageDigestSpec-guard-on-field.txt` (B) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MESSAGEDIGEST-ORDER-00 ev=update obj=MessageDigest val='' exp='' msg='the observed call sequence is not one MessageDigestSpec accepts'`
- `MessageDigestSpec-guard-on-field.txt` (B) `spec=MessageDigestSpec,ev=d1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MESSAGEDIGEST-ORDER-00 ev=update obj=MessageDigest val='' exp='' msg='the observed call sequence is not one MessageDigestSpec accepts'`
- `MessageDigestSpec-unlisted-only.txt` (A) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=MESSAGEDIGEST-ALG-02 ev=g4 obj=MessageDigest val='SHA3-256' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found SHA3-256'`
- `MessageDigestSpec-unlisted-only.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=MESSAGEDIGEST-ALG-02 ev=g4 obj=MessageDigest val='SHA3-256' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found SHA3-256'`
